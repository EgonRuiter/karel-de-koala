"""Karel de Koala — Sticky Studio Super-Hub Window (7 Tabs, Portrait, Perks, Sliders)."""

import os
import tkinter as tk

from karel_audio import MUSIC_TRACKS
from karel_data import (
    ACHIEVEMENTS, COMMITTEES, COMPANIONS, FOOD_SHOP, INGREDIENTS,
    LOOT_TABLE, RECIPES, TOYS, UPGRADES, title_for_level,
    xp_for_next_level,
)
from karel_games import (
    MiniGame2048, MiniGameBugSmash, MiniGameCatch, MiniGameFlappy,
    MiniGameMemory, MiniGameRPG, MiniGameRhythm, MiniGameSnake,
)
from karel_games_extra import MiniGameGans, MiniGameKoala
from karel_i18n import (
    coin_u, lang_of, tr, tr_ach, tr_arcade_row, tr_committee, tr_event,
    tr_item, tr_perk, tr_quest, tr_title,
)
from karel_wardrobe import OUTFIT_PERKS, SKINS, WARDROBE_ITEMS, get_outfit_perk
from karel_world import IS_MAC, KAREL_SIZES, apply_window_icon, make_flat_button

BG = "#12141B"
PANEL = "#171B26"
CARD = "#1B1F2A"
CARD2 = "#232837"
BORDER = "#2D3346"
TRACK = "#0F1218"
RED = "#C41E25"
RED_HOVER = "#DC2D35"
GREEN = "#3ECF8E"
GOLD = "#F5C451"
CYAN = "#56B6F7"
PINK = "#FF7597"
FG = "#F2F5FA"
MUTED = "#98A2B8"
DIM_BTN = "#2A3040"
UI_FONT = "Segoe UI" if os.name == "nt" else ("Helvetica Neue" if IS_MAC else "DejaVu Sans")
MONO = "Consolas" if os.name == "nt" else ("Menlo" if IS_MAC else "DejaVu Sans Mono")

TABS = (
    "Status & Audio",
    "Shop & Keuken",
    "Looks & Maatje",
    "Sticky BK",
    "Arcade (10)",
    "StickyDex (36)",
    f"Quests ({len(ACHIEVEMENTS)})",
)

ARCADE_LIST = (
    ("catch", "1. Eucalyptus & Coffee Catch", "Vang blaadjes & Sticky-bekers, ontwijk deadlines!", MiniGameCatch, "#2E7D32"),
    ("flappy", "2. Koala Flappy Hop", "Flap langs Uithof-obstakels door de windtunnel!", MiniGameFlappy, "#0277BD"),
    ("smash", "3. BBG Bug Smasher", "Plet productie-bugs op de Stickykamer voor de ALV begint!", MiniGameBugSmash, "#C41E25"),
    ("memory", "4. Sticky Code Memory 4x4", "Match alle 8 klassieke Informatica-symbolen!", MiniGameMemory, "#6A1B9A"),
    ("snake", "5. Sticky Code Snake", "Verzamel koffiebonen zonder je eigen staart te raken!", MiniGameSnake, "#1B5E20"),
    ("merge", "6. Merge Conflicts 2048", "Fuseer git-commits helemaal naar Sticky 2048!", MiniGame2048, "#EF6C00"),
    ("rhythm", "7. De Vagant Beat Drop", "Druk exact op de maat in De Vagant!", MiniGameRhythm, "#AD1457"),
    ("rpg", "8. BBG Dungeon Boss RPG", "Versla 5 eindbazen met Sticky combo-aanvallen!", MiniGameRPG, "#4527A0"),
    ("gans", "9. Uithof Ganzen Run", "Spring & buk voor boze Uithof-ganzen op pad naar BBG!", MiniGameGans, "#00838F"),
    ("koala", "10. Koala Server Rescue", "Verdedig de Koala-server tegen een DDoS-regen!", MiniGameKoala, "#B71C1C"),
)

RARITY_COLORS = {
    "Gewoon": MUTED,
    "Zeldzaam": CYAN,
    "Episch": "#C792EA",
    "Legendarisch": GOLD,
}


def _mix_hex(hex_col, amt=0.14):
    """Lighten a #RRGGBB hex color safely for hover feedback."""
    try:
        h = hex_col.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r = min(255, int(r + (255 - r) * amt))
        g = min(255, int(g + (255 - g) * amt))
        b = min(255, int(b + (255 - b) * amt))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_col


class KarelHub:
    """7-tab Sticky Studio Super-Hub with live portrait, Canvas bars, sliders & cooldowns."""

    def __init__(self, app):
        self.app = app
        self.win = None
        self.tab = 0
        self.body = None
        self.canvas = None
        self.head_lbl = None
        self.coin_lbl = None
        self.coin_sub_lbl = None
        self.usb_lbl = None
        self.perk_lbl = None
        self.avatar_lbl = None
        self.xp_cvs = None
        self._hero_img = None
        self.focus_lbl = None
        self.tab_btns = []
        self._cd_widgets = []
        self._timer_id = None
        self._bgm_after = None
        self.last_gacha = None

    def open(self, tab=0):
        """Open the Hub or raise it to focus on the selected tab."""
        self.tab = max(0, min(len(TABS) - 1, int(tab)))
        if self.win and self.win.winfo_exists():
            self.win.lift()
            self.refresh()
            return
        w = tk.Toplevel(self.app.r)
        w.title(tr(lang_of(self.app), "Karel de Koala — Sticky BK Hub"))
        w.configure(bg=BG)
        w.geometry("740x670")
        w.minsize(680, 540)
        w.attributes("-topmost", True)
        apply_window_icon(w, self.app, tk)
        w.protocol("WM_DELETE_WINDOW", self.close)
        self.win = w
        w.lift()
        w.focus_force()

        # Top crimson accent + Hero Header
        tk.Frame(w, bg=RED, height=3).pack(fill="x")
        hdr = tk.Frame(w, bg=PANEL, padx=14, pady=10, highlightbackground=BORDER, highlightthickness=1)
        hdr.pack(fill="x")

        av_box = tk.Frame(hdr, bg=CARD2, padx=3, pady=3, highlightbackground=BORDER, highlightthickness=1)
        av_box.pack(side="left", padx=(0, 12))
        self.avatar_lbl = tk.Label(av_box, bg=CARD2)
        self.avatar_lbl.pack()

        mid = tk.Frame(hdr, bg=PANEL)
        mid.pack(side="left", fill="both", expand=True)
        top_r = tk.Frame(mid, bg=PANEL)
        top_r.pack(fill="x")
        self.head_lbl = tk.Label(top_r, text="", bg=PANEL, fg=FG, font=(UI_FONT, 11, "bold"), anchor="w")
        self.head_lbl.pack(side="left", fill="x", expand=True)
        self.usb_lbl = tk.Label(top_r, text="", bg=PANEL, fg=GREEN, font=(MONO, 8, "bold"))
        self.usb_lbl.pack(side="right")

        self.xp_cvs = tk.Canvas(mid, height=10, bg=PANEL, highlightthickness=0)
        self.xp_cvs.pack(fill="x", pady=(6, 4))
        self.perk_lbl = tk.Label(mid, text="", bg=PANEL, fg=MUTED, font=(UI_FONT, 8), anchor="w")
        self.perk_lbl.pack(fill="x")

        right = tk.Frame(hdr, bg=CARD2, padx=10, pady=6, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", padx=(12, 0))
        self.coin_lbl = tk.Label(right, text="0 m", bg=CARD2, fg=GOLD, font=(MONO, 12, "bold"))
        self.coin_lbl.pack()
        self.coin_sub_lbl = tk.Label(right, text="STICKY MUNTEN", bg=CARD2, fg=MUTED, font=(UI_FONT, 7, "bold"))
        self.coin_sub_lbl.pack()

        # Segmented Navigation Tab Bar
        bar = tk.Frame(w, bg=TRACK, padx=8, pady=7)
        bar.pack(fill="x")
        self.tab_btns = []
        for idx, name in enumerate(TABS):
            b = make_flat_button(
                bar, tk, command=lambda i=idx: self._switch_tab(i),
                text=name, bd=0, padx=9, pady=5, font=(UI_FONT, 8, "bold"), cursor="hand2",
            )
            b.pack(side="left", padx=2)
            self._bind_tab_hover(b, idx)
            self.tab_btns.append(b)

        # Scrollable viewport
        wrap = tk.Frame(w, bg=BG)
        wrap.pack(fill="both", expand=True)
        sb = tk.Scrollbar(wrap, orient="vertical")
        sb.pack(side="right", fill="y")
        cvs = tk.Canvas(wrap, bg=BG, highlightthickness=0, yscrollcommand=sb.set)
        cvs.pack(side="left", fill="both", expand=True)
        sb.configure(command=cvs.yview)
        self.canvas = cvs

        inner = tk.Frame(cvs, bg=BG, padx=12, pady=10)
        win_id = cvs.create_window((0, 0), window=inner, anchor="nw")
        self.body = inner

        inner.bind("<Configure>", lambda _e: cvs.configure(scrollregion=cvs.bbox("all")))
        cvs.bind("<Configure>", lambda e: cvs.itemconfigure(win_id, width=e.width))
        for wid in (cvs, inner, w):
            wid.bind("<MouseWheel>", self._on_wheel)
            wid.bind("<Button-4>", self._on_wheel)
            wid.bind("<Button-5>", self._on_wheel)

        self.refresh()
        self._schedule_tick()

    def close(self):
        for tid in (self._timer_id, self._bgm_after):
            if tid and self.win and self.win.winfo_exists():
                try:
                    self.win.after_cancel(tid)
                except Exception:
                    pass
        self._timer_id = None
        self._bgm_after = None
        self._cd_widgets.clear()
        if self.win and self.win.winfo_exists():
            self.win.destroy()
        self.win = None

    def _on_wheel(self, e):
        if not (self.canvas and self.canvas.winfo_exists()):
            return
        if getattr(e, "num", None) == 4:
            step = -2
        elif getattr(e, "num", None) == 5:
            step = 2
        elif abs(e.delta) >= 120:
            step = int(-e.delta / 120)
        elif e.delta:
            step = -1 if e.delta > 0 else 1
        else:
            return
        self.canvas.yview_scroll(step, "units")

    def _switch_tab(self, idx):
        self.tab = idx
        if self.canvas and self.canvas.winfo_exists():
            self.canvas.yview_moveto(0.0)
        self.refresh()

    def _bind_tab_hover(self, btn, idx):
        btn.bind("<Enter>", lambda _e: btn.configure(bg=RED_HOVER if self.tab == idx else "#252B3B"))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=RED if self.tab == idx else CARD2))

    def _btn(self, parent, text, cmd, bg=CARD2, fg="#FFF", padx=10, pady=5, font_s=8, width=None):
        hv = _mix_hex(bg, 0.14)
        kw = dict(
            text=text, bg=bg, fg=fg, activebackground=hv, activeforeground=fg,
            bd=0, padx=padx, pady=pady, font=(UI_FONT, font_s, "bold"), cursor="hand2",
        )
        if width:
            kw["width"] = width
        b = make_flat_button(parent, tk, command=cmd, **kw)
        b.bind("<Enter>", lambda _e: b.configure(bg=hv))
        b.bind("<Leave>", lambda _e: b.configure(bg=bg))
        return b

    def _schedule_tick(self):
        if not self.win or not self.win.winfo_exists():
            self._timer_id = None
            return
        self._update_cooldown_widgets()
        self._timer_id = self.win.after(1000, self._schedule_tick)

    def _fmt_cd(self, base, key):
        rem = self.app.cooldown_left(key)
        if rem <= 0:
            return base, False
        m, s = divmod(rem, 60)
        t_str = f"{m}m{s:02d}s" if m else f"{s}s"
        return f"{base} ({t_str})", True

    def _update_cooldown_widgets(self):
        alive = []
        for w, base, key, active_bg in self._cd_widgets:
            try:
                if not w.winfo_exists():
                    continue
                lbl, on_cd = self._fmt_cd(base, key)
                cur_bg = DIM_BTN if on_cd else active_bg
                w.configure(text=lbl, bg=cur_bg, fg=MUTED if on_cd else w._orig_fg)
                alive.append((w, base, key, active_bg))
            except Exception:
                pass
        self._cd_widgets = alive
        if self.focus_lbl and self.focus_lbl.winfo_exists():
            lang = lang_of(self.app)
            if self.app.focus_active:
                fm, fs = divmod(int(self.app.focus_rem), 60)
                ph = tr(lang, "PAUZE") if self.app.focus_phase == "break" else tr(lang, "FOCUS")
                self.focus_lbl.configure(text=f"● {ph} {fm:02d}:{fs:02d}", fg=CYAN if self.app.focus_phase == "break" else GOLD)
            else:
                q_tag = "Quiet" if lang == "en" else "Stil"
                q_txt = f"  [{q_tag}: {self.app._quiet_reason}]" if self.app.auto_paused else ""
                self.focus_lbl.configure(text=f"{tr(lang, 'Klaar voor een blok')}{q_txt}", fg=MUTED)

    def _cd_btn(self, parent, base, key, cmd, active_bg=CARD2, fg="#FFF", padx=10, pady=5, width=None):
        lbl, on_cd = self._fmt_cd(base, key)
        cur_bg = DIM_BTN if on_cd else active_bg
        kw = dict(
            text=lbl, bg=cur_bg, fg=MUTED if on_cd else fg,
            activebackground=_mix_hex(active_bg, 0.16), activeforeground=fg,
            bd=0, padx=padx, pady=pady, font=(UI_FONT, 8, "bold"), cursor="hand2",
        )
        if width:
            kw["width"] = width
        b = make_flat_button(parent, tk, command=cmd, **kw)
        b._orig_fg = fg
        b.bind("<Enter>", lambda _e: b.configure(bg=_mix_hex(DIM_BTN if self.app.cooldown_left(key) > 0 else active_bg, 0.14)))
        b.bind("<Leave>", lambda _e: b.configure(bg=DIM_BTN if self.app.cooldown_left(key) > 0 else active_bg))
        self._cd_widgets.append((b, base, key, active_bg))
        return b

    def _card(self, parent, title, bg=CARD, accent=GOLD, subtitle=None):
        f = tk.Frame(parent, bg=bg, padx=12, pady=10, highlightbackground=BORDER, highlightthickness=1)
        f.pack(fill="x", pady=6)
        if title:
            hdr = tk.Frame(f, bg=bg)
            hdr.pack(fill="x", pady=(0, 6))
            tk.Label(hdr, text=title, bg=bg, fg=accent, font=(UI_FONT, 10, "bold"), anchor="w").pack(side="left")
            if subtitle:
                tk.Label(hdr, text=subtitle, bg=bg, fg=MUTED, font=(UI_FONT, 8), anchor="e").pack(side="right")
        return f

    @staticmethod
    def _draw_bar(cvs, ratio, fill_col, h=10):
        def _paint(e=None):
            w = max(24, cvs.winfo_width() if e is None else e.width)
            cvs.delete("all")
            cvs.create_rectangle(0, 0, w, h, fill=TRACK, outline=BORDER, width=1)
            fw = max(4 if ratio > 0 else 0, int((w - 2) * max(0.0, min(1.0, ratio))))
            if fw > 0:
                cvs.create_rectangle(1, 1, 1 + fw, h - 1, fill=fill_col, outline="")
                cvs.create_line(1, 2, fw, 2, fill=_mix_hex(fill_col, 0.25))
        cvs.bind("<Configure>", _paint)
        cvs.after(1, _paint)

    def refresh(self):
        if not self.win or not self.win.winfo_exists():
            return
        d = self.app.d
        lang = lang_of(self.app)
        u = coin_u(lang)
        self.win.title(tr(lang, "Karel de Koala — Sticky BK Hub"))
        lvl = int(d.get("level", 1))
        xp = int(d.get("xp", 0))
        prev_xp = xp_for_next_level(lvl - 1)
        next_xp = xp_for_next_level(lvl)
        pct = max(0.0, min(1.0, (xp - prev_xp) / max(1, next_xp - prev_xp)))

        eq = d.get("equipped") or []
        perk = get_outfit_perk(eq)
        if eq and eq[0] in WARDROBE_ITEMS:
            wn, _ = tr_item(lang, eq[0], WARDROBE_ITEMS[eq[0]][0])
            out_txt = f"Outfit: {wn}" + (f" ({tr_perk(lang, eq[0], perk[3])})" if perk else "")
        else:
            out_txt = tr(lang, "Outfit: Basis (Geen extra perk actief)")

        if hasattr(self.app, "render_portrait"):
            self._hero_img = self.app.render_portrait(scale=2)
            self.avatar_lbl.configure(image=self._hero_img)

        pres = int(d.get("prestige", 0))
        p_txt = f"  ★ Prestige {pres}" if pres > 0 else ""
        who = "Karel the Koala" if lang == "en" else "Karel de Koala"
        self.head_lbl.configure(text=f"{who}  ·  Lv.{lvl} {tr_title(lang, title_for_level(lvl))}{p_txt}")
        mem_txt = f"○ {tr(lang, 'Geheugen')}"
        self.usb_lbl.configure(
            text="● RP2350 USB" if self.app.sm.connected else mem_txt,
            fg=GREEN if self.app.sm.connected else MUTED,
        )
        self.coin_lbl.configure(text=f"{d.get('coins', 0)} {u}")
        if self.coin_sub_lbl:
            self.coin_sub_lbl.configure(text=tr(lang, "STICKY MUNTEN"))
        bon = f"  ·  +{pres * 15}% Prestige" if pres > 0 else ""
        self.perk_lbl.configure(text=f"{out_txt}   ·   {xp}/{next_xp} XP{bon}")
        self._draw_bar(self.xp_cvs, pct, GOLD, h=10)

        for idx, b in enumerate(self.tab_btns):
            b.configure(text=tr(lang, TABS[idx]), bg=RED if idx == self.tab else CARD2, fg="#FFF" if idx == self.tab else FG)

        self._cd_widgets.clear()
        for child in self.body.winfo_children():
            child.destroy()

        handlers = (
            self._tab_status, self._tab_shop, self._tab_looks,
            self._tab_sticky, self._tab_arcade, self._tab_dex, self._tab_quests,
        )
        handlers[self.tab](self.body)

    # ------------------------------------------------------------------ Tab 0
    def _tab_status(self, root):
        d = self.app.d
        lang = lang_of(self.app)
        u = coin_u(lang)
        ev_t, _ = tr_event(lang, self.app.campus_title, self.app.campus_buff)
        sev_t, sev_b = tr_event(lang, getattr(self.app, "seasonal_title", ""), getattr(self.app, "seasonal_buff", ""))
        today_pfx = "Today" if lang == "en" else "Vandaag"
        c0 = self._card(root, tr(lang, "Conditie & Vitals"), subtitle=f"{today_pfx}: {ev_t}")
        sev_pfx = "Season Event" if lang == "en" else "Seizoen-Event"
        tk.Label(
            c0, text=f"{sev_pfx}: {sev_t} — {sev_b}",
            bg=CARD, fg=CYAN, font=(UI_FONT, 8, "bold"), anchor="w",
        ).pack(fill="x", pady=(0, 6))
        for label, val, col in (
            ("Honger", d.get("hunger", 0), GREEN),
            ("Blijheid", d.get("happiness", 0), PINK),
            ("Energie", d.get("energy", 0), CYAN),
            ("Cafeïne", d.get("caffeine", 0), "#D7A86E"),
            ("Hygiëne", d.get("hygiene", 0), "#6FE3E1"),
        ):
            row = tk.Frame(c0, bg=CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=tr(lang, label), width=11, anchor="w", bg=CARD, fg=FG, font=(UI_FONT, 9, "bold")).pack(side="left")
            cvs = tk.Canvas(row, height=11, bg=CARD, highlightthickness=0)
            cvs.pack(side="left", fill="x", expand=True, padx=8)
            self._draw_bar(cvs, float(val) / 100.0, col, h=11)
            tk.Label(row, text=f"{int(val):3d}%", width=5, anchor="e", bg=CARD, fg=col, font=(MONO, 9, "bold")).pack(side="right")

        c1 = self._card(root, tr(lang, "Zorg & Acties"), subtitle=tr(lang, "Met gebalanceerde Sticky cooldowns"))
        grid = tk.Frame(c1, bg=CARD)
        grid.pack(fill="x")
        actions = (
            ("Voer Eucalyptus", "feed", self.app.feed, "#26734D"),
            ("Sticky Koffie", "coffee", self.app.coffee, "#734B3A"),
            ("Aai Karel", "pet", self.app.pet, "#A8205A"),
            ("WasBubbles", "wash", self.app.wash, "#0D7385"),
            ("Powernap AAN/UIT", None, self.app.nap_toggle, "#3B4A5A"),
            ("Dansen", "dance", self.app.dance, "#6C2B9A"),
            ("Sporten", "exercise", self.app.exercise, "#BF5D14"),
            ("Toverspreuk", "cast_spell", self.app.cast_spell, "#4527A0"),
            ("Vissen", "fish", self.app.fish, "#14689E"),
            (f"Trivia (+16{u})", "trivia", self.app.open_trivia, RED),
            (f"Selfie (+3{u})", "selfie", self.app.selfie, "#881E52"),
            ("SuperMini Boop", "boop", self.app.hardware_boop, "#9E1B24"),
        )
        for idx, (base, key, cmd, bgc) in enumerate(actions):
            t_lbl = tr(lang, base)
            btn = self._cd_btn(grid, t_lbl, key, cmd, bgc, padx=8, pady=6) if key else self._btn(grid, t_lbl, cmd, bgc, padx=8, pady=6)
            btn.grid(row=idx // 4, column=idx % 4, sticky="ew", padx=3, pady=3)
        for col_i in range(4):
            grid.grid_columnconfigure(col_i, weight=1)

        c2 = self._card(root, tr(lang, "Loopgedrag, Grootte & Studio Audio"))
        rm = tk.Frame(c2, bg=CARD)
        rm.pack(fill="x", pady=(0, 8))
        tk.Label(rm, text=tr(lang, "Loop-modus:"), bg=CARD, fg=MUTED, font=(UI_FONT, 8, "bold")).pack(side="left", padx=(0, 6))
        cur_roam = d.get("roam_mode", "free")
        for mid, mlbl in (("free", "Vrij Scherm"), ("window", "Actief Venster"), ("cursor", "Volg Muis"), ("park", "Blijf Zitten")):
            self._btn(
                rm, tr(lang, mlbl), lambda m=mid: self.app.set_roam_mode(m),
                bg="#26734D" if cur_roam == mid else CARD2, padx=8, pady=4,
            ).pack(side="left", padx=2)
        self._btn(rm, tr(lang, "Klim!"), self.app.trigger_climb, bg=CARD2, fg=GOLD, padx=9, pady=4).pack(side="right")

        sz_row = tk.Frame(c2, bg=CARD)
        sz_row.pack(fill="x", pady=(0, 8))
        tk.Label(sz_row, text=tr(lang, "Karel Grootte:"), bg=CARD, fg=MUTED, font=(UI_FONT, 8, "bold")).pack(side="left", padx=(0, 6))
        cur_sz = int(d.get("karel_scale", 3))
        for sz, slbl in KAREL_SIZES:
            self._btn(
                sz_row, tr(lang, slbl), lambda v=sz: self.app.set_karel_scale(v),
                bg="#26734D" if cur_sz == sz else CARD2, padx=7, pady=4,
            ).pack(side="left", padx=2)
        tk.Label(sz_row, text=tr(lang, "Taal / Language:"), bg=CARD, fg=MUTED, font=(UI_FONT, 8, "bold")).pack(side="left", padx=(10, 4))
        for code, lbl in (("nl", "NL"), ("en", "EN")):
            self._btn(
                sz_row, lbl, lambda c=code: self.app.set_language(c),
                bg=RED if lang == code else CARD2, padx=7, pady=4,
            ).pack(side="left", padx=2)

        bg_row = tk.Frame(c2, bg=CARD)
        bg_row.pack(fill="x", pady=(0, 8))
        cur_bgm = self.app.snd.track
        for tid, (tname, _) in MUSIC_TRACKS.items():
            self._btn(
                bg_row, tr(lang, tname), lambda k=tid: self.app.set_music(k),
                bg=RED if cur_bgm == tid else CARD2, padx=8, pady=4,
            ).pack(side="left", padx=2, pady=2)

        # Smooth SFX & BGM Volume Sliders
        vol_box = tk.Frame(c2, bg=CARD2, padx=10, pady=8)
        vol_box.pack(fill="x", pady=(0, 8))
        self._build_slider(vol_box, "SFX Volume", int(round(self.app.snd.sfx_vol * 100)), self._on_sfx_slide)
        self._build_slider(vol_box, "BGM Volume", int(round(self.app.snd.bgm_vol * 100)), self._on_bgm_slide)

        au_row = tk.Frame(c2, bg=CARD)
        au_row.pack(fill="x")
        self._btn(
            au_row,
            tr(lang, f"Geluid: {'GEDEMPT' if self.app.snd.muted else 'AAN'}"),
            self.app._toggle_mute,
            bg="#A82028" if self.app.snd.muted else "#26734D", padx=10, pady=5,
        ).pack(side="left", padx=(0, 6))
        self._btn(
            au_row,
            tr(lang, f"Koala Bliepjes: {'AAN' if self.app.snd.voice_on else 'UIT'}"),
            self.app._toggle_voice,
            bg="#14689E" if self.app.snd.voice_on else CARD2, padx=10, pady=5,
        ).pack(side="left", padx=(0, 6))
        aq = bool(d.get("auto_quiet_fullscreen", True))
        self._btn(
            au_row,
            tr(lang, f"Stil bij Fullscreen/Call: {'AAN' if aq else 'UIT'}"),
            self.app.toggle_auto_quiet,
            bg="#26734D" if aq else CARD2, padx=10, pady=5,
        ).pack(side="left")

        sub_f = f"Completed: {d.get('focus_sessions', 0)}" if lang == "en" else f"Voltooide sessies: {d.get('focus_sessions', 0)}"
        c_foc = self._card(root, tr(lang, "Focus / Pomodoro Studiemodus"), subtitle=sub_f)
        f_top = tk.Frame(c_foc, bg=CARD)
        f_top.pack(fill="x", pady=(0, 6))
        self.focus_lbl = tk.Label(f_top, text=tr(lang, "Klaar voor een blok"), bg=CARD, fg=MUTED, font=(MONO, 9, "bold"), anchor="w")
        self.focus_lbl.pack(side="left", fill="x", expand=True)
        for mins, lbl in ((25, "Focus 25m"), (45, "Deep 45m"), (5, "Sprint 5m")):
            self._btn(f_top, lbl, lambda m=mins: self.app.start_focus(m), bg="#26734D" if mins == 25 else CARD2, padx=8, pady=4).pack(side="left", padx=2)
        self._btn(f_top, tr(lang, "Stop"), self.app.stop_focus, bg="#A82028" if self.app.focus_active else DIM_BTN, padx=8, pady=4).pack(side="left", padx=(4, 0))
        self._update_cooldown_widgets()

        c3 = self._card(root, tr(lang, "RP2350 SuperMini Hardware"))
        mem_lbl = f"{tr(lang, 'Geheugen')}-mode" if lang == "en" else "Geheugen-modus"
        usb_s = self.app.sm.drive if self.app.sm.connected else f"{mem_lbl} ({self.app.sm.fallback})"
        ser_s = self.app.ser.port_name or tr(lang, "USB Serial klaar, wachten op RP2350" if self.app.ser.available else "Standby (Serial optioneel)")
        u_lbl = "USB Storage :" if lang == "en" else "USB Opslag  :"
        s_lbl = "Serial Port :" if lang == "en" else "Serial Poort:"
        tk.Label(c3, text=f"{u_lbl} {usb_s}", bg=CARD, fg=FG, font=(MONO, 8), anchor="w").pack(fill="x")
        tk.Label(c3, text=f"{s_lbl} {ser_s}", bg=CARD, fg=MUTED, font=(MONO, 8), anchor="w").pack(fill="x")
        if self.app.sm.connected and hasattr(self.app.sm, "has_no_hid_flag"):
            no_hid = self.app.sm.has_no_hid_flag()
            hrow = tk.Frame(c3, bg=CARD)
            hrow.pack(fill="x", pady=(6, 0))
            tk.Label(hrow, text=tr(lang, "Auto-Start HID") + ":", bg=CARD, fg=MUTED, font=(UI_FONT, 8, "bold")).pack(side="left", padx=(0, 8))
            h_lbl = tr(lang, "Mac Veilig (geen Win+R, klik = AAN)" if no_hid else "Windows Win+R AAN (klik = Mac veilig)")
            self._btn(
                hrow, h_lbl, self._toggle_hid_flag,
                bg="#14689E" if no_hid else "#26734D", padx=8, pady=3, font_s=7,
            ).pack(side="left")

    def _toggle_hid_flag(self):
        st = self.app.sm.toggle_no_hid_flag()
        if st is not None:
            self.app.say(self.app._t("hid_mac" if st else "hid_win"), 70)
        self.refresh()

    def _build_slider(self, parent, label, init_val, callback):
        r = tk.Frame(parent, bg=CARD2)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, width=12, anchor="w", bg=CARD2, fg=FG, font=(UI_FONT, 8, "bold")).pack(side="left")
        pct_lbl = tk.Label(r, text=f"{init_val:3d}%", width=5, anchor="e", bg=CARD2, fg=GOLD, font=(MONO, 8, "bold"))
        pct_lbl.pack(side="right")

        def _on_move(val_str):
            iv = int(float(val_str))
            pct_lbl.configure(text=f"{iv:3d}%")
            callback(iv)

        sc = tk.Scale(
            r, from_=0, to=100, orient="horizontal", showvalue=0, sliderlength=16,
            bg=CARD2, fg=FG, troughcolor=TRACK, activebackground=RED_HOVER,
            highlightthickness=0, bd=0, command=_on_move,
        )
        sc.set(init_val)
        sc.pack(side="left", fill="x", expand=True, padx=8)

    def _on_sfx_slide(self, pct):
        self.app.set_sfx_volume(pct / 100.0)

    def _on_bgm_slide(self, pct):
        self.app.set_bgm_volume(pct / 100.0, restart=False)
        if self._bgm_after and self.win and self.win.winfo_exists():
            try:
                self.win.after_cancel(self._bgm_after)
            except Exception:
                pass
        if self.win and self.win.winfo_exists():
            self._bgm_after = self.win.after(140, lambda p=pct: self.app.set_bgm_volume(p / 100.0, restart=True))

    # ------------------------------------------------------------------ Tab 1
    def _tab_shop(self, root):
        d = self.app.d
        lang = lang_of(self.app)
        u = coin_u(lang)
        inv = d.get("inventory", {})
        ing = d.get("ingredients", {})

        c_inv = self._card(root, tr(lang, "Rugzak"), subtitle=tr(lang, "Snacks & gebrouwen tosti's"))
        if not inv:
            tk.Label(c_inv, text=tr(lang, "Rugzak is leeg! Koop iets in de Sticky kantine of bak in de keuken."),
                     bg=CARD, fg=MUTED, font=(UI_FONT, 8), anchor="w").pack(fill="x")
        else:
            row = tk.Frame(c_inv, bg=CARD)
            row.pack(fill="x")
            col = 0
            for iid, qty in inv.items():
                if qty <= 0:
                    continue
                meta = FOOD_SHOP.get(iid) or RECIPES.get(iid)
                if not meta:
                    continue
                inm, _ = tr_item(lang, iid, meta["name"])
                self._cd_btn(row, f"{inm} ({qty}x)", "feed_item",
                             lambda k=iid: self.app.feed_item(k), "#26734D", padx=8, pady=5).grid(
                    row=col // 2, column=col % 2, sticky="ew", padx=3, pady=3)
                col += 1
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=1)

        k_sub = f"Ingredients & {len(RECIPES)} Recipes" if lang == "en" else f"Ingrediënten & {len(RECIPES)} Recepten"
        c_kit = self._card(root, tr(lang, "Sticky Tosti-Keuken"), subtitle=k_sub)
        ing_row = tk.Frame(c_kit, bg=CARD)
        ing_row.pack(fill="x", pady=(0, 8))
        for idx, (ik, im) in enumerate(INGREDIENTS.items()):
            have = ing.get(ik, 0)
            inm, _ = tr_item(lang, ik, im["name"])
            self._btn(ing_row, f"{inm} ({have}) · {im['price']}{u}",
                      lambda k=ik: self.app.buy_ingredient(k), bg=CARD2, padx=8, pady=5).grid(
                row=idx // 2, column=idx % 2, sticky="ew", padx=3, pady=2)
        ing_row.grid_columnconfigure(0, weight=1)
        ing_row.grid_columnconfigure(1, weight=1)

        for rid, rec in RECIPES.items():
            req_parts = [f"{tr_item(lang, ik, INGREDIENTS[ik]['name'])[0]} {ing.get(ik, 0)}/{q}" for ik, q in rec["ing"].items() if ik in INGREDIENTS]
            can = all(ing.get(ik, 0) >= q for ik, q in rec["ing"].items())
            r = tk.Frame(c_kit, bg=CARD2, padx=8, pady=5)
            r.pack(fill="x", pady=2)
            left = tk.Frame(r, bg=CARD2)
            left.pack(side="left", fill="x", expand=True)
            rn, rd = tr_item(lang, rid, rec["name"], rec["desc"])
            tk.Label(left, text=f"{rn}  ·  {rd}", bg=CARD2, fg=GOLD if can else FG, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x")
            tk.Label(left, text=", ".join(req_parts), bg=CARD2, fg=GREEN if can else MUTED, font=(UI_FONT, 7), anchor="w").pack(fill="x")
            self._cd_btn(r, tr(lang, "Kook!"), "craft", lambda k=rid: self.app.craft_recipe(k),
                         "#26734D" if can else DIM_BTN, fg="#FFF" if can else MUTED, padx=10, pady=4).pack(side="right")

        fs_sub = f"{len(FOOD_SHOP)} Snacks & Drinks" if lang == "en" else f"{len(FOOD_SHOP)} Snacks & Drankjes"
        buy_w = "Buy" if lang == "en" else "Koop"
        c_fs = self._card(root, tr(lang, "Sticky Kantine"), subtitle=fs_sub)
        fs_grid = tk.Frame(c_fs, bg=CARD)
        fs_grid.pack(fill="x")
        for idx, (fid, it) in enumerate(FOOD_SHOP.items()):
            fnm, fdesc = tr_item(lang, fid, it["name"], it["desc"])
            r = tk.Frame(fs_grid, bg=CARD2, padx=8, pady=5)
            r.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=3, pady=3)
            tk.Label(r, text=fnm, bg=CARD2, fg=FG, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x")
            tk.Label(r, text=fdesc, bg=CARD2, fg=MUTED, font=(UI_FONT, 7), anchor="w").pack(fill="x")
            self._btn(r, f"{buy_w} {it['price']}{u}", lambda k=fid: self.app.buy_food(k), bg=RED, padx=8, pady=3).pack(anchor="e", pady=(4, 0))
        fs_grid.grid_columnconfigure(0, weight=1)
        fs_grid.grid_columnconfigure(1, weight=1)

        play_w = "Play" if lang == "en" else "Speel"
        c_ty = self._card(root, tr(lang, "Speelgoed & Permanente Upgrades"))
        for tid, ty in TOYS.items():
            tnm, tdesc = tr_item(lang, tid, ty["name"], ty["desc"])
            r = tk.Frame(c_ty, bg=CARD2, padx=8, pady=5)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=f"{tnm} — {tdesc}", bg=CARD2, fg=FG, font=(UI_FONT, 8), anchor="w").pack(side="left", fill="x", expand=True)
            self._cd_btn(r, f"{play_w} {ty['price']}{u}", "play_toy", lambda k=tid: self.app.play_toy(k), "#14689E", padx=9, pady=4).pack(side="right")

        ups = d.get("upgrades", [])
        for uid, up in UPGRADES.items():
            owned = uid in ups
            unm, udesc = tr_item(lang, uid, up["name"], up["desc"])
            r = tk.Frame(c_ty, bg=CARD2, padx=8, pady=5)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=f"{unm} — {udesc}", bg=CARD2, fg=GOLD if owned else FG, font=(UI_FONT, 8), anchor="w").pack(side="left", fill="x", expand=True)
            if owned:
                tk.Label(r, text=tr(lang, "ACTIEF"), bg="#26734D", fg="#FFF", padx=9, pady=3, font=(MONO, 8, "bold")).pack(side="right")
            else:
                self._btn(r, f"{buy_w} {up['price']}{u}", lambda k=uid: self.app.buy_upgrade(k), bg=RED, padx=9, pady=3).pack(side="right")

        c_ga = self._card(root, tr(lang, "RP2350 Grijpmachine"), subtitle=tr(lang, "40 Munten per draai"))
        tk.Label(c_ga, text=tr(lang, "Win exclusieve Vachten, Maatjes, Outfits, Elixers en Zeldzame StickyDex schatten!"),
                 bg=CARD, fg=MUTED, font=(UI_FONT, 8), anchor="w").pack(fill="x", pady=(0, 6))
        self._cd_btn(c_ga, tr(lang, "Draai Grijpmachine (40m)"), "gacha", self._do_gacha, GOLD, fg="#111", padx=12, pady=6).pack(anchor="w")
        if self.last_gacha:
            lp_pfx = "Last prize" if lang == "en" else "Laatste prijs"
            tk.Label(c_ga, text=f"{lp_pfx}: {self.last_gacha}", bg=CARD, fg=GOLD, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x", pady=(5, 0))

    def _do_gacha(self):
        res = self.app.spin_gacha()
        if res:
            self.last_gacha = res
        self.refresh()

    # ------------------------------------------------------------------ Tab 2
    def _tab_looks(self, root):
        d = self.app.d
        lang = lang_of(self.app)
        u = coin_u(lang)
        buy_w = "Buy" if lang == "en" else "Koop"
        eq = d.get("equipped", [])
        acc = d.get("unlocked_accessories", [])
        lvl = int(d.get("level", 1))
        cur_name = tr_item(lang, eq[0], WARDROBE_ITEMS[eq[0]][0])[0] if eq and eq[0] in WARDROBE_ITEMS else tr(lang, "Niets gedragen")

        w_title = f"Clothing & Accessories ({len(WARDROBE_ITEMS)} Items)" if lang == "en" else f"Kleding & Accessoires ({len(WARDROBE_ITEMS)} Stuks)"
        c_w = self._card(root, w_title, subtitle=tr(lang, "Strict 1 item tegelijk + passieve perk"))
        top = tk.Frame(c_w, bg=CARD)
        top.pack(fill="x", pady=(0, 8))
        act_lbl = "Active outfit" if lang == "en" else "Actieve outfit"
        tk.Label(top, text=f"{act_lbl}: {cur_name}", bg=CARD, fg=GOLD, font=(UI_FONT, 9, "bold")).pack(side="left")
        self._btn(top, tr(lang, "Alles Uitdoen"), self.app.unequip_all, bg="#475569", padx=10, pady=4).pack(side="right")

        w_grid = tk.Frame(c_w, bg=CARD)
        w_grid.pack(fill="x")
        for idx, (wid, (wname, price, desc)) in enumerate(WARDROBE_ITEMS.items()):
            free = wid == "scarf" or (wid == "hoodie" and lvl >= 4) or (wid == "crown" and lvl >= 8) or (wid in acc)
            on = wid in eq
            perk = OUTFIT_PERKS.get(wid)
            wnm, wdesc = tr_item(lang, wid, wname, desc)
            r = tk.Frame(w_grid, bg=CARD2, padx=8, pady=6, highlightbackground=GOLD if on else BORDER, highlightthickness=1)
            r.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=3, pady=3)
            tk.Label(r, text=wnm, bg=CARD2, fg=GOLD if on else FG, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x")
            tk.Label(r, text=wdesc, bg=CARD2, fg=MUTED, font=(UI_FONT, 7), anchor="w").pack(fill="x")
            if perk:
                tk.Label(r, text=f"Perk: {tr_perk(lang, wid, perk[2])}", bg=CARD2, fg=CYAN, font=(UI_FONT, 7, "bold"), anchor="w").pack(fill="x")
            lbl, bgc = (tr(lang, "Uitdoen"), "#26734D") if on else ((tr(lang, "Aantrekken"), "#14689E") if free else (f"{buy_w} {price}{u}", RED))
            self._btn(r, lbl, lambda k=wid: self.app.wardrobe_action(k), bg=bgc, padx=8, pady=3).pack(anchor="e", pady=(4, 0))
        w_grid.grid_columnconfigure(0, weight=1)
        w_grid.grid_columnconfigure(1, weight=1)

        sk_t = f"Koala Coats & Themes ({len(SKINS)})" if lang == "en" else f"Koala Vachten & Thema's ({len(SKINS)})"
        c_sk = self._card(root, sk_t, subtitle=tr(lang, "Met kleurvoorbeeld"))
        uskins = d.get("unlocked_skins", ["classic"])
        cur_sk = d.get("skin", "classic")
        sk_grid = tk.Frame(c_sk, bg=CARD)
        sk_grid.pack(fill="x")
        for idx, (sid, (sname, price, pal)) in enumerate(SKINS.items()):
            on = sid == cur_sk
            snm, _ = tr_item(lang, sid, sname)
            r = tk.Frame(sk_grid, bg=CARD2, padx=8, pady=5, highlightbackground=GOLD if on else BORDER, highlightthickness=1)
            r.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=3, pady=3)
            sw = tk.Canvas(r, width=18, height=18, bg=CARD2, highlightthickness=0)
            sw.pack(side="left", padx=(0, 8))
            sw.create_rectangle(1, 1, 17, 17, fill=pal.get("B", "#888"), outline=FG)
            sw.create_rectangle(5, 5, 13, 13, fill=pal.get("H", "#EEE"), outline="")
            tk.Label(r, text=snm, bg=CARD2, fg=GOLD if on else FG, font=(UI_FONT, 8, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
            lbl, bgc = (tr(lang, "ACTIEF"), "#26734D") if on else ((tr(lang, "Kies Vacht"), "#14689E") if (sid in uskins or price == 0) else (f"{buy_w} {price}{u}", RED))
            self._btn(r, lbl, lambda k=sid: self.app.skin_action(k), bg=bgc, padx=8, pady=3).pack(side="right")
        sk_grid.grid_columnconfigure(0, weight=1)
        sk_grid.grid_columnconfigure(1, weight=1)

        cp_t = f"Desktop Buddies ({len(COMPANIONS) - 1} + None)" if lang == "en" else f"Bureau-Maatjes ({len(COMPANIONS) - 1} + Geen)"
        c_cp = self._card(root, cp_t)
        ucomp = d.get("unlocked_companions", ["none"])
        cur_cp = d.get("companion", "none")
        for cid, (cname, price, cdesc, ccol) in COMPANIONS.items():
            cnm, cdesc_l = tr_item(lang, cid, cname, cdesc)
            r = tk.Frame(c_cp, bg=CARD2, padx=8, pady=5)
            r.pack(fill="x", pady=2)
            dot = tk.Canvas(r, width=12, height=12, bg=CARD2, highlightthickness=0)
            dot.pack(side="left", padx=(0, 6))
            dot.create_oval(1, 1, 11, 11, fill=ccol, outline="")
            tk.Label(r, text=f"{cnm} — {cdesc_l}", bg=CARD2, fg=ccol if cid == cur_cp else FG, font=(UI_FONT, 8), anchor="w").pack(side="left", fill="x", expand=True)
            lbl, bgc = (tr(lang, "ACTIEF"), "#26734D") if cid == cur_cp else ((tr(lang, "Roep Op"), "#14689E") if (cid in ucomp or price == 0) else (f"{buy_w} {price}{u}", RED))
            self._btn(r, lbl, lambda k=cid: self.app.companion_action(k), bg=bgc, padx=8, pady=3).pack(side="right")

    # ------------------------------------------------------------------ Tab 3
    def _tab_sticky(self, root):
        d = self.app.d
        lang = lang_of(self.app)
        u = coin_u(lang)
        helped = d.get("committees_helped", [])

        ev_t, ev_b = tr_event(lang, self.app.campus_title, self.app.campus_buff)
        sev_t, sev_b = tr_event(lang, getattr(self.app, "seasonal_title", ""), getattr(self.app, "seasonal_buff", ""))
        uhdr = f"Today at De Uithof (BBG Sticky BK) — {ev_t}" if lang == "en" else f"Vandaag op De Uithof (BBG Sticky BK) — {ev_t}"
        c_ev = self._card(root, uhdr, bg="#211924", accent=GOLD, subtitle=tr(lang, "Actieve Buffs"))
        db_pfx = "Daily Buff" if lang == "en" else "Dagbuff"
        sb_pfx = "Season" if lang == "en" else "Seizoen"
        tk.Label(c_ev, text=f"{db_pfx}: {ev_b}", bg="#211924", fg=FG, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x")
        tk.Label(c_ev, text=f"{sb_pfx} ({sev_t}): {sev_b}", bg="#211924", fg=CYAN, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x", pady=(2, 8))
        ar = tk.Frame(c_ev, bg="#211924")
        ar.pack(fill="x")
        self._cd_btn(ar, tr(lang, "Almanak Selfie (+3m)"), "selfie", self.app.selfie, "#A8205A").pack(side="left", padx=(0, 6))
        self._cd_btn(ar, tr(lang, "8-Bit Jam (Gitaar/Drums)"), "music_jam", self.app.music_jam, "#6C2B9A").pack(side="left", padx=(0, 6))
        self._btn(ar, tr(lang, "Klim van Taakbalk!"), self.app.trigger_climb, bg="#14689E").pack(side="left")

        cm_t = f"All Sticky Committees & Working Groups ({len(COMMITTEES)})" if lang == "en" else f"Alle Sticky Commissies & Werkgroepen ({len(COMMITTEES)})"
        cm_s = f"Helped: {len(helped)}/{len(COMMITTEES)} · Shifts: {d.get('committee_runs', 0)}" if lang == "en" else f"Geholpen: {len(helped)}/{len(COMMITTEES)} · Diensten: {d.get('committee_runs', 0)}"
        c_cm = self._card(root, cm_t, subtitle=cm_s)
        grid = tk.Frame(c_cm, bg=CARD)
        grid.pack(fill="x")
        ing_s = "Ingr."
        for idx, (cid, cname, cdesc, base_c, base_xp, _, cq) in enumerate(COMMITTEES):
            done = cid in helped
            cn_l, cd_l, _ = tr_committee(lang, cid, cname, cdesc, cq)
            r = tk.Frame(grid, bg=CARD2, padx=8, pady=6, highlightbackground=GOLD if done else BORDER, highlightthickness=1)
            r.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=3, pady=3)
            mark = "✓ " if done else "○ "
            sc_c, sc_x = max(6, int(base_c * 0.65)), max(6, int(base_xp * 0.65))
            tk.Label(r, text=f"{mark}{cn_l}", bg=CARD2, fg=GOLD if done else FG, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x")
            tk.Label(r, text=cd_l, bg=CARD2, fg=MUTED, font=(UI_FONT, 7), anchor="w", wraplength=290, justify="left").pack(fill="x")
            bot = tk.Frame(r, bg=CARD2)
            bot.pack(fill="x", pady=(4, 0))
            tk.Label(bot, text=f"+{sc_c}{u} · +{sc_x} XP + {ing_s}", bg=CARD2, fg=CYAN, font=(MONO, 7, "bold")).pack(side="left")
            self._cd_btn(bot, tr(lang, "Werk Mee!"), "committee", lambda k=cid: self.app.run_committee(k), RED, padx=8, pady=3).pack(side="right")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------ Tab 4
    def _tab_arcade(self, root):
        d = self.app.d
        lang = lang_of(self.app)
        hs = d.get("high_scores", {})
        arc_sub = f"Played: {d.get('games_played', 0)} · RPG Bosses: {d.get('rpg_wins', 0)}" if lang == "en" else f"Gespeeld: {d.get('games_played', 0)} · RPG Bazen: {d.get('rpg_wins', 0)}"
        c_top = self._card(root, "Sticky Arcade Hall", subtitle=arc_sub)
        grid = tk.Frame(c_top, bg=CARD)
        grid.pack(fill="x")
        for idx, (key, title, desc, cls, col) in enumerate(ARCADE_LIST):
            at_l, ad_l = tr_arcade_row(lang, key, title, desc)
            r = tk.Frame(grid, bg=CARD2, padx=10, pady=8, highlightbackground=BORDER, highlightthickness=1)
            r.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=4, pady=4)
            tk.Frame(r, bg=col, height=3).pack(fill="x", pady=(0, 6))
            tk.Label(r, text=at_l, bg=CARD2, fg=FG, font=(UI_FONT, 9, "bold"), anchor="w").pack(fill="x")
            tk.Label(r, text=ad_l, bg=CARD2, fg=MUTED, font=(UI_FONT, 8), anchor="w", wraplength=290, justify="left").pack(fill="x", pady=(2, 6))
            bot = tk.Frame(r, bg=CARD2)
            bot.pack(fill="x")
            tk.Label(bot, text=f"{'Best' if lang == 'en' else 'Record'}: {hs.get(key, 0)}", bg=CARD2, fg=GOLD, font=(MONO, 8, "bold")).pack(side="left")
            self._btn(bot, tr(lang, "Speel!"), lambda g=cls: self.app.open_game(g), bg=col, padx=12, pady=4).pack(side="right")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------ Tab 5
    def _tab_dex(self, root):
        lang = lang_of(self.app)
        u = coin_u(lang)
        dex = self.app.d.get("dex", {})
        found = sum(1 for item in LOOT_TABLE if item[0] in dex)
        c_dex = self._card(root, f"StickyDex Collectibles ({found}/{len(LOOT_TABLE)})", subtitle=tr(lang, "Vissen of Grijpmachine"))
        bar = tk.Canvas(c_dex, height=10, bg=CARD, highlightthickness=0)
        bar.pack(fill="x", pady=(0, 8))
        self._draw_bar(bar, found / max(1, len(LOOT_TABLE)), CYAN, h=10)
        sell_w = "Sell" if lang == "en" else "Verkoop"
        unk_w = "??? (Undiscovered)" if lang == "en" else "??? (Nog niet ontdekt)"
        for lid, lname, rty, val, ldesc in LOOT_TABLE:
            cnt = dex.get(lid, 0)
            seen = lid in dex
            lnm, lds = tr_item(lang, lid, lname, ldesc)
            r_l = tr(lang, rty)
            r = tk.Frame(c_dex, bg=CARD2, padx=8, pady=5)
            r.pack(fill="x", pady=2)
            col = RARITY_COLORS.get(rty, FG) if seen else "#5C6270"
            title_t = f"[{r_l}] {lnm} ({val}{u})" if seen else f"[{r_l}] {unk_w}"
            info = tk.Frame(r, bg=CARD2)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=f"{title_t}  ×{cnt}" if seen else title_t, bg=CARD2, fg=col, font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x")
            if seen:
                tk.Label(info, text=lds, bg=CARD2, fg=MUTED, font=(UI_FONT, 7), anchor="w").pack(fill="x")
            if cnt > 0:
                self._btn(r, f"{sell_w} +{val}{u}", lambda k=lid: self.app.sell_loot(k), bg=GOLD, fg="#111", padx=8, pady=3).pack(side="right")

    # ------------------------------------------------------------------ Tab 6
    def _tab_quests(self, root):
        d = self.app.d
        lang = lang_of(self.app)
        u = coin_u(lang)
        lvl = int(d.get("level", 1))
        pres = int(d.get("prestige", 0))
        dex = d.get("dex", {})
        top_trophy = tr(lang, "Nog geen schat gevonden")
        for it in reversed(LOOT_TABLE):
            if it[0] in dex:
                tnm, _ = tr_item(lang, it[0], it[1])
                top_trophy = f"[{tr(lang, it[2])}] {tnm}"
                break
        p_sub = f"★ Prestige {pres} (+{pres * 15}% XP & {'Coins' if lang == 'en' else 'Munten'})" if pres > 0 else tr(lang, "Vanaf Level 50")
        c_vit = self._card(root, tr(lang, "Prestatie-Vitrine & Alumni Prestige"), bg="#211924", accent=GOLD, subtitle=p_sub)
        sess_w = "sessions" if lang == "en" else "sessies"
        com_w = "Committees" if lang == "en" else "Commissies"
        vit_txt = (
            f"{'Top Trophy' if lang == 'en' else 'Top Trofee'} : {top_trophy}\n"
            f"{'Focus Block' if lang == 'en' else 'Focus Blok'} : {d.get('focus_sessions', 0)} {sess_w}   ·   StickyDex: {sum(1 for it in LOOT_TABLE if it[0] in dex)}/{len(LOOT_TABLE)}   ·   {com_w}: {len(d.get('committees_helped', []))}/{len(COMMITTEES)}"
        )
        tk.Label(c_vit, text=vit_txt, bg="#211924", fg=FG, font=(MONO, 8), justify="left", anchor="w").pack(fill="x", pady=(0, 8))
        p_row = tk.Frame(c_vit, bg="#211924")
        p_row.pack(fill="x")
        if lvl >= 50:
            p_btn = f"Activate Alumni Prestige ({pres + 1})" if lang == "en" else f"Activeer Alumni Prestige ({pres + 1})"
            self._btn(p_row, p_btn, self.app.do_prestige, bg=GOLD, fg="#111", padx=12, pady=5).pack(side="left")
            tk.Label(p_row, text=tr(lang, "Reset XP -> Lv.1 met behoud van alle spullen & +15% bonus!"), bg="#211924", fg=GREEN, font=(UI_FONT, 8, "bold")).pack(side="left", padx=10)
        else:
            p_msg = f"Alumni Prestige unlocks at Lv.50 (now Lv.{lvl}): earn golden stars & +15% permanent bonus per rank!" if lang == "en" else f"Alumni Prestige op Lv.50 (nu Lv.{lvl}): ontgrendel gouden sterren & blijvende +15% bonus per rang!"
            tk.Label(p_row, text=p_msg, bg="#211924", fg=MUTED, font=(UI_FONT, 8)).pack(side="left")

        qdate = d.get("quest_date") or d.get("quests_date", "")
        c_q = self._card(root, tr(lang, "Dagelijkse Sticky Quests"), subtitle=qdate)
        for idx, q in enumerate(d.get("quests", [])):
            cur, tgt = q.get("cur", 0), max(1, q.get("target", 1))
            done = q.get("claimed", False)
            ready = (not done) and cur >= tgt
            qlbl = tr_quest(lang, q.get("id", ""), q["label"], tgt)
            r = tk.Frame(c_q, bg=CARD2, padx=10, pady=6)
            r.pack(fill="x", pady=3)
            top = tk.Frame(r, bg=CARD2)
            top.pack(fill="x")
            tk.Label(
                top, text=f"{qlbl}  ({min(cur, tgt)}/{tgt})   [+{q['coins']}{u}, +{q['xp']} XP]",
                bg=CARD2, fg=GREEN if done else (GOLD if ready else FG), font=(UI_FONT, 8, "bold"), anchor="w",
            ).pack(side="left", fill="x", expand=True)
            if done:
                tk.Label(top, text=tr(lang, "GECLAIMD"), bg="#26734D", fg="#FFF", padx=8, pady=2, font=(MONO, 7, "bold")).pack(side="right")
            elif ready:
                self._btn(top, tr(lang, "Claim!"), lambda i=idx: self.app.claim_quest(i), bg=GOLD, fg="#111", padx=10, pady=2).pack(side="right")
            else:
                tk.Label(top, text=tr(lang, "Bezig"), bg=DIM_BTN, fg=MUTED, padx=8, pady=2, font=(MONO, 7)).pack(side="right")
            qb = tk.Canvas(r, height=6, bg=CARD2, highlightthickness=0)
            qb.pack(fill="x", pady=(4, 0))
            self._draw_bar(qb, min(1.0, cur / tgt), GREEN if done else (GOLD if ready else CYAN), h=6)

        c_st = self._card(root, tr(lang, "Carrière Statistieken"))
        if lang == "en":
            stats_line = (
                f"Pets: {d.get('total_pets', 0)}  |  Feeds: {d.get('total_feeds', 0)}  |  "
                f"Coffee: {d.get('total_coffees', 0)}  |  Washes: {d.get('total_washes', 0)}  |  Fished: {d.get('total_fish', 0)}\n"
                f"Cooked: {d.get('total_crafted', 0)}  |  Trivia Correct: {d.get('total_trivia', 0)}  |  "
                f"Committees: {d.get('committee_runs', 0)} ({len(d.get('committees_helped', []))}/{len(COMMITTEES)} unique)"
            )
        else:
            stats_line = (
                f"Aaien: {d.get('total_pets', 0)}  |  Voeren: {d.get('total_feeds', 0)}  |  "
                f"Koffie: {d.get('total_coffees', 0)}  |  Wassen: {d.get('total_washes', 0)}  |  Vissen: {d.get('total_fish', 0)}\n"
                f"Gekookt: {d.get('total_crafted', 0)}  |  Trivia Goed: {d.get('total_trivia', 0)}  |  "
                f"Commissies: {d.get('committee_runs', 0)} ({len(d.get('committees_helped', []))}/{len(COMMITTEES)} uniek)"
            )
        tk.Label(c_st, text=stats_line, bg=CARD, fg=MUTED, font=(MONO, 8), justify="left", anchor="w").pack(fill="x")

        uach = set(d.get("unlocked_achievements", []))
        c_ach = self._card(root, f"Sticky Achievements ({len(uach)}/{len(ACHIEVEMENTS)})")
        ag = tk.Frame(c_ach, bg=CARD)
        ag.pack(fill="x")
        for idx, (aname, adesc) in enumerate(ACHIEVEMENTS.items()):
            unlocked = aname in uach
            an_l, ad_l = tr_ach(lang, aname, adesc)
            r = tk.Frame(ag, bg=CARD2, padx=8, pady=5, highlightbackground=GOLD if unlocked else BORDER, highlightthickness=1)
            r.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=3, pady=2)
            mark = "✓ " if unlocked else "○ "
            tk.Label(r, text=f"{mark}{an_l}", bg=CARD2, fg=GOLD if unlocked else "#7B8498", font=(UI_FONT, 8, "bold"), anchor="w").pack(fill="x")
            tk.Label(r, text=ad_l, bg=CARD2, fg=FG if unlocked else "#5C6270", font=(UI_FONT, 7), anchor="w", wraplength=290, justify="left").pack(fill="x")
        ag.grid_columnconfigure(0, weight=1)
        ag.grid_columnconfigure(1, weight=1)
