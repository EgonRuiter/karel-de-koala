#!/usr/bin/env python3
"""18 Sticky Skins, 22 Single-Slot Wardrobe Outfits, 10 Mini-Pet Sprites & Overlay Renderer."""

SKINS = {
    "classic": ("Klassiek Koala Grijs", 0, {}),
    "sticky": ("Sticky Rood", 160, {"g": "r", "s": "R", "w": "W"}),
    "bestuur": ("Bestuurs-Blazer", 380, {"g": "k", "s": "d", "w": "r"}),
    "baco": ("BaCo Bar-Kostuum", 340, {"g": "R", "s": "k", "w": "y"}),
    "kbg_beton": ("KBG Beton & Glas", 240, {"g": "u", "s": "d", "w": "a"}),
    "vagant_neon": ("De Vagant Neon", 440, {"g": "d", "s": "k", "w": "v"}),
    "tram22": ("Tram 22 Geel", 360, {"g": "y", "s": "Y", "w": "r"}),
    "uithof_gans": ("Uithof Witte Gans", 390, {"g": "W", "s": "u", "w": "o"}),
    "polar": ("IJsbeer Sneeuwwit", 190, {"g": "W", "s": "u", "w": "a"}),
    "panda": ("Stickykamer Panda", 220, {"g": "W", "s": "k", "w": "r"}),
    "sakura": ("Wilhelminapark Blossom", 260, {"g": "p", "s": "P", "w": "W"}),
    "mint": ("Eucalyptus Mint", 270, {"g": "n", "s": "e", "w": "W"}),
    "cyber": ("Koala Cyber Matrix", 340, {"g": "d", "s": "k", "w": "a"}),
    "midnight": ("BBG Nachtwacht", 370, {"g": "m", "s": "k", "w": "b"}),
    "vapor": ("Science Park Synth", 460, {"g": "v", "s": "V", "w": "a"}),
    "sunset": ("'t Gras Zonsondergang", 350, {"g": "o", "s": "r", "w": "y"}),
    "crimson": ("Crimson RP2350", 520, {"g": "R", "s": "r", "w": "y"}),
    "gold": ("Lustrum Gouden Koala", 850, {"g": "y", "s": "Y", "w": "W"}),
}

WARDROBE_ITEMS = {
    "scarf": ("Sticky Sjaal", 0, "Iconische rode Sticky sjaal"),
    "stickycap": ("Sticky Baseball Cap", 150, "Stoere rode pet uit de Stickykamer"),
    "hoodie": ("Sticky Hoodie & Laptop", 190, "Voor Informatiekunde-devs (gratis Lv.4)"),
    "partyhat": ("De Vagant Feestmuts", 140, "Altijd klaar voor de borrel"),
    "headphones": ("Lo-Fi Study Koptelefoon", 180, "Focus-modus tijdens programmeren"),
    "wizard": ("CommITCrowd Tovenaarhoed", 220, "Magische Koala debugging-krachten"),
    "shades": ("Deal-With-It Zonnebril", 300, "Konami unlock of direct kopen"),
    "crown": ("Bestuurskroon", 650, "Ere-bestuur (of gratis Lv.8 / 100 knuffels)"),
    "sash": ("Bestuurslint", 320, "Koninklijk rood-wit Sticky bestuurssjerp"),
    "baco_bow": ("BaCo Bar-Vlinderdas", 160, "Stijlvol achter de tap bij de borrel"),
    "hacc_scarf": ("HACC UTP-Sjaal", 210, "Warme Cat6-kabel voor tijdens hackathons"),
    "tosti_pin": ("Gouden Tosti-Speld", 230, "Officieel ereteken voor tosti-bakkers"),
    "cape": ("Super-Koala Cape", 280, "Wapperende rode Sticky superheldencape"),
    "wings": ("Engelenvleugels", 360, "Zuivere code, nul bugs in productie"),
    "horns": ("Force-Push Duiveltje", 250, "Voor als je force-pusht naar main"),
    "cowboy": ("Uithof Cowboyhoed", 200, "Yeehaw over 't Gras naar BBG"),
    "gradcap": ("Afstudeerhoed (BSc/MSc)", 450, "Voor echte Informatiekunde-alumni!"),
    "goggles": ("Debug-Duikbril", 240, "Diepduiken in legacy spaghetti-code"),
    "vr": ("College VR-Bril", 420, "Virtueel hoorcollege in KBG vanuit bed"),
    "nerd": ("College-Bril", 130, "Slimme uitstraling (+100 focus)"),
    "backpack": ("Stickykamer Rugzak", 270, "Altijd extra ruimte voor tosti's"),
    "umbrella": ("Utrecht Regenhoed", 220, "Beschermt tegen Hollandse buien op de fiets"),
}

# Gameplay synergy perk per equipped single outfit: (perk_key, multiplier_bonus, nl_label)
OUTFIT_PERKS = {
    "scarf": ("pet_xp", 0.15, "+15% XP bij aaien"),
    "stickycap": ("roam_coins", 0.25, "+25% scherm-buit munten"),
    "hoodie": ("study_xp", 0.25, "+25% XP bij CommITCrowd & studeren"),
    "partyhat": ("dance_xp", 0.25, "+25% XP bij dansen & jammen"),
    "headphones": ("energy_save", 0.25, "Energie daalt 25% trager"),
    "wizard": ("spell_bonus", 0.30, "+30% beloning uit toverspreuken"),
    "shades": ("game_coins", 0.20, "+20% munten in mini-games"),
    "crown": ("all_xp", 0.15, "+15% XP op álle acties"),
    "sash": ("committee_coins", 0.20, "+20% munten bij commissies"),
    "baco_bow": ("baco_coins", 0.35, "+35% munten bij BaCo & borrel"),
    "hacc_scarf": ("game_coins", 0.25, "+25% munten in Arcade mini-games"),
    "tosti_pin": ("cook_xp", 0.30, "+30% XP bij eten & koken"),
    "cape": ("roam_speed", 0.25, "+25% loopsnelheid"),
    "wings": ("hunger_save", 0.25, "Honger daalt 25% trager"),
    "horns": ("coffee_xp", 0.30, "+30% XP & blijheid bij koffie"),
    "cowboy": ("roam_speed", 0.20, "+20% sneller sprinten"),
    "gradcap": ("trivia_xp", 0.35, "+35% munten & XP bij Trivia"),
    "goggles": ("fish_luck", 0.30, "Veel meer kans op zeldzame vis-schatten"),
    "vr": ("study_xp", 0.25, "+25% CommITCrowd & Trivia XP"),
    "nerd": ("trivia_xp", 0.25, "+25% munten & XP bij Trivia"),
    "backpack": ("cook_xp", 0.25, "+25% keuken & snacks XP"),
    "umbrella": ("wash_bonus", 0.30, "+30% blijheid & XP bij wassen"),
}


def get_outfit_perk(equipped):
    """Return (wid, perk_key, bonus, label) for the single equipped item, or None."""
    if not equipped:
        return None
    wid = equipped[0]
    p = OUTFIT_PERKS.get(wid)
    return (wid, p[0], p[1], p[2]) if p else None

COMPANION_SPRITES = {
    "duckie": [
        ["..........", "...kkk....", "..kyyyk...", "..kykyok..", "..kyyyk...", ".kyyyyyk..", "kyyYyyyyk.", ".kkyyykk..", "...k.k....", "..o...o..."],
        ["...kkk....", "..kyyyk...", "..kykyok..", "..kyyyk...", ".kyyyyyk..", "kyyYyyyyk.", ".kkyyykk..", "...k.k....", "..o...o...", ".........."],
    ],
    "buggy": [
        ["..k...k...", "...k.k....", "..kkkkk...", ".krrkrrk..", "krrkWkrrk.", "krrrrrrrk.", ".krrkrrk..", "..kkkkk...", ".k.....k..", ".........."],
        ["...k.k....", "..kkkkk...", ".krrkrrk..", "krrkWkrrk.", "krrrrrrrk.", ".krrkrrk..", "..kkkkk...", ".k.....k..", "..k...k...", ".........."],
    ],
    "mug_jr": [
        ["....W..W..", "...W....W.", "..kkkkkk..", ".kcccccck.", ".krrrrrrkk", ".krrWWrrkk", ".krrrrrrk.", ".krrrrrrk.", "..kkkkkk..", ".........."],
        ["...W..W...", "....W..W..", "..kkkkkk..", ".kcccccck.", ".krrrrrrkk", ".krrWWrrkk", ".krrrrrrk.", ".krrrrrrk.", "..kkkkkk..", ".........."],
    ],
    "bmo21": [
        ["..kkkkkk..", ".kaaaaaak.", ".kaakaaak.", ".kaaaaWak.", ".kaakkkak.", ".klrlklrk.", ".kllllllk.", "..kkkkkk..", "..k....k..", ".........."],
        ["..kkkkkk..", ".kllllllk.", ".klakaaak.", ".kaanaaak.", ".kaakkkak.", ".klrlklrk.", ".kaaaaaak.", "..kkkkkk..", "...k..k...", ".........."],
    ],
    "floppy": [
        [".kkkkkkkk.", ".kddddddk.", ".kdWWWWdk.", ".kdWWWWdk.", ".kddddddk.", ".kdyyyydk.", ".kdyktydk.", ".kdyyyydk.", ".kkkkkkkk.", ".........."],
        ["..........", ".kkkkkkkk.", ".kddddddk.", ".kdWWWWdk.", ".kdWWWWdk.", ".kddddddk.", ".kdyyyydk.", ".kdyktydk.", ".kdyyyydk.", ".kkkkkkkk."],
    ],
    "spirit": [
        ["....e.....", "..eenee...", ".enWWWne..", ".enWnWne..", ".ennnnne..", ".eeeeeee..", "..eenee...", "...e.e....", "....n.....", ".........."],
        ["...e.e....", ".eennnee..", ".enWnWne..", ".enWWWne..", ".ennnnne..", ".eeeeeee..", "..eenee...", "...n.e....", "..........", ".........."],
    ],
    "gans": [
        ["....kkk...", "...kWWok..", "...kWkkk..", "....kWk...", "..kkkWWk..", ".kWWWWWWk.", ".kWWuuWWk.", "..kkkkkk..", "...o..o...", ".........."],
        ["....kkk...", "...kWWok..", "...kWkk...", "....kWk...", "..kkkWWk..", ".kWWWWWWk.", ".kWWuuWWk.", "..kkkkkk..", "..o....o..", ".........."],
    ],
    "tram22": [
        ["..........", "..kkkkkk..", ".kyyyyyyk.", ".kyakakyk.", ".kyyyyyyk.", ".krrrrrrk.", ".kYYYYYYk.", "..kkkkkk..", "..d....d..", ".........."],
        ["..kkkkkk..", ".kyyyyyyk.", ".kyakakyk.", ".kyyyyyyk.", ".krrrrrrk.", ".kYYYYYYk.", "..kkkkkk..", "..d....d..", "..........", ".........."],
    ],
    "tosti_jr": [
        ["..kkkkkk..", ".khhhhhhk.", ".khtyythk.", ".khtyythk.", ".khhhhhhk.", ".kddddddk.", "..kkkkkk..", "...k..k...", "..d....d..", ".........."],
        ["...W..W...", "..kkkkkk..", ".khhhhhhk.", ".khtyythk.", ".khtyythk.", ".khhhhhhk.", ".kddddddk.", "..kkkkkk..", "...k..k...", ".........."],
    ],
    "mini_karel": [
        [".k......k.", "kskkkkkksk", ".kggggggk.", ".gkWkkWgk.", ".kggkkggk.", ".krrrrrrk.", ".kggWWggk.", ".kkkkkkkk.", "..g....g..", ".........."],
        [".k......k.", "kskkkkkksk", ".kggggggk.", ".gkkggkkg.", ".kggkkggk.", ".krrrrrrk.", ".kggWWggk.", ".kkkkkkkk.", "...g..g...", ".........."],
    ],
}


def _paint(g, rects, pts):
    h, w = len(g), len(g[0])
    for x0, y0, x1, y1, ch in rects:
        for y in range(max(0, y0), min(h, y1 + 1)):
            for x in range(max(0, x0), min(w, x1 + 1)):
                g[y][x] = ch
    for x, y, ch in pts:
        if 0 <= x < w and 0 <= y < h:
            g[y][x] = ch


def apply_accessories(frame, st, lvl, sh, cr, tr, vm, eq=None, skin="classic"):
    """Apply skin recoloring and STRICTLY max 1 equipped clothing/accessory item."""
    smap = SKINS.get(skin, SKINS["classic"])[2]
    g = [[smap.get(c, c) for c in r] for r in frame] if smap else [list(r) for r in frame]
    if st in (
        "SLEEP", "CRY", "YAWN", "DIZZY", "CLIMB", "DIVE_WAVE", "DIVE_DOWN",
        "PEEK", "BACKFLIP", "SPIN", "UMBRELLA", "MUSIC", "EXERCISE",
        "LAPTOP_CODE", "SIT", "STRETCH", "BOW", "PARTY_HORN", "GAMING",
    ):
        return ["".join(r) for r in g]

    if eq is None:
        eq = ["scarf"]
    # Strictly only 1 item worn at any time
    valid_eq = [w for w in eq if w in WARDROBE_ITEMS]
    item = valid_eq[0] if valid_eq else None
    rc, pt = [], []

    if item == "cape" and st not in ("CLIMB", "JETPACK", "JUMP", "FLEX", "EXERCISE"):
        rc += [(5, 19, 8, 27, "r"), (23, 19, 26, 27, "r"), (6, 27, 7, 29, "S"), (24, 27, 25, 29, "S")]
    elif item == "wings" and st not in ("CLIMB", "JETPACK", "JUMP", "FLEX", "EXERCISE"):
        rc += [(1, 15, 5, 19, "W"), (26, 15, 30, 19, "W"), (2, 20, 5, 22, "u"), (26, 20, 29, 22, "u")]
    elif item == "backpack" and st not in ("CLIMB", "JETPACK", "JUMP", "FLEX", "EXERCISE"):
        rc += [(5, 20, 8, 26, "h"), (6, 21, 7, 24, "r")]
    elif item == "scarf":
        rc += [(10, 17, 21, 18, "r"), (17, 19, 18, 22, "r")]
        pt += [(x, 18, "R") for x in range(10, 22, 3)]
    elif item == "hacc_scarf":
        rc += [(10, 17, 21, 18, "b"), (17, 19, 18, 22, "b")]
        pt += [(x, 18, "a") for x in range(10, 22, 3)] + [(18, 23, "y")]
    elif item == "baco_bow":
        rc += [(13, 18, 18, 19, "r"), (15, 18, 16, 19, "k")]
        pt += [(13, 18, "R"), (18, 18, "R")]
    elif item == "sash":
        for i in range(6):
            pt += [(11 + i, 19 + i, "r"), (12 + i, 19 + i, "W")]
    elif item == "tosti_pin":
        rc += [(18, 19, 21, 22, "h"), (19, 20, 20, 21, "y")]
        pt += [(19, 19, "Y")]
    elif item == "hoodie":
        rc += [(8, 19, 11, 20, "r"), (20, 19, 23, 20, "r"), (11, 24, 20, 25, "r")]
        if st in ("IDLE", "WALK_LEFT", "WALK_RIGHT", "PET", "CLIMB"):
            rc += [(24, 25, 29, 28, "d"), (25, 26, 28, 27, "b"), (24, 29, 29, 29, "k")]
    elif item == "headphones" and st != "JUMP":
        rc += [(3, 7, 4, 11, "r"), (27, 7, 28, 11, "r"), (7, 4, 24, 4, "d")]
        pt += [(5, 6, "d"), (6, 5, "d"), (25, 5, "d"), (26, 6, "d")]
    elif item == "stickycap" and st != "JUMP":
        rc += [(9, 4, 22, 5, "r"), (11, 2, 20, 4, "r"), (19, 5, 25, 5, "R")]
        pt += [(15, 3, "W"), (16, 3, "W")]
    elif item == "umbrella" and st != "JUMP":
        rc += [(6, 4, 25, 4, "b"), (9, 2, 22, 3, "a"), (14, 1, 17, 1, "y")]
        pt += [(15, 5, "y"), (16, 5, "y")]
    elif item == "wizard" and st != "JUMP":
        rc += [(9, 4, 22, 5, "m"), (12, 2, 19, 3, "m"), (14, 0, 17, 1, "m"), (11, 4, 20, 4, "y")]
        pt += [(15, 2, "y"), (16, 1, "W")]
    elif item == "gradcap" and st != "JUMP":
        rc += [(8, 3, 23, 4, "k"), (11, 5, 20, 5, "k"), (22, 5, 22, 9, "y")]
        pt += [(22, 10, "Y"), (15, 3, "r")]
    elif item == "cowboy" and st != "JUMP":
        rc += [(7, 5, 24, 5, "h"), (10, 2, 21, 4, "h"), (10, 4, 21, 4, "H")]
        pt += [(15, 4, "y"), (16, 4, "y")]
    elif item == "partyhat" and st != "JUMP":
        rc += [(13, 3, 18, 5, "m"), (14, 1, 17, 2, "R")]
        pt += [(15, 0, "y"), (16, 0, "y"), (14, 4, "y"), (17, 3, "b")]
    elif item == "horns" and st != "JUMP":
        rc += [(8, 2, 9, 5, "r"), (22, 2, 23, 5, "r")]
        pt += [(7, 1, "R"), (24, 1, "R")]
    elif item == "crown" and st != "JUMP":
        rc.append((12, 3, 19, 5, "y"))
        pt += [(12, 2, "y"), (15, 1, "y"), (16, 1, "y"), (19, 2, "y"),
               (15, 4, "R"), (16, 4, "R"), (11, 5, "k"), (20, 5, "k")]
    elif item == "vr" and st != "JUMP":
        rc += [(9, 9, 22, 13, "k"), (10, 10, 21, 12, "a")]
        pt += [(12, 11, "W"), (19, 11, "W")]
    elif item == "shades" and st != "JUMP":
        rc += [(10, 10, 13, 12, "k"), (18, 10, 21, 12, "k"), (14, 11, 17, 11, "d")]
        pt += [(11, 11, "W"), (19, 11, "W")]
    elif item == "goggles" and st != "JUMP":
        rc += [(9, 10, 13, 12, "b"), (18, 10, 22, 12, "b"), (14, 11, 17, 11, "d")]
        pt += [(10, 11, "u"), (21, 11, "u")]
    elif item == "nerd" and st != "JUMP":
        rc += [(14, 11, 17, 11, "k")]
        pt += [(9, 10, "k"), (9, 12, "k"), (13, 10, "k"), (13, 12, "k"),
               (18, 10, "k"), (18, 12, "k"), (22, 10, "k"), (22, 12, "k")]

    if tr and st not in ("HYPER", "JUMP"):
        pt += [(x, y, "s") for x in (11, 12, 19, 20) for y in (11, 13)]
        if not vm and st not in ("EAT", "STUDY", "COFFEE", "CLIMB", "TOSTI", "BORREL"):
            rc += [(24, 18, 28, 23, "k"), (25, 19, 27, 22, "r"), (25, 18, 27, 18, "c")]
            pt += [(29, 19, "W"), (29, 20, "W"), (26, 15, "W"), (25, 16, "W")]

    if vm and st not in ("EAT", "STUDY", "JUMP", "CLIMB", "BORREL"):
        rc += [(24, 18, 28, 23, "k"), (25, 19, 27, 22, "y"), (24, 17, 27, 18, "W")]
        pt += [(26, 20, "W"), (29, 19, "w"), (29, 20, "w"), (29, 21, "w")]

    _paint(g, rc, pt)
    return ["".join(r) for r in g]
