#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/karel_mac.swift"
SPRITES="$HERE/karel_sprites.gz"
APP="$HERE/Karel.app"
MACOS_DIR="$APP/Contents/MacOS"
RES_DIR="$APP/Contents/Resources"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Fout: build_mac.sh moet op macOS draaien (voor Xcode/Swift macOS SDK)."
    exit 1
fi

if ! xcode-select -p >/dev/null 2>&1 || ! command -v swiftc >/dev/null 2>&1; then
    echo "Fout: swiftc / Xcode Command Line Tools vereist voor eenmalig bouwen: xcode-select --install"
    exit 1
fi

if [ ! -f "$SPRITES" ] && command -v python3 >/dev/null 2>&1 && [ -f "$HERE/../python_extended/karel_assets.py" ]; then
    python3 -c "import sys; sys.path.insert(0, '$HERE'); sys.path.insert(1, '$HERE/../python_extended'); import build_native; build_native.export_sprites_gz('$SPRITES')" || true
fi
[ -f "$SPRITES" ] || { echo "Fout: karel_sprites.gz niet gevonden naast build_mac.sh."; exit 1; }

rm -rf "$APP"
mkdir -p "$MACOS_DIR" "$RES_DIR"

ARM_BIN="$(mktemp "${TMPDIR:-/tmp}/karel_arm64.XXXXXX")"
X64_BIN="$(mktemp "${TMPDIR:-/tmp}/karel_x64.XXXXXX")"
trap 'rm -f "$ARM_BIN" "$X64_BIN"' EXIT

BUILD_ARM=0
BUILD_X64=0
swiftc -Osize -framework Cocoa -target arm64-apple-macosx12.0 "$SRC" -o "$ARM_BIN" 2>/dev/null && BUILD_ARM=1 || true
swiftc -Osize -framework Cocoa -target x86_64-apple-macosx12.0 "$SRC" -o "$X64_BIN" 2>/dev/null && BUILD_X64=1 || true

if [ "$BUILD_ARM" -eq 1 ] && [ "$BUILD_X64" -eq 1 ]; then
    lipo -create "$ARM_BIN" "$X64_BIN" -output "$MACOS_DIR/Karel"
elif [ "$BUILD_ARM" -eq 1 ]; then
    cp "$ARM_BIN" "$MACOS_DIR/Karel"
elif [ "$BUILD_X64" -eq 1 ]; then
    cp "$X64_BIN" "$MACOS_DIR/Karel"
else
    swiftc -Osize -framework Cocoa "$SRC" -o "$MACOS_DIR/Karel"
fi

strip -x "$MACOS_DIR/Karel" 2>/dev/null || true
chmod +x "$MACOS_DIR/Karel"

cp "$SPRITES" "$RES_DIR/karel_sprites.gz"
[ -f "$HERE/.VolumeIcon.icns" ] && cp "$HERE/.VolumeIcon.icns" "$RES_DIR/AppIcon.icns"

cat >"$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Karel</string>
    <key>CFBundleIdentifier</key>
    <string>nl.svsticky.karel</string>
    <key>CFBundleName</key>
    <string>Karel de Koala</string>
    <key>CFBundleDisplayName</key>
    <string>Karel de Koala</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.1.7</string>
    <key>CFBundleVersion</key>
    <string>217</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true

APP_SIZE="$(du -sk "$APP" | cut -f1)"
echo "Gebouwd: $APP (${APP_SIZE} KB)"
"$MACOS_DIR/Karel" --self-test
