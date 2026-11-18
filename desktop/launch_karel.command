#!/usr/bin/env bash
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$HERE/Karel.app"
[ -d "$APP" ] || APP="$HERE/desktop/Karel.app"
BUILD_SH="$HERE/build_mac.sh"
[ -f "$BUILD_SH" ] || BUILD_SH="$HERE/desktop/build_mac.sh"
PY_CMD="$HERE/../python_extended/launch_karel.command"
[ -f "$PY_CMD" ] || PY_CMD="$HERE/python_extended/launch_karel.command"

if [ "$(uname -s 2>/dev/null || true)" = "Darwin" ] && command -v xattr >/dev/null 2>&1; then
    xattr -dr com.apple.quarantine "$HERE" >/dev/null 2>&1 || true
fi

for a in "$@"; do
    case "$a" in
        --python|--full)
            if [ -f "$PY_CMD" ]; then
                exec bash "$PY_CMD" "$@"
            fi
            ;;
    esac
done

if [ ! -d "$APP" ] && [ -f "$BUILD_SH" ] && xcode-select -p >/dev/null 2>&1 && command -v swiftc >/dev/null 2>&1; then
    echo "Karel.app eenmalig compileren..."
    if ! bash "$BUILD_SH"; then
        echo ""
        echo "Compileren van Karel.app is mislukt. Kopieer de foutmelding hierboven."
        [ -t 0 ] && read -rp "Druk op Enter om te sluiten..."
        exit 1
    fi
fi

if [ -d "$APP" ]; then
    if [ "$#" -gt 0 ]; then
        open -a "$APP" --args "$@"
    else
        open "$APP"
    fi
    exit 0
fi

if [ -f "$PY_CMD" ]; then
    exec bash "$PY_CMD" "$@"
fi

MSG="Karel.app is nog niet gecompileerd voor macOS. Compileer eenmalig ./build_mac.sh op een Mac met Command Line Tools (of download Karel.app uit GitHub Actions)."
echo "$MSG"
if command -v osascript >/dev/null 2>&1; then
    osascript -e "display dialog \"$MSG\" buttons {\"OK\"} default button 1 with title \"Karel de Koala\"" >/dev/null 2>&1 || true
fi
exit 1
