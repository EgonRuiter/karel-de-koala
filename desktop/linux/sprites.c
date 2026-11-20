/* Karel de Koala - Sprite Bank Loader, Coat Recoloring & Outfit Overlay Renderer
 * Reads compressed karel_sprites.gz and renders 32x32 RGBA pixel frames.
 */

#include "../karel_linux.h"

const char *SKIN_IDS[NUM_SKINS] = {
    "classic", "sticky", "mint", "midnight", "gold", "crimson",
    "sakura", "ocean", "sunset", "espresso", "cyber", "forest", "snow", "obsidian"
};

const char *OUTFIT_IDS[NUM_OUTFITS] = {
    "scarf", "stickycap", "hoodie", "headphones", "shades", "crown", "wizard", "partyhat",
    "beanie", "tophat", "chef", "halo", "bowtie", "cape", "labcoat", "nerd", ""
};

/* =========================================================================
 * Sprite Bank Parsing
 * ========================================================================= */

static int find_state_idx(const SpriteBank *sb, const char *st) {
    for (int i = 0; i < sb->nstates; i++) {
        if (strcmp(sb->states[i].name, st) == 0) return i;
    }
    return -1;
}

static int ensure_state(SpriteBank *sb, const char *name) {
    int idx = find_state_idx(sb, name);
    if (idx >= 0 || sb->nstates >= MAX_STATES) return idx;
    idx = sb->nstates++;
    snprintf(sb->states[idx].name, sizeof(sb->states[idx].name), "%.31s", name);
    sb->states[idx].div = 2;
    return idx;
}

static int parse_hex2(const char *s) {
    int v = 0;
    for (int i = 0; i < 2; i++) {
        char c = s[i];
        v <<= 4;
        if (c >= '0' && c <= '9') v |= c - '0';
        else if (c >= 'a' && c <= 'f') v |= c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') v |= c - 'A' + 10;
    }
    return v;
}

static void parse_palette_line(SpriteBank *sb, char *q) {
    while (*q) {
        char *comma = strchr(q, ',');
        if (comma) *comma = 0;
        if (strlen(q) == 9 && q[1] == ':' && q[2] == '#') {
            unsigned char ch = (unsigned char)q[0];
            if (ch < 128) {
                sb->pal[ch] = (Rgba){
                    (uint8_t)parse_hex2(q + 3),
                    (uint8_t)parse_hex2(q + 5),
                    (uint8_t)parse_hex2(q + 7),
                    255
                };
            }
        }
        if (!comma) break;
        q = comma + 1;
    }
}

static void parse_div_line(SpriteBank *sb, char *q) {
    while (*q) {
        char *comma = strchr(q, ',');
        if (comma) *comma = 0;
        char *eq = strchr(q, '=');
        if (eq) {
            *eq = 0;
            int idx = ensure_state(sb, q);
            if (idx >= 0) sb->states[idx].div = atoi(eq + 1);
        }
        if (!comma) break;
        q = comma + 1;
    }
}

static void parse_anchor_line(SpriteBank *sb, char *body) {
    char *eq = strchr(body, '=');
    if (!eq) return;
    *eq = 0;
    int idx = ensure_state(sb, body);
    if (idx < 0) return;

    char *q = eq + 1;
    int fi = 0;
    while (*q && fi < MAX_FRAMES) {
        char *semi = strchr(q, ';');
        if (semi) *semi = 0;
        int hx = 0, hy = 0, tx = 0, ty = 0;
        if (sscanf(q, "%d,%d,%d,%d", &hx, &hy, &tx, &ty) == 4) {
            sb->states[idx].anc[fi][0] = (int8_t)hx;
            sb->states[idx].anc[fi][1] = (int8_t)hy;
            sb->states[idx].anc[fi][2] = (int8_t)tx;
            sb->states[idx].anc[fi][3] = (int8_t)ty;
        }
        fi++;
        if (!semi) break;
        q = semi + 1;
    }
}

int load_sprites_gz(SpriteBank *sb, const char *path) {
    memset(sb, 0, sizeof(*sb));
    FILE *fp = fopen(path, "rb");
    if (!fp) return 0;

    fseek(fp, 0, SEEK_END);
    long fsz = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    if (fsz <= 0 || fsz > 1024 * 1024) { fclose(fp); return 0; }

    uint8_t *comp = (uint8_t *)malloc((size_t)fsz);
    if (!comp || fread(comp, 1, (size_t)fsz, fp) != (size_t)fsz) {
        free(comp);
        fclose(fp);
        return 0;
    }
    fclose(fp);

    size_t raw_len = 0;
    uint8_t *raw = inflate_gzip(comp, (size_t)fsz, &raw_len);
    free(comp);
    if (!raw) return 0;

    int cur_st = -1, cur_row = 0;
    char *p = (char *)raw, *end = (char *)raw + raw_len;
    while (p < end) {
        char *nl = strchr(p, '\n');
        if (!nl) nl = end;
        *nl = 0;
        size_t l = strlen(p);
        if (l > 0 && p[l - 1] == '\r') p[--l] = 0;

        if (strncmp(p, "PAL|", 4) == 0) {
            parse_palette_line(sb, p + 4);
        } else if (strncmp(p, "DIV|", 4) == 0) {
            parse_div_line(sb, p + 4);
        } else if (strncmp(p, "ANC|", 4) == 0) {
            parse_anchor_line(sb, p + 4);
        } else if (p[0] == '@') {
            cur_st = ensure_state(sb, p + 1);
            cur_row = 0;
            if (cur_st >= 0 && sb->states[cur_st].nframes == 0) {
                sb->states[cur_st].nframes = 1;
            }
        } else if (strcmp(p, "---") == 0) {
            if (cur_st >= 0 && sb->states[cur_st].nframes < MAX_FRAMES) {
                sb->states[cur_st].nframes++;
                cur_row = 0;
            }
        } else if (cur_st >= 0 && l > 0 && cur_row < 32) {
            int fi = sb->states[cur_st].nframes - 1;
            strncpy(sb->states[cur_st].rows[fi][cur_row], p, 32);
            sb->states[cur_st].rows[fi][cur_row][32] = 0;
            cur_row++;
        }
        p = nl + 1;
    }

    free(raw);
    return sb->nstates > 0;
}

/* =========================================================================
 * Table-Driven Coat Mapping & Outfit Overlay Drawing
 * ========================================================================= */

static char map_skin(const char *skin, char ch) {
    /* Remap base gray ('g'), shadow ('s'), and highlight ('w') tokens per coat. */
    static const struct {
        const char *name;
        char g, s, w;
    } tbl[] = {
        {"sticky",   'r', 'R', 'W'},
        {"mint",     'n', 'e', 'W'},
        {"midnight", 'm', 'k', 'b'},
        {"gold",     'y', 'Y', 'W'},
        {"crimson",  'R', 'r', 'y'},
        {"sakura",   'p', 'v', 'P'},
        {"ocean",    'b', 'A', 'u'},
        {"sunset",   'o', 'f', 't'},
        {"espresso", 'h', 'H', 't'},
        {"cyber",    'd', 'k', 'a'},
        {"forest",   'e', 'E', 'l'},
        {"snow",     'W', 'w', 'u'},
        {"obsidian", 'd', 'k', 'W'},
    };
    for (size_t i = 0; i < sizeof(tbl) / sizeof(tbl[0]); i++) {
        if (strcmp(skin, tbl[i].name) == 0) {
            if (ch == 'g') return tbl[i].g;
            if (ch == 's') return tbl[i].s;
            if (ch == 'w') return tbl[i].w;
            return ch;
        }
    }
    return ch;
}

static void g_rect(char g[32][32], int dx, int dy, int x0, int y0, int x1, int y1, char ch) {
    int ly = y0 + dy < 0 ? 0 : y0 + dy;
    int hy = y1 + dy > 31 ? 31 : y1 + dy;
    int lx = x0 + dx < 0 ? 0 : x0 + dx;
    int hx = x1 + dx > 31 ? 31 : x1 + dx;
    for (int y = ly; y <= hy; y++) {
        for (int x = lx; x <= hx; x++) g[y][x] = ch;
    }
}

static void g_px(char g[32][32], int dx, int dy, int x, int y, char ch) {
    int nx = x + dx, ny = y + dy;
    if (nx >= 0 && nx < 32 && ny >= 0 && ny < 32) g[ny][nx] = ch;
}

static void apply_outfit_overlay(char g[32][32], const char *item, int hx, int hy, int tx, int ty) {
    /* Anchor coordinate 99 marks that side/back/sleeping frames omit overlays. */
    int draw_h = (hx != 99), draw_t = (tx != 99);

    if (strcmp(item, "scarf") == 0 && draw_t) {
        g_rect(g, tx, ty, 9, 17, 22, 18, 'r');
        g_px(g, tx, ty, 9, 17, 'k'); g_px(g, tx, ty, 22, 17, 'k');
        for (int x = 11; x <= 20; x += 3) g_px(g, tx, ty, x, 17, 'W');
        for (int x = 10; x <= 21; x += 3) g_px(g, tx, ty, x, 18, 'R');
        g_rect(g, tx, ty, 17, 19, 19, 22, 'r');
        g_px(g, tx, ty, 18, 20, 'W'); g_px(g, tx, ty, 17, 21, 'R'); g_px(g, tx, ty, 19, 21, 'R');
        g_px(g, tx, ty, 17, 23, 'W'); g_px(g, tx, ty, 19, 23, 'W');
    } else if (strcmp(item, "stickycap") == 0 && draw_h) {
        g_rect(g, hx, hy, 11, 1, 20, 1, 'k');
        g_rect(g, hx, hy, 10, 2, 21, 4, 'r');
        g_px(g, hx, hy, 10, 2, 'k'); g_px(g, hx, hy, 21, 2, 'k');
        g_rect(g, hx, hy, 9, 5, 18, 5, 'k');
        g_rect(g, hx, hy, 19, 5, 25, 5, 'R'); g_px(g, hx, hy, 25, 5, 'k');
        g_px(g, hx, hy, 15, 3, 'W'); g_px(g, hx, hy, 16, 3, 'W'); g_px(g, hx, hy, 15, 4, 'W');
    } else if (strcmp(item, "hoodie") == 0 && draw_t) {
        g_rect(g, tx, ty, 9, 17, 22, 18, 'R');
        g_rect(g, tx, ty, 10, 18, 21, 24, 'r');
        g_rect(g, tx, ty, 7, 19, 9, 22, 'r'); g_rect(g, tx, ty, 22, 19, 24, 22, 'r');
        g_px(g, tx, ty, 7, 22, 'R'); g_px(g, tx, ty, 24, 22, 'R');
        g_rect(g, tx, ty, 13, 21, 18, 23, 'R');
        g_rect(g, tx, ty, 10, 24, 21, 24, 'R');
        g_px(g, tx, ty, 14, 19, 'W'); g_px(g, tx, ty, 14, 20, 'W');
        g_px(g, tx, ty, 17, 19, 'W'); g_px(g, tx, ty, 17, 20, 'W');
    } else if (strcmp(item, "headphones") == 0 && draw_h) {
        g_rect(g, hx, hy, 8, 3, 23, 3, 's'); g_rect(g, hx, hy, 7, 4, 24, 4, 'd');
        g_px(g, hx, hy, 5, 6, 'd'); g_px(g, hx, hy, 6, 5, 'd'); g_px(g, hx, hy, 25, 5, 'd'); g_px(g, hx, hy, 26, 6, 'd');
        g_rect(g, hx, hy, 2, 7, 4, 11, 'k'); g_rect(g, hx, hy, 27, 7, 29, 11, 'k');
        g_rect(g, hx, hy, 3, 8, 4, 10, 'r'); g_rect(g, hx, hy, 27, 8, 28, 10, 'r');
        g_px(g, hx, hy, 5, 8, 'w'); g_px(g, hx, hy, 5, 9, 'w'); g_px(g, hx, hy, 5, 10, 'w');
        g_px(g, hx, hy, 26, 8, 'w'); g_px(g, hx, hy, 26, 9, 'w'); g_px(g, hx, hy, 26, 10, 'w');
    } else if (strcmp(item, "shades") == 0 && draw_h) {
        g_rect(g, hx, hy, 9, 10, 14, 12, 'k'); g_rect(g, hx, hy, 17, 10, 22, 12, 'k');
        g_rect(g, hx, hy, 10, 11, 13, 12, 'd'); g_rect(g, hx, hy, 18, 11, 21, 12, 'd');
        g_rect(g, hx, hy, 14, 10, 17, 10, 'k'); g_px(g, hx, hy, 8, 10, 'k'); g_px(g, hx, hy, 23, 10, 'k');
        g_px(g, hx, hy, 10, 11, 'W'); g_px(g, hx, hy, 11, 11, 'W');
        g_px(g, hx, hy, 18, 11, 'W'); g_px(g, hx, hy, 19, 11, 'W');
    } else if (strcmp(item, "crown") == 0 && draw_h) {
        g_rect(g, hx, hy, 11, 5, 20, 5, 'k'); g_rect(g, hx, hy, 11, 3, 20, 4, 'y');
        g_px(g, hx, hy, 11, 1, 'y'); g_px(g, hx, hy, 11, 2, 'y');
        g_px(g, hx, hy, 15, 1, 'y'); g_px(g, hx, hy, 16, 1, 'y'); g_px(g, hx, hy, 15, 2, 'y'); g_px(g, hx, hy, 16, 2, 'y');
        g_px(g, hx, hy, 20, 1, 'y'); g_px(g, hx, hy, 20, 2, 'y');
        g_px(g, hx, hy, 13, 3, 'Y'); g_px(g, hx, hy, 18, 3, 'Y');
        g_px(g, hx, hy, 15, 4, 'R'); g_px(g, hx, hy, 16, 4, 'R');
        g_px(g, hx, hy, 12, 4, 'b'); g_px(g, hx, hy, 19, 4, 'b');
    } else if (strcmp(item, "wizard") == 0 && draw_h) {
        g_rect(g, hx, hy, 8, 5, 23, 5, 'k');
        g_rect(g, hx, hy, 9, 4, 22, 4, 'm'); g_rect(g, hx, hy, 11, 4, 20, 4, 'y');
        g_rect(g, hx, hy, 12, 2, 19, 3, 'm'); g_rect(g, hx, hy, 14, 0, 17, 1, 'm');
        g_px(g, hx, hy, 18, 0, 'm'); g_px(g, hx, hy, 15, 2, 'y'); g_px(g, hx, hy, 16, 1, 'W');
    } else if (strcmp(item, "partyhat") == 0 && draw_h) {
        g_rect(g, hx, hy, 12, 5, 19, 5, 'k');
        g_rect(g, hx, hy, 13, 3, 18, 4, 'm'); g_rect(g, hx, hy, 14, 1, 17, 2, 'R');
        g_px(g, hx, hy, 15, 0, 'y'); g_px(g, hx, hy, 16, 0, 'W');
        g_px(g, hx, hy, 14, 4, 'y'); g_px(g, hx, hy, 17, 4, 'b'); g_px(g, hx, hy, 15, 2, 'y');
    } else if (strcmp(item, "beanie") == 0 && draw_h) {
        g_rect(g, hx, hy, 11, 1, 20, 4, 'r'); g_rect(g, hx, hy, 12, 1, 19, 1, 'k');
        g_px(g, hx, hy, 11, 1, '.'); g_px(g, hx, hy, 20, 1, '.');
        g_rect(g, hx, hy, 10, 4, 21, 5, 'R'); g_px(g, hx, hy, 10, 5, 'k'); g_px(g, hx, hy, 21, 5, 'k');
        for (int x = 11; x <= 20; x += 2) g_px(g, hx, hy, x, 5, 'S');
        g_rect(g, hx, hy, 15, 0, 16, 1, 'W'); g_px(g, hx, hy, 14, 0, 'w'); g_px(g, hx, hy, 17, 0, 'w');
    } else if (strcmp(item, "tophat") == 0 && draw_h) {
        g_rect(g, hx, hy, 9, 5, 22, 5, 'k');
        g_rect(g, hx, hy, 11, 0, 20, 4, 'k'); g_rect(g, hx, hy, 12, 1, 19, 3, 'd');
        g_rect(g, hx, hy, 12, 4, 19, 4, 'r'); g_px(g, hx, hy, 13, 1, 's'); g_px(g, hx, hy, 13, 2, 's');
    } else if (strcmp(item, "chef") == 0 && draw_h) {
        g_rect(g, hx, hy, 11, 5, 20, 5, 'k'); g_rect(g, hx, hy, 11, 4, 20, 4, 'r');
        g_rect(g, hx, hy, 10, 1, 21, 3, 'W'); g_rect(g, hx, hy, 12, 0, 19, 1, 'W');
        g_px(g, hx, hy, 10, 1, 'w'); g_px(g, hx, hy, 21, 1, 'w'); g_px(g, hx, hy, 14, 1, 'w'); g_px(g, hx, hy, 17, 1, 'w');
        g_px(g, hx, hy, 14, 2, 'w'); g_px(g, hx, hy, 17, 2, 'w'); g_rect(g, hx, hy, 11, 3, 20, 3, 'w');
    } else if (strcmp(item, "halo") == 0 && draw_h) {
        g_rect(g, hx, hy, 11, 1, 20, 1, 'y'); g_rect(g, hx, hy, 10, 2, 21, 2, 'Y');
        g_rect(g, hx, hy, 12, 2, 19, 2, '.'); g_rect(g, hx, hy, 11, 3, 20, 3, 'y');
        g_px(g, hx, hy, 12, 1, 'W'); g_px(g, hx, hy, 13, 1, 't'); g_px(g, hx, hy, 19, 1, 't');
    } else if (strcmp(item, "bowtie") == 0 && draw_t) {
        g_rect(g, tx, ty, 12, 17, 19, 17, 'W'); g_px(g, tx, ty, 11, 17, 'w'); g_px(g, tx, ty, 20, 17, 'w');
        g_rect(g, tx, ty, 12, 18, 13, 20, 'r'); g_px(g, tx, ty, 14, 19, 'r');
        g_rect(g, tx, ty, 18, 18, 19, 20, 'r'); g_px(g, tx, ty, 17, 19, 'r');
        g_px(g, tx, ty, 12, 18, 'k'); g_px(g, tx, ty, 19, 18, 'k'); g_px(g, tx, ty, 12, 20, 'k'); g_px(g, tx, ty, 19, 20, 'k');
        g_px(g, tx, ty, 15, 19, 'R'); g_px(g, tx, ty, 16, 19, 'y');
    } else if (strcmp(item, "cape") == 0 && draw_t) {
        g_rect(g, tx, ty, 7, 18, 9, 26, 'S'); g_rect(g, tx, ty, 22, 18, 24, 26, 'S');
        g_rect(g, tx, ty, 8, 19, 9, 25, 'r'); g_rect(g, tx, ty, 22, 19, 23, 25, 'r');
        g_px(g, tx, ty, 6, 23, 'S'); g_px(g, tx, ty, 6, 24, 'r'); g_px(g, tx, ty, 6, 25, 'S');
        g_px(g, tx, ty, 25, 23, 'S'); g_px(g, tx, ty, 25, 24, 'r'); g_px(g, tx, ty, 25, 25, 'S');
        g_rect(g, tx, ty, 10, 17, 21, 18, 'r'); g_rect(g, tx, ty, 14, 17, 17, 18, 'y'); g_px(g, tx, ty, 15, 18, 'W');
    } else if (strcmp(item, "labcoat") == 0 && draw_t) {
        g_rect(g, tx, ty, 9, 18, 22, 25, 'W'); g_rect(g, tx, ty, 7, 19, 9, 22, 'W'); g_rect(g, tx, ty, 22, 19, 24, 22, 'W');
        g_px(g, tx, ty, 9, 18, 'w'); g_px(g, tx, ty, 22, 18, 'w'); g_rect(g, tx, ty, 9, 25, 22, 25, 'w');
        g_rect(g, tx, ty, 15, 18, 16, 24, 'b'); g_px(g, tx, ty, 15, 18, 'A'); g_px(g, tx, ty, 16, 18, 'A');
        g_px(g, tx, ty, 14, 18, 'w'); g_px(g, tx, ty, 17, 18, 'w');
        g_rect(g, tx, ty, 18, 21, 20, 22, 'w'); g_px(g, tx, ty, 19, 20, 'r');
    } else if (strcmp(item, "nerd") == 0 && draw_h) {
        g_rect(g, hx, hy, 9, 10, 14, 13, 'k'); g_rect(g, hx, hy, 17, 10, 22, 13, 'k');
        g_rect(g, hx, hy, 10, 11, 13, 12, 'u'); g_rect(g, hx, hy, 18, 11, 21, 12, 'u');
        g_px(g, hx, hy, 12, 11, 'k'); g_px(g, hx, hy, 20, 11, 'k'); g_px(g, hx, hy, 11, 11, 'W'); g_px(g, hx, hy, 19, 11, 'W');
        g_rect(g, hx, hy, 14, 11, 17, 11, 'k'); g_px(g, hx, hy, 15, 11, 'W'); g_px(g, hx, hy, 16, 11, 'W');
        g_px(g, hx, hy, 8, 11, 'k'); g_px(g, hx, hy, 23, 11, 'k');
    }
}

void render_frame_rgba(const SpriteBank *sb, const char *req_st, int frame_idx,
                       const char *skin, const char *item, Rgba out[32][32]) {
    int si = find_state_idx(sb, req_st);
    const char *st = req_st;
    if (si < 0 || sb->states[si].nframes <= 0) {
        st = "IDLE";
        si = find_state_idx(sb, "IDLE");
    }
    memset(out, 0, sizeof(Rgba) * 32 * 32);
    if (si < 0) return;

    int div = sb->states[si].div < 1 ? 1 : sb->states[si].div;
    int fi = (frame_idx / div) % sb->states[si].nframes;
    const char *sk = (skin && *skin) ? skin : "classic";

    char g[32][32];
    for (int y = 0; y < 32; y++) {
        const char *row = sb->states[si].rows[fi][y];
        int rl = (int)strlen(row);
        for (int x = 0; x < 32; x++) {
            char ch = x < rl ? row[x] : '.';
            g[y][x] = (ch == '.') ? '.' : map_skin(sk, ch);
        }
    }

    int hx = sb->states[si].anc[fi][0], hy = sb->states[si].anc[fi][1];
    int tx = sb->states[si].anc[fi][2], ty = sb->states[si].anc[fi][3];
    if (item && *item) {
        apply_outfit_overlay(g, item, hx, hy, tx, ty);
    }

    time_t now = time(NULL);
    struct tm *lt = localtime(&now);
    int tired = lt && lt->tm_hour >= 0 && lt->tm_hour < 4;
    int fri_drinks = lt && lt->tm_wday == 5 && lt->tm_hour >= 16;

    if (tired && hx != 99 && strcmp(st, "HYPER") != 0) {
        int xs[4] = {11, 12, 19, 20}, ys[2] = {11, 13};
        for (int ix = 0; ix < 4; ix++) {
            for (int iy = 0; iy < 2; iy++) g_px(g, hx, hy, xs[ix], ys[iy], 's');
        }
    }
    if (fri_drinks && tx != 99 &&
        strcmp(st, "EAT") != 0 && strcmp(st, "STUDY") != 0 &&
        strcmp(st, "JUMP") != 0 && strcmp(st, "CLIMB") != 0 && strcmp(st, "BORREL") != 0) {
        g_rect(g, tx, ty, 24, 18, 28, 23, 'k');
        g_rect(g, tx, ty, 25, 19, 27, 22, 'y');
        g_rect(g, tx, ty, 24, 17, 27, 18, 'W');
    }

    for (int y = 0; y < 32; y++) {
        for (int x = 0; x < 32; x++) {
            unsigned char ch = (unsigned char)g[y][x];
            if (ch != '.' && ch < 128 && sb->pal[ch].a) {
                out[y][x] = sb->pal[ch];
            }
        }
    }
}
