import argparse, sys
from pathlib import Path

from . import __version__, core, manage
from .core import Error

EPILOG = """examples:
  driftpaper add ~/Videos/rain.mp4 ~/Pictures/sky.png
  driftpaper list --live
  driftpaper apply rain                 # all screens
  driftpaper apply sky --screen 2       # second screen only
  driftpaper random --live              # surprise me
  driftpaper back                       # undo the last apply
  driftpaper update                     # fetch and install the latest version
"""


def _screen(n):
    return None if n is None else n - 1


def cmd_gui(a):
    try:
        from .gui import run
    except ImportError as e:
        raise Error(f"the GUI needs PySide6 ({e}). Install it: pip install --user PySide6")
    return run()


def cmd_list(a):
    fs = core.items(a.kind)
    if not fs:
        print("Library is empty. Add files with: driftpaper add FILE..."); return
    w = max(4, *(len(f.name) for f in fs))
    print(f"{'NAME':<{w}}  {'TYPE':<6}  SIZE")
    for f in fs:
        print(f"{f.name:<{w}}  {core.kind(f):<6}  {f.stat().st_size / 1e6:6.1f} MB")


def cmd_add(a):
    bar = core.Bar(len(a.files), "Adding")
    added, failed = [], []
    for i, p in enumerate(a.files):
        bar.update(i, f"converting/copying {Path(p).name}")
        try:
            added.append(core.import_file(Path(p)))
        except Error as e:
            failed.append(str(e))
    bar.update(len(a.files), "done"); bar.done()
    for f in added:
        print(f"added {f.name} ({core.kind(f)})")
    for m in failed:
        print("skipped:", m, file=sys.stderr)
    if a.apply and added:
        _apply(added[-1], a)
    return 1 if failed and not added else 0


def _apply(f, a):
    live, scr = core.apply(f, _screen(a.screen), not a.no_pause_max, not a.no_pause_battery)
    print(f"applied {'live' if live else 'static'} wallpaper {f.name} to screen(s) {', '.join(str(s + 1) for s in scr)}")


def cmd_apply(a):
    f = core.find(a.name)
    _apply(f, a)


def cmd_random(a):
    _apply(core.pick_random(a.kind), a)


def cmd_remove(a):
    fs = [core.find(n) for n in a.names]
    if not a.yes and sys.stdin.isatty():
        if input(f"Delete {', '.join(f.name for f in fs)} from the library? [y/N] ").strip().lower() != "y":
            print("Cancelled."); return
    elif not a.yes:
        raise Error("refusing to delete non-interactively, pass -y")
    for f in fs:
        core.remove(f); print("removed", f.name)


def cmd_back(a):
    print("restored previous wallpaper on screen(s)", ", ".join(str(s + 1) for s in core.back()))


def cmd_status(a):
    for d in core.status():
        what = d["video"] or d["image"] or "-"
        mode = "live" if d["plugin"] == core.LIVE_PLUGIN else d["plugin"].replace("org.kde.", "")
        print(f"screen {d['screen'] + 1}: {mode:<8} {Path(what.replace('file://', '')).name if what != '-' else '-'}")


def cmd_screens(a):
    print("\n".join(f"{s + 1}" for s in core.screens()))


def cmd_install(a):
    manage.install(a.src, manage.guess_commit(a.src))


def cmd_uninstall(a):
    manage.uninstall(a.purge, a.yes)


def cmd_update(a):
    manage.update(a.check, a.force)


def cmd_doctor(a):
    return manage.doctor()


def cmd_version(a):
    print(f"driftpaper {__version__}")


def build():
    p = argparse.ArgumentParser(prog="driftpaper", description="Live and static wallpaper manager for KDE Plasma 6.",
                                epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-V", "--version", action="version", version=f"driftpaper {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND")

    def add(name, fn, help, **kw):
        sp = sub.add_parser(name, help=help, description=help, **kw)
        sp.set_defaults(fn=fn)
        return sp

    def target(sp):
        sp.add_argument("-s", "--screen", type=int, metavar="N", help="screen number (see `driftpaper screens`), default all")

    def pauses(sp):
        sp.add_argument("--no-pause-max", action="store_true", help="live: keep playing under maximized windows")
        sp.add_argument("--no-pause-battery", action="store_true", help="live: keep playing on battery")

    add("gui", cmd_gui, "open the graphical app")
    sp = add("list", cmd_list, "list the wallpaper library")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--live", dest="kind", action="store_const", const="live", help="only videos")
    g.add_argument("--static", dest="kind", action="store_const", const="static", help="only images")
    sp = add("add", cmd_add, "add images/videos to the library (GIFs become mp4)")
    sp.add_argument("files", nargs="+", metavar="FILE")
    sp.add_argument("--apply", action="store_true", help="apply the last added file")
    target(sp); pauses(sp)
    sp = add("apply", cmd_apply, "set a wallpaper from the library (name or part of it)")
    sp.add_argument("name"); target(sp); pauses(sp)
    sp = add("random", cmd_random, "apply a random wallpaper from the library")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--live", dest="kind", action="store_const", const="live")
    g.add_argument("--static", dest="kind", action="store_const", const="static")
    target(sp); pauses(sp)
    sp = add("remove", cmd_remove, "delete wallpapers from the library")
    sp.add_argument("names", nargs="+", metavar="NAME"); sp.add_argument("-y", "--yes", action="store_true")
    add("back", cmd_back, "undo the last apply")
    add("status", cmd_status, "show what each screen is showing")
    add("screens", cmd_screens, "list screen numbers")
    add("doctor", cmd_doctor, "check dependencies and installation")
    sp = add("update", cmd_update, "download and install the latest version")
    sp.add_argument("--check", action="store_true", help="only check, don't install")
    sp.add_argument("--force", action="store_true", help="reinstall even if up to date")
    sp = add("uninstall", cmd_uninstall, "remove Driftpaper (the library is kept unless --purge)")
    sp.add_argument("--purge", action="store_true", help="also delete the library and settings")
    sp.add_argument("-y", "--yes", action="store_true", help="don't ask")
    sp = add("install", cmd_install, "install from a source checkout (used by install.sh)")
    sp.add_argument("--src", required=True, metavar="DIR")
    add("version", cmd_version, "print the version")
    return p


def main(argv=None):
    p = build()
    a = p.parse_args(argv)
    if not getattr(a, "fn", None):
        p.print_help(); return 0
    try:
        return a.fn(a) or 0
    except Error as e:
        print(f"driftpaper: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
