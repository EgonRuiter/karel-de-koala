// Karel de Koala - Minimalist Zero-Install Windows Companion (.NET Framework 4.x / C# 5)
// Works standalone from the KAREL RP2350 USB stick without Python or pip installed.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.IO.Compression;
using System.IO.Ports;
using System.Media;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("Karel de Koala")]
[assembly: AssemblyDescription("Sticky RP2350 Desktop Koala Companion")]
[assembly: AssemblyCompany("Studievereniging Sticky")]
[assembly: AssemblyProduct("Karel de Koala")]
[assembly: AssemblyCopyright("Copyright (c) 2026 Studievereniging Sticky")]
[assembly: AssemblyVersion("2.3.0.0")]
[assembly: AssemblyFileVersion("2.3.0.0")]

namespace KarelNative {

    internal static class NativeWin {
        [StructLayout(LayoutKind.Sequential)]
        public struct RECT { public int Left, Top, Right, Bottom; }

        [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
        [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr value);
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
        [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
        [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, StringBuilder sb, int max);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int max);
        [DllImport("user32.dll")] public static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);
        [DllImport("user32.dll")] public static extern bool UnregisterHotKey(IntPtr hWnd, int id);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        public static extern bool GetVolumeInformation(string root, StringBuilder name, int nameLen, out uint serial, out uint maxComp, out uint flags, StringBuilder fs, int fsLen);

        private static readonly string[] MeetingMarkers = {
            "zoom meeting", "meeting | microsoft teams", "vergadering | microsoft teams",
            "google meet", "meet - ", "webex meeting", "powerpoint-diavoorstelling", "powerpoint slide show"
        };

        public static void EnableDpi() {
            try { if (!SetProcessDpiAwarenessContext((IntPtr)(-4))) SetProcessDPIAware(); }
            catch { try { SetProcessDPIAware(); } catch { } }
        }

        public static string GetDriveSerial(string root) {
            if (string.IsNullOrEmpty(root)) return "";
            try {
                uint ser, mc, fl;
                if (GetVolumeInformation(root, null, 0, out ser, out mc, out fl, null, 0) && ser != 0)
                    return ser.ToString("X8");
            } catch { }
            return "";
        }

        private static bool TryGetExternalFg(IntPtr own1, IntPtr own2, out IntPtr fg, out string title, out RECT r) {
            fg = IntPtr.Zero; title = ""; r = new RECT();
            try {
                fg = GetForegroundWindow();
                if (fg == IntPtr.Zero || fg == own1 || fg == own2 || !IsWindowVisible(fg) || IsIconic(fg)) return false;
                StringBuilder cls = new StringBuilder(64);
                GetClassName(fg, cls, cls.Capacity);
                string c = cls.ToString();
                if (c == "Shell_TrayWnd" || c == "Progman" || c == "WorkerW") return false;
                StringBuilder ttl = new StringBuilder(160);
                GetWindowText(fg, ttl, ttl.Capacity);
                title = ttl.ToString();
                if (title.StartsWith("Karel") || title == "Program Manager" || title.Length == 0) return false;
                return GetWindowRect(fg, out r);
            } catch { return false; }
        }

        public static Rectangle? GetForegroundLedge(IntPtr own1, IntPtr own2, int karelPx, Rectangle work) {
            IntPtr fg; string title; RECT r;
            if (!TryGetExternalFg(own1, own2, out fg, out title, out r)) return null;
            int w = r.Right - r.Left, h = r.Bottom - r.Top;
            if (w < Math.Max(karelPx + 48, 220) || h < 140 || r.Top < work.Top + 36 || r.Top > work.Bottom - 80) return null;
            int lx0 = Math.Max(work.Left, r.Left + 12);
            int lx1 = Math.Min(work.Right, r.Right - 12);
            if (lx1 - lx0 < karelPx + 20) return null;
            return new Rectangle(lx0, r.Top, lx1 - lx0, h);
        }

        public static string DetectFullscreenOrMeeting(IntPtr own1, IntPtr own2) {
            IntPtr fg; string title; RECT r;
            if (!TryGetExternalFg(own1, own2, out fg, out title, out r)) return "";
            string low = title.ToLowerInvariant();
            for (int i = 0; i < MeetingMarkers.Length; i++) {
                if (low.IndexOf(MeetingMarkers[i], StringComparison.Ordinal) >= 0) return "meeting";
            }
            try {
                Rectangle mb = Screen.FromHandle(fg).Bounds;
                if (r.Left <= mb.Left + 2 && r.Top <= mb.Top + 2 && r.Right >= mb.Right - 2 && r.Bottom >= mb.Bottom - 2)
                    return "fullscreen";
            } catch { }
            return "";
        }
    }

    internal sealed class SpriteBank {
        public readonly Dictionary<string, List<string[]>> States = new Dictionary<string, List<string[]>>();
        public readonly Dictionary<string, int> AnimDiv = new Dictionary<string, int>();
        private readonly Dictionary<char, Color> pal = new Dictionary<char, Color>();
        private readonly Dictionary<string, Bitmap> cache = new Dictionary<string, Bitmap>();

        public static readonly string[] SkinIds = { "classic", "sticky", "mint", "midnight", "gold", "crimson" };
        public static readonly string[] OutfitIds = { "scarf", "stickycap", "hoodie", "headphones", "shades", "crown", "wizard", "partyhat", "" };

        private static readonly HashSet<string> SkipOverlayStates = new HashSet<string>(new string[] {
            "SLEEP", "CRY", "YAWN", "DIZZY", "CLIMB", "DIVE_WAVE", "DIVE_DOWN",
            "PEEK", "BACKFLIP", "SPIN", "UMBRELLA", "MUSIC", "EXERCISE",
            "LAPTOP_CODE", "SIT", "STRETCH", "BOW", "PARTY_HORN", "GAMING"
        });

        public static SpriteBank LoadEmbedded() {
            SpriteBank bank = new SpriteBank();
            Assembly asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream("karel_sprites.gz"))
            using (GZipStream gz = new GZipStream(s, CompressionMode.Decompress))
            using (StreamReader sr = new StreamReader(gz, Encoding.UTF8)) {
                string curState = null;
                List<string> curRows = new List<string>();
                string line;
                while ((line = sr.ReadLine()) != null) {
                    if (line.StartsWith("PAL|")) {
                        string[] parts = line.Substring(4).Split(',');
                        for (int i = 0; i < parts.Length; i++) {
                            string[] kv = parts[i].Split(':');
                            if (kv.Length == 2 && kv[0].Length == 1 && kv[1].Length == 7)
                                bank.pal[kv[0][0]] = ColorTranslator.FromHtml(kv[1]);
                        }
                    } else if (line.StartsWith("DIV|")) {
                        string[] parts = line.Substring(4).Split(',');
                        for (int i = 0; i < parts.Length; i++) {
                            string[] kv = parts[i].Split('=');
                            int d;
                            if (kv.Length == 2 && int.TryParse(kv[1], out d)) bank.AnimDiv[kv[0]] = d;
                        }
                    } else if (line.StartsWith("@")) {
                        FlushFrame(bank, curState, curRows);
                        curState = line.Substring(1).Trim();
                    } else if (line == "---") {
                        FlushFrame(bank, curState, curRows);
                    } else if (curState != null && line.Length > 0) {
                        curRows.Add(line);
                    }
                }
                FlushFrame(bank, curState, curRows);
            }
            return bank;
        }

        private static void FlushFrame(SpriteBank bank, string st, List<string> rows) {
            if (string.IsNullOrEmpty(st) || rows.Count == 0) { rows.Clear(); return; }
            List<string[]> list;
            if (!bank.States.TryGetValue(st, out list)) {
                list = new List<string[]>();
                bank.States[st] = list;
            }
            list.Add(rows.ToArray());
            rows.Clear();
        }

        private static char MapSkinChar(string skin, char ch) {
            if (skin == "sticky") { if (ch == 'g') return 'r'; if (ch == 's') return 'R'; if (ch == 'w') return 'W'; }
            else if (skin == "mint") { if (ch == 'g') return 'n'; if (ch == 's') return 'e'; if (ch == 'w') return 'W'; }
            else if (skin == "midnight") { if (ch == 'g') return 'm'; if (ch == 's') return 'k'; if (ch == 'w') return 'b'; }
            else if (skin == "gold") { if (ch == 'g') return 'y'; if (ch == 's') return 'Y'; if (ch == 'w') return 'W'; }
            else if (skin == "crimson") { if (ch == 'g') return 'R'; if (ch == 's') return 'r'; if (ch == 'w') return 'y'; }
            return ch;
        }

        private static void FillRect(char[,] g, int x0, int y0, int x1, int y1, char ch) {
            for (int y = Math.Max(0, y0); y <= Math.Min(31, y1); y++)
                for (int x = Math.Max(0, x0); x <= Math.Min(31, x1); x++)
                    g[y, x] = ch;
        }

        private static void PutPx(char[,] g, int x, int y, char ch) {
            if (x >= 0 && x < 32 && y >= 0 && y < 32) g[y, x] = ch;
        }

        private static void ApplyOutfitAndTime(char[,] g, string st, string item, bool tired, bool vm) {
            if (SkipOverlayStates.Contains(st)) return;
            if (item == "scarf") {
                FillRect(g, 10, 17, 21, 18, 'r'); FillRect(g, 17, 19, 18, 22, 'r');
                for (int x = 10; x <= 21; x += 3) PutPx(g, x, 18, 'R');
            } else if (item == "stickycap" && st != "JUMP") {
                FillRect(g, 9, 4, 22, 5, 'r'); FillRect(g, 11, 2, 20, 4, 'r'); FillRect(g, 19, 5, 25, 5, 'R');
                PutPx(g, 15, 3, 'W'); PutPx(g, 16, 3, 'W');
            } else if (item == "hoodie") {
                FillRect(g, 8, 19, 11, 20, 'r'); FillRect(g, 20, 19, 23, 20, 'r'); FillRect(g, 11, 24, 20, 25, 'r');
            } else if (item == "headphones" && st != "JUMP") {
                FillRect(g, 3, 7, 4, 11, 'r'); FillRect(g, 27, 7, 28, 11, 'r'); FillRect(g, 7, 4, 24, 4, 'd');
                PutPx(g, 5, 6, 'd'); PutPx(g, 6, 5, 'd'); PutPx(g, 25, 5, 'd'); PutPx(g, 26, 6, 'd');
            } else if (item == "shades" && st != "JUMP") {
                FillRect(g, 10, 10, 13, 12, 'k'); FillRect(g, 18, 10, 21, 12, 'k'); FillRect(g, 14, 11, 17, 11, 'd');
                PutPx(g, 11, 11, 'W'); PutPx(g, 19, 11, 'W');
            } else if (item == "crown" && st != "JUMP") {
                FillRect(g, 12, 3, 19, 5, 'y');
                PutPx(g, 12, 2, 'y'); PutPx(g, 15, 1, 'y'); PutPx(g, 16, 1, 'y'); PutPx(g, 19, 2, 'y');
                PutPx(g, 15, 4, 'R'); PutPx(g, 16, 4, 'R'); PutPx(g, 11, 5, 'k'); PutPx(g, 20, 5, 'k');
            } else if (item == "wizard" && st != "JUMP") {
                FillRect(g, 9, 4, 22, 5, 'm'); FillRect(g, 12, 2, 19, 3, 'm');
                FillRect(g, 14, 0, 17, 1, 'm'); FillRect(g, 11, 4, 20, 4, 'y');
                PutPx(g, 15, 2, 'y'); PutPx(g, 16, 1, 'W');
            } else if (item == "partyhat" && st != "JUMP") {
                FillRect(g, 13, 3, 18, 5, 'm'); FillRect(g, 14, 1, 17, 2, 'R');
                PutPx(g, 15, 0, 'y'); PutPx(g, 16, 0, 'y'); PutPx(g, 14, 4, 'y'); PutPx(g, 17, 3, 'b');
            }
            if (tired && st != "HYPER" && st != "JUMP") {
                int[] xs = { 11, 12, 19, 20 }, ys = { 11, 13 };
                for (int ix = 0; ix < xs.Length; ix++)
                    for (int iy = 0; iy < ys.Length; iy++) PutPx(g, xs[ix], ys[iy], 's');
            }
            if (vm && st != "EAT" && st != "STUDY" && st != "JUMP" && st != "CLIMB" && st != "BORREL") {
                FillRect(g, 24, 18, 28, 23, 'k'); FillRect(g, 25, 19, 27, 22, 'y'); FillRect(g, 24, 17, 27, 18, 'W');
            }
        }

        public Bitmap GetFrame(string st, int frameIdx, string skin, string item) {
            List<string[]> frames;
            if (!States.TryGetValue(st, out frames) || frames.Count == 0) { st = "IDLE"; frames = States["IDLE"]; }
            int div = 2;
            AnimDiv.TryGetValue(st, out div);
            if (div < 1) div = 1;
            int fi = (frameIdx / div) % frames.Count;
            DateTime now = DateTime.Now;
            bool tired = now.Hour >= 0 && now.Hour < 4;
            bool vm = now.DayOfWeek == DayOfWeek.Friday && now.Hour >= 16;
            string sk = string.IsNullOrEmpty(skin) ? "classic" : skin;
            string it = item ?? "";
            string key = string.Format("{0}|{1}|{2}|{3}|{4}|{5}", sk, it, st, fi, tired ? 1 : 0, vm ? 1 : 0);
            Bitmap cached;
            if (cache.TryGetValue(key, out cached)) return cached;

            string[] raw = frames[fi];
            char[,] g = new char[32, 32];
            for (int y = 0; y < 32; y++) {
                string r = y < raw.Length ? raw[y] : "";
                for (int x = 0; x < 32; x++) {
                    char ch = x < r.Length ? r[x] : '.';
                    g[y, x] = ch == '.' ? '.' : MapSkinChar(sk, ch);
                }
            }
            ApplyOutfitAndTime(g, st, it, tired, vm);

            Bitmap bmp = new Bitmap(32, 32, PixelFormat.Format32bppArgb);
            for (int y = 0; y < 32; y++)
                for (int x = 0; x < 32; x++) {
                    Color c;
                    if (g[y, x] != '.' && pal.TryGetValue(g[y, x], out c)) bmp.SetPixel(x, y, c);
                }
            if (cache.Count > 360) {
                foreach (Bitmap old in cache.Values) old.Dispose();
                cache.Clear();
            }
            cache[key] = bmp;
            return bmp;
        }
    }

    internal sealed class WavSynth {
        private readonly Dictionary<string, byte[]> bank = new Dictionary<string, byte[]>();
        private readonly object playLock = new object();
        public bool Muted = false;
        public bool AutoQuiet = false;

        public WavSynth() {
            bank["climb"] = BuildSeq(new double[] { 330, 392, 523.25 }, 0.065, 0.20);
            bank["pet"] = BuildSeq(new double[] { 523.25, 659.25, 783.99 }, 0.055, 0.18);
            bank["eat"] = BuildSeq(new double[] { 293.66, 349.23, 440 }, 0.06, 0.20);
            bank["coffee"] = BuildSeq(new double[] { 440, 554.37, 659.25, 880 }, 0.05, 0.20);
            bank["boop"] = BuildSeq(new double[] { 587.33, 783.99, 1046.5 }, 0.06, 0.22);
            bank["levelup"] = BuildSeq(new double[] { 440, 554.37, 659.25, 880 }, 0.09, 0.22);
            bank["dive"] = BuildSeq(new double[] { 659.25, 523.25, 392.0, 261.63 }, 0.08, 0.20);
            bank["sneeze"] = BuildSeq(new double[] { 780, 220 }, 0.08, 0.22);
            bank["chirp"] = BuildSeq(new double[] { 620, 740 }, 0.035, 0.12);
        }

        private static byte[] BuildSeq(double[] freqs, double noteDur, double amp) {
            const int sr = 22050;
            int nPer = Math.Max(100, (int)(noteDur * sr));
            int total = nPer * freqs.Length;
            short[] pcm = new short[total];
            for (int fi = 0; fi < freqs.Length; fi++) {
                double f = freqs[fi], ph = 0.0;
                for (int i = 0; i < nPer; i++) {
                    double env = Math.Min(1.0, i / 120.0) * Math.Min(1.0, (nPer - i) / 220.0);
                    double s = Math.Sin(ph) + 0.28 * Math.Sin(2.0 * ph);
                    pcm[fi * nPer + i] = (short)(s * env * amp * 24000.0);
                    ph += 2.0 * Math.PI * f / sr;
                }
            }
            using (MemoryStream ms = new MemoryStream())
            using (BinaryWriter bw = new BinaryWriter(ms)) {
                int dataBytes = total * 2;
                bw.Write(Encoding.ASCII.GetBytes("RIFF")); bw.Write(36 + dataBytes);
                bw.Write(Encoding.ASCII.GetBytes("WAVEfmt ")); bw.Write(16);
                bw.Write((short)1); bw.Write((short)1);
                bw.Write(sr); bw.Write(sr * 2);
                bw.Write((short)2); bw.Write((short)16);
                bw.Write(Encoding.ASCII.GetBytes("data")); bw.Write(dataBytes);
                for (int i = 0; i < total; i++) bw.Write(pcm[i]);
                bw.Flush();
                return ms.ToArray();
            }
        }

        public void Play(string key) {
            if (Muted || AutoQuiet) return;
            byte[] wav;
            if (!bank.TryGetValue(key, out wav)) return;
            ThreadPool.QueueUserWorkItem(delegate {
                lock (playLock) {
                    try {
                        using (MemoryStream ms = new MemoryStream(wav))
                        using (SoundPlayer sp = new SoundPlayer(ms)) { sp.PlaySync(); }
                    } catch { }
                }
            });
        }
    }

    internal sealed class SaveStore {
        private readonly JavaScriptSerializer json = new JavaScriptSerializer();
        private readonly object ioLock = new object();
        public string DriveRoot;
        public string FallbackPath;
        public bool Connected;
        private volatile bool dirty;
        public Dictionary<string, object> Data = new Dictionary<string, object>();

        public SaveStore() {
            string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            if (string.IsNullOrEmpty(appData)) appData = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            FallbackPath = Path.Combine(appData, "KarelDeKoala_save.json");
            DriveRoot = FindKarelDrive();
            Connected = !string.IsNullOrEmpty(DriveRoot);
        }

        public static string FindKarelDrive() {
            try {
                DriveInfo[] drives = DriveInfo.GetDrives();
                for (int i = 0; i < drives.Length; i++) {
                    DriveInfo d = drives[i];
                    if (!d.IsReady) continue;
                    string r = d.RootDirectory.FullName;
                    if (File.Exists(Path.Combine(r, ".karel_drive")) ||
                        string.Equals(d.VolumeLabel, "KAREL", StringComparison.OrdinalIgnoreCase))
                        return r;
                }
            } catch { }
            string here = AppDomain.CurrentDomain.BaseDirectory;
            if (File.Exists(Path.Combine(here, ".karel_drive"))) return here;
            return null;
        }

        public string PollUsb() {
            string cur = FindKarelDrive();
            bool was = Connected;
            Connected = !string.IsNullOrEmpty(cur);
            if (!string.IsNullOrEmpty(cur)) DriveRoot = cur;
            if (was && !Connected) return "off";
            if (!was && Connected) return "on";
            return null;
        }

        public bool HasNoHidFlag() {
            return !string.IsNullOrEmpty(DriveRoot) && File.Exists(Path.Combine(DriveRoot, ".karel_no_hid"));
        }

        public bool? ToggleNoHidFlag() {
            if (string.IsNullOrEmpty(DriveRoot) || !Directory.Exists(DriveRoot)) return null;
            string p = Path.Combine(DriveRoot, ".karel_no_hid");
            try {
                if (File.Exists(p)) { File.Delete(p); return false; }
                File.WriteAllText(p, "MAC_SAFE_NO_WIN_R\n", Encoding.UTF8);
                return true;
            } catch { return null; }
        }

        public static int XpForNextLevel(int lvl) {
            return lvl <= 0 ? 0 : 180 * lvl * (lvl + 1);
        }

        public static int LevelFromXp(int xp) {
            int lvl = 1;
            while (xp >= XpForNextLevel(lvl)) lvl++;
            return lvl;
        }

        private static readonly UTF8Encoding Utf8NoBom = new UTF8Encoding(false);

        private Dictionary<string, object> ReadDict(string path) {
            if (string.IsNullOrEmpty(path) || !File.Exists(path)) return null;
            try {
                byte[] raw = File.ReadAllBytes(path);
                if (raw.Length < 2) return null;
                int start = (raw.Length >= 3 && raw[0] == 0xEF && raw[1] == 0xBB && raw[2] == 0xBF) ? 3 : 0;
                for (int i = start; i < raw.Length; i++) {
                    if (raw[i] == 0xFF || raw[i] == 0x00) return null;
                }
                string text = Utf8NoBom.GetString(raw, start, raw.Length - start).Trim();
                if (!text.StartsWith("{") || !text.EndsWith("}")) return null;
                object obj = json.DeserializeObject(text);
                return obj as Dictionary<string, object>;
            } catch { return null; }
        }

        private static long RankSave(Dictionary<string, object> d) {
            DateTime dt = DateTime.MinValue;
            object ls;
            if (d.TryGetValue("last_seen", out ls) && ls != null) DateTime.TryParse(ls.ToString(), out dt);
            return (dt.Ticks / 10000000L) * 100000L + GetIntFrom(d, "xp", 0);
        }

        public void Load() {
            string usbPath = string.IsNullOrEmpty(DriveRoot) ? null : Path.Combine(DriveRoot, "save.json");
            string curSer = string.IsNullOrEmpty(DriveRoot) ? "" : NativeWin.GetDriveSerial(DriveRoot);
            Dictionary<string, object> u = ReadDict(usbPath), f = ReadDict(FallbackPath), picked = null;
            bool recoveredFb = false;
            if (u != null && f != null) {
                string uSer = GetStrFrom(u, "stick_serial", "");
                if (string.IsNullOrEmpty(uSer)) uSer = curSer;
                string fSer = GetStrFrom(f, "stick_serial", "");
                if (!string.IsNullOrEmpty(fSer) && uSer == fSer && RankSave(f) > RankSave(u)) {
                    picked = f; recoveredFb = true;
                } else picked = u;
            } else if (u != null) picked = u;
            else if (f != null) {
                if (string.IsNullOrEmpty(DriveRoot) || (GetStrFrom(f, "stick_serial", "") == curSer && !string.IsNullOrEmpty(curSer))) {
                    picked = f; recoveredFb = !string.IsNullOrEmpty(DriveRoot);
                }
            }
            Data = DefaultSave();
            if (picked != null) {
                foreach (KeyValuePair<string, object> kv in picked) Data[kv.Key] = kv.Value;
            }
            DateTime prev;
            if (DateTime.TryParse(GetStr("last_seen", ""), out prev)) {
                double hrs = Math.Max(0.0, (DateTime.Now - prev).TotalSeconds / 3600.0);
                if (hrs > 0.05) {
                    Data["hunger"] = Math.Max(5, (int)Math.Round(GetInt("hunger", 80) - hrs * 2.5));
                    Data["happiness"] = Math.Max(10, (int)Math.Round(GetInt("happiness", 85) - hrs * 2.0));
                    Data["hygiene"] = Math.Max(15, (int)Math.Round(GetInt("hygiene", 90) - hrs * 1.1));
                    Data["caffeine"] = Math.Max(0, (int)Math.Round(GetInt("caffeine", 25) - hrs * 8.0));
                    if (hrs >= 1.0) Data["energy"] = Math.Min(100, (int)Math.Round(GetInt("energy", 85) + hrs * 5.0));
                }
            }
            Data["level"] = LevelFromXp(GetInt("xp", 0));
            if (!string.IsNullOrEmpty(curSer)) Data["stick_serial"] = curSer;
            if (recoveredFb) Save();
        }

        private static Dictionary<string, object> DefaultSave() {
            Dictionary<string, object> d = new Dictionary<string, object>();
            d["name"] = "Karel"; d["hunger"] = 80; d["happiness"] = 85;
            d["energy"] = 85; d["hygiene"] = 90; d["caffeine"] = 25;
            d["xp"] = 0; d["level"] = 1;
            d["total_pets"] = 0; d["roam_mode"] = "free"; d["karel_scale"] = 3;
            d["skin"] = "classic"; d["equipped"] = new string[] { "scarf" };
            d["auto_quiet_fullscreen"] = true;
            d["language"] = "nl"; d["stick_serial"] = "";
            d["last_seen"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss");
            return d;
        }

        public static int GetIntFrom(Dictionary<string, object> dict, string key, int def) {
            object v;
            if (dict == null || !dict.TryGetValue(key, out v) || v == null) return def;
            try { return Convert.ToInt32(v); } catch { return def; }
        }

        public static string GetStrFrom(Dictionary<string, object> dict, string key, string def) {
            object v;
            if (dict == null || !dict.TryGetValue(key, out v) || v == null) return def;
            return v.ToString();
        }

        public int GetInt(string key, int def) { return GetIntFrom(Data, key, def); }
        public string GetStr(string key, string def) { return GetStrFrom(Data, key, def); }

        public bool GetBool(string key, bool def) {
            object v;
            if (Data == null || !Data.TryGetValue(key, out v) || v == null) return def;
            try { return Convert.ToBoolean(v); } catch { return def; }
        }

        public string GetEquippedItem() {
            object v;
            if (!Data.TryGetValue("equipped", out v) || v == null) return "";
            object[] arr = v as object[];
            if (arr != null && arr.Length > 0 && arr[0] != null) return arr[0].ToString();
            System.Collections.IList lst = v as System.Collections.IList;
            if (lst != null && lst.Count > 0 && lst[0] != null) return lst[0].ToString();
            return "";
        }

        public void SetEquippedItem(string item) {
            Data["equipped"] = string.IsNullOrEmpty(item) ? new string[0] : new string[] { item };
        }

        public void ClampStat(string key, int delta, int lo, int hi) {
            Data[key] = Math.Max(lo, Math.Min(hi, GetInt(key, lo) + delta));
        }

        public void Save() {
            lock (ioLock) {
                if (Connected && !string.IsNullOrEmpty(DriveRoot) && string.IsNullOrEmpty(GetStr("stick_serial", ""))) {
                    string ser = NativeWin.GetDriveSerial(DriveRoot);
                    if (!string.IsNullOrEmpty(ser)) Data["stick_serial"] = ser;
                }
                Data["last_seen"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss");
                string txt = json.Serialize(Data) + "\n";
                AtomicWrite(FallbackPath, txt);
                if (Connected && !string.IsNullOrEmpty(DriveRoot) && Directory.Exists(DriveRoot)) {
                    WriteUsbFlush(Path.Combine(DriveRoot, "save.json"), txt);
                }
                dirty = false;
            }
        }

        public void MarkDirty() { dirty = true; }
        public void FlushIfDirty() { if (dirty) Save(); }

        private static void WriteUsbFlush(string path, string txt) {
            try {
                byte[] bytes = Utf8NoBom.GetBytes(txt);
                bool keepHidden = File.Exists(path) && ((File.GetAttributes(path) & FileAttributes.Hidden) != 0);
                if (File.Exists(path)) {
                    try { File.SetAttributes(path, FileAttributes.Normal); } catch { }
                }
                using (FileStream fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough)) {
                    fs.Write(bytes, 0, bytes.Length);
                    fs.Flush(true);
                }
                if (keepHidden) {
                    try { File.SetAttributes(path, File.GetAttributes(path) | FileAttributes.Hidden); } catch { }
                }
            } catch { }
        }

        private static void AtomicWrite(string path, string txt) {
            try {
                string dir = Path.GetDirectoryName(path);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                byte[] bytes = Utf8NoBom.GetBytes(txt);
                string tmp = path + ".tmp";
                using (FileStream fs = new FileStream(tmp, FileMode.Create, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough)) {
                    fs.Write(bytes, 0, bytes.Length);
                    fs.Flush(true);
                }
                if (File.Exists(path)) File.Delete(path);
                File.Move(tmp, path);
            } catch { }
        }
    }

    internal sealed class SerialSync {
        private SerialPort sp;
        private string lastState = "";
        private volatile bool stopping;
        private volatile bool paused;
        private readonly AutoResetEvent wakeEv = new AutoResetEvent(false);
        public string PortName = "";
        private readonly Action<string> onEvent;

        public SerialSync(Action<string> onEvent) {
            this.onEvent = onEvent;
            Thread t = new Thread(new ThreadStart(Loop));
            t.IsBackground = true;
            t.Start();
        }

        public void SetPaused(bool p) {
            paused = p;
            if (p) Drop();
            else { try { wakeEv.Set(); } catch { } }
        }

        public void Send(string line) {
            if (sp == null) return;
            if (line.StartsWith("STATE:")) {
                if (line == lastState) return;
                lastState = line;
            }
            try { sp.WriteLine(line.Trim()); } catch { Drop(); }
        }

        private void Drop() {
            if (sp != null) { try { sp.Close(); sp.Dispose(); } catch { } }
            sp = null; PortName = ""; lastState = "";
        }

        private static int ParseComNum(string p) {
            int v = 0;
            if (p != null && p.StartsWith("COM", StringComparison.OrdinalIgnoreCase)) int.TryParse(p.Substring(3), out v);
            return v;
        }

        private void TryConnect() {
            string[] names;
            try { names = SerialPort.GetPortNames(); } catch { return; }
            Array.Sort(names, delegate(string a, string b) { return ParseComNum(b).CompareTo(ParseComNum(a)); });
            for (int i = 0; i < names.Length; i++) {
                SerialPort cand = null;
                try {
                    cand = new SerialPort(names[i], 115200);
                    cand.NewLine = "\n";
                    cand.DtrEnable = true;
                    cand.RtsEnable = true;
                    cand.ReadTimeout = 120;
                    cand.WriteTimeout = 150;
                    cand.Open();
                    Thread.Sleep(25);
                    cand.DiscardInBuffer();
                    cand.WriteLine("KAREL_PING");
                    string resp = cand.ReadLine();
                    if (resp != null && resp.IndexOf("KAREL_PONG", StringComparison.Ordinal) >= 0) {
                        cand.ReadTimeout = 60;
                        sp = cand; PortName = names[i];
                        return;
                    }
                    cand.Close();
                } catch { if (cand != null) { try { cand.Close(); } catch { } } }
            }
        }

        private void Loop() {
            DateTime lastHb = DateTime.Now;
            while (!stopping) {
                if (paused) { wakeEv.WaitOne(); continue; }
                if (sp == null) { TryConnect(); Thread.Sleep(350); continue; }
                if ((DateTime.Now - lastHb).TotalSeconds >= 1.0) {
                    lastHb = DateTime.Now;
                    Send("KAREL_PING");
                    if (sp == null) continue;
                }
                try {
                    string line = sp.ReadLine();
                    if (!string.IsNullOrEmpty(line)) {
                        string t = line.Trim();
                        if (t.StartsWith("EVENT:") && onEvent != null) onEvent(t);
                    }
                } catch (TimeoutException) { Thread.Sleep(35); }
                catch { Drop(); }
            }
        }

        public void Stop() { stopping = true; Drop(); try { wakeEv.Set(); } catch { } }
    }

    internal static class StartupHelper {
        private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
        private const string AppName = "KarelDeKoala";

        public static bool IsEnabled() {
            try {
                using (RegistryKey k = Registry.CurrentUser.OpenSubKey(RunKey, false)) {
                    return k != null && k.GetValue(AppName) != null;
                }
            } catch { return false; }
        }

        public static string InstalledDir() {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), AppName);
        }

        public static string InstalledExePath() {
            return Path.Combine(InstalledDir(), "karel_native.exe");
        }

        public static bool IsRunningInstalled() {
            try {
                return string.Equals(Path.GetFullPath(Application.ExecutablePath), Path.GetFullPath(InstalledExePath()), StringComparison.OrdinalIgnoreCase);
            } catch { return false; }
        }

        public static void ScheduleRemoveInstalledDir() {
            string dir = InstalledDir();
            if (!Directory.Exists(dir)) return;
            try {
                Process.Start(new ProcessStartInfo("cmd.exe", "/c timeout /t 2 /nobreak >nul & rmdir /s /q \"" + dir + "\"") {
                    WindowStyle = ProcessWindowStyle.Hidden,
                    CreateNoWindow = true,
                    UseShellExecute = false
                });
            } catch { }
        }

        public static bool SetEnabled(bool on) {
            try {
                string dstExe = InstalledExePath();
                string localDir = InstalledDir();
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(RunKey)) {
                    if (on) {
                        Directory.CreateDirectory(localDir);
                        string curExe = Path.GetFullPath(Application.ExecutablePath);
                        if (!string.Equals(curExe, Path.GetFullPath(dstExe), StringComparison.OrdinalIgnoreCase)) {
                            if (File.Exists(dstExe)) {
                                try { File.SetAttributes(dstExe, FileAttributes.Normal); } catch { }
                            }
                            File.Copy(curExe, dstExe, true);
                        }
                        k.SetValue(AppName, "\"" + dstExe + "\" --tray");
                    } else {
                        k.DeleteValue(AppName, false);
                        if (!IsRunningInstalled() && Directory.Exists(localDir)) {
                            try { Directory.Delete(localDir, true); } catch { }
                        }
                    }
                }
                return on;
            } catch { return IsEnabled(); }
        }

        public static void UninstallFromPc(string fallbackSavePath) {
            try {
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(RunKey)) {
                    if (k != null) k.DeleteValue(AppName, false);
                }
            } catch { }
            try {
                if (!string.IsNullOrEmpty(fallbackSavePath)) {
                    if (File.Exists(fallbackSavePath)) File.Delete(fallbackSavePath);
                    if (File.Exists(fallbackSavePath + ".tmp")) File.Delete(fallbackSavePath + ".tmp");
                }
            } catch { }
            string dir = InstalledDir();
            if (Directory.Exists(dir)) {
                if (IsRunningInstalled()) ScheduleRemoveInstalledDir();
                else { try { Directory.Delete(dir, true); } catch { ScheduleRemoveInstalledDir(); } }
            }
        }

        public static bool Toggle() {
            return SetEnabled(!IsEnabled());
        }
    }

    internal static class AutoUpdater {
        public const string Version = "2.3.0";
        public const string ManifestUrl = "https://github.com/EgonRuiter/karel-de-koala/releases/latest/download/version.json";

        public static int CompareVer(string a, string b) {
            int[] pa = ParseVer(a), pb = ParseVer(b);
            for (int i = 0; i < 3; i++) {
                if (pa[i] != pb[i]) return pa[i] > pb[i] ? 1 : -1;
            }
            return 0;
        }

        private static int[] ParseVer(string v) {
            int[] r = { 0, 0, 0 };
            if (string.IsNullOrEmpty(v)) return r;
            string s = v.Trim().TrimStart('v', 'V');
            string[] parts = s.Split('.');
            for (int i = 0; i < Math.Min(3, parts.Length); i++) {
                int val;
                if (int.TryParse(parts[i], out val)) r[i] = val;
            }
            return r;
        }

        public static string Sha256Hex(byte[] data) {
            using (SHA256 sha = SHA256.Create()) {
                byte[] hash = sha.ComputeHash(data);
                StringBuilder sb = new StringBuilder(hash.Length * 2);
                for (int i = 0; i < hash.Length; i++) sb.Append(hash[i].ToString("x2"));
                return sb.ToString();
            }
        }

        private static byte[] FetchBytes(string url, int timeoutMs) {
            try {
                try { ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072 | SecurityProtocolType.Tls12; } catch { }
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
                req.Timeout = timeoutMs;
                req.ReadWriteTimeout = timeoutMs;
                req.UserAgent = "KarelDeKoala/" + Version;
                req.AllowAutoRedirect = true;
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                using (Stream st = resp.GetResponseStream())
                using (MemoryStream ms = new MemoryStream()) {
                    byte[] buf = new byte[8192];
                    int n;
                    while ((n = st.Read(buf, 0, buf.Length)) > 0) ms.Write(buf, 0, n);
                    return ms.ToArray();
                }
            } catch { return null; }
        }

        private static bool UpdateFirmwareIfNeeded(SaveStore save, string codeUrl, string codeSha) {
            if (!save.Connected || string.IsNullOrEmpty(codeUrl) || string.IsNullOrEmpty(codeSha)) return false;
            string bootP = Path.Combine(save.DriveRoot, "boot.py");
            string codeP = Path.Combine(save.DriveRoot, "code.py");
            if (!File.Exists(bootP) || !File.Exists(codeP)) return false;
            try {
                byte[] cur = File.ReadAllBytes(codeP);
                if (string.Equals(Sha256Hex(cur), codeSha.Trim(), StringComparison.OrdinalIgnoreCase)) return false;
                byte[] next = FetchBytes(codeUrl, 10000);
                if (next == null || next.Length < 500) return false;
                if (!string.Equals(Sha256Hex(next), codeSha.Trim(), StringComparison.OrdinalIgnoreCase)) return false;
                bool keepHidden = (File.GetAttributes(codeP) & FileAttributes.Hidden) != 0;
                try { File.SetAttributes(codeP, FileAttributes.Normal); } catch { }
                using (FileStream fs = new FileStream(codeP, FileMode.Create, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough)) {
                    fs.Write(next, 0, next.Length);
                    fs.Flush(true);
                }
                if (keepHidden) { try { File.SetAttributes(codeP, File.GetAttributes(codeP) | FileAttributes.Hidden); } catch { } }
                return true;
            } catch { return false; }
        }

        public static void CheckNowAsync(SaveStore save, string updatedFrom, Action<string, string> onReady, Action<string> onStatus) {
            Thread t = new Thread(new ThreadStart(delegate {
                try {
                    byte[] raw = FetchBytes(ManifestUrl, 6000);
                    if (raw == null || raw.Length == 0) { if (onStatus != null) onStatus("offline"); return; }
                    JavaScriptSerializer ser = new JavaScriptSerializer();
                    Dictionary<string, object> man = ser.DeserializeObject(Encoding.UTF8.GetString(raw)) as Dictionary<string, object>;
                    if (man == null) { if (onStatus != null) onStatus("error"); return; }
                    string remVer = SaveStore.GetStrFrom(man, "version", "");
                    if (CompareVer(remVer, Version) <= 0 || (!string.IsNullOrEmpty(updatedFrom) && CompareVer(remVer, updatedFrom) == 0)) {
                        if (onStatus != null) onStatus("uptodate");
                        return;
                    }

                    if (onStatus != null) onStatus("downloading:" + remVer);
                    string exeUrl = SaveStore.GetStrFrom(man, "exe_url", "");
                    string exeSha = SaveStore.GetStrFrom(man, "exe_sha256", "");
                    if (string.IsNullOrEmpty(exeUrl) || string.IsNullOrEmpty(exeSha)) { if (onStatus != null) onStatus("error"); return; }
                    byte[] exeBytes = FetchBytes(exeUrl, 15000);
                    if (exeBytes == null || exeBytes.Length < 20000 || !string.Equals(Sha256Hex(exeBytes), exeSha.Trim(), StringComparison.OrdinalIgnoreCase)) {
                        if (onStatus != null) onStatus("error");
                        return;
                    }

                    UpdateFirmwareIfNeeded(save, SaveStore.GetStrFrom(man, "code_py_url", ""), SaveStore.GetStrFrom(man, "code_py_sha256", ""));

                    string curExe = Application.ExecutablePath;
                    string stageNew = Path.Combine(Path.GetTempPath(), "karel_native_" + remVer + ".exe");
                    File.WriteAllBytes(stageNew, exeBytes);

                    string usbCopyCmd = "";
                    if (save.Connected) {
                        string winExe = Path.Combine(save.DriveRoot, "Karel (Windows).exe");
                        string oldExe = Path.Combine(save.DriveRoot, "karel_native.exe");
                        string usbExe = File.Exists(winExe) ? winExe : (File.Exists(oldExe) ? oldExe : winExe);
                        if (!string.Equals(Path.GetFullPath(curExe), Path.GetFullPath(usbExe), StringComparison.OrdinalIgnoreCase))
                            usbCopyCmd += string.Format("copy /Y \"{0}\" \"{1}\" >nul 2>&1\r\n", curExe, usbExe);
                    }
                    if (StartupHelper.IsEnabled()) {
                        string instExe = StartupHelper.InstalledExePath();
                        if (!string.Equals(Path.GetFullPath(curExe), Path.GetFullPath(instExe), StringComparison.OrdinalIgnoreCase))
                            usbCopyCmd += string.Format("copy /Y \"{0}\" \"{1}\" >nul 2>&1\r\n", curExe, instExe);
                    }
                    string cmdPath = Path.Combine(Path.GetTempPath(), "karel_upd.cmd");
                    string script = string.Format(
                        "@echo off\r\n:wait\r\ntimeout /t 1 /nobreak >nul\r\ncopy /Y \"{0}\" \"{1}\" >nul 2>&1\r\nif errorlevel 1 goto :wait\r\ndel \"{0}\" >nul 2>&1\r\n{2}start \"\" \"{1}\" --updated-from={3}\r\ndel \"%~f0\"\r\n",
                        stageNew, curExe, usbCopyCmd, remVer
                    );
                    File.WriteAllText(cmdPath, script, Encoding.Default);
                    if (onReady != null) onReady(remVer, cmdPath);
                } catch { if (onStatus != null) onStatus("error"); }
            }));
            t.IsBackground = true;
            t.Start();
        }
    }

    internal sealed class KarelForm : Form {
        private readonly SpriteBank sprites;
        private readonly SaveStore save;
        private readonly WavSynth snd = new WavSynth();
        private readonly SerialSync ser;
        private readonly Queue<string> rxQueue = new Queue<string>();
        private readonly object rxLock = new object();
        private readonly NotifyIcon trayIcon;
        private readonly System.Windows.Forms.Timer tick = new System.Windows.Forms.Timer();
        private readonly System.Windows.Forms.Timer usbDebounce = new System.Windows.Forms.Timer();
        private readonly Random rng = new Random();
        private TcpListener ipcSrv;
        private Form hubForm;

        private string state = "IDLE", roamMode = "free", bubble = "";
        private int scale = 3, frameIdx = 0, actTicks = 0, bubbleTicks = 0, discoTicks = 0, hyperTicks = 0, noseClicks = 0;
        private int climbStep = 0, closeStep = 0, roamTicks = 0, roamWait = 120, ledgeTicks = 0;
        private double wx, wy, roamTx, roamTy, jumpY = 0, jumpVy = 0, flingVx = 0, flingVy = 0, closeStartY = 0;
        private bool dragging = false, flying = false, climbing = false, closing = false, autoPaused = false;
        private bool umbrellaFall = false, trayHidden = false, usbSleeping = false, uninstalling = false, updateBusy = false, focusActive = false;
        private readonly string updatedFromVer = "";
        private string diveMode = "quit", climbMsg = "", pendingUpdateCmd = "", pendingUpdateVer = "";
        private double preQuietX = 0, preQuietY = 0;
        private bool hasPreQuiet = false;
        private int focusRem = 0;
        private DateTime lastUsbBlink = DateTime.MinValue, lastNoseClick = DateTime.MinValue, lastAutoSay = DateTime.Now;
        private DateTime focusLastTick = DateTime.Now;
        private readonly List<DateTime> coffeeTimes = new List<DateTime>();
        private readonly List<Keys> konamiBuf = new List<Keys>();
        private static readonly Keys[] KonamiSeq = { Keys.Up, Keys.Up, Keys.Down, Keys.Down, Keys.Left, Keys.Right, Keys.Left, Keys.Right, Keys.B, Keys.A };
        private Point dragOff, dragStart;
        private Rectangle? curLedge = null;
        private readonly List<Particle> particles = new List<Particle>();

        private sealed class Particle {
            public double X, Y, Vx, Vy; public int Life; public string Ch; public Color Col;
        }

        private static readonly string[] QuotesNL = {
            "Eucalyptus? Of toch een Sticky tosti?",
            "RP2350 SuperMini draait op volle toeren!",
            "Even uitrekken achter de taakbalk...",
            "Al een git commit gepusht vandaag?",
            "Tip: Ctrl+Alt+K verstopt of roept me op!"
        };
        private static readonly string[] QuotesEN = {
            "Eucalyptus? Or a Sticky toasted cheese?",
            "RP2350 SuperMini running smoothly!",
            "Zero-Install Sticky companion living on USB!",
            "Did you git commit today?",
            "Tip: Ctrl+Alt+K hides or wakes me!"
        };
        private static readonly string[] NightNL = {
            "Nachtelijke code-sessie? Vergeet geen water!",
            "Zzz... Karel programmeert mee in stilte.",
            "Nog één bug en dan lekker slapen?"
        };

        protected override CreateParams CreateParams {
            get { CreateParams cp = base.CreateParams; cp.ExStyle |= 0x00000080; return cp; }
        }

        public KarelForm() : this(42421, false, "", false) { }

        public KarelForm(int ipcPort) : this(ipcPort, false, "", false) { }

        public KarelForm(int ipcPort, bool noUpdate, string updatedFrom, bool startHidden) {
            sprites = SpriteBank.LoadEmbedded();
            save = new SaveStore();
            save.Load();
            scale = Math.Max(2, Math.Min(5, save.GetInt("karel_scale", 3)));
            roamMode = save.GetStr("roam_mode", "free");

            FormBorderStyle = FormBorderStyle.None;
            TopMost = true;
            ShowInTaskbar = false;
            KeyPreview = true;
            BackColor = Color.FromArgb(1, 2, 3);
            TransparencyKey = BackColor;
            DoubleBuffered = true;
            Text = "Karel de Koala";
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }

            UpdateFormSize();
            Rectangle wa = Screen.PrimaryScreen.WorkingArea;
            wx = wa.Right - Width - 40;
            wy = GroundY(wa);
            roamTx = wx; roamTy = wy;
            Location = new Point((int)wx, (int)wy);

            trayIcon = new NotifyIcon();
            trayIcon.Icon = Icon != null ? Icon : SystemIcons.Application;
            trayIcon.Text = "Karel de Koala (Ctrl+Alt+K)";
            try { trayIcon.Visible = true; } catch { }
            trayIcon.MouseUp += delegate(object s, MouseEventArgs e) {
                if (e.Button == MouseButtons.Left) Enqueue("EVENT:TRAY_TOGGLE");
                else if (e.Button == MouseButtons.Right) ShowKarelContextMenu(Cursor.Position);
            };

            ser = new SerialSync(delegate(string ev) { Enqueue(ev); });
            StartIpc(ipcPort);

            MouseDown += OnMouseDownHandler;
            MouseMove += OnMouseMoveHandler;
            MouseUp += OnMouseUpHandler;
            DoubleClick += delegate { DoPet(); };

            updatedFromVer = updatedFrom ?? "";
            tick.Interval = 62;
            tick.Tick += OnTick;
            usbDebounce.Interval = 700;
            usbDebounce.Tick += delegate {
                usbDebounce.Stop();
                if (usbSleeping && save.PollUsb() == "on") WakeFromUsbSleep();
            };
            if (startHidden && !save.Connected) {
                trayHidden = true;
                usbSleeping = true;
                ser.SetPaused(true);
                trayIcon.Visible = false;
                Opacity = 0;
                Shown += delegate { Hide(); Opacity = 1.0; };
            } else {
                tick.Start();
                TriggerClimb(IsEn() ? "Karel climbed onto your desktop!" : "Karel klimt je bureau op!");
            }
        }

        protected override bool ProcessCmdKey(ref Message msg, Keys keyData) {
            Keys k = keyData & Keys.KeyCode;
            if (k == Keys.Up || k == Keys.Down || k == Keys.Left || k == Keys.Right || k == Keys.B || k == Keys.A) {
                konamiBuf.Add(k);
                if (konamiBuf.Count > KonamiSeq.Length) konamiBuf.RemoveAt(0);
                if (konamiBuf.Count == KonamiSeq.Length) {
                    bool match = true;
                    for (int i = 0; i < KonamiSeq.Length; i++) if (konamiBuf[i] != KonamiSeq[i]) { match = false; break; }
                    if (match) { konamiBuf.Clear(); TriggerKonami(); return true; }
                }
            } else {
                konamiBuf.Clear();
            }
            return base.ProcessCmdKey(ref msg, keyData);
        }

        protected override void OnHandleCreated(EventArgs e) {
            base.OnHandleCreated(e);
            try { NativeWin.RegisterHotKey(Handle, 1, 0x4003, (uint)Keys.K); }
            catch { try { NativeWin.RegisterHotKey(Handle, 1, 0x0003, (uint)Keys.K); } catch { } }
        }

        protected override void WndProc(ref Message m) {
            if (m.Msg == 0x0312 && m.WParam == (IntPtr)1) { Enqueue("EVENT:TRAY_TOGGLE"); return; }
            if (m.Msg == 0x0219 && usbSleeping) {
                int wp = m.WParam.ToInt32();
                if (wp == 0x8000 || wp == 0x0007) {
                    if (save.PollUsb() == "on") WakeFromUsbSleep();
                    else { usbDebounce.Stop(); usbDebounce.Start(); }
                }
            }
            if (m.Msg == 0x0011 || (m.Msg == 0x0016 && m.WParam != IntPtr.Zero)) { if (!uninstalling) save.Save(); m.Result = (IntPtr)1; return; }
            base.WndProc(ref m);
        }

        private bool IsEn() { return save.GetStr("language", "nl") == "en"; }
        private int Px() { return 32 * scale; }
        private int Ox() { return (Width - Px()) / 2; }
        private int Oy() { return Height - Px() - 6; }
        private Rectangle CurWork() { return Screen.GetWorkingArea(new Point((int)wx + Width / 2, (int)wy + Height / 2)); }
        private int MinX(Rectangle wa) { return wa.Left - Ox() + 8; }
        private int MaxX(Rectangle wa) { return wa.Right - Ox() - Px() - 8; }
        private int MinY(Rectangle wa) { return wa.Top - Oy() + 8; }
        private int GroundY(Rectangle wa) { return wa.Bottom - (Oy() + Px()); }

        private float GetDpiScale() {
            try {
                using (Graphics g = CreateGraphics()) return Math.Max(1.0f, g.DpiX / 96.0f);
            } catch { return 1.0f; }
        }

        internal static int Sc(int px, float s) { return (int)Math.Round(px * s); }

        private void UpdateFormSize() {
            float s = GetDpiScale();
            int p = Px();
            Size = new Size(Math.Max(Sc(250, s), p + Sc(124, s)), p + Sc(78, s));
        }

        private void Enqueue(string ev) {
            lock (rxLock) rxQueue.Enqueue(ev);
            if (usbSleeping && IsHandleCreated) {
                try { BeginInvoke(new Action(delegate { if (usbSleeping) WakeFromUsbSleep(); })); } catch { }
            }
        }

        private void StartIpc(int ipcPort) {
            Thread t = new Thread(new ThreadStart(delegate {
                try {
                    ipcSrv = new TcpListener(IPAddress.Loopback, ipcPort);
                    ipcSrv.Start();
                    while (true) {
                        using (TcpClient c = ipcSrv.AcceptTcpClient())
                        using (NetworkStream ns = c.GetStream()) {
                            byte[] buf = new byte[64];
                            int n = ns.Read(buf, 0, buf.Length);
                            string msg = Encoding.ASCII.GetString(buf, 0, n);
                            if (msg.IndexOf("TOGGLE", StringComparison.Ordinal) >= 0) Enqueue("EVENT:TOGGLE_KAREL");
                            else if (msg.IndexOf("BOOP", StringComparison.Ordinal) >= 0) Enqueue("EVENT:RST_BOOP");
                        }
                    }
                } catch { }
            }));
            t.IsBackground = true;
            t.Start();
        }

        private void Say(string msg, int ticks) { if (!autoPaused) { bubble = msg; bubbleTicks = ticks; } }

        private void AwardXp(int amount) {
            int oldLvl = SaveStore.LevelFromXp(save.GetInt("xp", 0));
            int nextXp = save.GetInt("xp", 0) + amount;
            save.Data["xp"] = nextXp;
            int newLvl = SaveStore.LevelFromXp(nextXp);
            save.Data["level"] = newLvl;
            if (newLvl > oldLvl) {
                snd.Play("levelup");
                SetAction(rng.NextDouble() < 0.5 ? "BACKFLIP" : "PARTY_HORN", 42);
                SpawnParticles("*", Color.Gold, 16);
                Say(string.Format("LEVEL UP! Lv.{0}!", newLvl), 75);
            }
        }

        private void SpawnParticles(string sym, Color col, int count) {
            for (int i = 0; i < count; i++) {
                particles.Add(new Particle {
                    X = Width / 2.0 + rng.Next(-24, 25), Y = Oy() + rng.Next(4, 24),
                    Vx = (rng.NextDouble() - 0.5) * 4.5, Vy = -1.8 - rng.NextDouble() * 3.0,
                    Life = rng.Next(12, 22), Ch = sym, Col = col
                });
            }
        }

        private void SetAction(string st, int ticks) { if (!climbing) { state = st; actTicks = ticks; } }

        private void DoPet() {
            save.ClampStat("happiness", 14, 0, 100);
            save.Data["total_pets"] = save.GetInt("total_pets", 0) + 1;
            SetAction(save.GetInt("happiness", 85) >= 95 ? "LOVE" : "PET", 28);
            AwardXp(8);
            SpawnParticles("*", Color.FromArgb(255, 122, 144), 6);
            snd.Play("pet");
            ser.Send("EVENT:HEART");
            Say(IsEn() ? "Aww! Sticky love! +8 XP" : "Heerlijk! Sticky liefde! +8 XP", 45);
            save.Save(); RefreshHub();
        }

        private void DoFeed() {
            save.ClampStat("hunger", 24, 0, 100);
            save.ClampStat("happiness", 8, 0, 100);
            save.ClampStat("hygiene", -2, 0, 100);
            SetAction("EAT", 28);
            AwardXp(7);
            SpawnParticles("+", Color.FromArgb(62, 207, 142), 5);
            snd.Play("eat");
            Say(IsEn() ? "Fresh eucalyptus! Yummm!" : "Verse eucalyptus! Smullen!", 45);
            save.Save(); RefreshHub();
        }

        private void DoCoffee() {
            save.ClampStat("energy", 22, 0, 100);
            save.ClampStat("caffeine", 25, 0, 100);
            SetAction("COFFEE", 28);
            AwardXp(9);
            SpawnParticles("~", Color.FromArgb(245, 196, 81), 6);
            snd.Play("coffee");
            DateTime now = DateTime.Now;
            coffeeTimes.RemoveAll(delegate(DateTime d) { return (now - d).TotalSeconds > 120; });
            coffeeTimes.Add(now);
            if (coffeeTimes.Count >= 3) {
                hyperTicks = 95;
                ser.Send("STATE:HYPER");
                Say(IsEn() ? "CAFFEINE OVERDOSE! 200 MHz!" : "CAFEINE OVERDOSIS! 200 MHz MODE!", 75);
            } else {
                Say(IsEn() ? "Sticky espresso boost! +9 XP" : "Sticky koffie boost! +9 XP", 45);
            }
            save.Save(); RefreshHub();
        }

        private void DoWash() {
            save.ClampStat("hygiene", 35, 0, 100);
            save.ClampStat("happiness", 10, 0, 100);
            SetAction("WASH", 30);
            AwardXp(8);
            SpawnParticles("o", Color.FromArgb(79, 195, 247), 7);
            snd.Play("pet");
            Say(IsEn() ? "Sparkling clean!" : "Lekker fris gewassen!", 45);
            save.Save(); RefreshHub();
        }

        private void NapToggle() {
            if (state == "SLEEP") {
                state = "STRETCH"; actTicks = 18;
                Say(IsEn() ? "Good morning! Refreshed!" : "Goedemorgen! Uitgerust!", 40);
            } else {
                state = "SLEEP"; actTicks = 220;
                snd.Play("dive");
                Say(IsEn() ? "Zzz... Sticky powernap!" : "Zzz... Sticky powernap!", 45);
            }
        }

        private void TriggerKonami() {
            discoTicks = 115;
            save.SetEquippedItem("shades");
            SetAction("DANCE", 65);
            SpawnParticles("*", Color.Gold, 16);
            ser.Send("STATE:PARTY");
            snd.Play("levelup");
            Say(IsEn() ? "DISCO BORREL MODE ON!" : "DISCO BORREL MODE AAN!", 80);
            save.Save(); RefreshHub();
        }

        private void DoBoop() {
            AwardXp(10);
            snd.Play("boop");
            SpawnParticles("*", Color.Gold, 10);
            TriggerClimb("SuperMini Boop! +10 XP!");
            save.Save(); RefreshHub();
        }

        private void TriggerClimb(string msg) {
            Rectangle wa = CurWork();
            flying = false; umbrellaFall = false; jumpY = 0;
            wy = GroundY(wa);
            wx = Math.Max(MinX(wa), Math.Min(MaxX(wa), wx));
            climbing = true; climbStep = 0; climbMsg = msg;
            roamTx = wx; roamTy = wy; roamWait = 95;
            snd.Play("climb");
            Say(IsEn() ? "Climbing up..." : "Even over de taakbalk klimmen...", 26);
        }

        private void WakeFromTray() {
            if (trayHidden) { trayHidden = false; Opacity = 1.0; Show(); TopMost = true; }
            TriggerClimb(IsEn() ? "I'm back! (Ctrl+Alt+K)" : "Daar ben ik weer! (Ctrl+Alt+K)");
        }

        private void TriggerDive(string mode, string customMsg = null) {
            if (closing) return;
            diveMode = mode; closing = true; closeStep = 0; climbing = false; flying = false; dragging = false; umbrellaFall = false;
            jumpY = 0; closeStartY = wy; actTicks = 0;
            string diveMsg = !string.IsNullOrEmpty(customMsg) ? customMsg
                : (mode == "tray"
                    ? (IsEn() ? "Napping in tray! (Ctrl+Alt+K)" : "Even dutten in systeemvak! (Ctrl+Alt+K)")
                    : (IsEn() ? "See ya! Diving back!" : "Tot ziens! Ik duik weg!"));
            Say(diveMsg, 40);
            SpawnParticles("*", Color.FromArgb(255, 122, 144), 4);
            snd.Play("dive");
        }

        private void EnterUsbSleep() {
            closing = false;
            trayHidden = true;
            usbSleeping = true;
            tick.Stop();
            usbDebounce.Stop();
            ser.SetPaused(true);
            try { trayIcon.Visible = false; } catch { }
            Hide();
        }

        private void WakeFromUsbSleep() {
            usbDebounce.Stop();
            usbSleeping = false;
            trayHidden = false;
            ser.SetPaused(false);
            try { trayIcon.Visible = true; } catch { }
            save.Load();
            scale = Math.Max(2, Math.Min(5, save.GetInt("karel_scale", 3)));
            UpdateFormSize();
            RefreshHub();
            Opacity = 1.0;
            Show();
            TopMost = true;
            tick.Start();
            TriggerClimb(IsEn() ? "KAREL USB connected!" : "KAREL USB verbonden!");
        }

        private void CheckForUpdatesManual() {
            if (updateBusy) return;
            updateBusy = true;
            Say(IsEn() ? "Checking GitHub for updates..." : "Controleren op updates...", 55);
            AutoUpdater.CheckNowAsync(save, updatedFromVer,
                delegate(string ver, string cmd) {
                    pendingUpdateVer = ver;
                    pendingUpdateCmd = cmd;
                    Enqueue("EVENT:APPLY_UPDATE");
                },
                delegate(string status) {
                    try {
                        BeginInvoke(new Action(delegate {
                            if (status.StartsWith("downloading:")) {
                                Say(string.Format(IsEn() ? "Downloading v{0}..." : "Downloaden v{0}...", status.Substring(12)), 90);
                                return;
                            }
                            updateBusy = false;
                            if (status == "uptodate") Say(string.Format(IsEn() ? "Up to date (v{0})!" : "Al de nieuwste versie (v{0})!", AutoUpdater.Version), 65);
                            else if (status == "offline") Say(IsEn() ? "Cannot reach GitHub." : "Kan GitHub niet bereiken.", 60);
                            else Say(IsEn() ? "Update check failed." : "Update-check mislukt.", 60);
                        }));
                    } catch { updateBusy = false; }
                });
        }

        private void DoUninstallFromPc() {
            bool en = IsEn();
            DialogResult r = MessageBox.Show(
                en ? "Remove all Karel files from this PC (auto-start, local copy & local backup)?\nYour USB stick will NOT be touched."
                   : "Alle Karel-bestanden van deze laptop verwijderen (auto-start, lokale kopie & lokale back-up)?\nJe USB-stick blijft gewoon bewaard.",
                en ? "Uninstall Karel from this PC" : "Karel verwijderen van deze laptop",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question
            );
            if (r != DialogResult.Yes) return;
            uninstalling = true;
            if (hubForm != null && !hubForm.IsDisposed) { try { hubForm.Close(); } catch { } }
            StartupHelper.UninstallFromPc(save.FallbackPath);
            FinalizeQuit(false);
        }

        private void HandoffToLocalWatcher() {
            FinalizeQuit(true);
        }

        private void FinalizeQuit(bool spawnLocalTray = false) {
            tick.Stop();
            usbDebounce.Stop();
            ser.Send("STATE:BYE");
            if (!uninstalling) save.Save();
            ser.Stop();
            try { NativeWin.UnregisterHotKey(Handle, 1); } catch { }
            if (ipcSrv != null) { try { ipcSrv.Stop(); } catch { } ipcSrv = null; }
            trayIcon.Visible = false;
            trayIcon.Dispose();
            if (!uninstalling && !StartupHelper.IsEnabled() && StartupHelper.IsRunningInstalled()) {
                StartupHelper.ScheduleRemoveInstalledDir();
            }
            if (spawnLocalTray) {
                string instExe = StartupHelper.InstalledExePath();
                if (File.Exists(instExe) && !string.Equals(Path.GetFullPath(Application.ExecutablePath), Path.GetFullPath(instExe), StringComparison.OrdinalIgnoreCase)) {
                    try { Process.Start(new ProcessStartInfo(instExe, "--tray") { UseShellExecute = false }); } catch { }
                }
            }
            Application.Exit();
        }

        private void ApplyAutoQuiet(string reason, Rectangle wa) {
            bool busy = !string.IsNullOrEmpty(reason);
            if (busy && !autoPaused) {
                preQuietX = wx; preQuietY = wy; hasPreQuiet = true;
                autoPaused = true; snd.AutoQuiet = true;
                wx = MaxX(wa); wy = MinY(wa);
                bubble = ""; bubbleTicks = 0; state = "IDLE";
            } else if (!busy && autoPaused) {
                autoPaused = false; snd.AutoQuiet = false;
                if (hasPreQuiet) {
                    wx = Math.Max(MinX(wa), Math.Min(MaxX(wa), preQuietX));
                    wy = Math.Max(MinY(wa), Math.Min(GroundY(wa), preQuietY));
                    hasPreQuiet = false;
                }
            }
        }

        private void DrainEvents() {
            while (true) {
                string ev;
                lock (rxLock) { if (rxQueue.Count == 0) break; ev = rxQueue.Dequeue(); }
                if (ev == "EVENT:PET") DoPet();
                else if (ev == "EVENT:FEED") DoFeed();
                else if (ev == "EVENT:COFFEE") DoCoffee();
                else if (ev == "EVENT:WASH") DoWash();
                else if (ev == "EVENT:MINIGAME") { SetAction("BACKFLIP", 30); snd.Play("boop"); }
                else if (ev == "EVENT:DISCO") TriggerKonami();
                else if (ev == "EVENT:RST_BOOP" || ev == "EVENT:GIFT") { if (trayHidden) WakeFromTray(); DoBoop(); }
                else if (ev == "EVENT:TOGGLE_KAREL") { if (trayHidden) WakeFromTray(); else TriggerDive("quit"); }
                else if (ev == "EVENT:TRAY_TOGGLE") { if (trayHidden) WakeFromTray(); else TriggerDive("tray"); }
                else if (ev == "EVENT:QUIT_NOW") { if (trayHidden) FinalizeQuit(); else TriggerDive("quit"); }
                else if (ev == "EVENT:SHUTDOWN_SAVE") save.Save();
                else if (ev == "EVENT:APPLY_UPDATE" && !string.IsNullOrEmpty(pendingUpdateCmd)) {
                    Say(string.Format(IsEn() ? "Updated to v{0}! Restarting..." : "Update v{0} klaar! Herstarten...", pendingUpdateVer), 40);
                    save.Save();
                    try {
                        Process.Start(new ProcessStartInfo(pendingUpdateCmd) { WindowStyle = ProcessWindowStyle.Hidden, CreateNoWindow = true, UseShellExecute = true });
                    } catch { }
                    FinalizeQuit();
                    return;
                }
            }
        }

        private void SyncHardware() {
            int hr = DateTime.Now.Hour;
            if (autoPaused || trayHidden) ser.Send("STATE:QUIET");
            else if (focusActive) ser.Send("STATE:STUDY");
            else if (discoTicks > 0 || state == "DANCE") ser.Send("STATE:PARTY");
            else if (hyperTicks > 0) ser.Send("STATE:HYPER");
            else if (state == "SLEEP" || (hr >= 23 && actTicks == 0)) ser.Send("STATE:SLEEP");
            else if (save.GetInt("hunger", 100) < 25) ser.Send("STATE:HUNGRY");
            else ser.Send("STATE:HAPPY");
        }

        private void OnTick(object sender, EventArgs e) {
            frameIdx++;
            Rectangle wa = CurWork();
            if (frameIdx % 16 == 0) {
                if (save.GetBool("auto_quiet_fullscreen", true)) {
                    IntPtr hHub = (hubForm != null && !hubForm.IsDisposed) ? hubForm.Handle : IntPtr.Zero;
                    ApplyAutoQuiet(NativeWin.DetectFullscreenOrMeeting(Handle, hHub), wa);
                } else if (autoPaused) ApplyAutoQuiet("", wa);
                string usb = save.PollUsb();
                if (usb == "off") {
                    if (hubForm != null && !hubForm.IsDisposed) { try { hubForm.Close(); } catch { } }
                    bool autoOn = StartupHelper.IsEnabled();
                    bool onLocal = StartupHelper.IsRunningInstalled();
                    if (trayHidden) {
                        if (autoOn) {
                            if (onLocal) EnterUsbSleep();
                            else { HandoffToLocalWatcher(); return; }
                        } else {
                            FinalizeQuit(false); return;
                        }
                    } else if (autoOn) {
                        TriggerDive(onLocal ? "usb_sleep" : "handoff", IsEn() ? "USB unplugged! See you next time!" : "USB los! Tot de volgende keer!");
                    } else {
                        TriggerDive("quit", IsEn() ? "USB unplugged! Bye!" : "USB los! Doei!");
                    }
                } else if (usb == "on") {
                    save.Load();
                    scale = Math.Max(2, Math.Min(5, save.GetInt("karel_scale", 3)));
                    UpdateFormSize();
                    RefreshHub();
                    if (trayHidden) WakeFromTray();
                    else TriggerClimb(IsEn() ? "KAREL USB reconnected!" : "KAREL USB herverbonden!");
                }
            }
            if (focusActive && (DateTime.Now - focusLastTick).TotalSeconds >= 1.0) {
                focusLastTick = DateTime.Now;
                focusRem = Math.Max(0, focusRem - 1);
                if (focusRem == 0) {
                    focusActive = false;
                    AwardXp(45);
                    SetAction("CELEBRATE", 40);
                    SpawnParticles("*", Color.Gold, 14);
                    snd.Play("levelup");
                    Say(IsEn() ? "Focus complete! +45 XP!" : "Focus klaar! +45 XP!", 70);
                    save.Save(); RefreshHub();
                }
            }
            DrainEvents();

            int minx = MinX(wa), maxx = MaxX(wa), miny = MinY(wa), gy = GroundY(wa);

            if (closing) {
                closeStep++;
                if (closeStep <= 9) wy = closeStartY + (gy - closeStartY) * (closeStep / 9.0);
                else if (closeStep <= 13) { wy = gy; jumpY = -14.0 * Math.Sin((closeStep - 9) * Math.PI / 4.0); }
                else { wy = gy; jumpY = 0; }
                if (closeStep >= 27) {
                    if (diveMode == "usb_sleep") { save.Save(); EnterUsbSleep(); return; }
                    else if (diveMode == "tray") { closing = false; trayHidden = true; save.Save(); Hide(); }
                    else if (diveMode == "handoff") { HandoffToLocalWatcher(); return; }
                    else { FinalizeQuit(); return; }
                }
            } else if (climbing) {
                climbStep++;
                if (climbStep >= 18) {
                    climbing = false; jumpVy = -9.0;
                    SetAction(rng.NextDouble() < 0.35 ? "BACKFLIP" : "JUMP", 16);
                    ser.Send("EVENT:HEART"); snd.Play("pet");
                    SpawnParticles("*", Color.FromArgb(255, 122, 144), 6);
                    Say(climbMsg, 65);
                }
            } else if (!trayHidden) {
                StepRoam(wa, minx, maxx, miny, gy);
            }

            if (actTicks > 0) {
                actTicks--;
                if (actTicks == 0) {
                    if (state == "SLEEP") save.ClampStat("energy", 30, 0, 100);
                    state = "IDLE";
                }
            }
            if (discoTicks > 0) discoTicks--;
            if (hyperTicks > 0) hyperTicks--;
            if (bubbleTicks > 0) bubbleTicks--;
            for (int i = particles.Count - 1; i >= 0; i--) {
                Particle p = particles[i];
                p.X += p.Vx; p.Y += p.Vy; p.Vy += 0.25; p.Life--;
                if (p.Life <= 0) particles.RemoveAt(i);
            }
            if (frameIdx % 65 == 0) {
                if (state == "SLEEP") { save.ClampStat("energy", 2, 0, 100); save.MarkDirty(); }
                else if (rng.NextDouble() < 0.28) { save.ClampStat("hunger", -1, 0, 100); save.MarkDirty(); }
                if (frameIdx % 130 == 0 && rng.NextDouble() < 0.32) {
                    save.ClampStat("energy", -1, 0, 100); save.ClampStat("hygiene", -1, 0, 100); save.MarkDirty();
                }
            }
            if (frameIdx % 720 == 0) save.FlushIfDirty();
            SyncHardware();

            if (!trayHidden) {
                Location = new Point((int)Math.Round(wx), (int)Math.Round(wy + jumpY));
                Invalidate();
            }
        }

        private void StepRoam(Rectangle wa, int minx, int maxx, int miny, int gy) {
            if (dragging) return;
            if (autoPaused) { state = "IDLE"; return; }
            if (focusActive && actTicks == 0) { state = "STUDY"; return; }
            if (flying) {
                state = "JETPACK";
                wx += flingVx; wy += flingVy; flingVy += 1.45; flingVx *= 0.985;
                if (wx <= minx) { wx = minx; flingVx = Math.Abs(flingVx) * 0.65; }
                else if (wx >= maxx) { wx = maxx; flingVx = -Math.Abs(flingVx) * 0.65; }
                if (wy <= miny) { wy = miny; flingVy = Math.Abs(flingVy) * 0.65; }
                if (wy >= gy) {
                    wy = gy;
                    if (Math.Abs(flingVy) > 6.5) flingVy = -Math.Abs(flingVy) * 0.55;
                    else { flying = false; flingVx = 0; flingVy = 0; SetAction("DIZZY", 20); }
                }
                return;
            }
            if (umbrellaFall) {
                state = "UMBRELLA";
                wy = Math.Min((double)gy, wy + 2.6);
                wx = Math.Max((double)minx, Math.Min((double)maxx, wx + Math.Sin(frameIdx * 0.22) * 1.15));
                if (wy >= gy - 0.5) {
                    wy = gy; umbrellaFall = false; roamWait = 45; jumpVy = -4.5;
                    SpawnParticles("*", Color.Gold, 4);
                }
                return;
            }
            if (jumpY < 0 || jumpVy < 0) {
                jumpY += jumpVy; jumpVy += 1.35;
                if (jumpY >= 0) { jumpY = 0; jumpVy = 0; }
            }
            if (hyperTicks > 0) wx = Math.Max(minx, Math.Min(maxx, wx + (rng.Next(2) == 0 ? -7 : 7)));
            if (actTicks > 0 || state == "SLEEP") return;
            if (roamMode == "park") { state = "IDLE"; return; }
            if (roamMode == "cursor") {
                Point cp = Cursor.Position;
                double px = Math.Max(minx, Math.Min(maxx, cp.X - Width / 2));
                double py = Math.Max(miny, Math.Min(gy, cp.Y - (Oy() + Px() / 2)));
                double dx = px - wx, dy = py - wy, dist = Math.Sqrt(dx * dx + dy * dy);
                if (dist > 110) {
                    wx += (dx / dist) * 4.4; wy += (dy / dist) * 4.4;
                    state = dx < 0 ? "RUN_LEFT" : "RUN_RIGHT";
                } else state = "IDLE";
                return;
            }
            if (roamMode == "window") {
                ledgeTicks++;
                if (ledgeTicks % 12 == 1 || !curLedge.HasValue)
                    curLedge = NativeWin.GetForegroundLedge(Handle, hubForm != null && !hubForm.IsDisposed ? hubForm.Handle : IntPtr.Zero, Px(), wa);
                if (curLedge.HasValue) {
                    Rectangle lg = curLedge.Value;
                    double tx0 = Math.Max(minx, lg.Left - Ox());
                    double tx1 = Math.Max(tx0, Math.Min(maxx, lg.Right - Ox() - Px()));
                    roamTy = Math.Max(miny, Math.Min(gy, lg.Top - (Oy() + Px())));
                    if (roamTx < tx0 || roamTx > tx1) roamTx = tx0 + rng.NextDouble() * (tx1 - tx0);
                } else roamTy = gy;
                if ((!curLedge.HasValue && wy < gy - 18) || roamTy > wy + 28) {
                    umbrellaFall = true; roamWait = 0; roamTicks = 0; actTicks = 0;
                    Say(IsEn() ? "Window gone! Sticky umbrella open!" : "Oeps, venster weg! Paraplu open!", 42);
                    return;
                }
            }
            if (roamWait > 0) {
                roamWait--;
                if (roamWait % 60 == 30 && rng.NextDouble() < 0.6) {
                    string[] acts = { "BLINK_SMILE", "EARS_WIGGLE", "PEEK", "SIT", "LAPTOP_CODE", "UMBRELLA", "BOW", "WAVE" };
                    SetAction(acts[rng.Next(acts.Length)], 24);
                } else state = "IDLE";
                return;
            }
            double ddx = roamTx - wx, ddy = roamTy - wy, dd = Math.Sqrt(ddx * ddx + ddy * ddy);
            roamTicks++;
            if (dd < 10 || roamTicks > 155) {
                roamTicks = 0; roamWait = rng.Next(130, 280);
                roamTx = minx + rng.NextDouble() * Math.Max(1, maxx - minx);
                roamTy = (roamMode == "window" && curLedge.HasValue)
                    ? Math.Max(miny, Math.Min(gy, curLedge.Value.Top - (Oy() + Px())))
                    : gy - (rng.NextDouble() < 0.35 ? rng.Next(0, Math.Max(10, (gy - miny) / 2)) : 0);
                if (rng.NextDouble() < 0.14 && (DateTime.Now - lastAutoSay).TotalSeconds > 35 && bubbleTicks == 0) {
                    lastAutoSay = DateTime.Now;
                    bool night = DateTime.Now.Hour >= 0 && DateTime.Now.Hour < 5;
                    string[] pool = IsEn() ? QuotesEN : (night ? NightNL : QuotesNL);
                    Say(pool[rng.Next(pool.Length)], 55);
                }
                return;
            }
            wx += (ddx / dd) * 2.2; wy += (ddy / dd) * 2.2;
            state = jumpY < -1 ? "JUMP" : (ddx < 0 ? "WALK_LEFT" : "WALK_RIGHT");
        }

        private void OnMouseDownHandler(object sender, MouseEventArgs e) {
            if (e.Button == MouseButtons.Right) { ShowKarelContextMenu(PointToScreen(e.Location)); return; }
            if (e.Button != MouseButtons.Left || closing) return;
            Activate();
            dragging = true; flying = false; umbrellaFall = false; climbing = false; jumpY = 0;
            dragOff = e.Location; dragStart = Cursor.Position; lastUsbBlink = DateTime.Now;
        }

        private void OnMouseMoveHandler(object sender, MouseEventArgs e) {
            if (!dragging) return;
            state = "JETPACK";
            Point cur = Cursor.Position;
            Rectangle vb = SystemInformation.VirtualScreen;
            wx = Math.Max(vb.Left - Ox() + 4, Math.Min(vb.Right - Ox() - Px() - 4, cur.X - dragOff.X));
            wy = Math.Max(vb.Top - Oy() + 4, Math.Min(vb.Bottom - (Oy() + Px()), cur.Y - dragOff.Y));
            Location = new Point((int)Math.Round(wx), (int)Math.Round(wy));
        }

        private void OnMouseUpHandler(object sender, MouseEventArgs e) {
            if (!dragging) return;
            dragging = false;
            Point cur = Cursor.Position;
            Rectangle wa = CurWork();
            wx = Math.Max(MinX(wa), Math.Min(MaxX(wa), wx));
            wy = Math.Max(MinY(wa), Math.Min(GroundY(wa), wy));
            double moved = Math.Sqrt(Math.Pow(cur.X - dragStart.X, 2) + Math.Pow(cur.Y - dragStart.Y, 2));
            if (moved < 6) {
                int sx = (e.X - Ox()) / scale, sy = (e.Y - Oy()) / scale;
                if (sx >= 13 && sx <= 18 && sy >= 12 && sy <= 16) {
                    if ((DateTime.Now - lastNoseClick).TotalSeconds > 4.5) noseClicks = 0;
                    lastNoseClick = DateTime.Now; noseClicks++;
                    if (noseClicks >= 7) {
                        noseClicks = 0; snd.Play("sneeze"); SetAction("SNEEZE", 24);
                        SpawnParticles("*", Color.WhiteSmoke, 10);
                        Say(IsEn() ? "Achoo! BBG dust!" : "Hatsjoe! BBG stof!", 55);
                    }
                } else if (actTicks == 0 && state != "SLEEP") {
                    string[] pool = IsEn() ? QuotesEN : QuotesNL;
                    Say(pool[rng.Next(pool.Length)], 45); snd.Play("chirp");
                }
                return;
            }
            double dt = Math.Max(0.04, (DateTime.Now - lastUsbBlink).TotalSeconds);
            double vx = (cur.X - dragStart.X) / (dt * 20.0), vy = (cur.Y - dragStart.Y) / (dt * 20.0);
            if (Math.Sqrt(vx * vx + vy * vy) > 10.0) {
                flying = true;
                flingVx = Math.Max(-36.0, Math.Min(36.0, vx));
                flingVy = Math.Max(-32.0, Math.Min(26.0, vy));
            }
        }

        protected override void OnPaint(PaintEventArgs e) {
            Graphics g = e.Graphics;
            g.InterpolationMode = InterpolationMode.NearestNeighbor;
            g.PixelOffsetMode = PixelOffsetMode.Half;

            string renderSt = state;
            int clipRows = 32;
            if (closing) {
                if (closeStep <= 9) renderSt = "DIVE_WAVE";
                else if (closeStep <= 13) renderSt = "JUMP";
                else {
                    renderSt = "DIVE_DOWN";
                    clipRows = Math.Max(0, (int)Math.Round(32.0 * (1.0 - (closeStep - 13) / 13.0)));
                }
            } else if (climbing) {
                renderSt = "CLIMB";
                clipRows = Math.Max(2, (int)Math.Round(32.0 * Math.Min(1.0, climbStep / 17.0)));
            } else if (renderSt == "IDLE") {
                if (hyperTicks > 0) renderSt = "HYPER";
                else if (DateTime.Now.Hour >= 23 && actTicks == 0) renderSt = "SLEEP";
                else if (save.GetInt("hunger", 100) < 25) renderSt = "HUNGRY";
            }

            int p = Px(), ox = Ox(), oy = Oy();
            if (!climbing && !closing) {
                int ins = Math.Max(8, p / 5);
                using (SolidBrush sh = new SolidBrush(Color.FromArgb(24, 28, 38)))
                    g.FillEllipse(sh, ox + ins, oy + p - 4, Math.Max(12, p - 2 * ins), 7);
            }

            Bitmap bmp = sprites.GetFrame(renderSt, frameIdx, save.GetStr("skin", "classic"), save.GetEquippedItem());
            if (clipRows > 0) {
                int dy = oy + (32 - clipRows) * scale;
                g.DrawImage(bmp, new Rectangle(ox, dy, p, clipRows * scale), new Rectangle(0, 0, 32, clipRows), GraphicsUnit.Pixel);
            }

            using (Font pf = new Font("Consolas", 10f, FontStyle.Bold)) {
                for (int i = 0; i < particles.Count; i++) {
                    Particle pt = particles[i];
                    using (SolidBrush br = new SolidBrush(pt.Col))
                        g.DrawString(pt.Ch, pf, br, (float)pt.X, (float)pt.Y);
                }
            }

            if (bubbleTicks > 0 && !string.IsNullOrEmpty(bubble)) {
                float sc = Math.Max(1.0f, g.DpiX / 96.0f);
                using (Font bf = new Font("Segoe UI", 8.5f, FontStyle.Bold)) {
                    SizeF sz = g.MeasureString(bubble, bf, Width - Sc(22, sc));
                    int bw = Math.Min(Width - Sc(10, sc), Math.Max(Sc(74, sc), (int)Math.Ceiling(sz.Width) + Sc(20, sc)));
                    int bh = (int)Math.Ceiling(sz.Height) + Sc(10, sc);
                    int bx = Math.Max(Sc(4, sc), (Width - bw) / 2);
                    int by = Math.Max(Sc(4, sc), oy - bh - Sc(9, sc));
                    int tx = Width / 2;
                    int tailH = Sc(6, sc);
                    using (SolidBrush bg = new SolidBrush(Color.FromArgb(248, 250, 255)))
                    using (SolidBrush acc = new SolidBrush(Color.FromArgb(196, 30, 37)))
                    using (Pen bd = new Pen(Color.FromArgb(196, 30, 37), 1.6f))
                    using (SolidBrush fg = new SolidBrush(Color.FromArgb(20, 24, 34))) {
                        g.FillRectangle(bg, bx, by, bw, bh);
                        g.FillRectangle(acc, bx, by, Math.Max(3, Sc(4, sc)), bh);
                        g.DrawRectangle(bd, bx, by, bw, bh);
                        Point[] tri = { new Point(tx - Sc(5, sc), by + bh), new Point(tx + Sc(5, sc), by + bh), new Point(tx, by + bh + tailH) };
                        g.FillPolygon(bg, tri);
                        g.DrawLine(bd, tri[0], tri[2]); g.DrawLine(bd, tri[2], tri[1]);
                        g.DrawString(bubble, bf, fg, new RectangleF(bx + Sc(8, sc), by + Sc(5, sc), bw - Sc(12, sc), bh - Sc(8, sc)));
                    }
                }
            }
        }

        private void ShowKarelContextMenu(Point pt) {
            ContextMenuStrip m = new ContextMenuStrip();
            bool en = IsEn();
            m.Items.Add(en ? "Open Sticky Hub" : "Open Sticky Hub", null, delegate { OpenHub(); });
            m.Items.Add(new ToolStripSeparator());
            m.Items.Add(en ? "Feed Eucalyptus" : "Voer Eucalyptus", null, delegate { DoFeed(); });
            m.Items.Add(en ? "Sticky Coffee" : "Sticky Koffie", null, delegate { DoCoffee(); });
            m.Items.Add(en ? "Pet Karel" : "Aai Karel", null, delegate { DoPet(); });
            m.Items.Add(en ? "Wash Karel" : "Was Karel", null, delegate { DoWash(); });
            m.Items.Add(en ? "Powernap ON/OFF" : "Powernap AAN/UIT", null, delegate { NapToggle(); });
            m.Items.Add(focusActive ? "Stop Focus" : (en ? "Focus Mode (25m)" : "Focus Modus (25m)"), null, delegate { ToggleFocus(); });
            m.Items.Add(new ToolStripSeparator());

            ToolStripMenuItem tm = new ToolStripMenuItem(en ? "Tricks & Animations" : "Trucjes & Animaties");
            string[,] tricks = {
                { "Backflip!", "BACKFLIP", "Wooo! Koala Backflip!!" },
                { "360° Spin", "SPIN", "Swoosh!" },
                { "Jetpack", "JETPACK", "Naar de BBG-maan!" },
                { "Peek", "PEEK", "Psst... zie je me?" },
                { "Laptop Coding", "LAPTOP_CODE", "git commit -m 'fix'" },
                { "Debug Magnifier", "MAGNIFY", "Zoekende naar bugs..." },
                { "Paper Plane", "PAPER_PLANE", "Zoooef!" },
                { "Sticky Umbrella", "UMBRELLA", "Typisch Nederlands weer!" },
                { "Ear Wiggle", "EARS_WIGGLE", "*Wiebel wiebel*" },
                { "Hug Plush", "HUG_PLUSH", "Sticky liefde!" },
                { "Eucalyptus Hug", "EUCALYPTUS_HUG", "Favoriete tak!" },
                { "Party Horn", "PARTY_HORN", "VrijMiBo tijd!" },
                { "Polite Bow", "BOW", "Dankjewel!" },
                { "Wave Hello", "WAVE", "Hoi!!" },
                { "Guitar Solo", "GUITAR", "8-bit riff!" },
                { "Drums", "DRUM", "Ba-dum-tss!" },
                { "Flex Muscles", "FLEX", "RP2350 spierkracht!" },
                { "Dance", "DANCE", "De Vagant boogie!" }
            };
            for (int i = 0; i < tricks.GetLength(0); i++) {
                string s0 = tricks[i, 1], m0 = tricks[i, 2];
                tm.DropDownItems.Add(tricks[i, 0], null, delegate { SetAction(s0, 42); Say(m0, 42); });
            }
            m.Items.Add(tm);

            ToolStripMenuItem rm = new ToolStripMenuItem(en ? "Roam Mode" : "Loopgedrag");
            rm.DropDownItems.Add(en ? "Free Roam" : "Heel Scherm", null, delegate { SetRoam("free"); });
            rm.DropDownItems.Add(en ? "Active Window" : "Op Actief Venster", null, delegate { SetRoam("window"); });
            rm.DropDownItems.Add(en ? "Follow Mouse" : "Volg Muis", null, delegate { SetRoam("cursor"); });
            rm.DropDownItems.Add(en ? "Stay Put" : "Blijf Zitten", null, delegate { SetRoam("park"); });
            m.Items.Add(rm);

            ToolStripMenuItem sm = new ToolStripMenuItem(en ? "Size" : "Grootte");
            for (int sc = 2; sc <= 5; sc++) {
                int sVal = sc;
                sm.DropDownItems.Add(string.Format("{0}x ({1}px)", sVal, sVal * 32), null, delegate { SetScale(sVal); });
            }
            m.Items.Add(sm);

            m.Items.Add(en ? "Sound On/Off" : "Geluid Aan/Uit", null, delegate { snd.Muted = !snd.Muted; RefreshHub(); });
            m.Items.Add(en ? "Auto-Quiet Fullscreen" : "Auto-Stil Fullscreen", null, delegate {
                save.Data["auto_quiet_fullscreen"] = !save.GetBool("auto_quiet_fullscreen", true);
                save.Save(); RefreshHub();
            });
            m.Items.Add(en ? "Language: NL / EN" : "Taal: NL / EN", null, delegate {
                save.Data["language"] = en ? "nl" : "en"; save.Save(); RefreshHub();
            });
            ToolStripMenuItem bgIt = new ToolStripMenuItem(en ? "Auto-open on USB plug-in" : "Automatisch openen bij USB");
            bgIt.Checked = StartupHelper.IsEnabled();
            bgIt.Click += delegate {
                bool on = StartupHelper.Toggle();
                Say(on ? (en ? "Auto-open on USB ON!" : "Automatisch openen bij USB AAN!") : (en ? "Auto-open on USB OFF." : "Automatisch openen bij USB UIT."), 55);
                RefreshHub();
            };
            m.Items.Add(bgIt);
            m.Items.Add(en ? "Check for updates" : "Check op updates", null, delegate { CheckForUpdatesManual(); });
            m.Items.Add(en ? "Uninstall from this PC..." : "Verwijder van deze laptop...", null, delegate { DoUninstallFromPc(); });
            m.Items.Add(new ToolStripSeparator());
            m.Items.Add(en ? "Hide Behind Taskbar (Ctrl+Alt+K)" : "Verberg achter Taakbalk (Ctrl+Alt+K)", null, delegate { Enqueue("EVENT:TRAY_TOGGLE"); });
            m.Items.Add(en ? "Dive & Quit" : "Duik achter Taakbalk & Sluit", null, delegate { Enqueue("EVENT:QUIT_NOW"); });
            m.Show(pt);
        }

        private void SetRoam(string mode) {
            roamMode = mode; save.Data["roam_mode"] = mode; save.Save();
            umbrellaFall = false; Say(mode, 30);
        }

        private void SetScale(int sc) {
            scale = Math.Max(2, Math.Min(5, sc));
            save.Data["karel_scale"] = scale;
            UpdateFormSize();
            Rectangle wa = CurWork();
            wy = Math.Min(GroundY(wa), wy);
            save.Save();
        }

        private void ToggleFocus() {
            focusActive = !focusActive;
            if (focusActive) { focusRem = 25 * 60; focusLastTick = DateTime.Now; Say("Focus: 25m!", 45); }
            else Say(IsEn() ? "Focus stopped." : "Focus gestopt.", 35);
            RefreshHub();
        }

        private void RefreshHub() {
            if (hubForm == null || hubForm.IsDisposed) return;
            bool en = IsEn();
            int xp = save.GetInt("xp", 0);
            int lvl = SaveStore.LevelFromXp(xp);
            int prevXp = SaveStore.XpForNextLevel(lvl - 1);
            int nextXp = SaveStore.XpForNextLevel(lvl);
            double pct = Math.Max(0.0, Math.Min(1.0, (double)(xp - prevXp) / Math.Max(1, nextXp - prevXp)));

            Control statsCard = hubForm.Controls["statsCard"];
            if (statsCard != null) {
                Control topL = statsCard.Controls["statsTopLbl"];
                if (topL != null) topL.Text = string.Format("Lv.{0}   ·   {1} / {2} XP", lvl, xp, nextXp);
                Control xT = statsCard.Controls["xpTrack"];
                if (xT != null && xT.Controls["xpFill"] != null)
                    xT.Controls["xpFill"].Width = Math.Max(xp > 0 ? 4 : 0, (int)Math.Round(xT.Width * pct));
                Control botL = statsCard.Controls["statsBotLbl"];
                if (botL != null) botL.Text = HubVitalsLine();
            }

            string[] actKeys = { en ? "Feed" : "Voer", en ? "Coffee" : "Koffie", en ? "Pet" : "Aai", en ? "Wash" : "Was", "Powernap", focusActive ? "Stop Focus" : "Focus 25m" };
            for (int i = 0; i < 6; i++) {
                Control ab = hubForm.Controls["actBtn" + i];
                if (ab != null) ab.Text = actKeys[i];
            }

            Control styleCard = hubForm.Controls["styleCard"];
            if (styleCard != null) {
                Control sl = styleCard.Controls["styleLbl"];
                if (sl != null) sl.Text = en ? "Style:" : "Stijl:";
                Control sb = styleCard.Controls["skinBtn"];
                if (sb != null) sb.Text = string.Format("{0}: {1}  v", en ? "Coat" : "Vacht", save.GetStr("skin", "classic"));
                Control ob = styleCard.Controls["outBtn"];
                if (ob != null) {
                    string eq = save.GetEquippedItem();
                    ob.Text = string.Format("Outfit: {0}  v", string.IsNullOrEmpty(eq) ? (en ? "none" : "geen") : eq);
                }
            }

            Control aqBtn = hubForm.Controls["aqBtn"];
            if (aqBtn != null) aqBtn.Text = AutoQuietLabel();
            Control sndBtn = hubForm.Controls["sndBtn"];
            if (sndBtn != null) sndBtn.Text = SoundLabel();
            Control usb = hubForm.Controls["usbLbl"];
            Control hidBtn = hubForm.Controls["hidBtn"];
            Control updBtn = hubForm.Controls["updBtn"];
            Control uninstBtn = hubForm.Controls["uninstBtn"];
            if (hidBtn != null && usb != null) {
                hidBtn.Visible = true;
                hidBtn.Text = HidFlagLabel();
                if (updBtn != null) updBtn.Text = en ? "Check for updates" : "Check op updates";
                if (uninstBtn != null) uninstBtn.Text = en ? "Uninstall from PC" : "Verwijder van laptop";
                usb.Text = HubUsbLine();
                int anchorBottom = (updBtn != null) ? updBtn.Bottom : hidBtn.Bottom;
                usb.Top = anchorBottom + Sc(8, GetDpiScale());
                int targetH = usb.Bottom + Sc(14, GetDpiScale());
                if (hubForm.ClientSize.Height != targetH)
                    hubForm.ClientSize = new Size(hubForm.ClientSize.Width, targetH);
            }
        }

        private string AutoQuietLabel() {
            bool aq = save.GetBool("auto_quiet_fullscreen", true);
            return (IsEn() ? "Quiet: " : "Auto-Stil: ") + (aq ? (IsEn() ? "ON" : "AAN") : (IsEn() ? "OFF" : "UIT"));
        }

        private string SoundLabel() {
            return (IsEn() ? "Sound: " : "Geluid: ") + (snd.Muted ? (IsEn() ? "OFF" : "UIT") : (IsEn() ? "ON" : "AAN"));
        }

        private string HidFlagLabel() {
            bool on = StartupHelper.IsEnabled();
            return on
                ? (IsEn() ? "Auto-open on USB plug-in: ON" : "Automatisch openen bij USB: AAN")
                : (IsEn() ? "Auto-open on USB plug-in: OFF" : "Automatisch openen bij USB: UIT");
        }

        private string HubUsbLine() {
            bool en = IsEn();
            string usbTxt = save.Connected ? ("● USB: KAREL (" + save.DriveRoot + ")") : (en ? "○ Memory mode (no USB)" : "○ Geheugen-modus (geen USB)");
            string serTxt = string.IsNullOrEmpty(ser.PortName) ? (en ? "Serial: waiting..." : "Serial: wachten...") : ("RP2350 @ " + ser.PortName);
            return usbTxt + "   |   " + serTxt;
        }

        private string HubVitalsLine() {
            bool en = IsEn();
            return string.Format(
                "{0}: {1}%  ·  {2}: {3}%  ·  {4}: {5}%  ·  {6}: {7}%",
                en ? "Hungry" : "Honger", save.GetInt("hunger", 80),
                en ? "Happy" : "Blij", save.GetInt("happiness", 85),
                en ? "Energy" : "Energie", save.GetInt("energy", 85),
                en ? "Clean" : "Fris", save.GetInt("hygiene", 90)
            );
        }

        internal static Button MakeFlatBtn(string text, int x, int y, int w, int h, Color bg, float fontPt) {
            Button b = new Button {
                Text = text, Location = new Point(x, y), Size = new Size(w, h),
                FlatStyle = FlatStyle.Flat, BackColor = bg, ForeColor = Color.White,
                Font = new Font("Segoe UI", fontPt, FontStyle.Bold), Cursor = Cursors.Hand
            };
            b.FlatAppearance.BorderSize = 0;
            return b;
        }

        private void ShowPickerMenu(Control anchor, string[] ids, bool isSkin) {
            bool en = IsEn();
            ContextMenuStrip m = new ContextMenuStrip();
            string cur = isSkin ? save.GetStr("skin", "classic") : save.GetEquippedItem();
            for (int i = 0; i < ids.Length; i++) {
                string id = ids[i];
                string lbl = string.IsNullOrEmpty(id) ? (en ? "(none)" : "(geen)") : id;
                ToolStripMenuItem it = new ToolStripMenuItem((id == cur ? "✓ " : "   ") + lbl);
                it.Click += delegate {
                    if (isSkin) save.Data["skin"] = id; else save.SetEquippedItem(id);
                    save.Save(); Invalidate(); RefreshHub();
                };
                m.Items.Add(it);
            }
            m.Show(anchor, new Point(0, anchor.Height));
        }

        private void OpenHub() {
            if (trayHidden) WakeFromTray();
            if (hubForm != null && !hubForm.IsDisposed) { hubForm.Activate(); RefreshHub(); return; }
            bool en = IsEn();
            float s = GetDpiScale();
            int W = Sc(560, s), P = Sc(18, s), Win = W - 2 * P, gap = Sc(10, s);

            Form f = new Form();
            hubForm = f;
            f.AutoScaleMode = AutoScaleMode.None;
            f.Text = "Karel de Koala — Sticky Hub";
            f.ClientSize = new Size(W, Sc(400, s));
            f.FormBorderStyle = FormBorderStyle.FixedDialog;
            f.MaximizeBox = false;
            f.StartPosition = FormStartPosition.CenterScreen;
            f.BackColor = Color.FromArgb(18, 20, 27);
            f.ForeColor = Color.FromArgb(242, 245, 250);
            f.TopMost = true;
            if (Icon != null) f.Icon = Icon;

            int hdrH = Sc(44, s);
            Label hdr = new Label {
                Text = "  KAREL DE KOALA  •  STICKY RP2350   v" + AutoUpdater.Version,
                Location = new Point(0, 0), Size = new Size(W, hdrH),
                BackColor = Color.FromArgb(196, 30, 37), ForeColor = Color.White,
                Font = new Font("Segoe UI", 10.5f, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft
            };
            f.Controls.Add(hdr);

            int curY = hdrH + Sc(14, s);
            int cardH = Sc(90, s);
            Panel statsCard = new Panel {
                Name = "statsCard", Location = new Point(P, curY), Size = new Size(Win, cardH),
                BackColor = Color.FromArgb(27, 31, 42)
            };
            Label topL = new Label {
                Name = "statsTopLbl", Location = new Point(Sc(14, s), Sc(10, s)),
                Size = new Size(Win - Sc(28, s), Sc(24, s)),
                Font = new Font("Segoe UI", 10f, FontStyle.Bold), ForeColor = Color.FromArgb(242, 245, 250),
                TextAlign = ContentAlignment.MiddleLeft
            };
            Panel xpTrack = new Panel {
                Name = "xpTrack", Location = new Point(Sc(14, s), Sc(40, s)),
                Size = new Size(Win - Sc(28, s), Sc(8, s)), BackColor = Color.FromArgb(15, 18, 24)
            };
            Panel xpFill = new Panel {
                Name = "xpFill", Location = new Point(0, 0), Size = new Size(0, Sc(8, s)),
                BackColor = Color.FromArgb(245, 196, 81)
            };
            xpTrack.Controls.Add(xpFill);
            Label botL = new Label {
                Name = "statsBotLbl", Location = new Point(Sc(14, s), Sc(55, s)),
                Size = new Size(Win - Sc(28, s), Sc(24, s)),
                Font = new Font("Consolas", 9.0f), ForeColor = Color.FromArgb(176, 184, 202),
                TextAlign = ContentAlignment.MiddleLeft
            };
            statsCard.Controls.Add(topL);
            statsCard.Controls.Add(xpTrack); statsCard.Controls.Add(botL);
            f.Controls.Add(statsCard);

            curY += cardH + Sc(14, s);
            int bw = (Win - 2 * gap) / 3, bh = Sc(38, s);
            string[] lbls = { en ? "Feed" : "Voer", en ? "Coffee" : "Koffie", en ? "Pet" : "Aai", en ? "Wash" : "Was", "Powernap", "Focus 25m" };
            Action[] acts = { DoFeed, DoCoffee, DoPet, DoWash, NapToggle, ToggleFocus };
            Color[] cols = {
                Color.FromArgb(38, 115, 77), Color.FromArgb(115, 75, 58), Color.FromArgb(168, 32, 90),
                Color.FromArgb(13, 115, 133), Color.FromArgb(59, 74, 90), Color.FromArgb(42, 48, 66)
            };
            for (int i = 0; i < 6; i++) {
                int idx = i;
                Button b = MakeFlatBtn(lbls[i], P + (i % 3) * (bw + gap), curY + (i / 3) * (bh + gap), bw, bh, cols[i], 9.0f);
                b.Name = "actBtn" + i;
                b.Click += delegate { acts[idx](); };
                f.Controls.Add(b);
            }

            curY += 2 * bh + gap + Sc(14, s);
            int stH = Sc(48, s);
            Panel styleCard = new Panel {
                Name = "styleCard", Location = new Point(P, curY), Size = new Size(Win, stH),
                BackColor = Color.FromArgb(27, 31, 42)
            };
            Label stLbl = new Label {
                Name = "styleLbl", Text = en ? "Style:" : "Stijl:",
                Location = new Point(Sc(14, s), Sc(10, s)), Size = new Size(Sc(64, s), Sc(28, s)),
                Font = new Font("Segoe UI", 9.0f, FontStyle.Bold), ForeColor = Color.FromArgb(152, 162, 184),
                TextAlign = ContentAlignment.MiddleLeft
            };
            int pkw = (Win - Sc(96, s)) / 2;
            Button skinBtn = MakeFlatBtn("", Sc(80, s), Sc(8, s), pkw, Sc(32, s), Color.FromArgb(42, 48, 66), 8.5f);
            skinBtn.Name = "skinBtn";
            skinBtn.Click += delegate { ShowPickerMenu(skinBtn, SpriteBank.SkinIds, true); };
            Button outBtn = MakeFlatBtn("", Sc(88, s) + pkw, Sc(8, s), Win - Sc(100, s) - pkw, Sc(32, s), Color.FromArgb(42, 48, 66), 8.5f);
            outBtn.Name = "outBtn";
            outBtn.Click += delegate { ShowPickerMenu(outBtn, SpriteBank.OutfitIds, false); };
            styleCard.Controls.Add(stLbl); styleCard.Controls.Add(skinBtn); styleCard.Controls.Add(outBtn);
            f.Controls.Add(styleCard);

            curY += stH + Sc(12, s);
            int sh = Sc(36, s);
            Button sndBtn = MakeFlatBtn("", P, curY, bw, sh, Color.FromArgb(42, 48, 66), 8.5f);
            sndBtn.Name = "sndBtn";
            sndBtn.Click += delegate { snd.Muted = !snd.Muted; RefreshHub(); };

            Button aqBtn = MakeFlatBtn("", P + bw + gap, curY, bw, sh, Color.FromArgb(42, 48, 66), 8.5f);
            aqBtn.Name = "aqBtn";
            aqBtn.Click += delegate {
                save.Data["auto_quiet_fullscreen"] = !save.GetBool("auto_quiet_fullscreen", true);
                save.Save(); RefreshHub();
            };

            Button langBtn = MakeFlatBtn("NL / EN", P + 2 * (bw + gap), curY, Win - 2 * (bw + gap), sh, Color.FromArgb(42, 48, 66), 8.5f);
            langBtn.Click += delegate {
                save.Data["language"] = IsEn() ? "nl" : "en"; save.Save(); RefreshHub();
            };
            f.Controls.Add(sndBtn); f.Controls.Add(aqBtn); f.Controls.Add(langBtn);

            curY += sh + Sc(12, s);
            Button hidBtn = MakeFlatBtn(HidFlagLabel(), P, curY, Win, Sc(32, s), Color.FromArgb(20, 104, 158), 8.5f);
            hidBtn.Name = "hidBtn";
            hidBtn.Click += delegate {
                bool on = StartupHelper.Toggle();
                Say(on ? (IsEn() ? "Auto-open on USB ON!" : "Automatisch openen bij USB AAN!") : (IsEn() ? "Auto-open on USB OFF." : "Automatisch openen bij USB UIT."), 55);
                RefreshHub();
            };
            f.Controls.Add(hidBtn);

            curY += Sc(38, s);
            int halfW = (Win - gap) / 2;
            Button updBtn = MakeFlatBtn("", P, curY, halfW, Sc(30, s), Color.FromArgb(42, 48, 66), 8.5f);
            updBtn.Name = "updBtn";
            updBtn.Click += delegate { CheckForUpdatesManual(); };
            Button uninstBtn = MakeFlatBtn("", P + halfW + gap, curY, Win - halfW - gap, Sc(30, s), Color.FromArgb(120, 36, 44), 8.5f);
            uninstBtn.Name = "uninstBtn";
            uninstBtn.Click += delegate { DoUninstallFromPc(); };
            f.Controls.Add(updBtn);
            f.Controls.Add(uninstBtn);

            Label usbLbl = new Label {
                Name = "usbLbl", Text = HubUsbLine(), Location = new Point(P, curY + Sc(38, s)), Size = new Size(Win, Sc(26, s)),
                Font = new Font("Consolas", 8.5f), ForeColor = Color.FromArgb(62, 207, 142), TextAlign = ContentAlignment.MiddleLeft
            };
            f.Controls.Add(usbLbl);

            RefreshHub();
            f.Show();
        }
    }

    internal static class Program {
        private static bool TrySignalExisting(bool toggle, int port) {
            try {
                using (TcpClient c = new TcpClient()) {
                    IAsyncResult ar = c.BeginConnect("127.0.0.1", port, null, null);
                    if (!ar.AsyncWaitHandle.WaitOne(350)) return false;
                    c.EndConnect(ar);
                    byte[] msg = Encoding.ASCII.GetBytes(toggle ? "TOGGLE\n" : "BOOP\n");
                    c.GetStream().Write(msg, 0, msg.Length);
                    return true;
                }
            } catch { return false; }
        }

        private static bool ShowAutoStartPrompt() {
            SaveStore s = new SaveStore();
            s.Load();
            bool en = s.GetStr("language", "nl") == "en";
            SpriteBank bank = SpriteBank.LoadEmbedded();
            Bitmap sprite = bank.GetFrame("IDLE", 0, s.GetStr("skin", "classic"), s.GetEquippedItem());

            float sc = 1.0f;
            try { using (Graphics g = Graphics.FromHwnd(IntPtr.Zero)) sc = Math.Max(1.0f, g.DpiX / 96.0f); } catch { }
            int W = KarelForm.Sc(490, sc), H = KarelForm.Sc(224, sc), P = KarelForm.Sc(18, sc), hdrH = KarelForm.Sc(40, sc);

            using (Form f = new Form()) {
                f.AutoScaleMode = AutoScaleMode.None;
                f.Text = "Karel de Koala";
                f.ClientSize = new Size(W, H);
                f.FormBorderStyle = FormBorderStyle.FixedDialog;
                f.MaximizeBox = false;
                f.MinimizeBox = false;
                f.StartPosition = FormStartPosition.CenterScreen;
                f.BackColor = Color.FromArgb(18, 20, 27);
                f.ForeColor = Color.FromArgb(242, 245, 250);
                f.TopMost = true;
                try { f.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
                f.Shown += delegate { f.Activate(); };

                Label hdr = new Label {
                    Text = "  KAREL DE KOALA  •  STICKY RP2350   v" + AutoUpdater.Version,
                    Location = new Point(0, 0), Size = new Size(W, hdrH),
                    BackColor = Color.FromArgb(196, 30, 37), ForeColor = Color.White,
                    Font = new Font("Segoe UI", 10f, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft
                };
                f.Controls.Add(hdr);

                int boxSz = KarelForm.Sc(104, sc);
                Panel icoBox = new Panel {
                    Location = new Point(P, hdrH + KarelForm.Sc(16, sc)), Size = new Size(boxSz, boxSz),
                    BackColor = Color.FromArgb(27, 31, 42)
                };
                icoBox.Paint += delegate(object sender, PaintEventArgs pe) {
                    pe.Graphics.InterpolationMode = InterpolationMode.NearestNeighbor;
                    pe.Graphics.PixelOffsetMode = PixelOffsetMode.Half;
                    int drawSz = KarelForm.Sc(96, sc);
                    int off = (boxSz - drawSz) / 2;
                    pe.Graphics.DrawImage(sprite, off, off, drawSz, drawSz);
                };
                f.Controls.Add(icoBox);

                int tx = P + boxSz + KarelForm.Sc(16, sc), tw = W - tx - P;
                Label titleLbl = new Label {
                    Text = en ? "Auto-start Karel on USB plug-in?" : "Karel voortaan automatisch starten?",
                    Location = new Point(tx, hdrH + KarelForm.Sc(18, sc)), Size = new Size(tw, KarelForm.Sc(46, sc)),
                    Font = new Font("Segoe UI", 12f, FontStyle.Bold), ForeColor = Color.FromArgb(242, 245, 250),
                    TextAlign = ContentAlignment.TopLeft
                };
                Label subLbl = new Label {
                    Text = en
                        ? "Should Karel automatically appear whenever you plug in this USB stick? (You can change this anytime in the menu.)"
                        : "Wil je dat Karel voortaan vanzelf verschijnt zodra je deze USB-stick inplugt? (Altijd weer uit te zetten in het menu.)",
                    Location = new Point(tx, hdrH + KarelForm.Sc(64, sc)), Size = new Size(tw, KarelForm.Sc(58, sc)),
                    Font = new Font("Segoe UI", 9.5f), ForeColor = Color.FromArgb(176, 184, 202),
                    TextAlign = ContentAlignment.TopLeft
                };
                f.Controls.Add(titleLbl);
                f.Controls.Add(subLbl);

                int btnY = H - KarelForm.Sc(54, sc), btnH = KarelForm.Sc(36, sc);
                Button btnYes = KarelForm.MakeFlatBtn(en ? "Yes, auto-start" : "Ja, automatisch", P, btnY, KarelForm.Sc(162, sc), btnH, Color.FromArgb(38, 115, 77), 9.5f);
                Button btnNo = KarelForm.MakeFlatBtn(en ? "No, just start" : "Nee, alleen nu", P + KarelForm.Sc(172, sc), btnY, KarelForm.Sc(162, sc), btnH, Color.FromArgb(42, 48, 66), 9.5f);
                Button btnReadme = KarelForm.MakeFlatBtn("README", W - P - KarelForm.Sc(110, sc), btnY, KarelForm.Sc(110, sc), btnH, Color.FromArgb(32, 37, 52), 9.5f);

                btnYes.Click += delegate {
                    StartupHelper.SetEnabled(true);
                    f.DialogResult = DialogResult.Yes;
                    f.Close();
                };
                btnNo.Click += delegate {
                    f.DialogResult = DialogResult.No;
                    f.Close();
                };
                btnReadme.Click += delegate {
                    string exeDir = Path.GetDirectoryName(Application.ExecutablePath) ?? "";
                    string[] localCands = {
                        string.IsNullOrEmpty(s.DriveRoot) ? "" : Path.Combine(s.DriveRoot, "Lees mij.html"),
                        Path.Combine(exeDir, "Lees mij.html"),
                    };
                    for (int ci = 0; ci < localCands.Length; ci++) {
                        if (!string.IsNullOrEmpty(localCands[ci]) && File.Exists(localCands[ci])) {
                            try { Process.Start(new ProcessStartInfo(localCands[ci]) { UseShellExecute = true }); return; } catch { }
                        }
                    }
                    const string url = "https://github.com/EgonRuiter/karel-de-koala#readme";
                    try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); } catch { }
                };
                f.AcceptButton = btnYes;
                f.KeyPreview = true;
                f.KeyDown += delegate(object ks, KeyEventArgs ke) {
                    if (ke.KeyCode == Keys.Escape) { f.DialogResult = DialogResult.No; f.Close(); }
                };
                f.Controls.Add(btnYes);
                f.Controls.Add(btnNo);
                f.Controls.Add(btnReadme);
                DialogResult dr = f.ShowDialog();
                return dr == DialogResult.Yes || dr == DialogResult.No;
            }
        }

        [STAThread]
        public static void Main(string[] args) {
            bool selfTest = false, toggle = false, noUpdate = false, startHidden = false, noShadow = false, askPrompt = false, noAsk = false;
            string updatedFrom = "";
            int ipcPort = 42421;
            for (int i = 0; i < args.Length; i++) {
                string a = args[i];
                if (a == "--self-test") selfTest = true;
                else if (a == "--no-update") noUpdate = true;
                else if (a == "--no-shadow") noShadow = true;
                else if (a == "--ask") askPrompt = true;
                else if (a == "--no-ask") noAsk = true;
                else if (a == "--tray" || a == "--hidden") startHidden = true;
                else if (a == "--toggle" || a == "-t" || a == "t") toggle = true;
                else if (a.StartsWith("--updated-from=")) updatedFrom = a.Substring(15);
                else if (a.StartsWith("--ipc-port=")) {
                    int p;
                    if (int.TryParse(a.Substring(11), out p) && p > 0 && p < 65536) ipcPort = p;
                }
            }
            if (selfTest) {
                SpriteBank b = SpriteBank.LoadEmbedded();
                Bitmap testBmp = b.GetFrame("IDLE", 0, "sticky", "crown");
                if (testBmp.Width != 32 || testBmp.Height != 32) throw new InvalidOperationException("Bad frame");
                WavSynth w = new WavSynth();
                SaveStore s = new SaveStore();
                s.Load();
                if (AutoUpdater.CompareVer("2.3.1", AutoUpdater.Version) <= 0 || AutoUpdater.Sha256Hex(Encoding.ASCII.GetBytes("abc")).Length != 64)
                    throw new InvalidOperationException("Bad updater self-check");
                Console.WriteLine(string.Format("SELF_TEST_OK version={0} states={1} xp={2} has_synth={3}", AutoUpdater.Version, b.States.Count, s.GetInt("xp", 0), w != null));
                return;
            }
            NativeWin.EnableDpi();
            if (TrySignalExisting(toggle, ipcPort)) return;
            if (toggle) return;
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            bool shouldAsk = askPrompt || (!noAsk && !startHidden && string.IsNullOrEmpty(updatedFrom) && !StartupHelper.IsEnabled());
            if (shouldAsk && !ShowAutoStartPrompt()) return;
            if (!noShadow && StartupHelper.IsEnabled()) {
                string instExe = StartupHelper.InstalledExePath();
                if (!string.Equals(Path.GetFullPath(Application.ExecutablePath), Path.GetFullPath(instExe), StringComparison.OrdinalIgnoreCase)) {
                    StartupHelper.SetEnabled(true);
                    if (File.Exists(instExe)) {
                        string pass = startHidden ? "--tray --no-shadow" : "--no-ask --no-shadow";
                        if (noUpdate) pass += " --no-update";
                        if (!string.IsNullOrEmpty(updatedFrom)) pass += " --updated-from=" + updatedFrom;
                        try { Process.Start(new ProcessStartInfo(instExe, pass) { UseShellExecute = false }); return; } catch { }
                    }
                }
            }
            Application.Run(new KarelForm(ipcPort, noUpdate, updatedFrom, startHidden));
        }
    }
}
