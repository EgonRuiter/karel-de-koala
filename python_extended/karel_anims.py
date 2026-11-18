"""Procedural sprite upgrades, fixes, and extended animations (54 states total)."""

ANIM_DIV = {
    **dict.fromkeys(("HYPER", "DIZZY", "JETPACK", "JUMP"), 1),
    **dict.fromkeys((
        "IDLE", "SIT", "SLEEP", "THINK", "YAWN", "STUDY", "LAPTOP_CODE",
        "PEEK", "EARS_WIGGLE", "BLINK_SMILE", "BOW", "UMBRELLA", "MAGNIFY",
        "FISHING", "HUG_PLUSH", "EUCALYPTUS_HUG", "HUNGRY",
    ), 3),
}

DESKTOP_IDLE_ACTS = (
    "BLINK_SMILE", "EARS_WIGGLE", "PEEK", "SIT", "STRETCH",
    "THINK", "LAPTOP_CODE", "MAGNIFY", "PAPER_PLANE",
    "HUG_PLUSH", "EUCALYPTUS_HUG", "UMBRELLA", "BOW", "SPIN", "WAVE",
)


def _paint(g, rc, pt=()):
    for x1, y1, x2, y2, c in rc:
        for y in range(max(0, y1), min(32, y2 + 1)):
            row_len = min(32, x2 + 1) - max(0, x1)
            if row_len > 0:
                g[y][max(0, x1):min(32, x2 + 1)] = [c] * row_len
    for x, y, c in pt:
        if 0 <= x < 32 and 0 <= y < 32:
            g[y][x] = c


def _shift(frame, dx=0, dy=0):
    g = [["."] * 32 for _ in range(32)]
    for y in range(32):
        ny = y + dy
        if 0 <= ny < 32:
            for x in range(32):
                nx = x + dx
                if 0 <= nx < 32:
                    g[ny][nx] = frame[y][x]
    return g


def _mirror_h(frame):
    return [r[::-1] for r in frame]


def _make(base, rc=(), pt=(), dx=0, dy=0):
    g = _shift(base, dx=dx, dy=dy)
    _paint(g, rc, pt)
    return ["".join(r) for r in g]


def _to_grid(rc=(), pt=()):
    g = [["."] * 32 for _ in range(32)]
    _paint(g, rc, pt)
    return ["".join(r) for r in g]


def _eyes(frame, mode="open", dx=0, dy=0):
    """Draw clean eye expressions on an IDLE-based koala before/after shifting."""
    g = _shift(frame, dx=dx, dy=dy)
    rc = [(11 + dx, 11 + dy, 12 + dx, 12 + dy, "g"), (19 + dx, 11 + dy, 20 + dx, 12 + dy, "g")]
    pt = []
    if mode == "open":
        pt += [(11 + dx, 11 + dy, "W"), (12 + dx, 11 + dy, "k"), (19 + dx, 11 + dy, "W"), (20 + dx, 11 + dy, "k")]
    elif mode == "happy":
        pt += [
            (10 + dx, 12 + dy, "k"), (11 + dx, 11 + dy, "k"), (12 + dx, 12 + dy, "k"),
            (19 + dx, 12 + dy, "k"), (20 + dx, 11 + dy, "k"), (21 + dx, 12 + dy, "k"),
        ]
    elif mode == "blink":
        pt += [
            (10 + dx, 12 + dy, "k"), (11 + dx, 12 + dy, "k"), (12 + dx, 12 + dy, "k"),
            (19 + dx, 12 + dy, "k"), (20 + dx, 12 + dy, "k"), (21 + dx, 12 + dy, "k"),
        ]
    elif mode == "wink":
        pt += [
            (11 + dx, 11 + dy, "W"), (12 + dx, 11 + dy, "k"),
            (19 + dx, 12 + dy, "k"), (20 + dx, 11 + dy, "k"), (21 + dx, 12 + dy, "k"),
        ]
    elif mode == "heart":
        pt += [
            (10 + dx, 10 + dy, "r"), (12 + dx, 10 + dy, "r"),
            (10 + dx, 11 + dy, "p"), (11 + dx, 11 + dy, "r"), (12 + dx, 11 + dy, "p"), (11 + dx, 12 + dy, "v"),
            (19 + dx, 10 + dy, "r"), (21 + dx, 10 + dy, "r"),
            (19 + dx, 11 + dy, "p"), (20 + dx, 11 + dy, "r"), (21 + dx, 11 + dy, "p"), (20 + dx, 12 + dy, "v"),
        ]
    elif mode in ("look_l", "look_r"):
        lx, rx = (11 + dx, 19 + dx) if mode == "look_l" else (12 + dx, 20 + dx)
        wx, wy = (12 + dx, 20 + dx) if mode == "look_l" else (11 + dx, 19 + dx)
        pt += [(lx, 11 + dy, "k"), (wx, 11 + dy, "W"), (rx, 11 + dy, "k"), (wy, 11 + dy, "W")]
    _paint(g, rc, pt)
    return ["".join(r) for r in g]


def _erase_arm(rc, side):
    if side in ("L", "LR"):
        rc.append((5, 19, 8, 24, "."))
    if side in ("R", "LR"):
        rc.append((23, 19, 26, 24, "."))


def _arm_up(rc, pt, side, h=0):
    """Draw outlined raised arm cleanly outside the face/ears silhouette."""
    _erase_arm(rc, side)
    y = 14 - h
    if side in ("L", "LR"):
        rc += [(3, y + 1, 5, y + 6, "g"), (5, y + 4, 7, y + 6, "g"), (3, y, 5, y + 1, "w")]
        pt += [(3, y - 1, "k"), (4, y - 1, "k"), (5, y - 1, "k"), (2, y, "k"), (2, y + 1, "k"), (2, y + 2, "k"), (2, y + 3, "k"), (2, y + 4, "k"), (2, y + 5, "k"), (3, y + 6, "k")]
    if side in ("R", "LR"):
        rc += [(26, y + 1, 28, y + 6, "g"), (24, y + 4, 26, y + 6, "g"), (26, y, 28, y + 1, "w")]
        pt += [(26, y - 1, "k"), (27, y - 1, "k"), (28, y - 1, "k"), (29, y, "k"), (29, y + 1, "k"), (29, y + 2, "k"), (29, y + 3, "k"), (29, y + 4, "k"), (29, y + 5, "k"), (28, y + 6, "k")]


def _crouch_base(idle0, dy=2):
    g = _shift(idle0, dy=dy)
    _paint(g, [
        (9, 27, 22, 31, "."), (9, 27, 13, 29, "k"), (18, 27, 22, 29, "k"),
        (10, 27, 12, 28, "g"), (19, 27, 21, 28, "g"), (9, 29, 13, 30, "s"), (18, 29, 22, 30, "s"),
    ], [])
    return ["".join(r) for r in g]


def _headphones_on(frame):
    return _make(
        frame,
        [(3, 7, 4, 12, "r"), (27, 7, 28, 12, "r"), (3, 8, 3, 11, "R"), (28, 8, 28, 11, "R"), (7, 4, 24, 5, "d")],
        [(5, 6, "d"), (6, 5, "d"), (25, 5, "d"), (26, 6, "d"), (7, 4, "k"), (24, 4, "k")],
    )


def _confetti(step):
    cols = ("y", "r", "a", "n", "v")
    pts = []
    for k in range(8):
        cx = (2 + (k * 4 + step * 3)) % 30 + 1
        cy = (1 + (k * 3 + step * 2)) % 9
        if cy < 4 or cx < 4 or cx > 27:
            pts.append((cx, cy, cols[(k + step) % len(cols)]))
    return pts


def _peek_from(base_face, dy=0):
    g = _shift(base_face, dy=15 + dy)
    for r_i in range(30, 32):
        g[r_i] = ["."] * 32
    _paint(g, [(8, 29, 11, 30, "g"), (20, 29, 23, 30, "g"), (3, 31, 28, 31, "s")], [(9, 29, "w"), (22, 29, "w")])
    return ["".join(r) for r in g]


def register_animations(sprites):
    """Upgrade core animations and register all 54 clean animations in SPRITES."""
    idle0 = sprites["IDLE"][0]
    pet_h = _eyes(idle0, "happy")
    blink = _eyes(idle0, "blink")
    wink = _eyes(idle0, "wink")
    jump_peak = sprites["JUMP"][1]
    study0, study1 = sprites["STUDY"]
    walk_l, walk_r = sprites["WALK_LEFT"], sprites["WALK_RIGHT"]
    hyper0 = sprites["HYPER"][0]
    crouch = _crouch_base(idle0, dy=2)
    breathe = _make(idle0, [(7, 19, 8, 21, "g"), (23, 19, 24, 21, "g")], [(5, 5, "k"), (26, 5, "k")], dy=-1)

    sprites["IDLE"] = [idle0, breathe, idle0, blink]
    sprites["JUMP"] = [
        _eyes(crouch, "happy"),
        _make(jump_peak, [], [(15, 30, "w"), (16, 30, "w")]),
        _make(jump_peak, [], [(11, 29, "u"), (20, 29, "u")], dy=-2),
        _make(crouch, [], [(7, 30, "w"), (8, 30, "u"), (23, 30, "w"), (24, 30, "u")]),
    ]

    def _climb_f(hi_side, dy=0, grin=False):
        rc, pt = [], []
        if hi_side == "L":
            _arm_up(rc, pt, "L", h=3)
            rc += [(23, 21, 26, 25, "g"), (9, 24, 13, 27, "g"), (9, 27, 13, 28, "s")]
        elif hi_side == "R":
            _arm_up(rc, pt, "R", h=3)
            rc += [(5, 21, 8, 25, "g"), (18, 24, 22, 27, "g"), (18, 27, 22, 28, "s")]
        else:
            _arm_up(rc, pt, "LR", h=1)
        rc.append((3, 29, 28, 29, "s"))
        return _make(pet_h if grin else idle0, rc, pt, dy=dy)

    sprites["CLIMB"] = [_climb_f("L", 0), _climb_f("BOTH", -1), _climb_f("R", 0), _climb_f("BOTH", -2, grin=True)]

    def _dance_f(arm_l, arm_r, dx, dy, step):
        rc, pt = [], _confetti(step)
        if arm_l:
            _arm_up(rc, pt, "L", h=1)
        if arm_r:
            _arm_up(rc, pt, "R", h=1)
        return _make(pet_h, rc, pt, dx=dx, dy=dy)

    sprites["DANCE"] = [_dance_f(True, False, -1, 0, 0), _dance_f(True, True, 0, -1, 1), _dance_f(False, True, 1, 0, 2), _dance_f(False, False, 0, -1, 3)]
    sprites["SNEEZE"] = [
        _make(wink, [(15, 15, 16, 16, "p")], [(14, 15, "k"), (17, 15, "k")], dy=-1),
        _make(blink, [(14, 15, 17, 16, "r")], [(12, 18, "W"), (14, 19, "u"), (18, 19, "u"), (20, 18, "W"), (15, 21, "W")], dy=1),
        _make(idle0, [(14, 13, 17, 14, "p")], [(9, 19, "u"), (22, 19, "u"), (11, 21, "W"), (20, 21, "W")]),
    ]
    sprites["CRY"] = [
        _make(blink, [(10, 13, 11, 16, "b"), (20, 13, 21, 16, "b")], [(10, 17, "a"), (21, 17, "a"), (15, 16, "s")]),
        _make(blink, [(10, 15, 11, 19, "b"), (20, 15, 21, 19, "b")], [(10, 20, "W"), (21, 20, "W"), (15, 16, "s"), (16, 16, "s")], dy=1),
        _make(blink, [(10, 14, 11, 17, "a"), (20, 14, 21, 17, "a")], [(9, 18, "b"), (22, 18, "b"), (15, 16, "s")]),
    ]
    heart_face = _eyes(idle0, "heart")
    sprites["LOVE"] = [
        _make(heart_face, [], [(5, 5, "p"), (26, 5, "r")]),
        _make(heart_face, [], [(4, 3, "r"), (5, 4, "r"), (6, 3, "r"), (25, 3, "p"), (26, 4, "p"), (27, 3, "p")], dy=-1),
        _make(heart_face, [], [(5, 1, "v"), (26, 1, "r"), (15, 1, "p"), (16, 1, "p")]),
    ]
    sprites["GAMING"] = [
        _make(study0, [(22, 22, 29, 27, "d"), (23, 23, 28, 26, "a"), (24, 24, 26, 25, "y")], [(27, 25, "r"), (28, 24, "e")]),
        _make(study1, [(22, 22, 29, 27, "d"), (23, 23, 28, 26, "n"), (25, 24, 27, 25, "W")], [(23, 25, "p"), (28, 25, "y")]),
        _make(study0, [(22, 22, 29, 27, "d"), (23, 23, 28, 26, "b"), (24, 24, 25, 26, "y")], [(27, 24, "y"), (28, 25, "r")], dy=-1),
    ]
    hp = _headphones_on(pet_h)
    sprites["MUSIC"] = [
        _make(hp, [], [(3, 2, "y"), (4, 1, "y"), (4, 2, "y")], dx=-1, dy=0),
        _make(hp, [], [(27, 2, "a"), (28, 1, "a"), (28, 2, "a"), (15, 1, "y")], dx=0, dy=-1),
        _make(hp, [], [(26, 2, "p"), (27, 1, "p"), (28, 1, "p")], dx=1, dy=0),
        _make(hp, [], [(4, 1, "n"), (5, 1, "n"), (27, 2, "y")], dx=0, dy=-1),
    ]

    def _ex_f(lift, dy=0):
        rc = [(8, 7, 23, 7, "r"), (10, 6, 21, 6, "R")]
        pt = [(3, 6, "a"), (28, 6, "a")] if lift == 2 else []
        if lift == 0:
            rc += [(2, 21, 6, 22, "k"), (3, 19, 3, 24, "d"), (25, 21, 29, 22, "k"), (28, 19, 28, 24, "d")]
        elif lift == 1:
            _arm_up(rc, pt, "L", h=1)
            rc += [(1, 11, 6, 12, "d"), (1, 9, 2, 13, "k"), (5, 9, 6, 13, "k"), (25, 21, 29, 22, "k")]
        else:
            _arm_up(rc, pt, "LR", h=3)
            rc += [(1, 8, 6, 9, "d"), (1, 6, 2, 10, "k"), (5, 6, 6, 10, "k"),
                   (25, 8, 30, 9, "d"), (25, 6, 26, 10, "k"), (29, 6, 30, 10, "k")]
        return _make(pet_h if lift == 2 else idle0, rc, pt, dy=dy)

    sprites["EXERCISE"] = [_ex_f(0, 1), _ex_f(1, 0), _ex_f(2, -1), _ex_f(0, 0)]
    sprites["TOSTI"] = [
        _make(idle0, [(23, 18, 28, 22, "h"), (24, 19, 27, 21, "y"), (25, 20, 26, 21, "t")], [(24, 18, "h"), (28, 18, "h"), (25, 15, "W")]),
        _make(pet_h, [(22, 16, 27, 20, "h"), (23, 17, 26, 19, "y"), (24, 18, 25, 20, "t")], [(15, 16, "r"), (16, 16, "y")]),
        _make(pet_h, [(23, 18, 26, 21, "h"), (24, 19, 25, 20, "y")], [(15, 15, "y"), (17, 17, "t"), (27, 16, "W")], dy=-1),
        _make(wink, [(24, 19, 27, 21, "h"), (25, 20, 26, 20, "y")], [(14, 16, "t")]),
    ]
    sprites["BORREL"] = [
        _make(pet_h, [(24, 17, 28, 23, "k"), (25, 18, 27, 22, "y"), (24, 16, 28, 17, "W")], [(29, 19, "w"), (29, 20, "w"), (26, 14, "W")]),
        _make(pet_h, [(24, 15, 28, 21, "k"), (25, 16, 27, 20, "o"), (24, 14, 28, 15, "W")], [(29, 17, "w"), (29, 18, "w"), (25, 12, "t")], dy=-1),
        _make(wink, [(24, 16, 28, 22, "k"), (25, 17, 27, 21, "y"), (24, 15, 28, 16, "W")], [(29, 18, "w"), (27, 13, "W")]),
    ]
    sprites["WIZARD_CAST"] = [
        _make(idle0, [(25, 14, 26, 25, "c"), (24, 12, 27, 14, "a")], [(25, 13, "W"), (28, 12, "y")]),
        _make(pet_h, [(26, 12, 27, 23, "c"), (25, 10, 28, 12, "n")], [(26, 11, "W"), (29, 9, "y"), (30, 11, "a"), (23, 9, "a")]),
        _make(pet_h, [(26, 12, 27, 23, "c"), (25, 10, 28, 12, "v")], [(26, 11, "y"), (30, 8, "W"), (29, 14, "a"), (22, 8, "y")], dy=-1),
    ]
    sprites["FISHING"] = [
        _make(idle0, [(24, 14, 29, 15, "c"), (29, 15, 29, 25, "W")], [(29, 26, "r"), (29, 27, "W"), (28, 28, "b"), (30, 28, "b")]),
        _make(idle0, [(24, 15, 29, 16, "c"), (29, 16, 29, 26, "W")], [(29, 27, "r"), (27, 28, "a"), (31, 28, "a")]),
        _make(wink, [(24, 12, 28, 13, "c"), (28, 13, 28, 21, "W")], [(28, 22, "y"), (27, 23, "b"), (29, 23, "b"), (28, 24, "W")], dy=-1),
    ]
    sprites["RUN_LEFT"] = [
        _make(f, [], [(26, 16, "u"), (28, 18, "W"), (26, 29, "w")] if i % 2 == 0 else [(27, 17, "u"), (29, 28, "W")], dx=-2 + (i % 2), dy=-(i % 2))
        for i, f in enumerate(walk_l)
    ]
    sprites["RUN_RIGHT"] = [
        _make(f, [], [(4, 16, "u"), (2, 18, "W"), (5, 29, "w")] if i % 2 == 0 else [(3, 17, "u"), (2, 28, "W")], dx=2 - (i % 2), dy=-(i % 2))
        for i, f in enumerate(walk_r)
    ]

    sit_rc = [(8, 24, 23, 31, "."), (9, 26, 13, 29, "k"), (18, 26, 22, 29, "k"), (10, 27, 12, 28, "s"), (19, 27, 21, 28, "s"), (13, 25, 18, 27, "w")]
    sprites["SIT"] = [_make(idle0, sit_rc, [], dy=2), _make(pet_h, sit_rc, [], dy=2), _make(blink, sit_rc, [], dy=2)]

    # STRETCH: arms spread cleanly wide outward above ears (face completely unobstructed!)
    st_r0, st_p0 = [], []
    _arm_up(st_r0, st_p0, "LR", h=1)
    st_r1, st_p1 = [], []
    _arm_up(st_r1, st_p1, "LR", h=5)
    st_r2, st_p2 = [], []
    _arm_up(st_r2, st_p2, "LR", h=3)
    sprites["STRETCH"] = [
        _make(blink, st_r0, st_p0),
        _make(pet_h, st_r1, st_p1 + [(15, 1, "y")], dy=-1),
        _make(pet_h, st_r2, st_p2, dy=-1),
        _make(idle0, [], [(15, 2, "p"), (16, 2, "p")]),
    ]
    sprites["YAWN"] = [
        _make(blink, [(15, 15, 16, 16, "k")], [(15, 16, "p")]),
        _make(blink, [(14, 15, 17, 17, "r"), (14, 15, 17, 15, "k")], [(23, 8, "b"), (25, 6, "u")]),
        _make(blink, [(14, 15, 17, 16, "k"), (19, 15, 22, 18, "g")], [(20, 14, "w")]),
    ]

    cel_rc, cel_pt = [], []
    _arm_up(cel_rc, cel_pt, "LR", h=3)
    sprites["CELEBRATE"] = [
        _make(crouch, [], _confetti(0)),
        _make(pet_h, cel_rc, cel_pt + _confetti(1), dy=-1),
        _make(jump_peak, [], _confetti(2), dy=-2),
        _make(pet_h, cel_rc, cel_pt + _confetti(3), dy=0),
    ]
    hf0, hf1, hf2 = ([], []), ([], []), ([], [])
    _arm_up(hf0[0], hf0[1], "R", h=0)
    _arm_up(hf1[0], hf1[1], "R", h=3)
    _arm_up(hf2[0], hf2[1], "R", h=2)
    sprites["HIGHFIVE"] = [
        _make(idle0, hf0[0], hf0[1]),
        _make(pet_h, hf1[0], hf1[1], dy=-1),
        _make(pet_h, hf1[0], hf1[1] + [(23, 8, "y"), (27, 5, "W"), (30, 8, "y"), (27, 12, "y"), (24, 6, "a"), (29, 6, "a")], dy=-1),
        _make(wink, hf2[0], hf2[1] + [(28, 7, "y")]),
    ]
    orbit = [((8, 2), (16, 1), (24, 2)), ((6, 3), (12, 2), (21, 1)), ((10, 1), (19, 1), (26, 3)), ((13, 2), (23, 2), (8, 3))]
    sprites["DIZZY"] = [
        _make(hyper0 if i % 2 == 0 else _mirror_h(hyper0), [], [(p[0], p[1], "y" if j != 1 else "a") for j, p in enumerate(orb)], dx=(-1 if i == 1 else (1 if i == 3 else 0)))
        for i, orb in enumerate(orbit)
    ]

    # WAVE: raised paw cleanly outside right ear silhouette, firmly joined at shoulder
    def _wave_f(base, shift_out=0, dy=0, extra_pt=()):
        rc = [(23, 19, 26, 24, "."), (23, 17, 25 + shift_out, 19, "g"), (24 + shift_out, 12, 26 + shift_out, 19, "g"), (25 + shift_out, 12, 26 + shift_out, 13, "w")]
        pt = [(23 + shift_out, 17, "k"), (24 + shift_out, 12, "k"), (25 + shift_out, 11, "k"), (26 + shift_out, 11, "k"),
              (27 + shift_out, 12, "k"), (27 + shift_out, 13, "k"), (27 + shift_out, 14, "k"), (27 + shift_out, 15, "k"),
              (24, 20, "k"), (25 + shift_out, 19, "k")] + list(extra_pt)
        return _make(base, rc, pt, dy=dy)

    sprites["WAVE"] = [
        _wave_f(pet_h, 0, 0, [(29, 11, "W")]),
        _wave_f(wink, 2, -1, [(30, 10, "y")]),
        _wave_f(pet_h, 0, 0, [(22, 11, "W")]),
        _wave_f(wink, 2, -1, [(29, 9, "y")]),
    ]
    sprites["SELFIE"] = [
        _make(idle0, [(25, 14, 29, 18, "d"), (26, 15, 28, 17, "a")], [(27, 16, "u")]),
        _make(wink, [(25, 14, 29, 18, "d"), (26, 15, 28, 17, "W")], [(27, 13, "y"), (24, 14, "W"), (30, 14, "W"), (27, 19, "W")]),
        _make(pet_h, [(25, 14, 29, 18, "d"), (26, 15, 28, 17, "W")], [(27, 11, "t"), (22, 12, "y"), (31, 12, "y"), (23, 17, "y")]),
        _make(wink, [(25, 14, 29, 18, "d"), (26, 15, 28, 17, "b")], [(27, 16, "W")]),
    ]
    g_rc = [(10, 20, 23, 23, "r"), (8, 19, 13, 25, "R"), (12, 21, 24, 21, "y")]
    sprites["GUITAR"] = [
        _make(idle0, g_rc, [(6, 4, "y"), (26, 4, "b")]),
        _make(pet_h, g_rc, [(19, 22, "g"), (20, 22, "W"), (5, 3, "a"), (27, 5, "n")], dx=1, dy=-1),
        _make(pet_h, g_rc, [(19, 20, "g"), (25, 3, "v")], dy=0),
        _make(wink, g_rc, [(27, 2, "y"), (4, 5, "b")], dx=-1, dy=-1),
    ]
    drum_rc = [(11, 21, 20, 25, "r"), (11, 21, 20, 22, "W"), (11, 25, 20, 25, "W")]
    sprites["DRUM"] = [
        _make(pet_h, drum_rc + [(7, 16, 13, 17, "c"), (18, 19, 24, 20, "c")], [(14, 18, "y"), (24, 19, "h")]),
        _make(pet_h, drum_rc + [(7, 19, 13, 20, "c"), (18, 16, 24, 17, "c")], [(17, 18, "a"), (8, 19, "h")], dy=-1),
        _make(pet_h, drum_rc + [(8, 18, 14, 19, "c"), (17, 18, 23, 19, "c")], [(15, 19, "y"), (16, 19, "W")]),
        _make(wink, drum_rc + [(7, 16, 13, 17, "c"), (18, 16, 24, 17, "c")], [(13, 15, "y"), (18, 15, "y"), (15, 14, "W")], dy=-1),
    ]
    sprites["THINK"] = [
        _make(idle0, [(18, 16, 21, 19, "g")], [(24, 9, "W")]),
        _make(idle0, [(18, 16, 21, 19, "g")], [(24, 9, "W"), (26, 7, "W")]),
        _make(_eyes(idle0, "look_r"), [(18, 16, 21, 19, "g")], [(24, 9, "W"), (26, 7, "W"), (28, 4, "y"), (29, 4, "y")]),
        _make(pet_h, [(18, 16, 21, 19, "g")], [(27, 3, "y"), (28, 3, "y"), (27, 4, "t"), (28, 4, "t"), (27, 5, "s"), (26, 2, "W"), (29, 2, "W")]),
    ]
    flex_rc = [(4, 14, 6, 18, "g"), (6, 17, 8, 19, "g"), (25, 14, 27, 18, "g"), (23, 17, 25, 19, "g"), (4, 13, 6, 14, "w"), (25, 13, 27, 14, "w")]
    sprites["FLEX"] = [
        _make(idle0, flex_rc, [(2, 13, "y"), (29, 13, "y")]),
        _make(pet_h, flex_rc, [(3, 11, "W"), (5, 10, "y"), (26, 10, "y"), (28, 11, "W")], dy=-1),
        _make(wink, flex_rc, [(2, 12, "y"), (29, 12, "y"), (15, 2, "y"), (16, 2, "y")]),
    ]

    # 16 Brand-New Animations (all crisp & defect-free!)
    sprites["DIVE_WAVE"] = [
        _wave_f(pet_h, 0, 0, [(27, 6, "p")]),
        _wave_f(wink, 2, -1, [(27, 4, "r"), (28, 3, "r")]),
        _wave_f(pet_h, 0, 0, [(26, 5, "p")]),
        _make(_eyes(crouch, "happy"), [(3, 29, 28, 29, "s")], [(7, 28, "u"), (24, 28, "u")]),
    ]
    inv_tuck = _make(idle0, [(7, 25, 24, 31, "."), (9, 24, 13, 26, "g"), (18, 24, 22, 26, "g")])[::-1]
    sprites["DIVE_DOWN"] = [
        _make(jump_peak, [(9, 1, 12, 8, "g"), (19, 1, 22, 8, "g"), (10, 0, 11, 2, "w"), (20, 0, 21, 2, "w")], [(7, 4, "u"), (24, 4, "u")], dy=-2),
        _make(inv_tuck, [(11, 24, 14, 30, "g"), (17, 24, 20, 30, "g"), (12, 29, 13, 30, "w"), (18, 29, 19, 30, "w")], [(5, 9, "u"), (26, 9, "u")], dy=1),
        _make(inv_tuck, [(10, 2, 13, 7, "s"), (18, 2, 21, 7, "s"), (11, 26, 13, 31, "w"), (18, 26, 20, 31, "w")], [(4, 15, "W"), (27, 15, "W"), (15, 1, "u")], dy=3),
        _to_grid([(9, 20, 13, 27, "g"), (18, 20, 22, 27, "g"), (10, 18, 12, 20, "w"), (19, 18, 21, 20, "w")],
                 [(6, 17, "u"), (8, 15, "W"), (15, 14, "b"), (23, 15, "W"), (25, 17, "u"), (5, 26, "a"), (26, 26, "a")]),
    ]
    # Fixed PEEK: apply eye mode BEFORE shifting down +15!
    sprites["PEEK"] = [
        _peek_from(idle0, dy=2),
        _peek_from(_eyes(idle0, "look_l"), dy=0),
        _peek_from(_eyes(idle0, "look_r"), dy=0),
        _peek_from(pet_h, dy=-1),
    ]
    # Smooth rounded outlined EARS_WIGGLE!
    ear_l_up = [(3, 4, 8, 11, "."), (3, 4, 7, 9, "k"), (4, 5, 6, 8, "g"), (4, 6, 5, 8, "w")]
    ear_r_up = [(23, 4, 28, 11, "."), (24, 4, 28, 9, "k"), (25, 5, 27, 8, "g"), (26, 6, 27, 8, "w")]
    sprites["EARS_WIGGLE"] = [
        idle0,
        _make(idle0, ear_l_up, [(15, 13, "s"), (2, 5, "W")]),
        _make(idle0, ear_r_up, [(16, 13, "s"), (29, 5, "W")]),
        _make(pet_h, ear_l_up + ear_r_up, [(2, 4, "y"), (29, 4, "y"), (10, 14, "r"), (21, 14, "r")], dy=-1),
    ]
    sprites["BLINK_SMILE"] = [idle0, blink, pet_h, _make(pet_h, [], [(10, 14, "r"), (21, 14, "r")], dy=-1)]
    lap_rc = [(9, 20, 22, 26, "k"), (10, 21, 21, 25, "d"), (8, 27, 23, 28, "s")]
    sprites["LAPTOP_CODE"] = [
        _make(study0, lap_rc + [(11, 22, 16, 22, "n"), (11, 24, 19, 24, "a")], [(7, 26, "g"), (24, 25, "g")]),
        _make(study1, lap_rc + [(11, 22, 18, 22, "a"), (12, 24, 20, 24, "y")], [(7, 25, "g"), (24, 26, "g")]),
        _make(study0, lap_rc + [(11, 22, 19, 22, "n"), (11, 23, 15, 23, "W"), (11, 24, 17, 24, "n")], [(8, 26, "g"), (23, 25, "g")]),
        _make(pet_h, lap_rc + [(12, 22, 19, 22, "n"), (14, 23, 17, 24, "a")], [(15, 19, "n"), (16, 19, "n")]),
    ]
    mag_rc = [(23, 17, 27, 21, "k"), (24, 18, 26, 20, "u"), (21, 21, 23, 24, "h")]
    sprites["MAGNIFY"] = [
        _make(_eyes(idle0, "look_r"), mag_rc, [(25, 19, "a")]),
        _make(_eyes(idle0, "look_r"), [(x - 2, y, x2 - 2, y2, c) for x, y, x2, y2, c in mag_rc], [(23, 19, "W")], dx=1),
        _make(_eyes(idle0, "look_l"), [(x - 16, y, x2 - 16, y2, c) for x, y, x2, y2, c in mag_rc], [(9, 19, "a")], dx=-1),
        _make(pet_h, mag_rc, [(25, 19, "y"), (28, 16, "y")]),
    ]
    sprites["PAPER_PLANE"] = [
        _make(idle0, [(22, 18, 26, 20, "W")], [(25, 19, "u")]),
        _make(wink, [(24, 13, 28, 15, "W")], [(27, 14, "u"), (23, 15, "s")]),
        _make(pet_h, [], [(26, 10, "W"), (27, 10, "W"), (28, 10, "W"), (27, 9, "W"), (28, 11, "u"), (23, 11, "s")]),
        _make(pet_h, [], [(29, 7, "W"), (30, 7, "W"), (31, 7, "W"), (30, 6, "W"), (26, 8, "u")]),
    ]
    umb_rc = [(15, 3, 16, 19, "d"), (8, 3, 23, 4, "r"), (10, 2, 21, 2, "r"), (12, 1, 19, 1, "R"), (14, 0, 17, 0, "y"),
              (11, 3, 13, 4, "W"), (18, 3, 20, 4, "W"), (23, 16, 25, 22, "c")]
    rain = [
        [(3, 2, "b"), (28, 5, "b"), (4, 15, "a"), (27, 20, "a"), (6, 28, "u")],
        [(4, 8, "b"), (29, 11, "b"), (3, 21, "a"), (28, 26, "a"), (5, 1, "u")],
        [(5, 14, "b"), (27, 17, "b"), (4, 27, "a"), (29, 3, "a"), (26, 29, "u")],
        [(3, 19, "b"), (28, 22, "b"), (5, 6, "a"), (27, 9, "a"), (3, 29, "u")],
    ]
    sprites["UMBRELLA"] = [_make(pet_h if i % 2 else idle0, umb_rc, rain[i], dy=1) for i in range(4)]

    tuck_ball = _make(pet_h, [(5, 18, 8, 24, "."), (23, 18, 26, 24, "."), (8, 24, 23, 31, "."),
                              (10, 18, 21, 23, "g"), (12, 19, 19, 22, "w"), (10, 23, 14, 25, "k"), (17, 23, 21, 25, "k")])
    sprites["BACKFLIP"] = [
        _eyes(crouch, "happy"),
        _make(jump_peak, [], [(14, 28, "u"), (17, 28, "u")], dy=-2),
        _make(tuck_ball[::-1], [], [(6, 12, "y"), (25, 12, "y"), (6, 18, "a"), (25, 18, "a")], dy=1),
        _make(_mirror_h(jump_peak), [], [(5, 8, "y"), (26, 8, "y")], dy=-1),
        _make(pet_h, [], [(7, 30, "y"), (24, 30, "y"), (15, 2, "W")], dy=1),
    ]

    # Rounded dark-outlined SPIN side & back views matching IDLE0 art style!
    side_r = _to_grid([
        (11, 6, 18, 15, "k"), (12, 7, 17, 14, "g"), (10, 8, 19, 14, "k"), (11, 8, 18, 14, "g"),
        (11, 5, 16, 10, "k"), (12, 6, 15, 9, "g"), (13, 7, 14, 8, "w"),
        (11, 16, 19, 17, "k"), (11, 18, 19, 25, "k"), (12, 18, 18, 24, "g"), (16, 19, 18, 23, "w"),
        (19, 12, 22, 14, "k"), (12, 25, 17, 30, "k"), (13, 25, 16, 28, "g"), (13, 29, 17, 30, "s"), (12, 19, 15, 23, "s"),
    ], [(16, 11, "W"), (17, 11, "k"), (16, 14, "p"), (10, 21, "w"), (10, 22, "k"), (11, 20, "k"),
        (11, 5, "."), (16, 5, ".")])
    back_v = _to_grid([
        (4, 5, 8, 10, "k"), (23, 5, 27, 10, "k"), (3, 7, 8, 10, "k"), (23, 7, 28, 10, "k"),
        (4, 6, 7, 9, "g"), (24, 6, 27, 9, "g"), (5, 7, 6, 8, "s"), (25, 7, 26, 8, "s"),
        (10, 6, 21, 16, "k"), (8, 8, 23, 15, "k"), (9, 7, 22, 15, "g"), (9, 17, 22, 17, "k"),
        (8, 18, 23, 25, "k"), (9, 18, 22, 24, "g"), (11, 19, 20, 24, "s"),
        (14, 22, 17, 24, "w"), (10, 26, 14, 30, "k"), (17, 26, 21, 30, "k"), (11, 26, 13, 28, "g"), (18, 26, 20, 28, "g"),
        (10, 29, 14, 30, "s"), (17, 29, 21, 30, "s"),
    ], [(14, 22, "k"), (17, 22, "k"), (4, 5, "."), (27, 5, "."), (3, 7, "."), (28, 7, "."), (3, 10, "."), (28, 10, ".")])
    sprites["SPIN"] = [idle0, side_r, back_v, _mirror_h(side_r)]

    def _jet_f(step):
        rc = [(5, 19, 8, 25, "d"), (23, 19, 26, 25, "d"), (6, 18, 7, 19, "r"), (24, 18, 25, 19, "r")]
        f1 = 26 + (step % 2) * 2
        pt = [(6, 26, "W"), (7, 26, "y"), (24, 26, "W"), (25, 26, "y"), (6, 27, "y"), (7, 27, "f"),
              (24, 27, "y"), (25, 27, "f"), (6, f1, "f"), (24, f1, "f"), (5, 28, "u"), (26, 28, "u")]
        return _make(pet_h, rc, pt, dy=-(step % 2) - 1)

    sprites["JETPACK"] = [_jet_f(i) for i in range(4)]
    plush = [(11, 19, 20, 24, "r"), (12, 18, 14, 19, "R"), (17, 18, 19, 19, "R"), (13, 25, 18, 26, "r"), (14, 20, 17, 23, "p")]
    sprites["HUG_PLUSH"] = [
        _make(pet_h, plush, [(9, 19, "g"), (22, 19, "g")]),
        _make(pet_h, plush, [(10, 20, "g"), (21, 20, "g"), (5, 4, "p"), (26, 4, "r")], dy=-1),
        _make(blink, plush, [(9, 19, "g"), (22, 19, "g")]),
        _make(pet_h, plush, [(10, 20, "g"), (21, 20, "g"), (15, 2, "r")], dy=-1),
    ]
    euc = [(12, 18, 13, 26, "h"), (10, 17, 13, 19, "e"), (14, 19, 18, 21, "e"), (9, 21, 13, 23, "E"), (15, 23, 19, 25, "e")]
    sprites["EUCALYPTUS_HUG"] = [
        _make(pet_h, euc, [(22, 19, "e")]),
        _make(pet_h, euc, [(22, 18, "e"), (8, 15, "n"), (24, 14, "n")], dy=-1),
        _make(wink, euc, [(21, 20, "E"), (15, 16, "n")]),
    ]
    horn_base = [(13, 3, 18, 5, "m"), (14, 1, 17, 2, "R"), (15, 0, 16, 0, "y")]
    sprites["PARTY_HORN"] = [
        _make(pet_h, horn_base + [(16, 15, 19, 16, "r")], _confetti(0)),
        _make(pet_h, horn_base + [(16, 15, 24, 16, "r"), (25, 15, 26, 16, "y")], _confetti(1), dy=-1),
        _make(wink, horn_base + [(16, 15, 28, 16, "y"), (27, 14, 29, 15, "r")], _confetti(2), dy=-1),
        _make(pet_h, horn_base + [(16, 15, 21, 16, "r")], _confetti(3)),
    ]
    _bg = _shift(blink, dy=3)
    _paint(_bg, [(11, 20, 20, 23, "g"), (13, 21, 18, 23, "s")], [(10, 29, "k"), (21, 29, "k"), (6, 10, "y"), (25, 10, "y")])
    sprites["BOW"] = [idle0, _make(blink, [], [], dy=1), ["".join(r) for r in _bg], _make(pet_h, [], [(15, 2, "y"), (16, 2, "y")])]
