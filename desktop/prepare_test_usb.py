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

TEST_README = """Karel de Koala - USB Test-Stick (Zero-Install)
===============================================

Deze gewone USB-stick boots niet als microcontroller (geen RP2350-chip),
maar gedraagt zich verder exact als de uiteindelijke Karel-stick:

1. Steek de USB-stick in willekeurige Windows-laptops/pc's, MacBooks of Linux-laptops.
2. Open het station `KAREL` (met eigen koala-icoon in Verkenner / Finder).
3. Start op Windows `launch_karel.bat`, op macOS `launch_karel.command` / `Karel.app`, op Linux `bash launch_karel.sh`.
4. Je XP, level, vacht, outfit en stats worden direct op DEZE stick
   opgeslagen in `save.json` en per stick-serienummer (`stick_serial`)
   gescheiden gehouden.

Wat er met de echte RP2350 SuperMini bordjes straks bijkomt:
- Automatisch starten ~2,5s na inpluggen via USB HID (Win+R)
- Live meeblinkende Sticky RGB LED op GP16 + optionele knop/touch
- Automatische stille SHA-256 updates via GitHub Releases (desktop + code.py)
"""


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


def populate_test_usb(target_dir, set_label=True, reset_save=False):
    """Copy Zero-Install Windows, macOS & Linux payload cleanly onto target_dir (folder or USB root)."""
    exe_src = os.path.join(HERE, "karel_native.exe")
    if not os.path.isfile(exe_src):
        raise FileNotFoundError(f"Niet gevonden: {exe_src}")
    os.makedirs(target_dir, exist_ok=True)
    files = (
        "karel_native.exe", "launch_karel.bat", "r.cmd", "t.cmd", "karel_sprites.gz",
        "karel_mac.swift", "build_mac.sh", "launch_karel.command",
        "karel_linux.c", "build_linux.sh", "launch_karel.sh",
        "karel_linux", "karel_linux_x86_64", "karel_linux_aarch64",
    )
    for fname in files:
        src = os.path.join(HERE, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(target_dir, fname))
    mac_app = os.path.join(HERE, "Karel.app")
    if os.path.isdir(mac_app):
        shutil.copytree(mac_app, os.path.join(target_dir, "Karel.app"), dirs_exist_ok=True)
    write_bundle_state(target_dir, force=reset_save)
    with open(os.path.join(target_dir, "README_TEST_STICK.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(TEST_README)
    labeled = set_volume_label(target_dir, "KAREL") if (set_label and len(target_dir) <= 3) else False
    return labeled


def main(argv=None):
    parser = argparse.ArgumentParser(description="Maak van een gewone USB-stick een Karel Test-Stick.")
    parser.add_argument("--drive", help="Schijfletter of doelmap, bijv. E:\\")
    parser.add_argument("--reset-save", action="store_true", help="Overschrijf bestaande save.json op de stick.")
    parser.add_argument("--no-label", action="store_true", help="Hernoem volumenaam niet naar KAREL.")
    args = parser.parse_args(argv)

    target = args.drive
    if not target:
        rems = find_removable_drives()
        if not rems:
            print("Geen verwijderbare USB-stick gevonden! Steek een USB-stick in en probeer opnieuw.")
            return 2
        if len(rems) == 1:
            target = rems[0]
        else:
            print("Meerdere USB-sticks gevonden:")
            for idx, r in enumerate(rems, 1):
                print(f"  [{idx}] {r}")
            pick = input("Kies nummer (of typ schijfletter zoals E:\\): ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(rems):
                target = rems[int(pick) - 1]
            else:
                target = pick
    if os.name == "nt" and len(target) == 1 and target.isalpha():
        target = target.upper() + ":\\"
    elif os.name == "nt" and len(target) == 2 and target[1] == ":":
        target = target.upper() + "\\"

    labeled = populate_test_usb(target, set_label=(not args.no_label), reset_save=args.reset_save)
    print(f"Klaar! Karel Test-Stick ingericht op: {target} (label=KAREL: {labeled})")
    print("Tip: Haal de USB-stick veilig uit & opnieuw erin om het nieuwe KAREL-icoon in Verkenner te zien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
