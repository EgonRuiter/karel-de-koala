#!/usr/bin/env bash
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH="$(uname -m)"
export KAREL_DRIVE_DIR="$HERE"

PY_SCRIPT="$HERE/../python_extended/karel.py"
[ -f "$PY_SCRIPT" ] || PY_SCRIPT="$HERE/python_extended/karel.py"

for a in "$@"; do
    case "$a" in
        --python|--full)
            if [ -f "$PY_SCRIPT" ] && command -v python3 >/dev/null 2>&1; then
                exec python3 "$PY_SCRIPT" "$@"
            fi
            ;;
    esac
done

BIN=""
for CAND in \
    "$HERE/.karel_linux_${ARCH}" \
    "$HERE/.karel_linux" \
    "$HERE/karel_linux_${ARCH}" \
    "$HERE/karel_linux" \
    "$HERE/desktop/karel_linux_${ARCH}" \
    "$HERE/desktop/karel_linux"; do
    if [ -f "$CAND" ]; then
        BIN="$CAND"
        break
    fi
done

RUN_DIR="${XDG_RUNTIME_DIR:-/tmp}/karel_de_koala_$(id -u)"
mkdir -p "$RUN_DIR"
RUN_BIN="$RUN_DIR/karel_linux_${ARCH}"

if [ -n "$BIN" ]; then
    cp -f "$BIN" "$RUN_BIN"
    chmod +x "$RUN_BIN"
elif [ -f "$HERE/build_linux.sh" ] && command -v gcc >/dev/null 2>&1; then
    echo "Karel Linux-versie eenmalig compileren..."
    if bash "$HERE/build_linux.sh" "$RUN_BIN"; then
        cp -f "$RUN_BIN" "$HERE/karel_linux_${ARCH}" 2>/dev/null || true
    fi
fi

if [ -x "$RUN_BIN" ]; then
    [ -f "$HERE/karel_sprites.gz" ] && cp -f "$HERE/karel_sprites.gz" "$RUN_DIR/karel_sprites.gz"
    exec "$RUN_BIN" "$@"
fi

if [ -f "$PY_SCRIPT" ] && command -v python3 >/dev/null 2>&1 && python3 -c "import tkinter" >/dev/null 2>&1; then
    exec python3 "$PY_SCRIPT" "$@"
fi

echo "Karel de Koala: geen voorgebouwde karel_linux_${ARCH} binary gevonden."
echo "Compileer eenmalig op Linux met:"
echo "  sudo apt install -y gcc libx11-dev libxext-dev && bash \"$HERE/build_linux.sh\""
exit 1
