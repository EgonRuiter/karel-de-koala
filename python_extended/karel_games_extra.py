#!/usr/bin/env python3
"""Arcade Mini-Games 9 & 10 (Uithof Ganzen Run + Koala Server Rescue) for Karel de Koala."""

import random
import tkinter as tk

from karel_games import BG, CARD, FG, FONT, GOLD, GREEN, MUTED, RED, _BaseGame


class MiniGameGans(_BaseGame):
    """Mini-game 9: Uithof Ganzen Run! Jump over Uithof geese & Tram 22."""

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 9/10 — Uithof Ganzen Run!", 460, 420)
        self.score = 0
        self.best_dist = 0
        self.lives = 3
        self.tick_n = 0
        self.ky = 240.0
        self.kvy = 0.0
        self.jumps = 0
        self.ground = 250.0
        self.obs = []  # [x, kind, y, speed]  kind: gans, tram, deadline, leaf, tosti, coin

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        self.cv = tk.Canvas(self.win, width=460, height=345, bg="#141822", highlightthickness=0)
        self.cv.pack()
        tk.Label(self.win, text=self._t("Spatie / Omhoog / Klik = Spring (Dubbel-sprong mogelijk!)"), bg=BG, fg=MUTED, font=(FONT, 8)).pack(pady=3)

        self.cv.bind("<Button-1>", lambda e: self.jump())
        self.win.bind("<space>", lambda e: self.jump())
        self.win.bind("<Up>", lambda e: self.jump())
        self.win.bind("<Escape>", lambda e: self.close())
        self.win.after(40, self.step)

    def action(self):
        self.jump()

    def jump(self):
        if not self.running or self.lives <= 0:
            return
        if self.jumps < 2:
            self.kvy = -12.8 if self.jumps == 0 else -11.2
            self.jumps += 1
            self.app.snd.jump()

    def _restart(self):
        self.score = 0
        self.lives = 3
        self.tick_n = 0
        self.ky = self.ground
        self.kvy = 0.0
        self.jumps = 0
        self.obs.clear()
        self.step()

    def step(self):
        if not self.running:
            return
        if self.lives <= 0:
            self._finish()
            return
        self.tick_n += 1
        self.kvy += 1.05
        self.ky += self.kvy
        if self.ky >= self.ground:
            self.ky = self.ground
            self.kvy = 0.0
            self.jumps = 0

        if self.tick_n % 6 == 0:
            self.score += 1

        if self.tick_n % max(22, 38 - self.score // 40) == 0:
            r = random.random()
            spd = min(11.5, 6.2 + self.score / 85.0)
            if r < 0.42:
                self.obs.append([480.0, "gans", self.ground + 6, spd])
            elif r < 0.62:
                self.obs.append([480.0, "tram", self.ground - 12, spd + 0.8])
            elif r < 0.82:
                self.obs.append([480.0, "leaf", self.ground - random.randint(24, 92), spd])
            elif r < 0.93:
                self.obs.append([480.0, "coin", self.ground - random.randint(36, 100), spd])
            else:
                self.obs.append([480.0, "tosti", self.ground - random.randint(45, 105), spd])

        kx0, kx1 = 62, 98
        ky0, ky1 = self.ky - 22, self.ky + 22
        kept = []
        for ob in self.obs:
            ob[0] -= ob[3]
            ox, kind, oy, _ = ob
            if ox < -45:
                continue
            hit = (kx0 < ox + 18) and (kx1 > ox - 18) and (ky0 < oy + 16) and (ky1 > oy - 16)
            if hit:
                if kind in ("gans", "tram"):
                    self.lives -= 1
                    self.app.snd.gans()
                elif kind == "leaf":
                    self.score += 12
                    self.app.snd.eat()
                elif kind == "coin":
                    self.score += 18
                    self.app.snd.coin()
                elif kind == "tosti":
                    self.score += 30
                    self.app.snd.craft()
                continue
            kept.append(ob)
        self.obs = kept

        path_lbl = "Uithof Bike Path" if self.en else "Uithof Fietspad"
        lv_lbl = "Lives" if self.en else "Levens"
        self.lbl.config(text=f"{path_lbl}  •  Score: {self.score}  •  {lv_lbl}: {'♥' * max(0, self.lives)}")
        self._draw()
        self._schedule(33, self.step)

    def _draw(self):
        self.cv.delete("all")
        self.cv.create_rectangle(0, self.ground + 24, 460, 345, fill="#1E2B22", outline="")
        self.cv.create_line(0, self.ground + 24, 460, self.ground + 24, fill=GREEN, width=3)
        self.cv.create_text(230, 58, text="BBG  <-->  Educatorium  <-->  't Gras", fill="#252A36", font=(FONT, 11, "bold"))

        sprite = self.app.mg_sprite(self.app.d)
        if sprite:
            self.cv.create_image(80, self.ky - 8, image=sprite)
        else:
            self.cv.create_oval(62, self.ky - 20, 98, self.ky + 20, fill="#8E949E")

        for ox, kind, oy, _ in self.obs:
            if kind == "gans":
                self.cv.create_oval(ox - 16, oy - 12, ox + 16, oy + 14, fill="#E2E5EB", outline="#FF9800", width=2)
                self.cv.create_text(ox, oy, text=self._t("GANS"), fill="#111", font=(FONT, 7, "bold"))
            elif kind == "tram":
                self.cv.create_rectangle(ox - 24, oy - 16, ox + 24, oy + 24, fill=GOLD, outline=RED, width=2)
                self.cv.create_text(ox, oy + 4, text="TRAM 22", fill="#111", font=(FONT, 7, "bold"))
            elif kind == "tosti":
                self.cv.create_polygon(ox - 12, oy + 10, ox, oy - 12, ox + 12, oy + 10, fill="#D7A15B", outline="#FFF")
            elif kind == "coin":
                self.cv.create_oval(ox - 10, oy - 10, ox + 10, oy + 10, fill=GOLD, outline="#FFF")
                self.cv.create_text(ox, oy, text="S", fill="#111", font=(FONT, 8, "bold"))
            else:
                self.cv.create_oval(ox - 10, oy - 7, ox + 10, oy + 7, fill=GREEN, outline="#A5D6A7")

    def _finish(self):
        self.app.snd.victory() if self.score >= 150 else self.app.snd.buzz()
        base_c = max(6, self.score // 7)
        if getattr(self.app, "campus_tag", "") == "gans_coins":
            base_c = int(round(base_c * 1.25))
        is_best, xp, coins = self._reward("gans", self.score, max(12, self.score // 4), base_c)
        self.app.quest_bump("gans_pts", self.score, max_mode=True)
        if self.score >= 150:
            self.app.unlock("Ganzen Sprinter")
        self.cv.create_rectangle(55, 85, 405, 255, fill="#111318", outline=RED, width=3)
        self.cv.create_text(230, 118, text=self._t("GEPAKT DOOR EEN GANS!"), fill="#FFF", font=(FONT, 13, "bold"))
        self.cv.create_text(230, 148, text=f"Score: {self.score}  {self._rec_txt(is_best)}", fill=GOLD, font=(FONT, 11, "bold"))
        self.cv.create_text(230, 178, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", fill=GREEN, font=(FONT, 10, "bold"))
        self.cv.create_window(175, 222, window=self._btn(self.cv, self._t("Opnieuw"), self._restart, bg=RED, fg="#FFF", bd=0, padx=12, pady=4, font=(FONT, 9, "bold")))
        self.cv.create_window(290, 222, window=self._btn(self.cv, self._t("Sluiten"), self.close, bg=CARD, fg="#FFF", bd=0, padx=12, pady=4, font=(FONT, 9)))


class MiniGameKoala(_BaseGame):
    """Mini-game 10: Koala Server Rescue! Typ dev-woorden of klik Patch om Koala te redden."""

    WORDS = (
        "git", "fix", "push", "koala", "tosti", "kbg", "bbg", "sudo", "merge",
        "code", "wifi", "ping", "lint", "test", "java", "hash", "pipe", "sync",
    )

    def __init__(self, app):
        super().__init__(app, "Karel Arcade 10/10 — Koala Server Rescue!", 450, 480)
        self.score = 0
        self.hp = 5
        self.tick_n = 0
        self.typed = ""
        self.enemies = []  # [x, y, word, spd]

        hdr = tk.Frame(self.win, bg=RED, height=40)
        hdr.pack(fill="x")
        self.lbl = tk.Label(hdr, text="", bg=RED, fg="#FFF", font=(FONT, 10, "bold"))
        self.lbl.pack(pady=9)
        self.cv = tk.Canvas(self.win, width=430, height=310, bg="#11131A", highlightthickness=0)
        self.cv.pack(pady=8)

        ctrl = tk.Frame(self.win, bg=BG)
        ctrl.pack(fill="x", padx=16, pady=4)
        self.inp_lbl = tk.Label(ctrl, text="Type word -> []" if self.en else "Typ woord -> []", bg=BG, fg="#4FC3F7", font=(FONT, 10, "bold"))
        self.inp_lbl.pack(side="left")
        self._btn(ctrl, self._t("Nood-Patch! (Klik / Spatie)"), self.action, bg=GREEN, fg="#FFF", bd=0, padx=10, pady=5,
                  font=(FONT, 8, "bold")).pack(side="right")

        self.win.bind("<KeyPress>", self._on_key)
        self.win.bind("<space>", lambda e: self.action())
        self.win.bind("<Escape>", lambda e: self.close())
        self._spawn()
        self.step()

    def _spawn(self):
        w = random.choice(self.WORDS)
        spd = min(2.4, 0.85 + self.score / 220.0)
        self.enemies.append([random.randint(45, 360), 18.0, w, spd])

    def action(self):
        if not self.running or self.hp <= 0 or not self.enemies:
            return
        # Emergency patch kills closest enemy cleanly for mouse / RP2350 button players
        self.enemies.sort(key=lambda e: e[1], reverse=True)
        w = self.enemies.pop(0)[2]
        self.typed = ""
        self.score += 12 + len(w) * 2
        self.app.snd.smash()
        self._draw()

    def _on_key(self, e):
        if not self.running or self.hp <= 0:
            return
        ch = (e.char or "").lower()
        if e.keysym == "BackSpace":
            self.typed = self.typed[:-1]
            self._draw()
            return
        if not ch or not ch.isalpha():
            return
        cand = self.typed + ch
        matches = [en for en in self.enemies if en[2].startswith(cand)]
        if not matches:
            matches = [en for en in self.enemies if en[2].startswith(ch)]
            cand = ch if matches else ""
        self.typed = cand
        exact = [en for en in matches if en[2] == self.typed]
        if exact:
            target = max(exact, key=lambda en: en[1])
            self.enemies.remove(target)
            self.score += 16 + len(target[2]) * 4
            self.typed = ""
            self.app.snd.trivia_ok()
        self._draw()

    def step(self):
        if not self.running:
            return
        if self.hp <= 0:
            self._finish()
            return
        self.tick_n += 1
        if self.tick_n % max(22, 42 - self.score // 25) == 0 and len(self.enemies) < 6:
            self._spawn()
        alive = []
        for en in self.enemies:
            en[1] += en[3]
            if en[1] >= 268:
                self.hp -= 1
                self.app.snd.buzz()
            else:
                alive.append(en)
        self.enemies = alive
        self.lbl.config(text=f"Koala Server HP: {'♥' * max(0, self.hp)}   •   Score: {self.score}")
        self._draw()
        self._schedule(48, self.step)

    def _draw(self):
        tw = "Type word" if self.en else "Typ woord"
        self.inp_lbl.config(text=f"{tw} -> [{self.typed or '...'}]")
        self.cv.delete("all")
        self.cv.create_rectangle(10, 268, 420, 304, fill="#1E222E", outline=RED, width=2)
        self.cv.create_text(215, 286, text=self._t("[ STICKY KOALA SERVER RACK — BESCHERM DE KERN! ]"), fill=GOLD, font=(FONT, 9, "bold"))
        for ex, ey, w, _ in self.enemies:
            hl = self.typed and w.startswith(self.typed)
            bg_c = "#3A1C22" if hl else CARD
            self.cv.create_rectangle(ex - 36, ey - 13, ex + 36, ey + 13, fill=bg_c, outline=GOLD if hl else RED, width=2 if hl else 1)
            self.cv.create_text(ex, ey, text=w, fill=GOLD if hl else "#FFF", font=(FONT, 9, "bold"))

    def _finish(self):
        is_best, xp, coins = self._reward("koala", self.score, max(14, self.score // 5), max(7, self.score // 10))
        self.app.quest_bump("koala_pts", self.score, max_mode=True)
        if self.score >= 180:
            self.app.unlock("Koala Verdediger")
        self.app.snd.victory()
        self.cv.create_rectangle(45, 85, 385, 245, fill="#111318", outline=RED, width=3)
        end_txt = self._t("KOALA SERVER GERED!" if self.score >= 120 else "502 BAD GATEWAY!")
        self.cv.create_text(215, 118, text=end_txt, fill="#FFF", font=(FONT, 13, "bold"))
        self.cv.create_text(215, 148, text=f"Score: {self.score}  {self._rec_txt(is_best)}", fill=GOLD, font=(FONT, 11, "bold"))
        self.cv.create_text(215, 178, text=f"+{xp} XP   +{coins} {self._coins_lbl()}", fill=GREEN, font=(FONT, 10, "bold"))
        self.cv.create_window(215, 216, window=self._btn(self.cv, self._t("Top! Sluiten"), self.close, bg=RED, fg="#FFF", bd=0, padx=14, pady=4, font=(FONT, 9, "bold")))
