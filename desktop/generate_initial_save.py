#!/usr/bin/env python3
"""Standalone generator for initial save.json, .karel_drive, karel.ico, AUTORUN.INF & .VolumeIcon.icns."""

import argparse
import datetime
import json
import os
import struct
import zlib

_ICON_PAL = {
    ".": None, "R": (196, 30, 37, 255), "r": (150, 20, 26, 255),
    "d": (23, 27, 38, 255), "k": (36, 40, 48, 255), "g": (142, 148, 158, 255),
    "s": (108, 114, 125, 255), "w": (222, 226, 232, 255), "W": (255, 255, 255, 255),
    "p": (255, 122, 144, 255), "y": (245, 196, 81, 255),
}

_ICON_16 = (
    "..RRRRRRRRRRRR..",
    ".RddddddddddddR.",
    "RkggkddddddkggkR",
    "RkwwgkggggkgwwkR",
    "RkwwggggggggwwkR",
    "RdkggggggggggkdR",
    "RdgWkggggggkWgdR",
    "RdgkkggkkggkkgdR",
    "RdgppggkkggppgdR",
    "RdgggggkkgggggdR",
    "RddggggggggggddR",
    "RddRRRRRRRRRRddR",
    "RddrrddyyddrrddR",
    ".RddddddddddddR.",
    ".RrrrrrrrrrrrrR.",
    "..RRRRRRRRRRRR..",
)


def _scale_icon_grid(grid, factor):
    if factor <= 1:
        return grid
    out = []
    for row in grid:
        sr = "".join(ch * factor for ch in row)
        for _ in range(factor):
            out.append(sr)
    return out


def _encode_ico_dib(grid):
    h, w = len(grid), len(grid[0])
    hdr = struct.pack("<IIIHHIIIIII", 40, w, h * 2, 1, 32, 0, w * h * 4, 0, 0, 0, 0)
    xor_px = bytearray()
    and_rows = bytearray()
    and_stride = ((w + 31) // 32) * 4
    for y in range(h - 1, -1, -1):
        row = grid[y]
        mask_row = bytearray(and_stride)
        for x, ch in enumerate(row):
            rgba = _ICON_PAL.get(ch)
            if rgba is None:
                xor_px.extend(b"\x00\x00\x00\x00")
                mask_row[x // 8] |= 1 << (7 - (x % 8))
            else:
                r, g, b, a = rgba
                xor_px.extend((b, g, r, a))
        and_rows.extend(mask_row)
    return hdr + bytes(xor_px) + bytes(and_rows)


def build_default_save(name="Karel"):
    """Return initial Sticky USB profile save dictionary."""
    today = datetime.date.today().isoformat()
    return {
        "name": name,
        "hunger": 80,
        "happiness": 85,
        "energy": 85,
        "hygiene": 90,
        "caffeine": 25,
        "xp": 0,
        "level": 1,
        "streak_days": 1,
        "total_pets": 0,
        "skin": "classic",
        "equipped": ["scarf"],
        "roam_mode": "free",
        "karel_scale": 3,
        "auto_quiet_fullscreen": True,
        "language": "nl",
        "stick_serial": "",
        "quest_date": today,
        "last_seen": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def _png_chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _encode_png_rgba(grid):
    h, w = len(grid), len(grid[0])
    rows = bytearray()
    for row in grid:
        rows.append(0)
        for ch in row:
            rgba = _ICON_PAL.get(ch)
            rows.extend(rgba if rgba is not None else (0, 0, 0, 0))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + _png_chunk(b"IEND", b"")


def write_drive_branding(target_dir):
    """Write karel.ico, AUTORUN.INF (Windows) & .VolumeIcon.icns (macOS) into target_dir."""
    os.makedirs(target_dir, exist_ok=True)
    ico_path = os.path.join(target_dir, "karel.ico")
    inf_path = os.path.join(target_dir, "AUTORUN.INF")
    icns_path = os.path.join(target_dir, ".VolumeIcon.icns")

    dibs = [
        (48, _encode_ico_dib(_scale_icon_grid(_ICON_16, 3))),
        (32, _encode_ico_dib(_scale_icon_grid(_ICON_16, 2))),
        (16, _encode_ico_dib(_ICON_16)),
    ]
    hdr = struct.pack("<HHH", 0, 1, len(dibs))
    off = 6 + 16 * len(dibs)
    entries = bytearray()
    for sz, dib in dibs:
        entries.extend(struct.pack("<BBBBHHII", sz, sz, 0, 0, 1, 32, len(dib), off))
        off += len(dib)
    with open(ico_path, "wb") as f:
        f.write(hdr + bytes(entries) + b"".join(d for _, d in dibs))

    with open(inf_path, "wb") as f:
        f.write(b"[AutoRun]\r\nICON=karel.ico\r\nLABEL=KAREL\r\n")

    icns_chunks = bytearray()
    for tag, factor in ((b"icp4", 1), (b"icp5", 2), (b"ic07", 8)):
        png = _encode_png_rgba(_scale_icon_grid(_ICON_16, factor))
        icns_chunks.extend(tag + struct.pack(">I", 8 + len(png)) + png)
    with open(icns_path, "wb") as f:
        f.write(b"icns" + struct.pack(">I", 8 + len(icns_chunks)) + bytes(icns_chunks))
    return ico_path, inf_path, icns_path


def write_bundle_state(target_dir, name="Karel", force=False):
    """Write .karel_drive, karel.ico, AUTORUN.INF, .VolumeIcon.icns and save.json into target_dir."""
    os.makedirs(target_dir, exist_ok=True)
    marker_path = os.path.join(target_dir, ".karel_drive")
    save_path = os.path.join(target_dir, "save.json")

    with open(marker_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("KAREL_DE_KOALA_STICKY\n")
    write_drive_branding(target_dir)

    if os.path.exists(save_path) and not force:
        print(f"Kept existing save.json: {save_path} (use --force to overwrite)")
        return marker_path, save_path

    data = build_default_save(name=name)
    with open(save_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Created: {marker_path}")
    print(f"Created: {save_path}")
    return marker_path, save_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate default save.json and .karel_drive marker for Karel de Koala."
    )
    parser.add_argument(
        "--out",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Target directory (default: directory of this script, or path to the KAREL drive).",
    )
    parser.add_argument("--name", default="Karel", help="Koala name (default: Karel).")
    parser.add_argument("--force", action="store_true", help="Overwrite existing save.json if present.")
    args = parser.parse_args(argv)
    write_bundle_state(args.out, name=args.name, force=args.force)


if __name__ == "__main__":
    main()
