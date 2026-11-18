# Karel de Koala — Assembly-Line Deployment Guide (50× RP2350 SuperMini in <30 Min)

Complete deployment guide for programming **50 Sticky RP2350 SuperMini boards** (`RP2350A`, 4 MB QSPI Flash, USB-C) with CircuitPython, two-way USB HID + CDC + MSC support, and **Karel de Koala**.

---

## 1. Hardware Pinout & Variant Configuration (`RP2350 SuperMini`)

| Function | GPIO Pin | Wiring / Notes |
|---|---|---|
| **WS2812 RGB LED (NeoPixel)** | **`GP16`** (default) / **`GP23`** or **`GP22`** (batch toggle) | Checks explicit `NEOPIXEL_PIN_NAME` (`"GP16"` default for RP2350 SuperMini / Zero layout) -> `board.NEOPIXEL` -> `GP16` -> `GP23`; 1-line toggle in [`firmware/boot.py`](firmware/boot.py) and [`firmware/code.py`](firmware/code.py) if your batch wires WS2812 to `GP22` or `GP23`. Falls back to onboard mono LED (`LED`/`GP17`/`GP25`) if a batch lacks WS2812. |
| **Onboard `BOOT` Button** | **`BOOTSEL`** (QSPI CS) | **Only onboard tactile button** on this 1-button RP2350 SuperMini! Hold **`BOOT`** while plugging USB-C to enter **`RP2350`** UF2 bootloader mode. Because `BOOT` sits directly on QSPI Flash `CSn` (XIP), CircuitPython on RP2350 cannot read it as a runtime toggle button after boot. |
| **Start / Stop Toggle Button** | **`GP15 -> GND`** (or **`GP24 -> GND`**) | Optional tiny external tactile button (note: on the SuperMini PCB back, pad **`24`** sits directly beside **`G`** (`GND`), or solder **`15` -> `GND`** on the bottom-left edge!). Pressing once **shows Karel** (climbing up behind taskbar via `Win+r -> launch_karel.bat --toggle`) or **cleanly closes Karel** (waves goodbye + dives smoothly back down behind the taskbar via `EVENT:TOGGLE_KAREL` / `--toggle` -> `STATE:BYE`)! |
| **Hardware Boop / `RUN` Pin** | **USB-C Replug** (or external `RUN`) | This 1-button RP2350 SuperMini has no onboard `RST` switch: simply **unplug & replug USB-C** while Karel runs to trigger the singleton handshake (`Win+r` -> `launch_karel.bat` on `127.0.0.1:42421`) and wake/boop Karel cleanly without opening a duplicate! If an external switch wires `RUN` to `GND`, `ResetReason.RESET_PIN` skips `GUI+r` (3.0 s silent ping) and sends **`EVENT:RST_BOOP`**. |
| **Dev / Safe Mode** | **`GP0`** (outer header pin -> `GND`) | Connect **`GP0` to `GND`** on the outer edge while plugging in USB: skips HID `GUI+r` auto-launch and holds solid **cyan** LED (`GP24` -> `GND` also triggers Dev Mode). |
| **Optional Pet Capacitive Pad (`EVENT:PET`)** | **`GP2`** | Copper tape / brass pad on case. Due to RP2350 GPIO E9 behavior, CircuitPython `touchio.TouchIn(..., pull=digitalio.Pull.UP)` requires an external **1 MΩ–2.2 MΩ pull-up resistor from `GP2` to `3.3V`** (`code.py` tries `Pull.UP` touch first and falls back cleanly to a digital `Pull.UP` input if unpopulated). |
| **Optional Action Button (`EVENT:FEED` / `COFFEE` / `MINIGAME`)** | **`GP1`** | Tactile switch wired between `GP1` and `GND` (internal `Pull.UP`). Short = Feed, Double = Coffee, Long (1.5s) = Mini-game. |
| **Optional Backup Action Touch Pad** | **`GP3`** | Second copper pad (mirrored to `GP1`) if no tactile switch is installed (also requires 1 MΩ pull-up to `3.3V` on RP2350 for capacitive touch). |

---

## 2. Flash Storage & Size Budget Verification (4 MB Flash)

The **RP2350 SuperMini** typically carries **4 MB (`4,096 KB`) QSPI Flash** (leaving **~2.5–2.9 MB** usable on the `CIRCUITPY` / `KAREL` USB partition after CircuitPython 9.2+ / 10.x). Because the **Zero-Install native host (`karel_native.exe`)** is now the streamlined standard (while the extended 7-tab/10-game Python suite lives separately in [`python_extended/`](python_extended/)), the entire drive payload uses **< 0.18 MB** (`~2.3+ MB` free — copies in ~1–2s per board!):

| Drive Path | Source File | Measured Size (Bytes) | Role |
|---|---|---:|---|
| `/boot.py` | `firmware/boot.py` | 2,949 B | USB label `KAREL`, host-RW remount, HID + Dual CDC, Dev Mode (`GP0`/`GP24`) |
| `/code.py` | `firmware/code.py` | 20,063 B | RP2350 SuperMini Base64 `Win+R` launch (skips via `/.karel_no_hid`), Toggle (`GP15`/`GP24`), NeoPixel (`GP16`/`GP23`) |
| `/karel_native.exe` | `desktop/karel_native.exe` | 94,208 B | **Standard Zero-Install** Windows `.NET 4.x` host (54 anims, skins/outfits, Auto-Quiet, Serial LED, Tray, `UMBRELLA` glide, Mini-Hub, SHA-256 auto-updater) |
| `/karel_sprites.gz` | `desktop/karel_sprites.gz` | 10,141 B | Shared compressed sprite pack (`54` anims, `194` frames) for macOS, Linux & source rebuilds |
| `/karel_mac.swift` | `desktop/karel_mac.swift` | 87,942 B | macOS native Cocoa/AppKit mirror of `karel_native.cs` (`v2.1.0` + `CryptoKit` auto-updater) |
| `/build_mac.sh` | `desktop/build_mac.sh` | 3,067 B | Compiles Universal `Karel.app` (`arm64` + `x86_64`) on macOS (or via `.github/workflows/release.yml`) |
| `/launch_karel.command` | `desktop/launch_karel.command` | 1,662 B | macOS launcher (`Karel.app` prebuilt / auto-build / `--python` fallback) |
| `/karel_linux_x86_64` | `desktop/karel_linux_x86_64` | 84,240 B | **Prebuilt Zero-Install** Linux x86_64 ELF binary (full Windows/macOS parity + SHA-256 auto-updater) |
| `/karel_linux.c` | `desktop/karel_linux.c` | 105,710 B | Linux C99 X11/XShape native host (pure C deflate, SHA-256, WAV, POSIX Serial, Mini-Hub, roam modes) |
| `/build_linux.sh` | `desktop/build_linux.sh` | 1,838 B | Compiles `karel_linux_<arch>` (84 KB) on Linux (WSL2 / Ubuntu / GitHub Action) |
| `/launch_karel.sh` | `desktop/launch_karel.sh` | 1,689 B | Linux launcher (`noexec`-safe `/tmp` staging + `gcc` fallback / `--python`) |
| `/karel.ico` | `desktop/karel.ico` | 15,086 B | Multi-size pixel Koala icon (`48/32/16`) for Windows Explorer drive branding & tray |
| `/AUTORUN.INF` | `desktop/AUTORUN.INF` | 40 B | Sets Explorer USB drive icon (`karel.ico`) & label (`KAREL`) automatically on Windows |
| `/.VolumeIcon.icns` | `desktop/.VolumeIcon.icns` | 1,058 B | Multi-size RGBA Apple `.icns` volume icon (`16/32/128`) for macOS Finder |
| `/launch_karel.bat` | `desktop/launch_karel.bat` | 2,721 B | Standard launcher: starts `karel_native.exe` immediately (`--python` launches archived `python_extended/`) |
| `/save.json` | generated by script | ~450–2,200 B | Initial Sticky profile, `stick_serial`, `skin`, `equipped`, `language`, cooldowns, `last_seen` |
| `/.karel_drive` | generated by script | 22 B | Portable drive marker alongside volume label `KAREL` |
| **Drive Code & Native Subtotal** | — | **~435 KB (~425 KiB)** | Fits ~6× over on 4 MB RP2350 Flash (incl. `Karel.app`: ~0.75 MB total) |
| `/lib/neopixel.mpy` + `/lib/adafruit_hid/` | Adafruit CircuitPython Bundle | ~30,000–45,000 B (external) | Compiled `.mpy` drivers matched to CircuitPython version |
| **Total Used on RP2350 Flash** | — | **~465–480 KB (< 0.48 MB)** | **~2.0+ MB free** on 4 MB Flash (`RP2350`) |

> *(Archived extended Python suite in [`python_extended/`](python_extended/): every `.py` module also remains strictly `< 60,000 B` — largest is `karel.py` at `59,378 B` — in case anyone copies the optional full Python bundle too.)*

---

## 3. One-Time Staging Setup (3 Minutes)

1. Download **CircuitPython 9.2+ or 10.x** (stable) `.uf2` for **RP2350** from `circuitpython.org`:
   - Recommended: **`waveshare_rp2350_zero`** (*Waveshare RP2350-Zero*, maps `board.NEOPIXEL` -> `GP16` and exposes `GP0..GP29`).
   - Alternative fallback: **`raspberry_pi_pico2`** (`Pico 2`, universal 4 MB RP2350A build; uses `GP16` or toggle `"GP23"`/`"GP22"` in `boot.py`/`code.py`).
2. Download the matching **Adafruit CircuitPython Library Bundle** `.zip` (**same major version** as your `.uf2`, e.g. `10.x-mpy` for CircuitPython 10.x), and extract only:
   - `lib/neopixel.mpy`
   - `lib/adafruit_hid/` (directory containing compiled `.mpy` files)
3. Build a clean `deploy_stage/` folder on your workstation:

```text
deploy_stage/
├── firmware.uf2            (CircuitPython 9.2+/10.x UF2: waveshare_rp2350_zero or pico2)
└── drive/
    ├── boot.py             <- firmware/boot.py
    ├── code.py             <- firmware/code.py (GP16 default; set "GP23"/"GP22" if batch differs)
    ├── AUTORUN.INF         <- desktop/AUTORUN.INF (Explorer USB icon + KAREL label)
    ├── karel.ico           <- desktop/karel.ico (48/32/16 pixel Koala icon)
    ├── .VolumeIcon.icns    <- desktop/.VolumeIcon.icns (macOS Finder Koala icon)
    ├── karel_native.exe    <- desktop/karel_native.exe (Standard Zero-Install Windows host)
    ├── karel_sprites.gz    <- desktop/karel_sprites.gz (Shared 54 animations / 194 frames)
    ├── karel_mac.swift     <- desktop/karel_mac.swift (macOS Swift/AppKit mirror)
    ├── build_mac.sh        <- desktop/build_mac.sh (One-command Universal Karel.app builder)
    ├── Karel.app/          <- built via build_mac.sh or GitHub Actions for instant Mac plug-and-play
    ├── launch_karel.bat    <- desktop/launch_karel.bat (Default Windows launcher)
    ├── launch_karel.command <- desktop/launch_karel.command (Default macOS launcher)
    ├── karel_linux_x86_64  <- desktop/karel_linux_x86_64 (Prebuilt Linux x86_64 ELF binary)
    ├── karel_linux.c       <- desktop/karel_linux.c (Linux C99 X11/XShape mirror)
    ├── build_linux.sh      <- desktop/build_linux.sh (Builds karel_linux_<arch> on Linux)
    ├── launch_karel.sh     <- desktop/launch_karel.sh (noexec-safe Linux launcher)
    ├── save.json           <- generated below
    ├── .karel_drive        <- generated below
    └── lib/
        ├── neopixel.mpy
        └── adafruit_hid/...
```

Generate the clean initial `save.json` and `.karel_drive` directly into `deploy_stage/drive`:

```bash
python desktop/generate_initial_save.py --out deploy_stage/drive --force
```

> **Test 1 board first!** Flash **1** `RP2350 SuperMini` board and unplug + replug USB-C: verify the `KAREL` drive mounts, Karel launches via `Win+R`, and the onboard LED breathes **Sticky-red** (if dark or wrong color order, change `GP16` -> `GP23`/`GP22` in `boot.py` and `code.py` for your batch, or verify mono LED fallback). Also verify your 3D-printed case fits from [`case/stl/`](case/stl/) before batch-printing!

---

## 4. Assembly-Line Workflow: 50 Boards in ~20 Minutes (~24s / board)

Use a powered USB hub with **4–8 ports** or a single fast USB-C pigtail cable. Keep a **Dev Mode jumper/clip connecting `GP0` to `GND`** on the outer pins during verification (or leave `flash_batch.ps1` unplug timing brisk) so `code.py` won't trigger `GUI+r` on your flashing laptop!

### Option A — Windows PowerShell Auto-Flasher Loop

Run from the folder containing `deploy_stage/`:

```powershell
# flash_batch.ps1 - Run in PowerShell on a Windows flashing station
$Stage = Resolve-Path ".\deploy_stage"
$Uf2 = Join-Path $Stage "firmware.uf2"
$Payload = Join-Path $Stage "drive"
$Count = 0

Write-Host "Karel 50-Board Batch Flasher klaar. Steek een RP2350 SuperMini in met BOOT ingedrukt..." -ForegroundColor Cyan

while ($true) {
    $vols = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.VolumeName -in @("RP2350", "RPI-RP2", "CIRCUITPY") }
    foreach ($v in $vols) {
        $drv = "$($v.DeviceID)\"
        if ($v.VolumeName -in @("RP2350", "RPI-RP2")) {
            Write-Host "[$($v.DeviceID)] $($v.VolumeName) gedetecteerd -> CircuitPython UF2 flashen..." -ForegroundColor Yellow
            Copy-Item $Uf2 -Destination $drv -Force
            Start-Sleep -Seconds 3
        }
        elseif (($v.VolumeName -eq "CIRCUITPY") -and (-not (Test-Path "$drv\.karel_drive"))) {
            $Count++
            Write-Host "[$Count/50] [$($v.DeviceID)] CIRCUITPY -> Karel bundle kopiëren..." -ForegroundColor Green
            Copy-Item "$Payload\*" -Destination $drv -Recurse -Force
            Start-Sleep -Milliseconds 700
            $ok = (Test-Path "$drv\boot.py") -and (Test-Path "$drv\code.py") -and
                  (Test-Path "$drv\karel_native.exe") -and (Test-Path "$drv\launch_karel.bat") -and
                  (Test-Path "$drv\karel.ico") -and (Test-Path "$drv\AUTORUN.INF") -and
                  (Test-Path "$drv\save.json") -and (Test-Path "$drv\.karel_drive") -and
                  (Test-Path "$drv\lib\neopixel.mpy") -and (Test-Path "$drv\lib\adafruit_hid")
            if ($ok) {
                try {
                    (New-Object -ComObject Shell.Application).Namespace(17).ParseName($v.DeviceID).InvokeVerb("Eject")
                    Start-Sleep -Milliseconds 400
                } catch {}
                [console]::Beep(880, 140)
                Write-Host "[$Count/50] KLAAR & uitgeworpen! Haal USB los en ga door naar volgende." -ForegroundColor Cyan
            } else {
                [console]::Beep(220, 400)
                Write-Warning "Verificatie mislukt op $drv!"
            }
            while (Test-Path $drv) { Start-Sleep -Milliseconds 300 }
        }
    }
    Start-Sleep -Milliseconds 400
}
```

> **Tip:** To prevent CircuitPython from triggering `GUI+r` while QC-testing a freshly flashed board, hold outer pin `GP0` to `GND` using a test clip: the LED turns **solid cyan** (`Dev Mode`) and HID typing stays off.

### Option B — macOS / Linux Auto-Flasher Loop

```bash
#!/usr/bin/env bash
STAGE="./deploy_stage"
UF2="$STAGE/firmware.uf2"
PAYLOAD="$STAGE/drive"
COUNT=0

# macOS: /Volumes | Linux: /media/$USER or /run/media/$USER
BASE="/Volumes"
[ -d "/media/$USER" ] && BASE="/media/$USER"
[ -d "/run/media/$USER" ] && BASE="/run/media/$USER"

chmod +x "$PAYLOAD/launch_karel.command" 2>/dev/null || true
echo "Plug RP2350 SuperMini boards in while holding BOOT..."

while true; do
    for BOOTVOL in "$BASE/RP2350" "$BASE/RPI-RP2"; do
        if [ -d "$BOOTVOL" ]; then
            echo "[$(basename "$BOOTVOL")] Flashing CircuitPython UF2..."
            cp "$UF2" "$BOOTVOL/"
            sleep 3
        fi
    done
    if [ -d "$BASE/CIRCUITPY" ] && [ ! -f "$BASE/CIRCUITPY/.karel_drive" ]; then
        COUNT=$((COUNT + 1))
        echo "[$COUNT/50] Copying Karel payload to CIRCUITPY..."
        cp -R "$PAYLOAD/." "$BASE/CIRCUITPY/"
        chmod +x "$BASE/CIRCUITPY/launch_karel.command" 2>/dev/null || true
        sync
        echo "[$COUNT/50] Done! Unplug board (next boot mounts as KAREL)."
        while [ -d "$BASE/CIRCUITPY" ]; do sleep 0.3; done
    fi
    sleep 0.4
done
```

### Timing Breakdown (50 Boards)
- Holding `BOOT` + plugging USB-C (~3s) -> UF2 copy + reboot to `CIRCUITPY` (~4s) -> File copy + `sync` (~6s) -> QC LED/unplug (~5s) = **~18–25 seconds per board**.
- With two cables or a hub (copying board `N` while holding `BOOT` on board `N+1`), **50 boards finish in ~15–22 minutes**.

---

## 5. Final Member QC & Troubleshooting

1. **First Member Boot:** Because `boot.py` renames the partition from `CIRCUITPY` to **`KAREL`** and sets `storage.remount("/", readonly=True)` (granting the host PC read/write permissions to `save.json`), a power cycle (unplug & replug) activates the final `KAREL` + Dual-CDC + HID USB descriptor.
2. **Verify on 1 Test PC (Windows + macOS):**
   - Plug in -> wait ~3s -> `launch_karel.bat` starts Karel climbing up behind the taskbar with warm band-limited synth audio -> SuperMini NeoPixel on **`GP16`** (or `"GP23"`/`"GP22"` batch toggle) breathes **Sticky-red (`#B21B21`)**.
   - **Cooldowns & Single-Outfit Regels:** Verzorgings-, commissie- en gacha-acties gebruiken eerlijke cooldowns (direct zichtbaar met afteller in de 7-tab Sticky Super-Hub; koffie blijft snel genoeg voor het *Cafeïne Overdosis* easter egg). Karel draagt maximaal **1 kledingstuk tegelijk**.
   - **Test USB Hardware Boop (1-button board):** While Karel runs, unplug and replug your RP2350 SuperMini via USB-C -> `launch_karel.bat` detects the already-running Karel on `127.0.0.1:42421`, climbs the taskbar with an Alumni cadeau, and spawns **zero** duplicate windows! (Optional: shorting external `RUN` -> `GND` with `pyserial` installed triggers `EVENT:RST_BOOP` directly without `Win+r`).
   - **Built-In USB Two-Way Sync (Zero `pip install`):** Built-in Win32 (`ctypes` + `winreg`) & POSIX (`termios`) USB CDC serial works **automatically without installing `pyserial`** (still uses `pyserial` if present) for real-time touch (`GP2` with 3.3V pull-up), action button (`GP1`/`GP3`), optional `GP24`/`GP15` toggle button, `RUN` Boop, and live `GP16` RGB LED mood mirroring. Even if serial is closed, Karel still reads/writes `save.json` directly on the `KAREL` USB drive (with per-stick serial fallback recovery)!
   - **macOS / Linux (optioneel, `python_extended/`):** Run `bash python_extended/launch_karel.command` (vereist Python 3 + Tk `>= 8.6`). Voor Mac-gebruikers kun je **Auto-Start HID -> Mac Veilig** aanzetten in de Hub (schrijft `/.karel_no_hid`).
3. **Editing Firmware Later (`Dev Mode` & `BOOT`):** Because `boot.py` gives the host OS write access by default (and sets CircuitPython itself read-only), members can simply edit `code.py` or `boot.py` directly on the `KAREL` drive from their computer; connecting outer pin `GP0` to `GND` at plug-in skips HID keystrokes so `GUI+r` never interrupts editing (holding **`BOOT` while plugging USB-C** enters `RP2350` bootloader mode for `.uf2` updates).
