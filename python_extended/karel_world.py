"""Desktop world helpers for Karel de Koala: LRU sprite cache, Win32/macOS ledge snap, tray, buttons & perks."""
import ctypes
import ctypes.wintypes as _wt
import json
import math
import os
import random
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections import OrderedDict

from karel_i18n import coin_u, lang_of, tr, tr_committee, tr_item, tr_trivia_pick, trf
from karel_wardrobe import get_outfit_perk

IS_MAC = sys.platform == "darwin"

KAREL_SIZES = ((2, "Klein (64px)"), (3, "Normaal (96px)"), (4, "Groot (128px)"), (5, "Reus (160px)"))

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


def set_win_app_id():
    """Enable Win32 Per-Monitor DPI awareness and register AppUserModelID before Tk starts."""
    if os.name == "nt":
        try:
            u32 = ctypes.windll.user32
            try:
                u32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
                u32.SetProcessDpiAwarenessContext.restype = _wt.BOOL
                if not u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                    raise OSError()
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    try:
                        u32.SetProcessDPIAware()
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Sticky.KarelDeKoala.1")
        except Exception:
            pass


def get_virtual_bounds(sw, sh):
    """Return multi-monitor virtual desktop bounding box (left, top, right, bottom)."""
    if os.name == "nt":
        try:
            u32 = ctypes.windll.user32
            u32.GetSystemMetrics.argtypes = [ctypes.c_int]
            u32.GetSystemMetrics.restype = ctypes.c_int
            vx = u32.GetSystemMetrics(76)
            vy = u32.GetSystemMetrics(77)
            vw = u32.GetSystemMetrics(78)
            vh = u32.GetSystemMetrics(79)
            if vw > 0 and vh > 0:
                return int(vx), int(vy), int(vx + vw), int(vy + vh)
        except Exception:
            pass
    elif IS_MAC:
        from karel_sync import get_mac_virtual_bounds
        return get_mac_virtual_bounds(sw, sh)
    return 0, 0, sw, sh


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


def _put_opaque_runs(img, row, y, color_map):
    """Write contiguous non-transparent pixel runs onto a PhotoImage row."""
    n = len(row)
    x = 0
    while x < n:
        ch = row[x]
        if ch == "." or ch not in color_map or not color_map[ch]:
            x += 1
            continue
        col = color_map[ch]
        x1 = x + 1
        while x1 < n and row[x1] == ch:
            x1 += 1
        img.put(col, to=(x, y, x1, y + 1))
        x = x1


def render_alpha_grid_photo(tk_mod, mat, size, scale, palette, clip_rows=None):
    """Render an alpha-transparent sprite PhotoImage scaled cleanly without key-color artifacts."""
    img = tk_mod.PhotoImage(width=size, height=size)
    if clip_rows is not None and clip_rows < size:
        y_off = size - max(0, clip_rows)
        for sy in range(max(0, clip_rows)):
            _put_opaque_runs(img, mat[sy], y_off + sy, palette)
    else:
        for sy in range(min(size, len(mat))):
            _put_opaque_runs(img, mat[sy], sy, palette)
    return img.zoom(scale, scale) if scale > 1 else img


def _grid_to_photo(tk_mod, grid):
    col_map = {k: f"#{v[0]:02x}{v[1]:02x}{v[2]:02x}" for k, v in _ICON_PAL.items() if v is not None}
    return render_alpha_grid_photo(tk_mod, grid, len(grid), 1, col_map)


def apply_window_icon(win, app, tk_mod=None, is_root=False):
    """Apply crisp Karel Koala icon to window titlebar, Windows taskbar, and macOS Dock."""
    try:
        if not getattr(app, "_icon_photos", None) and tk_mod is not None:
            g64 = _scale_icon_grid(_ICON_16, 4) if IS_MAC else _scale_icon_grid(_ICON_16, 2)
            p_lg = _grid_to_photo(tk_mod, g64)
            p16 = _grid_to_photo(tk_mod, _ICON_16)
            app._icon_photos = (p_lg, p16)
            if os.name == "nt":
                g32 = _scale_icon_grid(_ICON_16, 2)
                d32, d16 = _encode_ico_dib(g32), _encode_ico_dib(_ICON_16)
                hdr = struct.pack("<HHH", 0, 1, 2)
                off0 = 6 + 32
                off1 = off0 + len(d32)
                e0 = struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, len(d32), off0)
                e1 = struct.pack("<BBBBHHII", 16, 16, 0, 0, 1, 32, len(d16), off1)
                ico_p = os.path.join(tempfile.gettempdir(), "karel_sticky_icon.ico")
                with open(ico_p, "wb") as f:
                    f.write(hdr + e0 + e1 + d32 + d16)
                app._icon_ico = ico_p
        photos = getattr(app, "_icon_photos", None)
        if photos:
            win.iconphoto(is_root, *photos)
        ico_p = getattr(app, "_icon_ico", None)
        if os.name == "nt" and ico_p and os.path.isfile(ico_p):
            win.iconbitmap(ico_p)
    except Exception:
        pass


def make_flat_button(parent, tk_mod, command=None, hover_bg=None, **kw):
    """Create a colored flat button (uses Label-based button on macOS Aqua where Button ignores bg)."""
    if not IS_MAC:
        return tk_mod.Button(parent, command=command, **kw)
    for drop in ("activebackground", "activeforeground", "default", "overrelief"):
        kw.pop(drop, None)
    kw.setdefault("cursor", "hand2")
    kw.setdefault("relief", "flat")
    lbl = tk_mod.Label(parent, **kw)
    if command is not None:
        lbl.bind("<Button-1>", lambda _e, fn=command: fn())
    if hover_bg:
        orig_bg = kw.get("bg", "")
        lbl.bind("<Enter>", lambda _e: lbl.configure(bg=hover_bg))
        lbl.bind("<Leave>", lambda _e: lbl.configure(bg=orig_bg))
    return lbl


def setup_mac_hooks(app):
    """Wire macOS Aqua Dock Reopen, Cmd+Q, and Apple-menu Quit hooks cleanly."""
    if not IS_MAC:
        return
    try:
        app.r.createcommand("::tk::mac::Quit", lambda: app.quit_app(immediate=True))
    except Exception:
        pass
    try:
        app.r.createcommand("::tk::mac::ReopenApplication", app.wake_from_tray)
    except Exception:
        pass
    try:
        app.r.bind_all("<Command-q>", lambda _e: (app.quit_app(), "break")[1])
    except Exception:
        pass


def init_pet_window(app, tkey, fallback_bg):
    """Configure frameless topmost transparent pet window + macOS Aqua hooks; return canvas bg."""
    r = app.r
    r.overrideredirect(True)
    r.attributes("-topmost", True)
    cbg = tkey
    if os.name == "nt":
        r.attributes("-transparentcolor", tkey)
    elif IS_MAC:
        try:
            r.wm_attributes("-transparent", True)
        except Exception:
            cbg = fallback_bg
    else:
        cbg = fallback_bg
    r.configure(bg=cbg)
    setup_mac_hooks(app)
    return cbg


def karel_metrics(scale):
    """Return (scale, px, cw, ch, ox, oy) for Karel canvas & sprite size."""
    s = max(2, min(5, int(scale)))
    px = 32 * s
    cw = max(224, px + 114)
    ch = px + 72
    return s, px, cw, ch, (cw - px) // 2, ch - px - 6


class SpriteCache:
    """Bounded LRU cache for rendered Tkinter PhotoImage frames."""

    def __init__(self, max_karel=180, max_comp=36):
        self.max_karel = max_karel
        self.max_comp = max_comp
        self._karel = OrderedDict()
        self._comp = OrderedDict()

    def get_karel(self, key, builder):
        """Return cached Karel PhotoImage or build and store it cleanly."""
        img = self._karel.get(key)
        if img is not None:
            self._karel.move_to_end(key)
            return img
        img = builder()
        self._karel[key] = img
        if len(self._karel) > self.max_karel:
            self._karel.popitem(last=False)
        return img

    def get_comp(self, key, builder):
        """Return cached companion PhotoImage or build and store it cleanly."""
        img = self._comp.get(key)
        if img is not None:
            self._comp.move_to_end(key)
            return img
        img = builder()
        self._comp[key] = img
        if len(self._comp) > self.max_comp:
            self._comp.popitem(last=False)
        return img

    def clear(self):
        self._karel.clear()
        self._comp.clear()


def window_hwnd(widget):
    """Best-effort top-level Win32 HWND for a Tk/Toplevel widget (0 if unavailable)."""
    if os.name != "nt" or widget is None:
        return 0
    try:
        wid = widget.winfo_id()
        parent = ctypes.windll.user32.GetParent(wid)
        return int(parent or wid)
    except Exception:
        return 0


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


def _fg_window_info(own_hwnds):
    """Return (u32, hwnd, title, rect) for active external Win32 window, or None."""
    if os.name != "nt":
        return None
    try:
        u32 = ctypes.windll.user32
        hwnd = int(u32.GetForegroundWindow() or 0)
        if not hwnd or hwnd in own_hwnds or not u32.IsWindowVisible(hwnd) or u32.IsIconic(hwnd):
            return None
        cls_buf = ctypes.create_unicode_buffer(64)
        if u32.GetClassNameW(hwnd, cls_buf, 64) and cls_buf.value in ("Shell_TrayWnd", "Progman", "WorkerW"):
            return None
        tlen = u32.GetWindowTextLengthW(hwnd)
        title = ""
        if tlen > 0:
            buf = ctypes.create_unicode_buffer(min(160, tlen + 1))
            u32.GetWindowTextW(hwnd, buf, len(buf))
            title = buf.value
        if title.startswith("Karel") or title in ("Program Manager", ""):
            return None
        rect = _RECT()
        if not u32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        return u32, hwnd, title, rect
    except Exception:
        return None


_MAC_PROBE = {
    "started": False, "want_ledge": False, "se_denied": False,
    "app_name": "", "bundle": "", "rect": None, "ts": 0.0,
}


def _mac_probe_step(want_ledge):
    """Run a single lightweight macOS frontmost-app & optional window-bounds query."""
    if not IS_MAC:
        return
    try:
        js = (
            'ObjC.import("AppKit");'
            'var fa=$.NSWorkspace.sharedWorkspace.frontmostApplication;'
            'var an=fa?ObjC.unwrap(fa.localizedName)||"":"";'
            'var bid=fa?ObjC.unwrap(fa.bundleIdentifier)||"":"";'
            'JSON.stringify({app:an,bid:bid});'
        )
        res = subprocess.run(["osascript", "-l", "JavaScript", "-e", js], capture_output=True, text=True, timeout=0.9)
        if res.returncode == 0 and res.stdout.strip():
            info = json.loads(res.stdout.strip())
            _MAC_PROBE["app_name"] = str(info.get("app", ""))
            _MAC_PROBE["bundle"] = str(info.get("bid", ""))
    except Exception:
        pass
    rect = None
    if want_ledge and not _MAC_PROBE["se_denied"]:
        low_app = _MAC_PROBE["app_name"].lower()
        if not low_app.startswith(("karel", "python")):
            try:
                as_cmd = (
                    'tell application "System Events" to tell (first application process whose frontmost is true) '
                    'to get {position of front window, size of front window}'
                )
                r2 = subprocess.run(["osascript", "-e", as_cmd], capture_output=True, text=True, timeout=0.9)
                if r2.returncode == 0 and r2.stdout.strip():
                    nums = [int(x.strip()) for x in r2.stdout.strip().split(",") if x.strip().lstrip("-").isdigit()]
                    if len(nums) == 4:
                        px, py, pw, ph = nums
                        rect = (px, py, px + pw, py + ph)
                elif "-1743" in (r2.stderr or "") or "not allowed" in (r2.stderr or "").lower():
                    _MAC_PROBE["se_denied"] = True
            except Exception:
                pass
    _MAC_PROBE["rect"] = rect
    _MAC_PROBE["ts"] = time.monotonic()


def _ensure_mac_probe(want_ledge=False):
    if not IS_MAC:
        return
    if want_ledge:
        _MAC_PROBE["want_ledge"] = True
    if _MAC_PROBE["started"]:
        return
    _MAC_PROBE["started"] = True

    def _bg():
        while True:
            _mac_probe_step(_MAC_PROBE["want_ledge"])
            time.sleep(0.95)

    threading.Thread(target=_bg, daemon=True).start()


def get_foreground_ledge(own_hwnds, karel_w, wl, wt, wr, wb):
    """Return (lx0, lx1, ledge_wy) top-bar ledge of the active window, or None."""
    if IS_MAC:
        _ensure_mac_probe(want_ledge=True)
        rect = _MAC_PROBE.get("rect")
        if not rect:
            return None
        rleft, rtop, rright, rbottom = rect
        w, h = rright - rleft, rbottom - rtop
        if w < max(karel_w + 48, 220) or h < 140 or rtop < wt + 36 or rtop > wb - 80:
            return None
        lx0 = max(wl, rleft + 12)
        lx1 = min(wr, rright - 12)
        return (int(lx0), int(lx1), int(rtop)) if (lx1 - lx0) >= karel_w + 20 else None
    info = _fg_window_info(own_hwnds)
    if not info:
        return None
    _, _, _, rect = info
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    # Require a visible title-bar ledge within the usable desktop work area.
    if w < max(karel_w + 48, 220) or h < 140 or rect.top < wt + 36 or rect.top > wb - 80:
        return None
    lx0 = max(wl, rect.left + 12)
    lx1 = min(wr, rect.right - 12)
    if lx1 - lx0 < karel_w + 20:
        return None
    return (int(lx0), int(lx1), int(rect.top))


_MEETING_MARKERS = (
    "zoom meeting", "meeting | microsoft teams", "vergadering | microsoft teams",
    "google meet", "meet - ", "webex meeting", "powerpoint-diavoorstelling", "powerpoint slide show",
)
_MAC_MEETING_MARKERS = ("zoom.us", "microsoft teams", "webex", "facetime", "google meet", "keynote")


def detect_fullscreen_or_meeting(own_hwnds):
    """Return 'fullscreen' / 'meeting' when an external app covers the monitor or is in a call."""
    if IS_MAC:
        _ensure_mac_probe(want_ledge=False)
        an = (_MAC_PROBE.get("app_name") + " " + _MAC_PROBE.get("bundle")).lower()
        if any(tok in an for tok in _MAC_MEETING_MARKERS):
            return "meeting"
        rect = _MAC_PROBE.get("rect")
        if rect:
            from karel_sync import _mac_screens_snapshot
            scs = _mac_screens_snapshot() or []
            rl, rt, rr, rb = rect
            for frm, _ in scs:
                if rl <= frm[0] + 2 and rt <= frm[1] + 2 and rr >= frm[2] - 2 and rb >= frm[3] - 2:
                    return "fullscreen"
        return ""
    info = _fg_window_info(own_hwnds)
    if not info:
        return ""
    u32, hwnd, title, rect = info
    tl = title.lower()
    if any(tok in tl for tok in _MEETING_MARKERS):
        return "meeting"
    try:
        mon = u32.MonitorFromWindow(hwnd, 2)
        if mon:
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(mi)
            if u32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                mr = mi.rcMonitor
                if rect.left <= mr.left + 2 and rect.top <= mr.top + 2 and rect.right >= mr.right - 2 and rect.bottom >= mr.bottom - 2:
                    return "fullscreen"
    except Exception:
        pass
    return ""


def spawn_prop(props, kind, x_off=0.0, y_off=-14.0, ttl=42):
    """Add an interactive desktop prop next to Karel (max 5 live props)."""
    if len(props) >= 5:
        props.pop(0)
    props.append({
        "kind": kind,
        "x": float(x_off),
        "y": float(y_off),
        "vy": -2.2,
        "ttl": int(ttl),
        "max_ttl": max(1, int(ttl)),
    })


def step_and_draw_props(cv, props, anchor_x, ground_y, scale):
    """Advance simple bounce physics and draw crisp pixel props onto the desktop canvas."""
    s = max(2, int(scale))
    kept = []
    for p in props:
        p["ttl"] -= 1
        if p["ttl"] <= 0:
            continue
        p["vy"] += 0.48
        p["y"] += p["vy"]
        if p["y"] > 0.0:
            p["y"] = 0.0
            p["vy"] = -abs(p["vy"]) * 0.35 if abs(p["vy"]) > 1.3 else 0.0
        kept.append(p)
        px = int(anchor_x + p["x"])
        bob = int(round(math.sin(p["ttl"] * 0.25) * 1.5)) if p["vy"] == 0.0 else 0
        py = int(ground_y + p["y"] + bob)
        _draw_prop_icon(cv, p["kind"], px, py, s)
    props[:] = kept


def _draw_prop_icon(cv, kind, cx, cy, s):
    """Render lightweight multi-color pixel props onto tk.Canvas."""
    u = max(2, s - 1)
    if kind == "leaf":
        cv.create_rectangle(cx - 2 * u, cy - u, cx + 2 * u, cy + u, fill="#3ECF8E", outline="#1B4332")
        cv.create_rectangle(cx - 3 * u, cy, cx - 2 * u, cy + u, fill="#1F8A56", outline="")
        cv.create_rectangle(cx + 2 * u, cy - 2 * u, cx + 3 * u, cy, fill="#6BE6AF", outline="")
    elif kind == "tosti":
        cv.create_rectangle(cx - 2 * u, cy - 2 * u, cx + 2 * u, cy + u, fill="#E5A94C", outline="#7F4F24")
        cv.create_rectangle(cx - 2 * u, cy - u, cx + 2 * u, cy, fill="#F5D76E", outline="")
    elif kind == "coffee":
        cv.create_rectangle(cx - 2 * u, cy - 2 * u, cx + u, cy + u, fill="#C41E25", outline="#1B1F2A")
        cv.create_rectangle(cx + u, cy - u, cx + 2 * u, cy, fill="#C41E25", outline="")
        cv.create_rectangle(cx - u, cy - 3 * u, cx + 1, cy - 2 * u, fill="#DCE3F0", outline="")
    elif kind == "duckie":
        cv.create_rectangle(cx - 2 * u, cy - u, cx + 2 * u, cy + u, fill="#F5C451", outline="#8B5E00")
        cv.create_rectangle(cx + u, cy - 2 * u, cx + 3 * u, cy - u, fill="#FF8C42", outline="")
    elif kind == "laser":
        cv.create_oval(cx - 2 * u, cy - 2 * u, cx + 2 * u, cy + 2 * u, fill="#56B6F7", outline="#FF7597", width=2)
        cv.create_oval(cx - u, cy - u, cx + u, cy + u, fill="#F2F5FA", outline="")
    elif kind == "coin":
        cv.create_oval(cx - 2 * u, cy - 2 * u, cx + 2 * u, cy + 2 * u, fill="#F5C451", outline="#9A6B0A", width=2)
        cv.create_rectangle(cx - 1, cy - u, cx + 2, cy + u, fill="#FFF3B0", outline="")
    elif kind == "fish":
        cv.create_rectangle(cx - 2 * u, cy - u, cx + 2 * u, cy + u, fill="#56B6F7", outline="#1D4E89")
        cv.create_rectangle(cx - 3 * u, cy - 2 * u, cx - 2 * u, cy + 2 * u, fill="#2E8BC0", outline="")
    elif kind == "heart":
        cv.create_rectangle(cx - 2 * u, cy - 2 * u, cx, cy, fill="#FF5D8F", outline="")
        cv.create_rectangle(cx, cy - 2 * u, cx + 2 * u, cy, fill="#FF5D8F", outline="")
        cv.create_rectangle(cx - u, cy - u, cx + u, cy + u, fill="#C41E25", outline="")
    else:  # note
        cv.create_rectangle(cx - u, cy - 2 * u, cx, cy + u, fill="#56B6F7", outline="")
        cv.create_rectangle(cx - u, cy - 2 * u, cx + 2 * u, cy - u, fill="#B48EFB", outline="")
        cv.create_oval(cx - 2 * u, cy, cx, cy + 2 * u, fill="#56B6F7", outline="")


def perk_info(equipped):
    """Return (perk_key, bonus_float, nl_label) or ('', 0.0, '') for the active single outfit."""
    p = get_outfit_perk(equipped)
    return (p[1], p[2], p[3]) if p else ("", 0.0, "")


def calc_xp(base_xp, equipped, campus_tag="", action_tags=(), seasonal_tag="", prestige=0):
    """Compute XP after equipped outfit perk, daily buff, seasonal event & prestige."""
    pkey, pval, _ = perk_info(equipped)
    mult = 1.0 + 0.15 * min(10, max(0, int(prestige or 0)))
    if pkey == "all_xp":
        mult += pval
    elif pkey in action_tags:
        mult += pval
    if campus_tag == "food_xp" and "cook_xp" in action_tags:
        mult += 0.25
    elif campus_tag == "coffee_xp" and "coffee_xp" in action_tags:
        mult += 0.30
    elif campus_tag == "happy_boost":
        mult += 0.12
    if seasonal_tag and seasonal_tag in action_tags:
        mult += 0.25
    elif seasonal_tag == "intro_xp" and "pet_xp" in action_tags:
        mult += 0.20
    return max(1, int(round(base_xp * mult)))


def calc_coins(base_coins, equipped, campus_tag="", action_tags=(), seasonal_tag="", prestige=0):
    """Compute Sticky coins after outfit perk, daily buff, seasonal event & prestige."""
    if base_coins <= 0:
        return 0
    pkey, pval, _ = perk_info(equipped)
    mult = 1.0 + 0.15 * min(10, max(0, int(prestige or 0)))
    if pkey in action_tags:
        mult += pval
    if campus_tag == "roam_loot" and "roam_coins" in action_tags:
        mult += 0.25
    elif campus_tag == "gans_coins" and ("game_coins" in action_tags or "gans_coins" in action_tags):
        mult += 0.25
    if seasonal_tag == "committee_coins" and "committee_coins" in action_tags:
        mult += 0.30
    elif seasonal_tag and seasonal_tag in action_tags:
        mult += 0.25
    return max(1, int(round(base_coins * mult)))


def roam_speed_mult(upgrades, equipped):
    """Compute roaming movement multiplier from upgrades and equipped outfit perk."""
    pkey, pval, _ = perk_info(equipped)
    mult = 1.0
    if pkey == "roam_speed":
        mult += pval
    if "turbo_sneakers" in upgrades:
        mult += 0.30
    return mult


def fish_luck_bonus(equipped, campus_tag="", seasonal_tag=""):
    """Compute bonus multiplier on rare fish/loot rolls."""
    pkey, pval, _ = perk_info(equipped)
    mult = 1.0 + (pval if pkey == "fish_luck" else 0.0)
    if "fish_rarity" in (campus_tag, seasonal_tag):
        mult += 0.35
    return mult


def stat_decay_factors(equipped):
    """Return (hunger_mult, energy_mult) reduction from equipped passive outfit."""
    pkey, pval, _ = perk_info(equipped)
    hunger_k = max(0.55, 1.0 - pval) if pkey == "hunger_save" else 1.0
    energy_k = max(0.55, 1.0 - pval) if pkey == "energy_save" else 1.0
    return hunger_k, energy_k


_PARTICLE_COLORS = {
    "HEART": ("♥", ["#FF7597", "#FF4081", "#C41E25"]),
    "CRUMB": ("■", ["#3ECF8E", "#81C784", "#C8E6C9"]),
    "BUBBLE": ("o", ["#80DEEA", "#E0F7FA", "#56B6F7"]),
    "COIN": ("$", ["#F5C451", "#FFF176", "#FFB300"]),
    "SNEEZE": ("*", ["#E2E5EB", "#FFFFFF", "#B0BEC5"]),
    "CONFETTI": ("■", ["#C41E25", "#F5C451", "#3ECF8E", "#56B6F7", "#FF7597"]),
    "NOTE": ("♪", ["#F5C451", "#56B6F7", "#FF7597", "#69F0AE"]),
    "MAGIC": ("✦", ["#56B6F7", "#C792EA", "#F5C451", "#FFFFFF"]),
    "SWEAT": ("'", ["#56B6F7", "#80DEEA", "#FFFFFF"]),
}


def spawn_particles(particles, kind, ox, oy, px, count=6, label=None, gold="#F5C451"):
    """Append floating particles or XP/coin label bursts onto Karel's canvas queue."""
    if kind == "FLOAT":
        particles.append([ox + px // 2, oy + 6, 0.0, -1.3, label or "+XP", gold, 24])
        return
    sym, cols = _PARTICLE_COLORS.get(kind, ("*", ["#FFF"]))
    for _ in range(count):
        particles.append([
            ox + px // 2 + random.randint(-30, 30),
            oy + 24 + random.randint(-12, 16),
            random.uniform(-2.2, 2.2), random.uniform(-3.6, -1.2),
            sym, random.choice(cols), random.randint(16, 28),
        ])


def step_particles(particles):
    """Advance particle physics and drop expired items."""
    nxt = []
    for p in particles:
        p[0] += p[2]
        p[1] += p[3]
        if not (isinstance(p[4], str) and p[4].startswith("+")):
            p[3] += 0.14
        p[6] -= 1
        if p[6] > 0:
            nxt.append(p)
    particles[:] = nxt


def pick_roam_target(mode, own_hwnds, cached_ledge, min_x, max_x, min_y, ground_y, ox, oy, px, bounds):
    """Return (tx, ty, updated_ledge) for free or active-window ledge roaming."""
    wl, wt, wr, wb = bounds
    if mode == "window" and cached_ledge:
        lx0, lx1, lwy = cached_ledge
        tx0 = max(min_x, float(lx0 - ox))
        tx1 = max(tx0, min(max_x, float(lx1 - ox - px)))
        ty = max(min_y, min(ground_y, float(lwy - (oy + px))))
        return random.uniform(tx0, tx1), ty, cached_ledge
    ledge = get_foreground_ledge(own_hwnds, px, wl, wt, wr, wb) if random.random() < 0.14 else None
    if ledge:
        lx0, lx1, lwy = ledge
        ty = max(min_y, min(ground_y, float(lwy - (oy + px))))
        tx0 = max(min_x, float(lx0 - ox))
        tx1 = max(tx0, min(max_x, float(lx1 - ox - px)))
        return random.uniform(tx0, tx1), ty, cached_ledge
    ty = float(ground_y) if random.random() < 0.55 else float(random.randint(int(min_y), int(ground_y)))
    tx = float(random.randint(int(min_x), int(max_x)))
    return tx, ty, cached_ledge


def draw_speech_bubble(cv, text, cw, oy, red, ui_font):
    """Draw a compact dynamic-width Sticky Studio speech pill above Karel."""
    txt_id = cv.create_text(
        cw // 2 + 2,
        oy - 14,
        text=text,
        width=min(176, max(136, cw - 36)),
        anchor="s",
        fill="#141822",
        font=(ui_font, 10 if IS_MAC else 8, "bold"),
        justify="center",
    )
    box = cv.bbox(txt_id) or (cw // 2 - 48, oy - 36, cw // 2 + 48, oy - 16)
    bx0 = max(6, box[0] - 11)
    by0 = max(4, box[1] - 5)
    bx1 = min(cw - 6, box[2] + 9)
    by1 = min(oy - 8, box[3] + 5)
    tx = max(bx0 + 12, min(bx1 - 12, cw // 2))
    cv.create_rectangle(bx0 + 2, by0 + 2, bx1 + 2, by1 + 2, fill="#111318", outline="")
    cv.create_rectangle(bx0, by0, bx1, by1, fill="#F8FAFF", outline=red, width=2)
    cv.create_rectangle(bx0, by0, bx0 + 5, by1, fill=red, outline="")
    cv.create_polygon(tx - 5, by1, tx + 5, by1, tx, by1 + 6, fill="#F8FAFF", outline=red, width=2)
    cv.create_line(tx - 4, by1, tx + 4, by1, fill="#F8FAFF", width=2)
    cv.tag_raise(txt_id)


def popup_context_menu(tk_mod, app, event, card_bg, fg_col, red_bg, ui_font, music_tracks, arcade_entries=None):
    """Build and open Karel's streamlined, bilingual desktop context menu."""
    lang = lang_of(app)
    m = tk_mod.Menu(app.r, tearoff=0, bg=card_bg, fg=fg_col, activebackground=red_bg, activeforeground="#FFF", font=(ui_font, 9))
    m.add_command(label=tr(lang, "Open Sticky Hub"), command=lambda: app.open_hub(0))
    m.add_command(label=tr(lang, "Sticky BK"), command=lambda: app.open_hub(3))
    m.add_separator()
    for lbl, cmd in (
        ("Voer Eucalyptus (+25)", app.feed),
        ("Sticky Koffie (+9 XP)", app.coffee),
        ("Aai Karel (+20)", app.pet),
        ("Powernap AAN/UIT", app.nap_toggle),
    ):
        m.add_command(label=tr(lang, lbl), command=cmd)
    m.add_separator()

    foc_lbl = "Stop Focus" if getattr(app, "focus_active", False) else "Focus Modus (25m)"
    m.add_command(label=tr(lang, foc_lbl), command=lambda: app.toggle_focus(25))

    am = tk_mod.Menu(m, tearoff=0, bg=card_bg, fg=fg_col, activebackground=red_bg, font=(ui_font, 9))
    for lbl, cmd in (
        ("Was Karel", app.wash),
        ("Dansen", app.dance),
        ("Sporten", app.exercise),
        ("Vissen", app.fish),
        ("Trivia (+16m)", app.open_trivia),
    ):
        am.add_command(label=tr(lang, lbl), command=cmd)
    m.add_cascade(label=tr(lang, "Acties"), menu=am)

    tm = tk_mod.Menu(m, tearoff=0, bg=card_bg, fg=fg_col, activebackground=red_bg, font=(ui_font, 9))
    for tlbl, tst, tmsg in (
        ("Backflip!", "BACKFLIP", "Wooo! Koala Backflip!!"),
        ("360° Draai", "SPIN", "Swoosh! 360° draai!"),
        ("Jetpack Vlucht", "JETPACK", "Naar de BBG-maan!!"),
        ("Kijk achter Taakbalk", "PEEK", "Psst... zie je me?"),
        ("Code op Laptop", "LAPTOP_CODE", "git commit -m 'fix'"),
        ("Vergrootglas (Debug)", "MAGNIFY", "Zoekende naar bugs..."),
        ("Papieren Vliegtuigje", "PAPER_PLANE", "Zoooef!!"),
        ("Sticky Paraplu", "UMBRELLA", "Typisch Nederlands weer!"),
        ("Oortjes Wiebel", "EARS_WIGGLE", "*Wiebel wiebel*"),
        ("Hartje Knuffelen", "HUG_PLUSH", "Sticky liefde!"),
        ("Eucalyptus Knuffel", "EUCALYPTUS_HUG", "Mijn favoriete tak!"),
        ("Feesttoeter", "PARTY_HORN", "VrijMiBo tijd!!"),
        ("Diepe Buiging", "BOW", "Dankjewel, Sticky!"),
        ("Zwaaien", "WAVE", "Hoi!!"),
        ("Gitaar Solo", "GUITAR", "♪ 8-bit riff! ♪"),
        ("Snare Drums", "DRUM", "Ba-dum-tss!"),
        ("Flexen", "FLEX", "Pure RP2350 spierkracht!"),
    ):
        tm.add_command(label=tr(lang, tlbl), command=lambda s=tst, m0=tmsg: app.play_trick(s, m0))
    m.add_cascade(label=tr(lang, "Trucjes & Animaties"), menu=tm)

    sm_cfg = tk_mod.Menu(m, tearoff=0, bg=card_bg, fg=fg_col, activebackground=red_bg, font=(ui_font, 9))
    rm = tk_mod.Menu(sm_cfg, tearoff=0, bg=card_bg, fg=fg_col, activebackground=red_bg, font=(ui_font, 9))
    for mid, mlbl in (
        ("free", "Heel Scherm (Auto)"),
        ("window", "Op Actief Venster"),
        ("cursor", "Volg Mijn Muis"),
        ("park", "Blijf Zitten"),
    ):
        rm.add_command(label=tr(lang, mlbl), command=lambda k=mid: app.set_roam_mode(k))
    sm_cfg.add_cascade(label=tr(lang, "Loopgedrag"), menu=rm)

    szm = tk_mod.Menu(sm_cfg, tearoff=0, bg=card_bg, fg=fg_col, activebackground=red_bg, font=(ui_font, 9))
    for sz, slbl in KAREL_SIZES:
        szm.add_command(label=tr(lang, slbl), command=lambda v=sz: app.set_karel_scale(v))
    sm_cfg.add_cascade(label=tr(lang, "Karel Grootte"), menu=szm)

    mm = tk_mod.Menu(sm_cfg, tearoff=0, bg=card_bg, fg=fg_col, activebackground=red_bg, font=(ui_font, 9))
    for tid, (tname, _) in music_tracks.items():
        mm.add_command(label=tr(lang, tname), command=lambda k=tid: app.set_music(k))
    mm.add_separator()
    mm.add_command(label=tr(lang, "Geluid Dempen / Aan"), command=app._toggle_mute)
    mm.add_command(label=tr(lang, "Stem-Bliepjes Aan/Uit"), command=app._toggle_voice)
    sm_cfg.add_cascade(label=tr(lang, "Muziek & Audio"), menu=mm)
    sm_cfg.add_separator()
    sm_cfg.add_command(label=tr(lang, "Taal: English / Nederlands"), command=app.toggle_language)
    m.add_cascade(label=tr(lang, "Instellingen"), menu=sm_cfg)

    m.add_separator()
    hide_lbl = tr(lang, "Verberg in Dock" if IS_MAC else "Verberg achter Taakbalk (Tray)")
    m.add_command(label=hide_lbl, command=lambda: app.trigger_dive_close(mode="tray"))
    m.add_command(label=tr(lang, "Duik achter Taakbalk & Sluit"), command=app.quit_app)
    m.tk_popup(event.x_root, event.y_root)
    return m


def focus_start(app, mins=25):
    """Start Pomodoro focus session and settle Karel into STUDY state."""
    import time
    mins = max(1, int(mins))
    app.focus_active = True
    app.focus_phase = "focus"
    app.focus_total = mins * 60
    app.focus_rem = app.focus_total
    app.focus_last_ts = time.monotonic()
    app.climbing = False
    app.act_ticks = 0
    app.state = "STUDY"
    app.say(trf(lang_of(app), "focus_go", m=mins), 55)
    app.hub.refresh()


def focus_stop(app):
    """Cancel active Pomodoro focus or break session."""
    app.focus_active = False
    app.focus_phase = "focus"
    app.focus_rem = 0
    if app.state == "STUDY":
        app.state = "IDLE"
    app.hub.refresh()


def focus_complete(app):
    """Complete active focus block (awards XP/coins & enters 5m break) or end break."""
    import time
    lang = lang_of(app)
    mins = max(1, app.focus_total // 60)
    if app.focus_phase == "focus":
        app.d["focus_sessions"] = app.d.get("focus_sessions", 0) + 1
        xp = app._xp(max(12, mins + 5), "study_xp")
        c = app.add_coins(app._coins(max(6, mins // 2), "study_xp"))
        app.gain_xp(xp)
        app.unlock("Pomodoro Pro")
        if app.d["focus_sessions"] >= 10:
            app.unlock("Focus Legende")
        app._set_action("CELEBRATE", 40)
        app._spawn_particles("CONFETTI", 12)
        app.snd.levelup()
        app.focus_phase = "break"
        app.focus_total = 300
        app.focus_rem = 300
        app.focus_last_ts = time.monotonic()
        app.say(trf(lang, "focus_done", xp=xp, c=c), 85)
        app.sm.save(app.d)
    else:
        focus_stop(app)
        app.snd.unlock()
        app.say(trf(lang, "brk_done"), 60)
    app.hub.refresh()


def quiet_apply(app, reason):
    """Move Karel cleanly into corner quiet mode for fullscreen apps/meetings, or restore."""
    if reason:
        if not app.auto_paused:
            app._pre_quiet_pos = (app.wx, app.wy)
            app.auto_paused = True
            app._quiet_reason = reason
            app.wx = app.max_x()
            app.wy = app.min_y()
            app.bubble = ""
            app.bubble_ticks = 0
            app.state = "IDLE"
            app.snd.set_auto_quiet(True)
    elif app.auto_paused:
        app.auto_paused = False
        app._quiet_reason = ""
        app.snd.set_auto_quiet(False)
        if app._pre_quiet_pos:
            px, py = app._pre_quiet_pos
            app.wx = max(app.min_x(), min(app.max_x(), px))
            app.wy = max(app.min_y(), min(app.ground_y(), py))
            app._pre_quiet_pos = None


def prestige_activate(app):
    """Promote Lv.50+ Karel to next Alumni Prestige rank while keeping unlocks."""
    lang = lang_of(app)
    if int(app.d.get("level", 1)) < 50:
        app.snd.buzz()
        app.say(trf(lang, "pres_lock"), 65)
        return False
    p = int(app.d.get("prestige", 0)) + 1
    app.d["prestige"] = p
    app.d["xp"] = 0
    app.d["level"] = 1
    app.unlock("Alumni Prestige")
    app._set_action("CELEBRATE", 48)
    app._spawn_particles("CONFETTI", 20)
    app.snd.konami()
    app.say(trf(lang, "pres_go", p=p, bon=p * 15), 90)
    app.sm.save(app.d)
    app.hub.refresh()
    return True


def committee_execute(app, cid, committees, ingredients):
    """Execute one Sticky committee/working-group mission on cooldown."""
    lang = lang_of(app)
    meta = next((c for c in committees if c[0] == cid), None)
    if not meta or not app._use_cooldown("committee"):
        return False
    _, _, _, base_c, base_xp, anim, quote = meta
    _, _, quote_l = tr_committee(lang, cid, meta[1], meta[2], quote)
    mult = 1.25 if "vip_pas" in app.d.get("upgrades", []) else 1.0
    c_tags = ("committee_coins", "baco_coins") if cid == "baco" else ("committee_coins",)
    x_tags = ("study_xp",) if cid in ("commitcrowd", "educo", "hacc", "almanak", "kascom") else (("intro_xp",) if cid in ("intro", "ejw", "nova") else ())
    coins = app.add_coins(app._coins(max(6, int(base_c * 0.65 * mult)), *c_tags))
    app.gain_xp(app._xp(max(6, int(base_xp * 0.65 * mult)), *x_tags))
    ik = random.choice(list(ingredients.keys()))
    ing = app.d.setdefault("ingredients", {})
    ing[ik] = ing.get(ik, 0) + 1
    app.d["committee_runs"] = app.d.get("committee_runs", 0) + 1
    helped = app.d.setdefault("committees_helped", [])
    if cid not in helped:
        helped.append(cid)
    app._set_action(anim, 45)
    app._spawn_particles("CONFETTI", 10)
    app.snd.committee()
    app.quest_bump("committee", 1)
    app.unlock("Actief Commissielid")
    if app.d["committee_runs"] >= 15:
        app.unlock("Commissie-Kanter")
    if len(helped) >= len(committees):
        app.unlock("Alle Commissies")
    ing_n, _ = tr_item(lang, ik, ingredients[ik]["name"])
    app.say(f"{quote_l} (+{coins}{coin_u(lang)} & {ing_n})", 80)
    app.sm.save(app.d)
    app.hub.refresh()
    return True


def gacha_spin(app, skins, wardrobe_items, companions, loot_table):
    """Spin the RP2350 Mystery Gacha (40m) and award prize."""
    lang = lang_of(app)
    if app.d.get("coins", 0) < 40:
        app.snd.buzz()
        app.say(trf(lang, "need_40"))
        return None
    if not app._use_cooldown("gacha"):
        return None
    app.d["coins"] -= 40
    app.unlock("Gacha Geluk")
    locked_skins = [k for k in skins if k not in app.d.get("unlocked_skins", ["classic"])]
    locked_acc = [k for k in wardrobe_items if k not in app.d.get("unlocked_accessories", []) and k != "scarf"]
    locked_cp = [k for k in companions if k not in app.d.get("unlocked_companions", ["none"]) and k != "none"]
    r = random.random()
    if r < 0.25 and locked_skins:
        pick = random.choice(locked_skins)
        app.d["unlocked_skins"].append(pick)
        if len(app.d["unlocked_skins"]) >= 5:
            app.unlock("Mode-Icoon")
        sn, _ = tr_item(lang, pick, skins[pick][0])
        msg, jackpot = trf(lang, "g_skin", name=sn), True
    elif r < 0.45 and locked_cp:
        pick = random.choice(locked_cp)
        app.d["unlocked_companions"].append(pick)
        if len(app.d["unlocked_companions"]) >= 6:
            app.unlock("Dierentuin op Bureau")
        cn, _ = tr_item(lang, pick, companions[pick][0])
        msg, jackpot = trf(lang, "g_comp", name=cn), True
    elif r < 0.70 and locked_acc:
        pick = random.choice(locked_acc)
        app.d["unlocked_accessories"].append(pick)
        if len(app.d["unlocked_accessories"]) >= 6:
            app.unlock("Stylist van de Kamer")
        wn, _ = tr_item(lang, pick, wardrobe_items[pick][0])
        msg, jackpot = trf(lang, "g_acc", name=wn), True
    elif r < 0.85:
        inv = app.d.setdefault("inventory", {})
        inv["sterren_elixer"] = inv.get("sterren_elixer", 0) + 1
        msg, jackpot = trf(lang, "g_elix"), False
    else:
        lid, lname, rty, _, _ = random.choice(loot_table[15:])
        dex = app.d.setdefault("dex", {})
        dex[lid] = dex.get(lid, 0) + 1
        for req, ach in ((10, "Schatzoeker"), (20, "Archivaris"), (len(loot_table), "Museumdirecteur")):
            if len(dex) >= req:
                app.unlock(ach)
        ln, _ = tr_item(lang, lid, lname)
        msg, jackpot = trf(lang, "g_dex", rar=tr(lang, rty), name=ln), False
    app.snd.gacha(jackpot=jackpot)
    app._set_action("CELEBRATE", 40)
    app._spawn_particles("CONFETTI", 16 if jackpot else 8)
    app.say(msg, 85)
    app.sm.save(app.d)
    app.hub.refresh()
    return msg


def open_trivia_dialog(tk_mod, app, trivia_questions, colors, ui_font):
    """Open the Informational Sticky Trivia quiz Toplevel window."""
    lang = lang_of(app)
    bg, card, red, gold, fg = colors
    idx = random.randrange(len(trivia_questions))
    q_nl, opts_nl, ans_nl = trivia_questions[idx]
    q_txt, opts, ans_idx = tr_trivia_pick(lang, idx, q_nl, opts_nl, ans_nl)
    w = tk_mod.Toplevel(app.r)
    w.title(trf(lang, "triv_t"))
    w.configure(bg=bg)
    w.geometry("450x268")
    w.resizable(False, False)
    w.attributes("-topmost", True)
    apply_window_icon(w, app, tk_mod)
    app.trivia_win = w
    tk_mod.Label(w, text=trf(lang, "triv_h"), bg=red, fg="#FFF", pady=9, font=(ui_font, 10, "bold")).pack(fill="x")
    tk_mod.Label(w, text=q_txt, bg=bg, fg=gold, font=(ui_font, 10, "bold"), wraplength=410, pady=12).pack()

    def answer(i):
        if i == ans_idx:
            c = app.add_coins(app._coins(16, "trivia_xp"))
            xp = app._xp(12, "trivia_xp", "study_xp")
            app.gain_xp(xp)
            app.d["total_trivia"] = app.d.get("total_trivia", 0) + 1
            app.quest_bump("trivia", 1)
            if app.d["total_trivia"] >= 10:
                app.unlock("Quiz-Kanon")
            if app.d["total_trivia"] >= 25:
                app.unlock("Sticky Wikipedia")
            app.snd.trivia_ok()
            app._set_action("CELEBRATE", 28)
            app.say(trf(lang, "triv_ok", c=c, xp=xp))
        else:
            app.snd.buzz()
            app.say(trf(lang, "triv_no", ans=opts[ans_idx]))
        app.sm.save(app.d)
        app.hub.refresh()
        w.destroy()

    order = list(enumerate(opts))
    random.shuffle(order)
    for orig_i, text in order:
        make_flat_button(
            w, tk_mod, command=lambda oi=orig_i: answer(oi), hover_bg="#2A3042",
            text=text, bg=card, fg=fg, activebackground="#2A3042", activeforeground="#FFF",
            bd=0, pady=8, cursor="hand2", font=(ui_font, 11 if IS_MAC else 9, "bold"),
        ).pack(fill="x", padx=22, pady=3)


class WinTrayBridge:
    """Zero-dependency Win32 system tray icon, Ctrl+Alt+K hotkey & shutdown save hook."""

    def __init__(self, rx_q, ico_path="", lang_fn=None, on_shutdown=None, register_hotkey=True):
        self.rx_q = rx_q
        self.ico_path = ico_path or ""
        self.lang_fn = lang_fn or (lambda: "nl")
        self.on_shutdown = on_shutdown
        self.register_hotkey = register_hotkey
        self.hwnd = None
        self.hotkey_ok = False
        self.tray_ok = False
        self._ready = threading.Event()
        self._wndproc_ref = None
        if os.name == "nt":
            threading.Thread(target=self._run, daemon=True).start()
            self._ready.wait(timeout=1.0)
        else:
            self._ready.set()

    @staticmethod
    def _bind_u32():
        u32 = ctypes.windll.user32
        if getattr(u32, "_karel_tray_sig", False):
            return u32
        lp = ctypes.c_ssize_t
        u32.DefWindowProcW.argtypes = [_wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM]
        u32.DefWindowProcW.restype = lp
        u32.CreateWindowExW.argtypes = [
            _wt.DWORD, _wt.LPCWSTR, _wt.LPCWSTR, _wt.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            _wt.HWND, _wt.HMENU, _wt.HINSTANCE, _wt.LPVOID,
        ]
        u32.CreateWindowExW.restype = _wt.HWND
        u32.DestroyWindow.argtypes = [_wt.HWND]
        u32.DestroyWindow.restype = _wt.BOOL
        u32.PostMessageW.argtypes = [_wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM]
        u32.PostMessageW.restype = _wt.BOOL
        u32.PostQuitMessage.argtypes = [ctypes.c_int]
        u32.GetMessageW.argtypes = [ctypes.POINTER(_wt.MSG), _wt.HWND, _wt.UINT, _wt.UINT]
        u32.GetMessageW.restype = _wt.BOOL
        u32.TranslateMessage.argtypes = [ctypes.POINTER(_wt.MSG)]
        u32.DispatchMessageW.argtypes = [ctypes.POINTER(_wt.MSG)]
        u32.DispatchMessageW.restype = lp
        u32.RegisterHotKey.argtypes = [_wt.HWND, ctypes.c_int, _wt.UINT, _wt.UINT]
        u32.RegisterHotKey.restype = _wt.BOOL
        u32.UnregisterHotKey.argtypes = [_wt.HWND, ctypes.c_int]
        u32.UnregisterHotKey.restype = _wt.BOOL
        u32.LoadImageW.argtypes = [_wt.HINSTANCE, _wt.LPCWSTR, _wt.UINT, ctypes.c_int, ctypes.c_int, _wt.UINT]
        u32.LoadImageW.restype = _wt.HANDLE
        u32.LoadIconW.argtypes = [_wt.HINSTANCE, _wt.LPCWSTR]
        u32.LoadIconW.restype = _wt.HICON
        u32.CreatePopupMenu.argtypes = []
        u32.CreatePopupMenu.restype = _wt.HMENU
        u32.AppendMenuW.argtypes = [_wt.HMENU, _wt.UINT, _wt.WPARAM, _wt.LPCWSTR]
        u32.AppendMenuW.restype = _wt.BOOL
        u32.TrackPopupMenu.argtypes = [_wt.HMENU, _wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, _wt.HWND, ctypes.c_void_p]
        u32.TrackPopupMenu.restype = _wt.BOOL
        u32.DestroyMenu.argtypes = [_wt.HMENU]
        u32.SetForegroundWindow.argtypes = [_wt.HWND]
        u32.GetCursorPos.argtypes = [ctypes.POINTER(_wt.POINT)]
        u32._karel_tray_sig = True
        return u32

    def _run(self):
        u32 = self._bind_u32()
        k32 = ctypes.windll.kernel32
        k32.GetModuleHandleW.argtypes = [_wt.LPCWSTR]
        k32.GetModuleHandleW.restype = _wt.HINSTANCE
        s32 = ctypes.windll.shell32

        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, _wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", _wt.UINT), ("style", _wt.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", _wt.HINSTANCE), ("hIcon", _wt.HICON), ("hCursor", _wt.HANDLE),
                ("hbrBackground", _wt.HANDLE), ("lpszMenuName", _wt.LPCWSTR),
                ("lpszClassName", _wt.LPCWSTR), ("hIconSm", _wt.HICON),
            ]

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", _wt.DWORD), ("Data2", _wt.WORD),
                ("Data3", _wt.WORD), ("Data4", ctypes.c_ubyte * 8),
            ]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [
                ("cbSize", _wt.DWORD), ("hWnd", _wt.HWND), ("uID", _wt.UINT),
                ("uFlags", _wt.UINT), ("uCallbackMessage", _wt.UINT),
                ("hIcon", _wt.HICON), ("szTip", ctypes.c_wchar * 128),
                ("dwState", _wt.DWORD), ("dwStateMask", _wt.DWORD),
                ("szInfo", ctypes.c_wchar * 256), ("uTimeoutOrVersion", _wt.UINT),
                ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", _wt.DWORD),
                ("guidItem", _GUID), ("hBalloonIcon", _wt.HICON),
            ]

        u32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
        u32.RegisterClassExW.restype = _wt.ATOM
        s32.Shell_NotifyIconW.argtypes = [_wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        s32.Shell_NotifyIconW.restype = _wt.BOOL

        WM_TRAY = 0x0400 + 20
        nid = NOTIFYICONDATAW()

        def show_menu(hwnd):
            hm = u32.CreatePopupMenu()
            en = (self.lang_fn() == "en")
            u32.AppendMenuW(hm, 0x0000, 1001, "Hide / Wake Karel (Ctrl+Alt+K)" if en else "Verberg / Roep Karel (Ctrl+Alt+K)")
            u32.AppendMenuW(hm, 0x0000, 1002, "Open Sticky Hub")
            u32.AppendMenuW(hm, 0x0800, 0, None)
            u32.AppendMenuW(hm, 0x0000, 1003, "Dive & Quit" if en else "Duik & Sluit Af")
            pt = _wt.POINT()
            u32.GetCursorPos(ctypes.byref(pt))
            u32.SetForegroundWindow(hwnd)
            cmd = u32.TrackPopupMenu(hm, 0x0100 | 0x0002, pt.x, pt.y, 0, hwnd, None)
            u32.PostMessageW(hwnd, 0, 0, 0)
            u32.DestroyMenu(hm)
            if cmd == 1001:
                self.rx_q.put("EVENT:TRAY_TOGGLE")
            elif cmd == 1002:
                self.rx_q.put("EVENT:OPEN_HUB")
            elif cmd == 1003:
                self.rx_q.put("EVENT:QUIT_NOW")

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == 0x0011 or (msg == 0x0016 and wparam):  # WM_QUERYENDSESSION / WM_ENDSESSION
                try:
                    self.rx_q.put("EVENT:SHUTDOWN_SAVE")
                    if self.on_shutdown:
                        self.on_shutdown()
                except Exception:
                    pass
                return 1
            if msg == 0x0312 and wparam == 1:  # WM_HOTKEY
                self.rx_q.put("EVENT:TRAY_TOGGLE")
                return 0
            if msg == WM_TRAY:
                ev = lparam & 0xFFFF
                if ev in (0x0202, 0x0203):  # WM_LBUTTONUP / WM_LBUTTONDBLCLK
                    self.rx_q.put("EVENT:TRAY_TOGGLE")
                elif ev == 0x0205:  # WM_RBUTTONUP
                    show_menu(hwnd)
                return 0
            if msg == 0x0010:  # WM_CLOSE
                u32.DestroyWindow(hwnd)
                return 0
            if msg == 0x0002:  # WM_DESTROY
                try:
                    if self.hotkey_ok:
                        u32.UnregisterHotKey(hwnd, 1)
                    if self.tray_ok:
                        s32.Shell_NotifyIconW(2, ctypes.byref(nid))  # NIM_DELETE
                except Exception:
                    pass
                u32.PostQuitMessage(0)
                return 0
            return u32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc_ref = WNDPROC(wnd_proc)
        hinst = k32.GetModuleHandleW(None)
        cls_name = f"KarelStickyTray_{id(self)}"
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = cls_name
        u32.RegisterClassExW(ctypes.byref(wc))

        hwnd = u32.CreateWindowExW(0, cls_name, "KarelTray", 0, 0, 0, 0, 0, None, None, hinst, None)
        self.hwnd = hwnd
        if hwnd:
            hicon = None
            if self.ico_path and os.path.isfile(self.ico_path):
                hicon = u32.LoadImageW(None, self.ico_path, 1, 16, 16, 0x0010)
            if not hicon:
                hicon = u32.LoadIconW(None, ctypes.cast(32512, _wt.LPCWSTR))
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = hwnd
            nid.uID = 1
            nid.uFlags = 1 | 2 | 4  # NIF_MESSAGE | NIF_ICON | NIF_TIP
            nid.uCallbackMessage = WM_TRAY
            nid.hIcon = hicon
            nid.szTip = "Karel de Koala (Ctrl+Alt+K)"
            self.tray_ok = bool(s32.Shell_NotifyIconW(0, ctypes.byref(nid)))
            if self.register_hotkey:
                self.hotkey_ok = bool(u32.RegisterHotKey(hwnd, 1, 0x4003, 0x4B) or u32.RegisterHotKey(hwnd, 1, 0x0003, 0x4B))
        self._ready.set()

        if hwnd:
            msg = _wt.MSG()
            while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                u32.TranslateMessage(ctypes.byref(msg))
                u32.DispatchMessageW(ctypes.byref(msg))

    def stop(self):
        if os.name == "nt" and self.hwnd:
            try:
                ctypes.windll.user32.PostMessageW(self.hwnd, 0x0010, 0, 0)
            except Exception:
                pass


def sync_hardware_state(app):
    """Push Karel's current mood/status state to the RP2350 NeoPixel over USB serial."""
    import datetime
    hr = datetime.datetime.now().hour
    if app.auto_paused or app.tray_hidden:
        app.ser.send("STATE:QUIET")
    elif app.focus_active and app.focus_phase == "focus":
        app.ser.send("STATE:STUDY")
    elif app.disco_ticks > 0 or app.state == "DANCE":
        app.ser.send("STATE:PARTY")
    elif app.hyper_ticks > 0:
        app.ser.send("STATE:HYPER")
    elif app.state == "SLEEP" or (hr >= 23 and app.act_ticks == 0):
        app.ser.send("STATE:SLEEP")
    elif app.d.get("hunger", 100) < 25:
        app.ser.send("STATE:HUNGRY")
    else:
        app.ser.send("STATE:HAPPY")


def drain_serial_events(app, minigame_catch_cls):
    """Drain queued hardware, tray, hotkey, and session events on Tk's main thread."""
    while not app.rx_q.empty():
        ev = app.rx_q.get_nowait()
        if app.mg and app.mg.running:
            if ev == "EVENT:PET":
                app.mg.nudge(-28)
                app.mg.action()
            elif ev in ("EVENT:FEED", "EVENT:COFFEE", "EVENT:GIFT"):
                app.mg.nudge(28)
            continue
        if ev == "EVENT:PET":
            app.pet()
        elif ev == "EVENT:FEED":
            app.feed()
        elif ev == "EVENT:COFFEE":
            app.coffee()
        elif ev == "EVENT:MINIGAME":
            app.open_game(minigame_catch_cls)
        elif ev in ("EVENT:RST_BOOP", "EVENT:GIFT"):
            if app.tray_hidden:
                app.wake_from_tray()
            app.hardware_boop()
        elif ev == "EVENT:TOGGLE_KAREL":
            app.wake_from_tray() if app.tray_hidden else app.trigger_dive_close("quit")
        elif ev == "EVENT:TRAY_TOGGLE":
            app.wake_from_tray() if app.tray_hidden else app.trigger_dive_close("tray")
        elif ev == "EVENT:OPEN_HUB":
            if app.tray_hidden:
                app.wake_from_tray()
            app.open_hub(0)
        elif ev == "EVENT:QUIT_NOW":
            app._finalize_quit() if app.tray_hidden else app.trigger_dive_close("quit")
        elif ev == "EVENT:SHUTDOWN_SAVE":
            app.sm.save(app.d, force=True)
        elif ev == "EVENT:DISCO":
            app.trigger_konami()
        elif ev == "EVENT:WASH":
            app.wash()


def step_umbrella_fall(app):
    """Animate gentle Sticky umbrella glide down to taskbar when perched window vanishes."""
    app.state = "UMBRELLA"
    app.wy = min(float(app.ground_y()), app.wy + 2.6)
    app.wx = max(app.min_x(), min(app.max_x(), app.wx + math.sin(app.frame_idx * 0.22) * 1.15))
    if app.wy >= app.ground_y() - 0.5:
        app.wy = float(app.ground_y())
        app.umbrella_fall = False
        app.roam_wait = 45
        app.jump_vy = -4.5
        app._spawn_particles("STAR", 4)
