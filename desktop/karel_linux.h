/* Karel de Koala - Linux Companion Header (C99 + libX11 + XShape)
 * Shared constants, data structures, X11 portability declarations, and cross-module
 * APIs for desktop/karel_linux.c and desktop/linux/{codec,sprites,storage,system_io}.c.
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

#define KAREL_VERSION "2.7.1"
#define KAREL_MANIFEST_URL "https://github.com/svsticky/karel-de-koala/releases/latest/download/version.json"
#define KAREL_RELEASES_URL "https://github.com/svsticky/karel-de-koala/releases/latest"

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
 * Shared Cross-Module Symbols & APIs
 * ========================================================================= */

/* desktop/linux/codec.c */
uint8_t *inflate_gzip(const uint8_t *src, size_t len, size_t *out_len);
void sha256_hex(const uint8_t *data, size_t len, char out[65]);
int is_valid_semver(const char *s);
int compare_ver(const char *a, const char *b);

/* desktop/linux/sprites.c */
extern const char *SKIN_IDS[NUM_SKINS];
extern const char *OUTFIT_IDS[NUM_OUTFITS];
int load_sprites_gz(SpriteBank *sb, const char *path);
void render_frame_rgba(const SpriteBank *sb, const char *req_st, int frame_idx,
                       const char *skin, const char *item, Rgba out[32][32]);

/* desktop/linux/storage.c */
int xp_for_next_level(int lvl);
int level_from_xp(int xp);
int clamp_int(int v, int lo, int hi);
int file_exists(const char *p);
int json_find_str(const char *txt, const char *key, char *out, size_t max_out);
void save_persist(SaveStore *s);
void save_load(SaveStore *s);
size_t build_wav_bytes(const double *freqs, int nfreq, double dur, double amp, uint8_t *buf, size_t maxb);
int locate_sprites_gz(char *out, size_t max_out);

#ifndef KAREL_CORE_TEST
int poll_usb(SaveStore *s);

/* desktop/linux/system_io.c */
void sleep_ms(int ms);
void cleanup_sound_dir(void);
void open_with_xdg(const char *target);
void play_sound_key(const char *key, int muted, int auto_quiet);
void ser_drop(LinuxSerial *s);
void ser_send(LinuxSerial *s, const char *line);
void ser_poll(LinuxSerial *s, char *ev_out, size_t max_ev);
void start_updater_async(int *out_pipe_fd);
int try_signal_existing(int toggle, uint16_t port);
int start_ipc_server(uint16_t port);
#endif /* !KAREL_CORE_TEST */

#endif /* KAREL_LINUX_H */
