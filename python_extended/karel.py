#!/usr/bin/env python3
"""Karel de Koala — Complete Extended Desktop Companion for Sticky (RP2350 SuperMini)."""

import datetime
import math
import os
import queue
import random
import sys
import time
import tkinter as tk

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from karel_anims import ANIM_DIV, DESKTOP_IDLE_ACTS  # noqa: E402
from karel_assets import (  # noqa: E402, F401
    COMPANION_SPRITES, PALETTE, SKINS, SPRITES, WARDROBE_ITEMS, apply_accessories,
)
from karel_audio import MUSIC_TRACKS, SoundEngine  # noqa: E402, F401
from karel_data import (  # noqa: E402, F401
    ACHIEVEMENTS, COFFEE_QUOTES, COOLDOWNS, COMMITTEES, COMPANIONS, FEED_QUOTES,
    FOOD_SHOP, HYPER_QUOTES, INGREDIENTS, LOOT_TABLE, NIGHT_QUOTES, PET_QUOTES,
    QUEST_POOL, QUOTES, RECIPES, ROAM_QUOTES, TITLES, TOYS, TRIVIA_QUESTIONS,
    UPGRADES, daily_campus_event, generate_daily_quests, level_from_xp,
    seasonal_campus_event, title_for_level,
)
from karel_games import (  # noqa: E402, F401
    MiniGame2048, MiniGameBugSmash, MiniGameCatch, MiniGameFlappy,
    MiniGameMemory, MiniGameRPG, MiniGameRhythm, MiniGameSnake, MiniGameWindow,
)
from karel_games_extra import MiniGameGans, MiniGameKoala  # noqa: E402, F401
from karel_hub import KarelHub  # noqa: E402
from karel_i18n import (  # noqa: E402
    coin_u, lang_of, pick_quote, tr, tr_ach, tr_cooldown, tr_item, tr_title, trf,
)
from karel_sync import (  # noqa: E402, F401
    SaveManager, SerialBridge, _has_marker_or_label, default_save,
    find_karel_drive, get_work_area, start_singleton_listener, try_signal_existing,
)
from karel_world import (  # noqa: E402
    IS_MAC, SpriteCache, WinTrayBridge, apply_window_icon, calc_coins, calc_xp, committee_execute,
    detect_fullscreen_or_meeting, drain_serial_events, draw_speech_bubble, fish_luck_bonus,
    focus_complete, focus_start, focus_stop, gacha_spin, get_foreground_ledge,
    get_virtual_bounds, init_pet_window, karel_metrics, open_trivia_dialog, pick_roam_target,
    popup_context_menu, prestige_activate, quiet_apply, render_alpha_grid_photo, roam_speed_mult,
    set_win_app_id, spawn_particles, spawn_prop, stat_decay_factors,
    step_and_draw_props, step_particles, step_umbrella_fall, sync_hardware_state, window_hwnd,
)

TKEY = "systemTransparent" if IS_MAC else "#010203"
BG = "#12141B"
CARD = "#1B1F2A"
RED = "#C41E25"
GREEN = "#3ECF8E"
GOLD = "#F5C451"
FG = "#F2F5FA"
MUTED = "#98A2B8"
UI_FONT = "Segoe UI" if os.name == "nt" else ("Helvetica Neue" if IS_MAC else "DejaVu Sans")
FONT = "Consolas" if os.name == "nt" else ("Menlo" if IS_MAC else "DejaVu Sans Mono")

SCALE, PX, CW, CH, OX, OY = karel_metrics(3)
KONAMI = ["up", "up", "down", "down", "left", "right", "left", "right", "b", "a"]


class KarelApp:
    """Main transparent always-on-top desktop pet & companion coordinator."""

    def __init__(self, root=None):
        set_win_app_id()
        self.r = root or tk.Tk()
        self.r.title("Karel de Koala")
        cbg = init_pet_window(self, TKEY, BG)

        self.sw = self.r.winfo_screenwidth()
        self.sh = self.r.winfo_screenheight()
        self.wl, self.wt, self.wr, self.wb = get_work_area(self.sw, self.sh)

        self.sm = SaveManager()
        self.d, greeting = self.sm.load()
        if self.lang() == "en":
            self.r.title("Karel the Koala")
        apply_window_icon(self.r, self, tk_mod=tk, is_root=True)
        ev = daily_campus_event(datetime.date.today().isoformat())
        self.campus_title, self.campus_buff = ev[0], ev[1]
        self.campus_tag = ev[2] if len(ev) > 2 else ""
        sev = seasonal_campus_event(datetime.date.today().isoformat())
        self.seasonal_title, self.seasonal_buff, self.seasonal_tag = sev
        self.focus_active = False
        self.focus_phase = "focus"
        self.focus_total = 0
        self.focus_rem = 0
        self.focus_last_ts = time.monotonic()
        self.auto_paused = False
        self._quiet_reason = ""
        self._pre_quiet_pos = None
        self.snd = SoundEngine()
        self.snd.voice_on = bool(self.d.get("voice_on", True))
        self.snd.set_sfx_volume(self.d.get("sfx_vol", 0.75))
        self.snd.set_bgm_volume(self.d.get("bgm_vol", 0.65), restart=False)
        if self.d.get("music_track", "off") != "off":
            self.snd.set_music(self.d["music_track"])
        self.rx_q = queue.Queue()
        self.ser = SerialBridge(self.rx_q)
        self.sprite_cache = SpriteCache()
        self.props = []
        self._ledge = None
        self._ledge_ticks = 0
        self.hub = KarelHub(self)
        self.scale, self.px, self.cw, self.ch, self.ox, self.oy = karel_metrics(self.d.get("karel_scale", 3))
        self._last_auto_say = 0.0

        self.cv = tk.Canvas(self.r, width=self.cw, height=self.ch, bg=cbg, highlightthickness=0)
        self.cv.pack()

        self.state = "IDLE"
        self.frame_idx = 0
        self.act_ticks = 0
        self.disco_ticks = 0
        self.hyper_ticks = 0
        self.bubble = ""
        self.bubble_ticks = 0
        self.particles = []
        self.coffee_times = []
        self.nose_clicks = []
        self.k_buf = []
        self.usb_start = time.time()
        self.mg = None
        self.trivia_win = None
        self._photo_cache = None
        self._cp_cache = None

        self.wx = float(self.wr - self.cw - 40)
        self.wy = float(self.ground_y())
        self.jump_y = 0.0
        self.jump_vy = 0.0
        self.roam_tx = self.wx
        self.roam_ty = self.wy
        self.roam_wait = random.randint(90, 150)
        self.roam_ticks = 0
        self.last_dx = 1
        self.dragging = False
        self.flying = False
        self.umbrella_fall = False
        self.fling_vx = 0.0
        self.fling_vy = 0.0
        self._drag_off = (0, 0)
        self._drag_start = (0, 0)
        self._drag_hist = []
        self.climbing = False
        self.climb_step = 0
        self.climb_msg = ""
        self.closing = False
        self.closing_step = 0
        self._close_start_y = self.wy
        self.tray_hidden = False
        self._dive_mode = "quit"
        self.tray = WinTrayBridge(self.rx_q, getattr(self, "_icon_ico", ""), self.lang, lambda: self.sm.save(self.d))
        self.r.protocol("WM_DELETE_WINDOW", self.quit_app)

        self._bind_events()
        self._check_time_eggs()
        self.trigger_climb(greeting)
        self._loop()

    def min_x(self):
        return self.wl - self.ox + 10

    def max_x(self):
        return self.wr - self.ox - self.px - 10

    def min_y(self):
        return self.wt - self.oy + 8

    def ground_y(self):
        return self.wb - (self.oy + self.px)

    def _bind_events(self):
        self.cv.bind("<ButtonPress-1>", self._on_press)
        self.cv.bind("<B1-Motion>", self._on_drag)
        self.cv.bind("<ButtonRelease-1>", self._on_release)
        self.cv.bind("<Double-Button-1>", lambda e: self.pet())
        self.cv.bind("<Button-3>", self._show_menu)
        self.cv.bind("<Button-2>", self._show_menu)
        self.cv.bind("<Control-Button-1>", self._show_menu)
        self.r.bind("<KeyPress>", self._on_key)

    def _on_key(self, e):
        k = e.keysym.lower()
        self.k_buf.append(k)
        self.k_buf = self.k_buf[-len(KONAMI):]
        if self.k_buf == KONAMI:
            self.k_buf = []
            self.trigger_konami()

    def _on_press(self, e):
        if self.closing or (IS_MAC and (e.state & 0x4)):
            return
        self.r.focus_force()
        self.dragging = True
        self.flying = False
        self.umbrella_fall = False
        self.climbing = False
        self.jump_y = 0.0
        self._drag_off = (e.x, e.y)
        self._drag_start = (e.x_root, e.y_root)
        self._drag_hist = [(e.x_root, e.y_root, time.time())]

    def _on_drag(self, e):
        if not self.dragging:
            return
        self.state = "JETPACK"
        vx0, vy0, vx1, vy1 = get_virtual_bounds(self.sw, self.sh)
        self.wx = max(vx0 - self.ox + 4, min(vx1 - self.ox - self.px - 4, e.x_root - self._drag_off[0]))
        self.wy = max(vy0 - self.oy + 4, min(vy1 - (self.oy + self.px), e.y_root - self._drag_off[1]))
        self._drag_hist.append((e.x_root, e.y_root, time.time()))
        if len(self._drag_hist) > 6:
            self._drag_hist = self._drag_hist[-6:]
        self._place_win()

    def _on_release(self, e):
        if not self.dragging:
            return
        self.dragging = False
        self.wl, self.wt, self.wr, self.wb = get_work_area(self.sw, self.sh, (e.x_root, e.y_root))
        self.wx = max(self.min_x(), min(self.max_x(), self.wx))
        self.wy = max(self.min_y(), min(self.ground_y(), self.wy))
        moved = math.hypot(e.x_root - self._drag_start[0], e.y_root - self._drag_start[1])
        if moved < 6:
            sx = (e.x - self.ox) // self.scale
            sy = (e.y - self.oy) // self.scale
            if 13 <= sx <= 18 and 12 <= sy <= 16:
                self._nose_click()
            elif self.act_ticks == 0 and self.state != "SLEEP":
                hr = datetime.datetime.now().hour
                cat, pool = ("night", NIGHT_QUOTES) if 0 <= hr < 5 else ("idle", QUOTES)
                self.say(pick_quote(self.lang(), cat, pool), chirp=True)
            return

        if len(self._drag_hist) >= 2:
            x0, y0, t0 = self._drag_hist[0]
            x1, y1, t1 = self._drag_hist[-1]
            dt = max(0.02, t1 - t0)
            vx, vy = (x1 - x0) / (dt * 20.0), (y1 - y0) / (dt * 20.0)
            if math.hypot(vx, vy) > 8.5:
                self.flying = True
                self.fling_vx = max(-38.0, min(38.0, vx))
                self.fling_vy = max(-38.0, min(28.0, vy))
                self.d["total_throws"] = self.d.get("total_throws", 0) + 1
                self.unlock("Vliegende Koala")
                self.say(self._t("fling"), 40)
                self.snd.jump()

    def _nose_click(self):
        now = time.time()
        self.nose_clicks = [t for t in self.nose_clicks if now - t < 4.5] + [now]
        if len(self.nose_clicks) >= 7:
            self.nose_clicks = []
            self.snd.sneeze()
            self._set_action("SNEEZE", 24)
            self._spawn_particles("SNEEZE", 12)
            self.say(self._t("sneeze"), 75)
            self.unlock("Stof-allergie")

    def _place_win(self):
        self.r.geometry(f"{self.cw}x{self.ch}+{int(round(self.wx))}+{int(round(self.wy + self.jump_y))}")

    def trigger_climb(self, greeting=None):
        """Animate Karel climbing up smoothly from behind the Windows taskbar."""
        self.wl, self.wt, self.wr, self.wb = get_work_area(self.sw, self.sh, (self.wx + self.cw // 2, self.wy + self.ch // 2))
        self.flying = False
        self.umbrella_fall = False
        self.jump_y = 0.0
        self.wy = float(self.ground_y())
        self.wx = max(self.min_x(), min(self.max_x(), self.wx))
        self.climbing = True
        self.climb_step = 0
        self.climb_msg = greeting or self._t("climb_done")
        self.roam_tx = self.wx
        self.roam_ty = self.wy
        self.roam_wait = 95
        self.say(self._t("climb_start"), 28)

    def wake_from_tray(self, msg=None):
        """Restore Karel from system tray or Dock sleep and climb back onto the desktop."""
        if self.tray_hidden:
            self.tray_hidden = False
            self.r.deiconify()
            self.r.attributes("-topmost", True)
            if IS_MAC:
                try:
                    self.r.attributes("-transparent", True)
                except Exception:
                    pass
        self.trigger_climb(msg or self._t("dock_wake" if IS_MAC else "tray_wake"))

    def trigger_dive_close(self, mode="quit"):
        """Wave goodbye and dive behind taskbar (mode='quit' exits, 'tray' sleeps)."""
        if self.closing:
            return
        self._dive_mode = mode
        self.closing = True
        self.closing_step = 0
        self.climbing = False
        self.flying = False
        self.umbrella_fall = False
        self.dragging = False
        self.jump_y = 0.0
        self._close_start_y = self.wy
        self.act_ticks = 0
        msg_k = ("dock_sleep" if IS_MAC else "tray_sleep") if mode == "tray" else "dive_start"
        self.say(self._t(msg_k), 44, chirp=True)
        self._spawn_particles("HEART", 4)
        self.snd.dive_bye()

    def play_trick(self, st, msg="", ticks=44):
        """Play any showcase animation or trick cleanly on demand."""
        if self.closing:
            return
        self.climbing = False
        self._set_action(st, ticks)
        if msg:
            self.say(msg, max(35, ticks), chirp=True)
        self._spawn_particles("STAR", 5)

    def _render_grid_photo(self, mat, size, scale, clip_rows=None):
        return render_alpha_grid_photo(tk, mat, size, scale, PALETTE, clip_rows=clip_rows)

    def _render_photo(self, st, f_idx, scale=None, clip_rows=32):
        sc = self.scale if scale is None else scale
        frames = SPRITES.get(st, SPRITES["IDLE"])
        fi = (f_idx // ANIM_DIV.get(st, 2)) % len(frames)
        raw = frames[fi]
        d = self.d
        hr = datetime.datetime.now().hour
        tr = 0 <= hr < 4
        vm = datetime.datetime.now().weekday() == 4 and hr >= 16
        eq = d.get("equipped") or []
        wid = eq[0] if eq else ""
        skin = d.get("skin", "classic")
        key = (sc, clip_rows, skin, st, fi, wid, tr, vm)

        def _build():
            mat = apply_accessories(raw, st, d.get("level", 1), False, False, tr, vm, eq=eq, skin=skin)
            return self._render_grid_photo(mat, 32, sc, clip_rows=clip_rows)

        return self.sprite_cache.get_karel(key, _build)

    def render_portrait(self, scale=2):
        """Return cached current IDLE Karel PhotoImage for UI headers."""
        return self._render_photo("IDLE", 0, scale=scale)

    def mg_sprite(self, data):
        self.d = data
        self._mg_ref = self._render_photo("IDLE", 0, scale=2)
        return self._mg_ref

    def _xp(self, base, *tags):
        return calc_xp(base, self.d.get("equipped"), getattr(self, "campus_tag", ""), tags, getattr(self, "seasonal_tag", ""))

    def _coins(self, base, *tags):
        return calc_coins(base, self.d.get("equipped"), getattr(self, "campus_tag", ""), tags, getattr(self, "seasonal_tag", ""))

    def lang(self):
        return lang_of(self.d)

    def _t(self, key, **kw):
        return trf(self.lang(), key, **kw)

    def set_language(self, code):
        c = "en" if code == "en" else "nl"
        self.d["language"] = c
        self.r.title("Karel the Koala" if c == "en" else "Karel de Koala")
        self.say(trf(c, "lang_set"), 55)
        self.sm.save(self.d)
        self.hub.refresh()
        return c

    def toggle_language(self):
        return self.set_language("en" if self.lang() == "nl" else "nl")

    def say(self, text, ticks=60, chirp=False):
        if getattr(self, "auto_paused", False):
            return
        self.bubble = text
        self.bubble_ticks = ticks
        if chirp:
            self.snd.chirp()

    def cooldown_left(self, key):
        """Return remaining cooldown seconds (int) for action key, or 0 if ready."""
        cds = self.d.get("cooldowns") or {}
        rem = float(cds.get(key, 0.0)) - time.time()
        return max(0, int(math.ceil(rem))) if rem > 0.0 else 0

    def _use_cooldown(self, key):
        """Enforce action cooldown; return True if ready (and arm timer), else warn & False."""
        secs, reason = COOLDOWNS.get(key, (0, "Even geduld!"))
        if secs <= 0:
            return True
        if key == "coffee" and "koffie_pas" in self.d.get("upgrades", []):
            secs = max(12, secs // 2)
        rem = self.cooldown_left(key)
        if rem > 0:
            self.snd.cooldown()
            self.ser.send("EVENT:COOLDOWN")
            mins, s = divmod(rem, 60)
            t_str = f"{mins}m{s:02d}s" if mins else f"{s}s"
            lg = self.lang()
            self.say(trf(lg, "cooldown", reason=tr_cooldown(lg, key, reason), t=t_str), 50)
            return False
        self.d.setdefault("cooldowns", {})[key] = round(time.time() + secs, 2)
        return True

    def _spawn_particles(self, kind, count=6, label=None):
        spawn_particles(self.particles, kind, self.ox, self.oy, self.px, count=count, label=label, gold=GOLD)

    def unlock(self, name):
        achs = self.d.setdefault("unlocked_achievements", [])
        if name not in achs:
            achs.append(name)
            self.snd.unlock()
            self._spawn_particles("CONFETTI", 12)
            self.say(self._t("ach", title=tr_ach(self.lang(), name, "")[0]), 75)
            self.hub.refresh()

    def gain_xp(self, amount):
        if "overclock_2040" in self.d.get("upgrades", []):
            amount = int(math.ceil(amount * 1.3))
        pres = min(10, max(0, int(self.d.get("prestige", 0))))
        if pres > 0 and amount > 0:
            amount = int(math.ceil(amount * (1.0 + 0.15 * pres)))
        self.d["xp"] = int(self.d.get("xp", 0)) + int(amount)
        old_lvl = int(self.d.get("level", 1))
        new_lvl = level_from_xp(self.d["xp"])
        if new_lvl > old_lvl:
            self.d["level"] = new_lvl
            self.snd.levelup()
            self._set_action(random.choice(("BACKFLIP", "PARTY_HORN", "CELEBRATE")), 44)
            self._spawn_particles("CONFETTI", 18)
            ttl = tr_title(self.lang(), title_for_level(new_lvl))
            self.say(self._t("lvlup", lvl=new_lvl, title=ttl), 85)
            for req, ach in (
                (5, "Bestuurs-Karel"), (13, "Senior Koala"),
                (22, "Rector Karel"), (50, "Opperkoala"), (75, "Sticky Legende"),
            ):
                if new_lvl >= req:
                    self.unlock(ach)
        self.hub.refresh()

    def add_coins(self, amount, from_game=False):
        if from_game:
            amount = calc_coins(amount, self.d.get("equipped"), "", ("game_coins",), getattr(self, "seasonal_tag", ""))
            if "coin_magnet" in self.d.get("upgrades", []):
                amount = int(math.ceil(amount * 1.5))
        pres = min(10, max(0, int(self.d.get("prestige", 0))))
        if pres > 0 and amount > 0:
            amount = int(math.ceil(amount * (1.0 + 0.15 * pres)))
        self.d["coins"] = int(self.d.get("coins", 0)) + int(amount)
        if self.d["coins"] >= 1500:
            self.unlock("Munten-Verzamelaar")
        self.hub.refresh()
        return int(amount)

    def quest_bump(self, qid, val=1, max_mode=False):
        for q in self.d.get("quests", []):
            if q.get("id") == qid and not q.get("claimed"):
                q["cur"] = min(q["target"], max(q["cur"], int(val)) if max_mode else q["cur"] + int(val))
        self.hub.refresh()

    def _set_action(self, st, ticks=32):
        if not self.climbing:
            self.state = st
            self.act_ticks = ticks

    # --- Care & Fun Animations (all protected with balanced Sticky cooldowns) ---
    def feed(self):
        if not self._use_cooldown("feed"):
            return False
        self.d["hunger"] = min(100, self.d.get("hunger", 0) + 25)
        self.d["hygiene"] = max(0, self.d.get("hygiene", 90) - 3)
        self.d["total_feeds"] = self.d.get("total_feeds", 0) + 1
        self._set_action("EAT", 34)
        spawn_prop(self.props, "leaf", -24)
        self._spawn_particles("CRUMB", 6)
        xp = self._xp(6, "cook_xp")
        c = self.add_coins(self._coins(2, "cook_xp"))
        self._spawn_particles("FLOAT", 1, f"+{xp} XP +{c}{coin_u(self.lang())}")
        self.gain_xp(xp)
        self.quest_bump("feed", 1)
        self.snd.play_varied("eat")
        self.say(self._t("feed_ok", q=pick_quote(self.lang(), "feed", FEED_QUOTES), c=c))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def feed_item(self, item_id):
        inv = self.d.setdefault("inventory", {})
        meta = FOOD_SHOP.get(item_id) or RECIPES.get(item_id)
        if inv.get(item_id, 0) <= 0 or not meta:
            return False
        if not self._use_cooldown("feed_item"):
            return False
        inv[item_id] -= 1
        if inv[item_id] <= 0:
            del inv[item_id]
        for stat in ("hunger", "happiness", "energy", "caffeine"):
            if meta.get(stat):
                self.d[stat] = min(100, self.d.get(stat, 0) + meta[stat])
        is_caf = meta.get("caffeine", 0) > 0
        anim = meta.get("anim") or ("COFFEE" if is_caf else ("TOSTI" if "tosti" in item_id else "EAT"))
        self._set_action(anim, 38)
        spawn_prop(self.props, "coffee" if is_caf else ("tosti" if "tosti" in item_id else "leaf"), -24)
        self._spawn_particles("CRUMB", 8)
        xp = self._xp(max(5, int(meta["xp"] * 0.65)), "coffee_xp" if is_caf else "cook_xp")
        self._spawn_particles("FLOAT", 1, f"+{xp} XP")
        self.gain_xp(xp)
        self.quest_bump("coffee" if is_caf else "feed", 1)
        self.snd.coffee() if is_caf else self.snd.play_varied("eat")
        self.say(self._t("eat_item", name=tr_item(self.lang(), item_id, meta["name"])[0], xp=xp))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def coffee(self):
        if not self._use_cooldown("coffee"):
            return False
        self.d["caffeine"] = min(100, self.d.get("caffeine", 0) + 28)
        self.d["energy"] = min(100, self.d.get("energy", 0) + 18)
        if self.d.get("equipped") == ["horns"] or self.campus_tag == "coffee_xp":
            self.d["happiness"] = min(100, self.d.get("happiness", 80) + 8)
        self.d["total_coffees"] = self.d.get("total_coffees", 0) + 1
        now = time.time()
        self.coffee_times = [t for t in self.coffee_times if now - t < 120] + [now]
        self._set_action("COFFEE", 34)
        spawn_prop(self.props, "coffee", 26)
        xp = self._xp(9, "coffee_xp")
        self._spawn_particles("FLOAT", 1, f"+{xp} XP +2{coin_u(self.lang())}")
        self.gain_xp(xp)
        self.add_coins(2)
        self.quest_bump("coffee", 1)
        self.snd.coffee()
        if self.d["total_coffees"] >= 50:
            self.unlock("Koffie Sommelier")
        self.say(self._t("coffee_ok", q=pick_quote(self.lang(), "coffee", COFFEE_QUOTES), xp=xp))
        if len(self.coffee_times) >= 3:
            self.hyper_ticks = 95
            self.unlock("Cafeïne Overdosis")
            self.ser.send("STATE:HYPER")
            self.say(self._t("coffee_over"), 75)
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def pet(self):
        if not self._use_cooldown("pet"):
            return False
        hb = 25 if self.campus_tag == "happy_boost" else 20
        self.d["happiness"] = min(100, self.d.get("happiness", 0) + hb)
        self.d["total_pets"] = self.d.get("total_pets", 0) + 1
        self._set_action("LOVE" if self.d["happiness"] >= 95 else "PET", 32)
        spawn_prop(self.props, "heart", random.randint(-18, 18))
        self._spawn_particles("HEART", 7)
        self.ser.send("EVENT:HEART")
        base_xp = 9 if "disco_speaker" in self.d.get("upgrades", []) else 6
        self.gain_xp(self._xp(base_xp, "pet_xp"))
        self.add_coins(2)
        self.quest_bump("pet", 1)
        self.snd.play_varied("pet")
        self.say(pick_quote(self.lang(), "pet", PET_QUOTES))
        if self.d["total_pets"] >= 100:
            acc = self.d.setdefault("unlocked_accessories", [])
            if "crown" not in acc:
                acc.append("crown")
            self.unlock("100x Geknuffeld")
            self._spawn_particles("CONFETTI", 15)
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def wash(self):
        if not self._use_cooldown("wash"):
            return False
        self.d["hygiene"] = 100
        hb = 18 if self.d.get("equipped") == ["umbrella"] else 12
        self.d["happiness"] = min(100, self.d.get("happiness", 0) + hb)
        self.d["total_washes"] = self.d.get("total_washes", 0) + 1
        self._set_action("WASH", 40)
        self._spawn_particles("BUBBLE", 10)
        self.gain_xp(self._xp(8, "wash_bonus"))
        self.add_coins(3)
        self.quest_bump("wash", 1)
        self.unlock("Schoon & Fris")
        self.snd.wash()
        self.say(self._t("wash_ok"))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def nap_toggle(self):
        if self.state == "SLEEP":
            self.state = "STRETCH"
            self.act_ticks = 18
            self.say(self._t("nap_wake"))
        else:
            self.state = "SLEEP"
            self.act_ticks = 220
            self.snd.sleep()
            self.say(self._t("nap_sleep"))

    def dance(self):
        if not self._use_cooldown("dance"):
            return False
        self._set_action("DANCE", 48)
        spawn_prop(self.props, "note", -22)
        self._spawn_particles("NOTE", 8)
        base_xp = 11 if "disco_speaker" in self.d.get("upgrades", []) else 7
        self.d["happiness"] = min(100, self.d.get("happiness", 0) + 14)
        self.gain_xp(self._xp(base_xp, "dance_xp"))
        self.add_coins(2)
        self.quest_bump("dance", 1)
        self.snd.dance()
        self.say(self._t("dance_ok"))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def exercise(self):
        if not self._use_cooldown("exercise"):
            return False
        self._set_action("FLEX", 45)
        self._spawn_particles("SWEAT", 7)
        self.d["energy"] = min(100, self.d.get("energy", 0) + 15)
        self.d["happiness"] = min(100, self.d.get("happiness", 0) + 10)
        self.gain_xp(self._xp(8))
        self.add_coins(3)
        self.quest_bump("dance", 1)
        self.unlock("Sportieve Koala")
        self.snd.jump()
        self.say(self._t("ex_ok"))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def selfie(self):
        if not self._use_cooldown("selfie"):
            return False
        self._set_action("SELFIE", 38)
        self._spawn_particles("CONFETTI", 8)
        self.d["happiness"] = min(100, self.d.get("happiness", 0) + 10)
        self.gain_xp(self._xp(7))
        c = self.add_coins(3)
        self.quest_bump("selfie", 1)
        self.unlock("Almanak Fotomodel")
        self.snd.shop()
        self.say(self._t("selfie_ok", c=c))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def music_jam(self):
        if not self._use_cooldown("music_jam"):
            return False
        self._set_action(random.choice(("GUITAR", "DRUM")), 46)
        spawn_prop(self.props, "note", 22)
        self._spawn_particles("NOTE", 10)
        self.d["happiness"] = min(100, self.d.get("happiness", 0) + 16)
        base_xp = 12 if "disco_speaker" in self.d.get("upgrades", []) else 8
        self.gain_xp(self._xp(base_xp, "dance_xp"))
        c = self.add_coins(3)
        self.quest_bump("dance", 1)
        self.unlock("Rockster in De Vagant")
        self.snd.dance()
        self.say(self._t("jam_ok", c=c))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def cast_spell(self):
        if not self._use_cooldown("cast_spell"):
            return False
        self._set_action("WIZARD_CAST", 42)
        spawn_prop(self.props, "laser", 0)
        self._spawn_particles("MAGIC", 10)
        self.snd.magic()
        self.unlock("Magiër van het BBG")
        if random.random() < 0.5:
            c = self.add_coins(self._coins(random.randint(6, 11), "spell_bonus"))
            self.say(self._t("spell_c", c=c))
        else:
            self.d["energy"] = min(100, self.d.get("energy", 0) + 25)
            xp = self._xp(11, "spell_bonus")
            self.gain_xp(xp)
            self.say(self._t("spell_e", xp=xp))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def fish(self):
        """Go fishing from the taskbar edge and collect StickyDex treasures or ingredients."""
        if not self._use_cooldown("fish"):
            return False
        self.d["total_fish"] = self.d.get("total_fish", 0) + 1
        self._set_action("FISHING", 44)
        spawn_prop(self.props, "fish", 28)
        self._spawn_particles("BUBBLE", 6)
        self.snd.fish()
        self.quest_bump("fish", 1)
        self.unlock("Vis-Kampioen")

        lucky = "lucky_clover" in self.d.get("upgrades", [])
        luck_k = (1.5 if lucky else 1.0) * fish_luck_bonus(
            self.d.get("equipped"), getattr(self, "campus_tag", ""), getattr(self, "seasonal_tag", ""),
        )
        r = random.random() / max(1.0, luck_k)
        if r < 0.08:
            rarity = "Legendarisch"
        elif r < 0.28:
            rarity = "Episch"
        elif r < 0.62:
            rarity = "Zeldzaam"
        else:
            rarity = "Gewoon"
        pool = [item for item in LOOT_TABLE if item[2] == rarity] or LOOT_TABLE
        lid, lname, rty, val, _ = random.choice(pool)
        dex = self.d.setdefault("dex", {})
        is_new = lid not in dex
        dex[lid] = dex.get(lid, 0) + 1
        if random.random() < 0.48:
            ik = random.choice(list(INGREDIENTS.keys()))
            ing = self.d.setdefault("ingredients", {})
            ing[ik] = ing.get(ik, 0) + 1
        self.gain_xp(self._xp(12 if rty in ("Episch", "Legendarisch") else 6, "fish_luck"))
        if len(dex) >= 10:
            self.unlock("Schatzoeker")
        if len(dex) >= 20:
            self.unlock("Archivaris")
        if len(dex) >= len(LOOT_TABLE):
            self.unlock("Museumdirecteur")
        lg = self.lang()
        self.say(self._t("fish_ok", new=self._t("new_tag") if is_new else "",
                         name=tr_item(lg, lid, lname)[0], rar=tr(lg, rty), val=val), 75)
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def run_committee(self, cid):
        """Execute an interactive Sticky Committee mission on cooldown."""
        return committee_execute(self, cid, COMMITTEES, INGREDIENTS)

    def hardware_boop(self):
        """Triggered by USB-replug singleton handshake, optional RUN pin, or USR button."""
        if not self._use_cooldown("boop"):
            return False
        self.unlock("Hardware Boop")
        self.snd.boop()
        c = self.add_coins(random.randint(8, 16))
        ik = random.choice(list(INGREDIENTS.keys()))
        ing = self.d.setdefault("ingredients", {})
        ing[ik] = ing.get(ik, 0) + 1
        self.gain_xp(10)
        self._spawn_particles("CONFETTI", 12)
        inm = tr_item(self.lang(), ik, INGREDIENTS[ik]["name"])[0]
        self.trigger_climb(self._t("boop_msg", c=c, ing=inm))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def trigger_konami(self):
        self.disco_ticks = 115
        acc = self.d.setdefault("unlocked_accessories", [])
        if "shades" not in acc:
            acc.append("shades")
        self.d["equipped"] = ["shades"]
        self.unlock("Konami Koala")
        self._set_action("DANCE", 65)
        self._spawn_particles("CONFETTI", 16)
        self.ser.send("STATE:PARTY")
        self.snd.konami()
        self.say(self._t("konami"), 85)
        self.sm.save(self.d)
        self.hub.refresh()

    def _check_time_eggs(self):
        now = datetime.datetime.now()
        if 0 <= now.hour < 4:
            self.unlock("Nachtbraker")
        if now.weekday() == 4 and now.hour >= 16:
            self.unlock("Borrelbeest")

    def open_game(self, cls):
        if self.mg and self.mg.running:
            self.mg.close()
        self._set_action("GAMING", 45)
        self.mg = cls(self)

    # --- Economy, Crafting, Gacha, Looks & StickyDex ---
    def buy_food(self, fid):
        it = FOOD_SHOP.get(fid)
        if not it or self.d.get("coins", 0) < it["price"]:
            self.snd.buzz()
            return False
        self.d["coins"] -= it["price"]
        inv = self.d.setdefault("inventory", {})
        inv[fid] = inv.get(fid, 0) + 1
        self.unlock("Sticky Shopper")
        self.snd.shop()
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def buy_ingredient(self, iid):
        im = INGREDIENTS.get(iid)
        if not im or self.d.get("coins", 0) < im["price"]:
            self.snd.buzz()
            return False
        self.d["coins"] -= im["price"]
        ing = self.d.setdefault("ingredients", {})
        ing[iid] = ing.get(iid, 0) + 1
        self.snd.shop()
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def craft_recipe(self, rid):
        rec = RECIPES.get(rid)
        if not rec:
            return False
        ing = self.d.setdefault("ingredients", {})
        if not all(ing.get(ik, 0) >= qty for ik, qty in rec["ing"].items()):
            self.snd.buzz()
            self.say(self._t("no_ing"))
            return False
        if not self._use_cooldown("craft"):
            return False
        for ik, qty in rec["ing"].items():
            ing[ik] -= qty
            if ing[ik] <= 0:
                del ing[ik]
        inv = self.d.setdefault("inventory", {})
        inv[rid] = inv.get(rid, 0) + 1
        self.d["total_crafted"] = self.d.get("total_crafted", 0) + 1
        crafted = self.d.setdefault("crafted_recipes", [])
        if rid not in crafted:
            crafted.append(rid)
        self.unlock("Keukenprins")
        if len(crafted) >= 8:
            self.unlock("Alchemist")
        if len(crafted) >= 16:
            self.unlock("Tosti Chef-Kok")
        self.quest_bump("craft", 1)
        self._set_action("TOSTI", 34)
        spawn_prop(self.props, "tosti", -20)
        self.gain_xp(self._xp(12, "cook_xp"))
        self.snd.craft()
        self.say(self._t("cooked", name=tr_item(self.lang(), rid, rec["name"])[0]))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def play_toy(self, tid):
        toy = TOYS.get(tid)
        if not toy or self.d.get("coins", 0) < toy["price"]:
            self.snd.buzz()
            return False
        if not self._use_cooldown("play_toy"):
            return False
        self.d["coins"] -= toy["price"]
        self.d["happiness"] = min(100, self.d.get("happiness", 0) + 20)
        self.d["energy"] = min(100, self.d.get("energy", 0) + 15)
        self._set_action({"duckie": "PET", "laser": "EXERCISE", "mech_kb": "GAMING", "krant": "WAVE", "soldeer": "GAMING"}.get(tid, "JUMP"), 40)
        spawn_prop(self.props, {"duckie": "duckie", "laser": "laser"}.get(tid, "note"), -26)
        self.gain_xp(self._xp(14))
        self.snd.play_varied("pet")
        self.say(self._t("toy_ok", name=tr_item(self.lang(), tid, toy["name"])[0]))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def buy_upgrade(self, uid):
        up = UPGRADES.get(uid)
        ups = self.d.setdefault("upgrades", [])
        if not up or uid in ups or self.d.get("coins", 0) < up["price"]:
            self.snd.buzz()
            return False
        self.d["coins"] -= up["price"]
        ups.append(uid)
        self.unlock("Sticky Shopper")
        self.snd.levelup()
        self.say(self._t("up_ok", name=tr_item(self.lang(), uid, up["name"])[0]))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def spin_gacha(self):
        return gacha_spin(self, SKINS, WARDROBE_ITEMS, COMPANIONS, LOOT_TABLE)

    def sell_loot(self, lid):
        dex = self.d.get("dex", {})
        if dex.get(lid, 0) <= 0:
            return False
        item = next((x for x in LOOT_TABLE if x[0] == lid), None)
        if not item:
            return False
        dex[lid] -= 1
        c = self.add_coins(item[3])
        self.snd.shop()
        self.say(self._t("sold", name=tr_item(self.lang(), lid, item[1])[0], c=c))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def companion_action(self, cid):
        if cid not in COMPANIONS:
            return False
        cname, price, _, _ = COMPANIONS[cid]
        unlocked = self.d.setdefault("unlocked_companions", ["none"])
        if cid not in unlocked:
            if self.d.get("coins", 0) < price:
                self.snd.buzz()
                return False
            self.d["coins"] -= price
            unlocked.append(cid)
            self.unlock("Maatjes voor het Leven")
            if len(unlocked) >= 6:
                self.unlock("Dierentuin op Bureau")
            self.snd.levelup()
        self.d["companion"] = cid
        if cid != "none":
            self.say(self._t("comp_on", name=tr_item(self.lang(), cid, cname)[0]))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def wardrobe_action(self, wid):
        if wid not in WARDROBE_ITEMS:
            return False
        wname, price, _ = WARDROBE_ITEMS[wid]
        eq = self.d.setdefault("equipped", [])
        acc = self.d.setdefault("unlocked_accessories", [])
        free = (
            (wid == "scarf")
            or (wid == "hoodie" and self.d.get("level", 1) >= 4)
            or (wid == "crown" and self.d.get("level", 1) >= 8)
            or (wid in acc)
        )
        if not free:
            if self.d.get("coins", 0) < price:
                self.snd.buzz()
                return False
            self.d["coins"] -= price
            acc.append(wid)
            self.unlock("Sticky Shopper")
            if len(acc) >= 6:
                self.unlock("Stylist van de Kamer")
            self.snd.shop()
        wn = tr_item(self.lang(), wid, wname)[0]
        if wid in eq:
            self.d["equipped"] = []
            self.say(self._t("wear_off", name=wn))
        else:
            # Karel wears strictly 1 clothing/accessory item at a time.
            self.d["equipped"] = [wid]
            self.say(self._t("wear_on", name=wn))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def unequip_all(self):
        self.d["equipped"] = []
        self.say(self._t("unequip"))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def skin_action(self, sid):
        if sid not in SKINS:
            return False
        sname, price, _ = SKINS[sid]
        unlocked = self.d.setdefault("unlocked_skins", ["classic"])
        if sid not in unlocked:
            if self.d.get("coins", 0) < price:
                self.snd.buzz()
                return False
            self.d["coins"] -= price
            unlocked.append(sid)
            self.unlock("Sticky Shopper")
            self.snd.levelup()
        if len(unlocked) >= 5:
            self.unlock("Mode-Icoon")
        self.d["skin"] = sid
        self.say(self._t("skin_on", name=tr_item(self.lang(), sid, sname)[0]))
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def claim_quest(self, idx):
        qs = self.d.get("quests", [])
        if not (0 <= idx < len(qs)):
            return False
        q = qs[idx]
        if q.get("claimed") or q["cur"] < q["target"]:
            return False
        q["claimed"] = True
        self.gain_xp(q["xp"])
        self.add_coins(q["coins"])
        ing_k = q.get("ing")
        if ing_k in INGREDIENTS:
            ing = self.d.setdefault("ingredients", {})
            ing[ing_k] = ing.get(ing_k, 0) + 1
            inm = tr_item(self.lang(), ing_k, INGREDIENTS[ing_k]["name"])[0]
            msg = self._t("quest_ok", c=q["coins"], xp=q["xp"], ing=inm)
        else:
            msg = self._t("quest_plain", c=q["coins"], xp=q["xp"])
        self._set_action("CELEBRATE", 32)
        self.snd.levelup()
        self.say(msg)
        self.sm.save(self.d)
        self.hub.refresh()
        return True

    def open_trivia(self):
        if self.trivia_win and self.trivia_win.winfo_exists():
            self.trivia_win.lift()
            return False
        if not self._use_cooldown("trivia"):
            return False
        open_trivia_dialog(tk, self, TRIVIA_QUESTIONS, (BG, CARD, RED, GOLD, FG), UI_FONT)
        return True

    def set_music(self, track_id):
        self.snd.set_music(track_id)
        self.d["music_track"] = track_id
        self.sm.save(self.d)
        self.hub.refresh()

    def set_sfx_volume(self, vol):
        v = max(0.0, min(1.0, float(vol)))
        self.snd.set_sfx_volume(v)
        self.d["sfx_vol"] = round(v, 2)
        self.sm.mark_dirty()

    def set_bgm_volume(self, vol, restart=True):
        v = max(0.0, min(1.0, float(vol)))
        self.snd.set_bgm_volume(v, restart=restart)
        self.d["bgm_vol"] = round(v, 2)
        self.sm.mark_dirty()

    def set_roam_mode(self, mode):
        if mode in ("free", "cursor", "window", "park"):
            self.d["roam_mode"] = mode
            self.roam_wait = 0
            self.say(self._t(f"roam_{mode}"))
            self.sm.save(self.d)
            self.hub.refresh()

    def set_karel_scale(self, scale):
        """Resize Karel's sprite and floating window while keeping feet grounded."""
        s, px, cw, ch, ox, oy = karel_metrics(scale)
        old_foot_cx = self.wx + self.ox + self.px / 2.0
        old_foot_y = self.wy + self.oy + self.px
        self.scale, self.px, self.cw, self.ch, self.ox, self.oy = s, px, cw, ch, ox, oy
        self.d["karel_scale"] = s
        self.cv.config(width=cw, height=ch)
        self.wx = max(self.min_x(), min(self.max_x(), old_foot_cx - ox - px / 2.0))
        self.wy = max(self.min_y(), min(self.ground_y(), old_foot_y - oy - px))
        self._place_win()
        lbl = tr(self.lang(), {2: "Klein", 3: "Normaal", 4: "Groot", 5: "Reus"}[s])
        self.say(self._t("size_set", lbl=lbl, px=px), 55)
        self.sm.save(self.d)
        self.hub.refresh()

    def start_focus(self, mins=25):
        focus_start(self, mins)

    def stop_focus(self):
        focus_stop(self)

    def toggle_focus(self, mins=25):
        focus_stop(self) if self.focus_active else focus_start(self, mins)

    def complete_focus(self):
        focus_complete(self)

    def toggle_auto_quiet(self):
        nxt = not bool(self.d.get("auto_quiet_fullscreen", True))
        self.d["auto_quiet_fullscreen"] = nxt
        if not nxt:
            quiet_apply(self, "")
        self.say(self._t("auto_q", st=self._t("st_on" if nxt else "st_off")))
        self.sm.save(self.d)
        self.hub.refresh()

    def set_auto_quiet_state(self, reason):
        quiet_apply(self, reason)

    def do_prestige(self):
        return prestige_activate(self)

    def _try_roam_loot(self):
        bonus = 1.5 if "turbo_sneakers" in self.d.get("upgrades", []) else 1.0
        r = random.random()
        if r < 0.015 * bonus:
            coins = self._coins(random.randint(4, 10), "roam_coins")
            self.add_coins(coins)
            spawn_prop(self.props, "coin", 24)
            self._spawn_particles("COIN", 6)
            self._spawn_particles("FLOAT", 1, f"+{coins}{coin_u(self.lang())}")
            self.quest_bump("roam_loot", 1)
            self.snd.play_varied("coin")
            self.say(self._t("roam_c", c=coins), 65)
        elif r < 0.022 * bonus:
            ik = random.choice(list(INGREDIENTS.keys()))
            ing = self.d.setdefault("ingredients", {})
            ing[ik] = ing.get(ik, 0) + 1
            self.quest_bump("roam_loot", 1)
            self.snd.play_varied("coin")
            inm = tr_item(self.lang(), ik, INGREDIENTS[ik]["name"])[0]
            self.say(self._t("roam_i", name=inm), 65)

    def _own_hwnds(self):
        hw = {window_hwnd(self.r)}
        if getattr(self.hub, "win", None):
            hw.add(window_hwnd(self.hub.win))
        if self.trivia_win:
            hw.add(window_hwnd(self.trivia_win))
        hw.discard(0)
        return hw

    def _step_roam(self):
        if self.dragging:
            return
        if self.auto_paused:
            self.state = "IDLE"
            return
        if self.focus_active and self.focus_phase == "focus" and self.act_ticks == 0:
            self.state = "STUDY"
            return
        if self.flying:
            self.state = "JETPACK"
            self.wx += self.fling_vx
            self.wy += self.fling_vy
            self.fling_vy += 1.45
            self.fling_vx *= 0.985
            if self.wx <= self.min_x():
                self.wx = self.min_x()
                self.fling_vx = abs(self.fling_vx) * 0.65
                self.snd.bounce()
            elif self.wx >= self.max_x():
                self.wx = self.max_x()
                self.fling_vx = -abs(self.fling_vx) * 0.65
                self.snd.bounce()
            if self.wy <= self.min_y():
                self.wy = self.min_y()
                self.fling_vy = abs(self.fling_vy) * 0.65
            if self.wy >= self.ground_y():
                self.wy = float(self.ground_y())
                if abs(self.fling_vy) > 6.5:
                    self.fling_vy = -abs(self.fling_vy) * 0.55
                    self.snd.bounce()
                else:
                    self.flying = False
                    self.fling_vx = 0.0
                    self.fling_vy = 0.0
                    self._set_action("DIZZY", 22)
            return

        if self.umbrella_fall:
            step_umbrella_fall(self)
            return

        if self.jump_y < 0 or self.jump_vy < 0:
            self.jump_y += self.jump_vy
            self.jump_vy += 1.35
            if self.jump_y >= 0:
                self.jump_y = 0.0
                self.jump_vy = 0.0

        if self.state == "SLEEP" or self.act_ticks > 0 or self.hyper_ticks > 0:
            if self.hyper_ticks > 0:
                self.wx = max(self.min_x(), min(self.max_x(), self.wx + random.choice([-7, 7])))
            return

        mode = self.d.get("roam_mode", "free")
        if mode == "park":
            self.state = "MUSIC" if self.snd.track != "off" else "IDLE"
            return

        if mode == "cursor":
            try:
                px = max(self.min_x(), min(self.max_x(), self.r.winfo_pointerx() - self.cw // 2))
                py = max(self.min_y(), min(self.ground_y(), self.r.winfo_pointery() - (self.oy + self.px // 2)))
                dx, dy = px - self.wx, py - self.wy
                dist = math.hypot(dx, dy)
                if dist > 110:
                    spd = 4.4 * min(1.25, roam_speed_mult(self.d.get("upgrades", []), self.d.get("equipped")))
                    self.wx += (dx / dist) * spd
                    self.wy += (dy / dist) * spd
                    self.last_dx = -1 if dx < 0 else 1
                    self.state = "RUN_LEFT" if dx < 0 else "RUN_RIGHT"
                else:
                    self.state = "IDLE"
            except Exception:
                self.state = "IDLE"
            return

        if mode == "window":
            self._ledge_ticks += 1
            if self._ledge_ticks % 12 == 1 or not self._ledge:
                self._ledge = get_foreground_ledge(self._own_hwnds(), self.px, self.wl, self.wt, self.wr, self.wb)
            if self._ledge:
                lx0, lx1, lwy = self._ledge
                tx0 = max(self.min_x(), float(lx0 - self.ox))
                tx1 = max(tx0, min(self.max_x(), float(lx1 - self.ox - self.px)))
                self.roam_ty = max(self.min_y(), min(self.ground_y(), float(lwy - (self.oy + self.px))))
                if not (tx0 <= self.roam_tx <= tx1) or abs(self.roam_tx - self.wx) < 10:
                    if self.roam_wait <= 0:
                        self.roam_wait = random.randint(110, 220)
                        self.roam_tx = random.uniform(tx0, tx1)
            else:
                self.roam_ty = float(self.ground_y())
            if (not self._ledge and self.wy < self.ground_y() - 18) or self.roam_ty > self.wy + 28:
                self.umbrella_fall = True
                self.roam_wait = 0
                self.roam_ticks = 0
                self.act_ticks = 0
                self.say(self._t("umb_fall"), 42)
                return

        if self.roam_wait > 0:
            self.roam_wait -= 1
            if self.snd.track != "off":
                self.state = "MUSIC"
            elif self.d.get("happiness", 80) < 22 or self.d.get("hygiene", 90) < 20:
                self.state = "CRY"
            elif self.d.get("energy", 85) < 22:
                self.state = "YAWN"
            elif self.roam_wait % 55 == 28 and random.random() < 0.72:
                self._set_action(random.choice(DESKTOP_IDLE_ACTS), 24)
            else:
                self.state = "IDLE"
            return

        dx = self.roam_tx - self.wx
        dy = self.roam_ty - self.wy
        dist = math.hypot(dx, dy)
        self.roam_ticks += 1
        if dist < 10 or self.roam_ticks > 155:
            self.roam_ticks = 0
            self.roam_wait = random.randint(140, 310)
            self.roam_tx, self.roam_ty, self._ledge = pick_roam_target(
                mode, self._own_hwnds(), self._ledge,
                self.min_x(), self.max_x(), self.min_y(), self.ground_y(),
                self.ox, self.oy, self.px, (self.wl, self.wt, self.wr, self.wb),
            )
            self._try_roam_loot()
            r = random.random()
            if r < 0.04:
                self.jump_vy = -8.2
                self.state = "JUMP"
                self.snd.jump()
            elif r < 0.06 and self.wy >= self.ground_y() - 20 and self.cooldown_left("fish") == 0:
                self.fish()
            elif not self.bubble_ticks and r < 0.13 and time.time() - self._last_auto_say >= 38.0:
                self._last_auto_say = time.time()
                cat = "roam" if random.random() < 0.35 else "idle"
                self.say(pick_quote(self.lang(), cat, ROAM_QUOTES + QUOTES), 58)
            return

        spd = 2.2 * roam_speed_mult(self.d.get("upgrades", []), self.d.get("equipped"))
        self.wx += (dx / dist) * spd
        self.wy += (dy / dist) * spd
        self.last_dx = -1 if dx < 0 else 1
        self.state = "JUMP" if self.jump_y < -1 else ("WALK_LEFT" if dx < 0 else "WALK_RIGHT")
        if random.random() < 0.002 and self.jump_y == 0:
            self.jump_vy = -7.8

    def _draw_canvas(self):
        self.cv.delete("all")
        ox, oy, px, cw = self.ox, self.oy, self.px, self.cw
        if self.jump_y < -2 or self.flying:
            sw = max(14, int(px * 0.37 + self.jump_y * 0.4))
            self.cv.create_oval(cw // 2 - sw, oy + px - 4, cw // 2 + sw, oy + px + 4, fill="#111318", outline="")
        elif not self.climbing and not self.closing:
            ins = max(8, px // 5)
            self.cv.create_oval(ox + ins, oy + px - 3, ox + px - ins, oy + px + 3, fill="#181C26", outline="")

        if self.closing:
            if self.closing_step < 10:
                self._photo_cache = self._render_photo("DIVE_WAVE", self.closing_step)
            elif self.closing_step < 14:
                self._photo_cache = self._render_photo("DIVE_DOWN", 0)
            else:
                sub = self.closing_step - 13
                vis_rows = max(0, 32 - int(sub * 2.4))
                df = min(3, sub // 3)
                self._photo_cache = self._render_photo("DIVE_DOWN", df, clip_rows=vis_rows)
                self.cv.create_line(ox + 6, oy + px - 2, ox + px - 6, oy + px - 2, fill="#5C6370", width=2)
        elif self.climbing:
            if self.climb_step < 4:
                self._photo_cache = self._render_photo("PEEK", self.climb_step)
            else:
                vis_rows = min(32, 6 + (self.climb_step - 3) * 2)
                self._photo_cache = self._render_photo("CLIMB", self.climb_step, clip_rows=vis_rows)
            self.cv.create_line(ox + 6, oy + px - 2, ox + px - 6, oy + px - 2, fill="#5C6370", width=2)
        else:
            st = self.state
            if st == "IDLE":
                if self.hyper_ticks > 0:
                    st = "HYPER"
                elif datetime.datetime.now().hour >= 23 and self.act_ticks == 0:
                    st = "SLEEP"
                elif self.d.get("hunger", 100) < 25:
                    st = "HUNGRY"
                elif time.time() - self.usb_start >= 900 and self.sm.connected:
                    st = "STUDY"
            self._photo_cache = self._render_photo(st, self.frame_idx)

        self.cv.create_image(ox, oy, anchor="nw", image=self._photo_cache)

        cp = self.d.get("companion", "none")
        if not self.climbing and cp in COMPANION_SPRITES:
            c_idx = (self.frame_idx // 3) % len(COMPANION_SPRITES[cp])
            cf = COMPANION_SPRITES[cp][c_idx]
            c_sc = max(2, self.scale)
            self._cp_cache = self.sprite_cache.get_comp((c_sc, cp, c_idx), lambda: self._render_grid_photo(cf, 10, c_sc))
            cx = (ox - 10 * c_sc - 6) if self.last_dx >= 0 else (ox + px + 6)
            self.cv.create_image(cx, oy + px - 10 * c_sc - 2, anchor="nw", image=self._cp_cache)

        if self.props:
            step_and_draw_props(self.cv, self.props, ox + px // 2, oy + px - 6, self.scale)

        for p in self.particles:
            self.cv.create_text(p[0], p[1], text=p[4], fill=p[5], font=(FONT, 10, "bold"))

        if self.bubble and self.bubble_ticks > 0:
            draw_speech_bubble(self.cv, self.bubble, cw, oy, RED, UI_FONT)

    def _sync_hardware(self):
        sync_hardware_state(self)

    def _drain_serial(self):
        drain_serial_events(self, MiniGameCatch)

    def _loop(self):
        self.frame_idx += 1
        if self.frame_idx % 16 == 0:
            if self.d.get("auto_quiet_fullscreen", True):
                self.set_auto_quiet_state(detect_fullscreen_or_meeting(self._own_hwnds()))
            usb = self.sm.poll_usb()
            if usb == "off":
                self.say(self._t("usb_off"), 75)
            elif usb == "on":
                self.usb_start = time.time()
                self.trigger_climb(self._t("usb_on"))
                self.sm.save(self.d)

        if self.focus_active:
            now_m = time.monotonic()
            if now_m - self.focus_last_ts >= 1.0:
                dt = int(now_m - self.focus_last_ts)
                self.focus_last_ts += dt
                self.focus_rem = max(0, self.focus_rem - dt)
                if self.focus_rem == 0:
                    self.complete_focus()

        self._drain_serial()

        if self.closing:
            self.closing_step += 1
            if self.closing_step <= 9:
                u = self.closing_step / 9.0
                self.wy = self._close_start_y + (self.ground_y() - self._close_start_y) * u
            elif self.closing_step <= 13:
                self.wy = float(self.ground_y())
                self.jump_y = -16.0 * math.sin((self.closing_step - 9) * math.pi / 4.0)
            else:
                self.wy = float(self.ground_y())
                self.jump_y = 0.0
                if self.closing_step == 15:
                    self._spawn_particles("STAR", 6)
            if self.closing_step >= 27:
                if self._dive_mode == "tray":
                    self.closing = False
                    self.tray_hidden = True
                    self.sm.save(self.d, force=True)
                    self.r.withdraw()
                else:
                    self._finalize_quit()
                    return
        elif self.climbing:
            self.climb_step += 1
            if self.climb_step >= 18:
                self.climbing = False
                self.jump_vy = -9.0
                self._set_action("BACKFLIP" if random.random() < 0.35 else "JUMP", 16)
                self.ser.send("EVENT:HEART")
                self.snd.coin()
                self._spawn_particles("HEART", 6)
                self.say(self.climb_msg, 75)
        elif not self.tray_hidden:
            self._step_roam()

        if not self.tray_hidden:
            self._place_win()

        if self.act_ticks > 0:
            self.act_ticks -= 1
            if self.act_ticks == 0 and self.state != "IDLE":
                if self.state == "SLEEP":
                    self.d["energy"] = min(100, self.d.get("energy", 0) + 30)
                self.state = "IDLE"
        if self.disco_ticks > 0:
            self.disco_ticks -= 1
        if self.hyper_ticks > 0:
            self.hyper_ticks -= 1
            if self.hyper_ticks % 28 == 0:
                self.say(pick_quote(self.lang(), "hyper", HYPER_QUOTES), 24)
        if self.bubble_ticks > 0:
            self.bubble_ticks -= 1

        if self.frame_idx % 65 == 0:
            up = set(self.d.get("upgrades", []))
            hunger_k, energy_k = stat_decay_factors(self.d.get("equipped"))
            changed = False
            if self.state == "SLEEP":
                self.d["energy"] = min(100, self.d.get("energy", 0) + 2)
                changed = True
            elif random.random() < (0.18 if "golden_bowl" in up else 0.30) * hunger_k:
                self.d["hunger"] = max(0, self.d.get("hunger", 80) - 1)
                changed = True
            if self.frame_idx % 130 == 0:
                if random.random() < (0.20 if "coffee_thermos" in up else 0.35) * energy_k:
                    self.d["energy"] = max(0, self.d.get("energy", 85) - 1)
                    changed = True
                if random.random() < (0.16 if "soap_dispenser" in up else 0.32):
                    self.d["hygiene"] = max(0, self.d.get("hygiene", 90) - 1)
                    changed = True
            if changed:
                self.sm.mark_dirty()
            self._check_time_eggs()
        if self.frame_idx % 80 == 0:
            self.sm.flush(self.d)

        step_particles(self.particles)

        self._sync_hardware()
        if not self.tray_hidden:
            self._draw_canvas()
        if not getattr(self, "_quit_done", False):
            self._loop_id = self.r.after(62, self._loop)

    def _show_menu(self, e):
        popup_context_menu(tk, self, e, CARD, FG, RED, UI_FONT, MUSIC_TRACKS)

    def _toggle_mute(self):
        m = self.snd.toggle_mute()
        self.say(self._t("mute_on" if m else "mute_off"))
        self.hub.refresh()

    def _toggle_voice(self):
        self.snd.voice_on = not self.snd.voice_on
        self.d["voice_on"] = self.snd.voice_on
        self.say(self._t("voice_on" if self.snd.voice_on else "voice_off"))
        self.sm.save(self.d)
        self.hub.refresh()

    def open_hub(self, tab=0):
        self.hub.open(tab)

    def _finalize_quit(self):
        if getattr(self, "_quit_done", False):
            return
        self._quit_done = True
        lid = getattr(self, "_loop_id", None)
        if lid:
            try:
                self.r.after_cancel(lid)
            except Exception:
                pass
            self._loop_id = None
        self.ser.send("STATE:BYE")
        self.sm.save(self.d, force=True)
        self.ser._stop = True
        if getattr(self, "tray", None):
            self.tray.stop()
        self.snd.close()
        self.hub.close()
        self.r.destroy()

    def quit_app(self, immediate=False):
        if immediate:
            self._finalize_quit()
        else:
            self.trigger_dive_close()

    def run(self):
        self.r.mainloop()


if __name__ == "__main__":
    if try_signal_existing(toggle=any(a in ("t", "-t", "--toggle") for a in sys.argv[1:])):
        sys.exit(0)
    app = KarelApp()
    start_singleton_listener(app.rx_q)
    app.run()
