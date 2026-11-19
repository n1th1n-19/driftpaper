# Driftpaper

Keep a library of **static and live (video) wallpapers** on KDE Plasma 6 and switch between them per screen from a small desktop app.

- Add images or videos with a button or by dragging files onto the window (jpg, png, webp, mp4, webm, mkv, mov, gif).
- GIFs are converted to looping mp4 on import (QtMultimedia can't play GIF).
- Apply to all screens or a single one. Double-click a thumbnail to apply.
- Live wallpapers pause when a window is maximized/fullscreen on that screen and, optionally, when on battery.

It is two parts:

| Part | What it does |
|------|--------------|
| `bin/driftpaper` | PySide6 app. Manages the library in `~/.local/share/driftpaper/` and sets wallpapers through plasmashell's scripting DBus API. |
| `plugin/org.driftpaper.livewall` | Pure-QML Plasma wallpaper plugin that loops a video. No compiled code, no root needed. |

## Requirements

- KDE Plasma 6 (Wayland or X11)
- Python 3 with PySide6 (`pip install PySide6` or your distro's `python3-pyside6`)
- `ffmpeg` (thumbnails and GIF conversion)
- `qdbus-qt6` (usually in `qt6-qttools`)

## Install

```sh
git clone <this repo> && cd driftpaper
./install.sh            # installs to ~/.local, no sudo
./install.sh --uninstall
```

Then launch **Driftpaper** from the app menu, or run `driftpaper`.

## Notes and limits

- Video is muted and has no settings page, the app writes the plugin's config (`Video`, `PauseMaximized`, `PauseOnBattery`) directly.
- Memory and CPU depend on the clip. 1080p at 30 fps, short loops, are light. Avoid 4K/60 fps.
- Hardware decoding depends on your Qt Multimedia backend and GPU, hybrid-graphics laptops may fall back to the CPU.
- Pause-on-maximize uses Plasma's task manager model for the wallpaper's own screen.
- No day/night scheduling or playlists (yet).

## License

MIT, see [LICENSE](LICENSE).
