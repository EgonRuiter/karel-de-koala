#!/usr/bin/env bash
# Linux USB launcher wrapper (shipped on the KAREL drive as "Karel (Linux).sh").
# Copies the prebuilt binary from the FAT32/noexec USB mount into a private (0700)
# runtime directory so it can be executed cleanly and safely.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH="$(uname -m)"
export KAREL_DRIVE_DIR="$HERE"

# Locate the matching prebuilt binary on the USB drive or local build directory.
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

# Use an owner-verified XDG_RUNTIME_DIR or a private mktemp directory (mode 0700) to prevent /tmp symlink attacks.
CLEANUP_DIR=""
if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -d "$XDG_RUNTIME_DIR" ] && [ -O "$XDG_RUNTIME_DIR" ]; then
    RUN_DIR="$XDG_RUNTIME_DIR/karel_de_koala"
    mkdir -p "$RUN_DIR"
    chmod 700 "$RUN_DIR"
else
    RUN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/karel_de_koala.XXXXXX")"
    chmod 700 "$RUN_DIR"
    CLEANUP_DIR="$RUN_DIR"
    trap 'rm -rf "$CLEANUP_DIR"' EXIT INT TERM
fi
RUN_BIN="$RUN_DIR/karel_linux_${ARCH}"

if [ -n "$BIN" ]; then
    cp -f "$BIN" "$RUN_BIN"
    chmod +x "$RUN_BIN"
elif [ -f "$HERE/build_linux.sh" ] && command -v gcc >/dev/null 2>&1; then
    echo "Compiling Karel Linux binary (one-time build)..."
    if bash "$HERE/build_linux.sh" "$RUN_BIN"; then
        cp -f "$RUN_BIN" "$HERE/.karel_linux_${ARCH}" 2>/dev/null || true
    fi
fi

if [ -x "$RUN_BIN" ]; then
    [ -f "$HERE/karel_sprites.gz" ] && cp -f "$HERE/karel_sprites.gz" "$RUN_DIR/karel_sprites.gz"
    if [ -n "$CLEANUP_DIR" ]; then
        "$RUN_BIN" "$@"
        exit $?
    fi
    exec "$RUN_BIN" "$@"
fi

echo "Karel de Koala: no prebuilt karel_linux_${ARCH} binary found."
echo "Build once on Linux with:"
echo "  sudo apt install -y gcc libx11-dev libxext-dev && bash \"$HERE/build_linux.sh\""
exit 1
