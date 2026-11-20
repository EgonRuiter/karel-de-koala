#!/usr/bin/env python3
"""Prepare a normal USB flash drive as a plug-and-play Karel Test USB Stick."""

import argparse
import ctypes
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate_initial_save import write_bundle_state  # noqa: E402

VISIBLE_ROOT_ITEMS = {
    "Karel (Windows).exe",
    "Karel (Mac).app",
    "Karel (Linux).sh",
    "README.md",
}

OBSOLETE_ROOT_ITEMS = (
    "karel_native.exe",
    "launch_karel.bat",
    "launch_karel.command",
    "launch_karel.sh",
    "karel_mac.swift",
    "build_mac.sh",
    "karel_linux.c",
    "build_linux.sh",
    "karel_linux",
    "karel_linux_x86_64",
    "karel_linux_aarch64",
    "Karel.app",
    "Lees mij.html",
    "README_TEST_STICK.txt",
    "save.json.tmp",
    ".karel_no_hid",
    "AVG sandbox",
    "avast! sandbox",
)


def _set_hidden_attr(path, hidden=True):
    """Set or clear the FAT/Windows HIDDEN attribute (hides files on both Windows & macOS)."""
    if os.name != "nt" or not os.path.exists(path):
        return
    try:
        k32 = ctypes.windll.kernel32
        attrs = k32.GetFileAttributesW(path)
        if attrs == -1:
            return
        FILE_ATTRIBUTE_HIDDEN = 0x02
        new_attrs = (attrs | FILE_ATTRIBUTE_HIDDEN) if hidden else (attrs & ~FILE_ATTRIBUTE_HIDDEN)
        if new_attrs != attrs:
            k32.SetFileAttributesW(path, new_attrs)
    except Exception:
        pass


def _rm_path(path):
    if not os.path.lexists(path):
        return
    try:
        if os.name == "nt":
            ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.remove(path)
    except OSError:
        pass


def find_removable_drives():
    """Return list of ready removable Windows drive roots (e.g. ['E:\\\\'])."""
    if os.name != "nt":
        return []
    k32 = ctypes.windll.kernel32
    mask = k32.GetLogicalDrives()
    out = []
    for i in range(26):
        if not (mask & (1 << i)):
            continue
        root = f"{chr(65 + i)}:\\"
        if k32.GetDriveTypeW(root) == 2 and os.path.isdir(root):
            try:
                os.listdir(root)
                out.append(root)
            except OSError:
                pass
    return out


def set_volume_label(root, label="KAREL"):
    """Best-effort set Windows volume label to KAREL without formatting."""
    if os.name != "nt":
        return False
    try:
        ok = bool(ctypes.windll.kernel32.SetVolumeLabelW(root, label))
        return ok
    except Exception:
        return False


def _copy_over(src, dst):
    if os.name == "nt" and os.path.exists(dst):
        try:
            ctypes.windll.kernel32.SetFileAttributesW(dst, 0x80)
        except Exception:
            pass
    shutil.copy2(src, dst)


def populate_test_usb(target_dir, set_label=True, reset_save=False, include_firmware=None):
    """Copy clean Windows, macOS & Linux payload onto target_dir (folder, USB stick, or RP2350)."""
    exe_src = os.path.join(HERE, "karel_native.exe")
    if not os.path.isfile(exe_src):
        raise FileNotFoundError(f"Not found: {exe_src}")
    os.makedirs(target_dir, exist_ok=True)

    # Remove old/cluttered root items before writing the clean 4-item layout.
    for old_name in OBSOLETE_ROOT_ITEMS:
        _rm_path(os.path.join(target_dir, old_name))

    # Visible root launchers + OS-detecting guide (ONLY 4 visible items!)
    _copy_over(exe_src, os.path.join(target_dir, "Karel (Windows).exe"))
    mac_app = os.path.join(HERE, "Karel.app")
    if os.path.isdir(mac_app):
        dst_mac = os.path.join(target_dir, "Karel (Mac).app")
        _rm_path(dst_mac)
        shutil.copytree(mac_app, dst_mac)
    lin_sh = os.path.join(HERE, "launch_karel.sh")
    if os.path.isfile(lin_sh):
        _copy_over(lin_sh, os.path.join(target_dir, "Karel (Linux).sh"))
    readme_md = os.path.join(os.path.dirname(HERE), "README.md")
    if os.path.isfile(readme_md):
        _copy_over(readme_md, os.path.join(target_dir, "README.md"))

    # Hidden runtime support files
    spr_src = os.path.join(HERE, "karel_sprites.gz")
    if os.path.isfile(spr_src):
        _copy_over(spr_src, os.path.join(target_dir, "karel_sprites.gz"))
    for lin_bin in ("karel_linux_x86_64", "karel_linux_aarch64"):
        src = os.path.join(HERE, lin_bin)
        if os.path.isfile(src):
            _copy_over(src, os.path.join(target_dir, "." + lin_bin))

    # Optional / auto-detected RP2350 CircuitPython firmware (boot.py + code.py)
    is_rp2350 = os.path.isfile(os.path.join(target_dir, "boot_out.txt"))
    if include_firmware is True or (include_firmware is None and is_rp2350):
        fw_dir = os.path.join(os.path.dirname(HERE), "firmware")
        for fw in ("boot.py", "code.py"):
            src = os.path.join(fw_dir, fw)
            if os.path.isfile(src):
                _copy_over(src, os.path.join(target_dir, fw))
        # Remove unused adafruit_hid library from RP2350 flash (Zero-HID firmware)
        _rm_path(os.path.join(target_dir, "lib", "adafruit_hid"))

    # Clear Hidden on branding files before write_bundle_state rewrites them on Windows
    for bf in (".karel_drive", "karel.ico", "AUTORUN.INF", ".VolumeIcon.icns"):
        bp = os.path.join(target_dir, bf)
        if os.name == "nt" and os.path.exists(bp):
            try:
                ctypes.windll.kernel32.SetFileAttributesW(bp, 0x80)
            except Exception:
                pass
    write_bundle_state(target_dir, force=reset_save)

    # Mark ONLY the 4 user-facing files visible; hide all firmware/internal/dot files on Windows & macOS
    for entry in os.listdir(target_dir):
        full = os.path.join(target_dir, entry)
        _set_hidden_attr(full, hidden=(entry not in VISIBLE_ROOT_ITEMS))

    labeled = set_volume_label(target_dir, "KAREL") if (set_label and len(target_dir) <= 3) else False
    return labeled


def main(argv=None):
    parser = argparse.ArgumentParser(description="Provision a USB drive or RP2350 board as a Karel USB stick.")
    parser.add_argument("--drive", help="Drive letter or target folder, e.g. E:\\")
    parser.add_argument("--reset-save", action="store_true", help="Overwrite existing save.json on the drive.")
    parser.add_argument("--no-label", action="store_true", help="Do not rename the volume label to KAREL.")
    args = parser.parse_args(argv)

    target = args.drive
    if not target:
        rems = find_removable_drives()
        if not rems:
            print("No removable USB drive found! Plug in a USB drive and try again.")
            return 2
        if len(rems) == 1:
            target = rems[0]
        else:
            print("Multiple removable drives found:")
            for idx, r in enumerate(rems, 1):
                print(f"  [{idx}] {r}")
            pick = input("Choose number (or enter drive letter such as E:\\): ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(rems):
                target = rems[int(pick) - 1]
            else:
                target = pick
    if os.name == "nt" and len(target) == 1 and target.isalpha():
        target = target.upper() + ":\\"
    elif os.name == "nt" and len(target) == 2 and target[1] == ":":
        target = target.upper() + "\\"

    labeled = populate_test_usb(target, set_label=(not args.no_label), reset_save=args.reset_save)
    print(f"Done! Karel USB stick provisioned at: {target} (label=KAREL: {labeled})")
    print("Tip: Safely eject and reconnect the USB stick to refresh the KAREL drive icon in File Explorer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
