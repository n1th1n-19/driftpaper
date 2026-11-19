#!/bin/sh
# Installs Driftpaper into ~/.local (no root needed). Run with --uninstall to remove.
set -e
here=$(cd "$(dirname "$0")" && pwd)
plug=org.driftpaper.livewall
bin="$HOME/.local/bin"; wp="$HOME/.local/share/plasma/wallpapers/$plug"
app="$HOME/.local/share/applications/driftpaper.desktop"

if [ "$1" = "--uninstall" ]; then
    rm -rf "$wp" "$bin/driftpaper" "$app"
    echo "Removed. Your library in ~/.local/share/driftpaper was kept."
    exit 0
fi

mkdir -p "$bin" "$(dirname "$wp")" "$(dirname "$app")"
install -m755 "$here/bin/driftpaper" "$bin/driftpaper"
rm -rf "$wp"; cp -r "$here/plugin/$plug" "$wp"
cat > "$app" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Driftpaper
Comment=Add and switch live and static wallpapers
Exec=$bin/driftpaper
Icon=preferences-desktop-wallpaper
Categories=Settings;DesktopSettings;
DESKTOP
kbuildsycoca6 >/dev/null 2>&1 || true
echo "Installed. Launch 'Driftpaper' from the app menu or run driftpaper."
