// Karel de Koala - Minimalist Zero-Install macOS Companion (Swift / AppKit)
// Native Cocoa equivalent of desktop/karel_native.cs (~300 KB Universal app, 0 external deps).

import Cocoa
import CryptoKit
import Darwin
import Foundation

// MARK: - Mac Display & Window Utilities

private enum MacWin {
    private static let meetingMarkers = [
        "zoom meeting", "zoom workplace", "zoom", "microsoft teams",
        "google meet", "meet - ", "webex", "powerpoint", "keynote"
    ]

    static func primaryHeight() -> CGFloat {
        return NSScreen.screens.first?.frame.height ?? CGDisplayBounds(CGMainDisplayID()).height
    }

    static func topDownWorkArea(for screen: NSScreen? = nil) -> CGRect {
        let s = screen ?? NSScreen.screens.first
        guard let sc = s else { return CGRect(x: 0, y: 25, width: 1280, height: 775) }
        let mh = primaryHeight()
        let vf = sc.visibleFrame
        return CGRect(x: vf.minX, y: mh - vf.maxY, width: vf.width, height: vf.height)
    }

    static func topDownFrame(for screen: NSScreen) -> CGRect {
        let mh = primaryHeight()
        let f = screen.frame
        return CGRect(x: f.minX, y: mh - f.maxY, width: f.width, height: f.height)
    }

    static func screenContaining(point pt: CGPoint) -> NSScreen? {
        for sc in NSScreen.screens {
            if topDownFrame(for: sc).contains(pt) { return sc }
        }
        return NSScreen.main ?? NSScreen.screens.first
    }

    static func virtualTopDownBounds() -> CGRect {
        var acc = CGRect.null
        for sc in NSScreen.screens {
            acc = acc.union(topDownFrame(for: sc))
        }
        return acc.isNull ? topDownWorkArea() : acc
    }

    private static func visibleExternalWindows(ownPid: pid_t) -> [(owner: String, title: String, bounds: CGRect)] {
        guard let info = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID)
            as? [[String: Any]] else { return [] }
        var out: [(String, String, CGRect)] = []
        for win in info {
            let layer = (win[kCGWindowLayer as String] as? Int) ?? 0
            if layer != 0 { continue }
            let pid = (win[kCGWindowOwnerPID as String] as? Int32) ?? 0
            if pid == ownPid { continue }
            guard let bDict = win[kCGWindowBounds as String] as? NSDictionary,
                  let rect = CGRect(dictionaryRepresentation: bDict) else { continue }
            let owner = (win[kCGWindowOwnerName as String] as? String) ?? ""
            let title = (win[kCGWindowName as String] as? String) ?? ""
            if owner == "Dock" || owner == "Window Server" || owner == "ControlCenter" { continue }
            out.append((owner, title, rect))
        }
        return out
    }

    static func foregroundLedge(ownPid: pid_t, karelPx: CGFloat, work: CGRect) -> CGRect? {
        for w in visibleExternalWindows(ownPid: ownPid) {
            let r = w.bounds
            if r.width < max(karelPx + 48, 220) || r.height < 140 { continue }
            if r.minY < work.minY + 36 || r.minY > work.maxY - 80 { continue }
            let lx0 = max(work.minX, r.minX + 12)
            let lx1 = min(work.maxX, r.maxX - 12)
            if lx1 - lx0 >= karelPx + 20 {
                return CGRect(x: lx0, y: r.minY, width: lx1 - lx0, height: r.height)
            }
            return nil
        }
        return nil
    }

    static func detectFullscreenOrMeeting(ownPid: pid_t) -> String {
        let wins = visibleExternalWindows(ownPid: ownPid)
        guard let top = wins.first else { return "" }
        let low = (top.owner + " " + top.title).lowercased()
        for marker in meetingMarkers {
            if low.contains(marker) && !low.contains("terminal") { return "meeting" }
        }
        for sc in NSScreen.screens {
            let f = topDownFrame(for: sc)
            if top.bounds.minX <= f.minX + 2 && top.bounds.minY <= f.minY + 2
                && top.bounds.maxX >= f.maxX - 2 && top.bounds.maxY >= f.maxY - 2 {
                return "fullscreen"
            }
        }
        return ""
    }
}

// MARK: - Sprites (shared karel_sprites.gz)

private final class SpriteBank {
    static let skinIds = [
        "classic", "sticky", "mint", "midnight", "gold", "crimson",
        "sakura", "ocean", "sunset", "espresso", "cyber", "forest", "snow", "obsidian"
    ]
    static let outfitIds = [
        "scarf", "stickycap", "hoodie", "headphones", "shades", "crown", "wizard", "partyhat",
        "beanie", "tophat", "chef", "halo", "bowtie", "cape", "labcoat", "nerd", ""
    ]

    var states: [String: [[String]]] = [:]
    var animDiv: [String: Int] = [:]
    var anchors: [String: [(Int, Int, Int, Int)]] = [:]
    private var pal: [Character: (UInt8, UInt8, UInt8)] = [:]
    private var cache: [String: NSImage] = [:]

    static func findSpritesGz() -> String? {
        if let res = Bundle.main.path(forResource: "karel_sprites", ofType: "gz"),
           FileManager.default.fileExists(atPath: res) { return res }
        var cur = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
        for _ in 0..<5 {
            for sub in ["karel_sprites.gz", "desktop/karel_sprites.gz"] {
                let cand = cur.appendingPathComponent(sub).path
                if FileManager.default.fileExists(atPath: cand) { return cand }
            }
            cur.deleteLastPathComponent()
        }
        if FileManager.default.fileExists(atPath: "karel_sprites.gz") { return "karel_sprites.gz" }
        return nil
    }

    static func loadBundled() -> SpriteBank {
        let bank = SpriteBank()
        guard let gzPath = findSpritesGz() else {
            fputs("Error: karel_sprites.gz not found.\n", stderr)
            return bank
        }
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/gzip")
        proc.arguments = ["-dc", gzPath]
        let pipe = Pipe()
        proc.standardOutput = pipe
        do { try proc.run() } catch { return bank }
        let rawData = pipe.fileHandleForReading.readDataToEndOfFile()
        proc.waitUntilExit()
        guard let text = String(data: rawData, encoding: .utf8) else { return bank }

        var curState: String? = nil
        var curRows: [String] = []
        func flush() {
            if let st = curState, !st.isEmpty, !curRows.isEmpty {
                bank.states[st, default: []].append(curRows)
            }
            curRows.removeAll(keepingCapacity: true)
        }

        for lineSub in text.split(separator: "\n", omittingEmptySubsequences: false) {
            let line = lineSub.replacingOccurrences(of: "\r", with: "")
            if line.hasPrefix("PAL|") {
                for item in line.dropFirst(4).split(separator: ",") {
                    let kv = item.split(separator: ":", maxSplits: 1)
                    if kv.count == 2, kv[0].count == 1, kv[1].hasPrefix("#"), kv[1].count == 7,
                       let hex = UInt32(kv[1].dropFirst(), radix: 16), let ch = kv[0].first {
                        bank.pal[ch] = (UInt8((hex >> 16) & 0xFF), UInt8((hex >> 8) & 0xFF), UInt8(hex & 0xFF))
                    }
                }
            } else if line.hasPrefix("DIV|") {
                for item in line.dropFirst(4).split(separator: ",") {
                    let kv = item.split(separator: "=", maxSplits: 1)
                    if kv.count == 2, let d = Int(kv[1]) {
                        bank.animDiv[String(kv[0])] = d
                    }
                }
            } else if line.hasPrefix("ANC|") {
                let body = line.dropFirst(4)
                if let eq = body.firstIndex(of: "=") {
                    let stName = String(body[..<eq])
                    let spec = body[body.index(after: eq)...]
                    var list: [(Int, Int, Int, Int)] = []
                    for fSpec in spec.split(separator: ";") {
                        let nums = fSpec.split(separator: ",").compactMap { Int($0) }
                        if nums.count == 4 { list.append((nums[0], nums[1], nums[2], nums[3])) }
                        else { list.append((0, 0, 0, 0)) }
                    }
                    bank.anchors[stName] = list
                }
            } else if line.hasPrefix("@") {
                flush()
                curState = String(line.dropFirst()).trimmingCharacters(in: .whitespaces)
            } else if line == "---" {
                flush()
            } else if curState != nil, !line.isEmpty {
                curRows.append(line)
            }
        }
        flush()
        return bank
    }

    private static func mapSkinChar(_ skin: String, _ ch: Character) -> Character {
        switch skin {
        case "sticky":
            if ch == "g" { return "r" }; if ch == "s" { return "R" }; if ch == "w" { return "W" }
        case "mint":
            if ch == "g" { return "n" }; if ch == "s" { return "e" }; if ch == "w" { return "W" }
        case "midnight":
            if ch == "g" { return "m" }; if ch == "s" { return "k" }; if ch == "w" { return "b" }
        case "gold":
            if ch == "g" { return "y" }; if ch == "s" { return "Y" }; if ch == "w" { return "W" }
        case "crimson":
            if ch == "g" { return "R" }; if ch == "s" { return "r" }; if ch == "w" { return "y" }
        case "sakura":
            if ch == "g" { return "p" }; if ch == "s" { return "v" }; if ch == "w" { return "P" }
        case "ocean":
            if ch == "g" { return "b" }; if ch == "s" { return "A" }; if ch == "w" { return "u" }
        case "sunset":
            if ch == "g" { return "o" }; if ch == "s" { return "f" }; if ch == "w" { return "t" }
        case "espresso":
            if ch == "g" { return "h" }; if ch == "s" { return "H" }; if ch == "w" { return "t" }
        case "cyber":
            if ch == "g" { return "d" }; if ch == "s" { return "k" }; if ch == "w" { return "a" }
        case "forest":
            if ch == "g" { return "e" }; if ch == "s" { return "E" }; if ch == "w" { return "l" }
        case "snow":
            if ch == "g" { return "W" }; if ch == "s" { return "w" }; if ch == "w" { return "u" }
        case "obsidian":
            if ch == "g" { return "d" }; if ch == "s" { return "k" }; if ch == "w" { return "W" }
        default: break
        }
        return ch
    }

    private static func fillRect(_ g: inout [[Character]], _ dx: Int, _ dy: Int, _ x0: Int, _ y0: Int, _ x1: Int, _ y1: Int, _ ch: Character) {
        let loY = max(0, y0 + dy), hiY = min(31, y1 + dy)
        let loX = max(0, x0 + dx), hiX = min(31, x1 + dx)
        if loY > hiY || loX > hiX { return }
        for y in loY...hiY {
            for x in loX...hiX { g[y][x] = ch }
        }
    }

    private static func putPx(_ g: inout [[Character]], _ dx: Int, _ dy: Int, _ x: Int, _ y: Int, _ ch: Character) {
        let nx = x + dx, ny = y + dy
        if nx >= 0 && nx < 32 && ny >= 0 && ny < 32 { g[ny][nx] = ch }
    }

    private static func applyOutfitAndTime(_ g: inout [[Character]], st: String, item: String, hx: Int, hy: Int, tx: Int, ty: Int, tired: Bool, vm: Bool) {
        let drawHead = hx != 99
        let drawTorso = tx != 99
        switch item {
        case "scarf" where drawTorso:
            fillRect(&g, tx, ty, 9, 17, 22, 18, "r")
            putPx(&g, tx, ty, 9, 17, "k"); putPx(&g, tx, ty, 22, 17, "k")
            for x in stride(from: 11, through: 20, by: 3) { putPx(&g, tx, ty, x, 17, "W") }
            for x in stride(from: 10, through: 21, by: 3) { putPx(&g, tx, ty, x, 18, "R") }
            fillRect(&g, tx, ty, 17, 19, 19, 22, "r")
            putPx(&g, tx, ty, 18, 20, "W"); putPx(&g, tx, ty, 17, 21, "R"); putPx(&g, tx, ty, 19, 21, "R")
            putPx(&g, tx, ty, 17, 23, "W"); putPx(&g, tx, ty, 19, 23, "W")
        case "stickycap" where drawHead:
            fillRect(&g, hx, hy, 11, 1, 20, 1, "k")
            fillRect(&g, hx, hy, 10, 2, 21, 4, "r")
            putPx(&g, hx, hy, 10, 2, "k"); putPx(&g, hx, hy, 21, 2, "k")
            fillRect(&g, hx, hy, 9, 5, 18, 5, "k")
            fillRect(&g, hx, hy, 19, 5, 25, 5, "R"); putPx(&g, hx, hy, 25, 5, "k")
            putPx(&g, hx, hy, 15, 3, "W"); putPx(&g, hx, hy, 16, 3, "W"); putPx(&g, hx, hy, 15, 4, "W")
        case "hoodie" where drawTorso:
            fillRect(&g, tx, ty, 9, 17, 22, 18, "R")
            fillRect(&g, tx, ty, 10, 18, 21, 24, "r")
            fillRect(&g, tx, ty, 7, 19, 9, 22, "r"); fillRect(&g, tx, ty, 22, 19, 24, 22, "r")
            putPx(&g, tx, ty, 7, 22, "R"); putPx(&g, tx, ty, 24, 22, "R")
            fillRect(&g, tx, ty, 13, 21, 18, 23, "R")
            fillRect(&g, tx, ty, 10, 24, 21, 24, "R")
            putPx(&g, tx, ty, 14, 19, "W"); putPx(&g, tx, ty, 14, 20, "W")
            putPx(&g, tx, ty, 17, 19, "W"); putPx(&g, tx, ty, 17, 20, "W")
        case "headphones" where drawHead:
            fillRect(&g, hx, hy, 8, 3, 23, 3, "s"); fillRect(&g, hx, hy, 7, 4, 24, 4, "d")
            putPx(&g, hx, hy, 5, 6, "d"); putPx(&g, hx, hy, 6, 5, "d"); putPx(&g, hx, hy, 25, 5, "d"); putPx(&g, hx, hy, 26, 6, "d")
            fillRect(&g, hx, hy, 2, 7, 4, 11, "k"); fillRect(&g, hx, hy, 27, 7, 29, 11, "k")
            fillRect(&g, hx, hy, 3, 8, 4, 10, "r"); fillRect(&g, hx, hy, 27, 8, 28, 10, "r")
            putPx(&g, hx, hy, 5, 8, "w"); putPx(&g, hx, hy, 5, 9, "w"); putPx(&g, hx, hy, 5, 10, "w")
            putPx(&g, hx, hy, 26, 8, "w"); putPx(&g, hx, hy, 26, 9, "w"); putPx(&g, hx, hy, 26, 10, "w")
        case "shades" where drawHead:
            fillRect(&g, hx, hy, 9, 10, 14, 12, "k"); fillRect(&g, hx, hy, 17, 10, 22, 12, "k")
            fillRect(&g, hx, hy, 10, 11, 13, 12, "d"); fillRect(&g, hx, hy, 18, 11, 21, 12, "d")
            fillRect(&g, hx, hy, 14, 10, 17, 10, "k"); putPx(&g, hx, hy, 8, 10, "k"); putPx(&g, hx, hy, 23, 10, "k")
            putPx(&g, hx, hy, 10, 11, "W"); putPx(&g, hx, hy, 11, 11, "W")
            putPx(&g, hx, hy, 18, 11, "W"); putPx(&g, hx, hy, 19, 11, "W")
        case "crown" where drawHead:
            fillRect(&g, hx, hy, 11, 5, 20, 5, "k")
            fillRect(&g, hx, hy, 11, 3, 20, 4, "y")
            putPx(&g, hx, hy, 11, 1, "y"); putPx(&g, hx, hy, 11, 2, "y")
            putPx(&g, hx, hy, 15, 1, "y"); putPx(&g, hx, hy, 16, 1, "y"); putPx(&g, hx, hy, 15, 2, "y"); putPx(&g, hx, hy, 16, 2, "y")
            putPx(&g, hx, hy, 20, 1, "y"); putPx(&g, hx, hy, 20, 2, "y")
            putPx(&g, hx, hy, 13, 3, "Y"); putPx(&g, hx, hy, 18, 3, "Y")
            putPx(&g, hx, hy, 15, 4, "R"); putPx(&g, hx, hy, 16, 4, "R")
            putPx(&g, hx, hy, 12, 4, "b"); putPx(&g, hx, hy, 19, 4, "b")
        case "wizard" where drawHead:
            fillRect(&g, hx, hy, 8, 5, 23, 5, "k")
            fillRect(&g, hx, hy, 9, 4, 22, 4, "m"); fillRect(&g, hx, hy, 11, 4, 20, 4, "y")
            fillRect(&g, hx, hy, 12, 2, 19, 3, "m")
            fillRect(&g, hx, hy, 14, 0, 17, 1, "m"); putPx(&g, hx, hy, 18, 0, "m")
            putPx(&g, hx, hy, 15, 2, "y"); putPx(&g, hx, hy, 16, 1, "W")
        case "partyhat" where drawHead:
            fillRect(&g, hx, hy, 12, 5, 19, 5, "k")
            fillRect(&g, hx, hy, 13, 3, 18, 4, "m"); fillRect(&g, hx, hy, 14, 1, 17, 2, "R")
            putPx(&g, hx, hy, 15, 0, "y"); putPx(&g, hx, hy, 16, 0, "W")
            putPx(&g, hx, hy, 14, 4, "y"); putPx(&g, hx, hy, 17, 4, "b"); putPx(&g, hx, hy, 15, 2, "y")
        case "beanie" where drawHead:
            fillRect(&g, hx, hy, 11, 1, 20, 4, "r"); fillRect(&g, hx, hy, 12, 1, 19, 1, "k")
            putPx(&g, hx, hy, 11, 1, "."); putPx(&g, hx, hy, 20, 1, ".")
            fillRect(&g, hx, hy, 10, 4, 21, 5, "R"); putPx(&g, hx, hy, 10, 5, "k"); putPx(&g, hx, hy, 21, 5, "k")
            for x in stride(from: 11, through: 20, by: 2) { putPx(&g, hx, hy, x, 5, "S") }
            fillRect(&g, hx, hy, 15, 0, 16, 1, "W"); putPx(&g, hx, hy, 14, 0, "w"); putPx(&g, hx, hy, 17, 0, "w")
        case "tophat" where drawHead:
            fillRect(&g, hx, hy, 9, 5, 22, 5, "k")
            fillRect(&g, hx, hy, 11, 0, 20, 4, "k"); fillRect(&g, hx, hy, 12, 1, 19, 3, "d")
            fillRect(&g, hx, hy, 12, 4, 19, 4, "r"); putPx(&g, hx, hy, 13, 1, "s"); putPx(&g, hx, hy, 13, 2, "s")
        case "chef" where drawHead:
            fillRect(&g, hx, hy, 11, 5, 20, 5, "k"); fillRect(&g, hx, hy, 11, 4, 20, 4, "r")
            fillRect(&g, hx, hy, 10, 1, 21, 3, "W"); fillRect(&g, hx, hy, 12, 0, 19, 1, "W")
            putPx(&g, hx, hy, 10, 1, "w"); putPx(&g, hx, hy, 21, 1, "w"); putPx(&g, hx, hy, 14, 1, "w"); putPx(&g, hx, hy, 17, 1, "w")
            putPx(&g, hx, hy, 14, 2, "w"); putPx(&g, hx, hy, 17, 2, "w"); fillRect(&g, hx, hy, 11, 3, 20, 3, "w")
        case "halo" where drawHead:
            fillRect(&g, hx, hy, 11, 1, 20, 1, "y"); fillRect(&g, hx, hy, 10, 2, 21, 2, "Y")
            fillRect(&g, hx, hy, 12, 2, 19, 2, "."); fillRect(&g, hx, hy, 11, 3, 20, 3, "y")
            putPx(&g, hx, hy, 12, 1, "W"); putPx(&g, hx, hy, 13, 1, "t"); putPx(&g, hx, hy, 19, 1, "t")
        case "bowtie" where drawTorso:
            fillRect(&g, tx, ty, 12, 17, 19, 17, "W"); putPx(&g, tx, ty, 11, 17, "w"); putPx(&g, tx, ty, 20, 17, "w")
            fillRect(&g, tx, ty, 12, 18, 13, 20, "r"); putPx(&g, tx, ty, 14, 19, "r")
            fillRect(&g, tx, ty, 18, 18, 19, 20, "r"); putPx(&g, tx, ty, 17, 19, "r")
            putPx(&g, tx, ty, 12, 18, "k"); putPx(&g, tx, ty, 19, 18, "k"); putPx(&g, tx, ty, 12, 20, "k"); putPx(&g, tx, ty, 19, 20, "k")
            putPx(&g, tx, ty, 15, 19, "R"); putPx(&g, tx, ty, 16, 19, "y")
        case "cape" where drawTorso:
            fillRect(&g, tx, ty, 7, 18, 9, 26, "S"); fillRect(&g, tx, ty, 22, 18, 24, 26, "S")
            fillRect(&g, tx, ty, 8, 19, 9, 25, "r"); fillRect(&g, tx, ty, 22, 19, 23, 25, "r")
            putPx(&g, tx, ty, 6, 23, "S"); putPx(&g, tx, ty, 6, 24, "r"); putPx(&g, tx, ty, 6, 25, "S")
            putPx(&g, tx, ty, 25, 23, "S"); putPx(&g, tx, ty, 25, 24, "r"); putPx(&g, tx, ty, 25, 25, "S")
            fillRect(&g, tx, ty, 10, 17, 21, 18, "r"); fillRect(&g, tx, ty, 14, 17, 17, 18, "y"); putPx(&g, tx, ty, 15, 18, "W")
        case "labcoat" where drawTorso:
            fillRect(&g, tx, ty, 9, 18, 22, 25, "W"); fillRect(&g, tx, ty, 7, 19, 9, 22, "W"); fillRect(&g, tx, ty, 22, 19, 24, 22, "W")
            putPx(&g, tx, ty, 9, 18, "w"); putPx(&g, tx, ty, 22, 18, "w"); fillRect(&g, tx, ty, 9, 25, 22, 25, "w")
            fillRect(&g, tx, ty, 15, 18, 16, 24, "b"); putPx(&g, tx, ty, 15, 18, "A"); putPx(&g, tx, ty, 16, 18, "A")
            putPx(&g, tx, ty, 14, 18, "w"); putPx(&g, tx, ty, 17, 18, "w")
            fillRect(&g, tx, ty, 18, 21, 20, 22, "w"); putPx(&g, tx, ty, 19, 20, "r")
        case "nerd" where drawHead:
            fillRect(&g, hx, hy, 9, 10, 14, 13, "k"); fillRect(&g, hx, hy, 17, 10, 22, 13, "k")
            fillRect(&g, hx, hy, 10, 11, 13, 12, "u"); fillRect(&g, hx, hy, 18, 11, 21, 12, "u")
            putPx(&g, hx, hy, 12, 11, "k"); putPx(&g, hx, hy, 20, 11, "k"); putPx(&g, hx, hy, 11, 11, "W"); putPx(&g, hx, hy, 19, 11, "W")
            fillRect(&g, hx, hy, 14, 11, 17, 11, "k"); putPx(&g, hx, hy, 15, 11, "W"); putPx(&g, hx, hy, 16, 11, "W")
            putPx(&g, hx, hy, 8, 11, "k"); putPx(&g, hx, hy, 23, 11, "k")
        default: break
        }
        if tired && drawHead && st != "HYPER" {
            for x in [11, 12, 19, 20] { for y in [11, 13] { putPx(&g, hx, hy, x, y, "s") } }
        }
        if vm && drawTorso && st != "EAT" && st != "STUDY" && st != "JUMP" && st != "CLIMB" && st != "BORREL" {
            fillRect(&g, tx, ty, 24, 18, 28, 23, "k"); fillRect(&g, tx, ty, 25, 19, 27, 22, "y"); fillRect(&g, tx, ty, 24, 17, 27, 18, "W")
        }
    }

    func getFrame(state reqState: String, frameIdx: Int, skin: String, item: String) -> NSImage {
        var st = reqState
        var frames = states[st] ?? []
        if frames.isEmpty { st = "IDLE"; frames = states["IDLE"] ?? [] }
        if frames.isEmpty { return NSImage(size: NSSize(width: 32, height: 32)) }
        let div = max(1, animDiv[st] ?? 2)
        let fi = (frameIdx / div) % frames.count

        let now = Date()
        let cal = Calendar.current
        let hr = cal.component(.hour, from: now)
        let wd = cal.component(.weekday, from: now) // 6 = Friday in Gregorian
        let tired = hr >= 0 && hr < 4
        let vm = wd == 6 && hr >= 16
        let sk = skin.isEmpty ? "classic" : skin
        let key = "\(sk)|\(item)|\(st)|\(fi)|\(tired ? 1 : 0)|\(vm ? 1 : 0)"
        if let cached = cache[key] { return cached }

        let raw = frames[fi]
        var g = Array(repeating: Array(repeating: Character("."), count: 32), count: 32)
        for y in 0..<min(32, raw.count) {
            let row = Array(raw[y])
            for x in 0..<min(32, row.count) {
                let ch = row[x]
                g[y][x] = ch == "." ? "." : Self.mapSkinChar(sk, ch)
            }
        }
        let anc = (anchors[st].flatMap { fi < $0.count ? $0[fi] : nil }) ?? (0, 0, 0, 0)
        Self.applyOutfitAndTime(&g, st: st, item: item, hx: anc.0, hy: anc.1, tx: anc.2, ty: anc.3, tired: tired, vm: vm)

        var rgba = [UInt8](repeating: 0, count: 32 * 32 * 4)
        for y in 0..<32 {
            for x in 0..<32 {
                let ch = g[y][x]
                if ch != ".", let rgb = pal[ch] {
                    let off = (y * 32 + x) * 4
                    rgba[off] = rgb.0
                    rgba[off + 1] = rgb.1
                    rgba[off + 2] = rgb.2
                    rgba[off + 3] = 255
                }
            }
        }
        let img: NSImage = rgba.withUnsafeMutableBytes { ptr in
            if let base = ptr.baseAddress,
               let ctx = CGContext(
                   data: base, width: 32, height: 32, bitsPerComponent: 8, bytesPerRow: 128,
                   space: CGColorSpaceCreateDeviceRGB(),
                   bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
               ),
               let cg = ctx.makeImage() {
                return NSImage(cgImage: cg, size: NSSize(width: 32, height: 32))
            }
            return NSImage(size: NSSize(width: 32, height: 32))
        }
        if cache.count > 360 { cache.removeAll(keepingCapacity: true) }
        cache[key] = img
        return img
    }
}

// MARK: - In-Memory PCM WAV Synthesizer (NSSound)

private final class WavSynth {
    private var bank: [String: Data] = [:]
    private var sounds: [String: NSSound] = [:]
    private var activeSound: NSSound?
    private var lastPlayAt = Date.distantPast
    var muted = false
    var autoQuiet = false

    init() {
        bank["climb"] = Self.buildSeq([330, 392, 523.25], 0.065, 0.20)
        bank["pet"] = Self.buildSeq([523.25, 659.25, 783.99], 0.055, 0.18)
        bank["eat"] = Self.buildSeq([293.66, 349.23, 440], 0.06, 0.20)
        bank["coffee"] = Self.buildSeq([440, 554.37, 659.25, 880], 0.05, 0.20)
        bank["boop"] = Self.buildSeq([587.33, 783.99, 1046.5], 0.06, 0.22)
        bank["levelup"] = Self.buildSeq([440, 554.37, 659.25, 880, 1046.5], 0.08, 0.22)
        bank["dive"] = Self.buildSeq([659.25, 523.25, 392.0, 261.63], 0.08, 0.20)
        bank["sneeze"] = Self.buildSeq([780, 220], 0.08, 0.22)
        bank["chirp"] = Self.buildSeq([620, 740], 0.035, 0.12)
        bank["chirp2"] = Self.buildSeq([560, 680, 610], 0.032, 0.12)
        bank["chirp3"] = Self.buildSeq([680, 820], 0.034, 0.12)
        bank["chirp4"] = Self.buildSeq([520, 640, 760], 0.030, 0.11)
        bank["magic"] = Self.buildSeq([523.25, 659.25, 783.99, 1046.5, 1318.5], 0.05, 0.18)
        bank["karate"] = Self.buildSeq([220, 660, 330], 0.045, 0.20)
        bank["dj"] = Self.buildSeq([196, 261.63, 392, 523.25], 0.055, 0.19)
        bank["toss"] = Self.buildSeq([310, 460, 680], 0.04, 0.17)
        bank["trick"] = Self.buildSeq([440, 587.33, 783.99], 0.05, 0.18)
        bank["shuffle"] = Self.buildSeq([493.88, 659.25, 880], 0.04, 0.16)
    }

    private static func buildSeq(_ freqs: [Double], _ noteDur: Double, _ amp: Double) -> Data {
        let sr = 22050
        let nPer = max(100, Int(noteDur * Double(sr)))
        let total = nPer * freqs.count
        var pcm = [Int16](repeating: 0, count: total)
        for (fi, f) in freqs.enumerated() {
            var ph = 0.0
            for i in 0..<nPer {
                let env = min(1.0, Double(i) / 120.0) * min(1.0, Double(nPer - i) / 220.0)
                let s = sin(ph) + 0.28 * sin(2.0 * ph)
                pcm[fi * nPer + i] = Int16(max(-32767.0, min(32767.0, s * env * amp * 24000.0)))
                ph += 2.0 * Double.pi * f / Double(sr)
            }
        }
        let dataBytes = UInt32(total * 2)
        var d = Data()
        func appendLE<T: FixedWidthInteger>(_ v: T) {
            var le = v.littleEndian
            withUnsafeBytes(of: &le) { d.append(contentsOf: $0) }
        }
        d.append(contentsOf: "RIFF".utf8); appendLE(UInt32(36) + dataBytes)
        d.append(contentsOf: "WAVEfmt ".utf8); appendLE(UInt32(16))
        appendLE(UInt16(1)); appendLE(UInt16(1))
        appendLE(UInt32(sr)); appendLE(UInt32(sr * 2))
        appendLE(UInt16(2)); appendLE(UInt16(16))
        d.append(contentsOf: "data".utf8); appendLE(dataBytes)
        for sample in pcm { appendLE(sample) }
        return d
    }

    func play(_ key: String) {
        if muted || autoQuiet { return }
        guard let wav = bank[key] else { return }
        let now = Date()
        if now.timeIntervalSince(lastPlayAt) < 0.08 { return }
        lastPlayAt = now
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            let snd = self.sounds[key] ?? NSSound(data: wav)
            guard let snd = snd else { return }
            self.sounds[key] = snd
            if self.activeSound !== snd { self.activeSound?.stop() }
            if snd.isPlaying { snd.stop() }
            snd.currentTime = 0
            self.activeSound = snd
            snd.play()
        }
    }
}

// MARK: - USB Drive & Persistent SaveStore

private final class SaveStore {
    var data: [String: Any] = [:]
    private(set) var driveRoot = ""
    var connected: Bool { !driveRoot.isEmpty }
    private let fallbackPath: String
    private let ioLock = NSLock()
    private let ioQueue = DispatchQueue(label: "nl.svsticky.karel.saveio", qos: .utility)
    private var pendingBytes: Data?
    private var saveWorkItem: DispatchWorkItem?
    private static let isoFmt: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withFullDate, .withTime, .withDashSeparatorInDate, .withColonSeparatorInTime]
        return f
    }()

    init() {
        let appSup = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Library/Application Support")
        fallbackPath = appSup.appendingPathComponent("KarelDeKoala/save.json").path
        driveRoot = Self.findUsbDrive()
    }

    static func findUsbDrive() -> String {
        let fm = FileManager.default
        var cur = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
        for _ in 0..<5 {
            if fm.fileExists(atPath: cur.appendingPathComponent(".karel_drive").path) { return cur.path }
            cur.deleteLastPathComponent()
        }
        let karelVol = "/Volumes/KAREL"
        if fm.fileExists(atPath: karelVol + "/.karel_drive") { return karelVol }
        if let vols = try? fm.contentsOfDirectory(atPath: "/Volumes") {
            for v in vols {
                let p = "/Volumes/\(v)"
                if fm.fileExists(atPath: p + "/.karel_drive") { return p }
            }
        }
        return ""
    }

    static func volumeSerial(_ root: String) -> String {
        if root.isEmpty { return "" }
        let url = URL(fileURLWithPath: root)
        if let vals = try? url.resourceValues(forKeys: [.volumeUUIDStringKey]),
           let uuid = vals.volumeUUIDString, !uuid.isEmpty {
            return String(uuid.prefix(8)).uppercased()
        }
        return ""
    }

    func pollUsb() -> String {
        let was = connected
        let found = Self.findUsbDrive()
        driveRoot = found
        if !was && connected { return "on" }
        if was && !connected { return "off" }
        return ""
    }

    func hasNoHidFlag() -> Bool {
        return !driveRoot.isEmpty && FileManager.default.fileExists(atPath: driveRoot + "/.karel_no_hid")
    }

    func toggleNoHidFlag() -> Bool? {
        if driveRoot.isEmpty { return nil }
        let path = driveRoot + "/.karel_no_hid"
        do {
            if FileManager.default.fileExists(atPath: path) {
                try FileManager.default.removeItem(atPath: path)
                return false
            } else {
                try "NO_HID=1\n".write(toFile: path, atomically: true, encoding: .utf8)
                return true
            }
        } catch { return nil }
    }

    static func xpForNextLevel(_ lvl: Int) -> Int {
        return lvl <= 0 ? 0 : 180 * lvl * (lvl + 1)
    }

    static func levelFromXp(_ xp: Int) -> Int {
        var lvl = 1
        while xp >= xpForNextLevel(lvl) { lvl += 1 }
        return lvl
    }

    private static func readDict(_ path: String?) -> [String: Any]? {
        guard let p = path, FileManager.default.fileExists(atPath: p),
              var raw = try? Data(contentsOf: URL(fileURLWithPath: p)), raw.count >= 2 else { return nil }
        if raw.count >= 3 && raw[0] == 0xEF && raw[1] == 0xBB && raw[2] == 0xBF {
            raw = raw.subdata(in: 3..<raw.count)
        }
        if raw.contains(0xFF) || raw.contains(0x00) { return nil }
        guard let obj = try? JSONSerialization.jsonObject(with: raw) as? [String: Any] else { return nil }
        return obj
    }

    private static func parseDate(_ s: String) -> Date? {
        if let d = isoFmt.date(from: s) { return d }
        let df = DateFormatter()
        df.locale = Locale(identifier: "en_US_POSIX")
        df.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return df.date(from: s)
    }

    private static func rankSave(_ d: [String: Any]) -> Double {
        let ls = (d["last_seen"] as? String).flatMap(parseDate)?.timeIntervalSince1970 ?? 0.0
        let xp = (d["xp"] as? NSNumber)?.doubleValue ?? 0.0
        return floor(ls) * 100000.0 + xp
    }

    private static func defaultSave() -> [String: Any] {
        return [
            "name": "Karel",
            "hunger": 80,
            "happiness": 85,
            "energy": 85,
            "hygiene": 90,
            "caffeine": 25,
            "xp": 0,
            "level": 1,
            "total_pets": 0,
            "roam_mode": "free",
            "karel_scale": 3,
            "skin": "classic",
            "equipped": ["scarf"],
            "auto_quiet_fullscreen": true,
            "language": "nl",
            "stick_serial": "",
            "last_seen": formatNow()
        ]
    }

    private static func formatNow() -> String {
        let df = DateFormatter()
        df.locale = Locale(identifier: "en_US_POSIX")
        df.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return df.string(from: Date())
    }

    func load() {
        let usbPath = driveRoot.isEmpty ? nil : (driveRoot + "/save.json")
        let curSer = driveRoot.isEmpty ? "" : Self.volumeSerial(driveRoot)
        let u = Self.readDict(usbPath)
        let f = Self.readDict(fallbackPath)
        var picked: [String: Any]? = nil
        var recoveredFb = false
        if let u = u, let f = f {
            var uSer = (u["stick_serial"] as? String) ?? ""
            if uSer.isEmpty { uSer = curSer }
            let fSer = (f["stick_serial"] as? String) ?? ""
            if !fSer.isEmpty && uSer == fSer && Self.rankSave(f) > Self.rankSave(u) {
                picked = f; recoveredFb = true
            } else {
                picked = u
            }
        } else if let u = u {
            picked = u
        } else if let f = f {
            if driveRoot.isEmpty || ((f["stick_serial"] as? String) == curSer && !curSer.isEmpty) {
                picked = f; recoveredFb = !driveRoot.isEmpty
            }
        }
        data = Self.defaultSave()
        if let picked = picked {
            for (k, v) in picked { data[k] = v }
        }
        if let prev = Self.parseDate(getStr("last_seen", "")) {
            let hrs = max(0.0, Date().timeIntervalSince(prev) / 3600.0)
            if hrs > 0.05 {
                data["hunger"] = max(15, Int(round(Double(getInt("hunger", 80)) - hrs * 0.9)))
                data["happiness"] = max(25, Int(round(Double(getInt("happiness", 85)) - hrs * 0.6)))
                data["hygiene"] = max(25, Int(round(Double(getInt("hygiene", 90)) - hrs * 0.4)))
                data["caffeine"] = max(0, Int(round(Double(getInt("caffeine", 25)) - hrs * 4.0)))
                if hrs >= 1.0 {
                    data["energy"] = min(100, Int(round(Double(getInt("energy", 85)) + hrs * 6.0)))
                }
            }
        }
        data["level"] = Self.levelFromXp(getInt("xp", 0))
        if !curSer.isEmpty { data["stick_serial"] = curSer }
        if recoveredFb { save() }
    }

    func getInt(_ k: String, _ def: Int) -> Int {
        return (data[k] as? NSNumber)?.intValue ?? def
    }
    func getStr(_ k: String, _ def: String) -> String {
        return (data[k] as? String) ?? def
    }
    func getBool(_ k: String, _ def: Bool) -> Bool {
        return (data[k] as? NSNumber)?.boolValue ?? def
    }
    func getEquippedItem() -> String {
        return (data["equipped"] as? [String])?.first ?? ""
    }
    func setEquippedItem(_ item: String) {
        data["equipped"] = item.isEmpty ? [] : [item]
    }
    func clampStat(_ k: String, _ delta: Int, _ lo: Int, _ hi: Int) {
        data[k] = max(lo, min(hi, getInt(k, lo) + delta))
    }

    private func buildSaveBytes() -> Data? {
        if !driveRoot.isEmpty && getStr("stick_serial", "").isEmpty {
            let ser = Self.volumeSerial(driveRoot)
            if !ser.isEmpty { data["stick_serial"] = ser }
        }
        data["last_seen"] = Self.formatNow()
        guard var out = try? JSONSerialization.data(withJSONObject: data, options: [.prettyPrinted, .sortedKeys]) else { return nil }
        out.append(0x0A)
        return out
    }

    private func writeSnapshot(_ out: Data, rootSnapshot: String) {
        ioLock.lock()
        defer { ioLock.unlock() }
        let fm = FileManager.default
        atomicWrite(fallbackPath, out)
        if connected && !rootSnapshot.isEmpty && fm.fileExists(atPath: rootSnapshot) {
            writeUsbFlush(rootSnapshot + "/save.json", out)
        }
    }

    func saveDeferred() {
        guard let out = buildSaveBytes() else { return }
        let rootCopy = driveRoot
        ioLock.lock()
        pendingBytes = out
        saveWorkItem?.cancel()
        let item = DispatchWorkItem { [weak self] in
            guard let self = self else { return }
            self.ioLock.lock()
            let snap = self.pendingBytes
            self.pendingBytes = nil
            self.ioLock.unlock()
            if let snap = snap { self.writeSnapshot(snap, rootSnapshot: rootCopy) }
        }
        saveWorkItem = item
        ioLock.unlock()
        ioQueue.asyncAfter(deadline: .now() + 0.35, execute: item)
    }

    func save() {
        ioLock.lock()
        saveWorkItem?.cancel()
        saveWorkItem = nil
        pendingBytes = nil
        ioLock.unlock()
        guard let out = buildSaveBytes() else { return }
        writeSnapshot(out, rootSnapshot: driveRoot)
    }

    private func writeUsbFlush(_ path: String, _ bytes: Data) {
        let fd = Darwin.open(path, O_WRONLY | O_CREAT | O_TRUNC, 0o644)
        guard fd >= 0 else { return }
        defer { Darwin.close(fd) }
        bytes.withUnsafeBytes { raw in
            guard let base = raw.baseAddress else { return }
            var off = 0
            while off < raw.count {
                let n = Darwin.write(fd, base.advanced(by: off), raw.count - off)
                if n <= 0 { break }
                off += n
            }
        }
        _ = Darwin.fsync(fd)
    }

    private func atomicWrite(_ path: String, _ bytes: Data) {
        let url = URL(fileURLWithPath: path)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? bytes.write(to: url, options: .atomic)
    }
}

// MARK: - POSIX USB Serial Sync (/dev/cu.usbmodem*)

private final class SerialSync {
    private var fd: Int32 = -1
    private var lastState = ""
    private var stopping = false
    private(set) var portName = ""
    private let lock = NSLock()
    private let onEvent: (String) -> Void

    init(onEvent: @escaping (String) -> Void) {
        self.onEvent = onEvent
        DispatchQueue.global(qos: .background).async { [weak self] in self?.loop() }
    }

    func send(_ line: String) {
        lock.lock()
        defer { lock.unlock() }
        if fd < 0 { return }
        if line.hasPrefix("STATE:") {
            if line == lastState { return }
            lastState = line
        }
        let msg = line.trimmingCharacters(in: .whitespacesAndNewlines) + "\n"
        let ok = msg.withCString { ptr in
            let len = strlen(ptr)
            return Darwin.write(fd, ptr, len) == Int(len)
        }
        if !ok { dropLocked() }
    }

    private func dropLocked() {
        if fd >= 0 { Darwin.close(fd) }
        fd = -1; portName = ""; lastState = ""
    }

    private func tryConnect() {
        guard let devs = try? FileManager.default.contentsOfDirectory(atPath: "/dev") else { return }
        for d in devs.sorted().reversed() where d.hasPrefix("cu.usbmodem") {
            let path = "/dev/\(d)"
            let cand = Darwin.open(path, O_RDWR | O_NOCTTY | O_NONBLOCK)
            if cand < 0 { continue }
            var tio = termios()
            tcgetattr(cand, &tio)
            cfmakeraw(&tio)
            cfsetspeed(&tio, speed_t(B115200))
            tio.c_cflag |= tcflag_t(CLOCAL | CREAD)
            tcsetattr(cand, TCSANOW, &tio)
            usleep(25_000)
            tcflush(cand, TCIFLUSH)
            _ = "KAREL_PING\n".withCString { Darwin.write(cand, $0, strlen($0)) }
            var acc = ""
            for _ in 0..<6 {
                var buf = [UInt8](repeating: 0, count: 128)
                let n = Darwin.read(cand, &buf, 128)
                if n > 0 { acc += String(decoding: buf[0..<n], as: UTF8.self) }
                if acc.contains("KAREL_PONG") {
                    lock.lock(); fd = cand; portName = d; lock.unlock()
                    return
                }
                usleep(20_000)
            }
            Darwin.close(cand)
        }
    }

    private func loop() {
        var lineBuf = ""
        var hbTicks = 0
        while !stopping {
            lock.lock(); let curFd = fd; lock.unlock()
            if curFd < 0 {
                lineBuf = ""
                hbTicks = 0
                tryConnect()
                usleep(400_000)
                continue
            }
            hbTicks += 1
            if hbTicks >= 28 {
                hbTicks = 0
                send("KAREL_PING")
            }
            var buf = [UInt8](repeating: 0, count: 256)
            let n = Darwin.read(curFd, &buf, 256)
            if n > 0 {
                lineBuf += String(decoding: buf[0..<n], as: UTF8.self)
                while let nl = lineBuf.firstIndex(of: "\n") {
                    let line = String(lineBuf[..<nl]).trimmingCharacters(in: .whitespacesAndNewlines)
                    lineBuf = String(lineBuf[lineBuf.index(after: nl)...])
                    if line.hasPrefix("EVENT:") { onEvent(line) }
                }
            } else if n < 0 && errno != EAGAIN && errno != EWOULDBLOCK {
                lock.lock(); dropLocked(); lock.unlock()
            } else {
                usleep(35_000)
            }
        }
    }

    func stop() {
        stopping = true
        lock.lock(); dropLocked(); lock.unlock()
    }
}

// MARK: - GitHub Releases Version Check (Read-Only)

private enum AutoUpdater {
    static let version = "2.7.1"
    static let manifestUrl = "https://github.com/svsticky/karel-de-koala/releases/latest/download/version.json"
    static let releasesUrl = "https://github.com/svsticky/karel-de-koala/releases/latest"
    private static let maxManifestBytes = 65536

    static func isValidSemver(_ v: String) -> Bool {
        let parts = v.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 3 else { return false }
        for p in parts {
            if p.isEmpty || p.count > 3 { return false }
            for ch in p.utf8 where ch < 48 || ch > 57 { return false }
        }
        return true
    }

    static func compareVer(_ a: String, _ b: String) -> Int {
        func parts(_ s: String) -> [Int] {
            let trimmed = s.trimmingCharacters(in: CharacterSet(charactersIn: "vV "))
            let arr = trimmed.split(separator: ".").map { Int($0) ?? 0 }
            return [arr.count > 0 ? arr[0] : 0, arr.count > 1 ? arr[1] : 0, arr.count > 2 ? arr[2] : 0]
        }
        let pa = parts(a), pb = parts(b)
        for i in 0..<3 where pa[i] != pb[i] { return pa[i] > pb[i] ? 1 : -1 }
        return 0
    }

    static func sha256Hex(_ data: Data) -> String {
        return SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    private static func fetchManifestData(timeout: TimeInterval) -> Data? {
        guard let url = URL(string: manifestUrl) else { return nil }
        let sem = DispatchSemaphore(value: 0)
        var out: Data? = nil
        var req = URLRequest(url: url, timeoutInterval: timeout)
        req.setValue("KarelDeKoala/\(version)", forHTTPHeaderField: "User-Agent")
        URLSession.shared.dataTask(with: req) { data, resp, _ in
            if let http = resp as? HTTPURLResponse, http.statusCode >= 200 && http.statusCode < 300,
               let d = data, d.count <= maxManifestBytes {
                out = d
            }
            sem.signal()
        }.resume()
        _ = sem.wait(timeout: .now() + timeout + 1.0)
        return out
    }

    static func checkNowAsync(onNewVersion: @escaping (String) -> Void, onStatus: @escaping (String) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            guard let raw = fetchManifestData(timeout: 6.0) else { onStatus("offline"); return }
            guard let man = try? JSONSerialization.jsonObject(with: raw) as? [String: Any] else { onStatus("error"); return }
            let remVer = ((man["version"] as? String) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            guard isValidSemver(remVer) else { onStatus("error"); return }
            if compareVer(remVer, version) <= 0 {
                onStatus("uptodate")
                return
            }
            onNewVersion(remVer)
        }
    }
}

// MARK: - Stage View & Speech Bubble Rendering

private final class KarelStageView: NSView {
    weak var ctrl: KarelController?
    override var isFlipped: Bool { return true }
    override var acceptsFirstResponder: Bool { return true }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.clear.setFill()
        dirtyRect.fill()
        ctrl?.paint(in: self)
    }

    override func mouseDown(with event: NSEvent) {
        if event.modifierFlags.contains(.control) {
            ctrl?.showKarelMenu(event: event, view: self)
            return
        }
        if event.clickCount == 2 { ctrl?.doPet(); return }
        ctrl?.handleMouseDown(event)
    }
    override func rightMouseDown(with event: NSEvent) { ctrl?.showKarelMenu(event: event, view: self) }
    override func mouseDragged(with event: NSEvent) { ctrl?.handleMouseDragged(event) }
    override func mouseUp(with event: NSEvent) { ctrl?.handleMouseUp(event, view: self) }
    override func keyDown(with event: NSEvent) { ctrl?.handleKeyDown(event) }
}

// MARK: - Opt-In macOS Auto-Launch (LaunchAgent StartOnMount)

private enum MacStartupHelper {
    private static let label = "nl.svsticky.karel"

    private static var plistUrl: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/LaunchAgents/\(label).plist")
    }

    private static var installedDirUrl: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support")
        return base.appendingPathComponent("KarelDeKoala")
    }

    static var installedAppUrl: URL {
        return installedDirUrl.appendingPathComponent("Karel.app")
    }

    static func isEnabled() -> Bool {
        return FileManager.default.fileExists(atPath: plistUrl.path)
    }

    private static func runLaunchctl(_ args: [String]) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        p.arguments = args
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        try? p.run()
        p.waitUntilExit()
    }

    @discardableResult
    static func setEnabled(_ on: Bool) -> Bool {
        let fm = FileManager.default
        if on {
            let appDst = installedAppUrl
            let dir = installedDirUrl
            try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
            let curApp = Bundle.main.bundleURL
            if curApp.pathExtension == "app" && curApp.path != appDst.path {
                try? fm.removeItem(at: appDst)
                try? fm.copyItem(at: curApp, to: appDst)
            }
            let exePath = appDst.appendingPathComponent("Contents/MacOS/Karel").path
            guard fm.isExecutableFile(atPath: exePath) else { return false }
            let laDir = plistUrl.deletingLastPathComponent()
            try? fm.createDirectory(at: laDir, withIntermediateDirectories: true)
            // StartOnMount: 0 background processes & 0 MB RAM while USB stick is unplugged!
            let dict: [String: Any] = [
                "Label": label,
                "ProgramArguments": [exePath, "--on-mount"],
                "StartOnMount": true,
                "RunAtLoad": false,
            ]
            if let data = try? PropertyListSerialization.data(fromPropertyList: dict, format: .xml, options: 0) {
                try? data.write(to: plistUrl, options: .atomic)
                runLaunchctl(["unload", plistUrl.path])
                runLaunchctl(["load", "-w", plistUrl.path])
            }
        } else {
            runLaunchctl(["unload", "-w", plistUrl.path])
            try? fm.removeItem(at: plistUrl)
            if Bundle.main.bundleURL.path != installedAppUrl.path {
                try? fm.removeItem(at: installedAppUrl)
            }
        }
        return isEnabled()
    }

    // Remove LaunchAgent, local support directory, and live temp copy using positional shell args (no interpolation).
    static func uninstallFromMac() {
        let fm = FileManager.default
        runLaunchctl(["unload", "-w", plistUrl.path])
        try? fm.removeItem(at: plistUrl)
        let dirPath = installedDirUrl.path
        let liveApp = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("Karel_live.app").path
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/sh")
        p.arguments = ["-c", "sleep 1; rm -rf -- \"$1\" \"$2\" 2>/dev/null || true", "_", dirPath, liveApp]
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        try? p.run()
    }

    @discardableResult
    static func toggle() -> Bool {
        return setEnabled(!isEnabled())
    }
}

// MARK: - Main Karel Controller

private final class KarelController: NSObject, NSApplicationDelegate {
    private let sprites = SpriteBank.loadBundled()
    private let save = SaveStore()
    private let snd = WavSynth()
    private var ser: SerialSync!

    private var rxQueue: [String] = []
    private let rxLock = NSLock()
    private var ipcSock: Int32 = -1

    private var panel: KarelPanel!
    private var stageView: KarelStageView!
    private var statusItem: NSStatusItem!
    private var tickTimer: Timer?

    private var hubWin: NSWindow?
    private var hubStatsTop: NSTextField!
    private var hubXpFill: FlippedBox!
    private var hubStatsBot: NSTextField!
    private var hubActBtns: [NSButton] = []
    private var hubStyleLbl: NSTextField!
    private var hubSkinPop: NSPopUpButton!
    private var hubOutPop: NSPopUpButton!
    private var hubSndBtn: NSButton!
    private var hubAqBtn: NSButton!
    private var hubLangBtn: NSButton!
    private var hubHidBtn: NSButton!
    private var hubUpdBtn: NSButton!
    private var hubUninstBtn: NSButton!
    private var hubUsbLbl: NSTextField!

    private var state = "IDLE", roamMode = "free", bubble = "", diveMode = "quit", climbMsg = ""
    private var updatedFrom = ""
    private var noUpdate = false, startHidden = false, uninstalling = false, updateBusy = false
    private var scale = 3, frameIdx = 0, actTicks = 0, bubbleTicks = 0, discoTicks = 0, hyperTicks = 0
    private var noseClicks = 0, climbStep = 0, closeStep = 0, roamTicks = 0, roamWait = 120, ledgeTicks = 0
    private var wx = 200.0, wy = 200.0, roamTx = 200.0, roamTy = 200.0, jumpY = 0.0, jumpVy = 0.0
    private var flingVx = 0.0, flingVy = 0.0, closeStartY = 0.0, preQuietX = 0.0, preQuietY = 0.0
    private var dragging = false, flying = false, climbing = false, closing = false, autoPaused = false
    private var umbrellaFall = false, trayHidden = false, focusActive = false, hasPreQuiet = false
    private var focusRem = 0
    private var lastUsbBlink = Date.distantPast, lastNoseClick = Date.distantPast
    private var lastAutoSay = Date(), focusLastTick = Date()
    private var coffeeTimes: [Date] = []
    private var dragOff = CGPoint.zero, dragStartScreen = CGPoint.zero
    private var curLedge: CGRect? = nil
    private var particles: [(x: Double, y: Double, vx: Double, vy: Double, life: Int, ch: String, col: NSColor)] = []
    private var konamiBuf: [UInt16] = []
    private let konamiSeq: [UInt16] = [126, 126, 125, 125, 123, 124, 123, 124, 11, 0]
    private var ipcPort: UInt16 = 42421

    private let quotesNL = [
        "Eucalyptus? Of toch een Sticky tosti?",
        "RP2350 SuperMini draait op volle toeren!",
        "Even uitrekken boven je Dock...",
        "Al een git commit gepusht vandaag?",
        "Tip: klik op Karel in de menubalk om te verstoppen!",
        "Zit je code al in main of nog in 'fix_final_v3'?",
        "Ik hou je tabs in de gaten... dat zijn er veel!",
        "Zijn we al klaar met dat practicum?",
        "Even pauze? Mijn oren zijn het ermee eens.",
        "Werkt op mijn RP2350! (En op jouw Mac!)",
        "Vergeet niet af en toe een slokje water te nemen.",
        "Ik ruik verse koffie in het Buys Ballotgebouw!",
        "Geen zorgen, ik eet alleen eucalyptus, geen RAM.",
        "Sssst... ik denk aan een hele grote tosti.",
        "Wist je dat je me door je scherm kunt gooien?",
        "Even rekken en strekken — goede houding!",
        "O(1) knuffelbaarheid, O(n) gezelligheid.",
        "Heeft iemand de semikolon gezien? Gevonden: ;",
        "Stack Overflow is ook maar een soort eucalyptusboom.",
        "Ik ben native Swift. Wat is jouw excuus, Electron?",
        "Zwaai eens terug! Ik zit hier speciaal voor jou.",
        "Even checken: staat je rug recht? Mooi zo!",
        "Karel draait op 100% pure Sticky-energie.",
        "Tijd voor een backflip? Kijk bij Trucjes!",
        "Mijn favoriete datastructuur is een eucalyptus-tree.",
        "Heb je de Konami-code al geprobeerd? Hint: pijltjes...",
        "Klik 7x op mijn neus als je durft...",
        "Nog één tentamen en dan is het weer borreltijd!",
        "Ik beloof dat ik niet op Cmd+Q ga staan.",
        "Geen bugs gevonden vandaag — alleen maar features!"
    ]
    private let quotesEN = [
        "Eucalyptus? Or a Sticky toasted cheese?",
        "RP2350 SuperMini running smoothly!",
        "Zero-Install Sticky companion living on USB!",
        "Did you git commit today?",
        "Tip: click Karel in the menu bar to hide!",
        "Still on branch 'final_fix_really_final'?",
        "That's a lot of open browser tabs you've got there!",
        "Quick stretch break? My ears approve.",
        "Works on my RP2350! (And your Mac!)",
        "Hydration check! Take a sip of water.",
        "Don't worry, I eat eucalyptus, not your RAM.",
        "O(1) cuteness, O(n) good vibes.",
        "Anyone seen a missing semicolon? Found it: ;",
        "Native AppKit, tiny footprint. What's your excuse, Electron?",
        "Try tossing me across your desktop!",
        "My favorite data structure is a eucalyptus tree.",
        "Posture check! Shoulders relaxed, back straight.",
        "Have you tried the Konami code yet?",
        "Boop my nose 7 times if you dare...",
        "No bugs today — only surprise features!",
        "Powered by 100% pure Sticky spirit.",
        "I promise I won't step on Cmd+Q.",
        "Need a break? Check out my 28 tricks!",
        "Chilling above your Dock like a good koala.",
        "Rubber duck debugging? Try koala debugging!",
        "Compiling good vibes... 0 warnings, 0 errors!"
    ]
    private let morningNL = [
        "Goedemorgen! Eerst koffie, dan pas code.",
        "Vroege vogel of doorgehaald? Ik oordeel niet!",
        "Nieuwe dag, nieuwe commits!",
        "Lekker opstarten met een vers blaadje eucalyptus.",
        "Klaar voor college? Ik lift wel mee op je scherm!"
    ]
    private let morningEN = [
        "Good morning! Coffee first, code second.",
        "Early bird or all-nighter? No judgment here!",
        "New day, fresh commits!",
        "Ready for lectures? I'll ride along on your screen!",
        "Nothing beats morning eucalyptus!"
    ]
    private let nightNL = [
        "Nachtelijke code-sessie? Vergeet geen water!",
        "Zzz... Karel programmeert mee in stilte.",
        "Nog één bug en dan lekker slapen?",
        "Na middernacht worden alle bugs dubbel zo sneaky...",
        "Mijn oogjes worden zwaar, en die van jou?",
        "Pro-tip: na een nachtje slapen zie je die bug meteen!"
    ]
    private let nightEN = [
        "Late-night coding session? Stay hydrated!",
        "Zzz... Karel is quietly coding along.",
        "Just one more bug before bed?",
        "Bugs multiply after midnight, you know...",
        "Getting sleepy... maybe save and rest soon?",
        "Tomorrow-you will spot that bug in 2 seconds!"
    ]
    private let fridayNL = [
        "VrijMiBo tijd!! Proost op de week!",
        "Vrijdagmiddag: deployen op eigen risico!",
        "De Vagant roept! Tijd voor een borrel!",
        "Weekend in zicht — lekker gewerkt deze week!",
        "No deploy Friday! Tijd voor een drankje!"
    ]
    private let fridayEN = [
        "Friday drinks time!! Cheers to the week!",
        "No-deploy Friday! Time to unwind!",
        "Weekend incoming — great work this week!",
        "VrijMiBo mode activated!",
        "Close the IDE, it's Friday afternoon!"
    ]
    private let petNL = [
        "Heerlijk! Sticky liefde! +8 XP",
        "Knorrr... precies achter mijn oortjes! +8 XP",
        "Aaaah, beste pauze ooit! +8 XP",
        "Blije koala-geluidjes! +8 XP",
        "Jij bent echt mijn favoriete mens! +8 XP"
    ]
    private let petEN = [
        "Aww! Sticky love! +8 XP",
        "Purrrr... right behind the ears! +8 XP",
        "Best study break ever! +8 XP",
        "Happy koala noises! +8 XP",
        "You're my favorite human! +8 XP"
    ]
    private let feedNL = [
        "Verse eucalyptus! Smullen!",
        "Nom nom nom... lekker knapperig!",
        "Mmm, smaakt bijna net zo goed als een BBG-tosti!",
        "Buikje weer helemaal blij!",
        "Topkwaliteit blaadjes, 5 sterren!"
    ]
    private let feedEN = [
        "Fresh eucalyptus! Yummm!",
        "Nom nom nom... super crunchy!",
        "Almost as good as a Sticky toastie!",
        "Happy tummy, happy koala!",
        "Five-star gourmet leaves!"
    ]
    private let coffeeNL = [
        "Sticky koffie boost! +9 XP",
        "Aah, zwarte goud! +9 XP",
        "Klaar om 1000 regels code te schrijven! +9 XP",
        "Verse kamer-koffie! Lekker sterk! +9 XP",
        "Energie-balk zegt dankjewel! +9 XP"
    ]
    private let coffeeEN = [
        "Sticky espresso boost! +9 XP",
        "Liquid motivation! +9 XP",
        "Ready to ship 1000 lines of code! +9 XP",
        "Freshly brewed! Strong stuff! +9 XP",
        "Energy bar says thank you! +9 XP"
    ]
    private let washNL = [
        "Lekker fris gewassen!",
        "Squeaky clean koala!",
        "Ruik ik weer naar frisse eucalyptus!",
        "Klaar voor de fotoshoot!",
        "Bubbeltjes!! Heerlijk schoon!"
    ]
    private let washEN = [
        "Sparkling clean!",
        "Squeaky clean koala!",
        "Smelling like fresh eucalyptus again!",
        "Ready for my close-up!",
        "Bubbles!! Feeling fresh!"
    ]
    private let tossSoftNL = ["Weee! Zachte landing!", "Hoppa! Even zweven!", "Uitzicht is top hierboven!"]
    private let tossSoftEN = ["Wheee! Soft landing!", "Up, up and away!", "Great view from up here!"]
    private let tossHardNL = ["WOOOOOAAAH!! JETPACK AAN!!", "NAAR DE MAAN!!", "Koala in een baan om de aarde!!"]
    private let tossHardEN = ["WHOOOOAAA!! JETPACK ENGAGED!!", "TO THE MOON!!", "Koala achieved low Earth orbit!!"]

    private static func levelTitle(_ lvl: Int, en: Bool) -> String {
        let nl = [
            "Eerstejaars Koala", "Eucalyptus Fan", "BBG-Bewoner", "Tosti-Kenner", "Git Wizard",
            "Koffie-Connaisseur", "VrijMiBo-Baas", "Kamer-Regular", "RP2350 Meester", "Sticky Legende"
        ]
        let tEn = [
            "Freshman Koala", "Eucalyptus Fan", "BBG Resident", "Toastie Connoisseur", "Git Wizard",
            "Coffee Connoisseur", "Friday Drinks Boss", "Sticky Room Regular", "RP2350 Master", "Sticky Legend"
        ]
        let idx = max(0, min(9, lvl - 1))
        return en ? tEn[idx] : nl[idx]
    }

    private static func outfitQuote(_ item: String, en: Bool) -> String {
        switch item {
        case "scarf": return en ? "Cozy in my Sticky scarf!" : "Lekker warm met mijn Sticky-sjaal!"
        case "stickycap": return en ? "Repping SV Sticky in style!" : "Stijlvol met mijn Sticky-pet!"
        case "hoodie": return en ? "Nothing beats hoodie coding weather." : "Beste programmeer-hoodie ooit!"
        case "headphones": return en ? "Lo-fi beats to debug to..." : "Lo-fi beats om op te debuggen..."
        case "shades": return en ? "Too cool for light mode." : "Te cool voor light mode."
        case "crown": return en ? "Bow to King Karel!" : "Buig voor Koning Karel!"
        case "wizard": return en ? "You're a wizard, Karel!" : "Ik tover je bugs weg... *poef*!"
        case "partyhat": return en ? "Every day is a Sticky party!" : "Elke dag is een feestje!"
        case "beanie": return en ? "Comfy beanie, warm ears!" : "Lekker warme oortjes met deze muts!"
        case "tophat": return en ? "Dressed for the Sticky gala!" : "Helemaal klaar voor het Sticky-gala!"
        case "chef": return en ? "Chef Karel's BBG toasties coming up!" : "Chef Karel bakt de beste BBG-tosti's!"
        case "halo": return en ? "I have NEVER pushed broken code. Honest." : "Ik push NOOIT kapotte code. Echt niet."
        case "bowtie": return en ? "Bowties are cool!" : "Vlinderdas aan: extra professioneel!"
        case "cape": return en ? "Super-Koala to the rescue!" : "Super-Koala schiet te hulp!"
        case "labcoat": return en ? "Stand back, I'm doing computer science!" : "Aan de kant, ik doe wetenschap!"
        case "nerd": return en ? "Ackchyually, it's O(n log n)..." : "Eigenlijk is het O(n log n)..."
        default: return ""
        }
    }

    private func playChirp() {
        snd.play(["chirp", "chirp2", "chirp3", "chirp4"].randomElement() ?? "chirp")
    }

    private func playTrickSound(_ st: String) {
        if st == "MAGIC_TRICK" { snd.play("magic") }
        else if st == "KARATE" || st == "NINJA" { snd.play("karate") }
        else if st == "DJ" || st == "DANCE" || st == "GUITAR" || st == "DRUM" { snd.play("dj") }
        else if st == "BALLOON" || st == "JETPACK" || st == "SKATEBOARD" { snd.play("toss") }
        else { snd.play("trick") }
    }

    private func pickSmartQuote() -> String {
        let en = isEn()
        let eq = save.getEquippedItem()
        if !eq.isEmpty && Double.random(in: 0..<1) < 0.25 {
            let oq = Self.outfitQuote(eq, en: en)
            if !oq.isEmpty { return oq }
        }
        let now = Date()
        let cal = Calendar.current
        let hr = cal.component(.hour, from: now)
        let wd = cal.component(.weekday, from: now)
        if hr >= 0 && hr < 5 { return (en ? nightEN : nightNL).randomElement() ?? "" }
        if wd == 6 && hr >= 16 && Double.random(in: 0..<1) < 0.40 { return (en ? fridayEN : fridayNL).randomElement() ?? "" }
        if hr >= 6 && hr < 11 && Double.random(in: 0..<1) < 0.35 { return (en ? morningEN : morningNL).randomElement() ?? "" }
        return (en ? quotesEN : quotesNL).randomElement() ?? ""
    }

    private func doRandomStyle() {
        let sk = SpriteBank.skinIds.randomElement() ?? "classic"
        let nonEmpty = SpriteBank.outfitIds.filter { !$0.isEmpty }
        let ot = nonEmpty.randomElement() ?? "scarf"
        save.data["skin"] = sk
        save.setEquippedItem(ot)
        save.saveDeferred()
        snd.play("shuffle")
        spawnParticles("*", .systemYellow, 8)
        setAction("SPIN", 20)
        let oq = Self.outfitQuote(ot, en: isEn())
        say(oq.isEmpty ? "\(sk) + \(ot)!" : oq, 55)
        stageView.needsDisplay = true
        refreshHub()
    }

    init(ipcPort: UInt16, noUpdate: Bool = false, updatedFrom: String = "", startHidden: Bool = false) {
        self.ipcPort = ipcPort
        self.noUpdate = noUpdate
        self.updatedFrom = updatedFrom
        self.startHidden = startHidden
        super.init()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        save.load()
        scale = max(2, min(5, save.getInt("karel_scale", 3)))
        roamMode = save.getStr("roam_mode", "free")

        let sz = windowDimensions()
        panel = KarelPanel(
            contentRect: NSRect(x: 100, y: 100, width: sz.width, height: sz.height),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isMovable = false

        stageView = KarelStageView(frame: NSRect(origin: .zero, size: sz))
        stageView.ctrl = self
        panel.contentView = stageView

        let wa = MacWin.topDownWorkArea()
        wx = Double(wa.maxX) - Double(sz.width) - 40.0
        wy = groundY(wa)
        roamTx = wx; roamTy = wy
        applyPanelPosition()
        if startHidden && !save.connected {
            trayHidden = true
            panel.orderOut(nil)
        } else {
            panel.orderFrontRegardless()
        }

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        if let btn = statusItem.button {
            let icon = (sprites.getFrame(state: "IDLE", frameIdx: 0, skin: "classic", item: "scarf").copy() as? NSImage)
                ?? sprites.getFrame(state: "IDLE", frameIdx: 0, skin: "classic", item: "scarf")
            icon.size = NSSize(width: 18, height: 18)
            btn.image = icon
            btn.toolTip = "Karel de Koala"
            btn.action = #selector(onStatusBarClick(_:))
            btn.target = self
            btn.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }

        ser = SerialSync { [weak self] ev in self?.enqueue(ev) }
        startIpc()

        NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.willPowerOffNotification, object: nil, queue: .main
        ) { [weak self] _ in self?.save.save() }

        tickTimer = Timer.scheduledTimer(withTimeInterval: 0.062, repeats: true) { [weak self] _ in
            self?.onTick()
        }
        if !trayHidden {
            triggerClimb(isEn() ? "Karel climbed onto your Mac desktop!" : "Karel klimt je Dock op!")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        if !uninstalling { save.save() }
        ser?.stop()
        if ipcSock >= 0 { Darwin.close(ipcSock) }
    }

    @objc private func onStatusBarClick(_ sender: NSStatusBarButton) {
        let isRight = NSApp.currentEvent?.type == .rightMouseUp || (NSApp.currentEvent?.modifierFlags.contains(.control) ?? false)
        if isRight {
            let menu = buildContextMenu()
            statusItem.menu = menu
            statusItem.button?.performClick(nil)
            statusItem.menu = nil
        } else {
            enqueue("EVENT:TRAY_TOGGLE")
        }
    }

    private func enqueue(_ ev: String) {
        rxLock.lock(); rxQueue.append(ev); rxLock.unlock()
    }

    // Localhost single-instance IPC listener (127.0.0.1 only, 500ms timeout, strict KAREL_* tokens).
    private func startIpc() {
        let s = Darwin.socket(AF_INET, SOCK_STREAM, 0)
        if s < 0 { return }
        var yes: Int32 = 1
        setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = ipcPort.bigEndian
        addr.sin_addr = in_addr(s_addr: UInt32(0x7f000001).bigEndian)
        let bRes = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.bind(s, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        if bRes < 0 || Darwin.listen(s, 8) < 0 { Darwin.close(s); return }
        ipcSock = s
        DispatchQueue.global(qos: .background).async { [weak self] in
            while let self = self, self.ipcSock >= 0 {
                let c = Darwin.accept(self.ipcSock, nil, nil)
                if c < 0 { break }
                var tv = timeval(tv_sec: 0, tv_usec: 500_000)
                setsockopt(c, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))
                var buf = [CChar](repeating: 0, count: 128)
                let n = Darwin.read(c, &buf, 127)
                Darwin.close(c)
                if n > 0 {
                    let msg = String(cString: buf).trimmingCharacters(in: .whitespacesAndNewlines)
                    if msg == "KAREL_TOGGLE" { self.enqueue("EVENT:TOGGLE_KAREL") }
                    else if msg == "KAREL_BOOP" { self.enqueue("EVENT:RST_BOOP") }
                }
            }
        }
    }

    static func trySignalExisting(toggle: Bool, port: UInt16) -> Bool {
        let s = Darwin.socket(AF_INET, SOCK_STREAM, 0)
        if s < 0 { return false }
        defer { Darwin.close(s) }
        var tv = timeval(tv_sec: 0, tv_usec: 500_000)
        setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))
        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        addr.sin_addr = in_addr(s_addr: UInt32(0x7f000001).bigEndian)
        let rc = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.connect(s, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        if rc < 0 { return false }
        let msg = toggle ? "KAREL_TOGGLE\n" : "KAREL_BOOP\n"
        _ = msg.withCString { Darwin.write(s, $0, strlen($0)) }
        return true
    }

    // MARK: Geometry & Helpers

    private func isEn() -> Bool { return save.getStr("language", "nl") == "en" }
    private func px() -> Int { return 32 * scale }
    private func windowDimensions() -> CGSize {
        let p = px()
        return CGSize(width: max(290, p + 146), height: p + 96)
    }
    private func ox() -> Int { return (Int(panel.frame.width) - px()) / 2 }
    private func oy() -> Int { return Int(panel.frame.height) - px() - 16 }
    private func minX(_ wa: CGRect) -> Double { return Double(wa.minX) - Double(ox()) + 6.0 }
    private func maxX(_ wa: CGRect) -> Double { return Double(wa.maxX) - Double(ox() + px()) - 6.0 }
    private func minY(_ wa: CGRect) -> Double { return Double(wa.minY) - Double(oy()) + 6.0 }
    private func groundY(_ wa: CGRect) -> Double { return Double(wa.maxY) - Double(oy() + px()) }

    private func curWork() -> CGRect {
        let cx = wx + Double(panel.frame.width) * 0.5
        let cy = wy + Double(panel.frame.height) * 0.5
        return MacWin.topDownWorkArea(for: MacWin.screenContaining(point: CGPoint(x: cx, y: cy)))
    }

    private func applyPanelPosition(jumpOffset: Double = 0.0) {
        let mh = MacWin.primaryHeight()
        let cocoaY = mh - CGFloat(wy + jumpOffset) - panel.frame.height
        panel.setFrameOrigin(NSPoint(x: wx, y: Double(cocoaY)))
    }

    private func updatePanelSize() {
        let sz = windowDimensions()
        panel.setContentSize(sz)
        stageView.frame = NSRect(origin: .zero, size: sz)
        applyPanelPosition()
    }

    private func say(_ msg: String, _ ticks: Int) { if !autoPaused { bubble = msg; bubbleTicks = ticks } }
    private func setAction(_ st: String, _ ticks: Int) { if !climbing { state = st; actTicks = ticks } }

    private func spawnParticles(_ ch: String, _ col: NSColor, _ count: Int) {
        let cx = Double(panel.frame.width) * 0.5
        let cy = Double(oy())
        for _ in 0..<count {
            particles.append((
                cx + Double.random(in: -24...24),
                cy + Double.random(in: 4...24),
                Double.random(in: -2.25...2.25),
                -1.8 - Double.random(in: 0...3.0),
                Int.random(in: 12...21),
                ch, col
            ))
        }
        if particles.count > 48 { particles.removeFirst(particles.count - 48) }
    }

    private func awardXp(_ amount: Int) {
        let oldLvl = SaveStore.levelFromXp(save.getInt("xp", 0))
        let nextXp = save.getInt("xp", 0) + amount
        save.data["xp"] = nextXp
        let newLvl = SaveStore.levelFromXp(nextXp)
        save.data["level"] = newLvl
        if newLvl > oldLvl {
            snd.play("levelup")
            setAction(Bool.random() ? "BACKFLIP" : "PARTY_HORN", 42)
            spawnParticles("*", .systemYellow, 16)
            say("LEVEL UP! Lv.\(newLvl) — \(Self.levelTitle(newLvl, en: isEn()))!", 80)
        }
    }

    // MARK: Actions (No Coins!)

    func doPet() {
        save.clampStat("happiness", 18, 0, 100)
        save.data["total_pets"] = save.getInt("total_pets", 0) + 1
        setAction(save.getInt("happiness", 85) >= 95 ? "LOVE" : "PET", 28)
        awardXp(8)
        spawnParticles("*", NSColor(red: 1.0, green: 0.48, blue: 0.56, alpha: 1.0), 6)
        snd.play("pet")
        ser.send("EVENT:HEART")
        say((isEn() ? petEN : petNL).randomElement() ?? "", 45)
        save.saveDeferred(); refreshHub()
    }

    private func doFeed() {
        save.clampStat("hunger", 35, 0, 100)
        save.clampStat("happiness", 10, 0, 100)
        setAction("EAT", 28)
        awardXp(7)
        spawnParticles("+", NSColor(red: 0.24, green: 0.81, blue: 0.56, alpha: 1.0), 5)
        snd.play("eat")
        say((isEn() ? feedEN : feedNL).randomElement() ?? "", 45)
        save.saveDeferred(); refreshHub()
    }

    private func doCoffee() {
        save.clampStat("energy", 35, 0, 100)
        save.clampStat("caffeine", 25, 0, 100)
        setAction("COFFEE", 28)
        awardXp(9)
        spawnParticles("~", NSColor(red: 0.96, green: 0.77, blue: 0.32, alpha: 1.0), 6)
        snd.play("coffee")
        let now = Date()
        coffeeTimes.removeAll { now.timeIntervalSince($0) > 120 }
        coffeeTimes.append(now)
        if coffeeTimes.count >= 3 {
            hyperTicks = 95
            ser.send("STATE:HYPER")
            say(isEn() ? "CAFFEINE OVERDOSE! 200 MHz!" : "CAFEINE OVERDOSIS! 200 MHz MODE!", 75)
        } else {
            say((isEn() ? coffeeEN : coffeeNL).randomElement() ?? "", 45)
        }
        save.saveDeferred(); refreshHub()
    }

    private func doWash() {
        save.clampStat("hygiene", 45, 0, 100)
        save.clampStat("happiness", 12, 0, 100)
        setAction("WASH", 30)
        awardXp(8)
        spawnParticles("o", NSColor(red: 0.31, green: 0.76, blue: 0.97, alpha: 1.0), 7)
        snd.play("pet")
        say((isEn() ? washEN : washNL).randomElement() ?? "", 45)
        save.saveDeferred(); refreshHub()
    }

    private func napToggle() {
        if state == "SLEEP" {
            state = "STRETCH"; actTicks = 18
            say(isEn() ? "Good morning! Refreshed!" : "Goedemorgen! Uitgerust!", 40)
        } else {
            state = "SLEEP"; actTicks = 220
            snd.play("dive")
            say("Zzz... Sticky powernap!", 45)
        }
    }

    private func triggerKonami() {
        discoTicks = 115
        save.setEquippedItem("shades")
        setAction("DANCE", 65)
        spawnParticles("*", .systemYellow, 16)
        ser.send("STATE:PARTY")
        snd.play("levelup")
        say(isEn() ? "DISCO BORREL MODE ON!" : "DISCO BORREL MODE AAN!", 80)
        save.save(); refreshHub()
    }

    private func doBoop() {
        awardXp(10)
        snd.play("boop")
        spawnParticles("*", .systemYellow, 10)
        triggerClimb("SuperMini Boop! +10 XP!")
        save.save(); refreshHub()
    }

    private func triggerClimb(_ msg: String) {
        let wa = curWork()
        flying = false; umbrellaFall = false; jumpY = 0
        wy = groundY(wa)
        wx = max(minX(wa), min(maxX(wa), wx))
        climbing = true; climbStep = 0; climbMsg = msg
        roamTx = wx; roamTy = wy; roamWait = 95
        snd.play("climb")
        say(isEn() ? "Climbing up..." : "Even boven de Dock klimmen...", 26)
    }

    private func wakeFromTray() {
        if trayHidden {
            trayHidden = false
            panel.orderFrontRegardless()
        }
        triggerClimb(isEn() ? "I'm back!" : "Daar ben ik weer!")
    }

    private func triggerDive(_ mode: String, customMsg: String? = nil) {
        if closing { return }
        diveMode = mode; closing = true; closeStep = 0
        climbing = false; flying = false; dragging = false; umbrellaFall = false
        jumpY = 0; closeStartY = wy; actTicks = 0
        let msg = customMsg ?? (mode == "tray"
            ? (isEn() ? "Napping in menu bar!" : "Even dutten in de menubalk!")
            : (isEn() ? "See ya! Diving back!" : "Tot ziens! Ik duik weg!"))
        say(msg, 40)
        spawnParticles("*", NSColor(red: 1.0, green: 0.48, blue: 0.56, alpha: 1.0), 4)
        snd.play("dive")
    }

    private func checkForUpdatesManual() {
        if updateBusy { return }
        updateBusy = true
        say(isEn() ? "Checking GitHub for updates..." : "Controleren op updates...", 55)
        AutoUpdater.checkNowAsync(
            onNewVersion: { [weak self] ver in
                DispatchQueue.main.async {
                    guard let s = self else { return }
                    s.updateBusy = false
                    s.say(s.isEn() ? "Update v\(ver) available! Opening GitHub..." : "Update v\(ver) beschikbaar! GitHub openen...", 80)
                    if let url = URL(string: AutoUpdater.releasesUrl) {
                        NSWorkspace.shared.open(url)
                    }
                }
            },
            onStatus: { [weak self] status in
                DispatchQueue.main.async {
                    guard let s = self else { return }
                    s.updateBusy = false
                    if status == "uptodate" { s.say(s.isEn() ? "Up to date (v\(AutoUpdater.version))!" : "Al de nieuwste versie (v\(AutoUpdater.version))!", 65) }
                    else if status == "offline" { s.say(s.isEn() ? "Cannot reach GitHub." : "Kan GitHub niet bereiken.", 60) }
                    else { s.say(s.isEn() ? "Update check failed." : "Update-check mislukt.", 60) }
                }
            })
    }

    private func doUninstallFromMac() {
        let en = isEn()
        let a = NSAlert()
        a.messageText = en ? "Uninstall Karel from this Mac?" : "Karel verwijderen van deze Mac?"
        a.informativeText = en
            ? "Removes auto-start (LaunchAgent), local app copy and local backup from this Mac. Your USB stick will NOT be touched."
            : "Verwijdert auto-start (LaunchAgent), lokale app-kopie en lokale back-up van deze Mac. Je USB-stick blijft gewoon bewaard."
        a.addButton(withTitle: en ? "Uninstall" : "Verwijderen")
        a.addButton(withTitle: en ? "Cancel" : "Annuleren")
        NSApp.activate(ignoringOtherApps: true)
        guard a.runModal() == .alertFirstButtonReturn else { return }
        uninstalling = true
        hubWin?.close()
        MacStartupHelper.uninstallFromMac()
        finalizeQuit()
    }

    private func finalizeQuit() {
        tickTimer?.invalidate()
        ser.send("STATE:BYE")
        if !uninstalling { save.save() }
        ser.stop()
        if ipcSock >= 0 { Darwin.close(ipcSock); ipcSock = -1 }
        NSApp.terminate(nil)
    }

    private func applyAutoQuiet(_ reason: String, _ wa: CGRect) {
        let busy = !reason.isEmpty
        if busy && !autoPaused {
            preQuietX = wx; preQuietY = wy; hasPreQuiet = true
            autoPaused = true; snd.autoQuiet = true
            wx = maxX(wa); wy = minY(wa)
            bubble = ""; bubbleTicks = 0; state = "IDLE"
        } else if !busy && autoPaused {
            autoPaused = false; snd.autoQuiet = false
            if hasPreQuiet {
                wx = max(minX(wa), min(maxX(wa), preQuietX))
                wy = max(minY(wa), min(groundY(wa), preQuietY))
                hasPreQuiet = false
            }
        }
    }

    private func drainEvents() {
        while true {
            rxLock.lock()
            let ev: String? = rxQueue.isEmpty ? nil : rxQueue.removeFirst()
            rxLock.unlock()
            guard let e = ev else { break }
            switch e {
            case "EVENT:PET": doPet()
            case "EVENT:FEED": doFeed()
            case "EVENT:COFFEE": doCoffee()
            case "EVENT:WASH": doWash()
            case "EVENT:MINIGAME": setAction("BACKFLIP", 30); snd.play("boop")
            case "EVENT:DISCO": triggerKonami()
            case "EVENT:RST_BOOP", "EVENT:GIFT":
                if trayHidden { wakeFromTray() }; doBoop()
            case "EVENT:TOGGLE_KAREL":
                if trayHidden { wakeFromTray() } else { triggerDive("quit") }
            case "EVENT:TRAY_TOGGLE":
                if trayHidden { wakeFromTray() } else { triggerDive("tray") }
            case "EVENT:QUIT_NOW":
                if trayHidden { finalizeQuit() } else { triggerDive("quit") }
            case "EVENT:SHUTDOWN_SAVE": save.save()
            default: break
            }
        }
    }

    private func syncHardware() {
        let hr = Calendar.current.component(.hour, from: Date())
        if autoPaused || trayHidden { ser.send("STATE:QUIET") }
        else if focusActive { ser.send("STATE:STUDY") }
        else if discoTicks > 0 || state == "DANCE" { ser.send("STATE:PARTY") }
        else if hyperTicks > 0 { ser.send("STATE:HYPER") }
        else if state == "SLEEP" || (hr >= 23 && actTicks == 0) { ser.send("STATE:SLEEP") }
        else if save.getInt("hunger", 100) < 25 { ser.send("STATE:HUNGRY") }
        else { ser.send("STATE:HAPPY") }
    }

    private func onTick() {
        frameIdx += 1
        let wa = curWork()
        if frameIdx % 16 == 0 {
            if save.getBool("auto_quiet_fullscreen", true) {
                applyAutoQuiet(MacWin.detectFullscreenOrMeeting(ownPid: getpid()), wa)
            } else if autoPaused {
                applyAutoQuiet("", wa)
            }
            let usb = save.pollUsb()
            if usb == "off" {
                hubWin?.close()
                // On macOS, StartOnMount relaunches Karel automatically on next plug-in,
                // so always exit completely on unplug (0 background processes & 0 menu bar icon!).
                if trayHidden {
                    finalizeQuit()
                    return
                } else {
                    triggerDive("quit", customMsg: isEn() ? "USB unplugged! Bye!" : "USB los! Doei!")
                }
            } else if usb == "on" {
                save.load()
                scale = max(2, min(5, save.getInt("karel_scale", 3)))
                updatePanelSize()
                refreshHub()
                if trayHidden { wakeFromTray() }
                else { triggerClimb(isEn() ? "KAREL USB reconnected!" : "KAREL USB herverbonden!") }
            }
        }
        if focusActive && Date().timeIntervalSince(focusLastTick) >= 1.0 {
            focusLastTick = Date()
            focusRem = max(0, focusRem - 1)
            if focusRem == 0 {
                focusActive = false
                awardXp(45)
                setAction("CELEBRATE", 40)
                spawnParticles("*", .systemYellow, 14)
                snd.play("levelup")
                say(isEn() ? "Focus complete! +45 XP!" : "Focus klaar! +45 XP!", 70)
                save.save(); refreshHub()
            }
        }
        drainEvents()

        let lx = minX(wa), rx = maxX(wa), ty = minY(wa), gy = groundY(wa)

        if closing {
            closeStep += 1
            if closeStep <= 9 { wy = closeStartY + (gy - closeStartY) * (Double(closeStep) / 9.0) }
            else if closeStep <= 13 { wy = gy; jumpY = -14.0 * sin(Double(closeStep - 9) * Double.pi / 4.0) }
            else { wy = gy; jumpY = 0 }
            if closeStep >= 27 {
                if diveMode == "tray" { closing = false; trayHidden = true; save.save(); panel.orderOut(nil) }
                else { finalizeQuit(); return }
            }
        } else if climbing {
            climbStep += 1
            if climbStep >= 18 {
                climbing = false; jumpVy = -9.0
                say(climbMsg, 65)
                setAction("WAVE", 28)
            }
        } else if flying {
            wx += flingVx; wy += flingVy
            flingVx *= 0.98; flingVy += 1.45
            if wx < lx { wx = lx; flingVx = -flingVx * 0.65 }
            if wx > rx { wx = rx; flingVx = -flingVx * 0.65 }
            if wy < ty { wy = ty; flingVy = abs(flingVy) * 0.6 }
            if wy >= gy {
                wy = gy
                if abs(flingVy) > 5.0 { flingVy = -flingVy * 0.45 } else { flying = false; state = "IDLE" }
            } else {
                state = "JETPACK"
            }
        } else if umbrellaFall {
            state = "UMBRELLA"
            wy = min(gy, wy + 2.6)
            wx = max(lx, min(rx, wx + sin(Double(frameIdx) * 0.28) * 1.6))
            if wy >= gy - 0.5 { wy = gy; umbrellaFall = false; state = "IDLE"; roamWait = 80 }
        } else {
            stepRoam(wa)
        }

        if jumpY < 0 || jumpVy < 0 {
            jumpY += jumpVy; jumpVy += 1.9
            if jumpY >= 0 { jumpY = 0; jumpVy = 0 }
        }
        if frameIdx % 8 == 0 && Double.random(in: 0..<1) < 0.35 && jumpY == 0
            && (state == "WALK_LEFT" || state == "WALK_RIGHT") { jumpVy = -5.5 }
        if actTicks > 0 { actTicks -= 1; if actTicks == 0 { state = "IDLE" } }
        if discoTicks > 0 {
            discoTicks -= 1
            if discoTicks % 12 == 0 { spawnParticles("*", .systemYellow, 4) }
        }
        if hyperTicks > 0 { hyperTicks -= 1 }
        if bubbleTicks > 0 { bubbleTicks -= 1 }

        if frameIdx % 5 == 0 {
            var i = particles.count - 1
            while i >= 0 {
                particles[i].x += particles[i].vx; particles[i].y += particles[i].vy
                particles[i].vy += 0.35; particles[i].life -= 1
                if particles[i].life <= 0 { particles.remove(at: i) }
                i -= 1
            }
        }
        if frameIdx % 18 == 0 { syncHardware() }

        applyPanelPosition(jumpOffset: jumpY)
        stageView.needsDisplay = true
    }

    private func stepRoam(_ wa: CGRect) {
        if dragging || autoPaused || actTicks > 0 || state == "SLEEP" { return }
        if discoTicks > 0 { state = "DANCE"; return }
        let lx = minX(wa), rx = maxX(wa), ty = minY(wa), gy = groundY(wa)

        if roamMode == "park" {
            wx = max(lx, min(rx, wx)); wy = max(ty, min(gy, wy)); state = "IDLE"; return
        }
        if roamMode == "cursor" {
            let mh = MacWin.primaryHeight()
            let cur = NSEvent.mouseLocation
            let curTopY = Double(mh - cur.y)
            let tx = max(lx, min(rx, Double(cur.x) - Double(panel.frame.width) * 0.5))
            let tyC = max(ty, min(gy, curTopY - Double(oy() + px() / 2)))
            let dx = tx - wx, dy = tyC - wy, dist = hypot(dx, dy)
            if dist > 14 {
                wx += (dx / dist) * 3.4; wy += (dy / dist) * 3.4
                state = dx < 0 ? "WALK_LEFT" : "WALK_RIGHT"
            } else { state = "IDLE" }
            return
        }
        if roamMode == "window" {
            ledgeTicks += 1
            if ledgeTicks % 12 == 1 || curLedge == nil {
                curLedge = MacWin.foregroundLedge(ownPid: getpid(), karelPx: CGFloat(px()), work: wa)
            }
            if let lg = curLedge {
                let tx0 = max(lx, Double(lg.minX) - Double(ox()))
                let tx1 = max(tx0, min(rx, Double(lg.maxX) - Double(ox() + px())))
                roamTy = max(ty, min(gy, Double(lg.minY) - Double(oy() + px())))
                if roamTx < tx0 || roamTx > tx1 { roamTx = Double.random(in: tx0...tx1) }
            } else {
                roamTy = gy
            }
            if (curLedge == nil && wy < gy - 18) || roamTy > wy + 28 {
                umbrellaFall = true; roamWait = 0; roamTicks = 0; actTicks = 0
                say(isEn() ? "Window gone! Sticky umbrella open!" : "Oeps, venster weg! Paraplu open!", 42)
                return
            }
        }
        if roamWait > 0 {
            roamWait -= 1
            if roamWait % 60 == 30 && Double.random(in: 0..<1) < 0.6 {
                let acts = [
                    "BLINK_SMILE", "EARS_WIGGLE", "PEEK", "SIT", "LAPTOP_CODE", "UMBRELLA", "BOW", "WAVE",
                    "SKATEBOARD", "JUGGLE", "MAGIC_TRICK", "DJ", "TELESCOPE", "BALLOON", "MEDITATE", "PIZZA", "NINJA", "KARATE"
                ]
                setAction(acts.randomElement() ?? "IDLE", 32)
            } else { state = "IDLE" }
            return
        }
        let ddx = roamTx - wx, ddy = roamTy - wy, dd = hypot(ddx, ddy)
        roamTicks += 1
        if dd < 10 || roamTicks > 155 {
            roamTicks = 0; roamWait = Int.random(in: 130...280)
            roamTx = Double.random(in: lx...max(lx, rx))
            if roamMode == "window", let lg = curLedge {
                roamTy = max(ty, min(gy, Double(lg.minY) - Double(oy() + px())))
            } else {
                roamTy = gy - (Double.random(in: 0..<1) < 0.35 ? Double.random(in: 0...max(10.0, (gy - ty) / 2.0)) : 0.0)
            }
            if Double.random(in: 0..<1) < 0.14 && Date().timeIntervalSince(lastAutoSay) > 35 && bubbleTicks == 0 {
                lastAutoSay = Date()
                say(pickSmartQuote(), 60)
            }
            return
        }
        wx += (ddx / dd) * 2.2; wy += (ddy / dd) * 2.2
        state = jumpY < -1 ? "JUMP" : (ddx < 0 ? "WALK_LEFT" : "WALK_RIGHT")
    }

    // MARK: Mouse & Keyboard

    func handleMouseDown(_ event: NSEvent) {
        if closing { return }
        panel.makeKey()
        panel.makeFirstResponder(stageView)
        dragging = true; flying = false; umbrellaFall = false; climbing = false; jumpY = 0
        dragOff = stageView.convert(event.locationInWindow, from: nil)
        dragStartScreen = NSEvent.mouseLocation
        lastUsbBlink = Date()
    }

    func handleMouseDragged(_ event: NSEvent) {
        if !dragging { return }
        state = "JETPACK"
        let cur = NSEvent.mouseLocation
        let mh = MacWin.primaryHeight()
        let curTopY = Double(mh - cur.y)
        let vb = MacWin.virtualTopDownBounds()
        wx = max(Double(vb.minX) - Double(ox()) + 4, min(Double(vb.maxX) - Double(ox() + px()) - 4, Double(cur.x) - Double(dragOff.x)))
        wy = max(Double(vb.minY) - Double(oy()) + 4, min(Double(vb.maxY) - Double(oy() + px()), curTopY - Double(dragOff.y)))
        applyPanelPosition()
    }

    func handleMouseUp(_ event: NSEvent, view: NSView) {
        if !dragging { return }
        dragging = false
        let cur = NSEvent.mouseLocation
        let wa = curWork()
        wx = max(minX(wa), min(maxX(wa), wx))
        wy = max(minY(wa), min(groundY(wa), wy))
        let moved = hypot(Double(cur.x - dragStartScreen.x), Double(cur.y - dragStartScreen.y))
        if moved < 6 {
            let pt = view.convert(event.locationInWindow, from: nil)
            let sx = Int(pt.x - CGFloat(ox())) / scale
            let sy = Int(pt.y - CGFloat(oy())) / scale
            if sx >= 13 && sx <= 18 && sy >= 12 && sy <= 16 {
                if Date().timeIntervalSince(lastNoseClick) > 4.5 { noseClicks = 0 }
                lastNoseClick = Date(); noseClicks += 1
                if noseClicks >= 7 {
                    noseClicks = 0; snd.play("sneeze"); setAction("SNEEZE", 24)
                    spawnParticles("*", .white, 10)
                    say(isEn() ? "Achoo! BBG dust!" : "Hatsjoe! BBG stof!", 55)
                }
            } else if actTicks == 0 && state != "SLEEP" {
                say(pickSmartQuote(), 55)
                playChirp()
            }
            return
        }
        let dt = max(0.04, Date().timeIntervalSince(lastUsbBlink))
        let vx = Double(cur.x - dragStartScreen.x) / (dt * 20.0)
        let vy = Double(dragStartScreen.y - cur.y) / (dt * 20.0)
        let spd = hypot(vx, vy)
        if spd > 10.0 {
            flying = true
            flingVx = max(-36.0, min(36.0, vx))
            flingVy = max(-32.0, min(26.0, vy))
            snd.play("toss")
            let tp = spd > 22.0 ? (isEn() ? tossHardEN : tossHardNL) : (isEn() ? tossSoftEN : tossSoftNL)
            say(tp.randomElement() ?? "", 45)
        }
    }

    func handleKeyDown(_ event: NSEvent) {
        let kc = event.keyCode
        let valid: Set<UInt16> = [126, 125, 123, 124, 11, 0]
        if valid.contains(kc) {
            konamiBuf.append(kc)
            if konamiBuf.count > konamiSeq.count { konamiBuf.removeFirst() }
            if konamiBuf == konamiSeq { konamiBuf.removeAll(); triggerKonami() }
        } else { konamiBuf.removeAll() }
    }

    // MARK: Drawing

    func paint(in view: NSView) {
        var renderSt = state
        var clipRows = 32
        if closing {
            if closeStep <= 9 { renderSt = "DIVE_WAVE" }
            else if closeStep <= 13 { renderSt = "JUMP" }
            else {
                renderSt = "DIVE_DOWN"
                clipRows = max(0, Int(round(32.0 * (1.0 - Double(closeStep - 13) / 13.0))))
            }
        } else if climbing {
            renderSt = "CLIMB"
            clipRows = max(2, Int(round(32.0 * min(1.0, Double(climbStep) / 17.0))))
        } else if renderSt == "IDLE" {
            let hr = Calendar.current.component(.hour, from: Date())
            if hyperTicks > 0 { renderSt = "HYPER" }
            else if hr >= 23 && actTicks == 0 { renderSt = "SLEEP" }
            else if save.getInt("hunger", 100) < 25 { renderSt = "HUNGRY" }
        }

        let p = px(), x0 = ox(), y0 = oy()
        if !climbing && !closing {
            let ins = max(8, p / 5)
            NSColor(red: 0.09, green: 0.11, blue: 0.15, alpha: 0.72).setFill()
            NSBezierPath(ovalIn: NSRect(x: x0 + ins, y: y0 + p - 4, width: max(12, p - 2 * ins), height: 7)).fill()
        }

        let img = sprites.getFrame(state: renderSt, frameIdx: frameIdx, skin: save.getStr("skin", "classic"), item: save.getEquippedItem())
        if clipRows > 0, let gc = NSGraphicsContext.current {
            let prevQ = gc.imageInterpolation
            gc.imageInterpolation = .none
            let dy = y0 + (32 - clipRows) * scale
            img.draw(
                in: NSRect(x: x0, y: dy, width: p, height: clipRows * scale),
                from: NSRect(x: 0, y: 32 - clipRows, width: 32, height: clipRows),
                operation: .sourceOver, fraction: 1.0, respectFlipped: true, hints: nil
            )
            gc.imageInterpolation = prevQ
        }

        let pFont = NSFont.monospacedSystemFont(ofSize: 12, weight: .bold)
        for pt in particles {
            (pt.ch as NSString).draw(at: NSPoint(x: pt.x, y: pt.y), withAttributes: [.font: pFont, .foregroundColor: pt.col])
        }

        if bubbleTicks > 0 && !bubble.isEmpty {
            let bFont = NSFont.systemFont(ofSize: 11.5, weight: .semibold)
            let maxW = view.bounds.width - 24
            let attrs: [NSAttributedString.Key: Any] = [.font: bFont, .foregroundColor: NSColor(red: 0.08, green: 0.09, blue: 0.13, alpha: 1.0)]
            let est = (bubble as NSString).boundingRect(with: NSSize(width: maxW - 14, height: 120), options: [.usesLineFragmentOrigin, .usesFontLeading], attributes: attrs)
            let bw = min(view.bounds.width - 10, max(78, ceil(est.width) + 22))
            let bh = ceil(est.height) + 12
            let bx = max(4, (view.bounds.width - bw) / 2.0)
            let by = max(4, CGFloat(y0) - bh - 10)
            let tx = view.bounds.width / 2.0

            let boxRect = NSRect(x: bx, y: by, width: bw, height: bh)
            NSColor(red: 0.97, green: 0.98, blue: 1.0, alpha: 0.98).setFill()
            NSBezierPath(roundedRect: boxRect, xRadius: 5, yRadius: 5).fill()
            NSColor(red: 0.77, green: 0.12, blue: 0.15, alpha: 1.0).setFill()
            NSBezierPath(rect: NSRect(x: bx, y: by, width: 4, height: bh)).fill()
            NSColor(red: 0.77, green: 0.12, blue: 0.15, alpha: 1.0).setStroke()
            let border = NSBezierPath(roundedRect: boxRect, xRadius: 5, yRadius: 5)
            border.lineWidth = 1.5; border.stroke()

            let tail = NSBezierPath()
            tail.move(to: NSPoint(x: tx - 5, y: by + bh))
            tail.line(to: NSPoint(x: tx + 5, y: by + bh))
            tail.line(to: NSPoint(x: tx, y: by + bh + 6))
            tail.close()
            NSColor(red: 0.97, green: 0.98, blue: 1.0, alpha: 0.98).setFill(); tail.fill()
            NSColor(red: 0.77, green: 0.12, blue: 0.15, alpha: 1.0).setStroke(); tail.lineWidth = 1.5; tail.stroke()

            (bubble as NSString).draw(in: NSRect(x: bx + 9, y: by + 6, width: bw - 14, height: bh - 10), withAttributes: attrs)
        }
    }

    // MARK: Context Menu

    private func addMenuItem(_ menu: NSMenu, _ title: String, _ action: @escaping () -> Void) {
        let item = MenuClosureItem(title: title, block: action)
        menu.addItem(item)
    }

    func showKarelMenu(event: NSEvent, view: NSView) {
        let menu = buildContextMenu()
        NSMenu.popUpContextMenu(menu, with: event, for: view)
    }

    private func buildContextMenu() -> NSMenu {
        let m = NSMenu()
        let en = isEn()
        addMenuItem(m, "Open Sticky Hub") { [weak self] in self?.openHub() }
        m.addItem(.separator())
        addMenuItem(m, en ? "Feed Eucalyptus" : "Voer Eucalyptus") { [weak self] in self?.doFeed() }
        addMenuItem(m, en ? "Sticky Coffee" : "Sticky Koffie") { [weak self] in self?.doCoffee() }
        addMenuItem(m, en ? "Pet Karel" : "Aai Karel") { [weak self] in self?.doPet() }
        addMenuItem(m, en ? "Wash Karel" : "Was Karel") { [weak self] in self?.doWash() }
        addMenuItem(m, en ? "Powernap ON/OFF" : "Powernap AAN/UIT") { [weak self] in self?.napToggle() }
        addMenuItem(m, focusActive ? "Stop Focus" : (en ? "Focus Mode (25m)" : "Focus Modus (25m)")) { [weak self] in self?.toggleFocus() }
        m.addItem(.separator())

        let tricks: [(String, String, String)] = [
            ("Backflip!", "BACKFLIP", "Wooo! Koala Backflip!!"),
            ("360° Spin", "SPIN", "Swoosh!"),
            ("Jetpack", "JETPACK", "Naar de BBG-maan!"),
            ("Peek", "PEEK", "Psst... zie je me?"),
            ("Laptop Coding", "LAPTOP_CODE", "git commit -m 'fix'"),
            ("Debug Magnifier", "MAGNIFY", "Zoekende naar bugs..."),
            ("Paper Plane", "PAPER_PLANE", "Zoooef!"),
            ("Sticky Umbrella", "UMBRELLA", "Typisch Nederlands weer!"),
            ("Ear Wiggle", "EARS_WIGGLE", "*Wiebel wiebel*"),
            ("Hug Plush", "HUG_PLUSH", "Sticky liefde!"),
            ("Eucalyptus Hug", "EUCALYPTUS_HUG", "Favoriete tak!"),
            ("Party Horn", "PARTY_HORN", "VrijMiBo tijd!"),
            ("Polite Bow", "BOW", "Dankjewel!"),
            ("Wave Hello", "WAVE", "Hoi!!"),
            ("Guitar Solo", "GUITAR", "8-bit riff!"),
            ("Drums", "DRUM", "Ba-dum-tss!"),
            ("Flex Muscles", "FLEX", "RP2350 spierkracht!"),
            ("Dance", "DANCE", "De Vagant boogie!"),
            ("Skateboard", "SKATEBOARD", "Kickflip over de taakbalk!"),
            ("Karate Chop", "KARATE", "Hi-yaa!!"),
            ("Magic Trick", "MAGIC_TRICK", "Abraka-koala!"),
            ("Juggle", "JUGGLE", "Kijk, zonder handen!"),
            ("Pizza Time", "PIZZA", "Kwartiertje pizza!"),
            ("DJ Set", "DJ", "Drop de bass!!"),
            ("Stargazing", "TELESCOPE", "Sterren kijken..."),
            ("Sticky Balloon", "BALLOON", "Ik zweeef!"),
            ("Ninja Mode", "NINJA", "Poef! Onzichtbaar!"),
            ("Zen Meditate", "MEDITATE", "Ommm... 0 bugs...")
        ]
        let tmItem = NSMenuItem(title: en ? "Tricks & Animations" : "Trucjes & Animaties", action: nil, keyEquivalent: "")
        let tm = NSMenu()
        for t in tricks { addMenuItem(tm, t.0) { [weak self] in self?.setAction(t.1, 42); self?.say(t.2, 48); self?.playTrickSound(t.1) } }
        tmItem.submenu = tm; m.addItem(tmItem)

        let rmItem = NSMenuItem(title: en ? "Roam Mode" : "Loopgedrag", action: nil, keyEquivalent: "")
        let rm = NSMenu()
        addMenuItem(rm, en ? "Free Roam" : "Heel Scherm") { [weak self] in self?.setRoam("free") }
        addMenuItem(rm, en ? "Active Window" : "Op Actief Venster") { [weak self] in self?.setRoam("window") }
        addMenuItem(rm, en ? "Follow Mouse" : "Volg Muis") { [weak self] in self?.setRoam("cursor") }
        addMenuItem(rm, en ? "Stay Put" : "Blijf Zitten") { [weak self] in self?.setRoam("park") }
        rmItem.submenu = rm; m.addItem(rmItem)

        let smItem = NSMenuItem(title: en ? "Size" : "Grootte", action: nil, keyEquivalent: "")
        let sm = NSMenu()
        for sc in 2...5 { addMenuItem(sm, "\(sc)x (\(sc * 32)px)") { [weak self] in self?.setScale(sc) } }
        smItem.submenu = sm; m.addItem(smItem)

        addMenuItem(m, en ? "Sound On/Off" : "Geluid Aan/Uit") { [weak self] in guard let s = self else { return }; s.snd.muted.toggle(); s.refreshHub() }
        addMenuItem(m, en ? "Auto-Quiet Fullscreen" : "Auto-Stil Fullscreen") { [weak self] in
            guard let s = self else { return }
            s.save.data["auto_quiet_fullscreen"] = !s.save.getBool("auto_quiet_fullscreen", true)
            s.save.save(); s.refreshHub()
        }
        addMenuItem(m, en ? "Language: NL / EN" : "Taal: NL / EN") { [weak self] in
            guard let s = self else { return }
            s.save.data["language"] = s.isEn() ? "nl" : "en"; s.save.save(); s.refreshHub()
        }
        let stOn = MacStartupHelper.isEnabled()
        addMenuItem(m, (stOn ? "✓ " : "") + (en ? "Auto-open on USB plug-in" : "Automatisch openen bij USB")) { [weak self] in
            let on = MacStartupHelper.toggle()
            let msg = on
                ? (self?.isEn() == true ? "Auto-open on USB ON!" : "Automatisch openen bij USB AAN!")
                : (self?.isEn() == true ? "Auto-open on USB OFF" : "Automatisch openen bij USB UIT")
            self?.say(msg, 45)
            self?.refreshHub()
        }
        addMenuItem(m, en ? "Check for updates" : "Check op updates") { [weak self] in self?.checkForUpdatesManual() }
        addMenuItem(m, en ? "Uninstall from this Mac..." : "Verwijder van deze Mac...") { [weak self] in self?.doUninstallFromMac() }
        m.addItem(.separator())
        addMenuItem(m, trayHidden ? (en ? "Wake Karel" : "Wek Karel") : (en ? "Hide Behind Dock" : "Verberg achter Dock")) { [weak self] in self?.enqueue("EVENT:TRAY_TOGGLE") }
        addMenuItem(m, en ? "Dive & Quit" : "Duik weg & Sluit") { [weak self] in self?.enqueue("EVENT:QUIT_NOW") }
        return m
    }

    private func setRoam(_ mode: String) { roamMode = mode; save.data["roam_mode"] = mode; save.save(); umbrellaFall = false; say(mode, 30) }
    private func setScale(_ sc: Int) {
        scale = max(2, min(5, sc))
        save.data["karel_scale"] = scale
        updatePanelSize()
        wy = min(groundY(curWork()), wy)
        save.save()
    }

    private func toggleFocus() {
        focusActive.toggle()
        if focusActive { focusRem = 25 * 60; focusLastTick = Date(); say("Focus: 25m!", 45) }
        else { say(isEn() ? "Focus stopped." : "Focus gestopt.", 35) }
        refreshHub()
    }

    // MARK: Dark-Mode Sticky Hub

    private func makeFlatBtn(_ title: String, frame: NSRect, bg: NSColor, block: @escaping () -> Void) -> ActionButton {
        let b = ActionButton(frame: frame, block: block)
        b.isBordered = false; b.wantsLayer = true
        b.layer?.backgroundColor = bg.cgColor
        b.layer?.cornerRadius = 6
        b.setStyledTitle(title, size: 12.5)
        return b
    }

    private func openHub() {
        if trayHidden { wakeFromTray() }
        if let h = hubWin { h.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); refreshHub(); return }

        let W: CGFloat = 560, P: CGFloat = 18, Win = W - 2 * P, gap: CGFloat = 10
        let w = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: W, height: 396),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered, defer: false
        )
        hubWin = w
        w.title = "Karel de Koala — Sticky Hub"
        w.isReleasedWhenClosed = false
        w.appearance = NSAppearance(named: .darkAqua)
        w.backgroundColor = NSColor(red: 0.07, green: 0.08, blue: 0.11, alpha: 1.0)
        w.level = .floating
        w.center()

        let root = FlippedView(frame: NSRect(x: 0, y: 0, width: W, height: 396))
        w.contentView = root

        let hdr = FlippedBox(frame: NSRect(x: 0, y: 0, width: W, height: 44), fill: NSColor(red: 0.77, green: 0.12, blue: 0.15, alpha: 1.0))
        let hdrLbl = NSTextField(labelWithString: "  KAREL DE KOALA  •  STICKY RP2350   v\(AutoUpdater.version)")
        hdrLbl.frame = NSRect(x: 12, y: 11, width: W - 24, height: 22)
        hdrLbl.font = .boldSystemFont(ofSize: 14); hdrLbl.textColor = .white
        hdr.addSubview(hdrLbl); root.addSubview(hdr)

        var y: CGFloat = 58
        let cardBg = NSColor(red: 0.11, green: 0.12, blue: 0.16, alpha: 1.0)
        let statsCard = FlippedBox(frame: NSRect(x: P, y: y, width: Win, height: 88), fill: cardBg, radius: 8)
        hubStatsTop = NSTextField(labelWithString: "")
        hubStatsTop.frame = NSRect(x: 14, y: 10, width: Win - 28, height: 22)
        hubStatsTop.font = .boldSystemFont(ofSize: 13.5)
        hubStatsTop.textColor = NSColor(red: 0.95, green: 0.96, blue: 0.98, alpha: 1.0)

        let xpTrack = FlippedBox(frame: NSRect(x: 14, y: 39, width: Win - 28, height: 8), fill: NSColor(red: 0.06, green: 0.07, blue: 0.09, alpha: 1.0), radius: 4)
        hubXpFill = FlippedBox(frame: NSRect(x: 0, y: 0, width: 0, height: 8), fill: NSColor(red: 0.96, green: 0.77, blue: 0.32, alpha: 1.0), radius: 4)
        xpTrack.addSubview(hubXpFill)

        hubStatsBot = NSTextField(labelWithString: "")
        hubStatsBot.frame = NSRect(x: 14, y: 54, width: Win - 28, height: 22)
        hubStatsBot.font = .monospacedSystemFont(ofSize: 11.5, weight: .regular)
        hubStatsBot.textColor = NSColor(red: 0.69, green: 0.72, blue: 0.79, alpha: 1.0)
        statsCard.addSubview(hubStatsTop); statsCard.addSubview(xpTrack); statsCard.addSubview(hubStatsBot)
        root.addSubview(statsCard)

        y += 102
        let bw = (Win - 2 * gap) / 3, bh: CGFloat = 38
        let cols: [NSColor] = [
            NSColor(red: 0.15, green: 0.45, blue: 0.30, alpha: 1.0),
            NSColor(red: 0.45, green: 0.29, blue: 0.23, alpha: 1.0),
            NSColor(red: 0.66, green: 0.13, blue: 0.35, alpha: 1.0),
            NSColor(red: 0.05, green: 0.45, blue: 0.52, alpha: 1.0),
            NSColor(red: 0.23, green: 0.29, blue: 0.35, alpha: 1.0),
            NSColor(red: 0.16, green: 0.19, blue: 0.26, alpha: 1.0)
        ]
        let acts: [() -> Void] = [
            { [weak self] in self?.doFeed() }, { [weak self] in self?.doCoffee() },
            { [weak self] in self?.doPet() }, { [weak self] in self?.doWash() },
            { [weak self] in self?.napToggle() }, { [weak self] in self?.toggleFocus() }
        ]
        hubActBtns.removeAll()
        for i in 0..<6 {
            let b = makeFlatBtn("", frame: NSRect(x: P + CGFloat(i % 3) * (bw + gap), y: y + CGFloat(i / 3) * (bh + gap), width: bw, height: bh), bg: cols[i], block: acts[i])
            hubActBtns.append(b); root.addSubview(b)
        }

        y += 2 * bh + gap + 14
        let styleCard = FlippedBox(frame: NSRect(x: P, y: y, width: Win, height: 48), fill: cardBg, radius: 8)
        hubStyleLbl = NSTextField(labelWithString: "Stijl:")
        hubStyleLbl.frame = NSRect(x: 12, y: 14, width: 48, height: 20)
        hubStyleLbl.font = .boldSystemFont(ofSize: 12.5)
        hubStyleLbl.textColor = NSColor(red: 0.60, green: 0.64, blue: 0.72, alpha: 1.0)

        let rndW: CGFloat = 78
        let pkw = (Win - 84 - rndW) / 2
        hubSkinPop = NSPopUpButton(frame: NSRect(x: 64, y: 10, width: pkw, height: 28), pullsDown: false)
        hubSkinPop.addItems(withTitles: SpriteBank.skinIds)
        hubSkinPop.target = self; hubSkinPop.action = #selector(onSkinPick(_:))

        hubOutPop = NSPopUpButton(frame: NSRect(x: 70 + pkw, y: 10, width: pkw, height: 28), pullsDown: false)
        hubOutPop.addItems(withTitles: SpriteBank.outfitIds.map { $0.isEmpty ? "(geen)" : $0 })
        hubOutPop.target = self; hubOutPop.action = #selector(onOutPick(_:))

        let rndBtn = makeFlatBtn("Random", frame: NSRect(x: 76 + 2 * pkw, y: 10, width: Win - 86 - 2 * pkw, height: 28), bg: NSColor(red: 0.52, green: 0.16, blue: 0.42, alpha: 1.0)) { [weak self] in
            self?.doRandomStyle()
        }
        styleCard.addSubview(hubStyleLbl); styleCard.addSubview(hubSkinPop); styleCard.addSubview(hubOutPop); styleCard.addSubview(rndBtn)
        root.addSubview(styleCard)

        y += 60
        let darkBtn = NSColor(red: 0.16, green: 0.19, blue: 0.26, alpha: 1.0)
        hubSndBtn = makeFlatBtn("", frame: NSRect(x: P, y: y, width: bw, height: 36), bg: darkBtn) { [weak self] in
            guard let s = self else { return }; s.snd.muted.toggle(); s.refreshHub()
        }
        hubAqBtn = makeFlatBtn("", frame: NSRect(x: P + bw + gap, y: y, width: bw, height: 36), bg: darkBtn) { [weak self] in
            guard let s = self else { return }
            s.save.data["auto_quiet_fullscreen"] = !s.save.getBool("auto_quiet_fullscreen", true)
            s.save.save(); s.refreshHub()
        }
        hubLangBtn = makeFlatBtn("NL / EN", frame: NSRect(x: P + 2 * (bw + gap), y: y, width: Win - 2 * (bw + gap), height: 36), bg: darkBtn) { [weak self] in
            guard let s = self else { return }
            s.save.data["language"] = s.isEn() ? "nl" : "en"; s.save.save(); s.refreshHub()
        }
        root.addSubview(hubSndBtn); root.addSubview(hubAqBtn); root.addSubview(hubLangBtn)

        y += 48
        hubHidBtn = makeFlatBtn("", frame: NSRect(x: P, y: y, width: Win, height: 32), bg: NSColor(red: 0.08, green: 0.41, blue: 0.62, alpha: 1.0)) { [weak self] in
            guard let s = self else { return }
            let on = MacStartupHelper.toggle()
            s.say(on ? (s.isEn() ? "Auto-open on USB ON!" : "Automatisch openen bij USB AAN!") : (s.isEn() ? "Auto-open on USB OFF" : "Automatisch openen bij USB UIT"), 55)
            s.refreshHub()
        }
        y += 38
        let halfW = (Win - gap) / 2
        hubUpdBtn = makeFlatBtn("", frame: NSRect(x: P, y: y, width: halfW, height: 30), bg: darkBtn) { [weak self] in
            self?.checkForUpdatesManual()
        }
        hubUninstBtn = makeFlatBtn("", frame: NSRect(x: P + halfW + gap, y: y, width: Win - halfW - gap, height: 30), bg: NSColor(red: 0.47, green: 0.14, blue: 0.17, alpha: 1.0)) { [weak self] in
            self?.doUninstallFromMac()
        }
        hubUsbLbl = NSTextField(labelWithString: "")
        hubUsbLbl.frame = NSRect(x: P, y: y + 38, width: Win, height: 24)
        hubUsbLbl.font = .monospacedSystemFont(ofSize: 11.5, weight: .regular)
        hubUsbLbl.textColor = NSColor(red: 0.24, green: 0.81, blue: 0.56, alpha: 1.0)
        root.addSubview(hubHidBtn); root.addSubview(hubUpdBtn); root.addSubview(hubUninstBtn); root.addSubview(hubUsbLbl)

        refreshHub()
        w.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc private func onSkinPick(_ sender: NSPopUpButton) {
        let idx = sender.indexOfSelectedItem
        if idx >= 0 && idx < SpriteBank.skinIds.count {
            save.data["skin"] = SpriteBank.skinIds[idx]; save.save(); stageView.needsDisplay = true
        }
    }

    @objc private func onOutPick(_ sender: NSPopUpButton) {
        let idx = sender.indexOfSelectedItem
        if idx >= 0 && idx < SpriteBank.outfitIds.count {
            save.setEquippedItem(SpriteBank.outfitIds[idx]); save.save(); stageView.needsDisplay = true
        }
    }

    private func refreshHub() {
        guard let w = hubWin, let root = w.contentView else { return }
        let en = isEn()
        let xp = save.getInt("xp", 0)
        let lvl = SaveStore.levelFromXp(xp)
        let prevXp = SaveStore.xpForNextLevel(lvl - 1)
        let nextXp = SaveStore.xpForNextLevel(lvl)
        let pct = max(0.0, min(1.0, Double(xp - prevXp) / Double(max(1, nextXp - prevXp))))

        hubStatsTop.stringValue = "Lv.\(lvl)  \(Self.levelTitle(lvl, en: en))   ·   \(xp) / \(nextXp) XP"
        if let track = hubXpFill.superview {
            var f = hubXpFill.frame
            f.size.width = max(xp > 0 ? 4 : 0, round(track.frame.width * CGFloat(pct)))
            hubXpFill.frame = f
        }
        hubStatsBot.stringValue = String(
            format: "%@: %d%%  ·  %@: %d%%  ·  %@: %d%%  ·  %@: %d%%",
            en ? "Hungry" : "Honger", save.getInt("hunger", 80),
            en ? "Happy" : "Blij", save.getInt("happiness", 85),
            en ? "Energy" : "Energie", save.getInt("energy", 85),
            en ? "Clean" : "Fris", save.getInt("hygiene", 90)
        )

        let actLbls = [en ? "Feed" : "Voer", en ? "Coffee" : "Koffie", en ? "Pet" : "Aai", en ? "Wash" : "Was", "Powernap", focusActive ? "Stop Focus" : "Focus 25m"]
        for (i, b) in hubActBtns.enumerated() {
            (b as? ActionButton)?.setStyledTitle(actLbls[i], size: 12.5)
        }
        hubStyleLbl.stringValue = en ? "Style:" : "Stijl:"
        if let si = SpriteBank.skinIds.firstIndex(of: save.getStr("skin", "classic")) { hubSkinPop.selectItem(at: si) }
        if let oi = SpriteBank.outfitIds.firstIndex(of: save.getEquippedItem()) { hubOutPop.selectItem(at: oi) }
        hubOutPop.item(at: SpriteBank.outfitIds.count - 1)?.title = en ? "(none)" : "(geen)"

        (hubSndBtn as? ActionButton)?.setStyledTitle((en ? "Sound: " : "Geluid: ") + (snd.muted ? (en ? "OFF" : "UIT") : (en ? "ON" : "AAN")), size: 12)
        let aq = save.getBool("auto_quiet_fullscreen", true)
        (hubAqBtn as? ActionButton)?.setStyledTitle((en ? "Quiet: " : "Auto-Stil: ") + (aq ? (en ? "ON" : "AAN") : (en ? "OFF" : "UIT")), size: 12)

        hubHidBtn.isHidden = false
        let stOn = MacStartupHelper.isEnabled()
        (hubHidBtn as? ActionButton)?.setStyledTitle(
            stOn ? (en ? "Auto-open on USB plug-in: ON" : "Automatisch openen bij USB: AAN")
                 : (en ? "Auto-open on USB plug-in: OFF" : "Automatisch openen bij USB: UIT"),
            size: 11.5
        )
        (hubUpdBtn as? ActionButton)?.setStyledTitle(en ? "Check for updates" : "Check op updates", size: 11.5)
        (hubUninstBtn as? ActionButton)?.setStyledTitle(en ? "Uninstall from Mac" : "Verwijder van Mac", size: 11.5)
        let usbTxt = save.connected ? "● USB: KAREL (\(save.driveRoot))" : (en ? "○ Memory mode (no USB)" : "○ Geheugen-modus (geen USB)")
        let serTxt = ser.portName.isEmpty ? (en ? "Serial: waiting..." : "Serial: wachten...") : "RP2350 @ \(ser.portName)"
        hubUsbLbl.stringValue = "\(usbTxt)   |   \(serTxt)"

        var uFrame = hubUsbLbl.frame
        uFrame.origin.y = hubUpdBtn.frame.maxY + 8
        hubUsbLbl.frame = uFrame
        let targetH = uFrame.maxY + 14
        if abs(root.frame.height - targetH) > 1 {
            root.setFrameSize(NSSize(width: root.frame.width, height: targetH))
            w.setContentSize(NSSize(width: w.contentView!.frame.width, height: targetH))
        }
    }
}

// MARK: - AppKit Helper Subclasses

private final class KarelPanel: NSPanel {
    override var canBecomeKey: Bool { return true }
}

private final class FlippedView: NSView {
    override var isFlipped: Bool { return true }
}

private final class FlippedBox: NSView {
    override var isFlipped: Bool { return true }
    init(frame: NSRect, fill: NSColor, radius: CGFloat = 0) {
        super.init(frame: frame)
        wantsLayer = true
        layer?.backgroundColor = fill.cgColor
        if radius > 0 { layer?.cornerRadius = radius }
    }
    required init?(coder: NSCoder) { fatalError() }
}

private final class ActionButton: NSButton {
    private var block: () -> Void
    init(frame: NSRect, block: @escaping () -> Void) {
        self.block = block
        super.init(frame: frame)
        target = self
        action = #selector(fired)
    }
    required init?(coder: NSCoder) { fatalError() }
    @objc private func fired() { block() }
    func setStyledTitle(_ text: String, size: CGFloat) {
        let p = NSMutableParagraphStyle(); p.alignment = .center
        attributedTitle = NSAttributedString(string: text, attributes: [
            .font: NSFont.boldSystemFont(ofSize: size),
            .foregroundColor: NSColor.white,
            .paragraphStyle: p
        ])
    }
}

private final class MenuClosureItem: NSMenuItem {
    private let block: () -> Void
    init(title: String, block: @escaping () -> Void) {
        self.block = block
        super.init(title: title, action: #selector(fired), keyEquivalent: "")
        target = self
    }
    required init(coder: NSCoder) { fatalError() }
    @objc private func fired() { block() }
}

private func showAutoStartPrompt() {
    let s = SaveStore(); s.load()
    let en = s.getStr("language", "nl") == "en"
    let bank = SpriteBank.loadBundled()
    let ico = bank.getFrame(state: "IDLE", frameIdx: 0, skin: s.getStr("skin", "classic"), item: s.getEquippedItem())
    let app = NSApplication.shared
    app.setActivationPolicy(.regular)
    app.activate(ignoringOtherApps: true)
    while true {
        let a = NSAlert()
        a.messageText = en ? "Auto-start Karel on USB plug-in?" : "Karel voortaan automatisch starten?"
        a.informativeText = en
            ? "Should Karel automatically appear whenever you plug in this USB stick? (You can change this anytime in the menu.)"
            : "Wil je dat Karel voortaan vanzelf verschijnt zodra je deze USB-stick inplugt? (Altijd weer uit te zetten in het menu.)"
        a.icon = ico
        a.addButton(withTitle: en ? "Yes, auto-start" : "Ja, automatisch")
        a.addButton(withTitle: en ? "No, just start" : "Nee, alleen nu")
        a.addButton(withTitle: "README")
        let r = a.runModal()
        if r == .alertFirstButtonReturn {
            MacStartupHelper.setEnabled(true)
            app.setActivationPolicy(.accessory)
            return
        }
        if r == .alertSecondButtonReturn {
            app.setActivationPolicy(.accessory)
            return
        }
        let localReadme = s.driveRoot.isEmpty ? "" : (s.driveRoot + "/README.md")
        if !localReadme.isEmpty && FileManager.default.fileExists(atPath: localReadme) {
            NSWorkspace.shared.open(URL(fileURLWithPath: localReadme))
        } else if let url = URL(string: "https://github.com/svsticky/karel-de-koala#readme") {
            NSWorkspace.shared.open(url)
        }
    }
}

// MARK: - Entry Point

var selfTest = false
var toggle = false
var noUpdate = false
var askPrompt = false
var noAsk = false
var startHidden = false
var onMount = false
var noShadow = false
var updatedFrom = ""
var ipcPort: UInt16 = 42421
for a in CommandLine.arguments.dropFirst() {
    if a == "--self-test" { selfTest = true }
    else if a == "--no-update" { noUpdate = true }
    else if a == "--ask" { askPrompt = true }
    else if a == "--no-ask" { noAsk = true }
    else if a == "--no-shadow" { noShadow = true }
    else if a == "--on-mount" { onMount = true; noAsk = true }
    else if a == "--tray" || a == "--hidden" { startHidden = true }
    else if a == "--toggle" || a == "-t" || a == "t" { toggle = true }
    else if a.hasPrefix("--updated-from=") { updatedFrom = String(a.dropFirst(15)) }
    else if a.hasPrefix("--ipc-port="), let p = UInt16(a.dropFirst(11)), p > 0 { ipcPort = p }
}

if selfTest {
    let bank = SpriteBank.loadBundled()
    let img = bank.getFrame(state: "IDLE", frameIdx: 0, skin: "sticky", item: "crown")
    if img.size.width != 32 || img.size.height != 32 || bank.states.isEmpty
        || AutoUpdater.compareVer("2.7.2", AutoUpdater.version) <= 0
        || !AutoUpdater.isValidSemver(AutoUpdater.version)
        || AutoUpdater.isValidSemver("2.7.0;id") {
        fputs("SELF_TEST_FAILED sprites=\(bank.states.count)\n", stderr)
        exit(1)
    }
    _ = WavSynth()
    let s = SaveStore(); s.load()
    print("SELF_TEST_OK version=\(AutoUpdater.version) states=\(bank.states.count) xp=\(s.getInt("xp", 0)) has_synth=true")
    exit(0)
}

if onMount {
    var found = false
    for _ in 0..<12 {
        if !SaveStore.findUsbDrive().isEmpty { found = true; break }
        usleep(100_000)
    }
    if !found { exit(0) }
}

if KarelController.trySignalExisting(toggle: toggle, port: ipcPort) { exit(0) }
if toggle { exit(0) }

let curBundle = Bundle.main.bundleURL
if !noShadow && curBundle.pathExtension == "app" && curBundle.path.hasPrefix("/Volumes/") {
    let fm = FileManager.default
    let liveApp = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("Karel_live.app")
    let liveExe = liveApp.appendingPathComponent("Contents/MacOS/Karel")
    do {
        try? fm.removeItem(at: liveApp)
        try fm.copyItem(at: curBundle, to: liveApp)
        if fm.isExecutableFile(atPath: liveExe.path) {
            var passArgs = ["--no-shadow"]
            for a in CommandLine.arguments.dropFirst() where a != "--no-shadow" && !a.hasPrefix("-psn_") {
                passArgs.append(a)
            }
            let p = Process()
            p.executableURL = liveExe
            p.arguments = passArgs
            try p.run()
            exit(0)
        }
    } catch { }
}

let shouldAsk = askPrompt || (!noAsk && !startHidden && updatedFrom.isEmpty && !MacStartupHelper.isEnabled())
if shouldAsk { showAutoStartPrompt() }

private let app = NSApplication.shared
app.setActivationPolicy(.accessory)
private let ctrl = KarelController(ipcPort: ipcPort, noUpdate: noUpdate, updatedFrom: updatedFrom, startHidden: startHidden)
app.delegate = ctrl
withExtendedLifetime(ctrl) { app.run() }
