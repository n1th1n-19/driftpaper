# Driftpaper

Keep a library of **static and live (video) wallpapers** on KDE Plasma 6 and switch between them per screen, from a small desktop app or the command line.

## Install

One line, no root (installs into `~/.local`):

```sh
curl -fsSL https://raw.githubusercontent.com/n1th1n-19/driftpaper/main/install.sh | sh
```

You get a download progress bar and an install progress bar. Run the same line again to update, or use `driftpaper update`.

From a checkout instead: `git clone https://github.com/n1th1n-19/driftpaper && cd driftpaper && ./install.sh`

**Requirements:** KDE Plasma 6, Python 3.9+, `ffmpeg`, `qdbus-qt6` (`qt6-qttools`), and PySide6 for the GUI only (`pip install --user PySide6` or `python3-pyside6`). `driftpaper doctor` checks all of this.

## Update and uninstall

```sh
driftpaper update            # checks GitHub, downloads and installs the newest version (progress bars)
driftpaper update --check    # only check
driftpaper uninstall         # removes app, plugin, launcher; keeps your library
driftpaper uninstall --purge # also deletes the library and settings
```

Uninstall first switches any screen that is using live wallpaper back to the normal image wallpaper plugin.

## Usage

```sh
driftpaper                       # help
driftpaper gui                   # graphical app (also in the app menu)
driftpaper add rain.mp4 sky.png  # add to the library (GIFs are converted to mp4)
driftpaper list [--live|--static]
driftpaper apply rain            # all screens; name or any unique part of it
driftpaper apply sky --screen 2  # one screen
driftpaper random --live         # random pick
driftpaper back                  # undo the last apply
driftpaper status                # what each screen shows
driftpaper screens               # screen numbers
driftpaper remove rain -y
driftpaper doctor
driftpaper --help                # and driftpaper COMMAND --help
```

Live wallpapers pause when a window is maximized or fullscreen on that screen and when on battery. Turn either off per apply with `--no-pause-max` / `--no-pause-battery` (or the checkboxes in the GUI).

## How it works

| Part | What it does |
|------|--------------|
| `driftpaper/` | Python package. `core` and `cli` use only the standard library, `gui` needs PySide6. Library lives in `~/.local/share/driftpaper/`, wallpapers are set through plasmashell's scripting DBus API. |
| `plugin/org.driftpaper.livewall` | Pure-QML Plasma wallpaper plugin that loops a video. No compiled code, no root. |

## Notes and limits

- Video is muted. The plugin has no settings page, the app and CLI write its config (`Video`, `PauseMaximized`, `PauseAllScreens`, `PauseOnBattery`) directly.
- Memory and CPU depend on the clip. 1080p at 30 fps, short loops, are light. Avoid 4K/60 fps.
- Hardware decoding depends on your Qt Multimedia backend and GPU, hybrid-graphics laptops may fall back to the CPU.
- `update` tracks the `main` branch of this repo, there are no tagged releases yet.
- No day/night scheduling or playlists (yet).

## Develop

```sh
PYTHONPATH=. python3 -m driftpaper --help
python3 tests/test_core.py
```

## License

MIT, see [LICENSE](LICENSE).
