"""Shared logic: library, thumbnails, Plasma scripting, progress bar. Stdlib only."""
import json, os, random, shutil, subprocess, sys, time
from pathlib import Path

REPO = "n1th1n-19/driftpaper"
DATA = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
ROOT = DATA / "driftpaper"
LIB, THUMBS, STATE, APP = ROOT / "library", ROOT / "thumbs", ROOT / "state.json", ROOT / "app"
IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"}
VIDEOS = {".mp4", ".webm", ".mkv", ".mov", ".gif"}  # gif is converted to mp4 on import
LIVE_PLUGIN, IMAGE_PLUGIN = "org.driftpaper.livewall", "org.kde.image"


class Error(Exception):
    """User-facing failure; the CLI prints the message without a traceback."""


# ---------- progress bar ----------
class Bar:
    """`[#####-----]  50%  label` on stderr. total=None -> indeterminate (shows a counter)."""

    def __init__(self, total=None, label=""):
        self.total, self.label, self.tty, self.last = total, label, sys.stderr.isatty(), -1

    def update(self, done, label=None, text=None):
        label = self.label if label is None else label
        if self.total:
            pct = min(100, int(done * 100 / self.total))
            if not self.tty and pct == self.last:
                return
            self.last = pct
            fill = pct * 24 // 100
            line = f"[{'#' * fill}{'-' * (24 - fill)}] {pct:3d}%  {label}" + (f"  {text}" if text else "")
        else:
            line = f"[{'~' * 24}] {label}  {text or done}"
        if self.tty:
            sys.stderr.write("\r\033[K" + line); sys.stderr.flush()
        else:
            sys.stderr.write(line + "\n")

    def done(self, label=None):
        if self.tty:
            sys.stderr.write("\r\033[K")
        if label:
            sys.stderr.write(label + "\n")
        sys.stderr.flush()


def steps(title, funcs):
    """Run [(label, fn), ...] with a progress bar; the first failure stops the run."""
    bar = Bar(len(funcs), title)
    for i, (label, fn) in enumerate(funcs):
        bar.update(i, label)
        fn()
    bar.update(len(funcs), "done"); bar.done()


def download(url, dest: Path, label="Downloading"):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "driftpaper"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0) or None
            bar, got = Bar(total, label), 0
            while chunk := r.read(64 * 1024):
                f.write(chunk); got += len(chunk)
                bar.update(got, text=f"{got / 1e6:.1f} MB")
            bar.done()
    except OSError as e:
        raise Error(f"download failed: {e}")


# ---------- Plasma ----------
def qdbus():
    for n in ("qdbus-qt6", "qdbus6", "qdbus"):
        if shutil.which(n):
            return n
    raise Error("qdbus not found (install qt6-qttools)")


def plasma(script: str) -> str:
    r = subprocess.run([qdbus(), "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script],
                       capture_output=True, text=True)
    if r.returncode:
        raise Error(r.stderr.strip() or "plasmashell is not reachable (are you running Plasma?)")
    return r.stdout.strip()


def status():
    """[{screen, plugin, image, video}] for every desktop, screen is 0-based."""
    out = plasma("""var o=[];desktops().forEach(function(d){d.currentConfigGroup=["Wallpaper",d.wallpaperPlugin,"General"];
        o.push({screen:d.screen,plugin:d.wallpaperPlugin,image:d.readConfig("Image")||"",video:d.readConfig("Video")||""})});
        print(JSON.stringify(o))""")
    return sorted(json.loads(out), key=lambda d: d["screen"])


def screens():
    return [d["screen"] for d in status()]


def _write(entries):
    """entries: [{screen, plugin, cfg}] -> set each desktop's plugin and config."""
    plasma(f"""var e={json.dumps(entries)};
        desktops().forEach(function(d){{e.forEach(function(x){{if(x.screen!==d.screen)return;
            d.wallpaperPlugin=x.plugin;d.currentConfigGroup=["Wallpaper",x.plugin,"General"];
            for(var k in x.cfg)d.writeConfig(k,x.cfg[k]);d.reloadConfig()}})}});""")


def _state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(**kv):
    ROOT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({**_state(), **kv}, indent=1))


# ---------- library ----------
def kind(p: Path):
    e = p.suffix.lower()
    return "live" if e in VIDEOS else "static" if e in IMAGES else None


def items(which=None):
    LIB.mkdir(parents=True, exist_ok=True)
    fs = [f for f in LIB.iterdir() if kind(f) and (which in (None, kind(f)))]
    return sorted(fs, key=lambda p: p.stat().st_mtime, reverse=True)


def find(query: str) -> Path:
    """Exact filename/stem first, then a unique case-insensitive substring."""
    q, fs = query.lower(), items()
    exact = [f for f in fs if q in (f.name.lower(), f.stem.lower())]
    hits = exact or [f for f in fs if q in f.name.lower()]
    if not hits:
        raise Error(f"no wallpaper matches '{query}' (try: driftpaper list)")
    if len(hits) > 1:
        raise Error(f"'{query}' is ambiguous: " + ", ".join(f.name for f in hits))
    return hits[0]


def thumb_path(f: Path):
    return THUMBS / (f.stem + ".jpg")


def make_thumb(f: Path):
    """320x180 jpg via ffmpeg (images and videos). Silent no-op if ffmpeg is missing."""
    if not shutil.which("ffmpeg"):
        return
    THUMBS.mkdir(parents=True, exist_ok=True)
    vf = "scale=320:180:force_original_aspect_ratio=increase,crop=320:180"
    base = ["ffmpeg", "-y", "-loglevel", "quiet", "-strict", "unofficial"]
    for seek in (["-ss", "1"], []) if kind(f) == "live" else ([],):
        subprocess.run(base + seek + ["-i", str(f), "-frames:v", "1", "-vf", vf, str(thumb_path(f))],
                       stderr=subprocess.DEVNULL)
        if thumb_path(f).exists():
            return


def import_file(src: Path) -> Path:
    src = Path(src).expanduser()
    if not src.is_file() or not kind(src):
        raise Error(f"{src.name}: not a supported image/video file")
    LIB.mkdir(parents=True, exist_ok=True)
    dst, n = LIB / src.name, 1
    while dst.exists():
        dst = LIB / f"{src.stem}-{n}{src.suffix}"; n += 1
    if src.suffix.lower() == ".gif":  # Qt Multimedia can't play gif -> loopable mp4
        if not shutil.which("ffmpeg"):
            raise Error("ffmpeg is needed to import GIFs")
        dst = dst.with_suffix(".mp4")
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-movflags", "faststart",
                            "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", str(dst)],
                           capture_output=True, text=True)
        if r.returncode:
            raise Error(f"{src.name}: ffmpeg failed: {r.stderr.strip()[-200:]}")
    else:
        shutil.copy2(src, dst)
    make_thumb(dst)
    return dst


def remove(f: Path):
    f.unlink(missing_ok=True)
    thumb_path(f).unlink(missing_ok=True)


# ---------- apply ----------
def apply(f: Path, screen=None, pause_max=True, pause_battery=True):
    """screen: 0-based index or None for all. Remembers what was there so `back` can undo."""
    live = kind(f) == "live"
    plugin = LIVE_PLUGIN if live else IMAGE_PLUGIN
    cfg = ({"Video": f.as_uri(), "PauseMaximized": pause_max, "PauseOnBattery": pause_battery}
           if live else {"Image": f.as_uri()})
    cur = status()
    if screen is not None and screen not in [d["screen"] for d in cur]:
        raise Error(f"no screen {screen + 1} (have {len(cur)})")
    target = [d for d in cur if screen in (None, d["screen"])]
    save_state(previous=[{"screen": d["screen"], "plugin": d["plugin"],
                          "cfg": {k: v for k, v in (("Image", d["image"]), ("Video", d["video"])) if v}}
                         for d in target])
    _write([{"screen": d["screen"], "plugin": plugin, "cfg": cfg} for d in target])
    return live, [d["screen"] for d in target]


def back():
    prev = _state().get("previous")
    if not prev:
        raise Error("nothing to go back to yet")
    _write(prev)
    return [p["screen"] for p in prev]


def detach_live():
    """Switch every screen using the live plugin back to the image plugin (used before uninstall)."""
    mine = [{"screen": d["screen"], "plugin": IMAGE_PLUGIN, "cfg": {}} for d in status() if d["plugin"] == LIVE_PLUGIN]
    if mine:
        _write(mine)
    return len(mine)


def pick_random(which=None):
    fs = items(which)
    if not fs:
        raise Error("library is empty (try: driftpaper add FILE)")
    return random.choice(fs)
