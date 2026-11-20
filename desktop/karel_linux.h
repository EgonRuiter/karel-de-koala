/* Karel de Koala - Linux Companion Header (C99 + libX11 + XShape)
 * Shared constants, data structures, X11 portability declarations, and module
 * prototypes for desktop/karel_linux.c.
 */

#ifndef KAREL_LINUX_H
#define KAREL_LINUX_H

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

/* =========================================================================
 * Version, Read-Only Update Endpoints & Hard Safety Caps
 * ========================================================================= */

#define KAREL_VERSION "2.7.0"
#define KAREL_MANIFEST_URL "https://github.com/EgonRuiter/karel-de-koala/releases/latest/download/version.json"
#define KAREL_RELEASES_URL "https://github.com/EgonRuiter/karel-de-koala/releases/latest"

#define MAX_INFLATE_BYTES (2u * 1024u * 1024u)
#define MAX_MANIFEST_BYTES 65536u
#define MAX_STATES 96
#define MAX_FRAMES 16
#define NUM_SKINS 14
#define NUM_OUTFITS 17

/* =========================================================================
 * POSIX & X11 / XShape Headers (or Minimal Stubs for KAREL_CORE_TEST)
 * ========================================================================= */

#ifndef KAREL_CORE_TEST
#include <arpa/inet.h>
#include <netinet/in.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/statvfs.h>
#include <sys/time.h>
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
/* Minimal ABI-compatible X11/XShape declarations when dev headers are absent. */
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
#endif /* !KAREL_CORE_TEST */

/* =========================================================================
 * Core Data Structures
 * ========================================================================= */

typedef struct { const uint8_t *src; size_t len, pos; uint32_t bitbuf; int bitcnt; } BitRd;
typedef struct { uint16_t count[16]; uint16_t sym[320]; } HuffTbl;

typedef struct { uint8_t r, g, b, a; } Rgba;
typedef struct { char name[32]; int nframes, div; char rows[MAX_FRAMES][32][33]; int8_t anc[MAX_FRAMES][4]; } AnimState;
typedef struct { Rgba pal[128]; AnimState states[MAX_STATES]; int nstates; } SpriteBank;

typedef struct {
    int hunger, happiness, energy, hygiene, caffeine;
    int xp, level, total_pets, karel_scale, auto_quiet;
    char roam_mode[16], skin[24], equipped[32], language[8], stick_serial[32], last_seen[32];
    char drive_root[512], fallback_path[560];
    int connected;
} SaveStore;

#ifndef KAREL_CORE_TEST
typedef struct { int fd; char port[64], last_state[48], rbuf[256]; size_t rlen; time_t last_probe; } LinuxSerial;
typedef struct { int x, y, w, h, id; } HubBtn;
typedef struct { double x, y, vx, vy; int life; char ch[2]; uint8_t r, g, b; } Particle;
typedef struct { char lbl[48]; int kind, idx; } PopItem;
typedef struct { const char *lbl, *st, *msg; } TrickDef;

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
    PopItem pop_items[40]; int npop;
} KarelApp;
#endif /* !KAREL_CORE_TEST */

/* =========================================================================
 * Module Function Prototypes
 * ========================================================================= */

/* 1. Compression, Crypto & Version Validation */
static int br_bit(BitRd *b);
static int br_bits(BitRd *b, int n);
static void huff_build(HuffTbl *h, const uint8_t *lens, int n);
static int huff_dec(BitRd *b, const HuffTbl *h);
static uint8_t *inflate_grow(uint8_t *out, size_t *cap, size_t needed);
static uint8_t *inflate_gzip(const uint8_t *src, size_t len, size_t *out_len);
static void sha256_hex(const uint8_t *data, size_t len, char out[65]);
static int is_valid_semver(const char *s);
static int compare_ver(const char *a, const char *b);

/* 2. Sprite Bank & Pixel Renderer */
static int find_state_idx(const SpriteBank *sb, const char *st);
static int parse_hex2(const char *s);
static int load_sprites_gz(SpriteBank *sb, const char *path);
static char map_skin(const char *skin, char ch);
static void g_rect(char g[32][32], int dx, int dy, int x0, int y0, int x1, int y1, char ch);
static void g_px(char g[32][32], int dx, int dy, int x, int y, char ch);
static void render_frame_rgba(const SpriteBank *sb, const char *req_st, int frame_idx,
                              const char *skin, const char *item, Rgba out[32][32]);

/* 3. Persistent SaveStore & USB Drive Locator */
static int xp_for_next_level(int lvl);
static int level_from_xp(int xp);
static int clamp_int(int v, int lo, int hi);
static int file_exists(const char *p);
static void save_defaults(SaveStore *s);
static int json_find_str(const char *txt, const char *key, char *out, size_t max_out);
static int json_find_int(const char *txt, const char *key, int *out);
static time_t parse_iso_local(const char *s);
static int read_save_file(const char *path, SaveStore *out);
static void get_volume_serial(const char *root, char out[32]);
static void find_usb_drive(char *out, size_t max_out);
static void save_write_one(const char *path, const SaveStore *s, int direct);
static void save_persist(SaveStore *s);
static void save_load(SaveStore *s);

/* 4. Audio Synthesizer & Asset Locator */
static size_t build_wav_bytes(const double *freqs, int nfreq, double dur, double amp, uint8_t *buf, size_t maxb);
static int locate_sprites_gz(char *out, size_t max_out);

#ifndef KAREL_CORE_TEST
static int poll_usb(SaveStore *s);

/* 5. Audio Playback, RP2350 Serial, Read-Only Version Check & IPC */
static void sleep_ms(int ms);
static void cleanup_sound_dir(void);
static void open_with_xdg(const char *target);
static void play_sound_key(const char *key, int muted, int auto_quiet);
static void ser_drop(LinuxSerial *s);
static void ser_send(LinuxSerial *s, const char *line);
static void ser_poll(LinuxSerial *s, char *ev_out, size_t max_ev);
static uint8_t *exec_fetch_tool(const char *tool, char *const argv[], size_t *out_len);
static uint8_t *http_get_manifest(size_t *out_len);
static void start_updater_async(int *out_pipe_fd);
static int try_signal_existing(int toggle, uint16_t port);
static int start_ipc_server(uint16_t port);

/* 6. X11 Desktop UI, Physics Loop, Menus & Sticky Hub */
static int Sc(int px, float s);
static float get_dpi_scale(Display *dpy);
static unsigned long rgb_px(Display *dpy, int scr, uint8_t r, uint8_t g, uint8_t b);
static void get_work_area(Display *dpy, int scr, int *x, int *y, int *w, int *h);
static int query_active_win(KarelApp *k, int wa_x, int wa_y, int wa_w, int wa_h, int *rx, int *ry, int *rw, int *rh, char *title, size_t max_t);
static int detect_auto_quiet(KarelApp *k, int wa_x, int wa_y, int wa_w, int wa_h);
static void say_msg(KarelApp *k, const char *m, int ticks);
static void set_act(KarelApp *k, const char *st, int ticks);
static int is_en(const KarelApp *k);
static int px_sz(const KarelApp *k);
static int win_w(const KarelApp *k);
static int win_h(const KarelApp *k);
static int k_ox(const KarelApp *k);
static int k_oy(const KarelApp *k);
static void spawn_particles(KarelApp *k, const char *ch, uint8_t r, uint8_t g, uint8_t b, int count);
static void draw_hub(KarelApp *k);
static void open_hub(KarelApp *k);
static const char *level_title(int lvl, int en);
static const char *outfit_quote(const char *item, int en);
static const char *pick_smart_quote(const KarelApp *k);
static void play_trick_sound(const KarelApp *k, const char *st);
static void do_random_style(KarelApp *k);
static void award_xp(KarelApp *k, int amt);
static void trigger_climb(KarelApp *k, const char *msg);
static void do_pet(KarelApp *k);
static void do_feed(KarelApp *k);
static void do_coffee(KarelApp *k);
static void do_wash(KarelApp *k);
static void nap_toggle(KarelApp *k);
static void trigger_konami(KarelApp *k);
static void do_boop(KarelApp *k);
static void trigger_dive(KarelApp *k, const char *mode);
static void paint_karel(KarelApp *k);
static int pop_rh(const KarelApp *k);
static void close_popup(KarelApp *k);
static void draw_popup(KarelApp *k);
static void open_popup(KarelApp *k, int mode, int rx, int ry);
static void resize_karel_scale(KarelApp *k, int sc);
static void click_popup(KarelApp *k, int my, int x_root, int y_root);
static void add_hub_btn(KarelApp *k, int x, int y, int w, int h, int id);
static void handle_hub_click(KarelApp *k, int mx, int my, int x_root, int y_root);
static void handle_key_event(KarelApp *k, XKeyEvent *kev);
static void step_physics(KarelApp *k);
static int run_ask_prompt(KarelApp *k);
#endif /* !KAREL_CORE_TEST */

#endif /* KAREL_LINUX_H */
