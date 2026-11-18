#!/usr/bin/env python3
"""Expanded Sticky Lore, Cooldowns, Recipes, StickyDex, Committees, Quests & Trivia."""

import datetime
import random

# Cooldowns in seconds per action key + funny Sticky reason
COOLDOWNS = {
    "feed": (45, "Karel kauwt nog rustig op zijn blaadje..."),
    "feed_item": (18, "Karel slikt eerst deze Sticky snack door!"),
    "coffee": (45, "De koffiemachine in de Stickykamer warmt op!"),
    "pet": (30, "Karel geniet nog even na van die knuffel!"),
    "wash": (120, "Zeepbellen in het BBG zijn nog aan het drogen!"),
    "dance": (60, "Karel moet even op adem komen na dat dansje!"),
    "exercise": (75, "Even spierpijn weglachen met SportCo!"),
    "cast_spell": (180, "Mana-buffer laadt nog op in de BBG-kelder!"),
    "fish": (150, "De Kromme Rijn moet even nieuwe schatten aanspoelen!"),
    "craft": (30, "Het Sticky tosti-ijzer staat nog te gloeien!"),
    "play_toy": (60, "Karel stopt het speeltje heel even weg!"),
    "gacha": (45, "De Grijpmachine in de Stickykamer vult zichzelf bij!"),
    "trivia": (180, "EduCo bedenkt een nieuwe Informatiekunde-vraag!"),
    "boop": (90, "De USB-boop-condensator moet even opladen!"),
    "committee": (300, "Commissievergadering duurt even — straks weer!"),
    "selfie": (60, "Camera-rolletje van de Almanakwerkgroep is bijna vol!"),
    "music_jam": (60, "Bandjes moeten even stemmen voor het BBG-optreden!"),
    "game_reward": (20, "Arcade-kassa telt nog de laatste Sticky-munten!"),
}

FOOD_SHOP = {
    "tosti": {
        "name": "Sticky Tosti", "price": 15, "hunger": 45, "happiness": 12,
        "energy": 8, "caffeine": 0, "xp": 15, "desc": "+45 Honger, +12 Blijheid",
    },
    "filterkoffie": {
        "name": "Stickykamer Filterkoffie", "price": 10, "hunger": 2, "happiness": 10,
        "energy": 25, "caffeine": 30, "xp": 14, "desc": "+25 Energie, +30 Cafeïne",
    },
    "espresso": {
        "name": "BBG Dubbele Espresso", "price": 20, "hunger": 5, "happiness": 14,
        "energy": 35, "caffeine": 42, "xp": 20, "desc": "+35 Energie, +42 Cafeïne",
    },
    "bitterbal": {
        "name": "De Vagant Bitterballen", "price": 28, "hunger": 35, "happiness": 28,
        "energy": 10, "caffeine": 0, "xp": 25, "desc": "+35 Honger, +28 Blijheid",
    },
    "borrelplank": {
        "name": "BaCo Borrelplank", "price": 36, "hunger": 42, "happiness": 38,
        "energy": 16, "caffeine": 0, "xp": 32, "desc": "+42 Honger, +38 Blijheid",
    },
    "stroopwafel": {
        "name": "Utrechtse Stroopwafel", "price": 18, "hunger": 22, "happiness": 24,
        "energy": 18, "caffeine": 5, "xp": 18, "desc": "+22 Honger, +24 Blijheid",
    },
    "bbg_koek": {
        "name": "BBG Automaten-Koek", "price": 14, "hunger": 26, "happiness": 14,
        "energy": 15, "caffeine": 0, "xp": 14, "desc": "Klassieke muntjes-automaat (+26 Honger)",
    },
    "alv_pizza": {
        "name": "ALV Pizza Punt", "price": 32, "hunger": 55, "happiness": 30,
        "energy": 22, "caffeine": 0, "xp": 30, "desc": "Houdt je uren wakker tijdens moties!",
    },
    "wrap": {
        "name": "Kromme Rijn Wrap", "price": 26, "hunger": 48, "happiness": 22,
        "energy": 24, "caffeine": 0, "xp": 24, "desc": "Gezonde lunch op 't Gras (+48 Honger)",
    },
    "golden_leaf": {
        "name": "Gouden Eucalyptus", "price": 52, "hunger": 75, "happiness": 48,
        "energy": 35, "caffeine": 0, "xp": 55, "desc": "Mega Sticky-feestmaal (+55 XP!)",
    },
}

INGREDIENTS = {
    "brood": {"name": "Stickykamer Casinobrood", "price": 6},
    "kaas": {"name": "Jonge Belegen Kaas", "price": 8},
    "blad": {"name": "Verse Eucalyptus", "price": 7},
    "boon": {"name": "Sticky Koffieboon", "price": 10},
    "bes": {"name": "Uithof Bosbes", "price": 9},
    "suiker": {"name": "Suikerklontje", "price": 6},
    "saus": {"name": "Tosti-Curry & Mayo", "price": 7},
    "peper": {"name": "De Vagant Mosterd", "price": 8},
    "goudvlok": {"name": "Lustrum Goudvlok", "price": 22},
    "sterrenstof": {"name": "Koala Sterrenstof", "price": 30},
}

RECIPES = {
    "ham_kaas_tosti": {
        "name": "Klassieke Sticky Tosti",
        "ing": {"brood": 2, "kaas": 1},
        "hunger": 55, "happiness": 20, "energy": 12, "caffeine": 0, "xp": 32,
        "anim": "TOSTI", "desc": "Knapperige tosti met gesmolten kaas (+32 XP)",
    },
    "curry_tosti": {
        "name": "Stickykamer Curry-Tosti",
        "ing": {"brood": 2, "kaas": 1, "saus": 1},
        "hunger": 62, "happiness": 26, "energy": 14, "caffeine": 0, "xp": 40,
        "anim": "TOSTI", "desc": "De legendarische kamersmaak (+40 XP)",
    },
    "pesto_tosti": {
        "name": "Eucalyptus Pesto Tosti",
        "ing": {"brood": 2, "kaas": 1, "blad": 1},
        "hunger": 65, "happiness": 28, "energy": 18, "caffeine": 0, "xp": 45,
        "anim": "TOSTI", "desc": "Culinair tosti-meesterwerk (+45 XP)",
    },
    "tripel_espresso": {
        "name": "BBG Tripel Espresso",
        "ing": {"boon": 2, "suiker": 1},
        "hunger": 5, "happiness": 20, "energy": 50, "caffeine": 55, "xp": 42,
        "anim": "COFFEE", "desc": "Direct 50 Energie & +55 Cafeïne (+42 XP)",
    },
    "matcha_koala": {
        "name": "Minnaert Matcha Latte",
        "ing": {"blad": 2, "suiker": 1},
        "hunger": 25, "happiness": 32, "energy": 30, "caffeine": 20, "xp": 38,
        "anim": "COFFEE", "desc": "Zen-focus tussen de rode Minnaert-muren",
    },
    "bramen_smoothie": {
        "name": "Uithof Bosbes Smoothie",
        "ing": {"bes": 2, "blad": 1, "suiker": 1},
        "hunger": 40, "happiness": 38, "energy": 35, "caffeine": 0, "xp": 48,
        "anim": "EAT", "desc": "Vitaminebom voor lange deadlines (+48 XP)",
    },
    "bitterbal_mix": {
        "name": "Vagant Mosterd-Schaal",
        "ing": {"brood": 1, "kaas": 1, "peper": 2},
        "hunger": 52, "happiness": 45, "energy": 20, "caffeine": 0, "xp": 50,
        "anim": "BORREL", "desc": "BaCo favoriet met extra scherpe mosterd",
    },
    "koala_soep": {
        "name": "CommITCrowd Debug-Soep",
        "ing": {"blad": 2, "bes": 1, "saus": 1},
        "hunger": 58, "happiness": 36, "energy": 35, "caffeine": 0, "xp": 54,
        "anim": "EAT", "desc": "Fixt zelfs vastgelopen inschrijvingen",
    },
    "intro_ontbijt": {
        "name": "Intro-Kamp Sjaars Ontbijt",
        "ing": {"brood": 2, "bes": 1, "boon": 1},
        "hunger": 70, "happiness": 45, "energy": 45, "caffeine": 25, "xp": 60,
        "anim": "TOSTI", "desc": "Na een nachtje Cook Commissie-corvee (+60 XP)",
    },
    "nachtbraker_elixer": {
        "name": "Nachtbraker Study Elixer",
        "ing": {"boon": 2, "bes": 1, "suiker": 1},
        "hunger": 15, "happiness": 25, "energy": 75, "caffeine": 45, "xp": 58,
        "anim": "WIZARD_CAST", "desc": "Herstelt 75 Energie meteen (+58 XP)",
    },
    "tram22_broodje": {
        "name": "Tram 22 Haast-Broodje",
        "ing": {"brood": 2, "peper": 1, "saus": 1},
        "hunger": 64, "happiness": 34, "energy": 30, "caffeine": 0, "xp": 52,
        "anim": "TOSTI", "desc": "Snel opgegeten voordat de tram wegrijdt!",
    },
    "vrijmibo_borrel": {
        "name": "VrijMiBo Luxe Platter",
        "ing": {"kaas": 2, "peper": 1, "bes": 1},
        "hunger": 60, "happiness": 62, "energy": 25, "caffeine": 0, "xp": 65,
        "anim": "BORREL", "desc": "Feest in De Vagant! (+62 Blijheid, +65 XP)",
    },
    "bestuurs_fondue": {
        "name": "Gouden Bestuursfondue",
        "ing": {"kaas": 2, "brood": 2, "goudvlok": 1},
        "hunger": 90, "happiness": 65, "energy": 30, "caffeine": 0, "xp": 85,
        "anim": "TOSTI", "desc": "Het Sticky Bestuur keurt dit heerlijk goed",
    },
    "lustrum_taart": {
        "name": "Sticky Lustrum Gala-Taart",
        "ing": {"bes": 2, "suiker": 2, "goudvlok": 1},
        "hunger": 80, "happiness": 85, "energy": 45, "caffeine": 0, "xp": 92,
        "anim": "CELEBRATE", "desc": "Proost op een prachtig lustrumjaar!",
    },
    "hyper_9000": {
        "name": "Overclock Koffie 9000",
        "ing": {"boon": 3, "goudvlok": 1},
        "hunger": 10, "happiness": 35, "energy": 100, "caffeine": 95, "xp": 95,
        "anim": "HYPER", "desc": "200 MHz overclock! (+100 Energie, +95 XP)",
    },
    "sterren_elixer": {
        "name": "RP2350 Sterrenstof Elixer",
        "ing": {"sterrenstof": 1, "blad": 2, "goudvlok": 1},
        "hunger": 100, "happiness": 100, "energy": 100, "caffeine": 20, "xp": 160,
        "anim": "CELEBRATE", "desc": "Vult ALLE stats tot 100% & +160 XP!",
    },
}

TOYS = {
    "duckie": {"name": "BBG Debugging Eendje", "price": 75, "desc": "+18 Blijheid, +15 XP — bespreek elke bug"},
    "laser": {"name": "College-Laserpointer", "price": 95, "desc": "Karel sprint door collegezaal KBG voor +22 Energie"},
    "mech_kb": {"name": "HACC Cherry-MX Board", "price": 140, "desc": "Enthousiast hacken & gamen voor +28 XP"},
    "krant": {"name": "Sticky Almanak Origami", "price": 85, "desc": "Vouw een Sticky-koala (+22 Blijheid, +18 XP)"},
    "soldeer": {"name": "RP2350 Soldeerboutje", "price": 180, "desc": "Hardware hacken met Karel (+35 XP!)"},
}

UPGRADES = {
    "golden_bowl": {"name": "Gouden Tosti-Schotel", "price": 320, "desc": "Honger daalt 40% trager"},
    "coffee_thermos": {"name": "Sticky Thermosbeker", "price": 380, "desc": "Energie & blijheid dalen 35% trager"},
    "coin_magnet": {"name": "Sticky Munt-Magneet", "price": 480, "desc": "+50% bonusmunten in alle mini-games"},
    "turbo_sneakers": {"name": "Uithof Turbo Sneakers", "price": 440, "desc": "Sneller lopen & +50% scherm-buit"},
    "soap_dispenser": {"name": "Auto-Zeep Dispenser", "price": 340, "desc": "Hygiëne daalt 50% trager"},
    "disco_speaker": {"name": "De Vagant Sound System", "price": 520, "desc": "+50% XP bij dansen, jammen & aaien"},
    "lucky_clover": {"name": "BBG Geluksklaver", "price": 620, "desc": "Dubbele kans op Epische & Legendarische schatten"},
    "overclock_2040": {"name": "RP2350 Dual-Core OC", "price": 880, "desc": "+30% XP op alle acties & mini-games"},
    "koffie_pas": {"name": "Stickykamer Koffiepas", "price": 580, "desc": "Halveert de cooldown op Sticky-koffie!"},
    "vip_pas": {"name": "Sticky Commissie VIP-Pas", "price": 750, "desc": "+25% beloning bij alle Commissie-missies"},
}

COMPANIONS = {
    "none": ("Geen Maatje", 0, "Rustig alleen op je bureaublad", "#6C727D"),
    "duckie": ("Duckie jr.", 140, "Geel debugging-eendje uit het BBG", "#FFD700"),
    "buggy": ("Pixel Kever", 180, "Schattige rode Bug (zonder crashes)", "#FF5252"),
    "mug_jr": ("Koffiekopje Jr.", 220, "Stomende Stickykamer mok aan je zijde", "#B21B21"),
    "bmo21": ("Mini-Bot 21", 280, "Retro cyaan schermrobotje van Sticky", "#4FC3F7"),
    "floppy": ("Gouden Floppy", 340, "Zwevende 1.44 MB nostalgie uit BBG", "#FFB300"),
    "spirit": ("Eucalyptus Geest", 480, "Lichtgevende groene magische orb", "#69F0AE"),
    "gans": ("Uithof Gans Jr.", 400, "Brutale campus-gans die voor je juicht", "#E2E5EB"),
    "tram22": ("Mini Tram 22", 520, "Gele USP-tram (komt precies op tijd!)", "#FFD700"),
    "tosti_jr": ("Lopend Tosti-IJzer", 580, "Houdt je snacks lekker knapperig warm", "#8D6E63"),
    "mini_karel": ("Klein Koalaatje", 720, "Schattige mini-Sticky mascotte!", "#B21B21"),
}

# 28 Real Sticky Committees & Working Groups:
# (id, name, desc, min_coins, min_xp, anim, quote)
COMMITTEES = [
    ("baco", "BaCo — Themaborrel Tappen", "Verzorgt Sticky's iconische themaborrels zoals Kloktoberfest!", 28, 32, "BORREL",
     "BaCo dienst klaar! Iedereen een borrel van Karel!"),
    ("attac", "AttaC — Algemene Activiteiten", "Fietsborrels, bosklimmen & paintballen zonder vast thema!", 22, 38, "DANCE",
     "AttaC activiteit was weer onvergetelijk chaotisch!"),
    ("hacc", "HACC — Hackathon & Coding", "Organiseert programmeerwedstrijden & hackathons rond het BBG!", 30, 34, "GAMING",
     "Alle teamprojecten & coding-challenges op tijd ingeleverd!"),
    ("intro", "Introcommissie — Sjaars Week", "Zomervakantie opofferen voor een knallende introductieperiode!", 24, 36, "WAVE",
     "Alle nieuwe sjaars zijn nu officieel verliefd op Sticky!"),
    ("ejw", "Eerstejaarsweekendcommissie", "Laagdrempelig introductieweekend voor verse eerstejaars!", 25, 36, "CELEBRATE",
     "Eerstejaarsweekend geslaagd: nieuwe vriendengroepen gesmeed!"),
    ("educo", "EduCo — Academische Ontwikkeling", "Studiedagen, Teacher Awards & brug tussen student en docent!", 32, 42, "THINK",
     "EduCo studiedag vol lof! Docenten klappen mee!"),
    ("cards", "C.A.R.D.S. — Bord- & Kaartspellen", "Strategische bordspellen & kaartavonden voor iedereen!", 25, 35, "EXERCISE",
     "C.A.R.D.S. avond gewonnen zonder ruzie om de spelregels!"),
    ("cook", "Cook Commissie — Kampcatering", "Menu's plannen & koken voor EJW en Actief Leden Weekend!", 35, 30, "TOSTI",
     "Grote ketels vol smaak! Topcatering van de Cook Commissie!"),
    ("koco", "KoCo — Kookworkshops & Etentjes", "Samen koken, etentjes & paasontbijt voor alle fijnproevers!", 26, 34, "EAT",
     "De KoCo-maaltijd verdween binnen tien minuten!"),
    ("dies", "Dies — Verjaardagsweek Sticky", "Jaarlijkse verjaardag in april/mei met BBQ, cantus & thema!", 34, 40, "CELEBRATE",
     "Hiep hiep hoera! Diesweek vol taart, cantus & gezelligheid!"),
    ("airco", "AirCo — Europese Citytrips", "Weekendjes weg om samen prachtige Europese steden te verkennen!", 30, 38, "HIGHFIVE",
     "Koffers gepakt! AirCo citytrip was weer op en top geregeld!"),
    ("studiereis", "Studiereiscommissie — Verre Reis", "Jaarlijkse grote reis vol cultuur, plezier & bedrijfsbezoeken!", 38, 46, "STUDY",
     "Intercontinentale Sticky-studiereis zit veilig in de logboeken!"),
    ("wispo", "Wispo — Wintersport in de Alpen", "Zoekt het hele jaar naar de beste pistes, sneeuw & après-ski!", 32, 38, "JUMP",
     "Skibril op, piste af — Wispo was legendarisch!"),
    ("alw", "ALW — Actief Leden Weekend", "Jaarlijks ontspannend weekend weg voor alle actieve Sticky-leden!", 29, 37, "STRETCH",
     "ALW-kampvuur brandde tot diep in de nacht!"),
    ("cultco", "CultCo — Culturele Commissie", "Museumbezoeken, unieke filmavonden & creatieve workshops!", 24, 36, "MUSIC",
     "Cultuur gesnoven en stiekem bijgeleerd met CultCo!"),
    ("dgdarc", "DGDARC — Game Dev & Research", "Game jams, studio-lunches & lezingen rond Game Technology!", 30, 42, "GAMING",
     "Playable prototype af in 48 uur tijdens de DGDARC Game Jam!"),
    ("master1", "Mastercommissie 1 — MSc Events", "Informele & gezellige activiteiten voor en door masterstudenten!", 26, 38, "COFFEE",
     "Masterstudenten bijgepraat onder het genot van filterkoffie!"),
    ("master2", "Mastercommissie 2 — MSc Connect", "Extra borrels & lunches zodat masters elkaar moeiteloos vinden!", 26, 38, "HIGHFIVE",
     "Scriptiestress samen weggelachen dankzij Mastercommissie 2!"),
    ("nova", "NOVA — Nazomer Overbrugging", "Activiteiten aan het eind van de zomer voor vliegende college-start!", 25, 34, "WAVE",
     "De zomervakantie uitknallen met frisse NOVA-activiteiten!"),
    ("sportco", "SportCo — Sport & Batavierenrace", "Sportieve activiteiten voor iedereen én de jaarlijkse Batavierenrace!", 28, 36, "FLEX",
     "Estafettestokje doorgegeven op de Batavierenrace!"),
    ("tuco", "TuCo — De Vagant Tuincommissie", "Onderhoudt het bloeiende stukje groen achter De Vagant!", 24, 34, "WASH",
     "Verse munt en nieuwe plantjes groeien achter De Vagant!"),
    ("vrijmico", "VrijMiCo — Vrijdagmiddagborrel", "Luidt elke vrijdagmiddag feestelijk het weekend in voor leden!", 26, 32, "BORREL",
     "De vrijdagmiddag ingeluid! Weekend officieel begonnen!"),
    ("wit", "WIT — Women in IT", "Gezellige tapas- & filmavonden toegankelijk voor heel Sticky!", 25, 36, "LOVE",
     "Tapas en topfilms gedeeld bij een warme WIT-avond!"),
    ("xcom", "XCOM — Externe Bedrijfscontacten", "Ondersteunt Commissaris Extern bij acquisitie & lunchlezingen!", 34, 42, "THINK",
     "Succesvolle lunchlezing en verse sponsoring binnen via XCOM!"),
    ("commitcrowd", "CommITCrowd [Werkgroep] — IT & Koala", "Beheert Sticky's servers, tools & Koala-infrastructuur!", 28, 44, "STUDY",
     "Koala draait weer als een zonnetje! Deploy geslaagd!"),
    ("media", "Mediawerkgroep [Werkgroep] — Foto & Film", "Legt borrels vast en monteert aftermovies van Sticky-reizen!", 26, 35, "SELFIE",
     "Aftermovie gemonteerd en de scherpste borrelfoto's geüpload!"),
    ("almanak", "Almanakwerkgroep [Werkgroep] — Lustrumboek", "Bundelt vijf jaar foto's, verhalen & bestuurshistorie in de almanak!", 30, 40, "STUDY",
     "De drukproef van de nieuwe Lustrum-Almanak ziet er strak uit!"),
    ("kascom", "KasCom [Raad] — Financiële Controle", "Controleert nauwlettend de boekhouding en kas met de penningmeester!", 32, 38, "THINK",
     "Balans klopt tot op de laatste Sticky-cent — KasCom akkoord!"),
]

# 6 Random Campus Weather Events rolled once per startup / day: (title, buff_desc, buff_tag)
CAMPUS_EVENTS = [
    ("Vandaag op De Uithof: Gratis Koekjes in de Stickykamer!", "+25% XP bij eten & koken vandaag.", "food_xp"),
    ("Tram 22 rijdt zowaar op tijd! Goede karma door het BBG.", "+50% munten & hogere kans op bureaublad-buit.", "roam_loot"),
    ("Ganzen-alert op het plein bij het Educatorium!", "+25% bonusmunten in Uithof Ganzen Run!", "gans_coins"),
    ("Vandaag in het BBG: De koffiepot is vers gezet!", "+30% XP & extra blijheid bij koffie vandaag.", "coffee_xp"),
    ("CommITCrowd Maintenancedag: Alle commits gemerged.", "Extra hoge kans op zeldzame StickyDex-schatten!", "fish_rarity"),
    ("Zonnig terrasweer bij De Vagant & 't Gras!", "+30% blijheid & XP bij knuffels en dansjes!", "happy_boost"),
]

# 36 StickyDex Collectibles: (id, name, rarity, sell_coins, desc)
LOOT_TABLE = [
    ("old_boot", "Natte Klomp", "Gewoon", 6, "Opgevist uit de Kromme Rijn op De Uithof."),
    ("leaf_fossil", "Fossiel Blad", "Gewoon", 8, "Oeroud eucalyptusblad van een vorige generatie."),
    ("sticky_sticker", "Sticky Laptop-Sticker", "Gewoon", 9, "Plakt trots op elke Informatiekunde-laptop."),
    ("paperclip", "Verbogen Paperclip", "Gewoon", 7, "Houdt een half tentamendossier bij elkaar."),
    ("free_pens", "Utrecht U Pen", "Gewoon", 8, "Doet het nog maar héél soms tijdens college."),
    ("usbc_cable", "Korte USB-C Kabel", "Gewoon", 10, "Precies lang genoeg voor een RP2350 SuperMini."),
    ("gans_veer", "Uithof Ganzenveer", "Gewoon", 11, "Gevonden na een spannende sprint naar tram 22."),
    ("bbg_krijtje", "Krijtje uit BBG 065", "Gewoon", 9, "Voor snelle grafentheorie op het grote bord."),
    ("ov_pasje", "Vergeten Campuskaart", "Gewoon", 12, "Ligt altijd precies naast het tosti-apparaat."),
    ("coffee_card", "Volle Koffiekaart", "Zeldzaam", 18, "Goed voor gratis filterkoffie in de Stickykamer."),
    ("git_merge", "Schone Git Merge", "Zeldzaam", 20, "Zonder één conflict gerebased om 03:00!"),
    ("stroop_tin", "BBG Stroopwafelblik", "Zeldzaam", 22, "Ooit gevuld in de Stickykamer, nu vol met 1M-Ohm weerstandjes."),
    ("rubber_duck", "Luxe Code-Eendje", "Zeldzaam", 24, "Lost 90% van alle bugs op als je ernaar kijkt."),
    ("mech_cap", "Rode ESC-Keycap", "Zeldzaam", 25, "Sticky-rood PBT mechanisch toetsje."),
    ("borrel_token", "De Vagant Muntje", "Zeldzaam", 26, "Altijd geldig op donderdag en vrijdag!"),
    ("almanak_edit", "Sticky Almanak Editie", "Zeldzaam", 24, "Vol grappige quotes en foto's van leden."),
    ("hacc_splitter", "HACC Hackathon Switch", "Zeldzaam", 28, "Voor spontane CTF-, Code- & Smash-sessies."),
    ("intro_bandje", "Intro-Kamp Polsbandje", "Zeldzaam", 27, "Herinneringen aan de mooiste eerste week."),
    ("tosti_gold", "Verguld Tosti-IJzer", "Episch", 42, "Bakt perfecte driehoekjes zonder zwarte randjes."),
    ("koala_plush", "Mini Karel Knuffel", "Episch", 45, "Zachte pluche dubbelganger van jezelf."),
    ("dark_mode", "Koala Dark Mode CSS", "Episch", 48, "Zero white flashes bij het inschrijven in Koala."),
    ("crt_monitor", "Retro CRT Schermpje", "Episch", 50, "Geeft authentieke 60Hz Sticky-kelder vibes."),
    ("wizard_rune", "Lambda-Steen", "Episch", 55, "Functioneel programmeren zonder side-effects."),
    ("golden_mouse", "Gouden Trackball", "Episch", 58, "Uit het Minnaert-archief opgegraven."),
    ("vagant_opener", "BaCo Bieropener", "Episch", 60, "Gegraveerd met het Sticky-logo."),
    ("sport_beker", "Sticky Sportdag Beker", "Episch", 62, "Met bloed, zweet en bitterballen gewonnen."),
    ("dies_stropdas", "Lustrum Gala-Stropdas", "Episch", 65, "Dieprood met minuscule pixels geweven."),
    ("rp2040_diamond", "Diamanten RP2350", "Legendarisch", 95, "Dual-core Arm Cortex-M33 van puur kristal."),
    ("bestuur_scepter", "Sticky Bestuurshamer", "Legendarisch", 110, "Voor plechtige ALV-hamerslagen."),
    ("infinite_coffee", "Eeuwige Stickykamer Mok", "Legendarisch", 120, "Koelt nooit af, raakt nooit leeg."),
    ("bug_zero", "Zero-Bug Certificaat", "Legendarisch", 130, "Gecheckt in productie op vrijdagmiddag 16:59!"),
    ("rector_medal", "Medaille van de Uithof", "Legendarisch", 145, "Voor doorgewinterde Informatiekunde-helden."),
    ("koala_db_key", "Gouden Koala-Sleutel", "Legendarisch", 155, "Toegang tot het hart van het Sticky-systeem."),
    ("tram22_bel", "Gouden Tram 22 Bel", "Legendarisch", 160, "Tingelt als je op tijd voor je hoorcollege bent."),
    ("lustrum_kroon", "Lustrum Kroon van Sticky", "Legendarisch", 170, "Schittert al jarenlang op het Science Park."),
    ("karel_statue", "Gouden Karel Standbeeld", "Legendarisch", 185, "Het ultieme pronkstuk van jouw desktop!"),
]

TITLES = [
    "Sjaars Koala",                 # Lv 1
    "Stickykamer Bezoeker",         # Lv 2
    "Koffie-Schenker",              # Lv 3
    "Tosti-Bakker",                 # Lv 4
    "Bestuurs-Karel",               # Lv 5
    "AttaC Held",                   # Lv 7
    "BaCo Tapper",                  # Lv 9
    "Bug-Jager in BBG",             # Lv 11
    "Senior Koala",                 # Lv 13
    "CommITCrowd Wizard",           # Lv 16
    "BBG Legende",                  # Lv 19
    "De Vagant VIP",                # Lv 22
    "Master of Sticky",             # Lv 26
    "RP2350 Architect",             # Lv 32
    "Uithof Ganzenfluisteraar",     # Lv 40
    "Opperkoala van Sticky",        # Lv 50
    "Erelid der Sticky",            # Lv 60
    "Lustrum Legende",              # Lv 75
    "Grootmeester in BBG",          # Lv 90
    "Mythische Sticky Mascotte",    # Lv 100+
]

ACHIEVEMENTS = {
    "Sticky Lid": "Karel ontwaakt op je bureau.",
    "Konami Koala": "Konami code: Disco Borrel Mode!",
    "Cafeïne Overdosis": "3 Sticky koffies binnen 2 min.",
    "Nachtbraker": "Tussen 00:00 en 04:00 wakker.",
    "Borrelbeest": "VrijMiBo gevierd (vrijdag >=16:00).",
    "100x Geknuffeld": "100x geaaid (Gouden Kroon!).",
    "Stof-allergie": "7x op Karels neus geklikt.",
    "Bestuurs-Karel": "Level 5 bereikt!",
    "Eucalyptus Kampioen": "200+ in Eucalyptus Catch.",
    "Flappy Koala": "Score 15+ in Koala Flappy Hop.",
    "Bug Hunter": "Score 250+ in BBG Bug Smasher.",
    "Memory Meester": "Sticky Memory gewonnen in <=14 zetten.",
    "Vliegende Koala": "Karel vrolijk over het scherm gegooid.",
    "Schoon & Fris": "Karel gewassen met zeepbellen.",
    "Sticky Shopper": "Eerste item in het Sticky Winkeltje gekocht.",
    "Munten-Verzamelaar": "1500+ Sticky Munten verzameld.",
    "Senior Koala": "Level 13 bereikt!",
    "Rector Karel": "Level 22 bereikt!",
    "Snake Charmer": "Score 12+ in Sticky Code Snake.",
    "Merge Meester": "Haal een 512+ blok in Merge 2048.",
    "Vagant DJ": "Score 300+ in De Vagant Beat Drop.",
    "Dungeon Held": "Versla een Eindbaas in BBG RPG!",
    "Alle Bazen Verslagen": "Versla alle 5 eindbazen in BBG RPG!",
    "Ganzen Sprinter": "Score 150+ in Uithof Ganzen Run!",
    "Koala Verdediger": "Score 180+ in Koala Server Rescue!",
    "Keukenprins": "Eerste recept gekookt in de Tosti-Bar.",
    "Alchemist": "8 unieke recepten gekookt.",
    "Tosti Chef-Kok": "Alle 16 recepten uit de Tosti-Bar gekookt!",
    "Gacha Geluk": "Eerste draai aan de Mystery Grijpmachine.",
    "Schatzoeker": "10 unieke schatten in StickyDex verzameld.",
    "Archivaris": "20 unieke schatten in StickyDex verzameld.",
    "Museumdirecteur": "Alle 36 schatten in StickyDex compleet!",
    "Maatjes voor het Leven": "Eerste Mini-Pet bureau-vriendje gekozen.",
    "Dierentuin op Bureau": "5 mini-maatjes vrijgespeeld!",
    "Mode-Icoon": "5 verschillende vachten ontgrendeld.",
    "Stylist van de Kamer": "6 unieke kledingstukken in bezit.",
    "Vis-Kampioen": "Eerste schat vanaf de taakbalk gevist.",
    "Quiz-Kanon": "10 Trivia-vragen goed beantwoord.",
    "Sticky Wikipedia": "25 Trivia-vragen goed beantwoord!",
    "Sportieve Koala": "Karel laten sporten op het bureaublad.",
    "Magiër van het BBG": "Toverspreuk gecast in de Stickykamer (BBG).",
    "Rockster in De Vagant": "Een 8-bit jam-sessie gespeeld!",
    "Almanak Fotomodel": "Een bureau-selfie gemaakt met Karel.",
    "Actief Commissielid": "Eerste Sticky Commissie-missie voltooid!",
    "Commissie-Kanter": "15 Sticky Commissie-missies voltooid!",
    "Alle Commissies": "Help alle 28 Sticky commissies & werkgroepen!",
    "Hardware Boop": "Karel gewekt via een USB-herstart of hardware-boop!",
    "Opperkoala": "Level 50 behaald — pure toewijding!",
    "Sticky Legende": "Level 75 behaald — eeuwige roem!",
    "Koffie Sommelier": "50 keer Sticky koffie gedronken.",
    "Pomodoro Pro": "Voltooi je eerste Focus Studiemodus sessie!",
    "Focus Legende": "Voltooi 10 Focus Studiemodus sessies met Karel!",
    "Alumni Prestige": "Behaal Alumni Prestige (opnieuw klimmen vanaf Lv.50+).",
}

QUOTES = [
    "Tijd voor gratis koffie in de Stickykamer!",
    "Is het al donderdag voor de borrel in De Vagant?",
    "Het Sticky Bestuur keurt deze code helemaal goed.",
    "Heb je je voor de volgende activiteit ingeschreven op Koala?",
    "Heb je al een git push gedaan vandaag?",
    "Works on my RP2350 SuperMini!",
    "01001011 01100001 01110010 01100101 01101100",
    "Geen bugs, alleen ongedocumenteerde features in Koala.",
    "Informatiekunde > de rest van het Utrecht Science Park.",
    "Zin in een zelfgemaakte tosti uit de Stickykamer?",
    "Altijd handig: nog één keer je PR rebasen om 02:00.",
    "Wist je dat koala's bijna 20 uur slapen? Net als na een ALV.",
    "Wie heeft de koffiepot in het BBG weer leeggemaakt?",
    "Pas op voor zwevende boze ganzen voor het Educatorium!",
    "Als Sticky-cadeau draai ik op slechts 4 MB flash — knap hè?",
    "Probeer de Mystery Grijpmachine eens in het Winkeltje!",
    "Heb je alle 10 Arcade Mini-Games al uitgespeeld?",
    "Check het Sticky BK tabblad voor echte commissie-missies!",
    "Even stretchen! Zit je wel rechtop achter je laptop?",
    "Steek je SuperMini opnieuw in USB-C terwijl Karel draait voor een Hardware Boop!",
    "Tijd voor BBG Dungeon RPG tegen de boze Alpha-Gans!",
    "Wist je dat je StickyDex-schatten kunt vissen vanaf de taakbalk?",
    "Vergeet niet je dagelijkse quests te claimen in de Hub!",
    "Soms liggen er zomaar muntjes of ingrediënten onder een pixel!",
    "Wie gaat mee lunchen op 't Gras tussen de colleges door?",
    "Zet in de Hub de Tram 22 of Lo-Fi muziek aan tijdens het coderen!",
    "Python without semicolons feels so free.",
    "Merge conflict op line 42? Vraag het aan Duckie!",
    "Alumni verdienen voor altijd een trouwe Sticky-koala op hun bureau.",
    "Sticky rood (#C41E25) is wetenschappelijk bewezen de mooiste kleur.",
    "Ik ruik gesmolten kaas... tijd voor de Tosti-Bar!",
    "Als je me oppakt en weggooit kan ik vliegen!",
    "Ik draag altijd netjes maar één kledingstuk tegelijk, wel zo stijlvol.",
    "Houd BOOT ingedrukt bij het inpluggen van USB-C als je firmware wilt updaten.",
    "Aai me 100 keer voor de Gouden Bestuurskroon!",
    "Al 36 StickyDex schatten verstopt in de Kromme Rijn & rond BBG!",
    "Echte Informatiekundigen gebruiken dark mode nog vóór hun eerste koffie.",
    "Wie gaat mee naar de ALV voor gratis pizza?",
    "Tram 22 zit vol... gelukkig hoef ik alleen maar over je scherm te lopen!",
    "Even kijken wat CommITCrowd vandaag weer naar productie pusht.",
    "Hatsjoe! Ligt er tosti-poeder in de Stickykamer (BBG)?",
    "BaCo roept: vergeet je borrelmuntjes niet!",
    "Wie wil er een potje Mario Kart in de Stickykamer?",
    "Ik heb outfits met echte perks klaarliggen in Looks & Maatje!",
    "Een echte Informatiekundige schrijft eerst een simulator, daarna de test.",
    "Pas op voor oneindige `while True:` loops zonder `sleep`!",
    "Klik 7 keer snel op mijn neus als je durft...",
    "Probeer de Konami Code: ↑ ↑ ↓ ↓ ← → ← → b a!",
    "Zelfs als de USB los zit blijf ik trouw doordraaien in Geheugen-modus!",
    "Fijne dag toegewenst namens heel Sticky!",
    "Even ademhalen... niet alles hoeft binnen vijf minuten gedeployed.",
    "De Introcommissie vraagt: weet jij de Stickykamer in BBG nog te vinden?",
    "Cook Commissie heeft een geheim recept: extra kaas tussen elk boterhammetje!",
    "EduCo tip: maak back-ups vóór je aan je scriptie sleutelt!",
    "Bij C.A.R.D.S. telt strategisch spelen zwaarder dan geluk (meestal).",
    "AttaC belooft: de volgende activiteit wordt nóg grootser dan lasergamen!",
    "HACC vraagt of jouw laptop genoeg RAM heeft voor nog 40 browser-tabs.",
    "Oud-bestuurder gespot! Koffie staat altijd klaar op de kamer.",
    "Van sjaars naar alumnus: sommige tosti-herinneringen blijven voor eeuwig.",
    "Mijn kleine pixel-oortjes horen elk toetsenbordgeklik!",
    "Ik kan ook op de bovenbalk van je actieve venster klimmen via Loop-Gedrag!",
    "Focus-modus aan? Dan studeer ik muisstil met je mee!",
    "De plantjes van de TuCo achter De Vagant staan er prachtig bij.",
    "Volgende week weer game jammen met de DGDARC!",
    "Van de Batavierenrace via SportCo tot de Alpen met Wispo!",
    "Als je straks Level 50 haalt wacht Alumni Prestige op je!",
    "XCOM regelt vast weer heerlijke gratis lunch bij de lezing!",
    "VrijMiCo zorgt voor het gezelligste begin van je vrijdagavond.",
    "Mediawerkgroep legt onze beste desktop-momenten scherp vast.",
    "Heb je de volumesliders in Status & Audio al precies goed afgesteld?",
    "Soms is tien minuten pauze beter dan twee uur staren naar een stacktrace.",
    "Ook zonder stackoverflow kwamen wij wel uit dat tentamen... oké bijna.",
    "Als deze laptop oververhit raakt, ga ik op je touchpad zonnen!",
    "Elke outfit in mijn kast heeft zijn eigen passieve bonus — probeer ze uit!",
    "Kijk vandaag bij Sticky BK welke dagbuff er actief is op De Uithof!",
    "Ganzen hebben voorrang op het Science Park. Altijd.",
    "Heeft iemand een USB-C kabeltje voor mijn SuperMini gezien?",
    "Tijd voor een rustige eucalyptus-pauze tussen de commits door.",
    "Wie heeft 'DROP TABLE koffiepot;' uitgevoerd op de database?!",
    "Laatst telde ik alle pixels op je monitor. Het waren er minstens twaalf.",
    "Koala's haasten zich niet — echte snelheid zit in schone architectuur.",
    "Als je hard werkt, zorgt Karel ondertussen goed voor je taakbalk.",
    "Stickykamer-regel #1: wie het laatste plakje kaas pakt, haalt nieuw brood.",
    "Mijn RP2350-hartje klopt op 150 MHz — op borrels iets sneller.",
    "Ooit geprobeerd om in 2048 echt tot het Sticky 2048-blok te komen?",
    "De Kromme Rijn stroomt langzaam, maar zit vol zeldzame StickyDex-buit!",
    "Alumni-tip van de dag: drink water tussen je espresso's door.",
    "Geen haast hoor, ik leun hier gewoon relaxed tegen je open venster.",
    "Ik bewaar mijn spulletjes veilig via atomaire opslag op je stick!",
    "Sticky bestaat al jaren dankzij enthousiaste studenten zoals jij.",
    "Bug weggewerkt? Tijd om dat te vieren met een korte mini-game!",
    "Vrolijke groeten uit Utrecht Science Park!",
    "Ik blijf gezellig op mijn plekje zitten tot je weer klaar bent met typen.",
    "Soms staar ik gewoon naar je cursor en filosofeer over P vs NP.",
    "Zet me rustig iets groter of kleiner in de Hub als dat fijner kijkt!",
    "Tot de volgende borrel in De Vagant, alumnus!",
]

ROAM_QUOTES = [
    "Even rustig wandelen over het Utrecht Science Scherm...",
    "Hoppakee! Even kijken achter deze browser-tab.",
    "Volgens mij verstop je hier ergens Stickykamer-tosti's...",
    "Mooi uitzicht over de pixels, net vanaf de 7e verdieping BBG!",
    "Even checken of Tram 22 hier niet voorbijkomt.",
    "Ik ruik een verloren StickyDex-schat in de Kromme Rijn!",
    "Zoek je een rustig hoekje op je bureaublad? Ik houd je gezelschap.",
    "Even een relaxed ommetje langs de desktop-icoontjes.",
    "Is dat een verdwaalde gans onder je Start-knop?!",
    "Op naar de Stickykamer in het BBG van je bureaublad!",
    "Even vriendelijk knikken naar alle medestudenten & alumni!",
    "Wandelen langs 't Gras houdt Karel heerlijk kalm.",
    "Rustig pasje voor rustig pasje... geen haast vandaag.",
    "Even kijken hoe gezellig het bovenaan dit venster is.",
    "Kijk, mijn pixelpootjes maken bijna geen lawaai op het glas.",
    "Even langs de taakbalk struinen op zoek naar kruimels.",
    "Hier op het balkje van je app heb ik mooi overzicht over de hele campus.",
    "Zachtjes landen... zonder een enkele pixel te verschuiven.",
    "Ik patroilleer alleen even of er geen losse bugs rondzwerven.",
    "Tijd om weer ergens knus te gaan zitten.",
    "Even een luchtje scheppen buiten de terminal.",
    "Onderweg van de Stickykamer (BBG) naar college in het KBG!",
    "Soms ontdek je pas iets nieuws als je rustig blijft hangen.",
    "Mijn maatje wandelt trouw achter me aan!",
    "Zelfs op volle breedte van twee schermen blijft dit mijn favoriete plekje.",
    "Zo... hier zit ik wel weer even lekker.",
    "Altijd fijn, zo'n schone desktop zonder twintig zip-bestanden.",
    "Even mijn oortjes rechtzetten tijdens de wandeling.",
]

HYPER_QUOTES = [
    "01001011 01100001 01110010 01100101 01101100",
    "WHILE(TRUE) DRINK_STICKY_COFFEE();",
    "SEGFAULT IN MIJN CAFEINE-BUFFER!!",
    "200 MHz OVERCLOCK GEACTIVEERD!!",
    "STICKYKAMER ESPRESSO MACHINE OP 200 BAR!!",
    "ALLE THREADS OP 100% IN HET BBG!!",
    "IK ZIE DE KOALA MATRIX IN RGB!!",
    "SNELHEID SNELHEID — SNELLER DAN TRAM 22!!",
    "KOFFIE-OVERFLOW OP ADRES 0xC41E25!!",
    "ZOEM ZOEM ZOOMIES OVER DE TAAKBALK!!",
    "MIJN OORHAARTJES VIBREREN OP 60 FPS!!",
    "WIE HEEFT DUBBELE ESPRESSO IN DE KANNEN GEDAAN?!",
    "OVERCLOCKED TO THE MAX!! STICKY POWER!!",
    "COMPILEERTID = 0.0001 MILLISECONDEN!!",
    "DE KOFFIEPOT HEEFT ZELFBEWUSTZIJN GEKREGEN!!",
    "IK KAN DOOR MUURTJES HEEN DEBUGGING DOEN!!",
    "HYPER-MODUS: 3 ESPRESSO'S EN GEEN SPELFOUTEN!!",
    "SNEL NAAR DE STICKYKAMER VOOR EEN TOSTI OM TE AARDEN!!",
]

NIGHT_QUOTES = [
    "Nog steeds bezig met die deadline? Sticky respect!",
    "Zelfs midden in de nacht draait jouw RP2350 trouw door.",
    "Nog één espresso en één schone commit voor het slapen...",
    "Het BBG is pikkedonker, maar jouw laptop gloeit nog!",
    "Vergeet straks niet echt even te gaan slapen hoor!",
    "Nachtbraker-energie: 100% pure Sticky-focus.",
    "De laatste Tram 22 is al lang weg... wij houden het fort nog even.",
    "Stille nacht, perfecte code, knapperige tosti naast het toetsenbord.",
    "Mijn ogen vallen bijna dicht, maar voor jou blijf ik wakker!",
    "Morgenochtend ben je dankbaar als je nu opslaat en rust pakt.",
    "De sterren schijnen boven De Uithof — goedenacht bijna!",
    "Zelfs een nachtbraker verdient zo een zachte powernap.",
    "Om 02:00 lijken alle bugs óf briljant óf onmogelijk.",
    "Zet je scherm iets warmer, dat vindt jouw koala ook fijner.",
    "Fluister-modus aan zodat heel het BBG kan doorslapen.",
    "Nog even doorzetten of lekker onder de wol, ik ben trots op je!",
]

PET_QUOTES = [
    "Prrr... lief! *Sticky knuffel*",
    "Aaaah, precies achter mijn linkeroor!",
    "Zachte aai-sessie van een echte alumnus!",
    "Hier wordt een desktop-koala heel blij van.",
    "Prrr... voelt als een vrije middag op 't Gras!",
    "Nog zo'n knuffel en ik begin te spinnen op 440 Hz!",
    "Kijk mijn kleine wangen helemaal gloeien!",
    "Lief! Dat had ik echt even nodig tussen al dat coderen door.",
    "Sticky-keurmerk voor beste bureaublad-knuffelaar!",
    "Even lekker kroelen op de taakbalk.",
    "Zo aardig! Nu kan ik weer uren tegen deadlines aan.",
    "Dikke koala-knuffel terug!",
]

FEED_QUOTES = [
    "Nom nom! Verse eucalyptus!",
    "Knapperig! Net zo lekker als een kamertosti!",
    "Mmm... dit smaakt naar vijf sterren uit de Cook Commissie!",
    "Hap slik weg! Karel heeft weer brandstof!",
    "Dankjewel! Geen enkele hongerige pixel meer over.",
    "Heerlijk rustig op een blaadje kauwen...",
    "Zo, buikje rond en hoofd weer scherp!",
    "Beste lunch van heel Utrecht Science Park!",
    "Nog een kruimeltje voor mijn buurmaatsje?",
    "Yum! Direct weer energie voor de volgende sessie.",
    "Smaakt als goud! Dankjewel kok!",
    "Eucalyptus-perfectionisme in 32x32 pixels!",
]

COFFEE_QUOTES = [
    "Heerlijke Sticky koffie!",
    "Ahh... Stickykamer-zwartgoud!",
    "Caffeine.init() voltooid — klaar voor productie!",
    "Warme mok uit de Stickykamer (BBG), heerlijk!",
    "Dat werkt tien keer beter dan slaap!",
    "Precies de juiste temperatuur, nul compiler-warnings!",
    "Proost op alle nachtbrakers & scriptieschrijvers!",
    "Even nippen... aah, pure Informatiekunde-brandstof!",
    "Met deze mok overleef ik zelfs een drie uur durende ALV!",
    "Mmm, gebrand met passie door de koffieliefhebbers van Sticky!",
    "Eén slok en alle syntax-fouten springen meteen in het oog!",
    "Lekker bakkie! Vergeet niet: 3 heel snel achter elkaar = Overclock!",
]

TRIVIA_QUESTIONS = [
    ("In welk gebouw zit Sticky's gezelligheidskamer & BK?", ["Buys Ballotgebouw (BBG)", "Koningsbergergebouw (KBG)", "Ruppertgebouw"], 0),
    ("Welke studievereniging is voor Informatiekunde in Utrecht?", ["Sticky", "Plakband", "Muisjes"], 0),
    ("Welke microcontroller drijft dit USB-cadeau aan?", ["RP2350", "ATmega8", "ESP8266"], 0),
    ("Wat is de signature kleurcode van Sticky?", ["#B21B21", "#00FF00", "#FF00FF"], 0),
    ("Hoe heet het iconische inschrijfsysteem van Sticky?", ["Koala", "EucalyptusDB", "TramSys"], 0),
    ("Welke kroeg bezoekt Sticky klassiek voor borrels?", ["De Vagant", "Het Laboratorium", "Cafe Pixel"], 0),
    ("Welk gebouw naast het BBG ken je van hoor- en werkcolleges?", ["Koningsbergergebouw (KBG)", "Ziggo Dome", "NEMO"], 0),
    ("Welke lijn rijdt dwars over het Utrecht Science Park naar CS?", ["Tram 22", "Bus 999", "Metro Noord"], 0),
    ("Welke dieren staan op de Uithof bekend om hun brutale karakter?", ["Ganzen", "Pinguïns", "Flamingo's"], 0),
    ("Hoe heet het grasveld waar Utrechters lunchen op de Uithof?", ["'t Gras", "Het Binnenplein", "Eucalyptusweide"], 0),
    ("Welke Sticky-commissie regelt borrels en staat achter de tap?", ["BaCo", "SleepCo", "SyntaxCo"], 0),
    ("Welke werkgroep beheert de Sticky-websites, systemen & Koala?", ["CommITCrowd", "PostCo", "KrijtCo"], 0),
    ("Welke Sticky-commissie organiseert hackathons en coding-wedstrijden?", ["HACC", "WifiCo", "FaxCo"], 0),
    ("Welke snack wordt het meest gebakken in de Stickykamer?", ["Tosti's", "Kaviaar", "Poffertjes"], 0),
    ("Hoe zet je jouw RP2350 SuperMini in UF2 firmware-updatemodus?", ["BOOT inhouden + USB inpluggen", "Hard schudden", "Alt+F4 op je USB-poort"], 0),
    ("Hoe vaak doe je `git commit` idealiter?", ["Bij kleine logische stappen", "1x per jaar", "Nooit"], 0),
    ("Hoeveel bits is een standaard IPv4-adres?", ["32 bits", "16 bits", "128 bits"], 0),
    ("Welke datastructuur werkt volgens FIFO?", ["Queue", "Stack", "Binary Tree"], 0),
    ("Wat betekent `O(1)` complexiteit?", ["Constante rekentijd", "Kwadratisch traag", "Oneindige loop"], 0),
    ("Welk HTTP-statusnummer betekent 'OK'?", ["200", "404", "503"], 0),
    ("Wat gebruik je in Python om een bestand netjes automatisch te sluiten?", ["with open(...) as f:", "always_open()", "try: delete"], 0),
    ("Welk commando toon je in Python voor tekst-uitvoer?", ["print()", "echo_out()", "console.say()"], 0),
    ("Hoeveel kernen heeft de RP2350-chip?", ["2 (Dual ARM Cortex-M33)", "16", "1"], 0),
    ("Welke poort hoort standaard bij HTTPS?", ["443", "21", "8080"], 0),
    ("Wat doet `git rebase`?", ["Commits schoon herspelen", "Alles verwijderen", "Scherm dimmen"], 0),
    ("Welk bestand op je USB-stick draait zodra CircuitPython opstart?", ["code.py", "autorun.docx", "boot.exe"], 0),
    ("Wat gebeurt er op vrijdag na 16:00 bij Karel?", ["VrijMiBo-modus!", "Zelfdestructie", "Update naar DOS"], 0),
    ("Waar eet Karel van nature vooral van?", ["Eucalyptus", "Kwarktaart", "Batterijen"], 0),
    ("Wat betekent SQL?", ["Structured Query Language", "Sticky Quick Loop", "Super Quantum Logic"], 0),
    ("Hoeveel kledingstukken draagt Karel nu netjes tegelijk?", ["Max 1 tegelijk", "Alle 22 tegelijk", "Minimaal 7"], 0),
]

QUEST_POOL = [
    ("pet", "Aai Karel 6 keer", 6, 35, 28),
    ("feed", "Geef Karel 5 keer eten", 5, 35, 28),
    ("coffee", "Geef Karel 3 Sticky koffies", 3, 40, 32),
    ("wash", "Was Karel 2 keer lekker schoon", 2, 32, 26),
    ("fish", "Ga 3 keer vissen vanaf de taakbalk", 3, 48, 36),
    ("craft", "Kook 2 recepten in de Tosti-Bar", 2, 55, 45),
    ("dance", "Laat Karel 3x dansen, jammen of sporten", 3, 38, 30),
    ("committee", "Voltooi 2 Sticky Commissie-missies", 2, 65, 55),
    ("trivia", "Beantwoord 2 Trivia-vragen goed", 2, 45, 38),
    ("roam_loot", "Pak 3 scherm-buiten op", 3, 45, 35),
    ("catch_pts", "Scoor 150+ in Eucalyptus Catch", 150, 55, 42),
    ("flappy_pts", "Passeer 10 poorten in Flappy Hop", 10, 62, 50),
    ("smash_pts", "Scoor 180+ in Bug Smasher", 180, 58, 45),
    ("memory_win", "Win 2 potjes Sticky Memory", 2, 60, 50),
    ("snake_pts", "Scoor 10+ in Sticky Code Snake", 10, 58, 48),
    ("merge_pts", "Haal score 1000+ in Merge 2048", 1000, 70, 60),
    ("rhythm_pts", "Scoor 260+ in Beat Drop", 260, 65, 55),
    ("rpg_win", "Versla 2 eindbazen in BBG RPG", 2, 80, 70),
    ("gans_pts", "Scoor 110+ in Uithof Ganzen Run", 110, 60, 52),
    ("koala_pts", "Scoor 120+ in Koala Server Rescue", 120, 62, 54),
    ("selfie", "Maak 2 leuke Selfies met Karel", 2, 34, 28),
    ("gacha", "Draai 2 keer aan de Grijpmachine", 2, 48, 36),
]


def xp_for_next_level(lvl):
    """Deep RPG XP threshold to reach level lvl + 1 (lvl=0 -> 0)."""
    if lvl <= 0:
        return 0
    return 180 * lvl * (lvl + 1)


def level_from_xp(xp):
    lvl = 1
    while xp >= xp_for_next_level(lvl):
        lvl += 1
    return lvl


def title_for_level(lvl):
    thresholds = [1, 2, 3, 4, 5, 7, 9, 11, 13, 16, 19, 22, 26, 32, 40, 50, 60, 75, 90, 100]
    idx = 0
    for i, th in enumerate(thresholds):
        if lvl >= th:
            idx = i
    return TITLES[idx]


def generate_daily_quests(date_str):
    """Deterministically pick 4 daily quests for date_str with coin, XP & ingredient reward."""
    rng = random.Random("KAREL_STICKY_" + date_str)
    picks = rng.sample(QUEST_POOL, 4)
    ing_keys = list(INGREDIENTS.keys())
    return [
        {
            "id": qid, "label": lbl, "target": tgt, "cur": 0,
            "coins": c, "xp": xp, "ing": rng.choice(ing_keys), "claimed": False,
        }
        for qid, lbl, tgt, c, xp in picks
    ]


def daily_campus_event(date_str):
    """Pick the daily Sticky campus buff/event."""
    rng = random.Random("UITHOF_" + date_str)
    return rng.choice(CAMPUS_EVENTS)


def seasonal_campus_event(date_str=None):
    """Return active seasonal / academic calendar event (title, buff_desc, tag)."""
    try:
        dt = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    except Exception:
        dt = datetime.date.today()
    m, d = dt.month, dt.day
    md = m * 100 + d
    if 824 <= md <= 908:
        return ("Introductie & EJW!", "+25% XP bij sjaars-commissies & knuffels.", "intro_xp")
    if 1026 <= md <= 1110 or 118 <= md <= 130 or 406 <= md <= 414 or 615 <= md <= 628:
        return ("Tentamen-Grind op Science Park", "+25% XP bij Focus Studiemodus, EduCo & CommITCrowd!", "study_xp")
    if 1201 <= md <= 1205:
        return ("Sinterklaas in de Stickykamer (BBG)", "+25% XP in Tosti-Bar & KoCo keuken!", "cook_xp")
    if md >= 1216 or md <= 117:
        return ("Winter & Wispo-Seizoen!", "+25% bonusmunten & snelle koffie-boost!", "roam_coins")
    if 212 <= md <= 216:
        return ("Valentijns-Knuffeldagen", "+25% XP & blijheid bij aaien en maatjes!", "pet_xp")
    if 415 <= md <= 428:
        return ("Sticky Dies Natalis Week!", "+30% munten bij commissies & feesten!", "committee_coins")
    if 501 <= md <= 520:
        return ("Lente & Batavierenrace", "+25% bonusmunten in Arcade & SportCo!", "game_coins")
    if 701 <= md <= 823:
        return ("Zomer & NOVA-Voorbereiding", "Hogere kans op zeldzame StickyDex-schatten!", "fish_rarity")
    return ("Academisch Kwartaal in Utrecht", "+20% warmte & extra focus in de Stickykamer!", "coffee_xp")
