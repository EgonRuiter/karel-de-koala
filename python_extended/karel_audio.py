#!/usr/bin/env python3
"""Warm polyphonic PCM synth & chiptune engine (pure Python 3 stdlib) for Karel de Koala."""

from array import array
import ctypes
import io
import math
import os
import queue
import random
import shutil
import subprocess
import tempfile
import threading
import time
import wave

try:
    import winsound
except ImportError:
    winsound = None

SR = 22050
WT_N = 512

NOTE_HZ = {
    "R": 0.0,
    "C2": 65.41, "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.00, "A2": 110.00, "B2": 123.47,
    "C3": 130.81, "D3": 146.83, "Eb3": 155.56, "E3": 164.81, "F3": 174.61, "G3": 196.00,
    "Ab3": 207.65, "A3": 220.00, "Bb3": 233.08, "B3": 246.94,
    "C4": 261.63, "Db4": 277.18, "D4": 293.66, "Eb4": 311.13, "E4": 329.63, "F4": 349.23,
    "Gb4": 369.99, "G4": 392.00, "Ab4": 415.30, "A4": 440.00, "Bb4": 466.16, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "Eb5": 622.25, "E5": 659.25, "F5": 698.46, "G5": 783.99,
    "Ab5": 830.61, "A5": 880.00, "Bb5": 932.33, "B5": 987.77,
    "C6": 1046.50, "D6": 1174.66, "E6": 1318.51,
}

MUSIC_TRACKS = {
    "off": ("Uit", ""),
    "lofi": ("Stickykamer Lo-Fi", "Warme Rhodes-akkoorden & diepe bas"),
    "disco": ("De Vagant Synth-Disco", "Vrolijke warme retro groove"),
    "study": ("BBG Focus Chill", "Zachte ambient synthwave voor studie"),
    "arcade": ("Arcade 8-Bit Warm", "Zachte chiptune avonturenmuziek"),
    "uithof": ("Tram 22 Campus", "Opgewekte Utrecht Science Park tune"),
}


def _build_wavetables():
    """Precompute band-limited harmonic wavetables (no harsh aliasing!)."""
    wt = {}
    harmonics = {
        "sine": ((1, 1.0),),
        "tri": ((1, 1.0), (3, -0.11), (5, 0.04)),
        "rhodes": ((1, 1.0), (2, 0.28), (3, 0.09), (4, 0.03)),
        "bell": ((1, 1.0), (2, 0.45), (3, 0.16), (4, 0.08)),
        "soft_sq": ((1, 1.0), (3, 0.32), (5, 0.14), (7, 0.06)),
        "soft_pulse": ((1, 1.0), (2, 0.52), (3, 0.24), (4, 0.10)),
        "warm_saw": ((1, 1.0), (2, 0.46), (3, 0.24), (4, 0.12), (5, 0.06)),
    }
    two_pi = 2.0 * math.pi
    for name, hs in harmonics.items():
        tbl = []
        peak = 0.001
        for i in range(WT_N):
            ph = two_pi * (i / WT_N)
            v = sum(amp * math.sin(k * ph) for k, amp in hs)
            tbl.append(v)
            if abs(v) > peak:
                peak = abs(v)
        wt[name] = [v / peak for v in tbl]
    # Compatibility aliases
    wt["pulse25"] = wt["soft_pulse"]
    wt["pulse12"] = wt["bell"]
    wt["square"] = wt["soft_sq"]
    wt["saw"] = wt["warm_saw"]
    return wt


WAVETABLES = _build_wavetables()


def _render_tone(buf, start_idx, f0, f1, dur_s, wave_type="rhodes", vol=0.18,
                 attack=0.012, release=0.045, vibrato=0.0, lp=0.35):
    """Render a smooth envelope-shaped, low-pass-filtered tone into buf."""
    n = max(1, int(dur_s * SR))
    end = min(len(buf), start_idx + n)
    att_n = max(2, int(attack * SR))
    rel_n = max(4, int(release * SR))
    tbl = WAVETABLES.get(wave_type)
    is_noise = (wave_type == "noise")
    phase = 0.0
    seed = 13579
    lp_val = 0.0
    alpha = max(0.04, min(1.0, lp))
    scale = 28000.0 * vol
    for i in range(end - start_idx):
        if f0 <= 0 and f1 <= 0 and not is_noise:
            continue
        t = i / n
        freq = f0 + (f1 - f0) * t
        if vibrato > 0.0:
            freq *= 1.0 + vibrato * math.sin(2.0 * math.pi * 5.2 * (i / SR))
        if i < att_n:
            env = 0.5 - 0.5 * math.cos(math.pi * (i / att_n))
        else:
            env = math.exp(-2.2 * ((i - att_n) / max(1, n - att_n)))
        rem = n - i
        if rem < rel_n:
            env *= 0.5 - 0.5 * math.cos(math.pi * (rem / rel_n))
        if is_noise:
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            raw = (seed / 1073741824.0) - 1.0
        else:
            raw = tbl[int(phase * WT_N) % WT_N]
        lp_val += alpha * (raw - lp_val)
        idx = start_idx + i
        mixed = buf[idx] + int(lp_val * env * scale)
        if mixed > 31500:
            mixed = 31500
        elif mixed < -31500:
            mixed = -31500
        buf[idx] = mixed
        phase += max(0.0, freq) / SR


def _to_wav_bytes(buf):
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(buf.tobytes())
    return bio.getvalue()


def _seq_to_buf(total_s, events):
    buf = array("h", [0] * max(1, int(total_s * SR)))
    for ev in events:
        t_s, f0, f1, dur, wtype, vol = ev[:6]
        vib = ev[6] if len(ev) > 6 else 0.0
        rel = ev[7] if len(ev) > 7 else min(0.06, dur * 0.45)
        lp = ev[8] if len(ev) > 8 else (0.14 if wtype == "noise" else 0.42)
        _render_tone(buf, int(t_s * SR), f0, f1, dur, wtype, vol, release=rel, vibrato=vib, lp=lp)
    return buf


def _hz(n):
    return NOTE_HZ.get(n, 0.0) if isinstance(n, str) else float(n)


def _bake_sfx_bank():
    """Synthesize all 32 warm, pleasant polyphonic SFX clips once into RAM."""
    bank = {}

    def add(name, total_s, evs):
        bank[name] = _to_wav_bytes(_seq_to_buf(total_s, evs))

    add("coin", 0.25, [
        (0.00, 783.99, 783.99, 0.07, "bell", 0.16, 0.0, 0.03, 0.50),
        (0.055, 1046.50, 1046.50, 0.18, "bell", 0.18, 0.0, 0.08, 0.45),
        (0.055, 523.25, 523.25, 0.18, "tri", 0.11, 0.0, 0.08, 0.40),
    ])
    add("pet", 0.36, [
        (0.00, 440.00, 493.88, 0.11, "rhodes", 0.20, 0.0, 0.04, 0.45),
        (0.09, 523.25, 523.25, 0.11, "rhodes", 0.20, 0.0, 0.04, 0.45),
        (0.18, 659.25, 698.46, 0.17, "sine", 0.21, 0.012, 0.07, 0.55),
        (0.00, 220.00, 220.00, 0.32, "tri", 0.10, 0.0, 0.08, 0.35),
    ])
    add("eat", 0.26, [
        (0.00, 260.0, 180.0, 0.055, "tri", 0.15, 0.0, 0.02, 0.28),
        (0.00, 220.0, 140.0, 0.045, "noise", 0.08, 0.0, 0.02, 0.08),
        (0.09, 310.0, 210.0, 0.055, "tri", 0.16, 0.0, 0.02, 0.28),
        (0.18, 350.0, 240.0, 0.065, "rhodes", 0.16, 0.0, 0.03, 0.30),
    ])
    add("coffee", 0.38, [
        (0.00, 293.66, 392.00, 0.12, "sine", 0.18, 0.0, 0.04, 0.45),
        (0.11, 523.25, 523.25, 0.08, "rhodes", 0.17, 0.0, 0.03, 0.45),
        (0.18, 659.25, 659.25, 0.08, "rhodes", 0.17, 0.0, 0.03, 0.45),
        (0.25, 783.99, 783.99, 0.12, "bell", 0.16, 0.0, 0.06, 0.45),
    ])
    add("wash", 0.40, [
        (0.00, 320.0, 540.0, 0.14, "noise", 0.05, 0.0, 0.05, 0.10),
        (0.03, 440.00, 440.00, 0.09, "sine", 0.18, 0.0, 0.04, 0.6),
        (0.11, 523.25, 523.25, 0.09, "sine", 0.18, 0.0, 0.04, 0.6),
        (0.19, 659.25, 659.25, 0.09, "sine", 0.18, 0.0, 0.04, 0.6),
        (0.27, 783.99, 880.00, 0.12, "bell", 0.17, 0.0, 0.06, 0.5),
    ])
    add("jump", 0.18, [
        (0.00, 240.0, 560.0, 0.16, "sine", 0.19, 0.0, 0.04, 0.55),
        (0.00, 180.0, 340.0, 0.14, "tri", 0.12, 0.0, 0.04, 0.40),
    ])
    add("bounce", 0.13, [
        (0.00, 170.0, 380.0, 0.11, "sine", 0.20, 0.0, 0.04, 0.55),
        (0.00, 140.0, 90.0, 0.07, "tri", 0.11, 0.0, 0.03, 0.40),
    ])
    add("flap", 0.10, [
        (0.00, 320.0, 490.0, 0.09, "sine", 0.16, 0.0, 0.03, 0.55),
    ])
    add("smash", 0.15, [
        (0.00, 240.0, 88.0, 0.11, "sine", 0.24, 0.0, 0.03, 0.50),
        (0.00, 340.0, 140.0, 0.08, "tri", 0.14, 0.0, 0.03, 0.35),
        (0.03, 659.25, 783.99, 0.09, "bell", 0.11, 0.0, 0.04, 0.45),
    ])
    add("buzz", 0.22, [
        (0.00, 220.0, 196.0, 0.09, "tri", 0.18, 0.0, 0.03, 0.35),
        (0.10, 164.81, 146.83, 0.11, "tri", 0.18, 0.0, 0.04, 0.32),
    ])
    add("cooldown", 0.22, [
        (0.00, 349.23, 329.63, 0.08, "rhodes", 0.16, 0.0, 0.03, 0.38),
        (0.09, 261.63, 246.94, 0.11, "rhodes", 0.15, 0.0, 0.04, 0.35),
    ])
    add("sneeze", 0.26, [
        (0.00, 420.0, 620.0, 0.07, "sine", 0.15, 0.0, 0.02, 0.5),
        (0.08, 600.0, 220.0, 0.14, "noise", 0.11, 0.0, 0.05, 0.12),
        (0.08, 360.0, 180.0, 0.13, "tri", 0.14, 0.0, 0.05, 0.35),
    ])
    add("levelup", 0.72, [
        (0.00, 440.00, 440.00, 0.10, "rhodes", 0.18, 0.0, 0.03, 0.48),
        (0.10, 554.37, 554.37, 0.10, "rhodes", 0.18, 0.0, 0.03, 0.48),
        (0.20, 659.25, 659.25, 0.10, "rhodes", 0.19, 0.0, 0.03, 0.48),
        (0.30, 880.00, 880.00, 0.38, "bell", 0.20, 0.01, 0.14, 0.45),
        (0.30, 440.00, 440.00, 0.38, "tri", 0.14, 0.0, 0.12, 0.38),
        (0.30, 554.37, 554.37, 0.38, "sine", 0.12, 0.0, 0.12, 0.45),
    ])
    add("unlock", 0.48, [
        (0.00, 523.25, 523.25, 0.09, "rhodes", 0.16, 0.0, 0.03, 0.45),
        (0.08, 659.25, 659.25, 0.09, "rhodes", 0.16, 0.0, 0.03, 0.45),
        (0.16, 783.99, 783.99, 0.09, "rhodes", 0.17, 0.0, 0.03, 0.45),
        (0.24, 1046.50, 1046.50, 0.22, "bell", 0.18, 0.0, 0.10, 0.44),
        (0.24, 523.25, 523.25, 0.22, "sine", 0.14, 0.0, 0.10, 0.45),
    ])
    add("shop", 0.26, [
        (0.00, 659.25, 659.25, 0.07, "bell", 0.15, 0.0, 0.03, 0.45),
        (0.07, 987.77, 987.77, 0.17, "bell", 0.16, 0.0, 0.07, 0.45),
        (0.07, 493.88, 493.88, 0.17, "tri", 0.11, 0.0, 0.07, 0.40),
    ])
    add("craft", 0.42, [
        (0.00, 392.00, 440.00, 0.08, "rhodes", 0.17, 0.0, 0.03, 0.45),
        (0.09, 523.25, 523.25, 0.08, "rhodes", 0.18, 0.0, 0.03, 0.45),
        (0.18, 659.25, 783.99, 0.22, "bell", 0.18, 0.0, 0.08, 0.45),
    ])
    add("gacha", 0.56, [
        (0.00, 392.0, 392.0, 0.06, "rhodes", 0.15),
        (0.08, 440.0, 440.0, 0.06, "rhodes", 0.16),
        (0.16, 493.88, 493.88, 0.06, "rhodes", 0.16),
        (0.24, 523.25, 523.25, 0.06, "rhodes", 0.17),
        (0.32, 659.25, 659.25, 0.07, "bell", 0.17),
        (0.40, 783.99, 880.00, 0.15, "bell", 0.18, 0.0, 0.07, 0.45),
    ])
    add("gacha_jackpot", 0.80, [
        (0.00, 523.25, 523.25, 0.09, "rhodes", 0.18),
        (0.09, 659.25, 659.25, 0.09, "rhodes", 0.18),
        (0.18, 783.99, 783.99, 0.09, "rhodes", 0.19),
        (0.27, 880.00, 880.00, 0.10, "bell", 0.19),
        (0.37, 1046.50, 1046.50, 0.40, "bell", 0.20, 0.012, 0.16, 0.45),
        (0.37, 659.25, 659.25, 0.40, "rhodes", 0.14, 0.0, 0.14, 0.42),
        (0.37, 261.63, 261.63, 0.40, "tri", 0.15, 0.0, 0.14, 0.38),
    ])
    add("sleep", 0.54, [
        (0.00, 440.00, 440.00, 0.16, "sine", 0.16, 0.0, 0.06),
        (0.16, 392.00, 392.00, 0.16, "sine", 0.14, 0.0, 0.06),
        (0.32, 329.63, 293.66, 0.20, "sine", 0.13, 0.0, 0.08),
    ])
    add("dance", 0.36, [
        (0.00, 115.0, 52.0, 0.09, "sine", 0.22),
        (0.00, 440.00, 440.00, 0.08, "rhodes", 0.15),
        (0.14, 523.25, 523.25, 0.08, "rhodes", 0.15),
        (0.22, 587.33, 659.25, 0.13, "soft_pulse", 0.14, 0.0, 0.05, 0.42),
    ])
    add("magic", 0.44, [
        (0.00, 493.88, 493.88, 0.07, "sine", 0.15),
        (0.06, 587.33, 587.33, 0.07, "sine", 0.16),
        (0.12, 739.99, 739.99, 0.07, "rhodes", 0.16),
        (0.18, 987.77, 1046.50, 0.24, "bell", 0.17, 0.012, 0.10, 0.46),
    ])
    add("fish", 0.30, [
        (0.00, 620.0, 280.0, 0.11, "sine", 0.17),
        (0.11, 520.0, 240.0, 0.14, "noise", 0.06, 0.0, 0.06, 0.10),
    ])
    add("boop", 0.32, [
        (0.00, 392.0, 587.33, 0.11, "sine", 0.18),
        (0.11, 587.33, 783.99, 0.18, "rhodes", 0.18, 0.0, 0.07, 0.46),
    ])
    add("dive_bye", 0.56, [
        (0.00, 659.25, 659.25, 0.09, "rhodes", 0.16),
        (0.09, 523.25, 523.25, 0.09, "rhodes", 0.16),
        (0.18, 392.00, 392.00, 0.10, "sine", 0.16),
        (0.28, 329.63, 196.00, 0.24, "sine", 0.17, 0.0, 0.09),
        (0.42, 420.00, 180.00, 0.12, "noise", 0.06, 0.0, 0.05, 0.12),
    ])
    add("gans", 0.28, [
        (0.00, 460.0, 340.0, 0.09, "soft_sq", 0.15, 0.0, 0.03, 0.34),
        (0.10, 440.0, 310.0, 0.14, "soft_sq", 0.15, 0.0, 0.05, 0.32),
    ])
    add("committee", 0.46, [
        (0.00, 392.00, 392.00, 0.08, "rhodes", 0.16),
        (0.09, 493.88, 493.88, 0.08, "rhodes", 0.16),
        (0.18, 587.33, 587.33, 0.08, "rhodes", 0.17),
        (0.27, 783.99, 783.99, 0.17, "bell", 0.18, 0.0, 0.08, 0.45),
    ])
    add("trivia_ok", 0.38, [
        (0.00, 523.25, 523.25, 0.08, "bell", 0.16),
        (0.08, 659.25, 659.25, 0.08, "bell", 0.16),
        (0.16, 783.99, 783.99, 0.18, "bell", 0.17, 0.0, 0.08, 0.46),
    ])
    add("konami", 1.10, [
        (0.00, 440.00, 440.00, 0.09, "soft_pulse", 0.16),
        (0.10, 554.37, 554.37, 0.09, "soft_pulse", 0.16),
        (0.20, 659.25, 659.25, 0.09, "soft_pulse", 0.17),
        (0.30, 880.00, 880.00, 0.16, "bell", 0.18),
        (0.48, 659.25, 659.25, 0.10, "soft_pulse", 0.16),
        (0.60, 880.00, 880.00, 0.46, "bell", 0.19, 0.012, 0.18, 0.45),
        (0.00, 220.00, 220.00, 0.30, "tri", 0.14),
        (0.30, 164.81, 164.81, 0.30, "tri", 0.14),
        (0.60, 220.00, 220.00, 0.46, "tri", 0.16),
    ])
    add("victory", 0.85, [
        (0.00, 392.00, 392.00, 0.10, "rhodes", 0.18),
        (0.11, 493.88, 493.88, 0.10, "rhodes", 0.18),
        (0.22, 587.33, 587.33, 0.10, "rhodes", 0.18),
        (0.34, 783.99, 783.99, 0.48, "bell", 0.20, 0.010, 0.18, 0.46),
        (0.34, 392.00, 392.00, 0.48, "tri", 0.15, 0.0, 0.18, 0.40),
    ])
    for idx, pitch in enumerate((340.0, 390.0, 440.0, 500.0)):
        add(f"voice_{idx}", 0.07, [
            (0.00, pitch, pitch * 1.12, 0.06, "sine", 0.10, 0.0, 0.025, 0.45),
        ])
    return bank


def _bake_music_track(track_id):
    """Synthesize a cozy, warm looping WAV track with chords, bass & soft percussion."""
    if track_id == "lofi":
        step = 0.36
        lead = ["E4", "R", "G4", "A4", "G4", "R", "E4", "D4",
                "C4", "R", "E4", "G4", "E4", "R", "D4", "R"] * 2
        pad = ["C4", "R", "E4", "R", "A3", "R", "C4", "R",
               "F3", "R", "A3", "R", "G3", "R", "B3", "R"] * 2
        bass = ["C3", "C3", "G2", "G2", "A2", "A2", "F2", "F2",
                "C3", "C3", "E2", "E2", "G2", "G2", "G2", "R"] * 2
        w_lead, w_bass = "rhodes", "tri"
    elif track_id == "disco":
        step = 0.25
        lead = ["A4", "C5", "E5", "R", "G5", "E5", "D5", "C5",
                "A4", "A4", "E5", "D5", "C5", "B4", "A4", "R"] * 2
        pad = ["C4", "R", "E4", "R", "B3", "R", "D4", "R",
               "A3", "R", "C4", "R", "G3", "R", "B3", "R"] * 2
        bass = ["A2", "A3", "A2", "A3", "G2", "G3", "G2", "G3",
                "F2", "F3", "F2", "F3", "E2", "E3", "E2", "E3"] * 2
        w_lead, w_bass = "soft_pulse", "tri"
    elif track_id == "study":
        step = 0.28
        lead = ["D4", "F4", "A4", "C5", "A4", "F4", "D4", "F4",
                "C4", "E4", "G4", "B4", "G4", "E4", "C4", "E4"] * 2
        pad = ["A3", "R", "R", "R", "F3", "R", "R", "R",
               "G3", "R", "R", "R", "E3", "R", "R", "R"] * 2
        bass = ["D2", "D2", "D3", "D2", "D2", "D2", "D3", "D2",
                "C2", "C2", "C3", "C2", "G2", "G2", "G3", "G2"] * 2
        w_lead, w_bass = "rhodes", "sine"
    elif track_id == "uithof":
        step = 0.24
        lead = ["G4", "B4", "D5", "R", "E5", "D5", "B4", "G4",
                "A4", "C5", "E5", "R", "D5", "B4", "G4", "R"] * 2
        pad = ["B3", "R", "D4", "R", "C4", "R", "E4", "R",
               "A3", "R", "C4", "R", "D4", "R", "B3", "R"] * 2
        bass = ["G2", "G2", "D3", "G2", "C3", "C3", "G2", "C3",
                "A2", "A2", "E3", "A2", "D3", "D3", "G2", "R"] * 2
        w_lead, w_bass = "bell", "tri"
    else:  # arcade
        step = 0.22
        lead = ["C5", "E5", "G5", "A5", "G5", "E5", "D5", "E5",
                "F5", "E5", "D5", "C5", "D5", "E5", "C5", "R"] * 2
        pad = ["E4", "R", "G4", "R", "C4", "R", "E4", "R",
               "F4", "R", "A4", "R", "G4", "R", "E4", "R"] * 2
        bass = ["C3", "G2", "C3", "G2", "A2", "E2", "A2", "E2",
                "F2", "C3", "G2", "D3", "C3", "G2", "C3", "R"] * 2
        w_lead, w_bass = "soft_pulse", "tri"

    evs = []
    for i, note in enumerate(lead):
        t = i * step
        hz = _hz(note)
        if hz > 0:
            evs.append((t, hz, hz, step * 0.85, w_lead, 0.085, 0.0, step * 0.35, 0.42))
        phz = _hz(pad[i % len(pad)])
        if phz > 0:
            evs.append((t, phz, phz, step * 1.4, "sine", 0.055, 0.0, step * 0.45, 0.50))
        bhz = _hz(bass[i % len(bass)])
        if bhz > 0:
            evs.append((t, bhz, bhz, step * 0.88, w_bass, 0.105, 0.0, step * 0.30, 0.35))
        if i % 4 == 0:
            evs.append((t, 110.0, 48.0, 0.08, "sine", 0.13, 0.0, 0.03, 0.55))
        elif i % 4 == 2:
            evs.append((t, 450.0, 180.0, 0.045, "noise", 0.038, 0.0, 0.025, 0.10))
    return _to_wav_bytes(_seq_to_buf(len(lead) * step, evs))


def _scale_wav_pcm(wav_bytes, vol):
    """Scale 16-bit PCM WAV payload amplitude by vol in [0.0, 1.0]."""
    if vol >= 0.99 or len(wav_bytes) <= 44:
        return wav_bytes
    if vol <= 0.01:
        return wav_bytes[:44] + b"\x00" * (len(wav_bytes) - 44)
    from array import array
    arr = array("h")
    arr.frombytes(wav_bytes[44:])
    for i in range(len(arr)):
        arr[i] = int(arr[i] * vol)
    return wav_bytes[:44] + arr.tobytes()


def _resample_wav_pcm(wav_bytes, pitch_ratio):
    """Linearly resample 16-bit mono WAV at same sample rate for subtle pitch variation."""
    if len(wav_bytes) <= 48 or abs(pitch_ratio - 1.0) < 0.005:
        return wav_bytes
    from array import array
    import struct
    src = array("h")
    src.frombytes(wav_bytes[44:])
    n_src = len(src)
    n_dst = max(64, int(n_src / pitch_ratio))
    dst = array("h", [0]) * n_dst
    for i in range(n_dst):
        pos = i * pitch_ratio
        idx = int(pos)
        if idx >= n_src - 1:
            dst[i] = src[n_src - 1]
        else:
            frac = pos - idx
            dst[i] = int(src[idx] * (1.0 - frac) + src[idx + 1] * frac)
    data = dst.tobytes()
    hdr = bytearray(wav_bytes[:44])
    struct.pack_into("<I", hdr, 4, 36 + len(data))
    struct.pack_into("<I", hdr, 40, len(data))
    return bytes(hdr) + data


class SoundEngine:
    """Dual-channel audio engine: looping BGM (winmm MCI) + instant polyphonic SFX."""

    def __init__(self):
        self.muted = False
        self.auto_quiet = False
        self.voice_on = True
        self.sfx_vol = 0.75
        self.bgm_vol = 0.65
        self.track = "off"
        self.sfx = _bake_sfx_bank()
        self._variant_bank = {}
        for base in ("pet", "coin", "eat", "jump", "flap", "bounce"):
            if base in self.sfx:
                raw = self.sfx[base]
                self._variant_bank[base] = (
                    raw,
                    _resample_wav_pcm(raw, 0.95),
                    _resample_wav_pcm(raw, 1.06),
                )
        self._vol_cache = {}
        self._q = queue.Queue(maxsize=4)
        self._cache_dir = os.path.join(tempfile.gettempdir(), "karel_koala_audio")
        self._bgm_files = {}
        self._bgm_raw = {}
        self._bgm_active_path = ""
        self._bgm_proc = None
        self._sfx_proc = None
        self._sfx_slot = 0
        self._mci_open = False
        self._stop = False
        self._lock = threading.Lock()
        self._player_cmd = self._detect_unix_player()
        threading.Thread(target=self._sfx_worker, daemon=True).start()
        threading.Thread(target=self._bgm_watcher, daemon=True).start()

    @staticmethod
    def _stop_proc(proc):
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=0.18)
                except Exception:
                    proc.kill()
        except Exception:
            pass

    @staticmethod
    def _detect_unix_player():
        if os.name == "nt":
            return None
        for cmd in ("afplay", "paplay", "aplay"):
            if shutil.which(cmd):
                return cmd
        return None

    def _scaled_sfx(self, wav_bytes):
        vol = round(float(self.sfx_vol), 2)
        if vol >= 0.99:
            return wav_bytes
        key = (id(wav_bytes), vol)
        cached = self._vol_cache.get(key)
        if cached is not None:
            return cached
        scaled = _scale_wav_pcm(wav_bytes, vol)
        if len(self._vol_cache) >= 160:
            self._vol_cache.clear()
        self._vol_cache[key] = scaled
        return scaled

    def _play_wav_bytes(self, wav_bytes):
        if self.sfx_vol <= 0.01:
            return
        wav_bytes = self._scaled_sfx(wav_bytes)
        if os.name == "nt" and winsound:
            try:
                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY | winsound.SND_NODEFAULT)
            except Exception:
                pass
        elif self._player_cmd:
            try:
                os.makedirs(self._cache_dir, exist_ok=True)
                self._sfx_slot = (self._sfx_slot + 1) & 1
                p = os.path.join(self._cache_dir, f"sfx_{os.getpid()}_{self._sfx_slot}.wav")
                with open(p, "wb") as f:
                    f.write(wav_bytes)
                proc = subprocess.Popen([self._player_cmd, p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._sfx_proc = proc
                deadline = time.monotonic() + 2.5
                while proc.poll() is None and time.monotonic() < deadline:
                    if self._stop or self.muted or self.auto_quiet:
                        self._stop_proc(proc)
                        break
                    time.sleep(0.03)
                if proc.poll() is None:
                    self._stop_proc(proc)
            except Exception:
                pass
            finally:
                self._sfx_proc = None

    def _sfx_worker(self):
        while not self._stop:
            try:
                wav_bytes = self._q.get(timeout=0.3)
            except queue.Empty:
                continue
            if self.muted or self.auto_quiet or not wav_bytes:
                continue
            self._play_wav_bytes(wav_bytes)

    def play_sfx(self, name):
        if self.muted or self.auto_quiet or name not in self.sfx:
            return
        try:
            if self._q.full():
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    pass
            self._q.put_nowait(self.sfx[name])
        except Exception:
            pass

    def beep(self, freq=660, _ms=45):
        if freq >= 900:
            self.play_sfx("shop")
        elif freq <= 300:
            self.play_sfx("buzz")
        else:
            self.play_sfx("coin")

    def coin(self): self.play_sfx("coin")
    def pet(self): self.play_sfx("pet")
    def eat(self): self.play_sfx("eat")
    def coffee(self): self.play_sfx("coffee")
    def wash(self): self.play_sfx("wash")
    def jump(self): self.play_sfx("jump")
    def bounce(self): self.play_sfx("bounce")
    def flap(self): self.play_sfx("flap")
    def smash(self): self.play_sfx("smash")
    def buzz(self): self.play_sfx("buzz")
    def cooldown(self): self.play_sfx("cooldown")
    def sneeze(self): self.play_sfx("sneeze")
    def levelup(self): self.play_sfx("levelup")
    def unlock(self): self.play_sfx("unlock")
    def shop(self): self.play_sfx("shop")
    def craft(self): self.play_sfx("craft")
    def gacha(self, jackpot=False): self.play_sfx("gacha_jackpot" if jackpot else "gacha")
    def sleep(self): self.play_sfx("sleep")
    def dance(self): self.play_sfx("dance")
    def magic(self): self.play_sfx("magic")
    def fish(self): self.play_sfx("fish")
    def boop(self): self.play_sfx("boop")
    def dive_bye(self): self.play_sfx("dive_bye")
    def gans(self): self.play_sfx("gans")
    def committee(self): self.play_sfx("committee")
    def trivia_ok(self): self.play_sfx("trivia_ok")
    def victory(self): self.play_sfx("victory")
    def konami(self): self.play_sfx("konami")

    def play_varied(self, name):
        """Play a subtly pitch-varied variant when available (falls back to play_sfx)."""
        choices = self._variant_bank.get(name)
        if choices and not self.muted and not self.auto_quiet:
            try:
                self._q.put_nowait(random.choice(choices))
            except queue.Full:
                pass
            return
        self.play_sfx(name)

    def chirp(self):
        if not self.muted and not self.auto_quiet and self.voice_on:
            self.play_sfx(f"voice_{random.randint(0, 3)}")

    def set_auto_quiet(self, flag):
        """Pause/resume audio silently for fullscreen/meetings without altering manual mute."""
        flag = bool(flag)
        if flag == self.auto_quiet:
            return
        self.auto_quiet = flag
        if flag:
            self.stop_music()
            self._stop_proc(self._sfx_proc)
            if winsound:
                try:
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass
        elif not self.muted and self.track != "off":
            self.set_music(self.track)

    def set_sfx_volume(self, vol):
        """Set SFX volume multiplier in [0.0, 1.0]."""
        self.sfx_vol = max(0.0, min(1.0, float(vol)))

    def set_bgm_volume(self, vol, restart=True):
        """Set BGM volume multiplier in [0.0, 1.0] (quantized to 5% steps)."""
        new_v = max(0.0, min(1.0, float(vol)))
        old_q = int(round(self.bgm_vol * 20)) * 5
        new_q = int(round(new_v * 20)) * 5
        self.bgm_vol = new_v
        if restart and new_q != old_q and self.track != "off" and not self.muted and not self.auto_quiet:
            self.set_music(self.track)

    def _mci(self, cmd):
        if os.name != "nt":
            return -1, ""
        try:
            buf = ctypes.create_unicode_buffer(128)
            rc = ctypes.windll.winmm.mciSendStringW(cmd, buf, 128, 0)
            return rc, buf.value.strip()
        except Exception:
            return -1, ""

    def set_music(self, track_id):
        """Start or stop looping warm chiptune BGM track scaled by bgm_vol."""
        if track_id not in MUSIC_TRACKS:
            return False
        self.track = track_id
        self.stop_music()
        vol_q = max(0, min(100, int(round(self.bgm_vol * 20)) * 5))
        if track_id == "off" or self.muted or self.auto_quiet or vol_q == 0:
            return True
        if track_id not in self._bgm_raw:
            self._bgm_raw[track_id] = _bake_music_track(track_id)
        os.makedirs(self._cache_dir, exist_ok=True)
        path = os.path.join(self._cache_dir, f"bgm_v3_{track_id}_{vol_q}.wav")
        if not os.path.exists(path):
            raw = self._bgm_raw[track_id]
            scaled = raw if vol_q >= 99 else _scale_wav_pcm(raw, vol_q / 100.0)
            with open(path, "wb") as f:
                f.write(scaled)
        self._bgm_files[track_id] = path
        self._bgm_active_path = path
        if os.name == "nt":
            with self._lock:
                rc, _ = self._mci(f'open "{path}" type waveaudio alias karel_bgm')
                if rc == 0:
                    self._mci("play karel_bgm")
                    self._mci_open = True
        elif self._player_cmd:
            with self._lock:
                try:
                    self._bgm_proc = subprocess.Popen(
                        [self._player_cmd, path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    self._bgm_proc = None
        return True

    def stop_music(self):
        if os.name == "nt":
            with self._lock:
                if self._mci_open:
                    self._mci("stop karel_bgm")
                    self._mci("close karel_bgm")
                    self._mci_open = False
        else:
            with self._lock:
                self._stop_proc(self._bgm_proc)
                self._bgm_proc = None

    def _bgm_watcher(self):
        while not self._stop:
            time.sleep(0.5)
            if os.name == "nt" and self._mci_open and self.track != "off" and not self.muted and not self.auto_quiet:
                with self._lock:
                    rc, status = self._mci("status karel_bgm mode")
                    if rc == 0 and status.lower() == "stopped":
                        self._mci("seek karel_bgm to start")
                        self._mci("play karel_bgm")
            elif os.name != "nt" and self._player_cmd and self.track != "off" and not self.muted and not self.auto_quiet:
                with self._lock:
                    if self._bgm_proc is not None and self._bgm_proc.poll() is not None and os.path.exists(self._bgm_active_path):
                        try:
                            self._bgm_proc = subprocess.Popen(
                                [self._player_cmd, self._bgm_active_path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            )
                        except Exception:
                            self._bgm_proc = None

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_music()
            self._stop_proc(self._sfx_proc)
            if winsound:
                try:
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass
        elif self.track != "off" and not self.auto_quiet:
            self.set_music(self.track)
        return self.muted

    def close(self):
        self._stop = True
        self.stop_music()
        self._stop_proc(self._sfx_proc)
        if winsound:
            try:
                winsound.PlaySound(None, 0)
            except Exception:
                pass
