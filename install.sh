#!/bin/sh
# Driftpaper installer. One-liner (also updates an existing install):
#   curl -fsSL https://raw.githubusercontent.com/n1th1n-19/driftpaper/main/install.sh | sh
# From a checkout: ./install.sh      Remove later with: driftpaper uninstall
set -eu
REPO="n1th1n-19/driftpaper"
URL="${DRIFTPAPER_TARBALL:-https://github.com/$REPO/archive/refs/heads/main.tar.gz}"

command -v python3 >/dev/null 2>&1 || { echo "driftpaper: python3 is required" >&2; exit 1; }

if [ -f "$0" ] && [ -d "$(dirname "$0")/driftpaper" ] && [ -d "$(dirname "$0")/plugin" ]; then
    src=$(cd "$(dirname "$0")" && pwd)
else
    command -v curl >/dev/null 2>&1 || { echo "driftpaper: curl is required" >&2; exit 1; }
    command -v tar >/dev/null 2>&1 || { echo "driftpaper: tar is required" >&2; exit 1; }
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    echo "Downloading Driftpaper..."
    curl -fL --progress-bar "$URL" -o "$tmp/src.tar.gz"
    tar -xzf "$tmp/src.tar.gz" -C "$tmp"
    src=$(find "$tmp" -mindepth 1 -maxdepth 1 -type d | head -n 1)
fi

PYTHONPATH="$src" python3 -m driftpaper install --src "$src"
