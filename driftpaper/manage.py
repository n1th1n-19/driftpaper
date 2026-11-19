"""install / update / uninstall / doctor. Everything lives under ~/.local, no root."""
import json, os, re, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path

from . import __version__, core
from .core import DATA, LIVE_PLUGIN, ROOT, Error, steps

BIN = Path.home() / ".local/bin" / "driftpaper"
PLUGIN_DIR = DATA / "plasma/wallpapers" / LIVE_PLUGIN
DESKTOP = DATA / "applications/driftpaper.desktop"
LAUNCHER = '#!/bin/sh\nexec env PYTHONPATH="{app}${{PYTHONPATH:+:$PYTHONPATH}}" python3 -m driftpaper "$@"\n'
DESKTOP_FILE = """[Desktop Entry]
Type=Application
Name=Driftpaper
Comment=Add and switch live and static wallpapers
Exec={bin} gui
Icon=preferences-desktop-wallpaper
Categories=Settings;DesktopSettings;
"""


def _refresh_cache():
    if shutil.which("kbuildsycoca6"):
        subprocess.run(["kbuildsycoca6"], capture_output=True)


def _src_version(src: Path):
    m = re.search(r'__version__ = "(.+?)"', (src / "driftpaper/__init__.py").read_text())
    return m.group(1) if m else "?"


def install(src, commit=None):
    src = Path(src).resolve()
    pkg, plug = src / "driftpaper", src / "plugin" / LIVE_PLUGIN
    if not pkg.is_dir() or not plug.is_dir():
        raise Error(f"{src} is not a Driftpaper source tree")
    warns = []

    def deps():
        for tool, why in (("ffmpeg", "thumbnails and GIF import"), ("kbuildsycoca6", "Plasma cache refresh")):
            if not shutil.which(tool):
                warns.append(f"{tool} not found ({why})")
        try:
            core.qdbus()
        except Error:
            warns.append("qdbus not found (install qt6-qttools), apply/status will not work")
        if subprocess.run([sys.executable, "-c", "import PySide6"], capture_output=True).returncode:
            warns.append("PySide6 not found, the GUI needs it: pip install --user PySide6")

    def app():
        dst = core.APP / "driftpaper"
        shutil.rmtree(dst, ignore_errors=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(pkg, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def plugin():
        shutil.rmtree(PLUGIN_DIR, ignore_errors=True)
        PLUGIN_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(plug, PLUGIN_DIR)

    def launcher():
        BIN.parent.mkdir(parents=True, exist_ok=True)
        BIN.write_text(LAUNCHER.format(app=core.APP)); BIN.chmod(0o755)
        DESKTOP.parent.mkdir(parents=True, exist_ok=True)
        DESKTOP.write_text(DESKTOP_FILE.format(bin=BIN))

    steps("Installing", [("checking dependencies", deps), ("copying app", app), ("installing wallpaper plugin", plugin),
                         ("creating launcher", launcher), ("refreshing Plasma cache", _refresh_cache)])
    core.save_state(installed={"version": _src_version(src), "commit": commit})
    for w in warns:
        print("warning:", w, file=sys.stderr)
    if str(BIN.parent) not in os.environ.get("PATH", "").split(":"):
        print(f"warning: {BIN.parent} is not in your PATH", file=sys.stderr)
    print(f"Driftpaper {_src_version(src)} installed. Run: driftpaper  (or find it in the app menu)")


def guess_commit(src):
    """Commit of a source tree: git HEAD for a checkout, else the latest on GitHub (what a curl|sh fetched)."""
    try:
        r = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    except OSError:  # git not installed
        pass
    try:
        return latest_sha()
    except Error:
        return None


def uninstall(purge=False, yes=False):
    if not yes:
        if not sys.stdin.isatty():
            raise Error("refusing to uninstall non-interactively, pass -y")
        what = "app, plugin and launcher" + (" AND your wallpaper library" if purge else " (library is kept)")
        if input(f"Remove Driftpaper {what}? [y/N] ").strip().lower() != "y":
            print("Cancelled."); return
    detached = []

    def detach():
        try:
            detached.append(core.detach_live())
        except Error:
            pass  # plasmashell not running, nothing to switch

    def rm(*paths):
        return lambda: [shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True) for p in paths]

    funcs = [("switching screens off live wallpaper", detach), ("removing wallpaper plugin", rm(PLUGIN_DIR)),
             ("removing launcher", rm(BIN, DESKTOP)), ("removing app", rm(core.APP)), ("refreshing Plasma cache", _refresh_cache)]
    if purge:
        funcs.append(("deleting library and settings", rm(ROOT)))
    steps("Uninstalling", funcs)
    if detached and detached[0]:
        print(f"{detached[0]} screen(s) were using live wallpaper and are back on the image wallpaper plugin.")
    print("Driftpaper removed." + ("" if purge else f" Library kept in {ROOT}"))


def latest_sha():
    if os.environ.get("DRIFTPAPER_SHA"):
        return os.environ["DRIFTPAPER_SHA"]
    import urllib.request
    req = urllib.request.Request(f"https://api.github.com/repos/{core.REPO}/commits/main",
                                 headers={"Accept": "application/vnd.github.sha", "User-Agent": "driftpaper"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode().strip()
    except OSError as e:
        raise Error(f"could not check for updates: {e}")


def update(check=False, force=False):
    cur = core._state().get("installed", {}).get("commit")
    latest = latest_sha()
    if cur == latest and not force:
        print(f"Already up to date (version {__version__}, {latest[:7]})."); return
    print(f"Reinstalling {latest[:7]}" if cur == latest else f"Update available: {cur[:7] if cur else 'unknown'} -> {latest[:7]}")
    if check:
        return
    url = os.environ.get("DRIFTPAPER_TARBALL") or f"https://github.com/{core.REPO}/archive/refs/heads/main.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        tgz = Path(tmp) / "src.tar.gz"
        core.download(url, tgz, "Downloading")
        with tarfile.open(tgz) as t:
            members = t.getmembers()
            bar = core.Bar(len(members), "Extracting")
            for i, m in enumerate(members):
                t.extract(m, tmp, filter="data"); bar.update(i + 1)
            bar.done()
        roots = [p for p in Path(tmp).iterdir() if p.is_dir()]
        if len(roots) != 1:
            raise Error("unexpected archive layout")
        install(roots[0], commit=latest)


def doctor():
    ok = True

    def row(good, name, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"  {'ok  ' if good else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))

    print(f"Driftpaper {__version__}")
    row(sys.version_info >= (3, 9), "python", sys.version.split()[0])
    row(shutil.which("ffmpeg"), "ffmpeg", "thumbnails, GIF import")
    try:
        row(core.qdbus(), "qdbus")
        row(core.status() is not None, "plasmashell reachable")
    except Error as e:
        row(False, "plasma scripting", str(e))
    row(PLUGIN_DIR.is_dir(), "live wallpaper plugin", str(PLUGIN_DIR))
    row(subprocess.run([sys.executable, "-c", "import PySide6"], capture_output=True).returncode == 0, "PySide6", "GUI only")
    return 0 if ok else 1
