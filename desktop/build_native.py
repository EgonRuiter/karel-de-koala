#!/usr/bin/env python3
"""Build zero-install desktop/karel_native.exe from karel_native.cs + embedded sprites."""

import gzip
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY_EXT = os.path.join(os.path.dirname(HERE), "python_extended")
sys.path.insert(0, HERE)
if os.path.isdir(PY_EXT):
    sys.path.insert(1, PY_EXT)
from generate_initial_save import write_drive_branding  # noqa: E402
from karel_anims import ANIM_DIV  # noqa: E402
from karel_assets import PALETTE, SPRITES  # noqa: E402


def find_csc():
    for p in (
        r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
    ):
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(".NET Framework 4.x csc.exe niet gevonden.")


def export_sprites_gz(out_path):
    lines = []
    pal_items = [f"{k}:{v}" for k, v in PALETTE.items() if v is not None and len(k) == 1]
    lines.append("PAL|" + ",".join(pal_items))
    div_items = [f"{k}={v}" for k, v in sorted(ANIM_DIV.items())]
    lines.append("DIV|" + ",".join(div_items))
    for st, frames in SPRITES.items():
        lines.append("@" + st)
        for fi, fr in enumerate(frames):
            if fi > 0:
                lines.append("---")
            lines.extend(fr)
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    with gzip.open(out_path, "wb", compresslevel=9) as f:
        f.write(raw)
    return len(raw), os.path.getsize(out_path)


def patch_pe_removable_swap(exe_path):
    """Set IMAGE_FILE_REMOVABLE_RUN_FROM_SWAP (0x0400) & valid PE CheckSum so Windows keeps USB apps in swap/RAM."""
    with open(exe_path, "rb") as f:
        buf = bytearray(f.read())
    pe = struct.unpack_from("<I", buf, 0x3C)[0]
    if buf[pe : pe + 4] != b"PE\x00\x00":
        raise RuntimeError("Invalid PE header")
    ch_off = pe + 22
    chars = struct.unpack_from("<H", buf, ch_off)[0] | 0x0400
    struct.pack_into("<H", buf, ch_off, chars)
    cs_off = pe + 88
    struct.pack_into("<I", buf, cs_off, 0)
    pad = bytes(buf) + (b"\x00" * ((-len(buf)) % 4))
    acc = 0
    for off in range(0, len(pad), 4):
        acc += struct.unpack_from("<I", pad, off)[0]
        acc = (acc & 0xFFFFFFFF) + (acc >> 32)
    acc = (acc & 0xFFFF) + (acc >> 16)
    acc = (acc & 0xFFFF) + (acc >> 16)
    struct.pack_into("<I", buf, cs_off, (acc + len(buf)) & 0xFFFFFFFF)
    with open(exe_path, "wb") as f:
        f.write(buf)


def build_native(out_exe=None):
    csc = find_csc()
    ico_path = write_drive_branding(HERE)[0]
    cs_path = os.path.join(HERE, "karel_native.cs")
    exe_path = out_exe or os.path.join(HERE, "karel_native.exe")

    gz_path = os.path.join(HERE, "karel_sprites.gz")
    raw_sz, gz_sz = export_sprites_gz(gz_path)
    cmd = [
        csc,
        "/nologo",
        "/target:winexe",
        "/optimize+",
        "/platform:anycpu",
        f"/win32icon:{ico_path}",
        f"/resource:{gz_path},karel_sprites.gz",
        "/r:System.dll",
        "/r:System.Drawing.dll",
        "/r:System.Windows.Forms.dll",
        "/r:System.Web.Extensions.dll",
        f"/out:{exe_path}",
        cs_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"csc.exe failed:\n{res.stdout}\n{res.stderr}")
    patch_pe_removable_swap(exe_path)

    exe_sz = os.path.getsize(exe_path)
    print(f"Built {exe_path}: {exe_sz} B (sprites {raw_sz} B -> {gz_sz} B gzip)")
    chk = subprocess.run([exe_path, "--self-test"], capture_output=True, text=True, timeout=10)
    print("Self-test:", chk.returncode, chk.stdout.strip(), chk.stderr.strip())
    if chk.returncode != 0:
        raise RuntimeError(f"karel_native.exe self-test failed ({chk.returncode})")
    return exe_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    build_native(target)
