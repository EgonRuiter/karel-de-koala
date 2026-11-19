/* Karel de Koala - Minimalist Zero-Install Linux Companion (C99 + libX11 + XShape)
 * Feature-parity cross-platform counterpart of desktop/karel_native.cs & desktop/karel_mac.swift.
 * Build on Linux: bash desktop/build_linux.sh
 * Core test on any OS: gcc -std=c99 -Wall -Wextra -Werror -DKAREL_CORE_TEST desktop/karel_linux.c -lm -o test_core
 */

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#define KAREL_VERSION "2.2.1"
#define KAREL_MANIFEST_URL "https://github.com/EgonRuiter/karel-de-koala/releases/latest/download/version.json"

#ifndef KAREL_CORE_TEST
#include <arpa/inet.h>
#include <netinet/in.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/statvfs.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>
#if defined(__has_include) && __has_include(<X11/Xlib.h>) && __has_include(<X11/extensions/shape.h>)
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <X11/extensions/shape.h>
#include <X11/keysym.h>
#else
typedef struct _XDisplay Display;
typedef struct _Visual Visual;
typedef unsigned long XID, Window, Pixmap, Colormap, Atom, Font, Time, Drawable, Cursor, KeySym;
typedef int Bool, Status;
typedef void *GC;
typedef struct { void *ext_data; Font fid; } XFontStruct;
typedef struct { short x, y; } XPoint;
typedef struct {
    Pixmap background_pixmap; unsigned long background_pixel;
    Pixmap border_pixmap; unsigned long border_pixel;
    int bit_gravity, win_gravity, backing_store;
    unsigned long backing_planes, backing_pixel;
    Bool save_under; long event_mask, do_not_propagate_mask;
    Bool override_redirect; Colormap colormap; Cursor cursor;
} XSetWindowAttributes;
typedef struct { unsigned long pixel; unsigned short red, green, blue; char flags, pad; } XColor;
typedef struct { int type; unsigned long serial; Bool send_event; Display *display; Window window, root, subwindow; Time time; int x, y, x_root, y_root; unsigned int state, keycode; Bool same_screen; } XKeyEvent;
typedef struct { int type; unsigned long serial; Bool send_event; Display *display; Window window; int x, y, width, height, count; } XExposeEvent;
typedef struct { int type; unsigned long serial; Bool send_event; Display *display; Window window, root, subwindow; Time time; int x, y, x_root, y_root; unsigned int state, button; Bool same_screen; } XButtonEvent;
typedef struct { int type; unsigned long serial; Bool send_event; Display *display; Window window, root, subwindow; Time time; int x, y, x_root, y_root; unsigned int state; char is_hint; Bool same_screen; } XMotionEvent;
typedef struct { int type; unsigned long serial; Bool send_event; Display *display; Window window; Atom message_type; int format; union { char b[20]; short s[10]; long l[5]; } data; } XClientMessageEvent;
typedef union { int type; XKeyEvent xkey; XExposeEvent xexpose; XButtonEvent xbutton; XMotionEvent xmotion; XClientMessageEvent xclient; long pad[24]; } XEvent;
#define None 0L
#define CopyFromParent 0L
#define InputOutput 1
#define Success 0
#define False 0
#define True 1
#define XA_CARDINAL ((Atom)6)
#define XA_WINDOW ((Atom)33)
#define XA_ATOM ((Atom)4)
#define AnyPropertyType ((Atom)0L)
#define CWBackPixel (1L<<1)
#define CWOverrideRedirect (1L<<9)
#define DoRed (1<<0)
#define DoGreen (1<<1)
#define DoBlue (1<<2)
#define KeyPressMask (1L<<0)
#define ButtonPressMask (1L<<2)
#define ButtonReleaseMask (1L<<3)
#define PointerMotionMask (1L<<6)
#define ExposureMask (1L<<15)
#define KeyPress 2
#define ButtonPress 4
#define ButtonRelease 5
#define MotionNotify 6
#define Expose 12
#define ClientMessage 33
#define Button1 1
#define ShapeBounding 0
#define ShapeSet 0
#define Convex 2
#define CoordModeOrigin 0
#define XK_Return 0xff0d
#define XK_Escape 0xff1b
#define XK_Left 0xff51
#define XK_Up 0xff52
#define XK_Right 0xff53
#define XK_Down 0xff54
#define XK_A 0x0041
#define XK_B 0x0042
#define XK_a 0x0061
#define XK_b 0x0062
Display *XOpenDisplay(const char *);
int XCloseDisplay(Display *);
int XDefaultScreen(Display *);
Window XRootWindow(Display *, int);
Colormap XDefaultColormap(Display *, int);
int XDisplayWidth(Display *, int);
int XDisplayHeight(Display *, int);
Atom XInternAtom(Display *, const char *, Bool);
char *XGetDefault(Display *, const char *, const char *);
XFontStruct *XLoadQueryFont(Display *, const char *);
int XSetFont(Display *, GC, Font);
int XTextWidth(XFontStruct *, const char *, int);
int XDrawString(Display *, Drawable, GC, int, int, const char *, int);
Window XCreateWindow(Display *, Window, int, int, unsigned int, unsigned int, unsigned int, int, unsigned int, Visual *, unsigned long, XSetWindowAttributes *);
Window XCreateSimpleWindow(Display *, Window, int, int, unsigned int, unsigned int, unsigned int, unsigned long, unsigned long);
int XDestroyWindow(Display *, Window);
int XStoreName(Display *, Window, const char *);
Status XSetWMProtocols(Display *, Window, Atom *, int);
int XSelectInput(Display *, Window, long);
GC XCreateGC(Display *, Drawable, unsigned long, void *);
int XFreeGC(Display *, GC);
int XClearArea(Display *, Window, int, int, unsigned int, unsigned int, Bool);
int XMapRaised(Display *, Window);
int XUnmapWindow(Display *, Window);
int XMoveWindow(Display *, Window, int, int);
int XResizeWindow(Display *, Window, unsigned int, unsigned int);
int XPending(Display *);
int XNextEvent(Display *, XEvent *);
int XFlush(Display *);
int XSetForeground(Display *, GC, unsigned long);
int XFillRectangle(Display *, Drawable, GC, int, int, unsigned int, unsigned int);
int XDrawRectangle(Display *, Drawable, GC, int, int, unsigned int, unsigned int);
int XFillArc(Display *, Drawable, GC, int, int, unsigned int, unsigned int, int, int);
int XFillPolygon(Display *, Drawable, GC, XPoint *, int, int, int);
Pixmap XCreatePixmap(Display *, Drawable, unsigned int, unsigned int, unsigned int);
int XFreePixmap(Display *, Pixmap);
Status XAllocColor(Display *, Colormap, XColor *);
Status XGetGeometry(Display *, Drawable, Window *, int *, int *, unsigned int *, unsigned int *, unsigned int *, unsigned int *);
Bool XTranslateCoordinates(Display *, Window, Window, int, int, int *, int *, Window *);
Bool XQueryPointer(Display *, Window, Window *, Window *, int *, int *, int *, int *, unsigned int *);
KeySym XLookupKeysym(XKeyEvent *, int);
int XGetWindowProperty(Display *, Window, Atom, long, long, Bool, Atom, Atom *, int *, unsigned long *, unsigned long *, unsigned char **);
int XFree(void *);
void XShapeCombineMask(Display *, Window, int, int, int, Pixmap, int);
#endif
#endif

/* =========================================================================
 * 1. Pure-C99 RFC 1952/1951 Gzip/Deflate Decoder + FIPS 180-4 SHA-256
 * ========================================================================= */

typedef struct { const uint8_t *src; size_t len, pos; uint32_t bitbuf; int bitcnt; } BitRd;
typedef struct { uint16_t count[16]; uint16_t sym[320]; } HuffTbl;

static int br_bit(BitRd *b) {
    if (b->bitcnt == 0) {
        if (b->pos >= b->len) return -1;
        b->bitbuf = b->src[b->pos++]; b->bitcnt = 8;
    }
    int r = (int)(b->bitbuf & 1U); b->bitbuf >>= 1; b->bitcnt--;
    return r;
}

static int br_bits(BitRd *b, int n) {
    int v = 0;
    for (int i = 0; i < n; i++) {
        int bit = br_bit(b);
        if (bit < 0) return -1;
        v |= (bit << i);
    }
    return v;
}

static void huff_build(HuffTbl *h, const uint8_t *lens, int n) {
    uint16_t offs[16];
    memset(h->count, 0, sizeof(h->count));
    for (int i = 0; i < n; i++) if (lens[i] < 16) h->count[lens[i]]++;
    offs[1] = 0;
    for (int i = 1; i < 15; i++) offs[i + 1] = (uint16_t)(offs[i] + h->count[i]);
    for (int i = 0; i < n; i++) if (lens[i] > 0 && lens[i] < 16) h->sym[offs[lens[i]]++] = (uint16_t)i;
}

static int huff_dec(BitRd *b, const HuffTbl *h) {
    int code = 0, first = 0, idx = 0;
    for (int len = 1; len <= 15; len++) {
        int bit = br_bit(b);
        if (bit < 0) return -1;
        code |= bit;
        int c = h->count[len];
        if (code - c < first) return (int)h->sym[idx + (code - first)];
        idx += c; first += c; first <<= 1; code <<= 1;
    }
    return -1;
}

static uint8_t *inflate_gzip(const uint8_t *src, size_t len, size_t *out_len) {
    if (len < 18 || src[0] != 0x1f || src[1] != 0x8b || src[2] != 8) return NULL;
    uint8_t flg = src[3];
    size_t p = 10;
    if (flg & 0x04) { if (p + 2 > len) return NULL; p += 2 + ((size_t)src[p] | ((size_t)src[p + 1] << 8)); }
    if (flg & 0x08) { while (p < len && src[p]) p++; p++; }
    if (flg & 0x10) { while (p < len && src[p]) p++; p++; }
    if (flg & 0x02) p += 2;
    if (p >= len) return NULL;

    size_t cap = len * 24 + 4096, out_n = 0;
    uint8_t *out = (uint8_t *)malloc(cap);
    if (!out) return NULL;

    BitRd br = { src, len - 8, p, 0, 0 };
    static const uint16_t lbase[29] = {3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258};
    static const uint8_t lext[29] = {0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0};
    static const uint16_t dbase[30] = {1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577};
    static const uint8_t dext[30] = {0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13};
    static const uint8_t clord[19] = {16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15};

    int last = 0;
    while (!last) {
        last = br_bit(&br);
        int btype = br_bits(&br, 2);
        if (last < 0 || btype < 0 || btype == 3) { free(out); return NULL; }
        if (btype == 0) {
            br.bitcnt = 0; br.bitbuf = 0;
            if (br.pos + 4 > br.len) { free(out); return NULL; }
            uint16_t blen = (uint16_t)(br.src[br.pos] | (br.src[br.pos + 1] << 8));
            br.pos += 4;
            if (br.pos + blen > br.len) { free(out); return NULL; }
            if (out_n + blen + 1 > cap) { cap = (out_n + blen) * 2 + 1024; out = (uint8_t *)realloc(out, cap); }
            memcpy(out + out_n, br.src + br.pos, blen);
            br.pos += blen; out_n += blen;
            continue;
        }
        HuffTbl lt, dt;
        if (btype == 1) {
            uint8_t ll[288], dl[32];
            for (int i = 0; i < 144; i++) ll[i] = 8;
            for (int i = 144; i < 256; i++) ll[i] = 9;
            for (int i = 256; i < 280; i++) ll[i] = 7;
            for (int i = 280; i < 288; i++) ll[i] = 8;
            memset(dl, 5, 32);
            huff_build(&lt, ll, 288); huff_build(&dt, dl, 32);
        } else {
            int hlit = br_bits(&br, 5) + 257, hdist = br_bits(&br, 5) + 1, hclen = br_bits(&br, 4) + 4;
            uint8_t cll[19]; memset(cll, 0, sizeof(cll));
            for (int i = 0; i < hclen; i++) cll[clord[i]] = (uint8_t)br_bits(&br, 3);
            HuffTbl ct; huff_build(&ct, cll, 19);
            uint8_t lens[320]; int ti = 0;
            while (ti < hlit + hdist) {
                int s = huff_dec(&br, &ct);
                if (s < 0) { free(out); return NULL; }
                if (s < 16) lens[ti++] = (uint8_t)s;
                else {
                    int rep = 0; uint8_t val = 0;
                    if (s == 16) { if (ti == 0) { free(out); return NULL; } val = lens[ti - 1]; rep = 3 + br_bits(&br, 2); }
                    else if (s == 17) rep = 3 + br_bits(&br, 3);
                    else rep = 11 + br_bits(&br, 7);
                    while (rep-- > 0 && ti < 320) lens[ti++] = val;
                }
            }
            huff_build(&lt, lens, hlit);
            huff_build(&dt, lens + hlit, hdist);
        }
        while (1) {
            int s = huff_dec(&br, &lt);
            if (s < 0) { free(out); return NULL; }
            if (s < 256) {
                if (out_n + 2 > cap) { cap *= 2; out = (uint8_t *)realloc(out, cap); }
                out[out_n++] = (uint8_t)s;
            } else if (s == 256) break;
            else {
                int li = s - 257;
                if (li >= 29) { free(out); return NULL; }
                int clen = (int)lbase[li] + br_bits(&br, lext[li]);
                int di = huff_dec(&br, &dt);
                if (di < 0 || di >= 30) { free(out); return NULL; }
                int dist = (int)dbase[di] + br_bits(&br, dext[di]);
                if ((size_t)dist > out_n) { free(out); return NULL; }
                if (out_n + (size_t)clen + 2 > cap) { cap = (out_n + (size_t)clen) * 2 + 1024; out = (uint8_t *)realloc(out, cap); }
                for (int k = 0; k < clen; k++) { out[out_n] = out[out_n - (size_t)dist]; out_n++; }
            }
        }
    }
    out[out_n] = 0;
    if (out_len) *out_len = out_n;
    return out;
}

static void sha256_hex(const uint8_t *data, size_t len, char out[65]) {
    static const uint32_t K[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint32_t st[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    size_t pad_len = ((len + 9 + 63) / 64) * 64;
    uint8_t *msg = (uint8_t *)calloc(pad_len, 1);
    if (!msg) { out[0] = 0; return; }
    memcpy(msg, data, len);
    msg[len] = 0x80;
    uint64_t bitlen = (uint64_t)len * 8ULL;
    for (int i = 0; i < 8; i++) msg[pad_len - 1 - (size_t)i] = (uint8_t)((bitlen >> (i * 8)) & 0xFF);
    #define ROR32(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
    for (size_t off = 0; off < pad_len; off += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; i++) {
            const uint8_t *q = msg + off + i * 4;
            w[i] = ((uint32_t)q[0] << 24) | ((uint32_t)q[1] << 16) | ((uint32_t)q[2] << 8) | q[3];
        }
        for (int i = 16; i < 64; i++) {
            uint32_t s0 = ROR32(w[i - 15], 7) ^ ROR32(w[i - 15], 18) ^ (w[i - 15] >> 3);
            uint32_t s1 = ROR32(w[i - 2], 17) ^ ROR32(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        uint32_t a=st[0],b=st[1],c=st[2],d=st[3],e=st[4],f=st[5],g=st[6],h=st[7];
        for (int i = 0; i < 64; i++) {
            uint32_t S1 = ROR32(e, 6) ^ ROR32(e, 11) ^ ROR32(e, 25);
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t t1 = h + S1 + ch + K[i] + w[i];
            uint32_t S0 = ROR32(a, 2) ^ ROR32(a, 13) ^ ROR32(a, 22);
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t t2 = S0 + maj;
            h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
        }
        st[0]+=a; st[1]+=b; st[2]+=c; st[3]+=d; st[4]+=e; st[5]+=f; st[6]+=g; st[7]+=h;
    }
    #undef ROR32
    free(msg);
    for (int i = 0; i < 8; i++) snprintf(out + i * 8, 9, "%08x", st[i]);
    out[64] = 0;
}

static int compare_ver(const char *a, const char *b) {
    int pa[3] = {0, 0, 0}, pb[3] = {0, 0, 0};
    if (a) { if (*a == 'v' || *a == 'V') a++; (void)sscanf(a, "%d.%d.%d", &pa[0], &pa[1], &pa[2]); }
    if (b) { if (*b == 'v' || *b == 'V') b++; (void)sscanf(b, "%d.%d.%d", &pb[0], &pb[1], &pb[2]); }
    for (int i = 0; i < 3; i++) if (pa[i] != pb[i]) return pa[i] > pb[i] ? 1 : -1;
    return 0;
}

/* =========================================================================
 * 2. Sprite Bank (karel_sprites.gz)
 * ========================================================================= */

#define MAX_STATES 72
#define MAX_FRAMES 16

typedef struct { uint8_t r, g, b, a; } Rgba;
typedef struct { char name[32]; int nframes, div; char rows[MAX_FRAMES][32][33]; } AnimState;
typedef struct { Rgba pal[128]; AnimState states[MAX_STATES]; int nstates; } SpriteBank;

static const char *SKIN_IDS[] = {"classic", "sticky", "mint", "midnight", "gold", "crimson"};
static const char *OUTFIT_IDS[] = {"scarf", "stickycap", "hoodie", "headphones", "shades", "crown", "wizard", "partyhat", ""};
#define NUM_SKINS 6
#define NUM_OUTFITS 9

static int skip_overlay(const char *st) {
    static const char *skip[] = {
        "SLEEP", "CRY", "YAWN", "DIZZY", "CLIMB", "DIVE_WAVE", "DIVE_DOWN",
        "PEEK", "BACKFLIP", "SPIN", "UMBRELLA", "MUSIC", "EXERCISE",
        "LAPTOP_CODE", "SIT", "STRETCH", "BOW", "PARTY_HORN", "GAMING", NULL
    };
    for (int i = 0; skip[i]; i++) if (strcmp(st, skip[i]) == 0) return 1;
    return 0;
}

static int find_state_idx(const SpriteBank *sb, const char *st) {
    for (int i = 0; i < sb->nstates; i++) if (strcmp(sb->states[i].name, st) == 0) return i;
    return -1;
}

static int parse_hex2(const char *s) {
    int v = 0;
    for (int i = 0; i < 2; i++) {
        char c = s[i]; v <<= 4;
        if (c >= '0' && c <= '9') v |= c - '0';
        else if (c >= 'a' && c <= 'f') v |= c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') v |= c - 'A' + 10;
    }
    return v;
}

static int load_sprites_gz(SpriteBank *sb, const char *path) {
    memset(sb, 0, sizeof(*sb));
    FILE *fp = fopen(path, "rb");
    if (!fp) return 0;
    fseek(fp, 0, SEEK_END); long fsz = ftell(fp); fseek(fp, 0, SEEK_SET);
    if (fsz <= 0 || fsz > 1024 * 1024) { fclose(fp); return 0; }
    uint8_t *comp = (uint8_t *)malloc((size_t)fsz);
    if (!comp || fread(comp, 1, (size_t)fsz, fp) != (size_t)fsz) { free(comp); fclose(fp); return 0; }
    fclose(fp);
    size_t raw_len = 0;
    uint8_t *raw = inflate_gzip(comp, (size_t)fsz, &raw_len);
    free(comp);
    if (!raw) return 0;

    int cur_st = -1, cur_row = 0;
    char *p = (char *)raw, *end = (char *)raw + raw_len;
    while (p < end) {
        char *nl = strchr(p, '\n'); if (!nl) nl = end;
        *nl = 0;
        size_t l = strlen(p); if (l > 0 && p[l - 1] == '\r') p[--l] = 0;
        if (strncmp(p, "PAL|", 4) == 0) {
            char *q = p + 4;
            while (*q) {
                char *comma = strchr(q, ','); if (comma) *comma = 0;
                if (strlen(q) == 9 && q[1] == ':' && q[2] == '#') {
                    unsigned char ch = (unsigned char)q[0];
                    if (ch < 128) sb->pal[ch] = (Rgba){(uint8_t)parse_hex2(q + 3), (uint8_t)parse_hex2(q + 5), (uint8_t)parse_hex2(q + 7), 255};
                }
                if (!comma) break;
                q = comma + 1;
            }
        } else if (strncmp(p, "DIV|", 4) == 0) {
            char *q = p + 4;
            while (*q) {
                char *comma = strchr(q, ','); if (comma) *comma = 0;
                char *eq = strchr(q, '=');
                if (eq) {
                    *eq = 0;
                    int idx = find_state_idx(sb, q);
                    if (idx < 0 && sb->nstates < MAX_STATES) { idx = sb->nstates++; snprintf(sb->states[idx].name, 32, "%.31s", q); sb->states[idx].div = 2; }
                    if (idx >= 0) sb->states[idx].div = atoi(eq + 1);
                }
                if (!comma) break;
                q = comma + 1;
            }
        } else if (p[0] == '@') {
            int idx = find_state_idx(sb, p + 1);
            if (idx < 0 && sb->nstates < MAX_STATES) { idx = sb->nstates++; snprintf(sb->states[idx].name, 32, "%.31s", p + 1); sb->states[idx].div = 2; }
            cur_st = idx; cur_row = 0;
            if (cur_st >= 0 && sb->states[cur_st].nframes == 0) sb->states[cur_st].nframes = 1;
        } else if (strcmp(p, "---") == 0) {
            if (cur_st >= 0 && sb->states[cur_st].nframes < MAX_FRAMES) { sb->states[cur_st].nframes++; cur_row = 0; }
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

static char map_skin(const char *skin, char ch) {
    if (strcmp(skin, "sticky") == 0) { if (ch == 'g') return 'r'; if (ch == 's') return 'R'; if (ch == 'w') return 'W'; }
    else if (strcmp(skin, "mint") == 0) { if (ch == 'g') return 'n'; if (ch == 's') return 'e'; if (ch == 'w') return 'W'; }
    else if (strcmp(skin, "midnight") == 0) { if (ch == 'g') return 'm'; if (ch == 's') return 'k'; if (ch == 'w') return 'b'; }
    else if (strcmp(skin, "gold") == 0) { if (ch == 'g') return 'y'; if (ch == 's') return 'Y'; if (ch == 'w') return 'W'; }
    else if (strcmp(skin, "crimson") == 0) { if (ch == 'g') return 'R'; if (ch == 's') return 'r'; if (ch == 'w') return 'y'; }
    return ch;
}

static void g_rect(char g[32][32], int x0, int y0, int x1, int y1, char ch) {
    for (int y = y0 < 0 ? 0 : y0; y <= (y1 > 31 ? 31 : y1); y++)
        for (int x = x0 < 0 ? 0 : x0; x <= (x1 > 31 ? 31 : x1); x++) g[y][x] = ch;
}
static void g_px(char g[32][32], int x, int y, char ch) { if (x >= 0 && x < 32 && y >= 0 && y < 32) g[y][x] = ch; }

static void render_frame_rgba(const SpriteBank *sb, const char *req_st, int frame_idx,
                              const char *skin, const char *item, Rgba out[32][32]) {
    int si = find_state_idx(sb, req_st);
    const char *st = req_st;
    if (si < 0 || sb->states[si].nframes <= 0) { st = "IDLE"; si = find_state_idx(sb, "IDLE"); }
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

    time_t now = time(NULL);
    struct tm *lt = localtime(&now);
    int tired = lt && lt->tm_hour >= 0 && lt->tm_hour < 4;
    int vm = lt && lt->tm_wday == 5 && lt->tm_hour >= 16;

    if (!skip_overlay(st) && item) {
        if (strcmp(item, "scarf") == 0) {
            g_rect(g, 10, 17, 21, 18, 'r'); g_rect(g, 17, 19, 18, 22, 'r');
            for (int x = 10; x <= 21; x += 3) g_px(g, x, 18, 'R');
        } else if (strcmp(item, "stickycap") == 0 && strcmp(st, "JUMP") != 0) {
            g_rect(g, 9, 4, 22, 5, 'r'); g_rect(g, 11, 2, 20, 4, 'r'); g_rect(g, 19, 5, 25, 5, 'R');
            g_px(g, 15, 3, 'W'); g_px(g, 16, 3, 'W');
        } else if (strcmp(item, "hoodie") == 0) {
            g_rect(g, 8, 19, 11, 20, 'r'); g_rect(g, 20, 19, 23, 20, 'r'); g_rect(g, 11, 24, 20, 25, 'r');
        } else if (strcmp(item, "headphones") == 0 && strcmp(st, "JUMP") != 0) {
            g_rect(g, 3, 7, 4, 11, 'r'); g_rect(g, 27, 7, 28, 11, 'r'); g_rect(g, 7, 4, 24, 4, 'd');
            g_px(g, 5, 6, 'd'); g_px(g, 6, 5, 'd'); g_px(g, 25, 5, 'd'); g_px(g, 26, 6, 'd');
        } else if (strcmp(item, "shades") == 0 && strcmp(st, "JUMP") != 0) {
            g_rect(g, 10, 10, 13, 12, 'k'); g_rect(g, 18, 10, 21, 12, 'k'); g_rect(g, 14, 11, 17, 11, 'd');
            g_px(g, 11, 11, 'W'); g_px(g, 19, 11, 'W');
        } else if (strcmp(item, "crown") == 0 && strcmp(st, "JUMP") != 0) {
            g_rect(g, 12, 3, 19, 5, 'y');
            g_px(g, 12, 2, 'y'); g_px(g, 15, 1, 'y'); g_px(g, 16, 1, 'y'); g_px(g, 19, 2, 'y');
            g_px(g, 15, 4, 'R'); g_px(g, 16, 4, 'R'); g_px(g, 11, 5, 'k'); g_px(g, 20, 5, 'k');
        } else if (strcmp(item, "wizard") == 0 && strcmp(st, "JUMP") != 0) {
            g_rect(g, 9, 4, 22, 5, 'm'); g_rect(g, 12, 2, 19, 3, 'm');
            g_rect(g, 14, 0, 17, 1, 'm'); g_rect(g, 11, 4, 20, 4, 'y');
            g_px(g, 15, 2, 'y'); g_px(g, 16, 1, 'W');
        } else if (strcmp(item, "partyhat") == 0 && strcmp(st, "JUMP") != 0) {
            g_rect(g, 13, 3, 18, 5, 'm'); g_rect(g, 14, 1, 17, 2, 'R');
            g_px(g, 15, 0, 'y'); g_px(g, 16, 0, 'y'); g_px(g, 14, 4, 'y'); g_px(g, 17, 3, 'b');
        }
        if (tired && strcmp(st, "HYPER") != 0 && strcmp(st, "JUMP") != 0) {
            int xs[4] = {11, 12, 19, 20}, ys[2] = {11, 13};
            for (int ix = 0; ix < 4; ix++) for (int iy = 0; iy < 2; iy++) g_px(g, xs[ix], ys[iy], 's');
        }
        if (vm && strcmp(st, "EAT") != 0 && strcmp(st, "STUDY") != 0 && strcmp(st, "JUMP") != 0 &&
            strcmp(st, "CLIMB") != 0 && strcmp(st, "BORREL") != 0) {
            g_rect(g, 24, 18, 28, 23, 'k'); g_rect(g, 25, 19, 27, 22, 'y'); g_rect(g, 24, 17, 27, 18, 'W');
        }
    }

    for (int y = 0; y < 32; y++) {
        for (int x = 0; x < 32; x++) {
            unsigned char ch = (unsigned char)g[y][x];
            if (ch != '.' && ch < 128 && sb->pal[ch].a) out[y][x] = sb->pal[ch];
        }
    }
}

/* =========================================================================
 * 3. Persistent SaveStore + USB Serial/Flag Parity (No Coins)
 * ========================================================================= */

typedef struct {
    int hunger, happiness, energy, hygiene, caffeine;
    int xp, level, total_pets, karel_scale, auto_quiet;
    char roam_mode[16], skin[24], equipped[32], language[8], stick_serial[32], last_seen[32];
    char drive_root[512], fallback_path[560];
    int connected;
} SaveStore;

static int xp_for_next_level(int lvl) { return lvl <= 0 ? 0 : 180 * lvl * (lvl + 1); }
static int level_from_xp(int xp) { int l = 1; while (xp >= xp_for_next_level(l)) l++; return l; }
static int clamp_int(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }
static int file_exists(const char *p) { struct stat st; return p && *p && stat(p, &st) == 0; }

static void save_defaults(SaveStore *s) {
    s->hunger = 80; s->happiness = 85; s->energy = 85; s->hygiene = 90; s->caffeine = 25;
    s->xp = 0; s->level = 1; s->total_pets = 0; s->karel_scale = 3; s->auto_quiet = 1;
    strcpy(s->roam_mode, "free"); strcpy(s->skin, "classic"); strcpy(s->equipped, "scarf");
    strcpy(s->language, "nl"); s->stick_serial[0] = 0; s->last_seen[0] = 0;
}

static int json_find_str(const char *txt, const char *key, char *out, size_t max_out) {
    char pat[64]; snprintf(pat, sizeof(pat), "\"%.50s\"", key);
    const char *p = strstr(txt, pat); if (!p) return 0;
    p = strchr(p + strlen(pat), ':'); if (!p) return 0;
    p++; while (*p && (*p == ' ' || *p == '\t' || *p == '[' || *p == '\n' || *p == '\r')) p++;
    if (*p != '"') return 0;
    p++;
    const char *q = strchr(p, '"'); if (!q) return 0;
    size_t n = (size_t)(q - p); if (n >= max_out) n = max_out - 1;
    memcpy(out, p, n); out[n] = 0;
    return 1;
}

static int json_find_int(const char *txt, const char *key, int *out) {
    char pat[64]; snprintf(pat, sizeof(pat), "\"%.50s\"", key);
    const char *p = strstr(txt, pat); if (!p) return 0;
    p = strchr(p + strlen(pat), ':'); if (!p) return 0;
    p++; while (*p && isspace((unsigned char)*p)) p++;
    if (strncmp(p, "true", 4) == 0) { *out = 1; return 1; }
    if (strncmp(p, "false", 5) == 0) { *out = 0; return 1; }
    if (!isdigit((unsigned char)*p) && *p != '-') return 0;
    *out = atoi(p);
    return 1;
}

static time_t parse_iso_local(const char *s) {
    if (!s || strlen(s) < 19) return 0;
    struct tm t; memset(&t, 0, sizeof(t)); t.tm_isdst = -1;
    if (sscanf(s, "%d-%d-%dT%d:%d:%d", &t.tm_year, &t.tm_mon, &t.tm_mday, &t.tm_hour, &t.tm_min, &t.tm_sec) != 6) return 0;
    t.tm_year -= 1900; t.tm_mon -= 1;
    return mktime(&t);
}

static int read_save_file(const char *path, SaveStore *out) {
    FILE *fp = fopen(path, "rb"); if (!fp) return 0;
    char buf[8192]; size_t n = fread(buf, 1, sizeof(buf) - 1, fp); fclose(fp);
    if (n < 2) return 0;
    size_t off = (n >= 3 && (unsigned char)buf[0] == 0xEF && (unsigned char)buf[1] == 0xBB && (unsigned char)buf[2] == 0xBF) ? 3 : 0;
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
        char m[600]; snprintf(m, sizeof(m), "%.500s/.karel_drive", env);
        if (file_exists(m) && strlen(env) < max_out) { memcpy(out, env, strlen(env) + 1); return; }
    }
    char bases[4][512];
    const char *usr = getenv("USER");
    snprintf(bases[0], 512, "/media/%.200s", usr ? usr : "root");
    snprintf(bases[1], 512, "/run/media/%.200s", usr ? usr : "root");
    strcpy(bases[2], "/media"); strcpy(bases[3], "/mnt");
    for (int bi = 0; bi < 4; bi++) {
        DIR *dp = opendir(bases[bi]); if (!dp) continue;
        struct dirent *de;
        while ((de = readdir(dp)) != NULL) {
            if (de->d_name[0] == '.') continue;
            char cand[1024], mrk[1040];
            snprintf(cand, sizeof(cand), "%.500s/%.250s", bases[bi], de->d_name);
            snprintf(mrk, sizeof(mrk), "%s/.karel_drive", cand);
            if (file_exists(mrk) && strlen(cand) < max_out) { memcpy(out, cand, strlen(cand) + 1); closedir(dp); return; }
        }
        closedir(dp);
    }
}

static void save_write_one(const char *path, const SaveStore *s, int direct) {
    char tmp[600];
    const char *target = path;
    if (!direct) { snprintf(tmp, sizeof(tmp), "%.580s.tmp", path); target = tmp; }
    FILE *fp = fopen(target, "wb"); if (!fp) return;
    fprintf(fp,
        "{\n  \"name\": \"Karel\",\n"
        "  \"hunger\": %d,\n  \"happiness\": %d,\n  \"energy\": %d,\n  \"hygiene\": %d,\n  \"caffeine\": %d,\n"
        "  \"xp\": %d,\n  \"level\": %d,\n  \"total_pets\": %d,\n"
        "  \"skin\": \"%s\",\n  \"equipped\": %s%s%s,\n"
        "  \"roam_mode\": \"%s\",\n  \"karel_scale\": %d,\n  \"auto_quiet_fullscreen\": %s,\n"
        "  \"language\": \"%s\",\n  \"stick_serial\": \"%s\",\n  \"last_seen\": \"%s\"\n}\n",
        s->hunger, s->happiness, s->energy, s->hygiene, s->caffeine,
        s->xp, s->level, s->total_pets,
        s->skin, *s->equipped ? "[\"" : "[", *s->equipped ? s->equipped : "", *s->equipped ? "\"]" : "]",
        s->roam_mode, s->karel_scale, s->auto_quiet ? "true" : "false",
        s->language, s->stick_serial, s->last_seen);
    fflush(fp);
#if !defined(_WIN32) && !defined(KAREL_CORE_TEST)
    fsync(fileno(fp));
#endif
    fclose(fp);
    if (!direct) rename(tmp, path);
}

static void save_persist(SaveStore *s) {
    if (s->connected && !*s->stick_serial) get_volume_serial(s->drive_root, s->stick_serial);
    time_t now = time(NULL); struct tm *lt = localtime(&now);
    if (lt) strftime(s->last_seen, sizeof(s->last_seen), "%Y-%m-%dT%H:%M:%S", lt);
    if (*s->fallback_path) save_write_one(s->fallback_path, s, 0);
    if (s->connected && *s->drive_root) {
        char usb_p[600]; snprintf(usb_p, sizeof(usb_p), "%.500s/save.json", s->drive_root);
        save_write_one(usb_p, s, 1);
    }
}

static void save_load(SaveStore *s) {
    save_defaults(s);
    const char *home = getenv("HOME");
    if (home) {
        char d[512]; snprintf(d, sizeof(d), "%.480s/.local/share/karel-de-koala", home);
#ifndef _WIN32
        mkdir(d, 0755);
#endif
        snprintf(s->fallback_path, sizeof(s->fallback_path), "%s/save.json", d);
    } else s->fallback_path[0] = 0;

    find_usb_drive(s->drive_root, sizeof(s->drive_root));
    s->connected = (*s->drive_root != 0);
    char cur_ser[32]; get_volume_serial(s->drive_root, cur_ser);

    SaveStore u, f; int has_u = 0, has_f = 0;
    if (s->connected) {
        char up[600]; snprintf(up, sizeof(up), "%.500s/save.json", s->drive_root);
        has_u = read_save_file(up, &u);
    }
    if (*s->fallback_path) has_f = read_save_file(s->fallback_path, &f);

    int rec_fb = 0;
    if (has_u && has_f) {
        const char *u_ser = *u.stick_serial ? u.stick_serial : cur_ser;
        time_t tu = parse_iso_local(u.last_seen), tf = parse_iso_local(f.last_seen);
        if (*f.stick_serial && *u_ser && strcmp(u_ser, f.stick_serial) == 0 && (tf > tu || (tf == tu && f.xp > u.xp))) {
            *s = f; rec_fb = 1;
        } else { *s = u; }
    } else if (has_u) *s = u;
    else if (has_f && (!s->connected || (*cur_ser && strcmp(f.stick_serial, cur_ser) == 0))) {
        *s = f; rec_fb = s->connected;
    }

    find_usb_drive(s->drive_root, sizeof(s->drive_root));
    s->connected = (*s->drive_root != 0);
    if (home) snprintf(s->fallback_path, sizeof(s->fallback_path), "%.480s/.local/share/karel-de-koala/save.json", home);

    time_t prev = parse_iso_local(s->last_seen);
    if (prev > 0) {
        double hrs = difftime(time(NULL), prev) / 3600.0;
        if (hrs > 0.05) {
            s->hunger = clamp_int((int)llround(s->hunger - hrs * 2.5), 5, 100);
            s->happiness = clamp_int((int)llround(s->happiness - hrs * 2.0), 10, 100);
            s->hygiene = clamp_int((int)llround(s->hygiene - hrs * 1.1), 15, 100);
            s->caffeine = clamp_int((int)llround(s->caffeine - hrs * 8.0), 0, 100);
            if (hrs >= 1.0) s->energy = clamp_int((int)llround(s->energy + hrs * 5.0), 0, 100);
        }
    }
    s->level = level_from_xp(s->xp);
    if (*cur_ser) snprintf(s->stick_serial, sizeof(s->stick_serial), "%.31s", cur_ser);
    if (rec_fb) save_persist(s);
}

#ifndef KAREL_CORE_TEST
static int poll_usb(SaveStore *s) {
    int was = s->connected;
    find_usb_drive(s->drive_root, sizeof(s->drive_root));
    s->connected = (*s->drive_root != 0);
    if (!was && s->connected) return 1;
    if (was && !s->connected) return -1;
    return 0;
}
#endif

/* =========================================================================
 * 4. In-Memory WAV Synthesizer & Shared Sprites Locator
 * ========================================================================= */

static size_t build_wav_bytes(const double *freqs, int nfreq, double dur, double amp, uint8_t *buf, size_t maxb) {
    const int sr = 22050;
    int nper = (int)(dur * sr); if (nper < 100) nper = 100;
    int total = nper * nfreq; size_t need = 44 + (size_t)total * 2;
    if (need > maxb) return 0;
    uint32_t db = (uint32_t)(total * 2), rsz = 36 + db, fmt = 16, br = sr * 2, usr = sr;
    uint16_t pcm = 1, ch = 1, ba = 2, bps = 16;
    memcpy(buf, "RIFF", 4); memcpy(buf + 4, &rsz, 4); memcpy(buf + 8, "WAVEfmt ", 8);
    memcpy(buf + 16, &fmt, 4); memcpy(buf + 20, &pcm, 2); memcpy(buf + 22, &ch, 2);
    memcpy(buf + 24, &usr, 4); memcpy(buf + 28, &br, 4); memcpy(buf + 32, &ba, 2); memcpy(buf + 34, &bps, 2);
    memcpy(buf + 36, "data", 4); memcpy(buf + 40, &db, 4);
    int16_t *samples = (int16_t *)(buf + 44);
    for (int fi = 0; fi < nfreq; fi++) {
        double f = freqs[fi], ph = 0.0;
        for (int i = 0; i < nper; i++) {
            double e1 = i < 120 ? i / 120.0 : 1.0, e2 = (nper - i) < 220 ? (nper - i) / 220.0 : 1.0;
            double v = (sin(ph) + 0.28 * sin(2.0 * ph)) * (e1 < e2 ? e1 : e2) * amp * 24000.0;
            samples[fi * nper + i] = (int16_t)(v > 32767.0 ? 32767 : (v < -32767.0 ? -32767 : v));
            ph += 6.28318530718 * f / sr;
        }
    }
    return need;
}

static int locate_sprites_gz(char *out, size_t max_out) {
    const char *env = getenv("KAREL_DRIVE_DIR");
    const char *cands[] = {NULL, "karel_sprites.gz", "desktop/karel_sprites.gz", "../desktop/karel_sprites.gz", NULL};
    char envp[600];
    if (env && *env) { snprintf(envp, sizeof(envp), "%.500s/karel_sprites.gz", env); cands[0] = envp; }
    for (int i = 0; i < 4; i++) {
        if (cands[i] && file_exists(cands[i])) { snprintf(out, max_out, "%.550s", cands[i]); return 1; }
    }
#ifndef KAREL_CORE_TEST
    char exe[512]; ssize_t el = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
    if (el > 0) {
        exe[el] = 0; char *sl = strrchr(exe, '/');
        if (sl) { *sl = 0; snprintf(out, max_out, "%.480s/karel_sprites.gz", exe); if (file_exists(out)) return 1; }
    }
#endif
    return 0;
}

#ifndef KAREL_CORE_TEST

/* =========================================================================
 * 5. Linux Audio, Serial, GitHub Auto-Updater, X11 Widgets & Parity
 * ========================================================================= */

static void sleep_ms(int ms) {
    struct timespec ts; ts.tv_sec = ms / 1000; ts.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

static void play_sound_key(const char *key, int muted, int auto_quiet) {
    if (muted || auto_quiet) return;
    static const struct { const char *k; double f[4]; int n; double dur; double amp; } tbl[] = {
        {"climb", {330, 392, 523.25, 0}, 3, 0.065, 0.20},
        {"pet", {523.25, 659.25, 783.99, 0}, 3, 0.055, 0.18},
        {"eat", {293.66, 349.23, 440, 0}, 3, 0.06, 0.20},
        {"coffee", {440, 554.37, 659.25, 880}, 4, 0.05, 0.20},
        {"boop", {587.33, 783.99, 1046.5, 0}, 3, 0.06, 0.22},
        {"levelup", {440, 554.37, 659.25, 880}, 4, 0.09, 0.22},
        {"dive", {659.25, 523.25, 392.0, 261.63}, 4, 0.08, 0.20},
        {"sneeze", {780, 220, 0, 0}, 2, 0.08, 0.22},
        {"chirp", {620, 740, 0, 0}, 2, 0.035, 0.12}
    };
    int idx = -1;
    for (int i = 0; i < 9; i++) if (strcmp(tbl[i].k, key) == 0) { idx = i; break; }
    if (idx < 0) return;
    char path[128]; snprintf(path, sizeof(path), "/tmp/karel_snd_%.24s.wav", key);
    if (!file_exists(path)) {
        uint8_t wav[44 + 16384 * 2];
        size_t wn = build_wav_bytes(tbl[idx].f, tbl[idx].n, tbl[idx].dur, tbl[idx].amp, wav, sizeof(wav));
        FILE *fp = fopen(path, "wb"); if (fp) { fwrite(wav, 1, wn, fp); fclose(fp); }
    }
    if (fork() == 0) {
        int devnull = open("/dev/null", O_RDWR);
        if (devnull >= 0) { dup2(devnull, 0); dup2(devnull, 1); dup2(devnull, 2); close(devnull); }
        execlp("aplay", "aplay", "-q", path, (char *)NULL);
        execlp("paplay", "paplay", path, (char *)NULL);
        execlp("pw-play", "pw-play", path, (char *)NULL);
        _exit(0);
    }
}

typedef struct { int fd; char port[64], last_state[48], rbuf[256]; size_t rlen; time_t last_probe; } LinuxSerial;

static void ser_drop(LinuxSerial *s) {
    if (s->fd >= 0) close(s->fd);
    s->fd = -1; s->port[0] = 0; s->last_state[0] = 0; s->rlen = 0;
}

static void ser_send(LinuxSerial *s, const char *line) {
    if (s->fd < 0) return;
    if (strncmp(line, "STATE:", 6) == 0) {
        if (strcmp(line, s->last_state) == 0) return;
        snprintf(s->last_state, sizeof(s->last_state), "%.47s", line);
    }
    char out[128]; int n = snprintf(out, sizeof(out), "%.120s\n", line);
    if (n > 0 && write(s->fd, out, (size_t)n) < 0 && errno != EAGAIN) ser_drop(s);
}

static void ser_poll(LinuxSerial *s, char *ev_out, size_t max_ev) {
    ev_out[0] = 0; time_t now = time(NULL);
    if (s->fd < 0) {
        (void)now;
        static int probe_cd = 0;
        if (probe_cd-- > 0) return;
        probe_cd = 6;
        DIR *dp = opendir("/dev"); if (!dp) return;
        char cands[16][64]; int nc = 0;
        struct dirent *de;
        while ((de = readdir(dp)) != NULL && nc < 16) {
            if (strncmp(de->d_name, "ttyACM", 6) == 0 || strncmp(de->d_name, "ttyUSB", 6) == 0) {
                snprintf(cands[nc++], 64, "%.63s", de->d_name);
            }
        }
        closedir(dp);
        for (int i = nc - 1; i > 0; i--) {
            for (int j = 0; j < i; j++) {
                if (strcmp(cands[j], cands[j + 1]) < 0) {
                    char swp[64]; memcpy(swp, cands[j], 64); memcpy(cands[j], cands[j + 1], 64); memcpy(cands[j + 1], swp, 64);
                }
            }
        }
        for (int ci = 0; ci < nc; ci++) {
            char p[256]; snprintf(p, sizeof(p), "/dev/%.120s", cands[ci]);
            int fd = open(p, O_RDWR | O_NOCTTY | O_NONBLOCK); if (fd < 0) continue;
            struct termios tio; tcgetattr(fd, &tio);
            tio.c_iflag &= ~(tcflag_t)(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL | IXON);
            tio.c_oflag &= ~(tcflag_t)OPOST;
            tio.c_lflag &= ~(tcflag_t)(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
            tio.c_cflag &= ~(tcflag_t)(CSIZE | PARENB);
            tio.c_cflag |= CS8 | CLOCAL | CREAD;
            cfsetispeed(&tio, B115200); cfsetospeed(&tio, B115200);
            tcsetattr(fd, TCSANOW, &tio);
            sleep_ms(25); tcflush(fd, TCIFLUSH);
            (void)!write(fd, "KAREL_PING\n", 11);
            sleep_ms(95);
            char b[128]; ssize_t n = read(fd, b, sizeof(b) - 1);
            if (n > 0) {
                b[n] = 0;
                if (strstr(b, "KAREL_PONG")) { s->fd = fd; snprintf(s->port, sizeof(s->port), "%.60s", cands[ci]); return; }
            }
            close(fd);
        }
        return;
    }
    if (s->rlen >= sizeof(s->rbuf) - 1) s->rlen = 0;
    char tmp[128]; ssize_t n = read(s->fd, tmp, sizeof(tmp));
    if (n > 0) {
        size_t avail = sizeof(s->rbuf) - 1 - s->rlen;
        size_t take = (size_t)n < avail ? (size_t)n : avail;
        memcpy(s->rbuf + s->rlen, tmp, take); s->rlen += take; s->rbuf[s->rlen] = 0;
        char *nl = strchr(s->rbuf, '\n');
        if (nl) {
            *nl = 0; size_t l = strlen(s->rbuf);
            if (l > 0 && s->rbuf[l - 1] == '\r') s->rbuf[l - 1] = 0;
            if (strncmp(s->rbuf, "EVENT:", 6) == 0 && max_ev > 1) snprintf(ev_out, max_ev, "%.60s", s->rbuf);
            size_t rem = s->rlen - (size_t)(nl - s->rbuf) - 1;
            memmove(s->rbuf, nl + 1, rem); s->rlen = rem;
        }
    } else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK) { ser_drop(s); return; }
    static int hb = 0;
    if (s->fd >= 0 && ++hb >= 16) { hb = 0; ser_send(s, "KAREL_PING"); }
}

/* Auto-updater helper: uses curl or wget + pure-C99 SHA-256 verification */
static uint8_t *http_get_bytes(const char *url, size_t *out_len) {
    *out_len = 0;
    char cmd[1200];
    snprintf(cmd, sizeof(cmd), "(curl -fsSL --max-time 12 \"%.500s\" || wget -qO- -T 12 \"%.500s\") 2>/dev/null", url, url);
    FILE *fp = popen(cmd, "r"); if (!fp) return NULL;
    size_t cap = 16384, n = 0;
    uint8_t *buf = (uint8_t *)malloc(cap); if (!buf) { pclose(fp); return NULL; }
    while (1) {
        if (n + 4096 + 1 > cap) {
            if (cap > 8 * 1024 * 1024) { free(buf); pclose(fp); return NULL; }
            cap *= 2; buf = (uint8_t *)realloc(buf, cap);
        }
        size_t r = fread(buf + n, 1, 4096, fp);
        n += r;
        if (r == 0) break;
    }
    int rc = pclose(fp);
    if (rc != 0 || n == 0) { free(buf); return NULL; }
    buf[n] = 0; *out_len = n;
    return buf;
}

static int eq_ci(const char *a, const char *b) {
    while (*a && *b) {
        if (tolower((unsigned char)*a++) != tolower((unsigned char)*b++)) return 0;
    }
    return *a == *b;
}

static int write_verified_file(const char *dst, const char *url, const char *expected_sha, size_t min_bytes) {
    size_t n = 0;
    uint8_t *buf = http_get_bytes(url, &n);
    if (!buf || n < min_bytes) { free(buf); return 0; }
    char got[65]; sha256_hex(buf, n, got);
    if (!eq_ci(got, expected_sha)) { free(buf); return 0; }
    char tmp[600]; snprintf(tmp, sizeof(tmp), "%.580s.tmp", dst);
    FILE *fp = fopen(tmp, "wb"); if (!fp) { free(buf); return 0; }
    size_t w = fwrite(buf, 1, n, fp); fclose(fp); free(buf);
    if (w != n) { remove(tmp); return 0; }
    if (min_bytes >= 20000) (void)chmod(tmp, 0755);
    if (rename(tmp, dst) != 0) { remove(tmp); return 0; }
    return 1;
}

static void start_updater_async(const char *drive_root, const char *self_exe, const char *updated_from, int *out_pipe_fd) {
    int pfd[2]; *out_pipe_fd = -1;
    if (pipe(pfd) != 0) return;
    pid_t pid = fork();
    if (pid < 0) { close(pfd[0]); close(pfd[1]); return; }
    if (pid > 0) {
        close(pfd[1]);
        fcntl(pfd[0], F_SETFL, O_NONBLOCK);
        *out_pipe_fd = pfd[0];
        return;
    }
    close(pfd[0]);
    sleep_ms(3500);
    size_t mlen = 0;
    uint8_t *mraw = http_get_bytes(KAREL_MANIFEST_URL, &mlen);
    if (mraw && mlen > 10) {
        char rem_ver[32] = "", bin_url[512] = "", bin_sha[80] = "", spr_url[512] = "", spr_sha[80] = "", fw_url[512] = "", fw_sha[80] = "";
        json_find_str((const char *)mraw, "version", rem_ver, sizeof(rem_ver));
#if defined(__aarch64__)
        json_find_str((const char *)mraw, "linux_arm64_url", bin_url, sizeof(bin_url));
        json_find_str((const char *)mraw, "linux_arm64_sha256", bin_sha, sizeof(bin_sha));
#endif
        if (!*bin_url) {
            json_find_str((const char *)mraw, "linux_x64_url", bin_url, sizeof(bin_url));
            json_find_str((const char *)mraw, "linux_x64_sha256", bin_sha, sizeof(bin_sha));
        }
        json_find_str((const char *)mraw, "sprites_url", spr_url, sizeof(spr_url));
        json_find_str((const char *)mraw, "sprites_sha256", spr_sha, sizeof(spr_sha));
        json_find_str((const char *)mraw, "code_py_url", fw_url, sizeof(fw_url));
        json_find_str((const char *)mraw, "code_py_sha256", fw_sha, sizeof(fw_sha));
        free(mraw);

        if (*rem_ver && compare_ver(rem_ver, KAREL_VERSION) > 0 && (!*updated_from || compare_ver(rem_ver, updated_from) != 0) && *bin_url && *bin_sha) {
            if (*drive_root) {
                char bootp[600], codep[600];
                snprintf(bootp, sizeof(bootp), "%.500s/boot.py", drive_root);
                snprintf(codep, sizeof(codep), "%.500s/code.py", drive_root);
                if (file_exists(bootp) && file_exists(codep) && *fw_url && *fw_sha) {
                    FILE *cf = fopen(codep, "rb");
                    if (cf) {
                        uint8_t cur[65536]; size_t cn = fread(cur, 1, sizeof(cur), cf); fclose(cf);
                        char csha[65]; sha256_hex(cur, cn, csha);
                        if (!eq_ci(csha, fw_sha)) (void)write_verified_file(codep, fw_url, fw_sha, 500);
                    }
                }
            }
            if (*spr_url && *spr_sha) {
                char sdir[512], sp[600]; snprintf(sdir, sizeof(sdir), "%.500s", self_exe);
                char *sl = strrchr(sdir, '/');
                if (sl) { *sl = 0; snprintf(sp, sizeof(sp), "%.500s/karel_sprites.gz", sdir); (void)write_verified_file(sp, spr_url, spr_sha, 1000); }
                if (*drive_root) { snprintf(sp, sizeof(sp), "%.500s/karel_sprites.gz", drive_root); (void)write_verified_file(sp, spr_url, spr_sha, 1000); }
            }
            if (write_verified_file(self_exe, bin_url, bin_sha, 20000)) {
                chmod(self_exe, 0755);
                if (*drive_root) {
                    char usb_b[600];
                    snprintf(usb_b, sizeof(usb_b), "%.500s/karel_linux_x86_64", drive_root);
                    (void)write_verified_file(usb_b, bin_url, bin_sha, 20000);
                    snprintf(usb_b, sizeof(usb_b), "%.500s/karel_linux", drive_root);
                    (void)write_verified_file(usb_b, bin_url, bin_sha, 20000);
                }
                char msg[48]; snprintf(msg, sizeof(msg), "%.31s", rem_ver);
                (void)!write(pfd[1], msg, strlen(msg));
            }
        }
    } else free(mraw);
    close(pfd[1]);
    _exit(0);
}

static int try_signal_existing(int toggle, uint16_t port) {
    int s = socket(AF_INET, SOCK_STREAM, 0); if (s < 0) return 0;
    struct sockaddr_in a; memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (connect(s, (struct sockaddr *)&a, sizeof(a)) < 0) { close(s); return 0; }
    const char *m = toggle ? "TOGGLE\n" : "BOOP\n";
    (void)!write(s, m, strlen(m)); close(s);
    return 1;
}

static int start_ipc_server(uint16_t port) {
    int s = socket(AF_INET, SOCK_STREAM, 0); if (s < 0) return -1;
    int yes = 1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    fcntl(s, F_SETFL, O_NONBLOCK);
    struct sockaddr_in a; memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(s, (struct sockaddr *)&a, sizeof(a)) < 0 || listen(s, 8) < 0) { close(s); return -1; }
    return s;
}

/* =========================================================================
 * 6. X11 App State, Particles, Ledges, Popup Menus & Dark-Mode Hub
 * ========================================================================= */

typedef struct { int x, y, w, h, id; } HubBtn;
typedef struct { double x, y, vx, vy; int life; char ch[2]; uint8_t r, g, b; } Particle;
typedef struct { char lbl[48]; int kind, idx; } PopItem;

enum { POP_NONE = 0, POP_MAIN, POP_TRICKS, POP_ROAM, POP_SCALE, POP_SKIN, POP_OUTFIT };

typedef struct {
    Display *dpy; int scr;
    Window root, karel_win, hub_win, pop_win;
    GC karel_gc, hub_gc, pop_gc, mask_gc;
    XFontStruct *font, *bfont;
    Atom wm_del;
    float dpi;

    SpriteBank sb; SaveStore save; LinuxSerial ser;
    int ipc_fd, upd_pipe;
    char self_exe[512], upd_ver[32], updated_from[32];

    char state[32], bubble[160], climb_msg[128], dive_mode[16];
    int scale, frame_idx, act_ticks, bubble_ticks, disco_ticks, hyper_ticks, nose_clicks;
    int climb_step, close_step, roam_ticks, roam_wait, ledge_ticks;
    int muted, auto_paused, umbrella_fall, hidden, focus_active, has_ledge;
    int climbing, closing, dragging, flying, drag_dx, drag_dy, drag_sx, drag_sy, has_pq;
    double wx, wy, roam_tx, roam_ty, jump_y, jump_vy, fling_vx, fling_vy, close_sy, pq_x, pq_y;
    int ledge_x, ledge_y, ledge_w, focus_rem, quit_req;
    time_t focus_last, last_auto_say, last_nose_t, last_drag_t, coffee_t[3];
    int coffee_n;

    Particle parts[24];
    int nparts;
    KeySym konami[10]; int nkonami;

    HubBtn hub_btns[18]; int nhub_btns;
    int pop_mode, pop_w, pop_h, pop_hover;
    PopItem pop_items[22]; int npop;
} KarelApp;

static int Sc(int px, float s) { int v = (int)llround(px * s); return v < 1 ? 1 : v; }

static float get_dpi_scale(Display *dpy) {
    char *v = XGetDefault(dpy, "Xft", "dpi");
    if (v) { double d = atof(v) / 96.0; if (d > 0.9 && d < 3.0) return (float)d; }
    int h = XDisplayHeight(dpy, XDefaultScreen(dpy));
    if (h >= 1800) return 1.75f;
    if (h >= 1350) return 1.35f;
    return 1.0f;
}

static unsigned long rgb_px(Display *dpy, int scr, uint8_t r, uint8_t g, uint8_t b) {
    static struct { uint32_t key; unsigned long px; int valid; } cache[80];
    static int cache_n = 0;
    uint32_t k = ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
    for (int i = 0; i < cache_n; i++) if (cache[i].valid && cache[i].key == k) return cache[i].px;
    XColor c; c.red = (unsigned short)r * 257; c.green = (unsigned short)g * 257; c.blue = (unsigned short)b * 257;
    c.flags = DoRed | DoGreen | DoBlue;
    XAllocColor(dpy, XDefaultColormap(dpy, scr), &c);
    if (cache_n < 80) { cache[cache_n].key = k; cache[cache_n].px = c.pixel; cache[cache_n].valid = 1; cache_n++; }
    return c.pixel;
}

static void get_work_area(Display *dpy, int scr, int *x, int *y, int *w, int *h) {
    *x = 0; *y = 0; *w = XDisplayWidth(dpy, scr); *h = XDisplayHeight(dpy, scr);
    Atom a = XInternAtom(dpy, "_NET_WORKAREA", True), rt;
    int fmt; unsigned long n, rem; unsigned char *data = NULL;
    if (a != None && XGetWindowProperty(dpy, XRootWindow(dpy, scr), a, 0, 4, False, XA_CARDINAL, &rt, &fmt, &n, &rem, &data) == Success && data) {
        if (n >= 4) { long *v = (long *)data; *x = (int)v[0]; *y = (int)v[1]; *w = (int)v[2]; *h = (int)v[3]; }
        XFree(data);
    }
}

static int query_active_win(KarelApp *k, int wa_x, int wa_y, int wa_w, int wa_h, int *rx, int *ry, int *rw, int *rh, char *title, size_t max_t) {
    title[0] = 0;
    Atom a = XInternAtom(k->dpy, "_NET_ACTIVE_WINDOW", True), rt;
    int fmt; unsigned long n, rem; unsigned char *data = NULL;
    if (a == None || XGetWindowProperty(k->dpy, k->root, a, 0, 1, False, XA_WINDOW, &rt, &fmt, &n, &rem, &data) != Success || !data) return 0;
    Window aw = 0; if (n >= 1) aw = *(Window *)data;
    XFree(data);
    if (!aw || aw == k->karel_win || aw == k->hub_win || aw == k->pop_win) return 0;

    Window r; int gx = 0, gy = 0, tx = 0, ty = 0; unsigned gw = 0, gh = 0, bw = 0, dep = 0;
    if (!XGetGeometry(k->dpy, aw, &r, &gx, &gy, &gw, &gh, &bw, &dep)) return 0;
    Window ch = 0;
    if (!XTranslateCoordinates(k->dpy, aw, k->root, 0, 0, &tx, &ty, &ch)) return 0;
    int top_frame = 0;
    Atom fe = XInternAtom(k->dpy, "_NET_FRAME_EXTENTS", True); data = NULL;
    if (fe != None && XGetWindowProperty(k->dpy, aw, fe, 0, 4, False, XA_CARDINAL, &rt, &fmt, &n, &rem, &data) == Success && data) {
        if (n >= 4) { long *v = (long *)data; tx -= (int)v[0]; ty -= (int)v[2]; top_frame = (int)v[2]; gw += (unsigned)(v[0] + v[1]); gh += (unsigned)(v[2] + v[3]); }
        XFree(data);
    }
    (void)top_frame; (void)wa_x; (void)wa_y; (void)wa_w; (void)wa_h;
    *rx = tx; *ry = ty; *rw = (int)gw; *rh = (int)gh;

    Atom nm = XInternAtom(k->dpy, "_NET_WM_NAME", True);
    if (nm == None) nm = XInternAtom(k->dpy, "WM_NAME", True);
    data = NULL;
    if (nm != None && XGetWindowProperty(k->dpy, aw, nm, 0, 64, False, AnyPropertyType, &rt, &fmt, &n, &rem, &data) == Success && data) {
        size_t cp = n < max_t - 1 ? n : max_t - 1; memcpy(title, data, cp); title[cp] = 0; XFree(data);
    }
    for (size_t i = 0; title[i]; i++) title[i] = (char)tolower((unsigned char)title[i]);
    return 1;
}

static int detect_auto_quiet(KarelApp *k, int wa_x, int wa_y, int wa_w, int wa_h) {
    int x, y, w, h; char ttl[160];
    if (!query_active_win(k, wa_x, wa_y, wa_w, wa_h, &x, &y, &w, &h, ttl, sizeof(ttl))) return 0;
    static const char *mks[] = {"zoom meeting", "microsoft teams", "google meet", "meet - ", "webex", "powerpoint", "libreoffice impress", NULL};
    for (int i = 0; mks[i]; i++) if (strstr(ttl, mks[i])) return 1;
    int sw = XDisplayWidth(k->dpy, k->scr), sh = XDisplayHeight(k->dpy, k->scr);
    if (x <= 2 && y <= 2 && w >= sw - 2 && h >= sh - 2) return 1;
    return 0;
}

static void say_msg(KarelApp *k, const char *m, int ticks) {
    if (!k->auto_paused) { snprintf(k->bubble, sizeof(k->bubble), "%.155s", m); k->bubble_ticks = ticks; }
}
static void set_act(KarelApp *k, const char *st, int ticks) {
    if (!k->climbing) { snprintf(k->state, sizeof(k->state), "%.31s", st); k->act_ticks = ticks; }
}
static int is_en(const KarelApp *k) { return strcmp(k->save.language, "en") == 0; }
static int px_sz(const KarelApp *k) { return 32 * k->scale; }
static int win_w(const KarelApp *k) { int p = px_sz(k) + Sc(142, k->dpi); int mn = Sc(260, k->dpi); return p < mn ? mn : p; }
static int win_h(const KarelApp *k) { return px_sz(k) + Sc(84, k->dpi); }
static int k_ox(const KarelApp *k) { return (win_w(k) - px_sz(k)) / 2; }
static int k_oy(const KarelApp *k) { return win_h(k) - px_sz(k) - 12; }

static void spawn_particles(KarelApp *k, const char *ch, uint8_t r, uint8_t g, uint8_t b, int count) {
    for (int i = 0; i < count && k->nparts < 24; i++) {
        Particle *pt = &k->parts[k->nparts++];
        pt->x = win_w(k) * 0.5 + (rand() % 48) - 24;
        pt->y = k_oy(k) + (rand() % 20) + 4;
        pt->vx = ((rand() % 100) / 100.0 - 0.5) * 4.5;
        pt->vy = -1.8 - ((rand() % 100) / 100.0) * 3.0;
        pt->life = 12 + (rand() % 10);
        pt->ch[0] = ch[0]; pt->ch[1] = 0; pt->r = r; pt->g = g; pt->b = b;
    }
}

static void draw_hub(KarelApp *k);
static void open_hub(KarelApp *k);

static void award_xp(KarelApp *k, int amt) {
    int old_l = level_from_xp(k->save.xp);
    k->save.xp += amt; k->save.level = level_from_xp(k->save.xp);
    if (k->save.level > old_l) {
        play_sound_key("levelup", k->muted, k->auto_paused);
        set_act(k, (rand() & 1) ? "BACKFLIP" : "PARTY_HORN", 42);
        spawn_particles(k, "*", 245, 196, 81, 14);
        char m[64]; snprintf(m, sizeof(m), "LEVEL UP! Lv.%d!", k->save.level);
        say_msg(k, m, 75);
    }
}

static void trigger_climb(KarelApp *k, const char *msg) {
    int wx, wy, ww, wh; get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);
    k->flying = 0; k->umbrella_fall = 0; k->jump_y = 0;
    k->wy = wy + wh - (k_oy(k) + px_sz(k));
    k->climbing = 1; k->climb_step = 0; snprintf(k->climb_msg, sizeof(k->climb_msg), "%.120s", msg);
    k->roam_tx = k->wx; k->roam_ty = k->wy; k->roam_wait = 95;
    play_sound_key("climb", k->muted, k->auto_paused);
    say_msg(k, is_en(k) ? "Climbing up..." : "Even omhoog klimmen...", 26);
}

static void do_pet(KarelApp *k) {
    k->save.happiness = clamp_int(k->save.happiness + 14, 0, 100); k->save.total_pets++;
    set_act(k, k->save.happiness >= 95 ? "LOVE" : "PET", 28); award_xp(k, 8);
    spawn_particles(k, "*", 255, 122, 144, 6);
    play_sound_key("pet", k->muted, k->auto_paused); ser_send(&k->ser, "EVENT:HEART");
    say_msg(k, is_en(k) ? "Aww! Sticky love! +8 XP" : "Heerlijk! Sticky liefde! +8 XP", 45);
    save_persist(&k->save); draw_hub(k);
}

static void do_feed(KarelApp *k) {
    k->save.hunger = clamp_int(k->save.hunger + 24, 0, 100);
    k->save.happiness = clamp_int(k->save.happiness + 8, 0, 100);
    k->save.hygiene = clamp_int(k->save.hygiene - 2, 0, 100);
    set_act(k, "EAT", 28); award_xp(k, 7);
    spawn_particles(k, "+", 62, 207, 142, 5);
    play_sound_key("eat", k->muted, k->auto_paused);
    say_msg(k, is_en(k) ? "Fresh eucalyptus! Yummm!" : "Verse eucalyptus! Smullen!", 45);
    save_persist(&k->save); draw_hub(k);
}

static void do_coffee(KarelApp *k) {
    k->save.energy = clamp_int(k->save.energy + 22, 0, 100);
    k->save.caffeine = clamp_int(k->save.caffeine + 25, 0, 100);
    set_act(k, "COFFEE", 28); award_xp(k, 9);
    spawn_particles(k, "~", 245, 196, 81, 6);
    play_sound_key("coffee", k->muted, k->auto_paused);
    time_t now = time(NULL); int keep = 0;
    for (int i = 0; i < k->coffee_n; i++) if (difftime(now, k->coffee_t[i]) <= 120) k->coffee_t[keep++] = k->coffee_t[i];
    if (keep < 3) k->coffee_t[keep++] = now; else { k->coffee_t[0] = k->coffee_t[1]; k->coffee_t[1] = k->coffee_t[2]; k->coffee_t[2] = now; }
    k->coffee_n = keep;
    if (k->coffee_n >= 3) {
        k->hyper_ticks = 95; ser_send(&k->ser, "STATE:HYPER");
        say_msg(k, is_en(k) ? "CAFFEINE OVERDOSE! 200 MHz!" : "CAFEINE OVERDOSIS! 200 MHz MODE!", 75);
    } else say_msg(k, is_en(k) ? "Sticky espresso boost! +9 XP" : "Sticky koffie boost! +9 XP", 45);
    save_persist(&k->save); draw_hub(k);
}

static void do_wash(KarelApp *k) {
    k->save.hygiene = clamp_int(k->save.hygiene + 35, 0, 100);
    k->save.happiness = clamp_int(k->save.happiness + 10, 0, 100);
    set_act(k, "WASH", 30); award_xp(k, 8);
    spawn_particles(k, "o", 79, 195, 247, 7);
    play_sound_key("pet", k->muted, k->auto_paused);
    say_msg(k, is_en(k) ? "Sparkling clean!" : "Lekker fris gewassen!", 45);
    save_persist(&k->save); draw_hub(k);
}

static void nap_toggle(KarelApp *k) {
    if (strcmp(k->state, "SLEEP") == 0) { strcpy(k->state, "STRETCH"); k->act_ticks = 18; say_msg(k, is_en(k) ? "Good morning! Refreshed!" : "Goedemorgen! Uitgerust!", 40); }
    else { strcpy(k->state, "SLEEP"); k->act_ticks = 220; play_sound_key("dive", k->muted, k->auto_paused); say_msg(k, "Zzz... Sticky powernap!", 45); }
}

static void trigger_konami(KarelApp *k) {
    k->disco_ticks = 115; strcpy(k->save.equipped, "shades");
    set_act(k, "DANCE", 65); spawn_particles(k, "*", 245, 196, 81, 16);
    ser_send(&k->ser, "STATE:PARTY"); play_sound_key("levelup", k->muted, k->auto_paused);
    say_msg(k, is_en(k) ? "DISCO BORREL MODE ON!" : "DISCO BORREL MODE AAN!", 80);
    save_persist(&k->save); draw_hub(k);
}

static void do_boop(KarelApp *k) {
    award_xp(k, 10); play_sound_key("boop", k->muted, k->auto_paused);
    spawn_particles(k, "*", 245, 196, 81, 10);
    trigger_climb(k, "SuperMini Boop! +10 XP!");
    save_persist(&k->save); draw_hub(k);
}

static void trigger_dive(KarelApp *k, const char *mode) {
    if (k->closing) return;
    snprintf(k->dive_mode, sizeof(k->dive_mode), "%.15s", mode);
    k->closing = 1; k->close_step = 0; k->climbing = 0; k->flying = 0; k->dragging = 0; k->umbrella_fall = 0;
    k->jump_y = 0; k->close_sy = k->wy; k->act_ticks = 0;
    say_msg(k, strcmp(mode, "tray") == 0 ? (is_en(k) ? "Napping! --toggle to wake" : "Dutje! --toggle wekt Karel")
                                         : (is_en(k) ? "See ya! Diving back!" : "Tot ziens! Ik duik weg!"), 40);
    spawn_particles(k, "*", 255, 122, 144, 4);
    play_sound_key("dive", k->muted, k->auto_paused);
}

static void paint_karel(KarelApp *k) {
    int W = win_w(k), H = win_h(k), ox = k_ox(k), oy = k_oy(k), p = px_sz(k);
    char rst[32]; snprintf(rst, sizeof(rst), "%.31s", k->state);
    int clip = 32;
    if (k->closing) {
        if (k->close_step <= 9) strcpy(rst, "DIVE_WAVE");
        else if (k->close_step <= 13) strcpy(rst, "JUMP");
        else { strcpy(rst, "DIVE_DOWN"); clip = (int)llround(32.0 * (1.0 - (k->close_step - 13) / 13.0)); if (clip < 0) clip = 0; }
    } else if (k->climbing) {
        strcpy(rst, "CLIMB"); clip = (int)llround(32.0 * (k->climb_step < 17 ? k->climb_step / 17.0 : 1.0)); if (clip < 2) clip = 2;
    } else if (strcmp(rst, "IDLE") == 0) {
        time_t now = time(NULL); struct tm *lt = localtime(&now);
        if (k->hyper_ticks > 0) strcpy(rst, "HYPER");
        else if (lt && lt->tm_hour >= 23 && k->act_ticks == 0) strcpy(rst, "SLEEP");
        else if (k->save.hunger < 25) strcpy(rst, "HUNGRY");
    }

    Rgba frame[32][32];
    render_frame_rgba(&k->sb, rst, k->frame_idx, k->save.skin, k->save.equipped, frame);

    Pixmap mask = XCreatePixmap(k->dpy, k->karel_win, (unsigned)W, (unsigned)H, 1);
    if (!k->mask_gc) k->mask_gc = XCreateGC(k->dpy, mask, 0, NULL);
    XSetForeground(k->dpy, k->mask_gc, 0); XFillRectangle(k->dpy, mask, k->mask_gc, 0, 0, (unsigned)W, (unsigned)H);
    XSetForeground(k->dpy, k->mask_gc, 1);
    XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 1, 2, 3));
    XFillRectangle(k->dpy, k->karel_win, k->karel_gc, 0, 0, (unsigned)W, (unsigned)H);

    if (!k->climbing && !k->closing) {
        int ins = p / 5; if (ins < 8) ins = 8;
        int sw = p - 2 * ins; if (sw < 12) sw = 12;
        XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 24, 28, 38));
        XFillArc(k->dpy, k->karel_win, k->karel_gc, ox + ins, oy + p - 4, (unsigned)sw, 7, 0, 360 * 64);
        XFillArc(k->dpy, mask, k->mask_gc, ox + ins, oy + p - 4, (unsigned)sw, 7, 0, 360 * 64);
    }

    for (int y = 0; y < clip; y++) {
        for (int x = 0; x < 32; x++) {
            Rgba c = frame[y][x]; if (!c.a) continue;
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
        int tw = f ? XTextWidth(f, k->bubble, (int)strlen(k->bubble)) : (int)strlen(k->bubble) * 7;
        int bw = tw + 20; if (bw < 76) bw = 76; if (bw > W - 10) bw = W - 10;
        int bh = 26, bx = (W - bw) / 2, by = oy - bh - 12; if (by < 4) by = 4;
        int tx = W / 2;
        XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 248, 250, 255));
        XFillRectangle(k->dpy, k->karel_win, k->karel_gc, bx, by, (unsigned)bw, (unsigned)bh);
        XFillRectangle(k->dpy, mask, k->mask_gc, bx, by, (unsigned)bw, (unsigned)bh);
        XPoint tri[3] = {{(short)(tx - 5), (short)(by + bh)}, {(short)(tx + 5), (short)(by + bh)}, {(short)tx, (short)(by + bh + 6)}};
        XFillPolygon(k->dpy, k->karel_win, k->karel_gc, tri, 3, Convex, CoordModeOrigin);
        XFillPolygon(k->dpy, mask, k->mask_gc, tri, 3, Convex, CoordModeOrigin);
        XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 196, 30, 37));
        XFillRectangle(k->dpy, k->karel_win, k->karel_gc, bx, by, 4, (unsigned)bh);
        XDrawRectangle(k->dpy, k->karel_win, k->karel_gc, bx, by, (unsigned)bw - 1, (unsigned)bh - 1);
        XSetForeground(k->dpy, k->karel_gc, rgb_px(k->dpy, k->scr, 20, 24, 34));
        XDrawString(k->dpy, k->karel_win, k->karel_gc, bx + 10, by + 17, k->bubble, (int)strlen(k->bubble));
    }

    XShapeCombineMask(k->dpy, k->karel_win, ShapeBounding, 0, 0, mask, ShapeSet);
    XFreePixmap(k->dpy, mask);
}

/* Tricks & Popup / Dropdown Menu */
static const struct { const char *lbl, *st, *msg; } TRICKS[] = {
    {"Backflip!", "BACKFLIP", "Wooo! Koala Backflip!!"},
    {"360 Spin", "SPIN", "Swoosh!"},
    {"Jetpack", "JETPACK", "Naar de BBG-maan!"},
    {"Peek", "PEEK", "Psst... zie je me?"},
    {"Laptop Coding", "LAPTOP_CODE", "git commit -m 'fix'"},
    {"Debug Magnifier", "MAGNIFY", "Zoekende naar bugs..."},
    {"Paper Plane", "PAPER_PLANE", "Zoooef!"},
    {"Sticky Umbrella", "UMBRELLA", "Typisch Nederlands weer!"},
    {"Ear Wiggle", "EARS_WIGGLE", "*Wiebel wiebel*"},
    {"Hug Plush", "HUG_PLUSH", "Sticky liefde!"},
    {"Eucalyptus Hug", "EUCALYPTUS_HUG", "Favoriete tak!"},
    {"Party Horn", "PARTY_HORN", "VrijMiBo tijd!"},
    {"Polite Bow", "BOW", "Dankjewel!"},
    {"Wave Hello", "WAVE", "Hoi!!"},
    {"Guitar Solo", "GUITAR", "8-bit riff!"},
    {"Drums", "DRUM", "Ba-dum-tss!"},
    {"Flex Muscles", "FLEX", "RP2350 spierkracht!"},
    {"Dance", "DANCE", "De Vagant boogie!"}
};

static void close_popup(KarelApp *k) {
    if (k->pop_win) { XDestroyWindow(k->dpy, k->pop_win); k->pop_win = 0; k->pop_mode = POP_NONE; }
}

static void draw_popup(KarelApp *k) {
    if (!k->pop_win) return;
    int rh = 26;
    XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 27, 31, 42));
    XFillRectangle(k->dpy, k->pop_win, k->pop_gc, 0, 0, (unsigned)k->pop_w, (unsigned)k->pop_h);
    XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 196, 30, 37));
    XDrawRectangle(k->dpy, k->pop_win, k->pop_gc, 0, 0, (unsigned)k->pop_w - 1, (unsigned)k->pop_h - 1);
    if (k->font) XSetFont(k->dpy, k->pop_gc, k->font->fid);
    for (int i = 0; i < k->npop; i++) {
        int y = 4 + i * rh;
        if (strcmp(k->pop_items[i].lbl, "---") == 0) {
            XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 62, 70, 90));
            XFillRectangle(k->dpy, k->pop_win, k->pop_gc, 8, y + 12, (unsigned)(k->pop_w - 16), 1);
            continue;
        }
        if (i == k->pop_hover) {
            XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 168, 32, 42));
            XFillRectangle(k->dpy, k->pop_win, k->pop_gc, 3, y + 1, (unsigned)(k->pop_w - 6), (unsigned)(rh - 2));
        }
        XSetForeground(k->dpy, k->pop_gc, rgb_px(k->dpy, k->scr, 242, 245, 250));
        XDrawString(k->dpy, k->pop_win, k->pop_gc, 12, y + 17, k->pop_items[i].lbl, (int)strlen(k->pop_items[i].lbl));
    }
}

static void open_popup(KarelApp *k, int mode, int rx, int ry) {
    close_popup(k);
    k->npop = 0; k->pop_mode = mode; k->pop_hover = -1;
    int en = is_en(k);
    #define P_ADD(txt, kd, ix) do { if (k->npop < 22) { snprintf(k->pop_items[k->npop].lbl, 48, "%.47s", (txt)); k->pop_items[k->npop].kind = (kd); k->pop_items[k->npop].idx = (ix); k->npop++; } } while (0)
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
        P_ADD(en ? "Tricks (18)  >" : "Trucjes (18)  >", 3, POP_TRICKS);
        P_ADD(en ? "Roam Mode  >" : "Loopgedrag  >", 3, POP_ROAM);
        P_ADD(en ? "Size  >" : "Grootte  >", 3, POP_SCALE);
        P_ADD(en ? "Sound On/Off" : "Geluid Aan/Uit", 4, 0);
        P_ADD(en ? "Auto-Quiet Fullscreen" : "Auto-Stil Fullscreen", 4, 1);
        P_ADD(en ? "Language: NL / EN" : "Taal: NL / EN", 4, 2);
        P_ADD("---", 0, 0);
        P_ADD(en ? "Hide (Ctrl/Cmd --toggle)" : "Verberg (--toggle)", 4, 3);
        P_ADD(en ? "Dive & Quit" : "Duik & Sluit", 4, 4);
    } else if (mode == POP_TRICKS) {
        for (int i = 0; i < 18; i++) P_ADD(TRICKS[i].lbl, 5, i);
    } else if (mode == POP_ROAM) {
        P_ADD(en ? "Free Roam" : "Heel Scherm", 6, 0);
        P_ADD(en ? "Active Window" : "Op Actief Venster", 6, 1);
        P_ADD(en ? "Follow Mouse" : "Volg Muis", 6, 2);
        P_ADD(en ? "Stay Put" : "Blijf Zitten", 6, 3);
    } else if (mode == POP_SCALE) {
        for (int s = 2; s <= 5; s++) { char b[32]; snprintf(b, sizeof(b), "%dx (%dpx)", s, s * 32); P_ADD(b, 7, s); }
    } else if (mode == POP_SKIN) {
        for (int i = 0; i < NUM_SKINS; i++) {
            char b[48]; snprintf(b, sizeof(b), "%s%s", strcmp(k->save.skin, SKIN_IDS[i]) == 0 ? "* " : "  ", SKIN_IDS[i]);
            P_ADD(b, 8, i);
        }
    } else if (mode == POP_OUTFIT) {
        for (int i = 0; i < NUM_OUTFITS; i++) {
            const char *nm = *OUTFIT_IDS[i] ? OUTFIT_IDS[i] : (en ? "(none)" : "(geen)");
            char b[48]; snprintf(b, sizeof(b), "%s%s", strcmp(k->save.equipped, OUTFIT_IDS[i]) == 0 ? "* " : "  ", nm);
            P_ADD(b, 9, i);
        }
    }
    #undef P_ADD
    k->pop_w = 220; k->pop_h = 8 + k->npop * 26;
    int sw = XDisplayWidth(k->dpy, k->scr), sh = XDisplayHeight(k->dpy, k->scr);
    if (rx + k->pop_w > sw - 8) rx = sw - k->pop_w - 8;
    if (ry + k->pop_h > sh - 8) ry = sh - k->pop_h - 8;
    if (rx < 4) rx = 4;
    if (ry < 4) ry = 4;
    XSetWindowAttributes swa; swa.override_redirect = True; swa.background_pixel = rgb_px(k->dpy, k->scr, 27, 31, 42);
    k->pop_win = XCreateWindow(k->dpy, k->root, rx, ry, (unsigned)k->pop_w, (unsigned)k->pop_h,
                               0, CopyFromParent, InputOutput, CopyFromParent, CWOverrideRedirect | CWBackPixel, &swa);
    XSelectInput(k->dpy, k->pop_win, ExposureMask | ButtonPressMask | PointerMotionMask);
    k->pop_gc = XCreateGC(k->dpy, k->pop_win, 0, NULL);
    XMapRaised(k->dpy, k->pop_win);
    draw_popup(k);
}

static void resize_karel_scale(KarelApp *k, int sc) {
    k->scale = clamp_int(sc, 2, 5);
    k->save.karel_scale = k->scale;
    XResizeWindow(k->dpy, k->karel_win, (unsigned)win_w(k), (unsigned)win_h(k));
    int wx, wy, ww, wh; get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);
    int gy = wy + wh - (k_oy(k) + px_sz(k));
    if (k->wy > gy) k->wy = gy;
    save_persist(&k->save);
}

static void click_popup(KarelApp *k, int my, int x_root, int y_root) {
    int i = (my - 4) / 26;
    if (i < 0 || i >= k->npop) { close_popup(k); return; }
    int kd = k->pop_items[i].kind, ix = k->pop_items[i].idx;
    if (kd == 0) return;
    if (kd == 3) { open_popup(k, ix, x_root + 12, y_root - 20); return; }
    close_popup(k);
    if (kd == 1) open_hub(k);
    else if (kd == 2) {
        if (ix == 0) do_feed(k); else if (ix == 1) do_coffee(k); else if (ix == 2) do_pet(k);
        else if (ix == 3) do_wash(k); else if (ix == 4) nap_toggle(k);
        else if (ix == 5) {
            k->focus_active = !k->focus_active;
            if (k->focus_active) { k->focus_rem = 25 * 60; k->focus_last = time(NULL); say_msg(k, "Focus: 25m!", 45); }
            else say_msg(k, is_en(k) ? "Focus stopped." : "Focus gestopt.", 35);
            draw_hub(k);
        }
    } else if (kd == 4) {
        if (ix == 0) { k->muted = !k->muted; draw_hub(k); }
        else if (ix == 1) { k->save.auto_quiet = !k->save.auto_quiet; save_persist(&k->save); draw_hub(k); }
        else if (ix == 2) { strcpy(k->save.language, is_en(k) ? "nl" : "en"); save_persist(&k->save); draw_hub(k); }
        else if (ix == 3) trigger_dive(k, "tray");
        else if (ix == 4) trigger_dive(k, "quit");
    } else if (kd == 5) { set_act(k, TRICKS[ix].st, 42); say_msg(k, TRICKS[ix].msg, 42); }
    else if (kd == 6) {
        static const char *modes[] = {"free", "window", "cursor", "park"};
        snprintf(k->save.roam_mode, sizeof(k->save.roam_mode), "%s", modes[ix]);
        k->umbrella_fall = 0; save_persist(&k->save); say_msg(k, modes[ix], 30);
    } else if (kd == 7) resize_karel_scale(k, ix);
    else if (kd == 8) { snprintf(k->save.skin, sizeof(k->save.skin), "%s", SKIN_IDS[ix]); save_persist(&k->save); draw_hub(k); }
    else if (kd == 9) { snprintf(k->save.equipped, sizeof(k->save.equipped), "%s", OUTFIT_IDS[ix]); save_persist(&k->save); draw_hub(k); }
}

static void add_hub_btn(KarelApp *k, int x, int y, int w, int h, int id) {
    if (k->nhub_btns < 18) k->hub_btns[k->nhub_btns++] = (HubBtn){x, y, w, h, id};
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
    char hdr[96]; snprintf(hdr, sizeof(hdr), "KAREL DE KOALA  *  STICKY RP2350   v%s", KAREL_VERSION);
    XDrawString(k->dpy, k->hub_win, k->hub_gc, P, Sc(28, s), hdr, (int)strlen(hdr));

    int curY = Sc(58, s), cardH = Sc(88, s);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 27, 31, 42));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, P, curY, (unsigned)Win, (unsigned)cardH);
    int lvl = level_from_xp(k->save.xp), p_xp = xp_for_next_level(lvl - 1), n_xp = xp_for_next_level(lvl);
    double pct = (double)(k->save.xp - p_xp) / (double)(n_xp - p_xp > 0 ? n_xp - p_xp : 1);
    if (pct < 0) pct = 0;
    if (pct > 1) pct = 1;
    char l1[96], l2[140];
    snprintf(l1, sizeof(l1), "Lv.%d   -   %d / %d XP", lvl, k->save.xp, n_xp);
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

    k->nhub_btns = 0; curY += cardH + Sc(14, s);
    const char *act_lbls[6] = {en ? "Feed" : "Voer", en ? "Coffee" : "Koffie", en ? "Pet" : "Aai", en ? "Wash" : "Was", "Powernap", k->focus_active ? "Stop Focus" : "Focus 25m"};
    static const uint8_t bc[6][3] = {{38,115,77},{115,75,58},{168,32,90},{13,115,133},{59,74,90},{42,48,66}};
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
    int pkw = (Win - Sc(96, s)) / 2;
    int px0 = P + Sc(78, s), px1 = P + Sc(86, s) + pkw, pw1 = Win - Sc(98, s) - pkw;
    add_hub_btn(k, px0, curY + Sc(8, s), pkw, Sc(32, s), 10);
    add_hub_btn(k, px1, curY + Sc(8, s), pw1, Sc(32, s), 11);
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 42, 48, 66));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, px0, curY + Sc(8, s), (unsigned)pkw, (unsigned)Sc(32, s));
    XFillRectangle(k->dpy, k->hub_win, k->hub_gc, px1, curY + Sc(8, s), (unsigned)pw1, (unsigned)Sc(32, s));
    XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, px0 + Sc(12, s), curY + Sc(28, s), sk_l, (int)strlen(sk_l));
    XDrawString(k->dpy, k->hub_win, k->hub_gc, px1 + Sc(12, s), curY + Sc(28, s), out_l, (int)strlen(out_l));

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
    if (k->save.connected) {
        const char *hl = en ? "USB Safe Mode: Storage + LED Serial (No HID)" : "USB Veilige Modus: Opslag + LED Serial (Geen HID)";
        XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 28, 34, 46));
        XFillRectangle(k->dpy, k->hub_win, k->hub_gc, P, curY, (unsigned)Win, (unsigned)Sc(30, s));
        XSetForeground(k->dpy, k->hub_gc, rgb_px(k->dpy, k->scr, 170, 210, 195));
        XDrawString(k->dpy, k->hub_win, k->hub_gc, P + Sc(14, s), curY + Sc(20, s), hl, (int)strlen(hl));
        curY += Sc(38, s);
    }

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
    if (k->hidden) { k->hidden = 0; XMapRaised(k->dpy, k->karel_win); trigger_climb(k, is_en(k) ? "I'm back!" : "Daar ben ik weer!"); }
    if (k->hub_win) { XMapRaised(k->dpy, k->hub_win); draw_hub(k); return; }
    int W = Sc(560, k->dpi), H = Sc(408, k->dpi);
    k->hub_win = XCreateSimpleWindow(k->dpy, k->root, 200, 160, (unsigned)W, (unsigned)H, 0, 0, rgb_px(k->dpy, k->scr, 18, 20, 27));
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
            if (k->focus_active) { k->focus_rem = 25 * 60; k->focus_last = time(NULL); say_msg(k, "Focus: 25m!", 45); }
            else say_msg(k, is_en(k) ? "Focus stopped." : "Focus gestopt.", 35);
        } else if (b.id == 10) { open_popup(k, POP_SKIN, x_root - mx + b.x, y_root - my + b.y + b.h); return; }
        else if (b.id == 11) { open_popup(k, POP_OUTFIT, x_root - mx + b.x, y_root - my + b.y + b.h); return; }
        else if (b.id == 20) k->muted = !k->muted;
        else if (b.id == 21) { k->save.auto_quiet = !k->save.auto_quiet; save_persist(&k->save); }
        else if (b.id == 22) { strcpy(k->save.language, is_en(k) ? "nl" : "en"); save_persist(&k->save); }
        else if (b.id == 30) { trigger_dive(k, "quit"); return; }
        draw_hub(k); return;
    }
}

static void handle_key_event(KarelApp *k, XKeyEvent *kev) {
    KeySym ks = XLookupKeysym(kev, 0);
    if (ks == XK_A) ks = XK_a;
    if (ks == XK_B) ks = XK_b;
    static const KeySym seq[10] = {XK_Up, XK_Up, XK_Down, XK_Down, XK_Left, XK_Right, XK_Left, XK_Right, XK_b, XK_a};
    if (ks == XK_Up || ks == XK_Down || ks == XK_Left || ks == XK_Right || ks == XK_a || ks == XK_b) {
        if (k->nkonami == 10) { memmove(k->konami, k->konami + 1, sizeof(KeySym) * 9); k->nkonami = 9; }
        k->konami[k->nkonami++] = ks;
        if (k->nkonami == 10 && memcmp(k->konami, seq, sizeof(seq)) == 0) { k->nkonami = 0; trigger_konami(k); }
    } else k->nkonami = 0;
}

static void step_physics(KarelApp *k) {
    static const char *Q_NL[] = {"Eucalyptus? Of toch een Sticky tosti?", "RP2350 SuperMini draait op volle toeren!", "Even uitrekken achter de taakbalk...", "Al een git commit gepusht vandaag?", "Tip: --toggle verstopt of wekt me op!"};
    static const char *Q_EN[] = {"Eucalyptus? Or a Sticky toasted cheese?", "RP2350 SuperMini running smoothly!", "Zero-Install Sticky companion on Linux!", "Did you git commit today?", "Tip: --toggle hides or wakes me!"};
    static const char *N_NL[] = {"Nachtelijke code-sessie? Vergeet geen water!", "Zzz... Karel programmeert mee in stilte.", "Nog een bug en dan lekker slapen?"};

    k->frame_idx++;
    int wx, wy, ww, wh; get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);
    int minx = wx - k_ox(k) + 6, maxx = wx + ww - k_ox(k) - px_sz(k) - 6;
    int miny = wy - k_oy(k) + 6, gy = wy + wh - (k_oy(k) + px_sz(k));

    if (k->frame_idx % 16 == 0) {
        if (k->save.auto_quiet) {
            int busy = detect_auto_quiet(k, wx, wy, ww, wh);
            if (busy && !k->auto_paused) { k->pq_x = k->wx; k->pq_y = k->wy; k->has_pq = 1; k->auto_paused = 1; k->wx = maxx; k->wy = miny; k->bubble[0] = 0; k->bubble_ticks = 0; strcpy(k->state, "IDLE"); }
            else if (!busy && k->auto_paused) { k->auto_paused = 0; if (k->has_pq) { k->wx = k->pq_x; k->wy = k->pq_y; k->has_pq = 0; } }
        } else k->auto_paused = 0;
        int usb = poll_usb(&k->save);
        if (usb < 0) {
            if (k->hub_win) XUnmapWindow(k->dpy, k->hub_win);
            say_msg(k, is_en(k) ? "USB unplugged! Bye!" : "USB los! Doei!", 45);
            trigger_dive(k, "quit");
        } else if (usb > 0) { trigger_climb(k, is_en(k) ? "KAREL USB reconnected!" : "KAREL USB herverbonden!"); draw_hub(k); }
    }

    if (k->upd_pipe >= 0) {
        char buf[32]; ssize_t nr = read(k->upd_pipe, buf, sizeof(buf) - 1);
        if (nr > 0) {
            buf[nr] = 0; snprintf(k->upd_ver, sizeof(k->upd_ver), "%.31s", buf);
            close(k->upd_pipe); k->upd_pipe = -1; k->quit_req = 2;
            say_msg(k, is_en(k) ? "Update installed! Restarting..." : "Update klaar! Herstarten...", 50);
            paint_karel(k); XFlush(k->dpy); sleep_ms(500);
            return;
        }
    }

    if (k->focus_active && difftime(time(NULL), k->focus_last) >= 1.0) {
        k->focus_last = time(NULL);
        if (k->focus_rem > 0) k->focus_rem--;
        if (k->focus_rem == 0) {
            k->focus_active = 0; award_xp(k, 45); set_act(k, "CELEBRATE", 40);
            spawn_particles(k, "*", 245, 196, 81, 14); play_sound_key("levelup", k->muted, k->auto_paused);
            say_msg(k, is_en(k) ? "Focus complete! +45 XP!" : "Focus klaar! +45 XP!", 70);
            save_persist(&k->save); draw_hub(k);
        }
    }

    if (k->closing) {
        k->close_step++;
        if (k->close_step <= 9) k->wy = k->close_sy + (gy - k->close_sy) * (k->close_step / 9.0);
        else if (k->close_step <= 13) { k->wy = gy; k->jump_y = -14.0 * sin((k->close_step - 9) * 3.14159 / 4.0); }
        else { k->wy = gy; k->jump_y = 0; }
        if (k->close_step >= 27) {
            if (strcmp(k->dive_mode, "tray") == 0) { k->closing = 0; k->hidden = 1; save_persist(&k->save); XUnmapWindow(k->dpy, k->karel_win); }
            else k->quit_req = 1;
        }
    } else if (k->climbing) {
        k->climb_step++;
        if (k->climb_step >= 18) { k->climbing = 0; k->jump_vy = -9.0; say_msg(k, k->climb_msg, 65); set_act(k, "WAVE", 28); }
    } else if (k->flying) {
        k->wx += k->fling_vx; k->wy += k->fling_vy; k->fling_vx *= 0.98; k->fling_vy += 1.45;
        if (k->wx < minx) { k->wx = minx; k->fling_vx = -k->fling_vx * 0.65; }
        if (k->wx > maxx) { k->wx = maxx; k->fling_vx = -k->fling_vx * 0.65; }
        if (k->wy < miny) { k->wy = miny; k->fling_vy = fabs(k->fling_vy) * 0.6; }
        if (k->wy >= gy) { k->wy = gy; if (fabs(k->fling_vy) > 5.0) k->fling_vy = -k->fling_vy * 0.45; else { k->flying = 0; strcpy(k->state, "IDLE"); } }
        else strcpy(k->state, "JETPACK");
    } else if (k->umbrella_fall) {
        strcpy(k->state, "UMBRELLA");
        k->wy += 2.6; if (k->wy > gy) k->wy = gy;
        k->wx += sin(k->frame_idx * 0.28) * 1.6;
        if (k->wx < minx) k->wx = minx;
        if (k->wx > maxx) k->wx = maxx;
        if (k->wy >= gy - 0.5) { k->wy = gy; k->umbrella_fall = 0; strcpy(k->state, "IDLE"); k->roam_wait = 80; }
    } else if (!k->dragging && !k->auto_paused && k->act_ticks == 0 && strcmp(k->state, "SLEEP") != 0) {
        if (k->disco_ticks > 0) strcpy(k->state, "DANCE");
        else if (strcmp(k->save.roam_mode, "park") == 0) strcpy(k->state, "IDLE");
        else if (strcmp(k->save.roam_mode, "cursor") == 0) {
            Window rr, cc; int rx = 0, ry = 0, wxx = 0, wyy = 0; unsigned mm = 0;
            if (XQueryPointer(k->dpy, k->root, &rr, &cc, &rx, &ry, &wxx, &wyy, &mm)) {
                double tx = rx - win_w(k) * 0.5, tyc = ry - (k_oy(k) + px_sz(k) * 0.5);
                if (tx < minx) tx = minx;
                if (tx > maxx) tx = maxx;
                if (tyc < miny) tyc = miny;
                if (tyc > gy) tyc = gy;
                double dx = tx - k->wx, dy = tyc - k->wy, d = hypot(dx, dy);
                if (d > 14) { k->wx += (dx / d) * 3.4; k->wy += (dy / d) * 3.4; strcpy(k->state, dx < 0 ? "WALK_LEFT" : "WALK_RIGHT"); }
                else strcpy(k->state, "IDLE");
            }
        } else {
            if (strcmp(k->save.roam_mode, "window") == 0) {
                if ((++k->ledge_ticks % 12) == 1 || !k->has_ledge) {
                    int ax, ay, aw, ah; char ttl[64];
                    if (query_active_win(k, wx, wy, ww, wh, &ax, &ay, &aw, &ah, ttl, sizeof(ttl))
                        && aw >= px_sz(k) + 48 && ah >= 140 && ay >= wy + 36 && ay <= wy + wh - 80) {
                        k->has_ledge = 1; k->ledge_x = ax + 12; k->ledge_y = ay; k->ledge_w = aw - 24;
                    } else k->has_ledge = 0;
                }
                if (k->has_ledge) {
                    int tx0 = k->ledge_x - k_ox(k), tx1 = k->ledge_x + k->ledge_w - k_ox(k) - px_sz(k);
                    if (tx0 < minx) tx0 = minx;
                    if (tx1 > maxx) tx1 = maxx;
                    k->roam_ty = k->ledge_y - (k_oy(k) + px_sz(k));
                    if (k->roam_ty < miny) k->roam_ty = miny;
                    if (k->roam_ty > gy) k->roam_ty = gy;
                    if (k->roam_tx < tx0 || k->roam_tx > tx1) k->roam_tx = tx0 + (tx1 > tx0 ? rand() % (tx1 - tx0) : 0);
                } else k->roam_ty = gy;
                if ((!k->has_ledge && k->wy < gy - 18) || k->roam_ty > k->wy + 28) {
                    k->umbrella_fall = 1; k->roam_wait = 0; k->roam_ticks = 0; k->act_ticks = 0;
                    say_msg(k, is_en(k) ? "Window gone! Sticky umbrella open!" : "Oeps, venster weg! Paraplu open!", 42);
                }
            }
            if (!k->umbrella_fall && k->roam_wait > 0) {
                k->roam_wait--;
                if (k->roam_wait % 60 == 30 && (rand() % 10) < 6) {
                    static const char *acts[] = {"BLINK_SMILE", "EARS_WIGGLE", "PEEK", "SIT", "LAPTOP_CODE", "UMBRELLA", "BOW", "WAVE"};
                    set_act(k, acts[rand() % 8], 24);
                } else strcpy(k->state, "IDLE");
            } else if (!k->umbrella_fall) {
                double dx = k->roam_tx - k->wx, dy = k->roam_ty - k->wy, dd = hypot(dx, dy);
                k->roam_ticks++;
                if (dd < 10 || k->roam_ticks > 155) {
                    k->roam_ticks = 0; k->roam_wait = 130 + (rand() % 150);
                    k->roam_tx = minx + (rand() % (maxx > minx ? (maxx - minx) : 1));
                    k->roam_ty = (strcmp(k->save.roam_mode, "window") == 0 && k->has_ledge) ? k->roam_ty : gy - ((rand() % 3 == 0) ? (rand() % ((gy - miny > 10) ? (gy - miny) / 2 : 10)) : 0);
                    if ((rand() % 7 == 0) && difftime(time(NULL), k->last_auto_say) > 35 && k->bubble_ticks == 0) {
                        k->last_auto_say = time(NULL);
                        time_t now = time(NULL); struct tm *lt = localtime(&now);
                        int night = lt && lt->tm_hour >= 0 && lt->tm_hour < 5;
                        say_msg(k, is_en(k) ? Q_EN[rand() % 5] : (night ? N_NL[rand() % 3] : Q_NL[rand() % 5]), 55);
                    }
                } else {
                    k->wx += (dx / dd) * 2.2; k->wy += (dy / dd) * 2.2;
                    strcpy(k->state, k->jump_y < -1 ? "JUMP" : (dx < 0 ? "WALK_LEFT" : "WALK_RIGHT"));
                }
            }
        }
    }

    if (k->jump_y < 0 || k->jump_vy < 0) { k->jump_y += k->jump_vy; k->jump_vy += 1.9; if (k->jump_y >= 0) { k->jump_y = 0; k->jump_vy = 0; } }
    if ((k->frame_idx % 8) == 0 && (rand() % 10) < 3 && k->jump_y == 0 && (strcmp(k->state, "WALK_LEFT") == 0 || strcmp(k->state, "WALK_RIGHT") == 0)) k->jump_vy = -5.5;
    if (k->act_ticks > 0 && --k->act_ticks == 0) strcpy(k->state, "IDLE");
    if (k->disco_ticks > 0) { if ((--k->disco_ticks % 12) == 0) spawn_particles(k, "*", 245, 196, 81, 4); }
    if (k->hyper_ticks > 0) k->hyper_ticks--;
    if (k->bubble_ticks > 0) k->bubble_ticks--;
    if ((k->frame_idx % 5) == 0) {
        for (int i = k->nparts - 1; i >= 0; i--) {
            k->parts[i].x += k->parts[i].vx; k->parts[i].y += k->parts[i].vy; k->parts[i].vy += 0.35;
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
    int wx, wy, ww, wh; get_work_area(k->dpy, k->scr, &wx, &wy, &ww, &wh);
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
        XEvent ev; XNextEvent(k->dpy, &ev);
        if (ev.type == Expose) {
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 18, 20, 27));
            XFillRectangle(k->dpy, win, gc, 0, 0, (unsigned)W, (unsigned)H);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 196, 30, 37));
            XFillRectangle(k->dpy, win, gc, 0, 0, (unsigned)W, (unsigned)hdrH);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
            if (k->bfont) XSetFont(k->dpy, gc, k->bfont->fid);
            char hdr[96]; snprintf(hdr, sizeof(hdr), "KAREL DE KOALA  *  STICKY RP2350   v%s", KAREL_VERSION);
            XDrawString(k->dpy, win, gc, P, Sc(26, s), hdr, (int)strlen(hdr));

            int boxSz = Sc(104, s), by0 = hdrH + Sc(16, s);
            XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 27, 31, 42));
            XFillRectangle(k->dpy, win, gc, P, by0, (unsigned)boxSz, (unsigned)boxSz);
            int pxs = Sc(3, s), ox = P + (boxSz - 32 * pxs) / 2, oy = by0 + (boxSz - 32 * pxs) / 2;
            for (int py = 0; py < 32; py++)
                for (int px = 0; px < 32; px++)
                    if (frame[py][px].a) {
                        XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, frame[py][px].r, frame[py][px].g, frame[py][px].b));
                        XFillRectangle(k->dpy, win, gc, ox + px * pxs, oy + py * pxs, (unsigned)pxs, (unsigned)pxs);
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
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 38, 115, 77)); XFillRectangle(k->dpy, win, gc, x1, btnY, (unsigned)w1, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 42, 48, 66)); XFillRectangle(k->dpy, win, gc, x2, btnY, (unsigned)w2, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 140, 38, 48)); XFillRectangle(k->dpy, win, gc, x3, btnY, (unsigned)w3, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 255, 255, 255));
                if (k->bfont) XSetFont(k->dpy, gc, k->bfont->fid);
                const char *l1 = en ? "Yes" : "Ja", *l2 = en ? "View README" : "README bekijken", *l3 = en ? "No" : "Nee";
                XDrawString(k->dpy, win, gc, x1 + Sc(44, s), btnY + Sc(23, s), l1, (int)strlen(l1));
                XDrawString(k->dpy, win, gc, x2 + Sc(26, s), btnY + Sc(23, s), l2, (int)strlen(l2));
                XDrawString(k->dpy, win, gc, x3 + Sc(40, s), btnY + Sc(23, s), l3, (int)strlen(l3));
            } else {
                int w2 = Sc(218, s), x1 = P, x2 = W - P - w2;
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 38, 115, 77)); XFillRectangle(k->dpy, win, gc, x1, btnY, (unsigned)w2, (unsigned)btnH);
                XSetForeground(k->dpy, gc, rgb_px(k->dpy, k->scr, 140, 38, 48)); XFillRectangle(k->dpy, win, gc, x2, btnY, (unsigned)w2, (unsigned)btnH);
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
                        char lhtml[600];
                        if (k->save.connected && *k->save.drive_root) snprintf(lhtml, sizeof(lhtml), "%.500s/Lees mij.html", k->save.drive_root);
                        else lhtml[0] = 0;
                        if (*lhtml && file_exists(lhtml)) {
                            char cmd[700]; snprintf(cmd, sizeof(cmd), "xdg-open '%.600s' >/dev/null 2>&1 &", lhtml);
                            if (system(cmd) != 0) {}
                        } else {
                            if (system("xdg-open 'https://github.com/EgonRuiter/karel-de-koala#readme' >/dev/null 2>&1 &") != 0) {}
                        }
                    }
                    else if (cx >= x3 && cx <= x3 + w3) { confirm = 1; XClearArea(k->dpy, win, 0, 0, 0, 0, True); }
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

#endif /* !KAREL_CORE_TEST */

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
        else if (strncmp(argv[i], "--ipc-port=", 11) == 0) { int p = atoi(argv[i] + 11); if (p > 0 && p < 65536) ipc_port = (uint16_t)p; }
    }

    if (self_test) {
        char gz[600];
        if (!locate_sprites_gz(gz, sizeof(gz))) { fprintf(stderr, "karel_sprites.gz niet gevonden\n"); return 1; }
        static SpriteBank sb;
        if (!load_sprites_gz(&sb, gz)) { fprintf(stderr, "Failed loading %s\n", gz); return 1; }
        Rgba px[32][32];
        for (int s = 0; s < NUM_SKINS; s++)
            for (int o = 0; o < NUM_OUTFITS; o++) render_frame_rgba(&sb, "IDLE", 0, SKIN_IDS[s], OUTFIT_IDS[o], px);
        int opaque = 0; for (int y = 0; y < 32; y++) for (int x = 0; x < 32; x++) if (px[y][x].a) opaque++;
        char sha[65]; sha256_hex((const uint8_t *)"abc", 3, sha);
        if (opaque < 50 || strcmp(sha, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") != 0 || compare_ver("2.2.2", KAREL_VERSION) <= 0) {
            fprintf(stderr, "Self-check failed\n"); return 1;
        }
        double tf[3] = {440, 554.37, 659.25}; uint8_t wb[16384];
        size_t wn = build_wav_bytes(tf, 3, 0.05, 0.2, wb, sizeof(wb));
        SaveStore ss; save_load(&ss);
        printf("SELF_TEST_OK version=%s states=%d xp=%d wav=%zu\n", KAREL_VERSION, sb.nstates, ss.xp, wn);
        return 0;
    }

#ifdef KAREL_CORE_TEST
    (void)toggle; (void)no_update; (void)ask; (void)no_ask; (void)ipc_port; (void)updated_from;
    return 0;
#else
    signal(SIGCHLD, SIG_IGN);
    if (try_signal_existing(toggle, ipc_port)) return 0;
    if (toggle) return 0;

    static KarelApp k; memset(&k, 0, sizeof(k));
    k.ser.fd = -1; k.upd_pipe = -1;
    snprintf(k.updated_from, sizeof(k.updated_from), "%.31s", updated_from);
    ssize_t el = readlink("/proc/self/exe", k.self_exe, sizeof(k.self_exe) - 1);
    if (el > 0) k.self_exe[el] = 0; else snprintf(k.self_exe, sizeof(k.self_exe), "%.500s", argv[0]);

    char gz[600];
    if (!locate_sprites_gz(gz, sizeof(gz)) || !load_sprites_gz(&k.sb, gz)) {
        fprintf(stderr, "Karel: karel_sprites.gz niet gevonden.\n"); return 1;
    }
    save_load(&k.save);
    k.scale = clamp_int(k.save.karel_scale, 2, 5);
    srand((unsigned)time(NULL));

    k.dpy = XOpenDisplay(NULL);
    if (!k.dpy) { fprintf(stderr, "Geen X11/XWayland DISPLAY gevonden.\n"); return 1; }
    k.scr = XDefaultScreen(k.dpy); k.root = XRootWindow(k.dpy, k.scr);
    k.dpi = get_dpi_scale(k.dpy);
    k.wm_del = XInternAtom(k.dpy, "WM_DELETE_WINDOW", False);
    k.bfont = XLoadQueryFont(k.dpy, "-*-helvetica-bold-r-*-*-14-*-*-*-*-*-*");
    if (!k.bfont) k.bfont = XLoadQueryFont(k.dpy, "fixed");
    k.font = XLoadQueryFont(k.dpy, "-*-fixed-medium-r-*-*-13-*-*-*-*-*-*");
    if (!k.font) k.font = k.bfont;
    int should_ask = ask || (!no_ask && !*updated_from);
    if (should_ask && !run_ask_prompt(&k)) { XCloseDisplay(k.dpy); return 0; }
    k.ipc_fd = start_ipc_server(ipc_port);

    int wx, wy, ww, wh; get_work_area(k.dpy, k.scr, &wx, &wy, &ww, &wh);
    XSetWindowAttributes swa; swa.override_redirect = True; swa.background_pixel = 0;
    k.wx = wx + ww - win_w(&k) - 40;
    k.wy = wy + wh - (k_oy(&k) + px_sz(&k));
    k.karel_win = XCreateWindow(k.dpy, k.root, (int)k.wx, (int)k.wy, (unsigned)win_w(&k), (unsigned)win_h(&k),
                                0, CopyFromParent, InputOutput, CopyFromParent, CWOverrideRedirect | CWBackPixel, &swa);
    XStoreName(k.dpy, k.karel_win, "Karel de Koala");
    XSelectInput(k.dpy, k.karel_win, ExposureMask | ButtonPressMask | ButtonReleaseMask | PointerMotionMask | KeyPressMask);
    k.karel_gc = XCreateGC(k.dpy, k.karel_win, 0, NULL);
    XMapRaised(k.dpy, k.karel_win);
    trigger_climb(&k, is_en(&k) ? "Karel climbed onto your Linux desktop!" : "Karel klimt je Linux bureaublad op!");
    if (!no_update) start_updater_async(k.save.drive_root, k.self_exe, k.updated_from, &k.upd_pipe);

    while (!k.quit_req) {
        while (XPending(k.dpy)) {
            XEvent ev; XNextEvent(k.dpy, &ev);
            if (ev.type == ClientMessage && ev.xclient.window == k.hub_win && (Atom)ev.xclient.data.l[0] == k.wm_del) {
                XUnmapWindow(k.dpy, k.hub_win);
            } else if (ev.type == KeyPress) {
                handle_key_event(&k, &ev.xkey);
            } else if (ev.type == Expose && ev.xexpose.window == k.hub_win) {
                draw_hub(&k);
            } else if (ev.type == Expose && ev.xexpose.window == k.pop_win) {
                draw_popup(&k);
            } else if (ev.type == MotionNotify && ev.xmotion.window == k.pop_win) {
                int nh = (ev.xmotion.y - 4) / 26;
                if (nh != k.pop_hover) { k.pop_hover = nh; draw_popup(&k); }
            } else if (ev.type == ButtonPress && ev.xbutton.window == k.pop_win && ev.xbutton.button == 1) {
                click_popup(&k, ev.xbutton.y, ev.xbutton.x_root, ev.xbutton.y_root);
            } else if (ev.type == ButtonPress && ev.xbutton.window == k.hub_win && ev.xbutton.button == 1) {
                handle_hub_click(&k, ev.xbutton.x, ev.xbutton.y, ev.xbutton.x_root, ev.xbutton.y_root);
            } else if (ev.type == ButtonPress && ev.xbutton.window == k.karel_win) {
                close_popup(&k);
                if (ev.xbutton.button == 3) open_popup(&k, POP_MAIN, ev.xbutton.x_root, ev.xbutton.y_root);
                else if (ev.xbutton.button == 1) {
                    static Time last_click = 0;
                    if (ev.xbutton.time - last_click < 350) { do_pet(&k); last_click = 0; }
                    else {
                        last_click = ev.xbutton.time;
                        k.dragging = 1; k.flying = 0; k.climbing = 0; k.umbrella_fall = 0; k.jump_y = 0;
                        k.drag_dx = ev.xbutton.x; k.drag_dy = ev.xbutton.y;
                        k.drag_sx = ev.xbutton.x_root; k.drag_sy = ev.xbutton.y_root; k.last_drag_t = time(NULL);
                    }
                }
            } else if (ev.type == MotionNotify && ev.xmotion.window == k.karel_win && k.dragging) {
                strcpy(k.state, "JETPACK");
                k.wx = ev.xmotion.x_root - k.drag_dx; k.wy = ev.xmotion.y_root - k.drag_dy;
                XMoveWindow(k.dpy, k.karel_win, (int)k.wx, (int)k.wy);
            } else if (ev.type == ButtonRelease && ev.xbutton.window == k.karel_win && k.dragging) {
                k.dragging = 0;
                double moved = hypot(ev.xbutton.x_root - k.drag_sx, ev.xbutton.y_root - k.drag_sy);
                if (moved < 6) {
                    int sx = (ev.xbutton.x - k_ox(&k)) / k.scale, sy = (ev.xbutton.y - k_oy(&k)) / k.scale;
                    if (sx >= 13 && sx <= 18 && sy >= 12 && sy <= 16) {
                        if (difftime(time(NULL), k.last_nose_t) > 4.5) k.nose_clicks = 0;
                        k.last_nose_t = time(NULL);
                        if (++k.nose_clicks >= 7) {
                            k.nose_clicks = 0; play_sound_key("sneeze", k.muted, k.auto_paused);
                            spawn_particles(&k, "*", 245, 245, 245, 10);
                            set_act(&k, "SNEEZE", 24); say_msg(&k, is_en(&k) ? "Achoo! BBG dust!" : "Hatsjoe! BBG stof!", 55);
                        }
                    } else if (k.act_ticks == 0 && strcmp(k.state, "SLEEP") != 0) {
                        open_hub(&k);
                    }
                } else {
                    double dt = difftime(time(NULL), k.last_drag_t); if (dt < 0.08) dt = 0.08;
                    double vx = (ev.xbutton.x_root - k.drag_sx) / (dt * 20.0), vy = (ev.xbutton.y_root - k.drag_sy) / (dt * 20.0);
                    if (hypot(vx, vy) > 10.0) { k.flying = 1; k.fling_vx = vx > 36 ? 36 : (vx < -36 ? -36 : vx); k.fling_vy = vy > 26 ? 26 : (vy < -32 ? -32 : vy); }
                }
            }
        }
        if (k.ipc_fd >= 0) {
            int c = accept(k.ipc_fd, NULL, NULL);
            if (c >= 0) {
                char msg[64]; ssize_t n = read(c, msg, sizeof(msg) - 1); close(c);
                if (n > 0) {
                    msg[n] = 0;
                    if (strstr(msg, "TOGGLE")) {
                        if (k.hidden) { k.hidden = 0; XMapRaised(k.dpy, k.karel_win); trigger_climb(&k, is_en(&k) ? "I'm back!" : "Daar ben ik weer!"); }
                        else trigger_dive(&k, "quit");
                    } else { if (k.hidden) { k.hidden = 0; XMapRaised(k.dpy, k.karel_win); } do_boop(&k); }
                }
            }
        }
        char sev[64]; ser_poll(&k.ser, sev, sizeof(sev));
        if (*sev) {
            if (strcmp(sev, "EVENT:PET") == 0) do_pet(&k);
            else if (strcmp(sev, "EVENT:FEED") == 0) do_feed(&k);
            else if (strcmp(sev, "EVENT:COFFEE") == 0) do_coffee(&k);
            else if (strcmp(sev, "EVENT:WASH") == 0) do_wash(&k);
            else if (strcmp(sev, "EVENT:DISCO") == 0) trigger_konami(&k);
            else if (strcmp(sev, "EVENT:RST_BOOP") == 0 || strcmp(sev, "EVENT:GIFT") == 0) do_boop(&k);
            else if (strcmp(sev, "EVENT:TOGGLE_KAREL") == 0 || strcmp(sev, "EVENT:TRAY_TOGGLE") == 0) {
                if (k.hidden) { k.hidden = 0; XMapRaised(k.dpy, k.karel_win); trigger_climb(&k, is_en(&k) ? "I'm back!" : "Daar ben ik weer!"); }
                else trigger_dive(&k, "quit");
            }
        }
        step_physics(&k);
        XFlush(k.dpy);
        sleep_ms(62);
    }

    int restart = (k.quit_req == 2);
    ser_send(&k.ser, "STATE:BYE"); save_persist(&k.save); ser_drop(&k.ser);
    if (k.ipc_fd >= 0) close(k.ipc_fd);
    if (k.upd_pipe >= 0) close(k.upd_pipe);
    close_popup(&k);
    XCloseDisplay(k.dpy);
    if (restart && *k.self_exe) {
        char uf[48]; snprintf(uf, sizeof(uf), "--updated-from=%.31s", k.upd_ver);
        execl(k.self_exe, k.self_exe, uf, (char *)NULL);
    }
    return 0;
#endif
}
