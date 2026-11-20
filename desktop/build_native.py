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


SKIP_HEAD_STATES = {"MUSIC", "DJ", "PARTY_HORN", "UMBRELLA", "NINJA"}
SKIP_TORSO_STATES = {
    "STUDY", "GAMING", "LAPTOP_CODE", "GUITAR", "DRUM",
    "HUG_PLUSH", "EUCALYPTUS_HUG", "TOSTI", "BORREL", "PIZZA", "DJ", "JETPACK",
}


def compute_anchors():
    """Compute per-frame (hx, hy, tx, ty) outfit anchors by matching each frame against IDLE[0]."""
    idle0 = SPRITES["IDLE"][0]
    head_pts = [(x, y, idle0[y][x]) for y in range(6, 17) for x in range(4, 28) if idle0[y][x] in ("k", "g", "w")]
    torso_pts = [(x, y, idle0[y][x]) for y in range(17, 26) for x in range(9, 23) if idle0[y][x] in ("k", "w", "g")]

    def best_shift(fr, pts):
        best = (0, 0, -1.0)
        tot = len(pts)
        for dy in range(-6, 10):
            for dx in range(-6, 7):
                m = 0
                for x, y, c in pts:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < 32 and 0 <= ny < 32 and fr[ny][nx] == c:
                        m += 1
                sc = m / tot
                if sc > best[2] + 1e-6 or (abs(sc - best[2]) <= 1e-6 and (abs(dx) + abs(dy) < abs(best[0]) + abs(best[1]))):
                    best = (dx, dy, sc)
        return best

    anchors = {}
    for st, frames in SPRITES.items():
        fr_anc = []
        for fr in frames:
            hx, hy, hsc = best_shift(fr, head_pts)
            tx, ty, tsc = best_shift(fr, torso_pts)
            if hsc < 0.62:
                # Side/back/inverted/sleeping/peeking frame: hide both head & torso overlays
                fr_anc.append((99, 0, 99, 0))
            else:
                ahx, ahy = (99, 0) if st in SKIP_HEAD_STATES else (hx, hy)
                if st in SKIP_TORSO_STATES:
                    atx, aty = (99, 0)
                elif tsc >= 0.62:
                    atx, aty = (tx, ty)
                else:
                    atx, aty = (hx, hy)
                fr_anc.append((ahx, ahy, atx, aty))
        if any(a != (0, 0, 0, 0) for a in fr_anc):
            anchors[st] = fr_anc
    return anchors


def export_sprites_gz(out_path):
    lines = []
    pal_items = [f"{k}:{v}" for k, v in PALETTE.items() if v is not None and len(k) == 1]
    lines.append("PAL|" + ",".join(pal_items))
    div_items = [f"{k}={v}" for k, v in sorted(ANIM_DIV.items())]
    lines.append("DIV|" + ",".join(div_items))
    for st, fr_anc in sorted(compute_anchors().items()):
        spec = ";".join(f"{hx},{hy},{tx},{ty}" for hx, hy, tx, ty in fr_anc)
        lines.append(f"ANC|{st}={spec}")
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
