#!/usr/bin/env python3
"""USB persistence, offline stat decay, screen work-area & RP2350 serial bridge."""

import ctypes
import ctypes.wintypes as _wt
import datetime
import errno
import glob
import json
import os
import socket
import subprocess
import sys
import threading
import time

IS_MAC = sys.platform == "darwin"

try:
    import winreg
except ImportError:
    winreg = None

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

from karel_assets import SKINS, WARDROBE_ITEMS
from karel_data import COMPANIONS, generate_daily_quests, level_from_xp


_MAC_SCR_CACHE = (0.0, None)
_MAC_UUID_CACHE = {}


def _mac_screens_snapshot():
    """Return cached list of ((fx0, fy0, fx1, fy1), (wx0, wy0, wx1, wy1)) on macOS."""
    global _MAC_SCR_CACHE
    if not IS_MAC:
        return None
    now = time.monotonic()
    ts, cached = _MAC_SCR_CACHE
    if cached is not None and (now - ts) < 4.0:
        return cached
    js = (
        'ObjC.import("AppKit");'
        'var scs=$.NSScreen.screens,n=scs.count,out=[];'
        'var mh=n>0?scs.objectAtIndex(0).frame.size.height:0;'
        'for(var i=0;i<n;i++){var s=scs.objectAtIndex(i),f=s.frame,v=s.visibleFrame;'
        'out.push([[f.origin.x,mh-(f.origin.y+f.size.height),f.origin.x+f.size.width,mh-f.origin.y],'
        '[v.origin.x,mh-(v.origin.y+v.size.height),v.origin.x+v.size.width,mh-v.origin.y]]);}'
        'JSON.stringify(out);'
    )
    try:
        res = subprocess.run(["osascript", "-l", "JavaScript", "-e", js], capture_output=True, text=True, timeout=1.2)
        if res.returncode == 0 and res.stdout.strip():
            raw = json.loads(res.stdout.strip())
            parsed = [
                (tuple(int(round(v)) for v in frm), tuple(int(round(v)) for v in wrk))
                for frm, wrk in raw
            ]
            if parsed:
                _MAC_SCR_CACHE = (now, parsed)
                return parsed
    except Exception:
        pass
    _MAC_SCR_CACHE = (now, [])
    return []


def get_mac_virtual_bounds(sw, sh):
    """Return multi-monitor virtual bounding box across all macOS displays."""
    scs = _mac_screens_snapshot()
    if scs:
        xs0 = min(f[0] for f, _ in scs)
        ys0 = min(f[1] for f, _ in scs)
        xs1 = max(f[2] for f, _ in scs)
        ys1 = max(f[3] for f, _ in scs)
        if xs1 > xs0 and ys1 > ys0:
            return xs0, ys0, xs1, ys1
    return 0, 0, sw, sh


def get_work_area(sw, sh, pt=None):
    """Return usable screen (left, top, right, bottom) excluding OS taskbar/Dock & menubar."""
    if IS_MAC:
        scs = _mac_screens_snapshot()
        if scs:
            if pt is not None:
                px, py = pt
                for frm, wrk in scs:
                    if frm[0] <= px <= frm[2] and frm[1] <= py <= frm[3]:
                        return wrk
            return scs[0][1]
        return 0, 28, sw, max(240, sh - 72)
    if os.name == "nt":
        try:
            u32 = ctypes.windll.user32
            if pt is not None:
                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", _wt.DWORD),
                        ("rcMonitor", _wt.RECT),
                        ("rcWork", _wt.RECT),
                        ("dwFlags", _wt.DWORD),
                    ]
                u32.MonitorFromPoint.argtypes = [_wt.POINT, _wt.DWORD]
                u32.MonitorFromPoint.restype = _wt.HMONITOR
                u32.GetMonitorInfoW.argtypes = [_wt.HMONITOR, ctypes.POINTER(MONITORINFO)]
                u32.GetMonitorInfoW.restype = _wt.BOOL
                hmon = u32.MonitorFromPoint(_wt.POINT(int(pt[0]), int(pt[1])), 2)
                if hmon:
                    mi = MONITORINFO()
                    mi.cbSize = ctypes.sizeof(MONITORINFO)
                    if u32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                        w = mi.rcWork
                        return int(w.left), int(w.top), int(w.right), int(w.bottom)
            rect = _wt.RECT()
            u32.SystemParametersInfoW.argtypes = [_wt.UINT, _wt.UINT, ctypes.c_void_p, _wt.UINT]
            u32.SystemParametersInfoW.restype = _wt.BOOL
            if u32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)
        except Exception:
            pass
    return 0, 0, sw, max(240, sh - 48)


def default_save():
    """Return initial extended Sticky RPG/pet save dictionary."""
    today = datetime.date.today().isoformat()
    return {
        "name": "Karel",
        "hunger": 80,
        "happiness": 85,
        "energy": 85,
        "hygiene": 90,
        "caffeine": 25,
        "xp": 0,
        "level": 1,
        "coins": 60,
        "streak_days": 1,
        "total_pets": 0,
        "total_coffees": 0,
        "total_feeds": 0,
        "total_washes": 0,
        "total_throws": 0,
        "total_fish": 0,
        "total_crafted": 0,
        "total_trivia": 0,
        "committee_runs": 0,
        "snacks": 0,
        "high_score_minigame": 0,
        "high_scores": {
            "catch": 0, "flappy": 0, "smash": 0, "memory": 0,
            "snake": 0, "merge": 0, "rhythm": 0, "rpg": 0,
            "gans": 0, "koala": 0,
        },
        "unlocked_achievements": ["Sticky Lid"],
        "unlocked_accessories": [],
        "skin": "classic",
        "unlocked_skins": ["classic"],
        "equipped": ["scarf"],
        "inventory": {"tosti": 1},
        "ingredients": {"brood": 2, "kaas": 1, "blad": 1},
        "crafted_recipes": [],
        "upgrades": [],
        "dex": {},
        "committees_helped": [],
        "cooldowns": {},
        "companion": "none",
        "unlocked_companions": ["none"],
        "music_track": "off",
        "sfx_vol": 0.75,
        "bgm_vol": 0.65,
        "voice_on": True,
        "quest_date": today,
        "quests": generate_daily_quests(today),
        "roam_mode": "free",
        "karel_scale": 3,
        "prestige": 0,
        "focus_sessions": 0,
        "auto_quiet_fullscreen": True,
        "language": "nl",
        "stick_serial": "",
        "last_seen": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def get_drive_serial(root):
    """Return stable volume serial/UUID string for root drive (or empty string)."""
    if not root or not os.path.isdir(root):
        return ""
    if os.name == "nt":
        try:
            k32 = ctypes.windll.kernel32
            ser = _wt.DWORD(0)
            k32.GetVolumeInformationW.argtypes = [
                _wt.LPCWSTR, _wt.LPWSTR, _wt.DWORD, ctypes.POINTER(_wt.DWORD),
                ctypes.POINTER(_wt.DWORD), ctypes.POINTER(_wt.DWORD), _wt.LPWSTR, _wt.DWORD,
            ]
            k32.GetVolumeInformationW.restype = _wt.BOOL
            if k32.GetVolumeInformationW(root, None, 0, ctypes.byref(ser), None, None, None, 0) and ser.value:
                return f"{ser.value:08X}"
        except Exception:
            pass
    elif IS_MAC:
        if root in _MAC_UUID_CACHE:
            return _MAC_UUID_CACHE[root]
        try:
            res = subprocess.run(["diskutil", "info", root], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "UUID:" in line:
                        uid = line.split("UUID:", 1)[1].strip()
                        if uid:
                            _MAC_UUID_CACHE[root] = uid
                            return uid
        except Exception:
            pass
    try:
        st = os.stat(root)
        return f"dev-{int(st.st_dev)}"
    except Exception:
        return ""


def _has_marker_or_label(root):
    if os.path.exists(os.path.join(root, ".karel_drive")):
        return True
    if os.name == "nt":
        try:
            buf = ctypes.create_unicode_buffer(64)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(root, buf, 64, None, None, None, None, 0)
            if ok and buf.value.strip().upper() == "KAREL":
                return True
        except Exception:
            pass
    return False


def find_karel_drive():
    """Locate the KAREL USB drive safely without triggering empty card-reader popups."""
    if os.name == "nt":
        try:
            mask = ctypes.windll.kernel32.GetLogicalDrives()
        except Exception:
            mask = 0
        for i in range(26):
            if mask and not (mask & (1 << i)):
                continue
            root = f"{chr(65 + i)}:\\"
            if os.path.isdir(root) and _has_marker_or_label(root):
                return root
    else:
        candidates = []
        for base in ("/Volumes", "/media", "/run/media", f"/media/{os.getenv('USER', '')}", f"/run/media/{os.getenv('USER', '')}"):
            if os.path.isdir(base):
                try:
                    for e in sorted(os.listdir(base)):
                        candidates.append(os.path.join(base, e))
                except OSError:
                    pass
        for path in candidates:
            try:
                bn = os.path.basename(path).upper()
                if os.path.isdir(path) and (
                    bn == "KAREL" or bn.startswith("KAREL ") or os.path.exists(os.path.join(path, ".karel_drive"))
                ):
                    return path
            except OSError:
                pass
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(here, ".karel_drive")):
        return here
    return None


class SaveManager:
    """Persist Karel state directly to KAREL USB stick with safe local fallback."""

    _dirty = False
    _last_save_ts = 0.0

    def __init__(self):
        self.drive = find_karel_drive()
        if IS_MAC:
            self.fallback = os.path.expanduser("~/Library/Application Support/KarelDeKoala/save.json")
        else:
            self.fallback = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "KarelDeKoala_save.json")
        self.connected = self.drive is not None
        self._dirty = False
        self._last_save_ts = 0.0
        self._io_lock = threading.Lock()

    def has_no_hid_flag(self):
        """Return True when /.karel_no_hid disables Win+R HID auto-launch on the stick."""
        return bool(self.drive and os.path.exists(os.path.join(self.drive, ".karel_no_hid")))

    def toggle_no_hid_flag(self):
        """Toggle /.karel_no_hid on mounted KAREL drive; return new bool state or None."""
        if not self.drive or not os.path.isdir(self.drive):
            return None
        p = os.path.join(self.drive, ".karel_no_hid")
        try:
            if os.path.exists(p):
                os.remove(p)
                return False
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write("MAC_SAFE_NO_WIN_R\n")
            return True
        except Exception:
            return None

    def _path(self):
        if self.drive and os.path.isdir(self.drive):
            return os.path.join(self.drive, "save.json")
        return self.fallback

    def poll_usb(self):
        now_drv = find_karel_drive()
        was = self.connected
        self.connected = now_drv is not None
        if now_drv:
            self.drive = now_drv
        if was and not self.connected:
            return "off"
        if not was and self.connected:
            return "on"
        return None

    @staticmethod
    def _read_json(path):
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw if isinstance(raw, dict) else None
        except Exception:
            return None

    @staticmethod
    def _save_rank(raw):
        try:
            ts = datetime.datetime.fromisoformat(str(raw.get("last_seen", ""))).timestamp()
        except Exception:
            ts = 0.0
        return (ts, int(raw.get("xp", 0) or 0), int(raw.get("total_pets", 0) or 0))

    def load(self):
        data = default_save()
        usb_path = os.path.join(self.drive, "save.json") if self.drive else None
        cur_serial = get_drive_serial(self.drive) if self.drive else ""
        usb_raw = self._read_json(usb_path)
        fb_raw = self._read_json(self.fallback)
        if fb_raw is None and IS_MAC:
            fb_raw = self._read_json(os.path.expanduser("~/KarelDeKoala_save.json"))

        loaded = None
        recovered_fb = False
        if usb_raw is not None and fb_raw is not None:
            u_ser = str(usb_raw.get("stick_serial") or "") or cur_serial
            f_ser = str(fb_raw.get("stick_serial") or "")
            if f_ser and u_ser and f_ser == u_ser and self._save_rank(fb_raw) > self._save_rank(usb_raw):
                loaded = fb_raw
                recovered_fb = True
            else:
                loaded = usb_raw
        elif usb_raw is not None:
            loaded = usb_raw
        elif fb_raw is not None:
            # Only adopt fallback when running unplugged (no different USB stick present)
            if not self.drive:
                loaded = fb_raw
            else:
                f_ser = str(fb_raw.get("stick_serial") or "")
                if f_ser and cur_serial and f_ser == cur_serial:
                    loaded = fb_raw
                    recovered_fb = True

        if loaded:
            hs = dict(data["high_scores"])
            hs.update(loaded.get("high_scores") or {})
            if loaded.get("high_score_minigame", 0) > hs.get("catch", 0):
                hs["catch"] = loaded["high_score_minigame"]
            data.update(loaded)
            data["high_scores"] = hs
            for k, typ in (
                ("inventory", dict), ("ingredients", dict), ("dex", dict), ("cooldowns", dict),
                ("equipped", list), ("unlocked_skins", list), ("unlocked_companions", list),
                ("crafted_recipes", list), ("committees_helped", list),
            ):
                if not isinstance(data.get(k), typ):
                    data[k] = default_save()[k]
            data["equipped"] = [w for w in data["equipped"] if w in WARDROBE_ITEMS][:1]
            if not data["unlocked_skins"]:
                data["unlocked_skins"] = ["classic"]
            if data.get("skin") not in SKINS:
                data["skin"] = "classic"
            if data.get("companion") not in COMPANIONS:
                data["companion"] = "none"

        now = datetime.datetime.now()
        today = now.date().isoformat()
        if data.get("quest_date") != today or not data.get("quests"):
            data["quest_date"] = today
            data["quests"] = generate_daily_quests(today)

        lang = "en" if data.get("language") == "en" else "nl"
        data["language"] = lang
        from karel_i18n import trf
        greeting = trf(lang, "welcome_back")
        try:
            prev = datetime.datetime.fromisoformat(data["last_seen"])
            hrs = max(0.0, (now - prev).total_seconds() / 3600.0)
            up = set(data.get("upgrades", []))
            from karel_wardrobe import get_outfit_perk
            perk = get_outfit_perk(data.get("equipped", []))
            pkey, pval = (perk[1], perk[2]) if perk else ("", 0.0)
            energy_k = max(0.55, 1.0 - pval) if pkey == "energy_save" else 1.0
            hunger_k = max(0.55, 1.0 - pval) if pkey == "hunger_save" else 1.0
            h_rate = (1.5 if "golden_bowl" in up else 2.5) * hunger_k
            m_rate = (1.3 if "coffee_thermos" in up else 2.0) * energy_k
            s_rate = 0.55 if "soap_dispenser" in up else 1.1
            if hrs > 0.05:
                data["hunger"] = int(max(5, data["hunger"] - hrs * h_rate))
                data["happiness"] = int(max(10, data["happiness"] - hrs * m_rate))
                data["hygiene"] = int(max(15, data["hygiene"] - hrs * s_rate))
                data["caffeine"] = int(max(0, data["caffeine"] - hrs * 8.0))
                if hrs >= 1.0:
                    data["energy"] = int(min(100, data["energy"] + hrs * 5.0))
            for vk, vd in (("sfx_vol", 0.75), ("bgm_vol", 0.65)):
                try:
                    data[vk] = max(0.0, min(1.0, float(data.get(vk, vd))))
                except Exception:
                    data[vk] = vd
            if data.get("roam_mode") not in ("free", "cursor", "window", "park"):
                data["roam_mode"] = "free"
            try:
                ks_val = int(data.get("karel_scale", 3))
            except Exception:
                ks_val = 3
            data["karel_scale"] = max(2, min(5, ks_val))
            data["prestige"] = max(0, int(data.get("prestige", 0) or 0))
            data["focus_sessions"] = max(0, int(data.get("focus_sessions", 0) or 0))
            data["auto_quiet_fullscreen"] = bool(data.get("auto_quiet_fullscreen", True))
            day_diff = (now.date() - prev.date()).days
            if day_diff == 1:
                data["streak_days"] = int(data.get("streak_days", 1)) + 1
            elif day_diff > 1:
                data["streak_days"] = 1

            if hrs < 0.25:
                greeting = trf(lang, "welcome_fast")
            elif hrs < 6:
                greeting = trf(lang, "welcome_short")
            elif hrs < 48:
                greeting = trf(lang, "welcome_days", days=data["streak_days"])
            else:
                greeting = trf(lang, "welcome_long", days=int(hrs // 24))
        except Exception:
            pass

        data["level"] = level_from_xp(int(data.get("xp", 0)))
        data["last_seen"] = now.isoformat(timespec="seconds")
        if cur_serial and (not data.get("stick_serial") or not cur_serial.startswith("dev-")):
            data["stick_serial"] = cur_serial
        if recovered_fb:
            self._dirty = True
            self.save(data, force=True)
        return data, greeting

    def mark_dirty(self):
        """Mark save data as having unpersisted changes."""
        self._dirty = True

    def flush(self, data, force=False, min_interval=2.5):
        """Persist dirty state only after min_interval seconds (unless force=True)."""
        if not force and not getattr(self, "_dirty", False):
            return False
        now = time.monotonic()
        last = getattr(self, "_last_save_ts", 0.0)
        if not force and last > 0.0 and (now - last) < min_interval:
            return False
        self.save(data, force=True)
        self._last_save_ts = now
        return True

    @staticmethod
    def _atomic_write(path, payload):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(payload)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, path)

    def save(self, data, force=True):
        """Atomically persist save data to primary path and mirror local backup."""
        with self._io_lock:
            if self.drive and not data.get("stick_serial"):
                ser = get_drive_serial(self.drive)
                if ser:
                    data["stick_serial"] = ser
            data["last_seen"] = datetime.datetime.now().isoformat(timespec="seconds")
            payload = json.dumps(dict(data), indent=2, ensure_ascii=False) + "\n"
            primary = self._path()
            try:
                self._atomic_write(primary, payload)
            except Exception:
                primary = ""
            if primary != self.fallback:
                try:
                    self._atomic_write(self.fallback, payload)
                except Exception:
                    pass
            self._dirty = False
            self._last_save_ts = time.monotonic()


_INVALID_HANDLE = ctypes.c_void_p(-1).value


class _DCB(ctypes.Structure):
    _fields_ = [
        ("DCBlength", _wt.DWORD), ("BaudRate", _wt.DWORD), ("fFlags", _wt.DWORD),
        ("wReserved", _wt.WORD), ("XonLim", _wt.WORD), ("XoffLim", _wt.WORD),
        ("ByteSize", _wt.BYTE), ("Parity", _wt.BYTE), ("StopBits", _wt.BYTE),
        ("XonChar", ctypes.c_char), ("XoffChar", ctypes.c_char),
        ("ErrorChar", ctypes.c_char), ("EofChar", ctypes.c_char), ("EvtChar", ctypes.c_char),
        ("wReserved1", _wt.WORD),
    ]


class _COMMTIMEOUTS(ctypes.Structure):
    _fields_ = [
        ("ReadIntervalTimeout", _wt.DWORD), ("ReadTotalTimeoutMultiplier", _wt.DWORD),
        ("ReadTotalTimeoutConstant", _wt.DWORD), ("WriteTotalTimeoutMultiplier", _wt.DWORD),
        ("WriteTotalTimeoutConstant", _wt.DWORD),
    ]


def _win32_k32():
    k32 = ctypes.windll.kernel32
    if not getattr(k32, "_karel_sig", False):
        k32.CreateFileW.argtypes = [_wt.LPCWSTR, _wt.DWORD, _wt.DWORD, ctypes.c_void_p, _wt.DWORD, _wt.DWORD, _wt.HANDLE]
        k32.CreateFileW.restype = _wt.HANDLE
        k32.CloseHandle.argtypes = [_wt.HANDLE]
        k32.CloseHandle.restype = _wt.BOOL
        k32.GetCommState.argtypes = [_wt.HANDLE, ctypes.POINTER(_DCB)]
        k32.GetCommState.restype = _wt.BOOL
        k32.SetCommState.argtypes = [_wt.HANDLE, ctypes.POINTER(_DCB)]
        k32.SetCommState.restype = _wt.BOOL
        k32.SetCommTimeouts.argtypes = [_wt.HANDLE, ctypes.POINTER(_COMMTIMEOUTS)]
        k32.SetCommTimeouts.restype = _wt.BOOL
        k32.EscapeCommFunction.argtypes = [_wt.HANDLE, _wt.DWORD]
        k32.EscapeCommFunction.restype = _wt.BOOL
        k32.PurgeComm.argtypes = [_wt.HANDLE, _wt.DWORD]
        k32.PurgeComm.restype = _wt.BOOL
        k32.WriteFile.argtypes = [_wt.HANDLE, ctypes.c_void_p, _wt.DWORD, ctypes.POINTER(_wt.DWORD), ctypes.c_void_p]
        k32.WriteFile.restype = _wt.BOOL
        k32.ReadFile.argtypes = [_wt.HANDLE, ctypes.c_void_p, _wt.DWORD, ctypes.POINTER(_wt.DWORD), ctypes.c_void_p]
        k32.ReadFile.restype = _wt.BOOL
        k32._karel_sig = True
    return k32


class _WinSerialPort:
    """Zero-dependency Win32 COM-port transport matching serial.Serial basics (incl. DTR)."""

    def __init__(self, device, baud=115200, timeout=0.25):
        self.k32 = _win32_k32()
        path = device if device.startswith("\\\\.\\") else f"\\\\.\\{device}"
        self.handle = self.k32.CreateFileW(path, 0xC0000000, 0, None, 3, 0, None)
        if not self.handle or self.handle == _INVALID_HANDLE:
            raise OSError(f"Cannot open {device}")
        try:
            dcb = _DCB()
            dcb.DCBlength = ctypes.sizeof(_DCB)
            self.k32.GetCommState(self.handle, ctypes.byref(dcb))
            dcb.BaudRate = int(baud)
            dcb.ByteSize = 8
            dcb.Parity = 0
            dcb.StopBits = 0
            # Enable fBinary (bit 0) and fDtrControl=1 (bits 4..5) so CircuitPython usb_cdc.data sees DTR!
            dcb.fFlags = (dcb.fFlags & ~0x30) | 0x11
            self.k32.SetCommState(self.handle, ctypes.byref(dcb))
            self.k32.EscapeCommFunction(self.handle, 5)  # SETDTR
            self.k32.EscapeCommFunction(self.handle, 3)  # SETRTS
            self._timeout = float(timeout)
            self._apply_timeouts()
        except Exception:
            self.close()
            raise

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, val):
        self._timeout = float(val)
        self._apply_timeouts()

    def _apply_timeouts(self):
        to = _COMMTIMEOUTS()
        to.ReadIntervalTimeout = 0xFFFFFFFF
        to.ReadTotalTimeoutMultiplier = 0
        to.ReadTotalTimeoutConstant = max(1, int(self._timeout * 1000))
        to.WriteTotalTimeoutMultiplier = 0
        to.WriteTotalTimeoutConstant = 250
        self.k32.SetCommTimeouts(self.handle, ctypes.byref(to))

    def reset_input_buffer(self):
        self.k32.PurgeComm(self.handle, 0x000F)

    def write(self, data):
        buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        written = _wt.DWORD(0)
        if not self.k32.WriteFile(self.handle, buf, len(data), ctypes.byref(written), None):
            raise OSError("COM write failed")
        return int(written.value)

    def read(self, n=64):
        buf = ctypes.create_string_buffer(max(1, int(n)))
        got = _wt.DWORD(0)
        if not self.k32.ReadFile(self.handle, buf, len(buf), ctypes.byref(got), None):
            raise OSError("COM read failed")
        return buf.raw[: got.value]

    def readline(self):
        deadline = time.monotonic() + max(0.05, self._timeout)
        out = bytearray()
        while time.monotonic() < deadline and len(out) < 256:
            ch = self.read(1)
            if not ch:
                continue
            out.extend(ch)
            if ch == b"\n":
                break
        return bytes(out)

    def close(self):
        if getattr(self, "handle", None) and self.handle != _INVALID_HANDLE:
            try:
                self.k32.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None


class _PosixSerialPort:
    """Zero-dependency POSIX/macOS CDC serial transport fallback when pyserial is absent."""

    def __init__(self, device, timeout=0.25):
        import termios
        self.fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self.timeout = float(timeout)
        try:
            attrs = termios.tcgetattr(self.fd)
            attrs[0] = 0
            attrs[1] = 0
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[3] = 0
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 0
            if hasattr(termios, "cfsetispeed") and hasattr(termios, "B115200"):
                termios.cfsetispeed(attrs, termios.B115200)
                termios.cfsetospeed(attrs, termios.B115200)
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        except Exception:
            pass
        try:
            import fcntl
            if hasattr(termios, "TIOCSDTR"):
                fcntl.ioctl(self.fd, termios.TIOCSDTR)
        except Exception:
            pass

    def reset_input_buffer(self):
        try:
            while self.read(256):
                pass
        except Exception:
            pass

    def write(self, data):
        try:
            return os.write(self.fd, data)
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR):
                return 0
            raise

    def read(self, n=64):
        import select
        r, _, _ = select.select([self.fd], [], [], max(0.01, min(0.08, self.timeout)))
        if not r:
            return b""
        try:
            return os.read(self.fd, n)
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR):
                return b""
            raise

    def readline(self):
        deadline = time.monotonic() + max(0.05, self.timeout)
        out = bytearray()
        while time.monotonic() < deadline and len(out) < 256:
            ch = self.read(1)
            if not ch:
                continue
            out.extend(ch)
            if ch == b"\n":
                break
        return bytes(out)

    def close(self):
        if getattr(self, "fd", -1) >= 0:
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = -1


def _is_ignored_serial(dev):
    low = str(dev).lower()
    return any(tok in low for tok in ("bluetooth", "debug-console", "wlan-debug", "airpods", "beats"))


def _list_serial_candidates():
    """Return ordered list of (device_name, prefer_rank) using pyserial or OS registry/dev."""
    if serial is not None:
        try:
            ports = [p for p in serial.tools.list_ports.comports() if not _is_ignored_serial(p.device)]
            if IS_MAC:
                cu_set = {p.device for p in ports if "/dev/cu." in p.device}
                ports = [p for p in ports if not (p.device.startswith("/dev/tty.") and p.device.replace("/dev/tty.", "/dev/cu.", 1) in cu_set)]
            ports.sort(key=lambda p: (
                0 if getattr(p, "vid", None) in (0x2E8A, 0x239A) else 1,
                0 if "data" in str(getattr(p, "interface", "") or "").lower() else 1,
                p.device,
            ))
            return [(p.device, True) for p in ports]
        except Exception:
            pass
    if os.name == "nt" and winreg is not None:
        found = []
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM") as k:
                i = 0
                while True:
                    try:
                        kname, val, _ = winreg.EnumValue(k, i)
                        rk = 0 if "USBSER" in str(kname).upper() else 1
                        found.append((rk, str(val)))
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
        found.sort()
        return [(dev, False) for _, dev in found]
    devs = sorted(d for d in (glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/ttyACM*")) if not _is_ignored_serial(d))
    return [(d, False) for d in devs]


def _open_serial_port(device, use_pyserial):
    if use_pyserial and serial is not None:
        s = serial.Serial(device, 115200, timeout=0.25, write_timeout=0.25)
        try:
            s.dtr = True
            s.rts = True
        except Exception:
            pass
        return s
    if os.name == "nt":
        return _WinSerialPort(device, 115200, timeout=0.25)
    return _PosixSerialPort(device, timeout=0.25)


class SerialBridge:
    """Two-way USB CDC serial link to RP2350 SuperMini (works with or without pyserial)."""

    def __init__(self, rx_q):
        self.rx_q = rx_q
        self.ser = None
        self.port_name = None
        self.available = True
        self._stop = False
        self._last_scan = 0.0
        self._last_state = ""
        threading.Thread(target=self._loop, daemon=True).start()

    def send(self, line):
        if not self.ser:
            return
        if line.startswith("STATE:"):
            if line == self._last_state:
                return
            self._last_state = line
        try:
            self.ser.write((line.strip() + "\n").encode("utf-8"))
        except Exception:
            self._drop()

    def _drop(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.port_name = None
        self._last_state = ""

    def _connect(self):
        for dev, use_ps in _list_serial_candidates():
            try:
                s = _open_serial_port(dev, use_ps)
                time.sleep(0.08)
                s.reset_input_buffer()
                s.write(b"KAREL_PING\n")
                resp = s.readline().decode("utf-8", errors="ignore").strip()
                if "KAREL_PONG" in resp:
                    s.timeout = 0.05
                    self.ser = s
                    self.port_name = dev
                    return
                s.close()
            except Exception:
                pass

    def _loop(self):
        buf = ""
        while not self._stop:
            if not self.ser:
                now = time.time()
                if now - self._last_scan > 2.0:
                    self._last_scan = now
                    self._connect()
                time.sleep(0.2)
                continue
            try:
                chunk = self.ser.read(64)
                if chunk:
                    buf += chunk.decode("utf-8", errors="ignore")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if line.startswith("EVENT:"):
                            self.rx_q.put(line)
                else:
                    time.sleep(0.04)
            except Exception:
                self._drop()


SINGLETON_PORT = 42421


def try_signal_existing(toggle=False):
    """Signal a running Karel (TOGGLE dive-close or USB BOOP) instead of spawning a duplicate."""
    try:
        with socket.create_connection(("127.0.0.1", SINGLETON_PORT), timeout=0.35) as s:
            s.sendall(b"TOGGLE\n" if toggle else b"BOOP\n")
        return True
    except OSError:
        return False


def start_singleton_listener(rx_q):
    """Listen on localhost to handle BOOP or TOGGLE commands cleanly."""
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", SINGLETON_PORT))
        srv.listen(4)
    except OSError:
        return

    def _accept():
        while True:
            try:
                conn, _ = srv.accept()
                data = conn.recv(64)
                conn.close()
                if b"TOGGLE" in data:
                    rx_q.put("EVENT:TOGGLE_KAREL")
                elif b"BOOP" in data:
                    rx_q.put("EVENT:RST_BOOP")
            except OSError:
                break

    threading.Thread(target=_accept, daemon=True).start()
