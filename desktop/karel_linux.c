/* Karel de Koala - Linux Companion UI, Physics & Entry Point (C99 + libX11 + XShape)
 * Modular Linux implementation:
 *   - desktop/karel_linux.h      : shared structs, safety caps, X11 stubs, module APIs
 *   - desktop/linux/codec.c      : bounded gzip/DEFLATE, SHA-256, SemVer validator
 *   - desktop/linux/sprites.c    : sprite loader, coat mapping & outfit renderer
 *   - desktop/linux/storage.c    : save.json persistence, USB locator, WAV synth
 *   - desktop/linux/system_io.c  : audio exec, USB CDC serial, version check & IPC
 * Build: bash desktop/build_linux.sh
 */

#include "karel_linux.h"

#ifndef KAREL_CORE_TEST

/* =========================================================================
 * 1. X11 Geometry, Color Cache & Window Ledge Detection
 * ========================================================================= */

static int Sc(int px, float s) {
    int v = (int)llround(px * s);
    return v < 1 ? 1 : v;
}

static float get_dpi_scale(Display *dpy) {
    char *v = XGetDefault(dpy, "Xft", "dpi");
    if (v) {
        double d = atof(v) / 96.0;
        if (d > 0.9 && d < 3.0) return (float)d;
    }
    int h = XDisplayHeight(dpy, XDefaultScreen(dpy));
    if (h >= 1800) return 1.75f;
    if (h >= 1350) return 1.35f;
    return 1.0f;
}

static unsigned long rgb_px(Display *dpy, int scr, uint8_t r, uint8_t g, uint8_t b) {
    static struct { uint32_t key; unsigned long px; int valid; } cache[80];
    static int cache_n = 0;
    uint32_t k = ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
    for (int i = 0; i < cache_n; i++) {
        if (cache[i].valid && cache[i].key == k) return cache[i].px;
    }
    XColor c;
    c.red = (unsigned short)r * 257;
    c.green = (unsigned short)g * 257;
    c.blue = (unsigned short)b * 257;
    c.flags = DoRed | DoGreen | DoBlue;
    XAllocColor(dpy, XDefaultColormap(dpy, scr), &c);
    if (cache_n < 80) {
        cache[cache_n].key = k;
        cache[cache_n].px = c.pixel;
        cache[cache_n].valid = 1;
        cache_n++;
    }
    return c.pixel;
}

static void get_work_area(Display *dpy, int scr, int *x, int *y, int *w, int *h) {
    *x = 0;
    *y = 0;
    *w = XDisplayWidth(dpy, scr);
    *h = XDisplayHeight(dpy, scr);
    Atom a = XInternAtom(dpy, "_NET_WORKAREA", True), rt;
    int fmt;
    unsigned long n, rem;
    unsigned char *data = NULL;
    if (a != None &&
        XGetWindowProperty(dpy, XRootWindow(dpy, scr), a, 0, 4, False, XA_CARDINAL,
                           &rt, &fmt, &n, &rem, &data) == Success && data) {
        if (n >= 4) {
            long *v = (long *)data;
            *x = (int)v[0]; *y = (int)v[1]; *w = (int)v[2]; *h = (int)v[3];
        }
        XFree(data);
    }
}

static int query_active_win(KarelApp *k, int *rx, int *ry, int *rw, int *rh, char *title, size_t max_t) {
    title[0] = 0;
    Atom a = XInternAtom(k->dpy, "_NET_ACTIVE_WINDOW", True), rt;
    int fmt;
    unsigned long n, rem;
    unsigned char *data = NULL;
    if (a == None ||
        XGetWindowProperty(k->dpy, k->root, a, 0, 1, False, XA_WINDOW,
                           &rt, &fmt, &n, &rem, &data) != Success || !data) {
        return 0;
    }
    Window aw = (n >= 1) ? *(Window *)data : 0;
    XFree(data);
    if (!aw || aw == k->karel_win || aw == k->hub_win || aw == k->pop_win) return 0;

    Window r, ch = 0;
    int gx = 0, gy = 0, tx = 0, ty = 0;
    unsigned gw = 0, gh = 0, bw = 0, dep = 0;
    if (!XGetGeometry(k->dpy, aw, &r, &gx, &gy, &gw, &gh, &bw, &dep)) return 0;
    if (!XTranslateCoordinates(k->dpy, aw, k->root, 0, 0, &tx, &ty, &ch)) return 0;

    Atom fe = XInternAtom(k->dpy, "_NET_FRAME_EXTENTS", True);
    data = NULL;
    if (fe != None &&
        XGetWindowProperty(k->dpy, aw, fe, 0, 4, False, XA_CARDINAL,
                           &rt, &fmt, &n, &rem, &data) == Success && data) {
        if (n >= 4) {
            long *v = (long *)data;
            tx -= (int)v[0];
            ty -= (int)v[2];
            gw += (unsigned)(v[0] + v[1]);
            gh += (unsigned)(v[2] + v[3]);
        }
        XFree(data);
    }
    *rx = tx; *ry = ty; *rw = (int)gw; *rh = (int)gh;

    Atom nm = XInternAtom(k->dpy, "_NET_WM_NAME", True);
    if (nm == None) nm = XInternAtom(k->dpy, "WM_NAME", True);
    data = NULL;
    if (nm != None &&
        XGetWindowProperty(k->dpy, aw, nm, 0, 64, False, AnyPropertyType,
                           &rt, &fmt, &n, &rem, &data) == Success && data) {
        size_t cp = n < max_t - 1 ? n : max_t - 1;
        memcpy(title, data, cp);
        title[cp] = 0;
        XFree(data);
    }
    for (size_t i = 0; title[i]; i++) {
        title[i] = (char)tolower((unsigned char)title[i]);
    }
    return 1;
}

static int detect_auto_quiet(KarelApp *k) {
    int x, y, w, h;
    char ttl[160];
    if (!query_active_win(k, &x, &y, &w, &h, ttl, sizeof(ttl))) return 0;

    static const char *mks[] = {
        "zoom meeting", "microsoft teams", "google meet", "meet - ",
        "webex", "powerpoint", "libreoffice impress", NULL
    };
    for (int i = 0; mks[i]; i++) {
        if (strstr(ttl, mks[i])) return 1;
    }
    int sw = XDisplayWidth(k->dpy, k->scr);
    int sh = XDisplayHeight(k->dpy, k->scr);
    return (x <= 2 && y <= 2 && w >= sw - 2 && h >= sh - 2) ? 1 : 0;
}

static int is_en(const KarelApp *k) { return strcmp(k->save.language, "en") == 0; }
static int px_sz(const KarelApp *k) { return 32 * k->scale; }
static int win_w(const KarelApp *k) { int p = px_sz(k) + Sc(142, k->dpi); int mn = Sc(260, k->dpi); return p < mn ? mn : p; }
static int win_h(const KarelApp *k) { return px_sz(k) + Sc(84, k->dpi); }
static int k_ox(const KarelApp *k) { return (win_w(k) - px_sz(k)) / 2; }
static int k_oy(const KarelApp *k) { return win_h(k) - px_sz(k) - 12; }

static void say_msg(KarelApp *k, const char *m, int ticks) {
    if (!k->auto_paused) {
        snprintf(k->bubble, sizeof(k->bubble), "%.155s", m);
        k->bubble_ticks = ticks;
    }
}

static void set_act(KarelApp *k, const char *st, int ticks) {
    if (!k->climbing) {
        snprintf(k->state, sizeof(k->state), "%.31s", st);
        k->act_ticks = ticks;
    }
}

static void spawn_particles(KarelApp *k, const char *ch, uint8_t r, uint8_t g, uint8_t b, int count) {
    for (int i = 0; i < count && k->nparts < 24; i++) {
        Particle *pt = &k->parts[k->nparts++];
        pt->x = win_w(k) * 0.5 + (rand() % 48) - 24;
        pt->y = k_oy(k) + (rand() % 20) + 4;
        pt->vx = ((rand() % 100) / 100.0 - 0.5) * 4.5;
        pt->vy = -1.8 - ((rand() % 100) / 100.0) * 3.0;
        pt->life = 12 + (rand() % 10);
        pt->ch[0] = ch[0]; pt->ch[1] = 0;
        pt->r = r; pt->g = g; pt->b = b;
    }
}

static void draw_hub(KarelApp *k);
static void open_hub(KarelApp *k);

/* =========================================================================
 * 2. Quotes, Level Titles & Koala Actions (Backed by desktop/locale.json)
 * ========================================================================= */

static const LocaleSet *active_locale(const KarelApp *k) {
    return is_en(k) ? &k->loc.en : &k->loc.nl;
}

static const char *pick_arr(const void *base, int count, size_t stride, const char *fb) {
    if (count <= 0) return fb;
    return (const char *)base + (size_t)(rand() % count) * stride;
}

static const char *level_title(const KarelApp *k, int lvl) {
    const LocaleSet *ls = active_locale(k);
    if (ls->n_levels <= 0) return "Sticky Koala";
    int idx = clamp_int(lvl - 1, 0, ls->n_levels - 1);
    return ls->level_titles[idx];
}

static const char *outfit_quote(const KarelApp *k, const char *item) {
    if (!item || !*item) return "";
    const LocaleSet *ls = active_locale(k);
    for (int i = 0; i < ls->n_outfits; i++) {
        if (strcmp(item, ls->outfit_keys[i]) == 0) return ls->outfit_vals[i];
    }
    return "";
}

static const char *pick_smart_quote(const KarelApp *k) {
    const LocaleSet *ls = active_locale(k);
    if (*k->save.equipped && (rand() % 4) == 0) {
        const char *oq = outfit_quote(k, k->save.equipped);
        if (*oq) return oq;
    }
    time_t now = time(NULL);
    struct tm *lt = localtime(&now);
    if (lt && lt->tm_hour == 21 && lt->tm_min == 21) {
        return is_en(k) ? "21:21 on the clock... Vo' B21!!" : "21:21 op de klok... Vo' B21!!";
    }
    if (lt && lt->tm_hour >= 0 && lt->tm_hour < 5 && ls->n_night > 0) {
        return pick_arr(ls->night, ls->n_night, sizeof(ls->night[0]), "Zzz...");
    }
    if (lt && lt->tm_wday == 5 && lt->tm_hour >= 16 && (rand() % 10) < 4 && ls->n_friday > 0) {
        return pick_arr(ls->friday, ls->n_friday, sizeof(ls->friday[0]), "VrijMiBo!");
    }
    if (lt && lt->tm_hour >= 6 && lt->tm_hour < 11 && (rand() % 10) < 4 && ls->n_morning > 0) {
        return pick_arr(ls->morning, ls->n_morning, sizeof(ls->morning[0]), "Goedemorgen!");
    }
    return pick_arr(ls->quotes, ls->n_quotes, sizeof(ls->quotes[0]), "Sticky RP2350!");
}

static void play_trick_sound(const KarelApp *k, const char *st) {
    if (strcmp(st, "MAGIC_TRICK") == 0) play_sound_key("magic", k->muted, k->auto_paused);
    else if (strcmp(st, "KARATE") == 0 || strcmp(st, "NINJA") == 0) play_sound_key("karate", k->muted, k->auto_paused);
    else if (strcmp(st, "DJ") == 0 || strcmp(st, "DANCE") == 0 || strcmp(st, "GUITAR") == 0 || strcmp(st, "DRUM") == 0) play_sound_key("dj", k->muted, k->auto_paused);
    else if (strcmp(st, "BALLOON") == 0 || strcmp(st, "JETPACK") == 0 || strcmp(st, "SKATEBOARD") == 0) play_sound_key("toss", k->muted, k->auto_paused);
    else play_sound_key("trick", k->muted, k->auto_paused);
}

static void do_random_style(KarelApp *k) {
    const char *sk = SKIN_IDS[rand() % NUM_SKINS];
    const char *ot = OUTFIT_IDS[rand() % (NUM_OUTFITS - 1)];
    snprintf(k->save.skin, sizeof(k->save.skin), "%s", sk);
    snprintf(k->save.equipped, sizeof(k->save.equipped), "%s", ot);
    save_persist(&k->save);
    play_sound_key("shuffle", k->muted, k->auto_paused);
    spawn_particles(k, "*", 245, 196, 81, 8);
    set_act(k, "SPIN", 20);
    const char *oq = outfit_quote(k, ot);
    say_msg(k, *oq ? oq : ot, 55);
}

static void award_xp(KarelApp *k, int amt) {
    int old_l = level_from_xp(k->save.xp);
    k->save.xp += amt;
    k->save.level = level_from_xp(k->save.xp);
    if (k->save.level > old_l) {
        play_sound_key("levelup", k->muted, k->auto_paused);
        set_act(k, (rand() & 1) ? "BACKFLIP" : "PARTY_HORN", 42);
        spawn_particles(k, "*", 245, 196, 81, 14);
        char m[96];
        snprintf(m, sizeof(m), "LEVEL UP! Lv.%d - %s!", k->save.level, level_title(k, k->save.level));
        say_msg(k, m, 80);
    }
}

static void trigger_climb(KarelApp *k, const char *msg) {
    int wx, wy, ww, wh;
    get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);
    k->flying = 0; k->umbrella_fall = 0; k->jump_y = 0;
    k->wy = wy + wh - (k_oy(k) + px_sz(k));
    k->climbing = 1; k->climb_step = 0;
    snprintf(k->climb_msg, sizeof(k->climb_msg), "%.120s", msg);
    k->roam_tx = k->wx; k->roam_ty = k->wy; k->roam_wait = 95;
    play_sound_key("climb", k->muted, k->auto_paused);
    say_msg(k, is_en(k) ? "Climbing up..." : "Even omhoog klimmen...", 26);
}

static void do_pet(KarelApp *k) {
    const LocaleSet *ls = active_locale(k);
    k->save.happiness = clamp_int(k->save.happiness + 18, 0, 100);
    k->save.total_pets++;
    if (k->save.total_pets % 21 == 0) {
        set_act(k, "PARTY_HORN", 42);
        award_xp(k, 21);
        spawn_particles(k, "*", 245, 196, 81, 21);
        play_sound_key("levelup", k->muted, k->auto_paused);
        ser_send(&k->ser, "STATE:B21");
        say_msg(k, is_en(k) ? "Vo' B21!! 21x pet bonus! +21 XP!" : "Vo' B21!! 21x geaaid bonus! +21 XP!", 65);
    } else {
        set_act(k, k->save.happiness >= 95 ? "LOVE" : "PET", 28);
        award_xp(k, 8);
        spawn_particles(k, "*", 255, 122, 144, 6);
        play_sound_key("pet", k->muted, k->auto_paused);
        ser_send(&k->ser, "EVENT:HEART");
        say_msg(k, pick_arr(ls->pet, ls->n_pet, sizeof(ls->pet[0]), "+8 XP!"), 45);
    }
    save_persist(&k->save);
    draw_hub(k);
}

static void do_feed(KarelApp *k) {
    const LocaleSet *ls = active_locale(k);
    k->save.hunger = clamp_int(k->save.hunger + 35, 0, 100);
    k->save.happiness = clamp_int(k->save.happiness + 10, 0, 100);
    set_act(k, "EAT", 28);
    award_xp(k, 7);
    spawn_particles(k, "+", 62, 207, 142, 5);
    play_sound_key("eat", k->muted, k->auto_paused);
    say_msg(k, pick_arr(ls->feed, ls->n_feed, sizeof(ls->feed[0]), "Nom nom!"), 45);
    save_persist(&k->save);
    draw_hub(k);
}

static void do_coffee(KarelApp *k) {
    const LocaleSet *ls = active_locale(k);
    k->save.energy = clamp_int(k->save.energy + 35, 0, 100);
    k->save.caffeine = clamp_int(k->save.caffeine + 25, 0, 100);
    set_act(k, "COFFEE", 28);
    award_xp(k, 9);
    spawn_particles(k, "~", 245, 196, 81, 6);
    play_sound_key("coffee", k->muted, k->auto_paused);

    time_t now = time(NULL);
    int keep = 0;
    for (int i = 0; i < k->coffee_n; i++) {
        if (difftime(now, k->coffee_t[i]) <= 120) k->coffee_t[keep++] = k->coffee_t[i];
    }
    if (keep < 3) {
        k->coffee_t[keep++] = now;
    } else {
        k->coffee_t[0] = k->coffee_t[1];
        k->coffee_t[1] = k->coffee_t[2];
        k->coffee_t[2] = now;
    }
    k->coffee_n = keep;

    if (k->coffee_n >= 3) {
        k->hyper_ticks = 95;
        ser_send(&k->ser, "STATE:HYPER");
        say_msg(k, is_en(k) ? "CAFFEINE OVERDOSE! 200 MHz!" : "CAFEINE OVERDOSIS! 200 MHz MODE!", 75);
    } else {
        say_msg(k, pick_arr(ls->coffee, ls->n_coffee, sizeof(ls->coffee[0]), "+9 XP!"), 45);
    }
    save_persist(&k->save);
    draw_hub(k);
}

static void do_wash(KarelApp *k) {
    const LocaleSet *ls = active_locale(k);
    k->save.hygiene = clamp_int(k->save.hygiene + 45, 0, 100);
    k->save.happiness = clamp_int(k->save.happiness + 12, 0, 100);
    set_act(k, "WASH", 30);
    award_xp(k, 8);
    spawn_particles(k, "o", 79, 195, 247, 7);
    play_sound_key("pet", k->muted, k->auto_paused);
    say_msg(k, pick_arr(ls->wash, ls->n_wash, sizeof(ls->wash[0]), "Clean!"), 45);
    save_persist(&k->save);
    draw_hub(k);
}

static void nap_toggle(KarelApp *k) {
    if (strcmp(k->state, "SLEEP") == 0) {
        strcpy(k->state, "STRETCH");
        k->act_ticks = 18;
        say_msg(k, is_en(k) ? "Good morning! Refreshed!" : "Goedemorgen! Uitgerust!", 40);
    } else {
        strcpy(k->state, "SLEEP");
        k->act_ticks = 220;
        play_sound_key("dive", k->muted, k->auto_paused);
        say_msg(k, "Zzz... Sticky powernap!", 45);
    }
}

static void trigger_konami(KarelApp *k) {
    k->disco_ticks = 115;
    strcpy(k->save.equipped, "shades");
    set_act(k, "DANCE", 65);
    spawn_particles(k, "*", 245, 196, 81, 16);
    ser_send(&k->ser, "STATE:PARTY");
    play_sound_key("levelup", k->muted, k->auto_paused);
    say_msg(k, is_en(k) ? "DISCO BORREL MODE ON!" : "DISCO BORREL MODE AAN!", 80);
    save_persist(&k->save);
    draw_hub(k);
}

static void trigger_b21(KarelApp *k) {
    k->disco_ticks = 121;
    strcpy(k->save.equipped, "crown");
    set_act(k, "PARTY_HORN", 65);
    award_xp(k, 21);
    spawn_particles(k, "*", 245, 196, 81, 21);
    ser_send(&k->ser, "STATE:B21");
    play_sound_key("levelup", k->muted, k->auto_paused);
    say_msg(k, is_en(k) ? "Vo' B21!! Board 21 represent! +21 XP!" : "Vo' B21!! Bestuur 21 represent! +21 XP!", 85);
    save_persist(&k->save);
    draw_hub(k);
}

static void do_boop(KarelApp *k) {
    award_xp(k, 10);
    play_sound_key("boop", k->muted, k->auto_paused);
    spawn_particles(k, "*", 245, 196, 81, 10);
    trigger_climb(k, "SuperMini Boop! +10 XP!");
    save_persist(&k->save);
    draw_hub(k);
}

static void trigger_dive(KarelApp *k, const char *mode) {
    if (k->closing) return;
    snprintf(k->dive_mode, sizeof(k->dive_mode), "%.15s", mode);
    k->closing = 1; k->close_step = 0; k->climbing = 0; k->flying = 0;
    k->dragging = 0; k->umbrella_fall = 0;
    k->jump_y = 0; k->close_sy = k->wy; k->act_ticks = 0;
    say_msg(k, strcmp(mode, "tray") == 0
        ? (is_en(k) ? "Napping! --toggle to wake" : "Dutje! --toggle wekt Karel")
        : (is_en(k) ? "See ya! Diving back!" : "Tot ziens! Ik duik weg!"), 40);
    spawn_particles(k, "*", 255, 122, 144, 4);
    play_sound_key("dive", k->muted, k->auto_paused);
}

/* =========================================================================
 * 3. X11 Shaped Koala Rendering & Speech Bubble
 * ========================================================================= */

static void resolve_render_state(KarelApp *k, char rst[32], int *clip_out) {
    snprintf(rst, 32, "%.31s", k->state);
    int clip = 32;
    if (k->closing) {
        if (k->close_step <= 9) strcpy(rst, "DIVE_WAVE");
        else if (k->close_step <= 13) strcpy(rst, "JUMP");
        else {
            strcpy(rst, "DIVE_DOWN");
            clip = (int)llround(32.0 * (1.0 - (k->close_step - 13) / 13.0));
            if (clip < 0) clip = 0;
        }
    } else if (k->climbing) {
        strcpy(rst, "CLIMB");
        clip = (int)llround(32.0 * (k->climb_step < 17 ? k->climb_step / 17.0 : 1.0));
        if (clip < 2) clip = 2;
    } else if (strcmp(rst, "IDLE") == 0) {
        time_t now = time(NULL);
        struct tm *lt = localtime(&now);
        if (k->hyper_ticks > 0) strcpy(rst, "HYPER");
        else if (lt && lt->tm_hour >= 23 && k->act_ticks == 0) strcpy(rst, "SLEEP");
        else if (k->save.hunger < 25) strcpy(rst, "HUNGRY");
    }
    *clip_out = clip;
}

static void draw_speech_bubble(KarelApp *k, Pixmap mask, XFontStruct *f, int W, int oy) {
    int tw = f ? XTextWidth(f, k->bubble, (int)strlen(k->bubble)) : (int)strlen(k->bubble) * 7;
    int bw = tw + 20;
    if (bw < 76) bw = 76;
    if (bw > W - 10) bw = W - 10;
    int bh = 26, bx = (W - bw) / 2, by = oy - bh - 12;
    if (by < 4) by = 4;
    int tx = W / 2;

    XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 248, 250, 255));
    XFillRectangle(k->dpy, k->karel_win, k->karel_gc, bx, by, (unsigned)bw, (unsigned)bh);
    XFillRectangle(k->dpy, mask, k->mask_gc, bx, by, (unsigned)bw, (unsigned)bh);

    XPoint tri[3] = {
        {(short)(tx - 5), (short)(by + bh)},
        {(short)(tx + 5), (short)(by + bh)},
        {(short)tx, (short)(by + bh + 6)}
    };
    XFillPolygon(k->dpy, k->karel_win, k->karel_gc, tri, 3, Convex, CoordModeOrigin);
    XFillPolygon(k->dpy, mask, k->mask_gc, tri, 3, Convex, CoordModeOrigin);

    XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 196, 30, 37));
    XFillRectangle(k->dpy, k->karel_win, k->karel_gc, bx, by, 4, (unsigned)bh);
    XDrawRectangle(k->dpy, k->karel_win, k->karel_gc, bx, by, (unsigned)bw - 1, (unsigned)bh - 1);

    XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 20, 24, 34));
    XDrawString(k->dpy, k->karel_win, k->karel_gc, bx + 10, by + 17, k->bubble, (int)strlen(k->bubble));
}

static void paint_karel(KarelApp *k) {
    int W = win_w(k), H = win_h(k), ox = k_ox(k), oy = k_oy(k), p = px_sz(k);
    char rst[32];
    int clip = 32;
    resolve_render_state(k, rst, &clip);

    Rgba frame[32][32];
    render_frame_rgba(&k->sb, rst, k->frame_idx, k->save.skin, k->save.equipped, frame);

    /* Build a 1-bit XShape transparency mask matching painted pixels + bubble. */
    Pixmap mask = XCreatePixmap(k->dpy, k->karel_win, (unsigned)W, (unsigned)H, 1);
    if (!k->mask_gc) k->mask_gc = XCreateGC(k->dpy, mask, 0, NULL);
    XSetForeground(k->dpy, k->mask_gc, 0);
    XFillRectangle(k->dpy, mask, k->mask_gc, 0, 0, (unsigned)W, (unsigned)H);
    XSetForeground(k->dpy, k->mask_gc, 1);

    XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 1, 2, 3));
    XFillRectangle(k->dpy, k->karel_win, k->karel_gc, 0, 0, (unsigned)W, (unsigned)H);

    if (!k->climbing && !k->closing) {
        int ins = p / 5 < 8 ? 8 : p / 5;
        int sw = (p - 2 * ins) < 12 ? 12 : (p - 2 * ins);
        XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 24, 28, 38));
        XFillArc(k->dpy, k->karel_win, k->karel_gc, ox + ins, oy + p - 4, (unsigned)sw, 7, 0, 360 * 64);
        XFillArc(k->dpy, mask, k->mask_gc, ox + ins, oy + p - 4, (unsigned)sw, 7, 0, 360 * 64);
    }

    for (int y = 0; y < clip; y++) {
        for (int x = 0; x < 32; x++) {
            Rgba c = frame[y][x];
            if (!c.a) continue;
            int dx = ox + x * k->scale, dy = oy + (32 - clip + y) * k->scale;
            XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, c.r, c.g, c.b));
            XFillRectangle(k->dpy, k->karel_win, k->karel_gc, dx, dy, (unsigned)k->scale, (unsigned)k->scale);
            XFillRectangle(k->dpy, mask, k->mask_gc, dx, dy, (unsigned)k->scale, (unsigned)k->scale);
        }
    }

    XFontStruct *f = k->bfont ? k->bfont : k->font;
    if (f) XSetFont(k->dpy, k->karel_gc, f->fid);
    for (int i = 0; i < k->nparts; i++) {
        int px = (int)llround(k->parts[i].x), py = (int)llround(k->parts[i].y);
        XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, k->parts[i].r, k->parts[i].g, k->parts[i].b));
        XDrawString(k->dpy, k->karel_win, k->karel_gc, px, py, k->parts[i].ch, 1);
        XFillRectangle(k->dpy, mask, k->mask_gc, px - 1, py - 11, 10, 14);
    }

    if (k->bubble_ticks > 0 && k->bubble[0]) {
        draw_speech_bubble(k, mask, f, W, oy);
    }

    XShapeCombineMask(k->dpy, k->karel_win, ShapeBounding, 0, 0, mask, ShapeSet);
    XFreePixmap(k->dpy, mask);
}

/* =========================================================================
 * 4. Context Menu, Dark-Mode Sticky Hub & Auto-Start Ask Prompt
 * ========================================================================= */

static int pop_rh(const KarelApp *k) { return k->npop > 20 ? 20 : 26; }

static void close_popup(KarelApp *k) {
    if (k->pop_win) {
        XDestroyWindow(k->dpy, k->pop_win);
        k->pop_win = 0;
        k->pop_mode = POP_NONE;
    }
}

static void draw_popup(KarelApp *k) {
    if (!k->pop_win) return;
    int rh = pop_rh(k);
    XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 27, 31, 42));
    XFillRectangle(k->dpy, k->pop_win, k->pop_gc, 0, 0, (unsigned)k->pop_w, (unsigned)k->pop_h);
    XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 196, 30, 37));
    XDrawRectangle(k->dpy, k->pop_win, k->pop_gc, 0, 0, (unsigned)k->pop_w - 1, (unsigned)k->pop_h - 1);

    if (k->font) XSetFont(k->dpy, k->pop_gc, k->font->fid);
    for (int i = 0; i < k->npop; i++) {
        int y = 4 + i * rh;
        if (strcmp(k->pop_items[i].lbl, "---") == 0) {
            XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 62, 70, 90));
            XFillRectangle(k->dpy, k->pop_win, k->pop_gc, 8, y + rh / 2, (unsigned)(k->pop_w - 16), 1);
            continue;
        }
        if (i == k->pop_hover) {
            XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 168, 32, 42));
            XFillRectangle(k->dpy, k->pop_win, k->pop_gc, 3, y + 1, (unsigned)(k->pop_w - 6), (unsigned)(rh - 2));
        }
        XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 242, 245, 250));
        XDrawString(k->dpy, k->pop_win, k->pop_gc, 12, y + rh - 6, k->pop_items[i].lbl, (int)strlen(k->pop_items[i].lbl));
    }
}

static void open_popup(KarelApp *k, int mode, int rx, int ry) {
    close_popup(k);
    k->npop = 0;
    k->pop_mode = mode;
    k->pop_hover = -1;
    int en = is_en(k);
    #define P_ADD(txt, kd, ix) do { \
        if (k->npop < 40) { \
            snprintf(k->pop_items[k->npop].lbl, 48, "%.47s", (txt)); \
            k->pop_items[k->npop].kind = (kd); \
            k->pop_items[k->npop].idx = (ix); \
            k->npop++; \
        } \
    } while (0)

    if (mode == POP_MAIN) {
        P_ADD("Open Sticky Hub", 1, 0);
        P_ADD("---", 0, 0);
        P_ADD(en ? "Feed Eucalyptus" : "Voer Eucalyptus", 2, 0);
        P_ADD(en ? "Sticky Coffee" : "Sticky Koffie", 2, 1);
        P_ADD(en ? "Pet Karel" : "Aai Karel", 2, 2);
        P_ADD(en ? "Wash Karel" : "Was Karel", 2, 3);
        P_ADD(en ? "Powernap ON/OFF" : "Powernap AAN/UIT", 2, 4);
        P_ADD(k->focus_active ? "Stop Focus" : (en ? "Focus Mode (25m)" : "Focus Modus (25m)"), 2, 5);
        P_ADD("---", 0, 0);
        P_ADD(en ? "Tricks (28)  >" : "Trucjes (28)  >", 3, POP_TRICKS);
        P_ADD(en ? "Roam Mode  >" : "Loopgedrag  >", 3, POP_ROAM);
        P_ADD(en ? "Size  >" : "Grootte  >", 3, POP_SCALE);
        P_ADD(en ? "Sound On/Off" : "Geluid Aan/Uit", 4, 0);
        P_ADD(en ? "Auto-Quiet Fullscreen" : "Auto-Stil Fullscreen", 4, 1);
        P_ADD(en ? "Language: NL / EN" : "Taal: NL / EN", 4, 2);
        P_ADD("---", 0, 0);
        P_ADD(en ? "Hide (Ctrl/Cmd --toggle)" : "Verberg (--toggle)", 4, 3);
        P_ADD(en ? "Dive & Quit" : "Duik & Sluit", 4, 4);
    } else if (mode == POP_TRICKS) {
        for (int i = 0; i < k->loc.n_tricks; i++) P_ADD(k->loc.tricks[i].lbl, 5, i);
    } else if (mode == POP_ROAM) {
        P_ADD(en ? "Free Roam" : "Heel Scherm", 6, 0);
        P_ADD(en ? "Active Window" : "Op Actief Venster", 6, 1);
        P_ADD(en ? "Follow Mouse" : "Volg Muis", 6, 2);
        P_ADD(en ? "Stay Put" : "Blijf Zitten", 6, 3);
    } else if (mode == POP_SCALE) {
        for (int s = 2; s <= 5; s++) {
            char b[32];
            snprintf(b, sizeof(b), "%dx (%dpx)", s, s * 32);
            P_ADD(b, 7, s);
        }
    } else if (mode == POP_SKIN) {
        for (int i = 0; i < NUM_SKINS; i++) {
            char b[48];
            snprintf(b, sizeof(b), "%s%s", strcmp(k->save.skin, SKIN_IDS[i]) == 0 ? "* " : "  ", SKIN_IDS[i]);
            P_ADD(b, 8, i);
        }
    } else if (mode == POP_OUTFIT) {
        for (int i = 0; i < NUM_OUTFITS; i++) {
            const char *nm = *OUTFIT_IDS[i] ? OUTFIT_IDS[i] : (en ? "(none)" : "(geen)");
            char b[48];
            snprintf(b, sizeof(b), "%s%s", strcmp(k->save.equipped, OUTFIT_IDS[i]) == 0 ? "* " : "  ", nm);
            P_ADD(b, 9, i);
        }
    }
    #undef P_ADD

    k->pop_w = 220;
    k->pop_h = 8 + k->npop * pop_rh(k);
    int sw = XDisplayWidth(k->dpy, k->scr), sh = XDisplayHeight(k->dpy, k->scr);
    if (rx + k->pop_w > sw - 8) rx = sw - k->pop_w - 8;
    if (ry + k->pop_h > sh - 8) ry = sh - k->pop_h - 8;
    if (rx < 4) rx = 4;
    if (ry < 4) ry = 4;

    XSetWindowAttributes swa;
    swa.override_redirect = True;
    swa.background_pixel = rgb_px(k->dpy, k->scr, 27, 31, 42);
    k->pop_win = XCreateWindow(k->dpy, k->root, rx, ry, (unsigned)k->pop_w, (unsigned)k->pop_h,
                               0, CopyFromParent, InputOutput, CopyFromParent,
                               CWOverrideRedirect | CWBackPixel, &swa);
    XSelectInput(k->dpy, k->pop_win, ExposureMask | ButtonPressMask | PointerMotionMask);
    k->pop_gc = XCreateGC(k->dpy, k->pop_win, 0, NULL);
    XMapRaised(k->dpy, k->pop_win);
    draw_popup(k);
}

static void resize_karel_scale(KarelApp *k, int sc) {
    k->scale = clamp_int(sc, 2, 5);
    k->save.karel_scale = k->scale;
    XResizeWindow(k->dpy, k->karel_win, (unsigned)win_w(k), (unsigned)win_h(k));
    int wx, wy, ww, wh;
    get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);
    int gy = wy + wh - (k_oy(k) + px_sz(k));
    if (k->wy > gy) k->wy = gy;
    save_persist(&k->save);
}

static void click_popup(KarelApp *k, int my, int x_root, int y_root) {
    int i = (my - 4) / pop_rh(k);
    if (i < 0 || i >= k->npop) { close_popup(k); return; }
    int kd = k->pop_items[i].kind, ix = k->pop_items[i].idx;
    if (kd == 0) return;
    if (kd == 3) { open_popup(k, ix, x_root + 12, y_root - 20); return; }
    close_popup(k);

    if (kd == 1) {
        open_hub(k);
    } else if (kd == 2) {
        if (ix == 0) do_feed(k);
        else if (ix == 1) do_coffee(k);
        else if (ix == 2) do_pet(k);
        else if (ix == 3) do_wash(k);
        else if (ix == 4) nap_toggle(k);
        else if (ix == 5) {
            k->focus_active = !k->focus_active;
            if (k->focus_active) {
                k->focus_rem = 25 * 60;
                k->focus_last = time(NULL);
                say_msg(k, "Focus: 25m!", 45);
            } else {
                say_msg(k, is_en(k) ? "Focus stopped." : "Focus gestopt.", 35);
            }
            draw_hub(k);
        }
    } else if (kd == 4) {
        if (ix == 0) { k->muted = !k->muted; draw_hub(k); }
        else if (ix == 1) { k->save.auto_quiet = !k->save.auto_quiet; save_persist(&k->save); draw_hub(k); }
        else if (ix == 2) { strcpy(k->save.language, is_en(k) ? "nl" : "en"); save_persist(&k->save); draw_hub(k); }
        else if (ix == 3) trigger_dive(k, "tray");
        else if (ix == 4) trigger_dive(k, "quit");
    } else if (kd == 5 && ix >= 0 && ix < k->loc.n_tricks) {
        set_act(k, k->loc.tricks[ix].st, 42);
        say_msg(k, k->loc.tricks[ix].msg, 48);
        play_trick_sound(k, k->loc.tricks[ix].st);
    } else if (kd == 6) {
        static const char *modes[] = {"free", "window", "cursor", "park"};
        snprintf(k->save.roam_mode, sizeof(k->save.roam_mode), "%s", modes[ix]);
        k->umbrella_fall = 0;
        save_persist(&k->save);
        say_msg(k, modes[ix], 30);
    } else if (kd == 7) {
        resize_karel_scale(k, ix);
    } else if (kd == 8) {
        snprintf(k->save.skin, sizeof(k->save.skin), "%s", SKIN_IDS[ix]);
        save_persist(&k->save);
        draw_hub(k);
    } else if (kd == 9) {
        snprintf(k->save.equipped, sizeof(k->save.equipped), "%s", OUTFIT_IDS[ix]);
        save_persist(&k->save);
        draw_hub(k);
    }
}

static void add_hub_btn(KarelApp *k, int x, int y, int w, int h, int id) {
    if (k->nhub_btns < 18) {
        k->hub_btns[k->nhub_btns++] = (HubBtn){x, y, w, h, id};
    }
}

static int draw_hub_stats_card(KarelApp *k, float s, int P, int Win, int curY, int en) {
    int cardH = Sc(88, s);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 27, 31, 42));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, P, curY, (unsigned)Win, (unsigned)cardH);

    int lvl = level_from_xp(k->save.xp);
    int p_xp = xp_for_next_level(lvl - 1), n_xp = xp_for_next_level(lvl);
    double pct = (double)(k->save.xp - p_xp) / (double)(n_xp - p_xp > 0 ? n_xp - p_xp : 1);
    if (pct < 0) pct = 0;
    if (pct > 1) pct = 1;

    char l1[128], l2[140];
    snprintf(l1, sizeof(l1), "Lv.%d  %s  -  %d / %d XP", lvl, level_title(k, lvl), k->save.xp, n_xp);
    snprintf(l2, sizeof(l2), "%s: %d%%  |  %s: %d%%  |  %s: %d%%  |  %s: %d%%",
             en ? "Hungry" : "Honger", k->save.hunger, en ? "Happy" : "Blij", k->save.happiness,
             en ? "Energy" : "Energie", k->save.energy, en ? "Clean" : "Fris", k->save.hygiene);

    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 242, 245, 250));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, P + Sc(14, s), curY + Sc(24, s), l1, (int)strlen(l1));

    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 15, 18, 24));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, P + Sc(14, s), curY + Sc(38, s), (unsigned)(Win - Sc(28, s)), (unsigned)Sc(8, s));

    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 245, 196, 81));
    int fw = (int)llround((Win - Sc(28, s)) * pct);
    if (k->save.xp > 0 && fw < 4) fw = 4;
    if (fw > 0) XFillRectangle(k->dpy, k->hub_win, k->hub_gc, P + Sc(14, s), curY + Sc(38, s), (unsigned)fw, (unsigned)Sc(8, s));

    if (k->font) XSetFont(k->dpy, k->hub_gc, k->font->fid);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 176, 184, 202));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, P + Sc(14, s), curY + Sc(70, s), l2, (int)strlen(l2));
    return curY + cardH + Sc(14, s);
}

static void draw_hub(KarelApp *k) {
    if (!k->hub_win) return;
    float s = k->dpi;
    int W = Sc(560, s), P = Sc(18, s), Win = W - 2 * P, gap = Sc(10, s), en = is_en(k);
    int totH = Sc(k->save.connected ? 446 : 408, s);
    XResizeWindow(k->dpy, k->hub_win, (unsigned)W, (unsigned)totH);

    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 18, 20, 27));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, 0, 0, (unsigned)W, (unsigned)totH);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 196, 30, 37));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, 0, 0, (unsigned)W, (unsigned)Sc(44, s));

    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
    if (k->bfont) XSetFont(k->dpy, k->hub_gc, k->bfont->fid);
    char hdr[96];
    snprintf(hdr, sizeof(hdr), "KAREL DE KOALA  *  STICKY RP2350   v%s", KAREL_VERSION);
    XDrawString(k->dpy, k->hub_win, k->hub_gc, P, Sc(28, s), hdr, (int)strlen(hdr));

    k->nhub_btns = 0;
    int curY = draw_hub_stats_card(k, s, P, Win, Sc(58, s), en);

    const char *act_lbls[6] = {
        en ? "Feed" : "Voer", en ? "Coffee" : "Koffie",
        en ? "Pet" : "Aai",   en ? "Wash" : "Was",
        "Powernap", k->focus_active ? "Stop Focus" : "Focus 25m"
    };
    static const uint8_t bc[6][3] = {
        {38, 115, 77}, {115, 75, 58}, {168, 32, 90},
        {13, 115, 133}, {59, 74, 90}, {42, 48, 66}
    };
    int bw = (Win - 2 * gap) / 3, bh = Sc(38, s);
    for (int i = 0; i < 6; i++) {
        int bx = P + (i % 3) * (bw + gap), by = curY + (i / 3) * (bh + gap);
        add_hub_btn(k, bx, by, bw, bh, i + 1);
        XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, bc[i][0], bc[i][1], bc[i][2]));
        XFillRectangle(k->dpy, k->hub_win, k->hub_gc, bx, by, (unsigned)bw, (unsigned)bh);
        XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
        XDrawString(k->dpy, k->hub_win, k->hub_gc, bx + Sc(14, s), by + Sc(24, s), act_lbls[i], (int)strlen(act_lbls[i]));
    }

    curY += 2 * bh + gap + Sc(14, s);
    int stH = Sc(48, s);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 27, 31, 42));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, P, curY, (unsigned)Win, (unsigned)stH);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 152, 162, 184));
    const char *sl = en ? "Style:" : "Stijl:";
    XDrawString(k->dpy, k->hub_win, k->hub_gc, P + Sc(14, s), curY + Sc(28, s), sl, (int)strlen(sl));

    char sk_l[48], out_l[48];
    snprintf(sk_l, sizeof(sk_l), "%s: %s  v", en ? "Coat" : "Vacht", k->save.skin);
    snprintf(out_l, sizeof(out_l), "Outfit: %s  v", *k->save.equipped ? k->save.equipped : (en ? "none" : "geen"));
    int rndW = Sc(76, s), pkw = (Win - Sc(88, s) - rndW) / 2;
    int px0 = P + Sc(66, s), px1 = P + Sc(72, s) + pkw, px2 = P + Sc(78, s) + 2 * pkw, pw2 = Win - Sc(88, s) - 2 * pkw;
    add_hub_btn(k, px0, curY + Sc(8, s), pkw, Sc(32, s), 10);
    add_hub_btn(k, px1, curY + Sc(8, s), pkw, Sc(32, s), 11);
    add_hub_btn(k, px2, curY + Sc(8, s), pw2, Sc(32, s), 12);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 42, 48, 66));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, px0, curY + Sc(8, s), (unsigned)pkw, (unsigned)Sc(32, s));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, px1, curY + Sc(8, s), (unsigned)pkw, (unsigned)Sc(32, s));
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 132, 42, 108));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, px2, curY + Sc(8, s), (unsigned)pw2, (unsigned)Sc(32, s));
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, px0 + Sc(10, s), curY + Sc(28, s), sk_l, (int)strlen(sk_l));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, px1 + Sc(10, s), curY + Sc(28, s), out_l, (int)strlen(out_l));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, px2 + Sc(12, s), curY + Sc(28, s), "Random", 6);

    curY += stH + Sc(12, s);
    char snd_l[32], aq_l[32];
    snprintf(snd_l, sizeof(snd_l), "%s%s", en ? "Sound: " : "Geluid: ", k->muted ? (en ? "OFF" : "UIT") : (en ? "ON" : "AAN"));
    snprintf(aq_l, sizeof(aq_l), "%s%s", en ? "Quiet: " : "Auto-Stil: ", k->save.auto_quiet ? (en ? "ON" : "AAN") : (en ? "OFF" : "UIT"));
    const char *row3[3] = {snd_l, aq_l, "NL / EN"};
    int sh = Sc(36, s);
    for (int i = 0; i < 3; i++) {
        int bx = P + i * (bw + gap);
        add_hub_btn(k, bx, curY, bw, sh, 20 + i);
        XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 42, 48, 66));
        XFillRectangle(k->dpy, k->hub_win, k->hub_gc, bx, curY, (unsigned)bw, (unsigned)sh);
        XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
        XDrawString(k->dpy, k->hub_win, k->hub_gc, bx + Sc(14, s), curY + Sc(23, s), row3[i], (int)strlen(row3[i]));
    }

    curY += sh + Sc(12, s);
    const char *hl = en ? "Check for updates (GitHub)" : "Check op updates (GitHub)";
    add_hub_btn(k, P, curY, Win, Sc(30, s), 26);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 28, 42, 62));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, P, curY, (unsigned)Win, (unsigned)Sc(30, s));
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 220, 232, 250));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, P + Sc(14, s), curY + Sc(20, s), hl, (int)strlen(hl));
    curY += Sc(38, s);

    char foot[700];
    snprintf(foot, sizeof(foot), "%.200s   |   %.60s",
             k->save.connected ? k->save.drive_root : (en ? "Memory mode (no USB)" : "Geheugen-modus (geen USB)"),
             *k->ser.port ? k->ser.port : (en ? "Serial: waiting..." : "Serial: wachten..."));
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 62, 207, 142));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, P, curY + Sc(18, s), foot, (int)strlen(foot));

    int qw = Sc(105, s);
    add_hub_btn(k, W - P - qw, curY, qw, Sc(26, s), 30);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 150, 28, 36));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, W - P - qw, curY, (unsigned)qw, (unsigned)Sc(26, s));
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
    const char *qlbl = en ? "Dive & Quit" : "Sluit Karel";
    XDrawString(k->dpy, k->hub_win, k->hub_gc, W - P - qw + Sc(12, s), curY + Sc(17, s), qlbl, (int)strlen(qlbl));
}

static void open_hub(KarelApp *k) {
    if (k->hidden) {
        k->hidden = 0;
        XMapRaised(k->dpy, k->karel_win);
        trigger_climb(k, is_en(k) ? "I'm back!" : "Daar ben ik weer!");
    }
    if (k->hub_win) {
        XMapRaised(k->dpy, k->hub_win);
        draw_hub(k);
        return;
    }
    int W = Sc(560, k->dpi), H = Sc(408, k->dpi);
    k->hub_win = XCreateSimpleWindow(k->dpy, k->root, 200, 160, (unsigned)W, (unsigned)H,
                                     0, 0, rgb_px(k->dpy, k->scr, 18, 20, 27));
    XStoreName(k->dpy, k->hub_win, "Karel de Koala - Sticky Hub");
    XSetWMProtocols(k->dpy, k->hub_win, &k->wm_del, 1);
    XSelectInput(k->dpy, k->hub_win, ExposureMask | ButtonPressMask | KeyPressMask);
    k->hub_gc = XCreateGC(k->dpy, k->hub_win, 0, NULL);
    XMapRaised(k->dpy, k->hub_win);
    draw_hub(k);
}

static void handle_hub_click(KarelApp *k, int mx, int my, int x_root, int y_root) {
    close_popup(k);
    for (int i = 0; i < k->nhub_btns; i++) {
        HubBtn b = k->hub_btns[i];
        if (mx < b.x || mx > b.x + b.w || my < b.y || my > b.y + b.h) continue;
        if (b.id == 1) do_feed(k);
        else if (b.id == 2) do_coffee(k);
        else if (b.id == 3) do_pet(k);
        else if (b.id == 4) do_wash(k);
        else if (b.id == 5) nap_toggle(k);
        else if (b.id == 6) {
            k->focus_active = !k->focus_active;
            if (k->focus_active) {
                k->focus_rem = 25 * 60;
                k->focus_last = time(NULL);
                say_msg(k, "Focus: 25m!", 45);
            } else {
                say_msg(k, is_en(k) ? "Focus stopped." : "Focus gestopt.", 35);
            }
        }
        else if (b.id == 10) { open_popup(k, POP_SKIN, x_root - mx + b.x, y_root - my + b.y + b.h); return; }
        else if (b.id == 11) { open_popup(k, POP_OUTFIT, x_root - mx + b.x, y_root - my + b.y + b.h); return; }
        else if (b.id == 12) do_random_style(k);
        else if (b.id == 20) k->muted = !k->muted;
        else if (b.id == 21) { k->save.auto_quiet = !k->save.auto_quiet; save_persist(&k->save); }
        else if (b.id == 22) { strcpy(k->save.language, is_en(k) ? "nl" : "en"); save_persist(&k->save); }
        else if (b.id == 26) {
            say_msg(k, is_en(k) ? "Checking GitHub for updates..." : "Controleren op updates...", 60);
            if (k->upd_pipe < 0) start_updater_async(&k->upd_pipe);
        }
        else if (b.id == 30) { trigger_dive(k, "quit"); return; }
        draw_hub(k);
        return;
    }
}

static void handle_key_event(KarelApp *k, XKeyEvent *kev) {
    KeySym ks = XLookupKeysym(kev, 0);
    if (ks == XK_A) ks = XK_a;
    if (ks == XK_B) ks = XK_b;
    if (ks == XK_b) k->b21_step = 1;
    else if (ks == XK_2 && k->b21_step == 1) k->b21_step = 2;
    else if (ks == XK_1 && k->b21_step == 2) { k->b21_step = 0; trigger_b21(k); return; }
    else k->b21_step = 0;
    static const KeySym seq[10] = {
        XK_Up, XK_Up, XK_Down, XK_Down, XK_Left, XK_Right, XK_Left, XK_Right, XK_b, XK_a
    };
    if (ks == XK_Up || ks == XK_Down || ks == XK_Left || ks == XK_Right || ks == XK_a || ks == XK_b) {
        if (k->nkonami == 10) {
            memmove(k->konami, k->konami + 1, sizeof(KeySym) * 9);
            k->nkonami = 9;
        }
        k->konami[k->nkonami++] = ks;
        if (k->nkonami == 10 && memcmp(k->konami, seq, sizeof(seq)) == 0) {
            k->nkonami = 0;
            trigger_konami(k);
        }
    } else {
        k->nkonami = 0;
    }
}

/* =========================================================================
 * 5. Roaming Physics, Background Event Polling & Ask Prompt
 * ========================================================================= */

static void poll_background_events(KarelApp *k, int maxx, int miny) {
    if (k->frame_idx % 16 == 0) {
        if (k->save.auto_quiet) {
            int busy = detect_auto_quiet(k);
            if (busy && !k->auto_paused) {
                k->pq_x = k->wx; k->pq_y = k->wy; k->has_pq = 1;
                k->auto_paused = 1; k->wx = maxx; k->wy = miny;
                k->bubble[0] = 0; k->bubble_ticks = 0; strcpy(k->state, "IDLE");
            } else if (!busy && k->auto_paused) {
                k->auto_paused = 0;
                if (k->has_pq) { k->wx = k->pq_x; k->wy = k->pq_y; k->has_pq = 0; }
            }
        } else {
            k->auto_paused = 0;
        }

        int usb = poll_usb(&k->save);
        if (usb < 0) {
            if (k->hub_win) XUnmapWindow(k->dpy, k->hub_win);
            say_msg(k, is_en(k) ? "USB unplugged! Bye!" : "USB los! Doei!", 45);
            trigger_dive(k, "quit");
        } else if (usb > 0) {
            trigger_climb(k, is_en(k) ? "KAREL USB reconnected!" : "KAREL USB herverbonden!");
            draw_hub(k);
        }
    }

    if (k->upd_pipe >= 0) {
        char buf[48];
        ssize_t nr = read(k->upd_pipe, buf, sizeof(buf) - 1);
        if (nr > 0) {
            buf[nr] = 0;
            close(k->upd_pipe);
            k->upd_pipe = -1;
            if (strncmp(buf, "NEW:", 4) == 0 && is_valid_semver(buf + 4)) {
                char um[96];
                snprintf(um, sizeof(um),
                         is_en(k) ? "Update v%.16s available! Opening GitHub..." : "Update v%.16s beschikbaar! GitHub openen...",
                         buf + 4);
                say_msg(k, um, 80);
                open_with_xdg(KAREL_RELEASES_URL);
            } else if (strcmp(buf, "UPTODATE") == 0) {
                char um[64];
                snprintf(um, sizeof(um), is_en(k) ? "Up to date (v%s)!" : "Al nieuwste versie (v%s)!", KAREL_VERSION);
                say_msg(k, um, 65);
            } else if (strcmp(buf, "OFFLINE") == 0) {
                say_msg(k, is_en(k) ? "Cannot reach GitHub." : "Kan GitHub niet bereiken.", 60);
            } else {
                say_msg(k, is_en(k) ? "Update check failed." : "Update-check mislukt.", 60);
            }
        } else if (nr == 0) {
            close(k->upd_pipe);
            k->upd_pipe = -1;
        }
    }

    if (k->focus_active && difftime(time(NULL), k->focus_last) >= 1.0) {
        k->focus_last = time(NULL);
        if (k->focus_rem > 0) k->focus_rem--;
        if (k->focus_rem == 0) {
            k->focus_active = 0;
            award_xp(k, 45);
            set_act(k, "CELEBRATE", 40);
            spawn_particles(k, "*", 245, 196, 81, 14);
            play_sound_key("levelup", k->muted, k->auto_paused);
            say_msg(k, is_en(k) ? "Focus complete! +45 XP!" : "Focus klaar! +45 XP!", 70);
            save_persist(&k->save);
            draw_hub(k);
        }
    }
}

static void step_window_ledge_roam(KarelApp *k, int wy, int wh, int minx, int maxx, int miny, int gy) {
    if (strcmp(k->save.roam_mode, "window") == 0) {
        if ((++k->ledge_ticks % 12) == 1 || !k->has_ledge) {
            int ax, ay, aw, ah;
            char ttl[64];
            if (query_active_win(k, &ax, &ay, &aw, &ah, ttl, sizeof(ttl)) &&
                aw >= px_sz(k) + 48 && ah >= 140 && ay >= wy + 36 && ay <= wy + wh - 80) {
                k->has_ledge = 1;
                k->ledge_x = ax + 12;
                k->ledge_y = ay;
                k->ledge_w = aw - 24;
            } else {
                k->has_ledge = 0;
            }
        }
        if (k->has_ledge) {
            int tx0 = k->ledge_x - k_ox(k);
            int tx1 = k->ledge_x + k->ledge_w - k_ox(k) - px_sz(k);
            if (tx0 < minx) tx0 = minx;
            if (tx1 > maxx) tx1 = maxx;
            k->roam_ty = k->ledge_y - (k_oy(k) + px_sz(k));
            if (k->roam_ty < miny) k->roam_ty = miny;
            if (k->roam_ty > gy) k->roam_ty = gy;
            if (k->roam_tx < tx0 || k->roam_tx > tx1) {
                k->roam_tx = tx0 + (tx1 > tx0 ? rand() % (tx1 - tx0) : 0);
            }
        } else {
            k->roam_ty = gy;
        }
        if ((!k->has_ledge && k->wy < gy - 18) || k->roam_ty > k->wy + 28) {
            k->umbrella_fall = 1;
            k->roam_wait = 0; k->roam_ticks = 0; k->act_ticks = 0;
            say_msg(k, is_en(k) ? "Window gone! Sticky umbrella open!" : "Oeps, venster weg! Paraplu open!", 42);
        }
    }
}

static void step_roam(KarelApp *k, int wy, int wh, int minx, int maxx, int miny, int gy) {
    if (k->disco_ticks > 0) { strcpy(k->state, "DANCE"); return; }
    if (strcmp(k->save.roam_mode, "park") == 0) { strcpy(k->state, "IDLE"); return; }

    if (strcmp(k->save.roam_mode, "cursor") == 0) {
        Window rr, cc;
        int rx = 0, ry = 0, wxx = 0, wyy = 0;
        unsigned mm = 0;
        if (XQueryPointer(k->dpy, k->root, &rr, &cc, &rx, &ry, &wxx, &wyy, &mm)) {
            double tx = rx - win_w(k) * 0.5;
            double tyc = ry - (k_oy(k) + px_sz(k) * 0.5);
            if (tx < minx) tx = minx;
            if (tx > maxx) tx = maxx;
            if (tyc < miny) tyc = miny;
            if (tyc > gy) tyc = gy;
            double dx = tx - k->wx, dy = tyc - k->wy, d = hypot(dx, dy);
            if (d > 14) {
                k->wx += (dx / d) * 3.4;
                k->wy += (dy / d) * 3.4;
                strcpy(k->state, dx < 0 ? "WALK_LEFT" : "WALK_RIGHT");
            } else {
                strcpy(k->state, "IDLE");
            }
        }
        return;
    }

    step_window_ledge_roam(k, wy, wh, minx, maxx, miny, gy);
    if (k->umbrella_fall) return;

    if (k->roam_wait > 0) {
        k->roam_wait--;
        if (k->roam_wait % 60 == 30 && (rand() % 10) < 6) {
            static const char *acts[] = {
                "BLINK_SMILE", "EARS_WIGGLE", "PEEK", "SIT", "LAPTOP_CODE", "UMBRELLA",
                "BOW", "WAVE", "SKATEBOARD", "JUGGLE", "MAGIC_TRICK", "DJ",
                "TELESCOPE", "BALLOON", "MEDITATE", "PIZZA", "NINJA", "KARATE"
            };
            set_act(k, acts[rand() % 18], 32);
        } else {
            strcpy(k->state, "IDLE");
        }
        return;
    }

    double dx = k->roam_tx - k->wx, dy = k->roam_ty - k->wy, dd = hypot(dx, dy);
    k->roam_ticks++;
    if (dd < 10 || k->roam_ticks > 155) {
        k->roam_ticks = 0;
        k->roam_wait = 130 + (rand() % 150);
        k->roam_tx = minx + (rand() % (maxx > minx ? (maxx - minx) : 1));
        k->roam_ty = (strcmp(k->save.roam_mode, "window") == 0 && k->has_ledge)
            ? k->roam_ty
            : gy - ((rand() % 3 == 0) ? (rand() % ((gy - miny > 10) ? (gy - miny) / 2 : 10)) : 0);
        if ((rand() % 7 == 0) && difftime(time(NULL), k->last_auto_say) > 35 && k->bubble_ticks == 0) {
            k->last_auto_say = time(NULL);
            say_msg(k, pick_smart_quote(k), 60);
        }
    } else {
        k->wx += (dx / dd) * 2.2;
        k->wy += (dy / dd) * 2.2;
        strcpy(k->state, k->jump_y < -1 ? "JUMP" : (dx < 0 ? "WALK_LEFT" : "WALK_RIGHT"));
    }
}

static void step_physics(KarelApp *k) {
    k->frame_idx++;
    int wx, wy, ww, wh;
    get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);
    int minx = wx - k_ox(k) + 6, maxx = wx + ww - k_ox(k) - px_sz(k) - 6;
    int miny = wy - k_oy(k) + 6, gy = wy + wh - (k_oy(k) + px_sz(k));

    poll_background_events(k, maxx, miny);

    if (k->closing) {
        k->close_step++;
        if (k->close_step <= 9) k->wy = k->close_sy + (gy - k->close_sy) * (k->close_step / 9.0);
        else if (k->close_step <= 13) { k->wy = gy; k->jump_y = -14.0 * sin((k->close_step - 9) * 3.14159 / 4.0); }
        else { k->wy = gy; k->jump_y = 0; }
        if (k->close_step >= 27) {
            if (strcmp(k->dive_mode, "tray") == 0) {
                k->closing = 0; k->hidden = 1;
                save_persist(&k->save);
                XUnmapWindow(k->dpy, k->karel_win);
            } else {
                k->quit_req = 1;
            }
        }
    } else if (k->climbing) {
        if (++k->climb_step >= 18) {
            k->climbing = 0;
            k->jump_vy = -9.0;
            say_msg(k, k->climb_msg, 65);
            set_act(k, "WAVE", 28);
        }
    } else if (k->flying) {
        k->wx += k->fling_vx; k->wy += k->fling_vy;
        k->fling_vx *= 0.98; k->fling_vy += 1.45;
        if (k->wx < minx) { k->wx = minx; k->fling_vx = -k->fling_vx * 0.65; }
        if (k->wx > maxx) { k->wx = maxx; k->fling_vx = -k->fling_vx * 0.65; }
        if (k->wy < miny) { k->wy = miny; k->fling_vy = fabs(k->fling_vy) * 0.6; }
        if (k->wy >= gy) {
            k->wy = gy;
            if (fabs(k->fling_vy) > 5.0) k->fling_vy = -k->fling_vy * 0.45;
            else { k->flying = 0; strcpy(k->state, "IDLE"); }
        } else {
            strcpy(k->state, "JETPACK");
        }
    } else if (k->umbrella_fall) {
        strcpy(k->state, "UMBRELLA");
        k->wy += 2.6;
        if (k->wy > gy) k->wy = gy;
        k->wx += sin(k->frame_idx * 0.28) * 1.6;
        if (k->wx < minx) k->wx = minx;
        if (k->wx > maxx) k->wx = maxx;
        if (k->wy >= gy - 0.5) {
            k->wy = gy;
            k->umbrella_fall = 0;
            strcpy(k->state, "IDLE");
            k->roam_wait = 80;
        }
    } else if (!k->dragging && !k->auto_paused && k->act_ticks == 0 && strcmp(k->state, "SLEEP") != 0) {
        step_roam(k, wy, wh, minx, maxx, miny, gy);
    }

    if (k->jump_y < 0 || k->jump_vy < 0) {
        k->jump_y += k->jump_vy;
        k->jump_vy += 1.9;
        if (k->jump_y >= 0) { k->jump_y = 0; k->jump_vy = 0; }
    }
    if ((k->frame_idx % 8) == 0 && (rand() % 10) < 3 && k->jump_y == 0 &&
        (strcmp(k->state, "WALK_LEFT") == 0 || strcmp(k->state, "WALK_RIGHT") == 0)) {
        k->jump_vy = -5.5;
    }
    if (k->act_ticks > 0 && --k->act_ticks == 0) strcpy(k->state, "IDLE");
    if (k->disco_ticks > 0 && (--k->disco_ticks % 12) == 0) spawn_particles(k, "*", 245, 196, 81, 4);
    if (k->hyper_ticks > 0) k->hyper_ticks--;
    if (k->bubble_ticks > 0) k->bubble_ticks--;

    if ((k->frame_idx % 5) == 0) {
        for (int i = k->nparts - 1; i >= 0; i--) {
            k->parts[i].x += k->parts[i].vx;
            k->parts[i].y += k->parts[i].vy;
            k->parts[i].vy += 0.35;
            if (--k->parts[i].life <= 0) k->parts[i] = k->parts[--k->nparts];
        }
    }

    if ((k->frame_idx % 18) == 0) {
        if (k->hidden || k->auto_paused) ser_send(&k->ser, "STATE:QUIET");
        else if (k->focus_active) ser_send(&k->ser, "STATE:STUDY");
        else if (k->disco_ticks > 0 || strcmp(k->state, "DANCE") == 0) ser_send(&k->ser, "STATE:PARTY");
        else if (k->hyper_ticks > 0) ser_send(&k->ser, "STATE:HYPER");
        else if (k->save.hunger < 25) ser_send(&k->ser, "STATE:HUNGRY");
        else ser_send(&k->ser, "STATE:HAPPY");
    }

    if (!k->hidden) {
        XMoveWindow(k->dpy, k->karel_win, (int)llround(k->wx), (int)llround(k->wy + k->jump_y));
        paint_karel(k);
    }
}

static int run_ask_prompt(KarelApp *k) {
    float s = k->dpi;
    int W = Sc(490, s), H = Sc(224, s), P = Sc(18, s), hdrH = Sc(40, s), en = is_en(k);
    int wx, wy, ww, wh;
    get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);

    Window win = XCreateSimpleWindow(k->dpy, k->root, wx + (ww - W) / 2, wy + (wh - H) / 2,
                                     (unsigned)W, (unsigned)H, 0, 0, rgb_px(k->dpy, k->scr, 18, 20, 27));
    XStoreName(k->dpy, win, "Karel de Koala");
    XSetWMProtocols(k->dpy, win, &k->wm_del, 1);
    XSelectInput(k->dpy, win, ExposureMask | ButtonPressMask | KeyPressMask);
    GC gc = XCreateGC(k->dpy, win, 0, NULL);

    Rgba frame[32][32];
    render_frame_rgba(&k->sb, "IDLE", 0, k->save.skin, k->save.equipped, frame);
    XMapRaised(k->dpy, win);

    int confirm = 0, done = 0, res = 0;
    while (!done) {
        XEvent ev;
        XNextEvent(k->dpy, &ev);
        if (ev.type == Expose) {
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 18, 20, 27));
            XFillRectangle(k->dpy, win, gc, 0, 0, (unsigned)W, (unsigned)H);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 196, 30, 37));
            XFillRectangle(k->dpy, win, gc, 0, 0, (unsigned)W, (unsigned)hdrH);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
            if (k->bfont) XSetFont(k->dpy, gc, k->bfont->fid);
            char hdr[96];
            snprintf(hdr, sizeof(hdr), "KAREL DE KOALA  *  STICKY RP2350   v%s", KAREL_VERSION);
            XDrawString(k->dpy, win, gc, P, Sc(26, s), hdr, (int)strlen(hdr));

            int boxSz = Sc(104, s), by0 = hdrH + Sc(16, s);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 27, 31, 42));
            XFillRectangle(k->dpy, win, gc, P, by0, (unsigned)boxSz, (unsigned)boxSz);
            int pxs = Sc(3, s), ox = P + (boxSz - 32 * pxs) / 2, oy = by0 + (boxSz - 32 * pxs) / 2;
            for (int py = 0; py < 32; py++) {
                for (int px = 0; px < 32; px++) {
                    if (!frame[py][px].a) continue;
                    XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, frame[py][px].r, frame[py][px].g, frame[py][px].b));
                    XFillRectangle(k->dpy, win, gc, ox + px * pxs, oy + py * pxs, (unsigned)pxs, (unsigned)pxs);
                }
            }

            int tx = P + boxSz + Sc(16, s);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 242, 245, 250));
            const char *q = confirm
                ? (en ? "Are you sure?" : "Weet je het zeker?")
                : (en ? "Do you want a koala on your screen?" : "Wil je een koala op je scherm hebben?");
            XDrawString(k->dpy, win, gc, tx, hdrH + Sc(42, s), q, (int)strlen(q));
            if (k->font) XSetFont(k->dpy, gc, k->font->fid);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 176, 184, 202));
            const char *sub = confirm
                ? (en ? "Karel stays off your screen." : "Karel verschijnt dan niet op je scherm.")
                : (en ? "Karel lives on your Sticky RP2350." : "Karel woont op je Sticky RP2350-stick.");
            XDrawString(k->dpy, win, gc, tx, hdrH + Sc(72, s), sub, (int)strlen(sub));

            int btnY = H - Sc(54, s), btnH = Sc(36, s);
            if (!confirm) {
                int x1 = P, w1 = Sc(118, s), x2 = P + Sc(128, s), w2 = Sc(198, s), x3 = W - P - Sc(118, s), w3 = Sc(118, s);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 38, 115, 77));  XFillRectangle(k->dpy, win, gc, x1, btnY, (unsigned)w1, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 42, 48, 66));   XFillRectangle(k->dpy, win, gc, x2, btnY, (unsigned)w2, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 140, 38, 48));  XFillRectangle(k->dpy, win, gc, x3, btnY, (unsigned)w3, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
                if (k->bfont) XSetFont(k->dpy, gc, k->bfont->fid);
                const char *l1 = en ? "Yes" : "Ja", *l2 = en ? "View README" : "README bekijken", *l3 = en ? "No" : "Nee";
                XDrawString(k->dpy, win, gc, x1 + Sc(44, s), btnY + Sc(23, s), l1, (int)strlen(l1));
                XDrawString(k->dpy, win, gc, x2 + Sc(26, s), btnY + Sc(23, s), l2, (int)strlen(l2));
                XDrawString(k->dpy, win, gc, x3 + Sc(40, s), btnY + Sc(23, s), l3, (int)strlen(l3));
            } else {
                int w2 = Sc(218, s), x1 = P, x2 = W - P - w2;
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 38, 115, 77));  XFillRectangle(k->dpy, win, gc, x1, btnY, (unsigned)w2, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 140, 38, 48));  XFillRectangle(k->dpy, win, gc, x2, btnY, (unsigned)w2, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
                if (k->bfont) XSetFont(k->dpy, gc, k->bfont->fid);
                const char *l1 = en ? "Actually yes!" : "Toch wel!", *l2 = en ? "Yes, skip" : "Ja, sluit af";
                XDrawString(k->dpy, win, gc, x1 + Sc(64, s), btnY + Sc(23, s), l1, (int)strlen(l1));
                XDrawString(k->dpy, win, gc, x2 + Sc(58, s), btnY + Sc(23, s), l2, (int)strlen(l2));
            }
        } else if (ev.type == ButtonPress && ev.xbutton.button == Button1) {
            int cx = ev.xbutton.x, cy = ev.xbutton.y, btnY = H - Sc(54, s), btnH = Sc(36, s);
            if (cy >= btnY && cy <= btnY + btnH) {
                if (!confirm) {
                    int x1 = P, w1 = Sc(118, s), x2 = P + Sc(128, s), w2 = Sc(198, s), x3 = W - P - Sc(118, s), w3 = Sc(118, s);
                    if (cx >= x1 && cx <= x1 + w1) { res = 1; done = 1; }
                    else if (cx >= x2 && cx <= x2 + w2) {
                        char lmd[600];
                        if (k->save.connected && *k->save.drive_root) snprintf(lmd, sizeof(lmd), "%.500s/README.md", k->save.drive_root);
                        else lmd[0] = 0;
                        open_with_xdg((*lmd && file_exists(lmd)) ? lmd : "https://github.com/svsticky/karel-de-koala#readme");
                    } else if (cx >= x3 && cx <= x3 + w3) {
                        confirm = 1;
                        XClearArea(k->dpy, win, 0, 0, 0, 0, True);
                    }
                } else {
                    int w2 = Sc(218, s), x1 = P, x2 = W - P - w2;
                    if (cx >= x1 && cx <= x1 + w2) { res = 1; done = 1; }
                    else if (cx >= x2 && cx <= x2 + w2) { res = 0; done = 1; }
                }
            }
        } else if (ev.type == KeyPress) {
            KeySym ks = XLookupKeysym(&ev.xkey, 0);
            if (ks == XK_Escape) { res = 0; done = 1; }
            else if (ks == XK_Return && !confirm) { res = 1; done = 1; }
        } else if (ev.type == ClientMessage && (Atom)ev.xclient.data.l[0] == k->wm_del) {
            res = 0; done = 1;
        }
    }

    XFreeGC(k->dpy, gc);
    XDestroyWindow(k->dpy, win);
    XFlush(k->dpy);
    return res;
}

static void handle_karel_mouse_release(KarelApp *k, const XButtonEvent *be) {
    k->dragging = 0;
    double moved = hypot(be->x_root - k->drag_sx, be->y_root - k->drag_sy);
    if (moved < 6) {
        int sx = (be->x - k_ox(k)) / k->scale, sy = (be->y - k_oy(k)) / k->scale;
        if (sx >= 13 && sx <= 18 && sy >= 12 && sy <= 16) {
            if (difftime(time(NULL), k->last_nose_t) > 4.5) k->nose_clicks = 0;
            k->last_nose_t = time(NULL);
            if (++k->nose_clicks >= 7) {
                k->nose_clicks = 0;
                play_sound_key("sneeze", k->muted, k->auto_paused);
                spawn_particles(k, "*", 245, 245, 245, 10);
                set_act(k, "SNEEZE", 24);
                say_msg(k, is_en(k) ? "Achoo! BBG dust!" : "Hatsjoe! BBG stof!", 55);
            }
        } else if (k->act_ticks == 0 && strcmp(k->state, "SLEEP") != 0) {
            open_hub(k);
        }
        return;
    }

    double dt = difftime(time(NULL), k->last_drag_t);
    if (dt < 0.08) dt = 0.08;
    double vx = (be->x_root - k->drag_sx) / (dt * 20.0);
    double vy = (be->y_root - k->drag_sy) / (dt * 20.0);
    double spd = hypot(vx, vy);
    if (spd > 10.0) {
        const LocaleSet *ls = active_locale(k);
        k->flying = 1;
        k->fling_vx = vx > 36 ? 36 : (vx < -36 ? -36 : vx);
        k->fling_vy = vy > 26 ? 26 : (vy < -32 ? -32 : vy);
        play_sound_key("toss", k->muted, k->auto_paused);
        say_msg(k, spd > 22.0 ? pick_arr(ls->toss_hard, ls->n_toss_hard, sizeof(ls->toss_hard[0]), "JETPACK!!")
                              : pick_arr(ls->toss_soft, ls->n_toss_soft, sizeof(ls->toss_soft[0]), "Wheee!"), 45);
    }
}

static void handle_x11_events(KarelApp *k) {
    while (XPending(k->dpy)) {
        XEvent ev;
        XNextEvent(k->dpy, &ev);
        if (ev.type == ClientMessage && ev.xclient.window == k->hub_win && (Atom)ev.xclient.data.l[0] == k->wm_del) {
            XUnmapWindow(k->dpy, k->hub_win);
        } else if (ev.type == KeyPress) {
            handle_key_event(k, &ev.xkey);
        } else if (ev.type == Expose && ev.xexpose.window == k->hub_win) {
            draw_hub(k);
        } else if (ev.type == Expose && ev.xexpose.window == k->pop_win) {
            draw_popup(k);
        } else if (ev.type == MotionNotify && ev.xmotion.window == k->pop_win) {
            int nh = (ev.xmotion.y - 4) / pop_rh(k);
            if (nh != k->pop_hover) { k->pop_hover = nh; draw_popup(k); }
        } else if (ev.type == ButtonPress && ev.xbutton.window == k->pop_win && ev.xbutton.button == 1) {
            click_popup(k, ev.xbutton.y, ev.xbutton.x_root, ev.xbutton.y_root);
        } else if (ev.type == ButtonPress && ev.xbutton.window == k->hub_win && ev.xbutton.button == 1) {
            handle_hub_click(k, ev.xbutton.x, ev.xbutton.y, ev.xbutton.x_root, ev.xbutton.y_root);
        } else if (ev.type == ButtonPress && ev.xbutton.window == k->karel_win) {
            close_popup(k);
            if (ev.xbutton.button == 3) {
                open_popup(k, POP_MAIN, ev.xbutton.x_root, ev.xbutton.y_root);
            } else if (ev.xbutton.button == 1) {
                static Time last_click = 0;
                if (ev.xbutton.time - last_click < 350) {
                    do_pet(k);
                    last_click = 0;
                } else {
                    last_click = ev.xbutton.time;
                    k->dragging = 1; k->flying = 0; k->climbing = 0; k->umbrella_fall = 0; k->jump_y = 0;
                    k->drag_dx = ev.xbutton.x; k->drag_dy = ev.xbutton.y;
                    k->drag_sx = ev.xbutton.x_root; k->drag_sy = ev.xbutton.y_root;
                    k->last_drag_t = time(NULL);
                }
            }
        } else if (ev.type == MotionNotify && ev.xmotion.window == k->karel_win && k->dragging) {
            strcpy(k->state, "JETPACK");
            k->wx = ev.xmotion.x_root - k->drag_dx;
            k->wy = ev.xmotion.y_root - k->drag_dy;
            XMoveWindow(k->dpy, k->karel_win, (int)k->wx, (int)k->wy);
        } else if (ev.type == ButtonRelease && ev.xbutton.window == k->karel_win && k->dragging) {
            handle_karel_mouse_release(k, &ev.xbutton);
        }
    }
}

static void poll_ipc_and_serial(KarelApp *k) {
    if (k->ipc_fd >= 0) {
        int c = accept(k->ipc_fd, NULL, NULL);
        if (c >= 0) {
            struct timeval tv;
            tv.tv_sec = 0;
            tv.tv_usec = 500000;
            setsockopt(c, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
            char msg[64];
            ssize_t n = read(c, msg, sizeof(msg) - 1);
            close(c);
            if (n > 0) {
                msg[n] = 0;
                if (strncmp(msg, "KAREL_TOGGLE", 12) == 0) {
                    if (k->hidden) {
                        k->hidden = 0;
                        XMapRaised(k->dpy, k->karel_win);
                        trigger_climb(k, is_en(k) ? "I'm back!" : "Daar ben ik weer!");
                    } else {
                        trigger_dive(k, "quit");
                    }
                } else if (strncmp(msg, "KAREL_BOOP", 10) == 0) {
                    if (k->hidden) { k->hidden = 0; XMapRaised(k->dpy, k->karel_win); }
                    do_boop(k);
                }
            }
        }
    }

    char sev[64];
    ser_poll(&k->ser, sev, sizeof(sev));
    if (!*sev) return;

    if (strcmp(sev, "EVENT:PET") == 0) do_pet(k);
    else if (strcmp(sev, "EVENT:FEED") == 0) do_feed(k);
    else if (strcmp(sev, "EVENT:COFFEE") == 0) do_coffee(k);
    else if (strcmp(sev, "EVENT:WASH") == 0) do_wash(k);
    else if (strcmp(sev, "EVENT:DISCO") == 0) trigger_konami(k);
    else if (strcmp(sev, "EVENT:RST_BOOP") == 0 || strcmp(sev, "EVENT:GIFT") == 0) do_boop(k);
    else if (strcmp(sev, "EVENT:TOGGLE_KAREL") == 0 || strcmp(sev, "EVENT:TRAY_TOGGLE") == 0) {
        if (k->hidden) {
            k->hidden = 0;
            XMapRaised(k->dpy, k->karel_win);
            trigger_climb(k, is_en(k) ? "I'm back!" : "Daar ben ik weer!");
        } else {
            trigger_dive(k, "quit");
        }
    }
}

#endif /* !KAREL_CORE_TEST */

/* =========================================================================
 * 6. Entry Point & Self-Test
 * ========================================================================= */

static int run_self_test(void) {
    char gz[600], lj[600];
    if (!locate_sprites_gz(gz, sizeof(gz))) {
        fprintf(stderr, "Error: karel_sprites.gz not found\n");
        return 1;
    }
    if (!locate_locale_json(lj, sizeof(lj))) {
        fprintf(stderr, "Error: locale.json not found\n");
        return 1;
    }
    static SpriteBank sb;
    if (!load_sprites_gz(&sb, gz)) {
        fprintf(stderr, "Failed loading %s\n", gz);
        return 1;
    }
    static LocaleStore loc;
    if (!load_locale_json(&loc, lj) || loc.nl.n_quotes < 25 || loc.en.n_quotes < 25 || loc.n_tricks != 28) {
        fprintf(stderr, "Failed loading locale %s (nl=%d en=%d tricks=%d)\n",
                lj, loc.nl.n_quotes, loc.en.n_quotes, loc.n_tricks);
        return 1;
    }
    Rgba px[32][32];
    for (int s = 0; s < NUM_SKINS; s++) {
        for (int o = 0; o < NUM_OUTFITS; o++) {
            render_frame_rgba(&sb, "IDLE", 0, SKIN_IDS[s], OUTFIT_IDS[o], px);
        }
    }
    int opaque = 0;
    for (int y = 0; y < 32; y++) {
        for (int x = 0; x < 32; x++) {
            if (px[y][x].a) opaque++;
        }
    }
    char sha[65];
    sha256_hex((const uint8_t *)"abc", 3, sha);
    if (opaque < 50 ||
        strcmp(sha, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") != 0 ||
        compare_ver("2.7.3", KAREL_VERSION) <= 0 ||
        !is_valid_semver(KAREL_VERSION) ||
        is_valid_semver("2.7.0;id")) {
        fprintf(stderr, "Self-check failed\n");
        return 1;
    }
    double tf[3] = {440, 554.37, 659.25};
    uint8_t wb[16384];
    size_t wn = build_wav_bytes(tf, 3, 0.05, 0.2, wb, sizeof(wb));
    SaveStore ss;
    save_load(&ss);
    printf("SELF_TEST_OK version=%s states=%d tricks=%d xp=%d wav=%zu\n",
           KAREL_VERSION, sb.nstates, loc.n_tricks, ss.xp, wn);
    return 0;
}

int main(int argc, char **argv) {
    int self_test = 0, toggle = 0, no_update = 0, ask = 0, no_ask = 0;
    char updated_from[32] = "";
    uint16_t ipc_port = 42421;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--self-test") == 0) self_test = 1;
        else if (strcmp(argv[i], "--no-update") == 0) no_update = 1;
        else if (strcmp(argv[i], "--ask") == 0) ask = 1;
        else if (strcmp(argv[i], "--no-ask") == 0) no_ask = 1;
        else if (strcmp(argv[i], "--toggle") == 0 || strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "t") == 0) toggle = 1;
        else if (strncmp(argv[i], "--updated-from=", 15) == 0) snprintf(updated_from, sizeof(updated_from), "%.31s", argv[i] + 15);
        else if (strncmp(argv[i], "--ipc-port=", 11) == 0) {
            int p = atoi(argv[i] + 11);
            if (p > 0 && p < 65536) ipc_port = (uint16_t)p;
        }
    }

    if (self_test) return run_self_test();

#ifdef KAREL_CORE_TEST
    (void)toggle; (void)no_update; (void)ask; (void)no_ask; (void)ipc_port; (void)updated_from;
    return 0;
#else
    signal(SIGCHLD, SIG_IGN);
    if (try_signal_existing(toggle, ipc_port)) return 0;
    if (toggle) return 0;

    static KarelApp k;
    memset(&k, 0, sizeof(k));
    k.ser.fd = -1;
    k.upd_pipe = -1;
    (void)updated_from;

    char gz[600], lj[600];
    if (!locate_sprites_gz(gz, sizeof(gz)) || !load_sprites_gz(&k.sb, gz)) {
        fprintf(stderr, "Karel: karel_sprites.gz not found.\n");
        return 1;
    }
    if (!locate_locale_json(lj, sizeof(lj)) || !load_locale_json(&k.loc, lj)) {
        fprintf(stderr, "Karel: locale.json not found.\n");
        return 1;
    }
    save_load(&k.save);
    k.scale = clamp_int(k.save.karel_scale, 2, 5);
    srand((unsigned)time(NULL));

    k.dpy = XOpenDisplay(NULL);
    if (!k.dpy) {
        fprintf(stderr, "Error: no X11/XWayland DISPLAY found.\n");
        return 1;
    }
    k.scr = XDefaultScreen(k.dpy);
    k.root = XRootWindow(k.dpy, k.scr);
    k.dpi = get_dpi_scale(k.dpy);
    k.wm_del = XInternAtom(k.dpy, "WM_DELETE_WINDOW", False);
    k.bfont = XLoadQueryFont(k.dpy, "-*-helvetica-bold-r-*-*-14-*-*-*-*-*-*");
    if (!k.bfont) k.bfont = XLoadQueryFont(k.dpy, "fixed");
    k.font = XLoadQueryFont(k.dpy, "-*-fixed-medium-r-*-*-13-*-*-*-*-*-*");
    if (!k.font) k.font = k.bfont;
    (void)no_ask;
    if (ask && !run_ask_prompt(&k)) {
        XCloseDisplay(k.dpy);
        return 0;
    }
    k.ipc_fd = start_ipc_server(ipc_port);

    int wx, wy, ww, wh;
    get_work_area(k.dpy, k.scr, &wx, &wy, &ww, &wh);
    XSetWindowAttributes swa;
    swa.override_redirect = True;
    swa.background_pixel = 0;
    k.wx = wx + ww - win_w(&k) - 40;
    k.wy = wy + wh - (k_oy(&k) + px_sz(&k));
    k.karel_win = XCreateWindow(k.dpy, k.root, (int)k.wx, (int)k.wy, (unsigned)win_w(&k), (unsigned)win_h(&k),
                                0, CopyFromParent, InputOutput, CopyFromParent,
                                CWOverrideRedirect | CWBackPixel, &swa);
    XStoreName(k.dpy, k.karel_win, "Karel de Koala");
    XSelectInput(k.dpy, k.karel_win, ExposureMask | ButtonPressMask | ButtonReleaseMask | PointerMotionMask | KeyPressMask);
    k.karel_gc = XCreateGC(k.dpy, k.karel_win, 0, NULL);
    XMapRaised(k.dpy, k.karel_win);
    (void)no_update;
    trigger_climb(&k, is_en(&k) ? "Karel climbed onto your Linux desktop!" : "Karel klimt je Linux bureaublad op!");

    while (!k.quit_req) {
        handle_x11_events(&k);
        poll_ipc_and_serial(&k);
        step_physics(&k);
        XFlush(k.dpy);
        sleep_ms(62);
    }

    ser_send(&k.ser, "STATE:BYE");
    save_persist(&k.save);
    ser_drop(&k.ser);
    if (k.ipc_fd >= 0) close(k.ipc_fd);
    if (k.upd_pipe >= 0) close(k.upd_pipe);
    close_popup(&k);
    cleanup_sound_dir();
    XCloseDisplay(k.dpy);
    return 0;
#endif
}
