# 🐨 Karel de Koala — Studievereniging Sticky Desktop Companion (RP2350)

**Karel de Koala** is een minimalistische, **Zero-Install** USB-bureaukoala voor leden van **Studievereniging Sticky** (Informatica, Universiteit Utrecht). Plug de **RP2350 SuperMini** in je laptop, en Karel klimt direct je taakbalk op — met je eigen voortgang (`save.json`) **direct op de USB-stick** én tweezijdige `GP16` RGB LED-synchronisatie via USB Serial.

> **Snel naar:** [Direct Gebruiken](#direct-gebruiken) · [Zero-Install Standaard](#zero-install-standaard) · [3D-Printbare Behuizing](#3d-printbare-behuizing) · [Uitgebreide Python Editie (`python_extended/`)](python_extended/README.md) · [50+ Bordjes Uitrollen](DEPLOYMENT_50_BOARDS.md)

---

## Direct Gebruiken

**Veilig & Zero-HID:** De RP2350-stick schakelt `usb_hid` volledig uit in `boot.py` — er wordt dus **nooit** een USB-toetsenbord gesimuleerd en er worden nooit automatisch commando's getypt (`Win+R` is volledig verwijderd). De stick is puur USB-opslag (`KAREL`) + een seriële verbinding voor de RGB LED.

Wanneer je het station **`KAREL`** opent, zie je slechts 4 overzichtelijke items (alle firmware- en systeembestanden zijn netjes verborgen):
- **`Karel (Windows).exe`** — dubbelklikken op Windows 10/11
- **`Karel (Mac).app`** — dubbelklikken op macOS (Universal: Apple Silicon & Intel)
- **`Karel (Linux).sh`** — starten op Linux (`bash "Karel (Linux).sh"`, kiest zelf de juiste architectuur)
- **`Lees mij.html`** — detecteert automatisch je besturingssysteem en toont direct het juiste startbestand + uitleg

### Automatisch openen bij inpluggen & automatisch sluiten bij loskoppelen
1. De eerste keer dat je Karel opent (als auto-start nog uit staat) vraagt Karel kort: *"Karel voortaan automatisch starten?"* (`Ja, automatisch` / `Nee, alleen nu` / `README`). Kies je **Ja**, dan luistert Karel stil in je systeemvak (Windows) of menubalk (macOS) en klimt hij voortaan automatisch je scherm op zodra je de USB-stick inplugt — helemaal zonder `Win+R`!
2. **Trek je de USB-stick eruit?** Dan zwaait Karel gedag en duikt hij direct weg van je scherm (en sluit volledig af, of wacht stil in je systeemvak/menubalk als je auto-start aan hebt staan).
3. *Optionele Python-editie:* [`python_extended/`](python_extended/README.md) blijft los beschikbaar (`--python`, vereist Python 3 + Tk `>= 8.6`).

---

## Zero-Install Standaard

De minimalistische desktop-apps ([`desktop/karel_native.cs`](desktop/karel_native.cs) → `karel_native.exe` voor Windows, [`desktop/karel_mac.swift`](desktop/karel_mac.swift) → `Karel.app` voor macOS en [`desktop/karel_linux.c`](desktop/karel_linux.c) → `karel_linux_x86_64` voor Linux) draaien zonder externe runtime direct vanaf de USB-stick, delen één sprite-archief (`desktop/karel_sprites.gz`) en ondersteunen automatische achtergrond-updates:

- **Alle `54` animaties (`194` frames):** o.a. *IDLE*, *CLIMB*, *DIVE_WAVE*, *EAT*, *COFFEE*, *WASH*, *PET*, *BACKFLIP*, *JETPACK*, *LAPTOP_CODE*, *GUITAR*, *DRUM*, *SNEEZE*, *DANCE* en een zachte **`UMBRELLA`-landing** zodra een actief venster onder Karel wegschuift (*Op Actief Venster*-modus).
- **Sticky Style & Looks:** `6` koalavachten (`classic`, `sticky`, `mint`, `midnight`, `gold`, `crimson`) en `8` op pixel-niveau getekende accessoires (`scarf`, `stickycap`, `hoodie`, `headphones`, `shades`, `crown`, `wizard`, `partyhat`; strikt 1 item tegelijk).
- **Strakke Sticky Mini-Hub & Zwerfgedrag:** Level & XP-balk (`Lv.`), vitals (*Voer / Koffie / Aai / Was / Powernap / Focus 25m*), Stijl-kiezer, **Auto-Stil bij Fullscreen/Meetings**, **Geluid Aan/Uit** (RAM WAV-synth), **NL / EN** wissel, 1-klik **Automatisch openen bij USB** schakelaar, plus rechtermuis-menu voor alle `18` trucjes, `4` zwerf-modi (*Vrij*, *Op Venster*, *Volg Muis*, *Geparkeerd*) en schaal (`2×–5×`).
- **Automatische Updates via GitHub Releases:** Controleert ~3,5s na opstarten stil op een nieuwere versie via `releases/latest/download/version.json`, verifieert de **SHA-256** checksum en werkt zowel de desktop-app (`karel_native.exe` / `Karel.app` / `karel_linux_x86_64` + `karel_sprites.gz`) als de RP2350-firmware (`code.py` op de stick) atomisch bij met automatische herstart (`--no-update` schakelt dit uit).
- **Systeemvak, Sneltoets & Bescherming:** Eigen Tray-icoon / X11-menu, automatisch opslaan bij afsluiten, per-stick `stick_serial`-isolatie, `3×` snelle koffie *Cafeïne Overdosis*, `7×` neusklik *Hatsjoe!*, en *Konami-code* (`↑↑↓↓←→←→BA`) disco!

---

## 3D-Printbare Behuizing

In [`case/stl/`](case/stl/) staan kant-en-klare, waterdichte STL-bestanden op maat voor een **kale RP2350 SuperMini** (`18,0 × 23,3–23,5 mm` zonder pinheaders):

| Bestand | Beschrijving |
|---|---|
| [`case/stl/karel_rp2350_complete_plate.stl`](case/stl/karel_rp2350_complete_plate.stl) | Bodem en deksel samen plat naast elkaar — direct in je slicer laden |
| [`case/stl/karel_rp2350_bottom.stl`](case/stl/karel_rp2350_bottom.stl) | Onderbak met 6 klemribbels, `12,2 × 5,3 mm` USB-C uitsparing & `Ø 4,6 mm` sleutelhanger-oog |
| [`case/stl/karel_rp2350_top.stl`](case/stl/karel_rp2350_top.stl) | Klikdeksel met gecentreerd `-0,6 mm` verzonken **Sticky Kop-logo**, gladde interne lichtdiffuser boven de `GP16` LED en afgedekte `BOOT`-knop |

- **Printadvies:** `0,4 mm` nozzle, `0,16 mm` laagdikte, **geen supports nodig**, bij voorkeur wit/licht PLA (of PETG) zodat de interne `0,42 mm` diffuser het RGB-licht mooi doorlaat.
- **Zelf regenereren:** `python case/generate_karel_case.py` (`--open-led`, `--open-boot`, `--out-dir`).

---

## Hardware & Pinout

De firmware ([`firmware/boot.py`](firmware/boot.py) & [`firmware/code.py`](firmware/code.py)) draait onder CircuitPython (`9.2+` / `10.x`) op de **RP2350 SuperMini** (`4 MB` Flash, totale Zero-Install payload incl. drivers slechts **`< 180 KB`**):

| Functie | Pin | Werking |
|---|---|---|
| **WS2812 RGB LED (NeoPixel)** | `GP16` (of `GP23`/`GP22`) | Spiegelt Karels stemming live over USB Serial (Sticky-rood, oranje, cyaan = Dev Mode, blauw = slaap, rainbow = boop/disco) |
| **`BOOT`-knop** | Onboard `BOOT` | Houd ingedrukt bij het inpluggen om als `RP2350` UF2-drive op te starten (voor firmware-updates) |
| **Dev / Safe Mode** | `GP0 → GND` (of `GP24 → GND`) | Houd verbonden tijdens inpluggen voor Dev-modus (cyaan LED + autoreload aan) |
| **Optionele hardware** | `GP1` / `GP2` / `GP3` / `GP15` / `GP24` | Ondersteuning voor externe actieknop, capacitieve aai-pad en Show/Hide toggle-knop |

---

## Mappenstructuur

```text
karel-de-koala/
├── README.md                        # Overzicht, snelstart & documentatie
├── DEPLOYMENT_50_BOARDS.md          # Mass-flashing handleiding (50× RP2350 in <15 min)
├── .gitattributes / .gitignore
├── firmware/
│   ├── boot.py                      # USB-label KAREL, Host-RW / CircuitPython-RO, Dual CDC + HID
│   └── code.py                      # RP2350 firmware: Base64 HID, Serial-protocol, LED & knoppen
├── desktop/                         # Standaard Zero-Install USB-bundel (Windows + macOS + Linux)
│   ├── karel_native.exe             # Zero-Install Windows-host (.NET 4.x, 54 animaties ingebakken)
│   ├── karel_native.cs              # Windows C# broncode
│   ├── karel_mac.swift              # macOS native Cocoa/AppKit broncode (Zelfde 54 animaties & Hub)
│   ├── build_mac.sh                 # Bouwt Universal Karel.app op macOS (arm64 + x86_64)
│   ├── karel_linux.c                # Linux native C99 X11/XShape broncode (pure C gzip + WAV + Serial)
│   ├── build_linux.sh               # Bouwt karel_linux_<arch> (~50 KB) op Linux
│   ├── launch_karel.bat             # Windows standaard launcher (karel_native.exe; optioneel --python)
│   ├── launch_karel.command         # macOS standaard launcher (Karel.app; optioneel --python)
│   ├── launch_karel.sh              # Linux standaard launcher (noexec-veilig; optioneel --python)
│   ├── karel_sprites.gz             # Gedeeld compressed sprite-pakket (54 animaties, 194 frames)
│   ├── karel.ico / AUTORUN.INF      # Windows Verkenner USB-icoon & KAREL-label
│   ├── .VolumeIcon.icns             # macOS Finder volume-icoon
│   ├── build_native.py              # Hercompileert karel_native.exe + exporteert karel_sprites.gz
│   ├── prepare_test_usb.py          # Richt gewone USB-stick in als KAREL test-stick (zonder chip)
│   ├── setup_test_usb.bat           # 1-klik launcher voor prepare_test_usb.py
│   └── generate_initial_save.py     # Zelfstandige generator voor save.json, .karel_drive & iconen
├── python_extended/                 # Losse uitgebreide Python-versie (10 minigames, 7-tab Hub, macOS)
│   ├── karel.py (+ 11 modules)      # Alle modules < 60.000 B
│   ├── launch_karel.command         # macOS / Linux launcher
│   ├── launch_python.bat            # Windows Python-launcher
│   └── README.md
└── case/
    ├── generate_karel_case.py       # Parametrische STL-generator met Sticky Kop-logo
    ├── assets/
    └── stl/                         # Kant-en-klare 3D-printbare .stl bestanden
```

---

## Zelf Bouwen & Testen

- **Zero-Install `.exe` bouwen** (Windows `.NET 4.x` `csc.exe`, sluit evt. openstaande Karel eerst):
  ```bash
  python desktop/build_native.py
  ```
- **Schone USB-bundel aanmaken** (naar bijv. `deploy_stage/drive/`):
  ```bash
  python desktop/generate_initial_save.py --out deploy_stage/drive --force
  ```
