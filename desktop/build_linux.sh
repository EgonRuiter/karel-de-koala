#!/usr/bin/env bash
# Build native Linux X11/XShape companion binary from karel_linux.c and run --self-test.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/karel_linux.c"
SPRITES="$HERE/karel_sprites.gz"
ARCH="$(uname -m)"
OUT="${1:-$HERE/karel_linux_${ARCH}}"

if [ "$(uname -s)" != "Linux" ]; then
    echo "Error: build_linux.sh must be run on Linux."
    exit 1
fi

command -v gcc >/dev/null 2>&1 || {
    echo "Error: gcc not found (Ubuntu/Debian: sudo apt install -y gcc)."
    exit 1
}

if [ ! -f "$SPRITES" ] && command -v python3 >/dev/null 2>&1 && [ -f "$HERE/sprites/karel_assets.py" ]; then
    python3 -c "import sys; sys.path.insert(0, '$HERE'); import build_native; build_native.export_sprites_gz('$SPRITES')" || true
fi
[ -f "$SPRITES" ] || { echo "Error: karel_sprites.gz not found."; exit 1; }

LIB_ARGS=()
TMP_LIB=""
trap 'if [ -n "$TMP_LIB" ] && [ -d "$TMP_LIB" ]; then rm -rf "$TMP_LIB"; fi' EXIT

# Fallback: if X11 dev headers are absent, link against runtime libX11.so.6 / libXext.so.6 via temp symlinks.
if ! echo '#include <X11/extensions/shape.h>' | gcc -E - >/dev/null 2>&1; then
    X11_SO="$(ldconfig -p 2>/dev/null | awk '/libX11\.so\.6 /{print $NF; exit}')"
    XEXT_SO="$(ldconfig -p 2>/dev/null | awk '/libXext\.so\.6 /{print $NF; exit}')"
    if [ -n "$X11_SO" ] && [ -n "$XEXT_SO" ] && [ -e "$X11_SO" ] && [ -e "$XEXT_SO" ]; then
        TMP_LIB="$(mktemp -d)"
        ln -sf "$X11_SO" "$TMP_LIB/libX11.so"
        ln -sf "$XEXT_SO" "$TMP_LIB/libXext.so"
        LIB_ARGS=(-L"$TMP_LIB")
    else
        echo "Error: X11 libraries missing (Ubuntu/Debian: sudo apt install -y libx11-dev libxext-dev)."
        exit 1
    fi
fi

gcc -Os -s -std=c99 -Wall -Wextra -Werror "$SRC" "${LIB_ARGS[@]}" -lX11 -lXext -lm -o "$OUT"
chmod +x "$OUT"
cp -f "$OUT" "$HERE/karel_linux" 2>/dev/null || true

SIZE_KB="$(du -k "$OUT" | cut -f1)"
echo "Built: $OUT (${SIZE_KB} KB)"
KAREL_DRIVE_DIR="$HERE" "$OUT" --self-test
