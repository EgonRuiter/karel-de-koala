/* Karel de Koala - OS Process, Audio, Serial, Read-Only Update Check & IPC
 * All process spawning, network I/O, temp-directory handling, serial CDC I/O,
 * and localhost socket code lives in this single file for focused auditing.
 */

#include "../karel_linux.h"

#ifdef KAREL_CORE_TEST
/* Keep translation unit valid under headless KAREL_CORE_TEST builds. */
typedef int karel_system_io_core_test_unused_t;
#else

void sleep_ms(int ms) {
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

/* =========================================================================
 * Audio Playback & Process Spawning (Zero Shell)
 * ========================================================================= */

/* Per-process private temporary directory (mode 0700) for synthesized WAV clips. */
static char g_snd_dir[128] = "";

void cleanup_sound_dir(void) {
    if (!g_snd_dir[0]) return;
    DIR *dp = opendir(g_snd_dir);
    if (dp) {
        struct dirent *de;
        while ((de = readdir(dp)) != NULL) {
            if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0) continue;
            char p[256];
            snprintf(p, sizeof(p), "%.120s/%.120s", g_snd_dir, de->d_name);
            remove(p);
        }
        closedir(dp);
    }
    rmdir(g_snd_dir);
    g_snd_dir[0] = 0;
}

void open_with_xdg(const char *target) {
    if (!target || !*target) return;
    pid_t pid = fork();
    if (pid == 0) {
        int devnull = open("/dev/null", O_RDWR);
        if (devnull >= 0) {
            dup2(devnull, 0);
            dup2(devnull, 1);
            dup2(devnull, 2);
            close(devnull);
        }
        execlp("xdg-open", "xdg-open", target, (char *)NULL);
        _exit(127);
    }
}

void play_sound_key(const char *key, int muted, int auto_quiet) {
    if (muted || auto_quiet) return;
    static const struct {
        const char *k;
        double f[5];
        int n;
        double dur;
        double amp;
    } tbl[] = {
        {"climb",   {330, 392, 523.25, 0, 0},         3, 0.065, 0.20},
        {"pet",     {523.25, 659.25, 783.99, 0, 0},   3, 0.055, 0.18},
        {"eat",     {293.66, 349.23, 440, 0, 0},      3, 0.060, 0.20},
        {"coffee",  {440, 554.37, 659.25, 880, 0},    4, 0.050, 0.20},
        {"boop",    {587.33, 783.99, 1046.5, 0, 0},   3, 0.060, 0.22},
        {"levelup", {440, 554.37, 659.25, 880, 1046.5}, 5, 0.080, 0.22},
        {"dive",    {659.25, 523.25, 392.0, 261.63, 0}, 4, 0.080, 0.20},
        {"sneeze",  {780, 220, 0, 0, 0},              2, 0.080, 0.22},
        {"chirp",   {620, 740, 0, 0, 0},              2, 0.035, 0.12},
        {"chirp2",  {560, 680, 610, 0, 0},            3, 0.032, 0.12},
        {"chirp3",  {680, 820, 0, 0, 0},              2, 0.034, 0.12},
        {"chirp4",  {520, 640, 760, 0, 0},            3, 0.030, 0.11},
        {"magic",   {523.25, 659.25, 783.99, 1046.5, 1318.5}, 5, 0.050, 0.18},
        {"karate",  {220, 660, 330, 0, 0},            3, 0.045, 0.20},
        {"dj",      {196, 261.63, 392, 523.25, 0},    4, 0.055, 0.19},
        {"toss",    {310, 460, 680, 0, 0},            3, 0.040, 0.17},
        {"trick",   {440, 587.33, 783.99, 0, 0},      3, 0.050, 0.18},
        {"shuffle", {493.88, 659.25, 880, 0, 0},      3, 0.040, 0.16}
    };
    int nt = (int)(sizeof(tbl) / sizeof(tbl[0]));
    int idx = -1;
    for (int i = 0; i < nt; i++) {
        if (strcmp(tbl[i].k, key) == 0) { idx = i; break; }
    }
    if (idx < 0) return;

    if (!g_snd_dir[0]) {
        strcpy(g_snd_dir, "/tmp/karel_snd_XXXXXX");
        if (!mkdtemp(g_snd_dir)) { g_snd_dir[0] = 0; return; }
        chmod(g_snd_dir, 0700);
    }

    char path[200];
    snprintf(path, sizeof(path), "%.120s/%.24s.wav", g_snd_dir, key);
    if (!file_exists(path)) {
        uint8_t wav[44 + 16384 * 2];
        size_t wn = build_wav_bytes(tbl[idx].f, tbl[idx].n, tbl[idx].dur, tbl[idx].amp, wav, sizeof(wav));
        FILE *fp = fopen(path, "wb");
        if (fp) {
            fwrite(wav, 1, wn, fp);
            fclose(fp);
        }
    }

    if (fork() == 0) {
        int devnull = open("/dev/null", O_RDWR);
        if (devnull >= 0) {
            dup2(devnull, 0);
            dup2(devnull, 1);
            dup2(devnull, 2);
            close(devnull);
        }
        execlp("aplay", "aplay", "-q", path, (char *)NULL);
        execlp("paplay", "paplay", path, (char *)NULL);
        execlp("pw-play", "pw-play", path, (char *)NULL);
        _exit(0);
    }
}

/* =========================================================================
 * USB CDC Serial Sync (115200 baud, KAREL_PING / KAREL_PONG)
 * ========================================================================= */

void ser_drop(LinuxSerial *s) {
    if (s->fd >= 0) close(s->fd);
    s->fd = -1;
    s->port[0] = 0;
    s->last_state[0] = 0;
    s->rlen = 0;
}

void ser_send(LinuxSerial *s, const char *line) {
    if (s->fd < 0) return;
    if (strncmp(line, "STATE:", 6) == 0) {
        if (strcmp(line, s->last_state) == 0) return;
        snprintf(s->last_state, sizeof(s->last_state), "%.47s", line);
    }
    char out[128];
    int n = snprintf(out, sizeof(out), "%.120s\n", line);
    if (n > 0 && write(s->fd, out, (size_t)n) < 0 && errno != EAGAIN) {
        ser_drop(s);
    }
}

static void ser_probe_ports(LinuxSerial *s) {
    static int probe_cd = 0;
    if (probe_cd-- > 0) return;
    probe_cd = 6;

    DIR *dp = opendir("/dev");
    if (!dp) return;
    char cands[16][64];
    int nc = 0;
    struct dirent *de;
    while ((de = readdir(dp)) != NULL && nc < 16) {
        if (strncmp(de->d_name, "ttyACM", 6) == 0 || strncmp(de->d_name, "ttyUSB", 6) == 0) {
            snprintf(cands[nc++], 64, "%.63s", de->d_name);
        }
    }
    closedir(dp);

    /* Probe highest numbered ports first (ttyACM1 CDC data precedes ttyACM0). */
    for (int i = nc - 1; i > 0; i--) {
        for (int j = 0; j < i; j++) {
            if (strcmp(cands[j], cands[j + 1]) < 0) {
                char swp[64];
                memcpy(swp, cands[j], 64);
                memcpy(cands[j], cands[j + 1], 64);
                memcpy(cands[j + 1], swp, 64);
            }
        }
    }

    for (int ci = 0; ci < nc; ci++) {
        char p[256];
        snprintf(p, sizeof(p), "/dev/%.120s", cands[ci]);
        int fd = open(p, O_RDWR | O_NOCTTY | O_NONBLOCK);
        if (fd < 0) continue;

        struct termios tio;
        tcgetattr(fd, &tio);
        tio.c_iflag &= ~(tcflag_t)(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL | IXON);
        tio.c_oflag &= ~(tcflag_t)OPOST;
        tio.c_lflag &= ~(tcflag_t)(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
        tio.c_cflag &= ~(tcflag_t)(CSIZE | PARENB);
        tio.c_cflag |= CS8 | CLOCAL | CREAD;
        cfsetispeed(&tio, B115200);
        cfsetospeed(&tio, B115200);
        tcsetattr(fd, TCSANOW, &tio);

        sleep_ms(25);
        tcflush(fd, TCIFLUSH);
        (void)!write(fd, "KAREL_PING\n", 11);
        sleep_ms(95);

        char b[128];
        ssize_t n = read(fd, b, sizeof(b) - 1);
        if (n > 0) {
            b[n] = 0;
            if (strstr(b, "KAREL_PONG")) {
                s->fd = fd;
                snprintf(s->port, sizeof(s->port), "%.60s", cands[ci]);
                return;
            }
        }
        close(fd);
    }
}

void ser_poll(LinuxSerial *s, char *ev_out, size_t max_ev) {
    ev_out[0] = 0;
    if (s->fd < 0) {
        ser_probe_ports(s);
        return;
    }

    if (s->rlen >= sizeof(s->rbuf) - 1) s->rlen = 0;
    char tmp[128];
    ssize_t n = read(s->fd, tmp, sizeof(tmp));
    if (n > 0) {
        size_t avail = sizeof(s->rbuf) - 1 - s->rlen;
        size_t take = (size_t)n < avail ? (size_t)n : avail;
        memcpy(s->rbuf + s->rlen, tmp, take);
        s->rlen += take;
        s->rbuf[s->rlen] = 0;
        char *nl = strchr(s->rbuf, '\n');
        if (nl) {
            *nl = 0;
            size_t l = strlen(s->rbuf);
            if (l > 0 && s->rbuf[l - 1] == '\r') s->rbuf[l - 1] = 0;
            if (strncmp(s->rbuf, "EVENT:", 6) == 0 && max_ev > 1) {
                snprintf(ev_out, max_ev, "%.60s", s->rbuf);
            }
            size_t rem = s->rlen - (size_t)(nl - s->rbuf) - 1;
            memmove(s->rbuf, nl + 1, rem);
            s->rlen = rem;
        }
    } else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
        ser_drop(s);
        return;
    }

    static int hb = 0;
    if (s->fd >= 0 && ++hb >= 16) {
        hb = 0;
        ser_send(s, "KAREL_PING");
    }
}

/* =========================================================================
 * Read-Only GitHub Version Check & Loopback Single-Instance IPC
 * ========================================================================= */

static uint8_t *exec_fetch_tool(const char *tool, char *const argv[], size_t *out_len) {
    *out_len = 0;
    int pfd[2];
    if (pipe(pfd) != 0) return NULL;
    pid_t pid = fork();
    if (pid < 0) {
        close(pfd[0]);
        close(pfd[1]);
        return NULL;
    }
    if (pid == 0) {
        close(pfd[0]);
        dup2(pfd[1], 1);
        close(pfd[1]);
        int devnull = open("/dev/null", O_RDWR);
        if (devnull >= 0) {
            dup2(devnull, 0);
            dup2(devnull, 2);
            close(devnull);
        }
        execvp(tool, argv);
        _exit(127);
    }
    close(pfd[1]);

    size_t cap = 4096, n = 0;
    uint8_t *buf = (uint8_t *)malloc(cap);
    if (!buf) {
        close(pfd[0]);
        waitpid(pid, NULL, 0);
        return NULL;
    }

    int too_big = 0;
    while (1) {
        if (n + 2048 + 1 > cap) {
            if (cap >= MAX_MANIFEST_BYTES + 1) { too_big = 1; break; }
            size_t ncap = cap * 2;
            if (ncap > MAX_MANIFEST_BYTES + 1) ncap = MAX_MANIFEST_BYTES + 1;
            uint8_t *tmp = (uint8_t *)realloc(buf, ncap);
            if (!tmp) {
                free(buf);
                close(pfd[0]);
                waitpid(pid, NULL, 0);
                return NULL;
            }
            buf = tmp;
            cap = ncap;
        }
        size_t avail = cap - n - 1;
        if (avail == 0) { too_big = 1; break; }
        ssize_t r = read(pfd[0], buf + n, avail > 2048 ? 2048 : avail);
        if (r < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (r == 0) break;
        n += (size_t)r;
    }
    close(pfd[0]);

    int st = 0;
    waitpid(pid, &st, 0);
    if (too_big || !WIFEXITED(st) || WEXITSTATUS(st) != 0 || n == 0) {
        free(buf);
        return NULL;
    }
    buf[n] = 0;
    *out_len = n;
    return buf;
}

static uint8_t *http_get_manifest(size_t *out_len) {
    char *curl_argv[] = {
        "curl", "-fsSL", "--max-time", "10", "--proto", "=https", "--", KAREL_MANIFEST_URL, NULL
    };
    uint8_t *res = exec_fetch_tool("curl", curl_argv, out_len);
    if (res) return res;

    char *wget_argv[] = {
        "wget", "-qO-", "-T", "10", "--https-only", "--", KAREL_MANIFEST_URL, NULL
    };
    return exec_fetch_tool("wget", wget_argv, out_len);
}

void start_updater_async(int *out_pipe_fd) {
    int pfd[2];
    *out_pipe_fd = -1;
    if (pipe(pfd) != 0) return;

    pid_t pid = fork();
    if (pid < 0) {
        close(pfd[0]);
        close(pfd[1]);
        return;
    }
    if (pid > 0) {
        close(pfd[1]);
        fcntl(pfd[0], F_SETFL, O_NONBLOCK);
        *out_pipe_fd = pfd[0];
        return;
    }

    close(pfd[0]);
    signal(SIGCHLD, SIG_DFL); /* waitpid inside exec_fetch_tool requires default SIGCHLD. */
    size_t mlen = 0;
    uint8_t *mraw = http_get_manifest(&mlen);
    if (mraw && mlen > 10) {
        char rem_ver[32] = "";
        json_find_str((const char *)mraw, "version", rem_ver, sizeof(rem_ver));
        free(mraw);
        if (!is_valid_semver(rem_ver)) {
            (void)!write(pfd[1], "ERROR", 5);
        } else if (compare_ver(rem_ver, KAREL_VERSION) <= 0) {
            (void)!write(pfd[1], "UPTODATE", 8);
        } else {
            char msg[48];
            snprintf(msg, sizeof(msg), "NEW:%.31s", rem_ver);
            (void)!write(pfd[1], msg, strlen(msg));
        }
    } else {
        free(mraw);
        (void)!write(pfd[1], "OFFLINE", 7);
    }
    close(pfd[1]);
    _exit(0);
}

int try_signal_existing(int toggle, uint16_t port) {
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) return 0;

    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 500000;
    setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    struct sockaddr_in a;
    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (connect(s, (struct sockaddr *)&a, sizeof(a)) < 0) {
        close(s);
        return 0;
    }

    const char *m = toggle ? "KAREL_TOGGLE\n" : "KAREL_BOOP\n";
    (void)!write(s, m, strlen(m));
    close(s);
    return 1;
}

int start_ipc_server(uint16_t port) {
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) return -1;
    int yes = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    fcntl(s, F_SETFL, O_NONBLOCK);

    struct sockaddr_in a;
    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(s, (struct sockaddr *)&a, sizeof(a)) < 0 || listen(s, 8) < 0) {
        close(s);
        return -1;
    }
    return s;
}

#endif /* !KAREL_CORE_TEST */
