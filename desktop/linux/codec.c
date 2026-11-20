/* Karel de Koala - Bounded Gzip/Deflate Decoder, SHA-256 & SemVer Validation
 * Pure C99 with zero OS, filesystem, or network dependencies for easy auditing.
 */

#include "../karel_linux.h"

/* =========================================================================
 * Bitstream Reader & Canonical Huffman Decoder (RFC 1951)
 * ========================================================================= */

typedef struct {
    const uint8_t *src;
    size_t len;
    size_t pos;
    uint32_t bitbuf;
    int bitcnt;
} BitReader;

typedef struct {
    uint16_t count[16];
    uint16_t sym[320];
} HuffTable;

static int read_bit(BitReader *b) {
    if (b->bitcnt == 0) {
        if (b->pos >= b->len) return -1;
        b->bitbuf = b->src[b->pos++];
        b->bitcnt = 8;
    }
    int bit = (int)(b->bitbuf & 1U);
    b->bitbuf >>= 1;
    b->bitcnt--;
    return bit;
}

static int read_bits(BitReader *b, int nbits) {
    int val = 0;
    for (int i = 0; i < nbits; i++) {
        int bit = read_bit(b);
        if (bit < 0) return -1;
        val |= (bit << i);
    }
    return val;
}

static void huff_build(HuffTable *h, const uint8_t *lens, int n) {
    uint16_t offs[16];
    memset(h->count, 0, sizeof(h->count));
    for (int i = 0; i < n; i++) {
        if (lens[i] < 16) h->count[lens[i]]++;
    }
    offs[1] = 0;
    for (int i = 1; i < 15; i++) {
        offs[i + 1] = (uint16_t)(offs[i] + h->count[i]);
    }
    for (int i = 0; i < n; i++) {
        if (lens[i] > 0 && lens[i] < 16) {
            h->sym[offs[lens[i]]++] = (uint16_t)i;
        }
    }
}

static int huff_decode(BitReader *b, const HuffTable *h) {
    int code = 0, first = 0, idx = 0;
    for (int len = 1; len <= 15; len++) {
        int bit = read_bit(b);
        if (bit < 0) return -1;
        code |= bit;
        int c = h->count[len];
        if (code - c < first) {
            return (int)h->sym[idx + (code - first)];
        }
        idx += c;
        first += c;
        first <<= 1;
        code <<= 1;
    }
    return -1;
}

static uint8_t *inflate_grow(uint8_t *out, size_t *cap, size_t needed) {
    /* Reject decompressed payloads beyond MAX_INFLATE_BYTES (zip-bomb defense). */
    if (needed > MAX_INFLATE_BYTES) {
        free(out);
        return NULL;
    }
    if (needed + 2 <= *cap) return out;

    size_t ncap = (*cap) * 2;
    if (ncap < needed + 1024) ncap = needed + 1024;
    if (ncap > MAX_INFLATE_BYTES + 16) ncap = MAX_INFLATE_BYTES + 16;

    uint8_t *tmp = (uint8_t *)realloc(out, ncap);
    if (!tmp) {
        free(out);
        return NULL;
    }
    *cap = ncap;
    return tmp;
}

static int build_fixed_tables(HuffTable *lt, HuffTable *dt) {
    uint8_t ll[288], dl[32];
    for (int i = 0; i < 144; i++) ll[i] = 8;
    for (int i = 144; i < 256; i++) ll[i] = 9;
    for (int i = 256; i < 280; i++) ll[i] = 7;
    for (int i = 280; i < 288; i++) ll[i] = 8;
    memset(dl, 5, sizeof(dl));
    huff_build(lt, ll, 288);
    huff_build(dt, dl, 32);
    return 1;
}

static int build_dynamic_tables(BitReader *br, HuffTable *lt, HuffTable *dt) {
    static const uint8_t clord[19] = {
        16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15
    };
    int hlit = read_bits(br, 5) + 257;
    int hdist = read_bits(br, 5) + 1;
    int hclen = read_bits(br, 4) + 4;
    if (hlit < 257 || hdist < 1 || hclen < 4) return 0;

    uint8_t cll[19];
    memset(cll, 0, sizeof(cll));
    for (int i = 0; i < hclen; i++) {
        int v = read_bits(br, 3);
        if (v < 0) return 0;
        cll[clord[i]] = (uint8_t)v;
    }

    HuffTable ct;
    huff_build(&ct, cll, 19);

    uint8_t lens[320];
    int ti = 0;
    while (ti < hlit + hdist) {
        int s = huff_decode(br, &ct);
        if (s < 0) return 0;
        if (s < 16) {
            lens[ti++] = (uint8_t)s;
        } else {
            int rep = 0;
            uint8_t val = 0;
            if (s == 16) {
                if (ti == 0) return 0;
                val = lens[ti - 1];
                rep = 3 + read_bits(br, 2);
            } else if (s == 17) {
                rep = 3 + read_bits(br, 3);
            } else {
                rep = 11 + read_bits(br, 7);
            }
            while (rep-- > 0 && ti < 320) {
                lens[ti++] = val;
            }
        }
    }
    huff_build(lt, lens, hlit);
    huff_build(dt, lens + hlit, hdist);
    return 1;
}

uint8_t *inflate_gzip(const uint8_t *src, size_t len, size_t *out_len) {
    if (len < 18 || src[0] != 0x1f || src[1] != 0x8b || src[2] != 8) return NULL;

    /* Skip standard RFC 1952 header and optional extra/name/comment/HCRC fields. */
    uint8_t flg = src[3];
    size_t p = 10;
    if (flg & 0x04) {
        if (p + 2 > len) return NULL;
        p += 2 + ((size_t)src[p] | ((size_t)src[p + 1] << 8));
    }
    if (flg & 0x08) { while (p < len && src[p]) p++; p++; }
    if (flg & 0x10) { while (p < len && src[p]) p++; p++; }
    if (flg & 0x02) p += 2;
    if (p >= len) return NULL;

    size_t cap = len * 24 + 4096;
    if (cap > MAX_INFLATE_BYTES + 16) cap = MAX_INFLATE_BYTES + 16;
    uint8_t *out = (uint8_t *)malloc(cap);
    if (!out) return NULL;
    size_t out_n = 0;

    BitReader br = { src, len - 8, p, 0, 0 };
    static const uint16_t lbase[29] = {
        3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31,
        35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258
    };
    static const uint8_t lext[29] = {
        0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
        3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0
    };
    static const uint16_t dbase[30] = {
        1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193,
        257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577
    };
    static const uint8_t dext[30] = {
        0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
        7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13
    };

    int last = 0;
    while (!last) {
        last = read_bit(&br);
        int btype = read_bits(&br, 2);
        if (last < 0 || btype < 0 || btype == 3) { free(out); return NULL; }

        if (btype == 0) {
            br.bitcnt = 0;
            br.bitbuf = 0;
            if (br.pos + 4 > br.len) { free(out); return NULL; }
            uint16_t blen = (uint16_t)(br.src[br.pos] | (br.src[br.pos + 1] << 8));
            br.pos += 4;
            if (br.pos + blen > br.len) { free(out); return NULL; }
            out = inflate_grow(out, &cap, out_n + blen);
            if (!out) return NULL;
            memcpy(out + out_n, br.src + br.pos, blen);
            br.pos += blen;
            out_n += blen;
            continue;
        }

        HuffTable lt, dt;
        int ok = (btype == 1) ? build_fixed_tables(&lt, &dt) : build_dynamic_tables(&br, &lt, &dt);
        if (!ok) { free(out); return NULL; }

        while (1) {
            int s = huff_decode(&br, &lt);
            if (s < 0) { free(out); return NULL; }
            if (s < 256) {
                out = inflate_grow(out, &cap, out_n + 1);
                if (!out) return NULL;
                out[out_n++] = (uint8_t)s;
            } else if (s == 256) {
                break;
            } else {
                int li = s - 257;
                if (li >= 29) { free(out); return NULL; }
                int clen = (int)lbase[li] + read_bits(&br, lext[li]);
                int di = huff_decode(&br, &dt);
                if (di < 0 || di >= 30) { free(out); return NULL; }
                int dist = (int)dbase[di] + read_bits(&br, dext[di]);
                if (dist <= 0 || (size_t)dist > out_n) { free(out); return NULL; }
                out = inflate_grow(out, &cap, out_n + (size_t)clen);
                if (!out) return NULL;
                for (int k = 0; k < clen; k++) {
                    out[out_n] = out[out_n - (size_t)dist];
                    out_n++;
                }
            }
        }
    }

    out[out_n] = 0;
    if (out_len) *out_len = out_n;
    return out;
}

/* =========================================================================
 * FIPS 180-4 SHA-256 & Strict SemVer Validation
 * ========================================================================= */

void sha256_hex(const uint8_t *data, size_t len, char out[65]) {
    static const uint32_t K[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };
    uint32_t st[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };
    size_t pad_len = ((len + 9 + 63) / 64) * 64;
    uint8_t *msg = (uint8_t *)calloc(pad_len, 1);
    if (!msg) {
        out[0] = 0;
        return;
    }
    memcpy(msg, data, len);
    msg[len] = 0x80;
    uint64_t bitlen = (uint64_t)len * 8ULL;
    for (int i = 0; i < 8; i++) {
        msg[pad_len - 1 - (size_t)i] = (uint8_t)((bitlen >> (i * 8)) & 0xFF);
    }

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
        uint32_t a = st[0], b = st[1], c = st[2], d = st[3];
        uint32_t e = st[4], f = st[5], g = st[6], h = st[7];
        for (int i = 0; i < 64; i++) {
            uint32_t S1 = ROR32(e, 6) ^ ROR32(e, 11) ^ ROR32(e, 25);
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t t1 = h + S1 + ch + K[i] + w[i];
            uint32_t S0 = ROR32(a, 2) ^ ROR32(a, 13) ^ ROR32(a, 22);
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t t2 = S0 + maj;
            h = g; g = f; f = e; e = d + t1;
            d = c; c = b; b = a; a = t1 + t2;
        }
        st[0] += a; st[1] += b; st[2] += c; st[3] += d;
        st[4] += e; st[5] += f; st[6] += g; st[7] += h;
    }
    #undef ROR32

    free(msg);
    for (int i = 0; i < 8; i++) {
        snprintf(out + i * 8, 9, "%08x", st[i]);
    }
    out[64] = 0;
}

int is_valid_semver(const char *s) {
    if (!s || !*s) return 0;
    const char *p = s;
    for (int part = 0; part < 3; part++) {
        int digits = 0;
        while (*p >= '0' && *p <= '9') {
            digits++;
            p++;
        }
        if (digits < 1 || digits > 3) return 0;
        if (part < 2) {
            if (*p != '.') return 0;
            p++;
        }
    }
    return *p == '\0';
}

int compare_ver(const char *a, const char *b) {
    int pa[3] = {0, 0, 0}, pb[3] = {0, 0, 0};
    if (a) {
        if (*a == 'v' || *a == 'V') a++;
        (void)sscanf(a, "%d.%d.%d", &pa[0], &pa[1], &pa[2]);
    }
    if (b) {
        if (*b == 'v' || *b == 'V') b++;
        (void)sscanf(b, "%d.%d.%d", &pb[0], &pb[1], &pb[2]);
    }
    for (int i = 0; i < 3; i++) {
        if (pa[i] != pb[i]) return pa[i] > pb[i] ? 1 : -1;
    }
    return 0;
}
