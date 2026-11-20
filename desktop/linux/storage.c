/* Karel de Koala - Persistent SaveStore, USB Discovery, WAV Synth & Asset Locator
 * Handles save.json synchronization across USB and ~/.local/share/karel-de-koala.
 */

#include "../karel_linux.h"

/* =========================================================================
 * General & Level Progression Helpers
 * ========================================================================= */

int xp_for_next_level(int lvl) {
    return lvl <= 0 ? 0 : 180 * lvl * (lvl + 1);
}

int level_from_xp(int xp) {
    int l = 1;
    while (xp >= xp_for_next_level(l)) l++;
    return l;
}

int clamp_int(int v, int lo, int hi) {
    if (v < lo) return lo;
    return v > hi ? hi : v;
}

int file_exists(const char *p) {
    struct stat st;
    return p && *p && stat(p, &st) == 0;
}

/* =========================================================================
 * Minimal JSON Parsing & save.json Persistence
 * ========================================================================= */

static void save_defaults(SaveStore *s) {
    s->hunger = 80;
    s->happiness = 85;
    s->energy = 85;
    s->hygiene = 90;
    s->caffeine = 25;
    s->xp = 0;
    s->level = 1;
    s->total_pets = 0;
    s->karel_scale = 3;
    s->auto_quiet = 1;
    strcpy(s->roam_mode, "free");
    strcpy(s->skin, "classic");
    strcpy(s->equipped, "scarf");
    strcpy(s->language, "nl");
    s->stick_serial[0] = 0;
    s->last_seen[0] = 0;
}

int json_find_str(const char *txt, const char *key, char *out, size_t max_out) {
    char pat[64];
    snprintf(pat, sizeof(pat), "\"%.50s\"", key);
    const char *p = strstr(txt, pat);
    if (!p) return 0;

    p = strchr(p + strlen(pat), ':');
    if (!p) return 0;
    p++;
    while (*p && (*p == ' ' || *p == '\t' || *p == '[' || *p == '\n' || *p == '\r')) p++;
    if (*p != '"') return 0;
    p++;

    const char *q = strchr(p, '"');
    if (!q) return 0;
    size_t n = (size_t)(q - p);
    if (n >= max_out) n = max_out - 1;
    memcpy(out, p, n);
    out[n] = 0;
    return 1;
}

static int json_find_int(const char *txt, const char *key, int *out) {
    char pat[64];
    snprintf(pat, sizeof(pat), "\"%.50s\"", key);
    const char *p = strstr(txt, pat);
    if (!p) return 0;

    p = strchr(p + strlen(pat), ':');
    if (!p) return 0;
    p++;
    while (*p && isspace((unsigned char)*p)) p++;
    if (strncmp(p, "true", 4) == 0) { *out = 1; return 1; }
    if (strncmp(p, "false", 5) == 0) { *out = 0; return 1; }
    if (!isdigit((unsigned char)*p) && *p != '-') return 0;
    *out = atoi(p);
    return 1;
}

static time_t parse_iso_local(const char *s) {
    if (!s || strlen(s) < 19) return 0;
    struct tm t;
    memset(&t, 0, sizeof(t));
    t.tm_isdst = -1;
    if (sscanf(s, "%d-%d-%dT%d:%d:%d", &t.tm_year, &t.tm_mon, &t.tm_mday,
               &t.tm_hour, &t.tm_min, &t.tm_sec) != 6) {
        return 0;
    }
    t.tm_year -= 1900;
    t.tm_mon -= 1;
    return mktime(&t);
}

static int read_save_file(const char *path, SaveStore *out) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return 0;
    char buf[8192];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    fclose(fp);
    if (n < 2) return 0;

    size_t off = (n >= 3 && (unsigned char)buf[0] == 0xEF &&
                  (unsigned char)buf[1] == 0xBB && (unsigned char)buf[2] == 0xBF) ? 3 : 0;
    for (size_t i = off; i < n; i++) {
        unsigned char c = (unsigned char)buf[i];
        if (c == 0xFF || c == 0x00) return 0;
    }
    buf[n] = 0;
    const char *jb = buf + off;
    if (!strchr(jb, '{') || !strchr(jb, '}')) return 0;

    save_defaults(out);
    json_find_int(jb, "hunger", &out->hunger);
    json_find_int(jb, "happiness", &out->happiness);
    json_find_int(jb, "energy", &out->energy);
    json_find_int(jb, "hygiene", &out->hygiene);
    json_find_int(jb, "caffeine", &out->caffeine);
    json_find_int(jb, "xp", &out->xp);
    json_find_int(jb, "total_pets", &out->total_pets);
    json_find_int(jb, "karel_scale", &out->karel_scale);
    json_find_int(jb, "auto_quiet_fullscreen", &out->auto_quiet);
    json_find_str(jb, "roam_mode", out->roam_mode, sizeof(out->roam_mode));
    json_find_str(jb, "skin", out->skin, sizeof(out->skin));
    if (!json_find_str(jb, "equipped", out->equipped, sizeof(out->equipped))) {
        const char *ep = strstr(jb, "\"equipped\"");
        if (ep && strstr(ep, "[]")) out->equipped[0] = 0;
    }
    json_find_str(jb, "language", out->language, sizeof(out->language));
    json_find_str(jb, "stick_serial", out->stick_serial, sizeof(out->stick_serial));
    json_find_str(jb, "last_seen", out->last_seen, sizeof(out->last_seen));
    return 1;
}

static void get_volume_serial(const char *root, char out[32]) {
    out[0] = 0;
#ifndef KAREL_CORE_TEST
    if (!root || !*root) return;
    struct statvfs sv;
    if (statvfs(root, &sv) == 0 && sv.f_fsid != 0) {
        snprintf(out, 32, "%08lX", (unsigned long)(sv.f_fsid & 0xFFFFFFFFUL));
    }
#else
    (void)root;
#endif
}

static void find_usb_drive(char *out, size_t max_out) {
    out[0] = 0;
    const char *env = getenv("KAREL_DRIVE_DIR");
    if (env && *env) {
        char m[600];
        snprintf(m, sizeof(m), "%.500s/.karel_drive", env);
        if (file_exists(m) && strlen(env) < max_out) {
            memcpy(out, env, strlen(env) + 1);
            return;
        }
    }

    char bases[4][512];
    const char *usr = getenv("USER");
    snprintf(bases[0], 512, "/media/%.200s", usr ? usr : "root");
    snprintf(bases[1], 512, "/run/media/%.200s", usr ? usr : "root");
    strcpy(bases[2], "/media");
    strcpy(bases[3], "/mnt");

    for (int bi = 0; bi < 4; bi++) {
        DIR *dp = opendir(bases[bi]);
        if (!dp) continue;
        struct dirent *de;
        while ((de = readdir(dp)) != NULL) {
            if (de->d_name[0] == '.') continue;
            char cand[1024], mrk[1040];
            snprintf(cand, sizeof(cand), "%.500s/%.250s", bases[bi], de->d_name);
            snprintf(mrk, sizeof(mrk), "%s/.karel_drive", cand);
            if (file_exists(mrk) && strlen(cand) < max_out) {
                memcpy(out, cand, strlen(cand) + 1);
                closedir(dp);
                return;
            }
        }
        closedir(dp);
    }
}

static void save_write_one(const char *path, const SaveStore *s, int direct) {
    char tmp[600];
    const char *target = path;
    if (!direct) {
        snprintf(tmp, sizeof(tmp), "%.580s.tmp", path);
        target = tmp;
    }
    FILE *fp = fopen(target, "wb");
    if (!fp) return;

    fprintf(fp,
        "{\n  \"name\": \"Karel\",\n"
        "  \"hunger\": %d,\n  \"happiness\": %d,\n  \"energy\": %d,\n  \"hygiene\": %d,\n  \"caffeine\": %d,\n"
        "  \"xp\": %d,\n  \"level\": %d,\n  \"total_pets\": %d,\n"
        "  \"skin\": \"%s\",\n  \"equipped\": %s%s%s,\n"
        "  \"roam_mode\": \"%s\",\n  \"karel_scale\": %d,\n  \"auto_quiet_fullscreen\": %s,\n"
        "  \"language\": \"%s\",\n  \"stick_serial\": \"%s\",\n  \"last_seen\": \"%s\"\n}\n",
        s->hunger, s->happiness, s->energy, s->hygiene, s->caffeine,
        s->xp, s->level, s->total_pets,
        s->skin,
        *s->equipped ? "[\"" : "[",
        *s->equipped ? s->equipped : "",
        *s->equipped ? "\"]" : "]",
        s->roam_mode, s->karel_scale, s->auto_quiet ? "true" : "false",
        s->language, s->stick_serial, s->last_seen);
    fflush(fp);
#if !defined(_WIN32) && !defined(KAREL_CORE_TEST)
    fsync(fileno(fp));
#endif
    fclose(fp);
    if (!direct) rename(tmp, path);
}

void save_persist(SaveStore *s) {
    if (s->connected && !*s->stick_serial) {
        get_volume_serial(s->drive_root, s->stick_serial);
    }
    time_t now = time(NULL);
    struct tm *lt = localtime(&now);
    if (lt) {
        strftime(s->last_seen, sizeof(s->last_seen), "%Y-%m-%dT%H:%M:%S", lt);
    }
    if (*s->fallback_path) {
        save_write_one(s->fallback_path, s, 0);
    }
    if (s->connected && *s->drive_root) {
        char usb_p[600];
        snprintf(usb_p, sizeof(usb_p), "%.500s/save.json", s->drive_root);
        save_write_one(usb_p, s, 1);
    }
}

void save_load(SaveStore *s) {
    save_defaults(s);
    const char *home = getenv("HOME");
    if (home) {
        char d[512];
        snprintf(d, sizeof(d), "%.480s/.local/share/karel-de-koala", home);
#ifndef _WIN32
        mkdir(d, 0755);
#endif
        snprintf(s->fallback_path, sizeof(s->fallback_path), "%s/save.json", d);
    } else {
        s->fallback_path[0] = 0;
    }

    find_usb_drive(s->drive_root, sizeof(s->drive_root));
    s->connected = (*s->drive_root != 0);
    char cur_ser[32];
    get_volume_serial(s->drive_root, cur_ser);

    SaveStore u, f;
    int has_u = 0, has_f = 0;
    if (s->connected) {
        char up[600];
        snprintf(up, sizeof(up), "%.500s/save.json", s->drive_root);
        has_u = read_save_file(up, &u);
    }
    if (*s->fallback_path) {
        has_f = read_save_file(s->fallback_path, &f);
    }

    int recover_fb = 0;
    if (has_u && has_f) {
        const char *u_ser = *u.stick_serial ? u.stick_serial : cur_ser;
        time_t tu = parse_iso_local(u.last_seen), tf = parse_iso_local(f.last_seen);
        if (*f.stick_serial && *u_ser && strcmp(u_ser, f.stick_serial) == 0 &&
            (tf > tu || (tf == tu && f.xp > u.xp))) {
            *s = f;
            recover_fb = 1;
        } else {
            *s = u;
        }
    } else if (has_u) {
        *s = u;
    } else if (has_f && (!s->connected || (*cur_ser && strcmp(f.stick_serial, cur_ser) == 0))) {
        *s = f;
        recover_fb = s->connected;
    }

    find_usb_drive(s->drive_root, sizeof(s->drive_root));
    s->connected = (*s->drive_root != 0);
    if (home) {
        snprintf(s->fallback_path, sizeof(s->fallback_path), "%.480s/.local/share/karel-de-koala/save.json", home);
    }

    /* Apply gentle offline stat decay based on elapsed hours since last_seen. */
    time_t prev = parse_iso_local(s->last_seen);
    if (prev > 0) {
        double hrs = difftime(time(NULL), prev) / 3600.0;
        if (hrs > 0.05) {
            s->hunger = clamp_int((int)llround(s->hunger - hrs * 0.9), 15, 100);
            s->happiness = clamp_int((int)llround(s->happiness - hrs * 0.6), 25, 100);
            s->hygiene = clamp_int((int)llround(s->hygiene - hrs * 0.4), 25, 100);
            s->caffeine = clamp_int((int)llround(s->caffeine - hrs * 4.0), 0, 100);
            if (hrs >= 1.0) s->energy = clamp_int((int)llround(s->energy + hrs * 6.0), 0, 100);
        }
    }
    s->level = level_from_xp(s->xp);
    if (*cur_ser) snprintf(s->stick_serial, sizeof(s->stick_serial), "%.31s", cur_ser);
    if (recover_fb) save_persist(s);
}

#ifndef KAREL_CORE_TEST
int poll_usb(SaveStore *s) {
    int was = s->connected;
    find_usb_drive(s->drive_root, sizeof(s->drive_root));
    s->connected = (*s->drive_root != 0);
    if (!was && s->connected) return 1;
    if (was && !s->connected) return -1;
    return 0;
}
#endif

/* =========================================================================
 * In-Memory WAV Synthesizer & Shared Sprite Archive Locator
 * ========================================================================= */

size_t build_wav_bytes(const double *freqs, int nfreq, double dur, double amp, uint8_t *buf, size_t maxb) {
    const int sr = 22050;
    int nper = (int)(dur * sr);
    if (nper < 100) nper = 100;
    int total = nper * nfreq;
    size_t need = 44 + (size_t)total * 2;
    if (need > maxb) return 0;

    uint32_t db = (uint32_t)(total * 2), rsz = 36 + db, fmt = 16, br = sr * 2, usr = sr;
    uint16_t pcm = 1, ch = 1, ba = 2, bps = 16;
    memcpy(buf, "RIFF", 4);
    memcpy(buf + 4, &rsz, 4);
    memcpy(buf + 8, "WAVEfmt ", 8);
    memcpy(buf + 16, &fmt, 4);
    memcpy(buf + 20, &pcm, 2);
    memcpy(buf + 22, &ch, 2);
    memcpy(buf + 24, &usr, 4);
    memcpy(buf + 28, &br, 4);
    memcpy(buf + 32, &ba, 2);
    memcpy(buf + 34, &bps, 2);
    memcpy(buf + 36, "data", 4);
    memcpy(buf + 40, &db, 4);

    int16_t *samples = (int16_t *)(buf + 44);
    for (int fi = 0; fi < nfreq; fi++) {
        double f = freqs[fi], ph = 0.0;
        for (int i = 0; i < nper; i++) {
            double e1 = i < 120 ? i / 120.0 : 1.0;
            double e2 = (nper - i) < 220 ? (nper - i) / 220.0 : 1.0;
            double v = (sin(ph) + 0.28 * sin(2.0 * ph)) * (e1 < e2 ? e1 : e2) * amp * 24000.0;
            samples[fi * nper + i] = (int16_t)(v > 32767.0 ? 32767 : (v < -32767.0 ? -32767 : v));
            ph += 6.28318530718 * f / sr;
        }
    }
    return need;
}

static int locate_asset_file(const char *fname, char *out, size_t max_out) {
    const char *env = getenv("KAREL_DRIVE_DIR");
    char envp[600], c1[128], c2[160], c3[160];
    snprintf(c1, sizeof(c1), "%.100s", fname);
    snprintf(c2, sizeof(c2), "desktop/%.100s", fname);
    snprintf(c3, sizeof(c3), "../desktop/%.100s", fname);
    const char *cands[4] = { NULL, c1, c2, c3 };
    if (env && *env) {
        snprintf(envp, sizeof(envp), "%.500s/%.80s", env, fname);
        cands[0] = envp;
    }
    for (int i = 0; i < 4; i++) {
        if (cands[i] && file_exists(cands[i])) {
            snprintf(out, max_out, "%.550s", cands[i]);
            return 1;
        }
    }
#ifndef KAREL_CORE_TEST
    char exe[512];
    ssize_t el = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
    if (el > 0) {
        exe[el] = 0;
        char *sl = strrchr(exe, '/');
        if (sl) {
            *sl = 0;
            snprintf(out, max_out, "%.460s/%.80s", exe, fname);
            if (file_exists(out)) return 1;
        }
    }
#endif
    return 0;
}

int locate_sprites_gz(char *out, size_t max_out) {
    return locate_asset_file("karel_sprites.gz", out, max_out);
}

int locate_locale_json(char *out, size_t max_out) {
    return locate_asset_file("locale.json", out, max_out);
}

/* =========================================================================
 * Centralized Bilingual Locale Loader (desktop/locale.json)
 * ========================================================================= */

static const char *json_read_quoted(const char *p, char *out, size_t max_out) {
    while (*p && isspace((unsigned char)*p)) p++;
    if (*p != '"') return NULL;
    p++;
    size_t n = 0;
    while (*p && *p != '"') {
        if (*p == '\\' && p[1]) {
            p++;
            char c = *p++;
            if (c == 'n') c = '\n';
            else if (c == 't') c = '\t';
            if (n + 1 < max_out) out[n++] = c;
        } else {
            if (n + 1 < max_out) out[n++] = *p;
            p++;
        }
    }
    if (*p != '"') return NULL;
    out[n] = 0;
    return p + 1;
}

static const char *json_find_block(const char *start, const char *end, const char *key, char open_ch, char close_ch, const char **out_end) {
    char pat[64];
    snprintf(pat, sizeof(pat), "\"%.50s\"", key);
    const char *p = start;
    while (p && p < end && (p = strstr(p, pat)) != NULL && p < end) {
        p += strlen(pat);
        while (p < end && isspace((unsigned char)*p)) p++;
        if (p < end && *p == ':') {
            p++;
            while (p < end && isspace((unsigned char)*p)) p++;
            if (p < end && *p == open_ch) {
                const char *b_start = p + 1;
                int depth = 1, in_str = 0;
                p++;
                while (p < end && depth > 0) {
                    if (*p == '\\' && in_str && p + 1 < end) { p += 2; continue; }
                    if (*p == '"') in_str = !in_str;
                    else if (!in_str) {
                        if (*p == open_ch) depth++;
                        else if (*p == close_ch) depth--;
                    }
                    p++;
                }
                if (depth == 0) {
                    *out_end = p - 1;
                    return b_start;
                }
            }
        }
    }
    return NULL;
}

static int parse_str_array(const char *blk, const char *blk_end, const char *key, void *arr_base, int max_items, size_t stride) {
    const char *a_end = NULL;
    const char *p = json_find_block(blk, blk_end, key, '[', ']', &a_end);
    if (!p) return 0;
    int count = 0;
    char *dst = (char *)arr_base;
    while (p < a_end && count < max_items) {
        while (p < a_end && (isspace((unsigned char)*p) || *p == ',')) p++;
        if (p >= a_end || *p != '"') break;
        p = json_read_quoted(p, dst + (size_t)count * stride, stride);
        if (!p) break;
        count++;
    }
    return count;
}

static int parse_str_map(const char *blk, const char *blk_end, const char *key,
                         void *keys_base, size_t key_stride, void *vals_base, size_t val_stride, int max_items) {
    const char *o_end = NULL;
    const char *p = json_find_block(blk, blk_end, key, '{', '}', &o_end);
    int count = 0;
    char *kdst = (char *)keys_base, *vdst = (char *)vals_base;
    while (p && p < o_end && count < max_items) {
        while (p < o_end && (isspace((unsigned char)*p) || *p == ',')) p++;
        if (p >= o_end || *p != '"') break;
        p = json_read_quoted(p, kdst + (size_t)count * key_stride, key_stride);
        if (!p) break;
        while (p < o_end && (isspace((unsigned char)*p) || *p == ':')) p++;
        p = json_read_quoted(p, vdst + (size_t)count * val_stride, val_stride);
        if (!p) break;
        count++;
    }
    return count;
}

static void parse_locale_set(const char *blk, const char *blk_end, LocaleSet *ls) {
    ls->n_quotes    = parse_str_array(blk, blk_end, "quotes",       ls->quotes,       40, sizeof(ls->quotes[0]));
    ls->n_morning   = parse_str_array(blk, blk_end, "morning",      ls->morning,       8, sizeof(ls->morning[0]));
    ls->n_night     = parse_str_array(blk, blk_end, "night",        ls->night,         8, sizeof(ls->night[0]));
    ls->n_friday    = parse_str_array(blk, blk_end, "friday",       ls->friday,        8, sizeof(ls->friday[0]));
    ls->n_pet       = parse_str_array(blk, blk_end, "pet",          ls->pet,           8, sizeof(ls->pet[0]));
    ls->n_feed      = parse_str_array(blk, blk_end, "feed",         ls->feed,          8, sizeof(ls->feed[0]));
    ls->n_coffee    = parse_str_array(blk, blk_end, "coffee",       ls->coffee,        8, sizeof(ls->coffee[0]));
    ls->n_wash      = parse_str_array(blk, blk_end, "wash",         ls->wash,          8, sizeof(ls->wash[0]));
    ls->n_toss_soft = parse_str_array(blk, blk_end, "toss_soft",    ls->toss_soft,     6, sizeof(ls->toss_soft[0]));
    ls->n_toss_hard = parse_str_array(blk, blk_end, "toss_hard",    ls->toss_hard,     6, sizeof(ls->toss_hard[0]));
    ls->n_levels    = parse_str_array(blk, blk_end, "level_titles", ls->level_titles, 12, sizeof(ls->level_titles[0]));
    ls->n_outfits   = parse_str_map(blk, blk_end, "outfit_quotes",
                                    ls->outfit_keys, sizeof(ls->outfit_keys[0]),
                                    ls->outfit_vals, sizeof(ls->outfit_vals[0]), 20);
    ls->n_ui        = parse_str_map(blk, blk_end, "ui",
                                    ls->ui_keys, sizeof(ls->ui_keys[0]),
                                    ls->ui_vals, sizeof(ls->ui_vals[0]), 120);
}

int load_locale_json(LocaleStore *loc, const char *path) {
    memset(loc, 0, sizeof(*loc));
    FILE *fp = fopen(path, "rb");
    if (!fp) return 0;
    char *buf = (char *)malloc(32768);
    if (!buf) { fclose(fp); return 0; }
    size_t n = fread(buf, 1, 32767, fp);
    fclose(fp);
    buf[n] = 0;
    const char *end = buf + n;

    const char *nl_end = NULL, *en_end = NULL, *tr_end = NULL;
    const char *nl_blk = json_find_block(buf, end, "nl", '{', '}', &nl_end);
    const char *en_blk = json_find_block(buf, end, "en", '{', '}', &en_end);
    const char *tr_blk = json_find_block(buf, end, "tricks", '[', ']', &tr_end);
    if (nl_blk) parse_locale_set(nl_blk, nl_end, &loc->nl);
    if (en_blk) parse_locale_set(en_blk, en_end, &loc->en);

    const char *p = tr_blk;
    while (p && p < tr_end && loc->n_tricks < 32) {
        const char *obj = strchr(p, '{');
        if (!obj || obj >= tr_end) break;
        const char *obj_end = strchr(obj, '}');
        if (!obj_end || obj_end > tr_end) break;
        char sub[384];
        size_t sl = (size_t)(obj_end - obj + 1);
        if (sl >= sizeof(sub)) sl = sizeof(sub) - 1;
        memcpy(sub, obj, sl);
        sub[sl] = 0;
        TrickDef *td = &loc->tricks[loc->n_tricks];
        if (json_find_str(sub, "label", td->lbl, sizeof(td->lbl)) &&
            json_find_str(sub, "state", td->st, sizeof(td->st)) &&
            json_find_str(sub, "msg", td->msg, sizeof(td->msg))) {
            loc->n_tricks++;
        }
        p = obj_end + 1;
    }

    free(buf);
    return (loc->nl.n_quotes > 0 && loc->en.n_quotes > 0 && loc->n_tricks > 0) ? 1 : 0;
}
