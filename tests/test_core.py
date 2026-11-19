"""Run: python3 tests/test_core.py  (no framework, no Plasma needed)"""
import io, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from driftpaper import core, cli

tmp = Path(tempfile.mkdtemp())
core.LIB, core.THUMBS = tmp / "lib", tmp / "thumbs"
core.LIB.mkdir()
for n in ("rain-city.mp4", "rain-forest.webm", "sky.png", "notes.txt"):
    (core.LIB / n).write_bytes(b"x")

assert core.kind(Path("a.MP4")) == "live" and core.kind(Path("a.jpg")) == "static" and core.kind(Path("a.txt")) is None
assert {f.name for f in core.items()} == {"rain-city.mp4", "rain-forest.webm", "sky.png"}
assert [f.name for f in core.items("static")] == ["sky.png"]
assert core.find("sky").name == "sky.png" and core.find("RAIN-CITY").name == "rain-city.mp4"
for bad in ("rain", "nope"):  # ambiguous, missing
    try: core.find(bad); raise SystemExit(f"find({bad!r}) should fail")
    except core.Error: pass

core.sys.stderr = io.StringIO()  # non-tty bar prints once per percent
b = core.Bar(10, "x"); [b.update(i) for i in (0, 0, 5, 5, 10)]
assert core.sys.stderr.getvalue().count("\n") == 3, core.sys.stderr.getvalue()
core.sys.stderr = sys.__stderr__

a = cli.build().parse_args(["apply", "sky", "--screen", "2", "--no-pause-max"])
assert (a.name, a.screen, a.no_pause_max, a.no_pause_battery) == ("sky", 2, True, False)
assert cli.build().parse_args(["apply", "sky", "--pause-all"]).pause_all
assert cli.build().parse_args(["list", "--live"]).kind == "live"
print("ok")
