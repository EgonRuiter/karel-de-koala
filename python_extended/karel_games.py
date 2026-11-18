#!/usr/bin/env python3
"""8 Arcade mini-games for Karel de Koala (Pure Python 3 stdlib / Tkinter)."""

import os
import random
import tkinter as tk

from karel_i18n import lang_of, tr
from karel_world import IS_MAC, apply_window_icon, make_flat_button

BG = "#12141B"
CARD = "#1B1F2A"
RED = "#C41E25"
GREEN = "#3ECF8E"
GOLD = "#F5C451"
FG = "#F2F5FA"
MUTED = "#98A2B8"
FONT = "Consolas" if os.name == "nt" else ("Menlo" if IS_MAC else "DejaVu Sans Mono")


class _BaseGame:
    """Shared lifecycle, rewards, and hardware control plumbing for all 8 games."""

    def __init__(self, app, title, w, h):
        self.app = app
        self.en = (lang_of(app) == "en")
        self.running = True
        self._after_id = None
        self.w = w
        self.h = h
        self.win = tk.Toplevel(app.r)
        self.win.title(self._t(title))
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        apply_window_icon(self.win, app, tk_mod=tk)
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{w}x{h}+{max(20, (sw - w) // 2)}+{max(20, (sh - h) // 2)}")
        self.win.lift()
        self.win.focus_force()

    def _btn(self, parent, text, cmd, **kw):
        return make_flat_button(parent, tk, command=cmd, text=text, **kw)

    def _t(self, nl_txt):
        return tr("en" if self.en else "nl", nl_txt)

    def _rec_txt(self, is_best):
        return ("(NEW RECORD!)" if self.en else "(NIEUW RECORD!)") if is_best else ""

    def _coins_lbl(self):
        return self._t("Sticky Munten")

    def _schedule(self, ms, fn):
        if self.running:
            self._after_id = self.win.after(ms, fn)

    def _reward(self, key, score, xp, coins, lower_better=False):
        d = self.app.d
        hs = d.setdefault("high_scores", {
            "catch": 0, "flappy": 0, "smash": 0, "memory": 0,
            "snake": 0, "merge": 0, "rhythm": 0, "rpg": 0,
            "gans": 0, "koala": 0,
        })
        prev = hs.get(key, 0)
        is_best = (score > 0 and (prev == 0 or score < prev)) if lower_better else (score > prev)
        if is_best:
            hs[key] = score
        if key == "catch" and score > d.get("high_score_minigame", 0):
            d["high_score_minigame"] = score
        if xp > 0:
            xp = max(4, int(xp * 0.6))
        if coins > 0:
            coins = max(2, int(coins * 0.6))
        if "overclock_2040" in d.get("upgrades", []):
            xp = int(xp * 1.3)
            coins = int(coins * 1.3)
        bonus_xp = max(0, xp)
        bonus_coins = max(0, coins)
        if bonus_xp:
            self.app.gain_xp(bonus_xp)
        if bonus_coins:
            bonus_coins = self.app.add_coins(bonus_coins, from_game=True)
        return is_best, bonus_xp, bonus_coins

    def nudge(self, dx):
        pass

    def action(self):
        pass

    def close(self):
        if not self.running:
            return
        self.running = False
        if self._after_id is not None:
            try:
                self.win.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if getattr(self.app, "mg", None) is self:
            self.app.mg = None
        try:
            self.win.destroy()
        except Exception:
            pass
        self.app.say(self._t("Terug van het arcade-hoekje!"))


class MiniGameCatch(_BaseGame):
    """Mini-game 1: Eucalyptus & Coffee Catch! with bonus Coins & Combos."""

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 1/8 — Eucalyptus & Coffee Catch!", 460, 520)
        self.cw, self.ch = 460, 445
        self.kx = self.cw // 2
        self.vx = 0
        self.score = 0
        self.combo = 0
        self.coins_caught = 0
        self.lives = 3
        self.items = []
        self.tick_n = 0
        self.over = False

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="Score: 0 | Combo x1 | ♥♥♥", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        self.cv = tk.Canvas(self.win, width=self.cw, height=self.ch, bg=BG, highlightthickness=0)
        self.cv.pack()
        tk.Label(
            self.win, text=self._t("◀ ▶ / Muis / USB: Bewegen  •  Groen:+10  Koffie:+25  Munt:+2  Deadline:-1♥"),
            bg=BG, fg=MUTED, font=(FONT, 8),
        ).pack(pady=6)

        self.win.bind("<Left>", lambda e: self._set_v(-8))
        self.win.bind("<Right>", lambda e: self._set_v(8))
        self.win.bind("<a>", lambda e: self._set_v(-8))
        self.win.bind("<d>", lambda e: self._set_v(8))
        self.win.bind("<KeyRelease-Left>", lambda e: self._set_v(0))
        self.win.bind("<KeyRelease-Right>", lambda e: self._set_v(0))
        self.win.bind("<KeyRelease-a>", lambda e: self._set_v(0))
        self.win.bind("<KeyRelease-d>", lambda e: self._set_v(0))
        self.win.bind("<Escape>", lambda e: self.close())
        self.cv.bind("<Motion>", lambda e: setattr(self, "kx", max(36, min(self.cw - 36, e.x))))
        self.step()

    def _set_v(self, v):
        self.vx = v

    def nudge(self, dx):
        self.kx = max(36, min(self.cw - 36, self.kx + dx))

    def action(self):
        if self.over:
            self._restart()

    def _restart(self):
        self.score = 0
        self.combo = 0
        self.coins_caught = 0
        self.lives = 3
        self.items = []
        self.tick_n = 0
        self.over = False
        self.step()

    def step(self):
        if not self.running:
            return
        self.tick_n += 1
        self.kx = max(36, min(self.cw - 36, self.kx + self.vx))
        rate = max(12, 28 - self.score // 40)
        if self.tick_n % rate == 0:
            r = random.random()
            kind = "LEAF" if r < 0.48 else ("COFFEE" if r < 0.68 else ("COIN" if r < 0.80 else "BUG"))
            self.items.append([random.randint(24, self.cw - 24), -12, kind, 3.2 + min(4.2, self.score / 75.0)])

        kept = []
        for it in self.items:
            it[1] += it[3]
            ix, iy, kind, _ = it
            if self.ch - 70 <= iy <= self.ch - 14 and abs(ix - self.kx) < 40:
                if kind == "BUG":
                    self.lives -= 1
                    self.combo = 0
                    self.app.snd.buzz()
                else:
                    self.combo += 1
                    mult = min(3, 1 + self.combo // 5)
                    if kind == "LEAF":
                        self.score += 10 * mult
                    elif kind == "COFFEE":
                        self.score += 25 * mult
                    elif kind == "COIN":
                        self.score += 15
                        self.coins_caught += 2
                    self.app.snd.coin()
                continue
            if iy < self.ch + 20:
                kept.append(it)
            elif kind in ("LEAF", "COFFEE"):
                self.combo = 0
        self.items = kept

        self.cv.delete("all")
        self.cv.create_line(0, self.ch - 14, self.cw, self.ch - 14, fill="#303443", width=2)
        for ix, iy, kind, _ in self.items:
            if kind == "LEAF":
                self.cv.create_oval(ix - 11, iy - 7, ix + 11, iy + 7, fill=GREEN, outline="#2E7D32", width=2)
            elif kind == "COFFEE":
                self.cv.create_rectangle(ix - 9, iy - 8, ix + 9, iy + 10, fill=RED, outline="#FFF")
                self.cv.create_text(ix, iy + 2, text="S", fill="#FFF", font=(FONT, 8, "bold"))
            elif kind == "COIN":
                self.cv.create_oval(ix - 9, iy - 9, ix + 9, iy + 9, fill=GOLD, outline="#FFF", width=2)
                self.cv.create_text(ix, iy, text="$", fill="#5C3A21", font=(FONT, 9, "bold"))
            else:
                self.cv.create_polygon(ix, iy - 11, ix - 11, iy + 10, ix + 11, iy + 10, fill="#FFB300", outline="#FF5252", width=2)
                self.cv.create_text(ix, iy + 3, text="!", fill="#111", font=(FONT, 9, "bold"))

        sprite = self.app.mg_sprite(self.app.d)
        if sprite:
            self.cv.create_image(self.kx, self.ch - 46, image=sprite)
        self.lbl.config(text=f"Score: {self.score} | Combo x{min(3, 1 + self.combo // 5)} | {'♥' * max(0, self.lives)}")

        if self.lives <= 0:
            self.over = True
            self._finish()
            return
        self._schedule(32, self.step)

    def _finish(self):
        xp_base = max(10, self.score // 4)
        if getattr(self.app, "campus_tag", "") == "happy_boost":
            xp_base = int(round(xp_base * 1.15))
        is_best, xp, coins = self._reward("catch", self.score, xp_base, self.score // 15 + self.coins_caught)
        self.app.quest_bump("catch_pts", self.score, max_mode=True)
        if self.score >= 200:
            self.app.unlock("Eucalyptus Kampioen")
        self.app.snd.victory()
        hs = self.app.d.get("high_scores", {}).get("catch", self.score)
        self.cv.create_rectangle(52, 130, 408, 325, fill="#111318", outline=RED, width=3)
        self.cv.create_text(230, 165, text="GAME OVER!", fill="#FFF", font=(FONT, 17, "bold"))
        rec = self._rec_txt(is_best) or f"(Best: {hs})"
        self.cv.create_text(230, 200, text=f"Score: {self.score}  {rec}", fill=GOLD, font=(FONT, 11, "bold"))
        self.cv.create_text(230, 232, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", fill=GREEN, font=(FONT, 10, "bold"))
        self.cv.create_window(165, 282, window=self._btn(self.cv, self._t("Opnieuw"), self._restart, bg=RED, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 10, "bold")))
        self.cv.create_window(295, 282, window=self._btn(self.cv, self._t("Sluiten"), self.close, bg=CARD, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 10)))


MiniGameWindow = MiniGameCatch


class MiniGameFlappy(_BaseGame):
    """Mini-game 2: Koala Flappy Hop! Dodge scrolling Sticky deadlines."""

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 2/8 — Koala Flappy Hop!", 440, 480)
        self.cw, self.ch = 440, 405
        self.ky = self.ch // 2
        self.vy = 0.0
        self.pipes = []
        self.score = 0
        self.bonus_coins = 0
        self.tick_n = 0
        self.started = False
        self.over = False

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="Gates: 0" if self.en else "Poorten: 0", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        self.cv = tk.Canvas(self.win, width=self.cw, height=self.ch, bg="#141923", highlightthickness=0)
        self.cv.pack()
        tk.Label(self.win, text=self._t("Spatie / Omhoog / Klik / USB: Flapperen!"), bg=BG, fg=MUTED, font=(FONT, 8)).pack(pady=6)

        self.win.bind("<space>", lambda e: self.flap())
        self.win.bind("<Up>", lambda e: self.flap())
        self.win.bind("<w>", lambda e: self.flap())
        self.cv.bind("<Button-1>", lambda e: self.flap())
        self.win.bind("<Escape>", lambda e: self.close())
        self._draw()
        self.step()

    def flap(self):
        if not self.running or self.over:
            return
        self.started = True
        self.vy = -7.6
        self.app.snd.flap()

    def nudge(self, _dx):
        self.flap()

    def action(self):
        if self.over:
            self._restart()
        else:
            self.flap()

    def _restart(self):
        self.ky = self.ch // 2
        self.vy = 0.0
        self.pipes = []
        self.score = 0
        self.bonus_coins = 0
        self.tick_n = 0
        self.started = False
        self.over = False
        self.step()

    def step(self):
        if not self.running or self.over:
            return
        self.tick_n += 1
        if self.started:
            self.vy = min(9.5, self.vy + 0.56)
            self.ky += self.vy
            if self.tick_n % 52 == 1:
                self.pipes.append([self.cw + 30, random.randint(105, self.ch - 105), False, random.random() < 0.65])
            kept = []
            for p in self.pipes:
                p[0] -= 4.2
                px, gap_y, passed, has_coin = p
                if not passed and px + 24 < 95:
                    p[2] = True
                    self.score += 1
                    self.app.snd.coin()
                if has_coin and abs(px - 95) < 26 and abs(self.ky - gap_y) < 36:
                    p[3] = False
                    self.bonus_coins += 3
                if abs(px - 95) < 32 and abs(self.ky - gap_y) > 54:
                    self.over = True
                if px > -40:
                    kept.append(p)
            self.pipes = kept
            if self.ky < 20 or self.ky > self.ch - 20:
                self.over = True
        self._draw()
        if self.over:
            self._finish()
            return
        self._schedule(28, self.step)

    def _draw(self):
        self.cv.delete("all")
        for sx in range(0, self.cw, 55):
            self.cv.create_line((sx - (self.tick_n * 2) % 55), 0, (sx - (self.tick_n * 2) % 55), self.ch, fill="#1E2534")
        for px, gap_y, _, has_coin in self.pipes:
            self.cv.create_rectangle(px - 22, 0, px + 22, gap_y - 62, fill=RED, outline="#7A0F14", width=2)
            self.cv.create_rectangle(px - 22, gap_y + 62, px + 22, self.ch, fill=RED, outline="#7A0F14", width=2)
            if has_coin:
                self.cv.create_oval(px - 9, gap_y - 9, px + 9, gap_y + 9, fill=GOLD, outline="#FFF", width=2)
                self.cv.create_text(px, gap_y, text="$", fill="#5C3A21", font=(FONT, 9, "bold"))
        sprite = self.app.mg_sprite(self.app.d)
        if sprite:
            self.cv.create_image(95, int(self.ky), image=sprite)
        if not self.started and not self.over:
            self.cv.create_text(self.cw // 2, self.ch // 2 - 70, text=self._t("KLIK OF SPATIE OM TE VLIEGEN!"), fill=GOLD, font=(FONT, 12, "bold"))
        best = self.app.d.get("high_scores", {}).get("flappy", 0)
        p_lbl, m_lbl = ("Gates", "Coins") if self.en else ("Poorten", "Munten")
        self.lbl.config(text=f"{p_lbl}: {self.score}  •  {m_lbl}: +{self.bonus_coins}  •  Best: {max(best, self.score)}")

    def _finish(self):
        self.app.snd.buzz()
        is_best, xp, coins = self._reward("flappy", self.score, max(8, self.score * 5), self.score * 2 + self.bonus_coins)
        self.app.quest_bump("flappy_pts", self.score, max_mode=True)
        if self.score >= 15:
            self.app.unlock("Flappy Koala")
        p_lbl = "Gates" if self.en else "Poorten"
        self.cv.create_rectangle(52, 115, 388, 295, fill="#111318", outline=RED, width=3)
        self.cv.create_text(220, 148, text=self._t("OEF, DEADLINE GERAAKT!"), fill="#FFF", font=(FONT, 14, "bold"))
        self.cv.create_text(220, 182, text=f"{p_lbl}: {self.score}  {self._rec_txt(is_best)}", fill=GOLD, font=(FONT, 11, "bold"))
        self.cv.create_text(220, 212, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", fill=GREEN, font=(FONT, 10, "bold"))
        self.cv.create_window(155, 256, window=self._btn(self.cv, self._t("Opnieuw"), self._restart, bg=RED, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 10, "bold")))
        self.cv.create_window(285, 256, window=self._btn(self.cv, self._t("Sluiten"), self.close, bg=CARD, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 10)))


class MiniGameBugSmash(_BaseGame):
    """Mini-game 3: BBG Bug Smasher! Whack bugs & segfaults in 30 seconds."""

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 3/8 — BBG Bug Smasher!", 420, 470)
        self.score = 0
        self.time_left = 30
        self.slots = [None] * 9
        self.cursor = 4
        self.over = False
        self._tick_n = 0

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        t_lbl = "Time" if self.en else "Tijd"
        self.lbl = tk.Label(hdr, text=f"Score: 0  •  {t_lbl}: 30s", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        grid = tk.Frame(self.win, bg=BG)
        grid.pack(pady=14)
        self.btns = []
        for idx in range(9):
            b = self._btn(grid, f"[{idx + 1}]", lambda i=idx: self.smash(i), width=11, height=4, bg=CARD, fg=MUTED, font=(FONT, 11, "bold"), bd=2, relief="flat")
            b.grid(row=idx // 3, column=idx % 3, padx=6, pady=6)
            self.btns.append(b)
            self.win.bind(str(idx + 1), lambda e, i=idx: self.smash(i))
        tk.Label(self.win, text=self._t("Klik of toets 1-9 • Pas op: sla geen Karel!"), bg=BG, fg=MUTED, font=(FONT, 8)).pack(pady=4)
        self.win.bind("<Escape>", lambda e: self.close())
        self.step()

    def nudge(self, dx):
        if not self.over:
            self.cursor = (self.cursor + (1 if dx >= 0 else -1)) % 9
            self._render()

    def action(self):
        if self.over:
            self._restart()
        else:
            idx = self.cursor
            if not self.slots[idx]:
                targets = [i for i, s in enumerate(self.slots) if s and s[0] != "KAREL"]
                if targets:
                    idx = targets[0]
            self.smash(idx)

    def _restart(self):
        self.score = 0
        self.time_left = 30
        self.slots = [None] * 9
        self._tick_n = 0
        self.over = False
        self.step()

    def smash(self, idx):
        if not self.running or self.over:
            return
        self.cursor = idx
        cur = self.slots[idx]
        if not cur:
            self.score = max(0, self.score - 2)
            self.app.snd.buzz()
        else:
            kind, _ = cur
            self.slots[idx] = None
            if kind == "BUG":
                self.score += 20
                self.app.snd.smash()
            elif kind == "SEGFAULT":
                self.score += 40
                self.app.snd.smash()
            elif kind == "COIN":
                self.score += 15
                self.time_left = min(35, self.time_left + 1)
                self.app.snd.coin()
            else:
                self.score = max(0, self.score - 25)
                self.app.snd.buzz()
        self._render()

    def _render(self):
        for i, b in enumerate(self.btns):
            cur = self.slots[i]
            sel = " *" if i == self.cursor else ""
            if not cur:
                b.config(text=f"[{i + 1}]{sel}", bg=CARD, fg=MUTED)
            elif cur[0] == "BUG":
                b.config(text="BUG!\n+20", bg="#3A1D24", fg="#FF6B6B")
            elif cur[0] == "SEGFAULT":
                b.config(text="SEGFAULT\n+40", bg="#422B12", fg="#FFB300")
            elif cur[0] == "COIN":
                b.config(text=self._t("$ MUNT\n+15 +1s"), bg="#3B3314", fg=GOLD)
            else:
                b.config(text=self._t("KAREL!\nNIET SLAAN"), bg="#1B3826", fg="#A5D6A7")
        self.lbl.config(text=f"Score: {self.score}  •  {'Time' if self.en else 'Tijd'}: {self.time_left}s")

    def step(self):
        if not self.running or self.over:
            return
        self._tick_n += 1
        for i in range(9):
            if self.slots[i] is not None:
                kind, ttl = self.slots[i]
                self.slots[i] = None if ttl <= 1 else (kind, ttl - 1)
        if self._tick_n % 2 == 1:
            free = [i for i, v in enumerate(self.slots) if v is None]
            if free:
                r = random.random()
                self.slots[random.choice(free)] = (
                    "BUG" if r < 0.50 else ("SEGFAULT" if r < 0.72 else ("COIN" if r < 0.86 else "KAREL")),
                    random.randint(3, 5),
                )
        if self._tick_n % 4 == 0:
            self.time_left -= 1
        self._render()
        if self.time_left <= 0:
            self.over = True
            self._finish()
            return
        self._schedule(250, self.step)

    def _finish(self):
        is_best, xp, coins = self._reward("smash", self.score, max(10, self.score // 5), max(5, self.score // 12))
        self.app.quest_bump("smash_pts", self.score, max_mode=True)
        if self.score >= 250:
            self.app.unlock("Bug Hunter")
        self.app.snd.victory()
        pop = tk.Frame(self.win, bg="#111318", highlightbackground=RED, highlightthickness=2)
        pop.place(relx=0.5, rely=0.52, anchor="center", width=330, height=180)
        tk.Label(pop, text=self._t("KLAAR MET DEBUGGEN!"), bg="#111318", fg="#FFF", font=(FONT, 13, "bold")).pack(pady=(16, 4))
        tk.Label(pop, text=f"Score: {self.score}  {self._rec_txt(is_best)}", bg="#111318", fg=GOLD, font=(FONT, 11, "bold")).pack()
        tk.Label(pop, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", bg="#111318", fg=GREEN, font=(FONT, 10, "bold")).pack(pady=8)
        row = tk.Frame(pop, bg="#111318")
        row.pack(pady=6)
        self._btn(row, self._t("Opnieuw"), lambda: (pop.destroy(), self._restart()), bg=RED, fg="#FFF", bd=0, padx=12, pady=4, font=(FONT, 9, "bold")).pack(side="left", padx=6)
        self._btn(row, self._t("Sluiten"), self.close, bg=CARD, fg="#FFF", bd=0, padx=12, pady=4, font=(FONT, 9)).pack(side="left", padx=6)


class MiniGameMemory(_BaseGame):
    """Mini-game 4: Sticky Code Memory 4x4! Pair all 8 icons."""

    PAIRS = [
        ("KOALA", "#8E949E"), ("KOFFIE", "#D94B4B"), ("PYTHON", "#4B8BBE"), ("GIT", "#F05032"),
        ("RUST", "#DEA584"), ("LINUX", "#FCC624"), ("RP2350", "#4CAF50"), ("VAGANT", "#BA68C8"),
    ]

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 4/8 — Sticky Code Memory 4x4!", 420, 490)
        self.cards = self.PAIRS * 2
        random.shuffle(self.cards)
        self.matched = [False] * 16
        self.open_idx = []
        self.moves = 0
        self.locked = False
        self.cursor = 0
        self.over = False

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        mv, pr = ("Moves", "Pairs") if self.en else ("Zetten", "Paren")
        self.lbl = tk.Label(hdr, text=f"{mv}: 0  •  {pr}: 0/8", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        grid = tk.Frame(self.win, bg=BG)
        grid.pack(pady=14)
        self.btns = []
        for idx in range(16):
            b = self._btn(grid, "?", lambda i=idx: self.flip(i), width=8, height=4, bg=CARD, fg=FG, font=(FONT, 10, "bold"), bd=2, relief="flat")
            b.grid(row=idx // 4, column=idx % 4, padx=5, pady=5)
            self.btns.append(b)
        tk.Label(self.win, text=self._t("Vind alle 8 paren! <=14 zetten = 'Memory Meester'"), bg=BG, fg=MUTED, font=(FONT, 8)).pack(pady=4)
        self.win.bind("<Left>", lambda e: self.nudge(-1))
        self.win.bind("<Right>", lambda e: self.nudge(1))
        self.win.bind("<space>", lambda e: self.action())
        self.win.bind("<Escape>", lambda e: self.close())
        self._render()

    def nudge(self, dx):
        if not self.over:
            self.cursor = (self.cursor + (1 if dx >= 0 else -1)) % 16
            self._render()

    def action(self):
        if self.over:
            self.close()
        else:
            self.flip(self.cursor)

    def flip(self, idx):
        if not self.running or self.over or self.locked or self.matched[idx] or idx in self.open_idx:
            return
        self.cursor = idx
        self.open_idx.append(idx)
        self.app.snd.flap()
        self._render()
        if len(self.open_idx) == 2:
            self.moves += 1
            a, b = self.open_idx
            if self.cards[a][0] == self.cards[b][0]:
                self.matched[a] = self.matched[b] = True
                self.open_idx = []
                self.app.snd.coin()
                self._render()
                if all(self.matched):
                    self.over = True
                    self._finish()
            else:
                self.locked = True
                self._schedule(650, self._hide_mismatch)

    def _hide_mismatch(self):
        self.open_idx = []
        self.locked = False
        self._render()

    def _render(self):
        best = self.app.d.get("high_scores", {}).get("memory", 0)
        mv, pr = ("Moves", "Pairs") if self.en else ("Zetten", "Paren")
        self.lbl.config(text=f"{mv}: {self.moves}  •  {pr}: {sum(self.matched) // 2}/8  •  Best: {best or '-'}")
        for i, b in enumerate(self.btns):
            label, col = self.cards[i]
            if self.matched[i]:
                b.config(text=label, bg="#1B3A26", fg=GOLD)
            elif i in self.open_idx:
                b.config(text=label, bg=col, fg="#111")
            else:
                b.config(text="[?]" if i == self.cursor else "?", bg="#2E3342" if i == self.cursor else CARD, fg=FG)

    def _finish(self):
        is_best, xp, coins = self._reward("memory", self.moves, max(20, 60 - self.moves * 2), max(15, 45 - self.moves), lower_better=True)
        self.app.quest_bump("memory_win", 1)
        if self.moves <= 14:
            self.app.unlock("Memory Meester")
        self.app.snd.victory()
        mv = "Moves" if self.en else "Zetten"
        pop = tk.Frame(self.win, bg="#111318", highlightbackground=RED, highlightthickness=2)
        pop.place(relx=0.5, rely=0.52, anchor="center", width=330, height=180)
        tk.Label(pop, text=self._t("GEHEUGEN GEOPTIMALISEERD!"), bg="#111318", fg="#FFF", font=(FONT, 12, "bold")).pack(pady=(16, 4))
        tk.Label(pop, text=f"{mv}: {self.moves}  {self._rec_txt(is_best)}", bg="#111318", fg=GOLD, font=(FONT, 11, "bold")).pack()
        tk.Label(pop, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", bg="#111318", fg=GREEN, font=(FONT, 10, "bold")).pack(pady=8)
        self._btn(pop, self._t("Top! Sluiten"), self.close, bg=RED, fg="#FFF", bd=0, padx=14, pady=5, font=(FONT, 10, "bold")).pack(pady=6)


class MiniGameSnake(_BaseGame):
    """Mini-game 5: Sticky Code Snake! Eat green bytes & bonus tosti's."""

    N, CELL = 18, 22

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 5/8 — Sticky Code Snake!", 420, 475)
        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="Length: 0  •  Best: 0" if self.en else "Lengte: 0  •  Best: 0", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        self.cv = tk.Canvas(self.win, width=self.N * self.CELL, height=self.N * self.CELL, bg="#12141A", highlightthickness=1, highlightbackground=RED)
        self.cv.pack(pady=10)
        tk.Label(self.win, text=self._t("◀ ▲ ▼ ▶ of WASD (of USB knoppen om te sturen)"), bg=BG, fg=MUTED, font=(FONT, 8)).pack()
        self.win.bind("<Up>", lambda e: self._dir(0, -1))
        self.win.bind("<Down>", lambda e: self._dir(0, 1))
        self.win.bind("<Left>", lambda e: self._dir(-1, 0))
        self.win.bind("<Right>", lambda e: self._dir(1, 0))
        self.win.bind("<w>", lambda e: self._dir(0, -1))
        self.win.bind("<s>", lambda e: self._dir(0, 1))
        self.win.bind("<a>", lambda e: self._dir(-1, 0))
        self.win.bind("<d>", lambda e: self._dir(1, 0))
        self.win.bind("<Escape>", lambda e: self.close())
        self._restart()

    def _dir(self, dx, dy):
        if (dx, dy) != (-self.vec[0], -self.vec[1]):
            self.next_vec = (dx, dy)

    def nudge(self, dx):
        vx, vy = self.vec
        self.next_vec = (vy, -vx) if dx < 0 else (-vy, vx)

    def action(self):
        if self.over:
            self._restart()
        else:
            self.nudge(1)

    def _spawn_food(self):
        free = [(x, y) for x in range(self.N) for y in range(self.N) if (x, y) not in self.snake]
        self.food = random.choice(free) if free else (0, 0)
        self.bonus = random.random() < 0.25

    def _restart(self):
        self.snake = [(9, 9), (8, 9), (7, 9)]
        self.vec = (1, 0)
        self.next_vec = (1, 0)
        self.score = 0
        self.over = False
        self._spawn_food()
        self.step()

    def step(self):
        if not self.running or self.over:
            return
        self.vec = self.next_vec
        hx, hy = self.snake[0][0] + self.vec[0], self.snake[0][1] + self.vec[1]
        if not (0 <= hx < self.N and 0 <= hy < self.N) or (hx, hy) in self.snake:
            self.over = True
            self._finish()
            return
        self.snake.insert(0, (hx, hy))
        if (hx, hy) == self.food:
            self.score += 3 if self.bonus else 1
            self.app.snd.coin()
            self._spawn_food()
        else:
            self.snake.pop()
        self._draw()
        self._schedule(max(75, 130 - self.score * 2), self.step)

    def _draw(self):
        self.cv.delete("all")
        c = self.CELL
        fx, fy = self.food
        self.cv.create_oval(fx * c + 3, fy * c + 3, (fx + 1) * c - 3, (fy + 1) * c - 3, fill=GOLD if self.bonus else GREEN, outline="#FFF")
        for idx, (sx, sy) in enumerate(self.snake):
            col = RED if idx == 0 else ("#4FC3F7" if idx % 2 == 0 else "#29B6F6")
            self.cv.create_rectangle(sx * c + 2, sy * c + 2, (sx + 1) * c - 2, (sy + 1) * c - 2, fill=col, outline="")
        best = self.app.d.get("high_scores", {}).get("snake", 0)
        ln = "Length" if self.en else "Lengte"
        self.lbl.config(text=f"Score: {self.score}  •  {ln}: {len(self.snake)}  •  Best: {max(best, self.score)}")

    def _finish(self):
        self.app.snd.buzz()
        is_best, xp, coins = self._reward("snake", self.score, max(10, self.score * 4), max(4, self.score * 2))
        self.app.quest_bump("snake_pts", self.score, max_mode=True)
        if self.score >= 12:
            self.app.unlock("Snake Charmer")
        self.cv.create_rectangle(35, 120, 360, 275, fill="#111318", outline=RED, width=3)
        self.cv.create_text(198, 150, text="SEGMENTATION FAULT!", fill="#FFF", font=(FONT, 13, "bold"))
        self.cv.create_text(198, 180, text=f"Score: {self.score}  {self._rec_txt(is_best)}", fill=GOLD, font=(FONT, 11, "bold"))
        self.cv.create_text(198, 208, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", fill=GREEN, font=(FONT, 10, "bold"))
        self.cv.create_window(140, 246, window=self._btn(self.cv, self._t("Opnieuw"), self._restart, bg=RED, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 9, "bold")))
        self.cv.create_window(255, 246, window=self._btn(self.cv, self._t("Sluiten"), self.close, bg=CARD, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 9)))


class MiniGame2048(_BaseGame):
    """Mini-game 6: Merge Conflicts 2048! Combine blocks with arrow keys."""

    COLS = {
        0: ("#252936", MUTED), 2: ("#394053", "#FFF"), 4: ("#4A536B", "#FFF"),
        8: ("#E65100", "#FFF"), 16: ("#D84315", "#FFF"), 32: ("#B21B21", "#FFF"),
        64: ("#D32F2F", "#FFF"), 128: ("#F9A825", "#111"), 256: ("#FBC02D", "#111"),
        512: ("#4CAF50", "#FFF"), 1024: ("#00ACC1", "#FFF"), 2048: (GOLD, "#111"),
    }

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 6/8 — Merge Conflicts 2048!", 400, 480)
        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="Score: 0", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        grid = tk.Frame(self.win, bg="#111318", padx=8, pady=8)
        grid.pack(pady=10)
        self.cells = [[tk.Label(grid, text="", width=6, height=3, font=(FONT, 14, "bold")) for _ in range(4)] for _ in range(4)]
        for r in range(4):
            for c in range(4):
                self.cells[r][c].grid(row=r, column=c, padx=5, pady=5)
        brow = tk.Frame(self.win, bg=BG)
        brow.pack()
        self._btn(brow, self._t("Reset Spel"), self._restart, bg=CARD, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 9)).pack(side="left", padx=6)
        self._btn(brow, self._t("Cash In & Sluit"), self._finish, bg=RED, fg="#FFF", bd=0, padx=10, pady=4, font=(FONT, 9, "bold")).pack(side="left", padx=6)
        tk.Label(self.win, text=self._t("Pijltjestoetsen / WASD om blokjes samen te voegen (512 = badge!)"), bg=BG, fg=MUTED, font=(FONT, 8)).pack(pady=6)

        self.win.bind("<Left>", lambda e: self.move("L"))
        self.win.bind("<Right>", lambda e: self.move("R"))
        self.win.bind("<Up>", lambda e: self.move("U"))
        self.win.bind("<Down>", lambda e: self.move("D"))
        self.win.bind("<a>", lambda e: self.move("L"))
        self.win.bind("<d>", lambda e: self.move("R"))
        self.win.bind("<w>", lambda e: self.move("U"))
        self.win.bind("<s>", lambda e: self.move("D"))
        self.win.bind("<Escape>", lambda e: self.close())
        self._restart()

    def action(self):
        if self.over:
            self._restart()
            return
        before = [row[:] for row in self.board]
        for d in ("L", "U", "R", "D"):
            self.move(d)
            if self.board != before or self.over:
                break

    def _restart(self):
        self.board = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.over = False
        self._add_tile()
        self._add_tile()
        self._render()

    def _add_tile(self):
        empties = [(r, c) for r in range(4) for c in range(4) if self.board[r][c] == 0]
        if empties:
            r, c = random.choice(empties)
            self.board[r][c] = 4 if random.random() < 0.1 else 2

    @staticmethod
    def _slide_row(row):
        vals = [v for v in row if v]
        out, gained = [], 0
        i = 0
        while i < len(vals):
            if i + 1 < len(vals) and vals[i] == vals[i + 1]:
                nv = vals[i] * 2
                out.append(nv)
                gained += nv
                i += 2
            else:
                out.append(vals[i])
                i += 1
        return out + [0] * (4 - len(out)), gained

    def move(self, d):
        if not self.running or self.over:
            return False
        before = [r[:] for r in self.board]
        gained = 0
        if d == "L":
            for r in range(4):
                self.board[r], g = self._slide_row(self.board[r])
                gained += g
        elif d == "R":
            for r in range(4):
                nr, g = self._slide_row(self.board[r][::-1])
                self.board[r] = nr[::-1]
                gained += g
        elif d == "U":
            for c in range(4):
                nr, g = self._slide_row([self.board[r][c] for r in range(4)])
                for r in range(4):
                    self.board[r][c] = nr[r]
                gained += g
        elif d == "D":
            for c in range(4):
                nr, g = self._slide_row([self.board[r][c] for r in range(3, -1, -1)])
                for r in range(4):
                    self.board[3 - r][c] = nr[r]
                gained += g
        if self.board != before:
            self.score += gained
            self._add_tile()
            self.app.snd.coin() if gained >= 32 else self.app.snd.flap()
            self._render()
            if max(v for r in self.board for v in r) >= 512:
                self.app.unlock("Merge Meester")
            if not self._can_move():
                self.over = True
                self._finish()
            return True
        return False

    def _can_move(self):
        for r in range(4):
            for c in range(4):
                v = self.board[r][c]
                if v == 0 or (r < 3 and self.board[r + 1][c] == v) or (c < 3 and self.board[r][c + 1] == v):
                    return True
        return False

    def _render(self):
        best = self.app.d.get("high_scores", {}).get("merge", 0)
        mx = "Max Tile" if self.en else "Max Blok"
        self.lbl.config(text=f"Score: {self.score}  •  {mx}: {max(v for r in self.board for v in r)}  •  Best: {max(best, self.score)}")
        for r in range(4):
            for c in range(4):
                v = self.board[r][c]
                bg, fg = self.COLS.get(v, (GOLD, "#111"))
                self.cells[r][c].config(text=str(v) if v else "", bg=bg, fg=fg)

    def _finish(self):
        self.over = True
        self._reward("merge", self.score, max(12, self.score // 20), max(5, self.score // 45))
        self.app.quest_bump("merge_pts", self.score, max_mode=True)
        if max(v for r in self.board for v in r) >= 512:
            self.app.unlock("Merge Meester")
        self.app.snd.victory()
        self.close()


class MiniGameRhythm(_BaseGame):
    """Mini-game 7: De Vagant Beat Drop! 4-lane 8-bit rhythm challenge."""

    LANE_COLS = ["#FF5252", "#4FC3F7", "#4CAF50", GOLD]
    LANE_KEYS = ["D", "F", "J", "K"]

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 7/8 — De Vagant Beat Drop!", 420, 500)
        self.cw, self.ch = 400, 420
        self.notes = []
        self.score = 0
        self.combo = 0
        self.ticks = 0
        self.max_ticks = 260
        self.feedback = ""
        self.over = False

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="Score: 0  •  Combo x0", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        self.cv = tk.Canvas(self.win, width=self.cw, height=self.ch, bg="#12141A", highlightthickness=0)
        self.cv.pack()
        tk.Label(self.win, text=self._t("Toetsen D F J K (of ◀ ▼ ▲ ▶) op het ritme bij de rode lijn!"), bg=BG, fg=MUTED, font=(FONT, 8)).pack(pady=6)

        for idx, sym in enumerate(("d", "f", "j", "k")):
            self.win.bind(f"<{sym}>", lambda e, l=idx: self.hit(l))
        for idx, sym in enumerate(("Left", "Down", "Up", "Right")):
            self.win.bind(f"<{sym}>", lambda e, l=idx: self.hit(l))
        self.cv.bind("<Button-1>", lambda e: self.hit(min(3, max(0, e.x // 100))))
        self.win.bind("<Escape>", lambda e: self.close())
        self.step()

    def nudge(self, dx):
        self.hit(1 if dx < 0 else 2)

    def action(self):
        self.hit(random.randint(0, 3))

    def hit(self, lane):
        if not self.running or self.over:
            return
        target_y = self.ch - 55
        best_note = None
        best_dist = 999
        for n in self.notes:
            if n[0] == lane and abs(n[1] - target_y) < best_dist:
                best_dist = abs(n[1] - target_y)
                best_note = n
        if best_note and best_dist <= 36:
            self.notes.remove(best_note)
            self.combo += 1
            pts = 30 if best_dist <= 16 else 15
            self.score += pts * min(3, 1 + self.combo // 8)
            self.feedback = "PERFECT!" if best_dist <= 16 else ("GOOD!" if self.en else "GOED!")
            self.app.snd.coin() if pts == 30 else self.app.snd.dance()
        else:
            self.combo = 0
            self.feedback = "MISS!" if self.en else "MIS!"
            self.app.snd.buzz()

    def step(self):
        if not self.running or self.over:
            return
        self.ticks += 1
        if self.ticks % 7 == 0 and self.ticks < self.max_ticks - 25:
            self.notes.append([random.randint(0, 3), -12])
        kept = []
        for n in self.notes:
            n[1] += 6.2
            if n[1] <= self.ch:
                kept.append(n)
            else:
                self.combo = 0
        self.notes = kept
        self._draw()
        if self.ticks >= self.max_ticks and not self.notes:
            self.over = True
            self._finish()
            return
        self._schedule(42, self.step)

    def _draw(self):
        self.cv.delete("all")
        ty = self.ch - 55
        for l in range(4):
            cx = l * 100 + 50
            self.cv.create_line(l * 100, 0, l * 100, self.ch, fill="#222530")
            self.cv.create_oval(cx - 22, ty - 14, cx + 22, ty + 14, outline=self.LANE_COLS[l], width=2)
            self.cv.create_text(cx, ty, text=self.LANE_KEYS[l], fill=MUTED, font=(FONT, 10, "bold"))
        self.cv.create_line(0, ty, self.cw, ty, fill=RED, width=2)
        for lane, ny in self.notes:
            cx = lane * 100 + 50
            self.cv.create_oval(cx - 20, ny - 12, cx + 20, ny + 12, fill=self.LANE_COLS[lane], outline="#FFF", width=2)
        if self.feedback:
            self.cv.create_text(200, 40, text=self.feedback, fill=GOLD, font=(FONT, 14, "bold"))
        pct = min(100, int(self.ticks * 100 / self.max_ticks))
        self.lbl.config(text=f"Score: {self.score}  •  Combo x{self.combo}  •  Track {pct}%")

    def _finish(self):
        is_best, xp, coins = self._reward("rhythm", self.score, max(12, self.score // 8), max(8, self.score // 22))
        self.app.quest_bump("rhythm_pts", self.score, max_mode=True)
        if self.score >= 300:
            self.app.unlock("Vagant DJ")
        self.app.snd.victory()
        self.cv.create_rectangle(45, 120, 355, 290, fill="#111318", outline=RED, width=3)
        self.cv.create_text(200, 154, text=self._t("SET AFGELOPEN!"), fill="#FFF", font=(FONT, 15, "bold"))
        self.cv.create_text(200, 186, text=f"Score: {self.score}  {self._rec_txt(is_best)}", fill=GOLD, font=(FONT, 11, "bold"))
        self.cv.create_text(200, 214, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", fill=GREEN, font=(FONT, 10, "bold"))
        self.cv.create_window(200, 256, window=self._btn(self.cv, self._t("Top! Sluiten"), self.close, bg=RED, fg="#FFF", bd=0, padx=14, pady=4, font=(FONT, 10, "bold")))


class MiniGameRPG(_BaseGame):
    """Mini-game 8: BBG Dungeon Boss Battle! Turn-based 5-stage Sticky RPG."""

    BOSSES = [
        ("Spaghetti-Commit Slime", 65, 9, 25, 30, "#4CAF50"),
        ("Boze Uithof Alpha-Gans", 105, 13, 45, 50, "#4FC3F7"),
        ("VrijMiBo Force-Push Draak", 150, 17, 70, 75, "#FF5252"),
        ("Legacy Koala Daemon Lich", 200, 21, 100, 110, "#BA68C8"),
        ("4-Uurs ALV Eindbaas", 270, 25, 160, 180, GOLD),
    ]

    def __init__(self, app, stage=0):
        super().__init__(app, "Karel Arcade 8/8 — BBG Dungeon RPG!", 460, 480)
        self.stage = max(0, min(len(self.BOSSES) - 1, stage))
        lvl = app.d.get("level", 1)
        self.k_max_hp = 95 + lvl * 8
        self.k_hp = self.k_max_hp
        self.k_mp = 60
        self.stunned = False
        self.over = False
        self.msg = self._t("Kies een actie! (Toets 1-4)")

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        self.cv = tk.Canvas(self.win, width=440, height=270, bg="#12141A", highlightthickness=0)
        self.cv.pack(pady=8)
        self.log = tk.Label(self.win, text="", bg=BG, fg=GOLD, font=(FONT, 9, "bold"), wraplength=430)
        self.log.pack(pady=4)

        acts = tk.Frame(self.win, bg=BG)
        acts.pack(fill="x", padx=14, pady=6)
        for idx, (lbl, fn) in enumerate((
            ("[1] Git Attack", lambda: self.turn("atk")),
            ("[2] Koffie Crit (10MP)", lambda: self.turn("crit")),
            ("[3] Tosti Heal (12MP)", lambda: self.turn("heal")),
            ("[4] Lambda Spreuk (22MP)", lambda: self.turn("magic")),
        )):
            self._btn(acts, self._t(lbl), fn, bg=CARD, fg="#FFF", bd=0, pady=8, font=(FONT, 8, "bold")).pack(side="left", expand=True, fill="x", padx=3)
            self.win.bind(str(idx + 1), lambda e, f=fn: f())
        self.win.bind("<Escape>", lambda e: self.close())
        self._load_boss(self.stage)

    def _load_boss(self, st):
        self.stage = st
        b = self.BOSSES[st]
        b_raw, self.b_max_hp, self.b_atk, self.b_coins, self.b_xp, self.b_col = b
        self.b_name = self._t(b_raw)
        self.b_hp = self.b_max_hp
        self.stunned = False
        self.over = False
        self._render()

    def action(self):
        if not self.over:
            self.turn("atk")

    def turn(self, move):
        if not self.running or self.over:
            return
        dmg = 16 + self.app.d.get("level", 1) * 2
        if move == "atk":
            hit = random.randint(dmg - 3, dmg + 5)
            self.b_hp = max(0, self.b_hp - hit)
            self.k_mp = min(60, self.k_mp + 6)
            self.msg = f"Karel lands Git Attack for {hit} dmg!" if self.en else f"Karel doet Git Attack voor {hit} schade!"
            self.app.snd.smash()
        elif move == "crit":
            if self.k_mp < 10:
                self.app.snd.buzz()
                self.msg = "Not enough MP (min 10)!" if self.en else "Te weinig MP (min 10)!"
                self._render()
                return
            self.k_mp -= 10
            hit = random.randint(int(dmg * 1.6), int(dmg * 2.1))
            self.b_hp = max(0, self.b_hp - hit)
            self.stunned = random.random() < 0.45
            if self.en:
                self.msg = f"COFFEE CRIT! {hit} dmg{' (STUNNED!)' if self.stunned else '!'}"
            else:
                self.msg = f"KOFFIE CRIT! {hit} schade{' (VERDOOFD!)' if self.stunned else '!'}"
            self.app.snd.coffee()
        elif move == "heal":
            if self.k_mp < 12:
                self.app.snd.buzz()
                self.msg = "Not enough MP (min 12)!" if self.en else "Te weinig MP (min 12)!"
                self._render()
                return
            self.k_mp -= 12
            heal = 48
            self.k_hp = min(self.k_max_hp, self.k_hp + heal)
            self.msg = f"Ate a warm Sticky Tosti: +{heal} HP!" if self.en else f"Warme Sticky Tosti gegeten: +{heal} HP!"
            self.app.snd.pet()
        elif move == "magic":
            if self.k_mp < 22:
                self.app.snd.buzz()
                self.msg = "Not enough MP (min 22)!" if self.en else "Te weinig MP (min 22)!"
                self._render()
                return
            self.k_mp -= 22
            hit = random.randint(int(dmg * 2.3), int(dmg * 2.9))
            self.b_hp = max(0, self.b_hp - hit)
            self.msg = f"LAMBDA SPELL! {hit} magic dmg!" if self.en else f"LAMBDA SPREUK! {hit} magische schade!"
            self.app.snd.magic()

        if self.b_hp <= 0:
            self._boss_defeated()
            return

        if self.stunned:
            self.stunned = False
            self.msg += " | Boss was stunned!" if self.en else " | Eindbaas was verdoofd!"
        else:
            rage = 0 < self.b_hp <= int(self.b_max_hp * 0.4)
            bdmg = random.randint(max(4, self.b_atk - 4), self.b_atk + 4)
            if rage:
                bdmg = int(round(bdmg * 1.35))
            self.k_hp = max(0, self.k_hp - bdmg)
            if self.en:
                self.msg += f" | {'[RAGE!] ' if rage else ''}{self.b_name} hits back for {bdmg}!"
            else:
                self.msg += f" | {'[RAGE!] ' if rage else ''}{self.b_name} slaat terug voor {bdmg}!"
            if self.k_hp <= 0:
                self.over = True
                self.app.snd.buzz()
                self.msg = self._t("Karel viel flauw! Volgende keer beter!")
        self._render()

    def _boss_defeated(self):
        self.over = True
        self.app.snd.victory()
        _, xp, coins = self._reward("rpg", self.stage + 1, self.b_xp, self.b_coins)
        self.app.quest_bump("rpg_win", 1)
        self.app.unlock("Dungeon Held")
        if self.stage == len(self.BOSSES) - 1:
            self.app.unlock("Alle Bazen Verslagen")
        c_lbl = "Coins" if self.en else "Munten"
        v_lbl = "VICTORY over" if self.en else "OVERWINNING op"
        self.msg = f"{v_lbl} {self.b_name}! +{xp} XP +{coins} {c_lbl}!"
        self._render()
        if self.stage + 1 < len(self.BOSSES):
            n_lbl = "Next Boss" if self.en else "Volgende Baas"
            nxt = self._btn(self.cv, f"{n_lbl} ({self.stage + 2}/5) ->", lambda: self._load_boss(self.stage + 1), bg=GREEN, fg="#FFF", bd=0, padx=10, pady=5, font=(FONT, 9, "bold"))
            self.cv.create_window(220, 235, window=nxt)

    def _render(self):
        rage = 0 < self.b_hp <= int(self.b_max_hp * 0.4)
        b_lbl = "Boss" if self.en else "Baas"
        self.lbl.config(text=f"{b_lbl} {self.stage + 1}/5: {self.b_name}{' [RAGE]' if rage else ''}   •   Karel MP: {self.k_mp}/60")
        self.cv.delete("all")
        sprite = self.app.mg_sprite(self.app.d)
        if sprite:
            self.cv.create_image(95, 130, image=sprite)
        self.cv.create_rectangle(35, 185, 155, 200, fill="#222530", outline="#FFF")
        self.cv.create_rectangle(35, 185, 35 + int(120 * self.k_hp / self.k_max_hp), 200, fill=GREEN, outline="")
        self.cv.create_text(95, 212, text=f"Karel HP: {self.k_hp}/{self.k_max_hp}", fill=FG, font=(FONT, 8, "bold"))

        b_outline = GOLD if rage else "#FFF"
        self.cv.create_oval(300, 75, 390, 165, fill=self.b_col, outline=b_outline, width=4 if rage else 3)
        if rage:
            self.cv.create_text(345, 60, text=self._t("RAZEND!"), fill=GOLD, font=(FONT, 9, "bold"))
        self.cv.create_text(345, 118, text=">.<" if self.b_hp == 0 else ("@_@" if rage else "O_O"), fill="#111", font=(FONT, 16, "bold"))
        self.cv.create_rectangle(275, 185, 415, 200, fill="#222530", outline="#FFF")
        self.cv.create_rectangle(275, 185, 275 + int(140 * self.b_hp / self.b_max_hp), 200, fill=RED, outline="")
        self.cv.create_text(345, 212, text=f"HP: {self.b_hp}/{self.b_max_hp}", fill=FG, font=(FONT, 8, "bold"))
        self.log.config(text=self.msg)
