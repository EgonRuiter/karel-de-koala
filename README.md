# 🐨 Karel de Koala — Studievereniging Sticky Desktop Companion (RP2350)

**Karel de Koala** is een minimalistische, **Zero-Install** USB-bureaukoala voor leden van **Studievereniging Sticky** (Informatica, Universiteit Utrecht). Plug de **RP2350 SuperMini** in je laptop, en Karel klimt direct je taakbalk op — met je eigen voortgang (`save.json`) **direct op de USB-stick** én tweezijdige `GP16` RGB LED-synchronisatie via USB Serial.

> **Snel naar:** [Direct Gebruiken](#direct-gebruiken) · [Zero-Install Standaard](#zero-install-standaard) · [3D-Printbare Behuizing](#3d-printbare-behuizing) · [Uitgebreide Python Editie (`python_extended/`)](python_extended/README.md) · [50+ Bordjes Uitrollen](DEPLOYMENT_50_BOARDS.md)

---

## Direct Gebruiken

### Windows 10 / 11 (Standaard Zero-Install Plug-and-Play)
1. **Steek de Karel USB-C stick in je pc.**
2. Het station verschijnt als **`KAREL`** (inclusief eigen koalasticker-icoon via `karel.ico` en `AUTORUN.INF`).
3. De RP2350 checkt eerst via USB Serial (`KAREL_PING`) of Karel al draait: zo ja, dan geeft Karel een *Hardware Boop* zonder popups. Daarna detecteert de stick automatisch Windows vs. macOS (`NumLock`-LED check, zodat macOS nooit per ongeluk `Cmd+R` / Windows-commando's ontvangt) en start op Windows razendsnel (`100` tekens via `cmd /q /c` + snelle 1-frame HID, zonder Defender-false-positives) **`desktop/karel_native.exe --ask`**: deze vraagt eerst via een Sticky pop-up *"Wil je een koala op je scherm hebben?"* met knoppen **Ja**, **README bekijken** en **Nee** (gevolgd door *"Weet je het zeker?"*). Via het rechtermuis-menu (**Stil mee-opstarten — 0 popups**) op Windows of **Automatisch mee-opstarten (Mac)** in de menubalk op macOS kan Karel daarna volledig stil op de achtergrond meedraaien.
4. **Handmatig starten / optionele Python-versie:**
   - Dubbelklik `desktop/launch_karel.bat` (standaard Zero-Install).
   - Geef `--python` mee (`launch_karel.bat --python`) om de uitgebreide Python-versie uit [`python_extended/`](python_extended/) te starten indien gewenst.
   - Repluggen terwijl Karel al draait geeft een *Hardware Boop* (zonder dubbel venster).

### macOS (Zero-Install Native Swift / AppKit)
De native macOS-tegenhanger staat nu direct naast de Windows-versie in **`desktop/`**:
- Dubbelklik direct op de vooraf gebouwde **`Karel.app`** op de stick of **`desktop/launch_karel.command`** (haalt quarantaine-vlag weg, schaduw-kopieert veilig uit `/Volumes/`, toont *"Wil je een koala op je scherm hebben?"* en biedt via het menu **Automatisch mee-opstarten (Mac)** via LaunchAgent; `desktop/build_mac.sh` compileert zo nodig lokaal via `swiftc`).
- **Universal App bouwen voor distributie op alle 50 sticks** (automatisch via [`.github/workflows/release.yml`](.github/workflows/release.yml), of eenmalig op een Mac met Command Line Tools via `./desktop/build_mac.sh`): maakt `desktop/Karel.app` (Apple Silicon + Intel), zodat studenten daarna **nul dependencies** nodig hebben.
- *Optionele Python-editie:* [`python_extended/`](python_extended/README.md) blijft los beschikbaar (`launch_karel.command --python`, vereist Python 3 + Tk `>= 8.6`).

### Linux (Zero-Install C99 X11 / XWayland)
De native Linux-versie (`desktop/karel_linux_x86_64`, `~86 KB` C99-binary tegen systeem-`libX11` + `XShape`, feature-pariteit met Windows & macOS) draait zonder extra dependencies:
- Start **`bash desktop/launch_karel.sh`** vanaf de USB-stick (omzeilt automatisch FAT32 `noexec`-mounts via `/tmp`, start voorgebouwde `karel_linux_x86_64` of compileert lokaal met `gcc` als X11 aanwezig is; `--python` start `python_extended/`).
- **Vooraf compileren voor distributie op alle 50 sticks:** via `./desktop/build_linux.sh` op Linux of automatisch in [`.github/workflows/release.yml`](.github/workflows/release.yml).

---

## Zero-Install Standaard

De minimalistische desktop-apps ([`desktop/karel_native.cs`](desktop/karel_native.cs) → `karel_native.exe` voor Windows, [`desktop/karel_mac.swift`](desktop/karel_mac.swift) → `Karel.app` voor macOS en [`desktop/karel_linux.c`](desktop/karel_linux.c) → `karel_linux_x86_64` voor Linux) draaien zonder externe runtime direct vanaf de USB-stick, delen één sprite-archief (`desktop/karel_sprites.gz`) en ondersteunen automatische achtergrond-updates:

- **Alle `54` animaties (`194` frames):** o.a. *IDLE*, *CLIMB*, *DIVE_WAVE*, *EAT*, *COFFEE*, *WASH*, *PET*, *BACKFLIP*, *JETPACK*, *LAPTOP_CODE*, *GUITAR*, *DRUM*, *SNEEZE*, *DANCE* en een zachte **`UMBRELLA`-landing** zodra een actief venster onder Karel wegschuift (*Op Actief Venster*-modus).
- **Sticky Style & Looks:** `6` koalavachten (`classic`, `sticky`, `mint`, `midnight`, `gold`, `crimson`) en `8` op pixel-niveau getekende accessoires (`scarf`, `stickycap`, `hoodie`, `headphones`, `shades`, `crown`, `wizard`, `partyhat`; strikt 1 item tegelijk).
- **Strakke Sticky Mini-Hub & Zwerfgedrag:** Level & XP-balk (`Lv.`), vitals (*Voer / Koffie / Aai / Was / Powernap / Focus 25m*), Stijl-kiezer, **Auto-Stil bij Fullscreen/Meetings**, **Geluid Aan/Uit** (RAM WAV-synth), **NL / EN** wissel, 1-klik **USB HID Mac-Veilig** schakelaar zodra de stick vastzit, plus rechtermuis-menu voor alle `18` trucjes, `4` zwerf-modi (*Vrij*, *Op Venster*, *Volg Muis*, *Geparkeerd*) en schaal (`2×–5×`).
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
| **Dev / Safe Mode** | `GP0 → GND` (of `GP24 → GND`) | Houd verbonden tijdens inpluggen om `Win+R` HID over te slaan en code veilig te bewerken |
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
