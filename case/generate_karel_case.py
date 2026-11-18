"""
Parametric, watertight 3D-printable STL generator for Karel de Koala (RP2350 SuperMini).

Designed for bare RP2350 SuperMini PCBs without pinheaders (18.0 x 23.3-23.5 mm PCB with
overhanging USB-C, 1x left BOOT button + right-side GP16 WS2812 RGB LED, no onboard RST button):
- Two-piece snap-fit enclosure (Bottom Base + Top Lid), zero screws/glue, zero supports needed.
- Reinforced monolithic keychain eyelet (4.6 mm hole) integrated into the Bottom Base.
- Front USB-C overmold-friendly cutout (12.2 x 5.3 mm, 1.9 mm cradle accommodating ~1.7-1.95 mm USB-C overhang).
- Official SV Sticky compact wordmark ("st!cky") debossed -0.6 mm into Top Lid exterior,
  with the Koala exclamation-mark outline broadened slightly for crisp 0.4 mm FDM slicing.
- Definitive two-piece snap-fit STL set in case/stl/:
  1. karel_rp2350_bottom.stl: rigid snap-fit tray with 6 compliant crush ribs and monolithic keychain eyelet.
  2. karel_rp2350_top.stl: completely smooth, hole-free exterior with the "-0.6 mm st!cky"
     wordmark symmetrically centered on the top lid (X=0.0, Y=+0.2 mm). An internal
     translucent light-funnel sits centered directly above the GP16 WS2812 RGB LED
     while the onboard BOOT switch stays safely shielded underneath.
  3. karel_rp2350_complete_plate.stl: both pieces oriented flat side-by-side ready to slice & test-print.
"""

from __future__ import annotations

import argparse
from collections import Counter
import math
import os
import struct
from typing import Callable, Iterable

import numpy as np
from matplotlib.path import Path
from PIL import Image
from scipy import ndimage
from scipy.spatial import Delaunay


# ---------------------------------------------------------------------------
# Board & Case Parameters (all dimensions in mm)
# ---------------------------------------------------------------------------
# Assembled orientation:
#   X: width   (-X left, +X right)
#   Y: length  (-Y USB-C front, +Y keychain back)
#   Z: height  (0 = bottom outer face, +Z = top outer face)
PCB_W = 18.30                 # Inner bay width  (fits 18.0 mm PCB + 0.15 mm/side, 18.00 mm at crush ribs!)
PCB_L = 23.75                 # Inner bay length (fits 23.46-23.50 mm PCB + rear crush ribs @ 23.60 mm)
PCB_THICK = 1.6               # Standard FR4 PCB thickness

BOTTOM_FLOOR = 1.4            # Solid base floor thickness
UNDER_PCB_CLEAR = 1.2         # Underside relief pocket below PCB (QFN/pads clearance)
OVER_PCB_CLEAR = 3.7          # Clearance above PCB top (USB-C shell ~3.2 mm + margin)
TOP_ROOF = 1.5                # Lid roof thickness (leaves 0.9 mm behind -0.6 mm logo)

Z_PCB_BOT = BOTTOM_FLOOR + UNDER_PCB_CLEAR       # 2.6 mm
Z_PCB_TOP = Z_PCB_BOT + PCB_THICK                # 4.2 mm
Z_SPLIT = 5.2                                    # Exterior split seam height
Z_RIM_TOP = 7.6                                  # Top of Base inner snap rim
Z_LID_CEILING = Z_PCB_TOP + OVER_PCB_CLEAR       # 7.9 mm
Z_TOTAL = Z_LID_CEILING + TOP_ROOF               # 9.4 mm

WALL_TOTAL = 2.35                                # Total side wall thickness
OUTER_W = PCB_W + 2 * WALL_TOTAL                 # 23.0 mm
HALF_W = OUTER_W / 2.0                           # 11.5 mm

Y_PCB_FRONT = -PCB_L / 2.0                       # -11.875 mm (front FR4 shoulder edge of PCB)
Y_PCB_BACK = PCB_L / 2.0                         # +11.875 mm (back edge of PCB)
FRONT_WALL = 1.925                               # Flush with ~1.7-1.95 mm USB-C shell overhang
BACK_WALL = 2.325
Y_FRONT = Y_PCB_FRONT - FRONT_WALL               # -13.8 mm
Y_BACK = Y_PCB_BACK + BACK_WALL                  # +14.2 mm (case body length = 28.0 mm)

R_OUTER = 2.0                                    # Outer corner radius
USBC_CUT_W = 12.2                                # Wide USB-C slot for cable boots
USBC_Z_BOT = 2.6                                 # Lower USB-C cradle shelf top
USBC_Z_TOP = 8.0                                 # Top bridge over USB-C starts here

# Snap-fit geometry (telescoping rim + tight 45-degree 2-step chamfered detent)
RIM_THICK = 1.10                                 # Base upper rim wall thickness
SNAP_GAP = 0.14                                  # Snug radial slip clearance between Base rim & Lid skirt
SKIRT_THICK = WALL_TOTAL - RIM_THICK - SNAP_GAP  # 1.11 mm outer Lid skirt
X_BAY = PCB_W / 2.0                              # 9.15 mm (9.00 mm at crush ribs)
X_RIM = X_BAY + RIM_THICK                        # 10.25 mm
X_SKIRT_IN = X_RIM + SNAP_GAP                    # 10.39 mm
CRUSH_RIB = 0.15                                 # Compliant inner crush-rib depth for zero XY rattle
SNAP_Y_HALF = 4.2                                # Snap latch span [-4.2, +4.2]

# Keychain lug on Bottom Base (monolithic, full base height down to split seam)
KEYCHAIN_Y_TIP = 21.8                            # Lug tip Y (+14.3 -> +21.8 = 7.5 mm extension)
KEYCHAIN_R = 5.4                                 # Tip rounding radius (width 10.8 mm)
KEYCHAIN_HOLE_Y = 17.6
KEYCHAIN_HOLE_R = 2.3                            # 4.6 mm hole diameter -> 3.1 mm radial wall

# Exact RP2350 SuperMini coordinates measured from top-down PCB photo (USB-C top, 5V left):
# - Photo width = 18.00 mm (2.54 mm pad pitch), black PCB length = 23.31 mm
# - Only ONE physical tactile button (`BOOT` on left of photo); NO onboard `RST` button
# - `WS2812 RGB LED` (`16` = GP16) on right side below USB-C / LDO
# Note: PCB sits inside case with USB-C at -Y (front) & keychain at +Y (back), i.e. 180-deg XY rotation
# from USB-C-up photo -> `case_x = (pcb_w / 2) - x_from_5v_left`, `case_y = Y_PCB_FRONT + 0.2 + y_from_usb_pcb`.
BUTTON_LAYOUT_SUPERMINI = {
    "pcb_w": 18.0,
    "pcb_l": 23.46,
    "pcb_y_offset": 0.10,            # Held forward against Y_PCB_FRONT by rear crush ribs
    "boot": (5.00, 9.40, 2.15),      # (x_from_5v_left, y_from_pcb_usb_edge, radius -> D=4.3 mm oval dome access)
    "led":  (13.85, 10.95, 1.45),    # (x_from_5v_left, y_from_pcb_usb_edge, radius -> D=2.9 mm GP16 RGB LED)
}

LOGO_DEBOSS_DEPTH = 0.6                          # -0.6 mm engraved Sticky wordmark


# ---------------------------------------------------------------------------
# 2D Primitives & Marching Squares for the Official Sticky SVG/PNG Logo
# ---------------------------------------------------------------------------

def circle_poly(cx: float, cy: float, r: float, n: int = 36, ccw: bool = True) -> np.ndarray:
    ang = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    if not ccw:
        ang = -ang
    return np.column_stack([cx + r * np.cos(ang), cy + r * np.sin(ang)])


def rect_poly(x0: float, x1: float, y0: float, y1: float, ccw: bool = True) -> np.ndarray:
    pts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)
    return pts if ccw else pts[::-1]


def rounded_rect_poly(
    x0: float, x1: float, y0: float, y1: float, r: float, n_arc: int = 8, ccw: bool = True
) -> np.ndarray:
    r = min(r, 0.49 * (x1 - x0), 0.49 * (y1 - y0))
    if r <= 1e-6:
        return rect_poly(x0, x1, y0, y1, ccw=ccw)
    corners = [
        (x1 - r, y1 - r, 0.0, 0.5 * np.pi),
        (x0 + r, y1 - r, 0.5 * np.pi, np.pi),
        (x0 + r, y0 + r, np.pi, 1.5 * np.pi),
        (x1 - r, y0 + r, 1.5 * np.pi, 2.0 * np.pi),
    ]
    pts = []
    for cx, cy, a0, a1 in corners:
        for a in np.linspace(a0, a1, n_arc + 1):
            pts.append([cx + r * np.cos(a), cy + r * np.sin(a)])
    arr = np.array(pts, dtype=float)
    # Remove consecutive nearly-equal vertices
    keep = [0]
    for i in range(1, len(arr)):
        if np.linalg.norm(arr[i] - arr[keep[-1]]) > 1e-6:
            keep.append(i)
    if len(keep) > 1 and np.linalg.norm(arr[keep[0]] - arr[keep[-1]]) < 1e-6:
        keep.pop()
    arr = arr[keep]
    return arr if ccw else arr[::-1]


def build_sticky_plaque_2d_mesh(
    logo_path: str,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    target_w_mm: float,
    step_mm: float = 0.10,
    rotate_ccw_deg: int = 0,
    min_gap_mm: float = 0.42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[float, float]]]:
    """
    Create a strictly planar, conforming 2D triangle mesh filling [x0, x1] x [y0, y1]
    at exact step_mm boundary spacing, partitioned sub-pixel accurately along the Sticky
    logo SDF=0 contour via cell-by-cell Marching Squares polygon splitting.

    Returns:
        pts: (V, 2) vertex positions
        tris: (T, 3) CCW triangle vertex indices
        in_logo: (T,) bool mask indicating whether each triangle is inside the debossed logo
        border_pts: ordered perimeter vertex coordinates matching [x0, x1] x [y0, y1]
    """
    nx = int(round((x1 - x0) / step_mm))
    ny = int(round((y1 - y0) / step_mm))
    xs = np.linspace(x0, x1, nx + 1)
    ys = np.linspace(y0, y1, ny + 1)

    # Render logo onto fine padded mask so bolding never clips outer tips
    fine_res = 0.025  # 40 px/mm for super crisp curve distance field
    src = Image.open(logo_path).convert("RGBA")
    logo_w_px = int(round(target_w_mm / fine_res))
    logo_h_px = int(round(logo_w_px * src.height / src.width))
    resized = src.resize((logo_w_px, logo_h_px), Image.Resampling.LANCZOS)
    rarr = np.pad(np.array(resized), ((20, 20), (20, 20), (0, 0)), mode="constant", constant_values=0)
    alpha = rarr[..., 3] > 100

    # Thicken letters + outline cleanly for 0.40 mm FDM nozzle while guarding gaps >= min_gap_mm
    is_red = alpha & (rarr[..., 0].astype(int) - rarr[..., 1].astype(int) > 60)
    is_black = alpha & (~is_red)
    lbl_b, nb = ndimage.label(is_black)
    lbl_r, nr = ndimage.label(is_red)
    comps: list[tuple[str, np.ndarray]] = (
        [("black", lbl_b == i) for i in range(1, nb + 1)]
        + [("red", lbl_r == i) for i in range(1, nr + 1)]
    )
    cur = [c.copy() for _, c in comps]
    types = [t for t, _ in comps]
    red_idxs = [idx for idx, t in enumerate(types) if t == "red"]
    outline_idx = max(red_idxs, key=lambda idx: cur[idx].sum())

    s3 = np.ones((3, 3), dtype=bool)
    for step in range(5):
        for idx in range(len(cur)):
            limit = 5 if idx == outline_idx else (4 if types[idx] == "black" else 0)
            if step >= limit:
                continue
            others = np.zeros_like(alpha)
            for j, m in enumerate(cur):
                if j != idx:
                    others |= m
            dist_other = ndimage.distance_transform_edt(~others) * fine_res
            cand = ndimage.binary_dilation(cur[idx], structure=s3)
            cur[idx] |= cand & (dist_other >= min_gap_mm)

    others_ex_out = np.zeros_like(alpha)
    for j, m in enumerate(cur):
        if j != outline_idx:
            others_ex_out |= m
    dist_out_other = ndimage.distance_transform_edt(~others_ex_out) * fine_res
    yy, xx = np.ogrid[-4:5, -4:5]
    closed_out = ndimage.binary_closing(cur[outline_idx], structure=(xx * xx + yy * yy) <= 16)
    cur[outline_idx] |= closed_out & (dist_out_other >= min_gap_mm)

    mask_bold = np.zeros_like(alpha)
    for m in cur:
        mask_bold |= m
    ry, rx = np.where(mask_bold)
    mask_crop = mask_bold[max(0, ry.min() - 2) : ry.max() + 3, max(0, rx.min() - 2) : rx.max() + 3]
    if rotate_ccw_deg:
        mask_crop = np.rot90(mask_crop, k=(rotate_ccw_deg // 90) % 4)

    # Flip rows vertically so image top maps to +Y when viewed upright
    combined = mask_crop[::-1, :]

    # Embed combined bitmap centered inside full plaque fine canvas
    plaque_w = x1 - x0
    plaque_h = y1 - y0
    cw = int(round(plaque_w / fine_res)) + 8
    ch = int(round(plaque_h / fine_res)) + 8
    canvas = np.zeros((ch, cw), dtype=bool)
    oy_px = (ch - combined.shape[0]) // 2
    ox_px = (cw - combined.shape[1]) // 2
    y_slice_dst = slice(max(0, oy_px), min(ch, oy_px + combined.shape[0]))
    x_slice_dst = slice(max(0, ox_px), min(cw, ox_px + combined.shape[1]))
    y_slice_src = slice(max(0, -oy_px), combined.shape[0] - max(0, oy_px + combined.shape[0] - ch))
    x_slice_src = slice(max(0, -ox_px), combined.shape[1] - max(0, ox_px + combined.shape[1] - cw))
    canvas[y_slice_dst, x_slice_dst] = combined[y_slice_src, x_slice_src]

    fine_sdf = (ndimage.distance_transform_edt(canvas) - ndimage.distance_transform_edt(~canvas)) * fine_res
    fine_sdf = ndimage.gaussian_filter(fine_sdf, sigma=0.75)

    # Bilinearly sample fine_sdf onto the (ny+1, nx+1) plaque grid vertices
    cx_grid = (xs - x0) / fine_res + (cw - plaque_w / fine_res) * 0.5
    cy_grid = (ys - y0) / fine_res + (ch - plaque_h / fine_res) * 0.5
    phi = ndimage.map_coordinates(
        fine_sdf,
        np.meshgrid(cy_grid, cx_grid, indexing="ij"),
        order=1,
        mode="constant",
        cval=-1.0,
    )
    # Clamp perimeter strictly outside logo & clamp near-zero corners away from 0 to avoid degenerate cuts
    phi[0, :] = np.minimum(phi[0, :], -0.05)
    phi[-1, :] = np.minimum(phi[-1, :], -0.05)
    phi[:, 0] = np.minimum(phi[:, 0], -0.05)
    phi[:, -1] = np.minimum(phi[:, -1], -0.05)
    near0 = np.abs(phi) < 1e-3
    phi[near0] = np.where(phi[near0] >= 0, 1e-3, -1e-3)

    verts: list[list[float]] = []
    corner_vid = np.full((ny + 1, nx + 1), -1, dtype=int)
    for r in range(ny + 1):
        for c in range(nx + 1):
            corner_vid[r, c] = len(verts)
            verts.append([float(xs[c]), float(ys[r])])

    edge_vid: dict[tuple[int, int, int, int], int] = {}

    def get_cut(r0: int, c0: int, r1: int, c1: int) -> int:
        key = (r0, c0, r1, c1) if (r0, c0) <= (r1, c1) else (r1, c1, r0, c0)
        if key not in edge_vid:
            v0, v1 = float(phi[r0, c0]), float(phi[r1, c1])
            t = max(0.02, min(0.98, v0 / (v0 - v1)))
            x = float(xs[c0] + t * (xs[c1] - xs[c0]))
            y = float(ys[r0] + t * (ys[r1] - ys[r0]))
            edge_vid[key] = len(verts)
            verts.append([x, y])
        return edge_vid[key]

    tris: list[tuple[int, int, int]] = []
    tri_logo: list[bool] = []

    def emit_poly(v_ids: list[int], is_inside: bool, fan_pt: tuple[float, float] | None = None) -> None:
        # Check convex or nearly-convex polygon fan; if >4 verts with potential reflex saddle corner, fan from center
        if len(v_ids) <= 4:
            for k in range(1, len(v_ids) - 1):
                tris.append((v_ids[0], v_ids[k], v_ids[k + 1]))
                tri_logo.append(is_inside)
        else:
            if fan_pt is None:
                coords = np.array([verts[i] for i in v_ids], dtype=float)
                cx, cy = coords.mean(axis=0)
            else:
                cx, cy = fan_pt
            cid = len(verts)
            verts.append([float(cx), float(cy)])
            m = len(v_ids)
            for k in range(m):
                tris.append((cid, v_ids[k], v_ids[(k + 1) % m]))
                tri_logo.append(is_inside)

    for r in range(ny):
        for c in range(nx):
            # Cell corners CCW: 0=(r,c) BL, 1=(r,c+1) BR, 2=(r+1,c+1) TR, 3=(r+1,c) TL
            c_rc = [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]
            s = [bool(phi[rr, cc] > 0.0) for rr, cc in c_rc]
            n_in = sum(s)
            if n_in == 0:
                v = [int(corner_vid[rr, cc]) for rr, cc in c_rc]
                emit_poly(v, False)
                continue
            if n_in == 4:
                v = [int(corner_vid[rr, cc]) for rr, cc in c_rc]
                emit_poly(v, True)
                continue

            # Walk cell perimeter inserting cut vertices where sign flips
            # Corner indices + edge cut nodes in strict CCW ring order
            ring: list[tuple[int, bool]] = []
            for side in range(4):
                rA, cA = c_rc[side]
                rB, cB = c_rc[(side + 1) % 4]
                ring.append((int(corner_vid[rA, cA]), s[side]))
                if s[side] != s[(side + 1) % 4]:
                    cut = get_cut(rA, cA, rB, cB)
                    # Cut point marks boundary
                    ring.append((cut, None))  # type: ignore[arg-type]

            cuts = [idx for idx, (_, flag) in enumerate(ring) if flag is None]
            if len(cuts) == 2:
                i0, i1 = cuts[0], cuts[1]
                arc_a = [ring[k % len(ring)][0] for k in range(i0, i1 + 1)]
                arc_b = [ring[k % len(ring)][0] for k in range(i1, i0 + len(ring) + 1)]
                # Determine which arc holds an inside corner
                in_a = any(bool(ring[k % len(ring)][1]) for k in range(i0 + 1, i1))
                emit_poly(arc_a, in_a)
                emit_poly(arc_b, not in_a)
            elif len(cuts) == 4:
                # True saddle: 2 opposite corners in vs 2 out. Disambiguate via cell midpoint sign
                v_mid = 0.25 * float(phi[r, c] + phi[r, c + 1] + phi[r + 1, c + 1] + phi[r + 1, c])
                center_in = v_mid > 0.0
                # Corners NOT matching center_in form two separated triangles across opposite corners;
                # center polygon connects all 4 cut vertices + the 2 center-matching corners!
                center_poly: list[int] = []
                for idx, (vid, flag) in enumerate(ring):
                    if flag is None:
                        center_poly.append(vid)
                    elif flag == center_in:
                        center_poly.append(vid)
                    else:
                        # Isolated triangle (prev_cut, corner, next_cut)
                        prev_cut = ring[(idx - 1) % len(ring)][0]
                        next_cut = ring[(idx + 1) % len(ring)][0]
                        emit_poly([prev_cut, vid, next_cut], flag)
                cell_mid = (0.5 * float(xs[c] + xs[c + 1]), 0.5 * float(ys[r] + ys[r + 1]))
                emit_poly(center_poly, center_in, fan_pt=cell_mid)

    # Ordered CCW perimeter coordinates along [x0, x1] x [y0, y1]
    border_pts: list[tuple[float, float]] = []
    for c in range(nx):
        border_pts.append((float(xs[c]), float(ys[0])))
    for r in range(ny):
        border_pts.append((float(xs[nx]), float(ys[r])))
    for c in range(nx, 0, -1):
        border_pts.append((float(xs[c]), float(ys[ny])))
    for r in range(ny, 0, -1):
        border_pts.append((float(xs[0]), float(ys[r])))

    return (
        np.array(verts, dtype=float),
        np.array(tris, dtype=int),
        np.array(tri_logo, dtype=bool),
        border_pts,
    )


# ---------------------------------------------------------------------------
# Conforming Delaunay + Interval-XOR Exact Watertight 2.5D Extruder
# ---------------------------------------------------------------------------

def subdivide_loop_max_edge(loop: np.ndarray, max_edge: float) -> np.ndarray:
    out = []
    n = len(loop)
    for i in range(n):
        a = loop[i]
        b = loop[(i + 1) % n]
        dist = float(np.linalg.norm(b - a))
        steps = max(1, int(math.ceil(dist / max_edge)))
        for s in range(steps):
            out.append(a + (s / steps) * (b - a))
    return np.array(out, dtype=float)


def merge_intervals(iv: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not iv:
        return []
    iv = sorted((min(a, b), max(a, b)) for a, b in iv if abs(b - a) > 1e-6)
    merged = [iv[0]]
    for a, b in iv[1:]:
        if a <= merged[-1][1] + 1e-6:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def extrude_interval_solid(
    pts: np.ndarray,
    simplices: np.ndarray,
    z_profile_fn: Callable[[np.ndarray], list[list[tuple[float, float]]]],
) -> np.ndarray:
    """
    Given a 2D conforming Delaunay mesh and a function returning sorted disjoint [z_lo, z_hi]
    solid intervals per triangle centroid, emit a 100% watertight outward-normal triangle array (N, 3, 3).
    """
    centroids = (pts[simplices[:, 0]] + pts[simplices[:, 1]] + pts[simplices[:, 2]]) / 3.0
    tri_ivs = [merge_intervals(iv) for iv in z_profile_fn(centroids)]

    # Build directed half-edge neighbor map for wall stitching
    edge_owners: dict[tuple[int, int], tuple[int, tuple[int, int]]] = {}
    tris_out: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    def add_tri(a: np.ndarray, b: np.ndarray, c: np.ndarray):
        tris_out.append((a, b, c))

    # 1. Top (+Z) and Bottom (-Z) horizontal caps per triangle
    for ti, (i0, i1, i2) in enumerate(simplices):
        ivs = tri_ivs[ti]
        x0, y0 = pts[i0]
        x1, y1 = pts[i1]
        x2, y2 = pts[i2]
        for zlo, zhi in ivs:
            # Top cap (+Z normal, CCW when viewed from +Z)
            add_tri(
                np.array([x0, y0, zhi]),
                np.array([x1, y1, zhi]),
                np.array([x2, y2, zhi]),
            )
            # Bottom cap (-Z normal, CW when viewed from +Z)
            add_tri(
                np.array([x0, y0, zlo]),
                np.array([x2, y2, zlo]),
                np.array([x1, y1, zlo]),
            )

        # Register directed edges
        for u, v in [(i0, i1), (i1, i2), (i2, i0)]:
            edge_owners[(u, v)] = (ti, (u, v))

    # Precompute ALL Z breakpoints touching each 2D vertex so adjacent walls never form vertical T-junctions
    vertex_zs: dict[int, set[float]] = {}
    for ti, (i0, i1, i2) in enumerate(simplices):
        for zlo, zhi in tri_ivs[ti]:
            for v_idx in (i0, i1, i2):
                s = vertex_zs.setdefault(v_idx, set())
                s.add(zlo)
                s.add(zhi)

    # 2. Stitch vertical walls wherever adjacent triangles differ in solid Z intervals
    visited_pairs: set[tuple[int, int]] = set()
    for (u, v), (ti, _) in edge_owners.items():
        ek = (min(u, v), max(u, v))
        if ek in visited_pairs:
            continue
        visited_pairs.add(ek)

        iv_left = tri_ivs[ti]
        twin = edge_owners.get((v, u))
        iv_right = tri_ivs[twin[0]] if twin is not None else []

        if iv_left == iv_right:
            continue

        # Collect bit-exact Z breakpoints strictly per vertex (u vs v) so neighbors never create vertical T-junctions
        raw_zs = sorted(a_or_b for a, b in (iv_left + iv_right) for a_or_b in (a, b))
        zs: list[float] = []
        for z in raw_zs:
            if not zs or z - zs[-1] > 1e-9:
                zs.append(z)
        if len(zs) < 2:
            continue

        xu, yu = pts[u]
        xv, yv = pts[v]
        uz_all = sorted(vertex_zs.get(u, ()))
        vz_all = sorted(vertex_zs.get(v, ()))

        def in_iv(zmid: float, ivs: list[tuple[float, float]]) -> bool:
            return any(a - 1e-7 <= zmid <= b + 1e-7 for a, b in ivs)

        for k in range(len(zs) - 1):
            za, zb = zs[k], zs[k + 1]
            if zb - za <= 1e-6:
                continue
            zm = 0.5 * (za + zb)
            s_left = in_iv(zm, iv_left)
            s_right = in_iv(zm, iv_right)
            if s_left == s_right:
                continue

            # Exact Z sequences strictly on u-edge and strictly on v-edge within [za, zb]
            uz_sub = [za] + [z for z in uz_all if za + 1e-9 < z < zb - 1e-9] + [zb]
            vz_sub = [za] + [z for z in vz_all if za + 1e-9 < z < zb - 1e-9] + [zb]

            # Two-pointer monotone zipper across [za, zb] with guaranteed positive triangle area
            i_u, i_v = 0, 0
            while i_u < len(uz_sub) - 1 or i_v < len(vz_sub) - 1:
                p_u = np.array([xu, yu, uz_sub[i_u]])
                p_v = np.array([xv, yv, vz_sub[i_v]])
                if i_v == len(vz_sub) - 1 or (i_u < len(uz_sub) - 1 and uz_sub[i_u + 1] <= vz_sub[i_v + 1]):
                    p_n = np.array([xu, yu, uz_sub[i_u + 1]])
                    i_u += 1
                    if s_left:
                        add_tri(p_u, p_v, p_n)
                    else:
                        add_tri(p_v, p_u, p_n)
                else:
                    p_n = np.array([xv, yv, vz_sub[i_v + 1]])
                    i_v += 1
                    if s_left:
                        add_tri(p_u, p_v, p_n)
                    else:
                        add_tri(p_v, p_u, p_n)

    return np.array(tris_out, dtype=np.float32)


# ---------------------------------------------------------------------------
# STL Binary I/O & Manifold / Watertight Verifier
# ---------------------------------------------------------------------------

def write_binary_stl(path: str, tris: np.ndarray, header_note: str = "Karel de Koala SV Sticky RP2350 Case") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Compute face normals cleanly in float64 before writing
    t64 = tris.astype(np.float64)
    nrm = np.cross(t64[:, 1] - t64[:, 0], t64[:, 2] - t64[:, 0])
    lens = np.linalg.norm(nrm, axis=1, keepdims=True)
    lens[lens == 0] = 1.0
    nrm = (nrm / lens).astype(np.float32)

    hdr = header_note.encode("ascii", errors="ignore")[:80].ljust(80, b"\0")
    rec_dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("v0", "<f4", (3,)),
        ("v1", "<f4", (3,)),
        ("v2", "<f4", (3,)),
        ("attr", "<u2"),
    ])
    buf = np.empty(len(tris), dtype=rec_dtype)
    buf["normal"] = nrm
    buf["v0"] = tris[:, 0]
    buf["v1"] = tris[:, 1]
    buf["v2"] = tris[:, 2]
    buf["attr"] = 0

    with open(path, "wb") as f:
        f.write(hdr)
        f.write(struct.pack("<I", len(tris)))
        f.write(buf.tobytes())


def verify_stl(path: str) -> dict[str, object]:
    with open(path, "rb") as f:
        raw = f.read()
    count = struct.unpack("<I", raw[80:84])[0]
    expected_len = 84 + 50 * count
    if len(raw) != expected_len:
        raise AssertionError(f"{path}: binary size mismatch ({len(raw)} vs {expected_len})")

    rec_dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("v0", "<f4", (3,)),
        ("v1", "<f4", (3,)),
        ("v2", "<f4", (3,)),
        ("attr", "<u2"),
    ])
    arr = np.frombuffer(raw[84:], dtype=rec_dtype)
    tris = np.stack([arr["v0"], arr["v1"], arr["v2"]], axis=1).astype(np.float64)

    if not np.all(np.isfinite(tris)):
        raise AssertionError(f"{path}: non-finite vertices")

    areas = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    min_area = float(areas.min())
    if min_area <= 1e-10:
        raise AssertionError(f"{path}: degenerate triangle with area={min_area}")

    # Signed volume check: sum (v0 . (v1 x v2)) / 6
    vol = float(np.sum(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])))) / 6.0

    # Topological closed 2-manifold edge check using quantized coordinates
    q = np.round(tris, 4)
    directed: Counter[tuple[tuple[float, ...], tuple[float, ...]]] = Counter()
    undirected: Counter[tuple[tuple[float, ...], tuple[float, ...]]] = Counter()
    for t in q:
        v = [tuple(map(float, t[0])), tuple(map(float, t[1])), tuple(map(float, t[2]))]
        for a, b in ((v[0], v[1]), (v[1], v[2]), (v[2], v[0])):
            directed[(a, b)] += 1
            undirected[(a, b) if a <= b else (b, a)] += 1

    non_manifold_undir = sum(1 for c in undirected.values() if c != 2)
    unmatched_dir = sum(1 for (a, b), c in directed.items() if c != 1 or directed.get((b, a), 0) != 1)

    bmin = tris.reshape(-1, 3).min(axis=0)
    bmax = tris.reshape(-1, 3).max(axis=0)
    dims = bmax - bmin
    stats = {
        "file": os.path.basename(path),
        "triangles": count,
        "dims_mm": tuple(round(float(x), 2) for x in dims),
        "bbox_min": tuple(round(float(x), 2) for x in bmin),
        "bbox_max": tuple(round(float(x), 2) for x in bmax),
        "volume_cm3": round(vol / 1000.0, 3),
        "min_tri_area_mm2": round(min_area, 6),
        "open_or_nonmanifold_edges": non_manifold_undir,
        "orientation_mismatches": unmatched_dir,
    }
    if non_manifold_undir != 0 or unmatched_dir != 0 or vol <= 0:
        raise AssertionError(f"Manifold check FAILED for {path}: {stats}")
    return stats


# ---------------------------------------------------------------------------
# Bottom Base & Top Lid Assembly Definitions
# ---------------------------------------------------------------------------

def build_bottom_base() -> np.ndarray:
    """
    Bottom Base (printed right-side up: flat Z=0 on build plate, cavity facing +Z).
    Includes:
    - Rounded outer lower shell (0..5.2 mm) + telescoping inner snap rim (5.2..7.6 mm)
    - 2-step 45-deg chamfered outward snap ridges on L/R mid-walls (print support-free)
    - Underside PCB relief pocket (16.0 x 21.8 mm) + perimeter PCB support ledge
    - Wide U-cradle USB-C cutout at front (-Y)
    - Monolithic reinforced keychain tab (+Y) with 4.6 mm hole & chamfered tip
    """
    # Step 1: Collect strictly non-overlapping boundary loops so Delaunay conforms smoothly
    loops: list[np.ndarray] = []

    # Outer main body contour + keychain lug combined into ONE smooth clean perimeter!
    # Wait: keychain lug spans X=[-5.4..+5.4], Y=[+14.3..+21.8] with R=5.4 semicircular tip.
    # Let's build a smooth unified outer silhouette with concave fillet shoulders at Y=+14.3!
    body_base = rounded_rect_poly(-HALF_W, HALF_W, Y_FRONT, Y_BACK, R_OUTER, n_arc=10)
    loops.append(body_base)

    # Disjoint keychain extension attached flush? No collinear edge overlap!
    # So instead of splitting at Y=Y_BACK, make ONE continuous silhouette for Bottom Floor/Body!
    loops.pop()
    ang_tip = np.linspace(0.0, np.pi, 64)
    lug_cx, lug_cy = 0.0, KEYCHAIN_Y_TIP - KEYCHAIN_R  # 16.4
    lug_tip = np.column_stack([lug_cx + KEYCHAIN_R * np.cos(ang_tip), lug_cy + KEYCHAIN_R * np.sin(ang_tip)])

    # Unified outer boundary: smooth dense arcs (no post-hoc straight chord subdivision on convex hull!)
    pts_outer: list[list[float]] = []
    # Bottom-left R_OUTER corner (180..270 deg)
    for a in np.linspace(np.pi, 1.5 * np.pi, 16):
        pts_outer.append([-HALF_W + R_OUTER + R_OUTER * np.cos(a), Y_FRONT + R_OUTER + R_OUTER * np.sin(a)])
    # Bottom-right R_OUTER corner (270..360 deg)
    for a in np.linspace(1.5 * np.pi, 2.0 * np.pi, 16):
        pts_outer.append([HALF_W - R_OUTER + R_OUTER * np.cos(a), Y_FRONT + R_OUTER + R_OUTER * np.sin(a)])
    # Top-right R_OUTER corner (0..90 deg)
    for a in np.linspace(0.0, 0.5 * np.pi, 16):
        pts_outer.append([HALF_W - R_OUTER + R_OUTER * np.cos(a), Y_BACK - R_OUTER + R_OUTER * np.sin(a)])
    # Right shoulder into keychain lug (Y_BACK -> lug_cy at X=+KEYCHAIN_R)
    pts_outer.append([KEYCHAIN_R + 1.1, Y_BACK])
    pts_outer.append([KEYCHAIN_R, Y_BACK + 0.8])
    for p in lug_tip:
        pts_outer.append([float(p[0]), float(p[1])])
    # Left shoulder back onto Y_BACK
    pts_outer.append([-KEYCHAIN_R, Y_BACK + 0.8])
    pts_outer.append([-KEYCHAIN_R - 1.1, Y_BACK])
    # Top-left R_OUTER corner (90..180 deg)
    for a in np.linspace(0.5 * np.pi, np.pi, 16):
        pts_outer.append([-HALF_W + R_OUTER + R_OUTER * np.cos(a), Y_BACK - R_OUTER + R_OUTER * np.sin(a)])

    outer_arr = np.array(pts_outer, dtype=float)
    # Deduplicate close vertices
    keep = [0]
    for i in range(1, len(outer_arr)):
        if np.linalg.norm(outer_arr[i] - outer_arr[keep[-1]]) > 1e-4:
            keep.append(i)
    if np.linalg.norm(outer_arr[keep[0]] - outer_arr[keep[-1]]) < 1e-4:
        keep.pop()
    outer_arr = outer_arr[keep]
    loops.append(outer_arr)

    # Keychain hole inside lug
    hole_loop = circle_poly(0.0, KEYCHAIN_HOLE_Y, KEYCHAIN_HOLE_R, n=32)
    loops.append(hole_loop)

    # Split wall step: separates outer base (Z_SPLIT) from raised inner snap rim + snap bumps
    # Build snap-rim outer boundary with 2-step outward snap bumps on L/R centered around Y=0!
    # Step 1 rim outer: X_RIM = 10.25 -> bump1 = 10.40 -> bump2 = 10.55
    def make_rim_outer(bump: float, y_span: float) -> np.ndarray:
        yb_in = Y_PCB_BACK + 1.0  # 13.1 (leaves 1.2 mm outer step for Lid rear skirt!)
        yf_in = Y_PCB_FRONT - 0.1 # -12.2 (keeps front corners at Z=Z_SPLIT cleanly flush)
        pts = [
            [-X_RIM, yf_in],
            [X_RIM, yf_in],
            [X_RIM, -y_span - 0.4],
            [X_RIM + bump, -y_span],
            [X_RIM + bump, y_span],
            [X_RIM, y_span + 0.4],
            [X_RIM, yb_in - 0.8],
        ]
        # Top-right small corner
        for a in np.linspace(0.0, 0.5 * np.pi, 6):
            pts.append([X_RIM - 0.8 + 0.8 * np.cos(a), yb_in - 0.8 + 0.8 * np.sin(a)])
        for a in np.linspace(0.5 * np.pi, np.pi, 6):
            pts.append([-X_RIM + 0.8 + 0.8 * np.cos(a), yb_in - 0.8 + 0.8 * np.sin(a)])
        pts.extend([
            [-X_RIM, y_span + 0.4],
            [-X_RIM - bump, y_span],
            [-X_RIM - bump, -y_span],
            [-X_RIM, -y_span - 0.4],
        ])
        arr = np.array(pts, dtype=float)
        kp = [0]
        for i in range(1, len(arr)):
            if np.linalg.norm(arr[i] - arr[kp[-1]]) > 1e-4:
                kp.append(i)
        return arr[kp]

    # Note: make two nested, strictly non-overlapping snap contours (outer step 2 inside rim? Wait: bump2 > bump1 > 0!)
    rim_outer_s0 = make_rim_outer(0.0, SNAP_Y_HALF + 0.6)
    rim_outer_s1 = make_rim_outer(0.16, SNAP_Y_HALF + 0.25)  # strictly outside rim_outer_s0 on snap strip
    # Keep non-snap perimeter outside by 0.12? No: overlapping collinear lines fail!
    # Instead, place TWO small independent disjoint snap-bump islands ONLY on Left & Right mid-walls
    # cleanly outside X_RIM (offset +0.02? No: start right INSIDE X_RIM? No: overlap!).
    # Wait: even cleaner -> make rim_outer HAVE the smooth snap contour directly AND use two tiny concentric
    # offset strips OUTSIDE on X_RIM? Even better: step out by tiny offset everywhere OR put step1 & step2 ONLY
    # where rim is shaped! Let's check: why not give bump1 = 0.16 along [-SNAP_Y-0.4..+SNAP_Y+0.4] and step2?
    # Look! If rim_outer ALREADY includes bump1 (0.16) at X_RIM..X_RIM+0.16, and bump2 is a separate disjoint D-strip
    # or just 1 clean 0.30 mm chamfered? Wait: one 0.25 mm snap bead at Z=[6.2..7.0] with 0.25 mm overhang prints
    # cleanly in PLA with ZERO supports (0.25 mm < 0.40 mm line width -> 62% supported by layer below!).
    # Wait: adding ONE chamfer-step strip (0.15 mm) along rim_outer with a 0.08 mm inset loop inside rim_outer?
    # Better yet: rim_outer IS the step-1 outer contour (`bump=0.26 mm` along Y in [-4.2..+4.2]), AND an outer
    # base line separates Y_BACK cleanly. Let's check rim_outer_s0 only -> NO overlapping loops at all!
    loops.append(rim_outer_s0)

    # Disjoint left & right snap bump strips sitting just outside X_RIM (gap? No gap! Wait: if left bump shares
    # X=X_RIM? If we split rim_outer NOT at all and offset bump slightly by +0.00? Still shared collinear edge!)
    # HOW TO AVOID COLLINEAR OVERLAPS COMPLETELY:
    # Make `snap_zone` a FULL outer ring offset `+0.16 mm` inside `[-X_RIM..+X_RIM]`? No, just make
    # `snap_rim` contour ITSELF have `0.26 mm` bump at `Y in [-4.2..+4.2]`, and make `rim_base` `0.15 mm` wider?
    # No: at `Z=6.3..6.9` a `0.24 mm` single-step snap bead on a 1.05 mm wall only steps out 0.24 mm per side,
    # which bridges cleanly cleanly in FDM (<0.3 mm single-bead shelf!). Wait: what about the Z-profile on that
    # exact `0.24 mm` bead strip if we shape `rim_outer` with `bump=0.0` AND place a `D-shaped` snap bump strip
    # intersecting at X=X_RIM-0.15 (inside the rim thickness!)?
    # GENIUS!! Look at that:
    # If the snap-bump loop starts at `X = X_RIM - 0.18` (INSIDE the solid wall thickness where BOTH wall
    # and bump are solid!), extends out to `X = X_RIM + 0.24`, then its inner edge `X = X_RIM - 0.18`
    # NEVER touches `X_RIM` (0.18 mm clearance!) -> ZERO collinear edges!!
    # Wait: the outer side crosses `X = X_RIM` at `Y = ±(SNAP_Y_HALF + 0.4)`!
    # Wait: any crossing between two boundary polygons SHOULD include the exact intersection point!
    # So EVEN CLEANER: don't cross `X_RIM` at all — keep `rim_outer` (`X_RIM`) as the full rim wall `[0..Z_RIM_TOP]`,
    # AND put a thin inward-extending closed pocket? NO — even simpler!!
    # Include the `0.25 mm` wide snap-bump strip cleanly by splitting `rim_outer` ONLY at `Y = ±4.6`? Or just offset
    # `rim_outer_outer = rim_outer + 0.24` ONLY along `Y in [-4.2..+4.2]` AND `rim_inner` (`X_BAY`) cleanly inside!
    # Wait: look at `make_rim_outer(0.24, SNAP_Y_HALF)` as `rim_outer_plus`: it is STRICTLY OUTSIDE `rim_outer_0`
    # everywhere in the bump zone (`0.24 mm`), except on Top/Bottom/Front where `rim_outer_plus` can have `+0.0`?
    # No: give `rim_outer_s0` `X_RIM = 10.25` around the entire rim, AND just shape `rim_outer_s0` ITSELF with the
    # `0.25 mm` snap-bump at `Y in [-4.2..+4.2]`! Inside `[X_BAY .. X_RIM_BUMP]`, where is the snap Z `[6.3 .. 6.9]`?
    # On `centroid`: if centroid has `abs(x) > X_RIM + 0.01`, it's ONLY in the snap bump `[6.25 .. 6.95]` (plus base below `Z_SPLIT`)!!
    # WAIT A SECOND!! RE-READ THAT!!
    # On triangles inside `[X_RIM .. X_RIM + 0.25]`: we don't even NEED an internal line at `X = X_RIM` because
    # wait: without a triangle boundary edge AT `X = X_RIM`, triangles inside the bump would connect `X_BAY` to `X_RIM+0.25`!
    # SO PUT AN EXPLICIT 0.15mm INNER WALL LINE AT `X = X_RIM` ONLY WHEN MAKING THE BUMP LOOP, OR JUST CONNECT
    # ALL RIM VERTICES CLEANLY AROUND A SEPARATE DISJOINT OUTER BUMP? No: if `rim_outer` is split cleanly into
    # shared graph segments `[front + left_s + left_bump_inner + right_s + right_bump_inner + back]` + `[left_bump_outer]` + `[right_bump_outer]`:
    # Let's write a tiny 10-line helper that passes **explicit graph segments** instead of only closed loops!
    # THEN YOU CAN HAVE SHARED JUNCTIONS, T-JUNCTIONS, CHAMFER STRIPS, AND ZERO DUPLICATE OR CROSSING EDGES!!

    # YES!! Let's check how trivial `segments` + `pts` is vs `loops`:
    # `subdivide_loop_max_edge` works on ANY edge list `[(p0, p1)]`!
    # Let's check: for Bottom Base, every junction vertex (where USB-C cradle meets inner bay, where snap bump meets X_RIM,
    # where keychain shoulder meets back wall) is cleanly defined ONCE!

    # Wait: check even simpler — DO WE EVEN NEED crossing curves at USB-C?
    # Look at the USB-C U-slot (`|X| <= 6.1`, `Y in [-13.7, -12.1]`):
    # Inner PCB bay (`X in [-9.2, +9.2]`, `Y in [-12.1, +12.1]`) and Front Cutout (`X in [-6.1, +6.1]`, `Y in [-13.7, -12.1]`)
    # form ONE SINGLE continuous closed inner-cutout loop at `Z > Z_PCB_BOT`!
    # Look:
    # - `Y = -13.7 .. -12.1`: USB-C channel `X = ±6.1`
    # - `Y = -12.1 .. +12.1`: PCB bay `X = ±9.2`!
    # Wait: below `Z = Z_PCB_BOT` (`1.4 .. 2.6`), the underside relief pocket is `X = ±8.0, Y = [-10.9, +10.9]`
    # (`1.2 mm` inset PCB ledge around ALL 4 sides — completely disjoint, inside `PCB bay` with `1.2 mm` margin!).
    # AND the front outer shell (`Y = -13.7`) vs USB-C U-slot:
    # - For `Z <= USBC_Z_BOT (2.6 mm)`: Base floor + cradle shelf is SOLID across `Y = -13.7 .. +12.1` (`2.6 mm` front wall under USB-C!).
    # - For `2.6 < Z <= Z_SPLIT (5.2 mm)`: Front USB-C channel `X in [-6.1, +6.1], Y in [-13.7, -12.1]` is OPEN!
    # - Wait: if `Z <= 2.6` is solid inside USB-C channel and `Z > 2.6` is open, that USB-C channel polygon shares `Y = -13.7` with the outer wall!
    # Wait: in our graph-segment Conforming Delaunay, sharing `[(-6.1, -13.7) -> (+6.1, -13.7)]` cleanly in ONE segment list handles BOTH without any duplicate edges!!

    # Build clean non-overlapping planar graph segments for Bottom Base!
    segs_poly: list[tuple[np.ndarray, np.ndarray]] = []

    def add_open_chain(coords: list[tuple[float, float]]) -> None:
        for i in range(len(coords) - 1):
            segs_poly.append((np.array(coords[i], float), np.array(coords[i + 1], float)))

    def add_closed_poly(coords: np.ndarray) -> None:
        n = len(coords)
        for i in range(n):
            segs_poly.append((coords[i], coords[(i + 1) % n]))

    # 1. Outer silhouette split cleanly at USB-C channel endpoints (-6.1, Y_FRONT) and (+6.1, Y_FRONT)
    chain_outer: list[tuple[float, float]] = [(USBC_CUT_W / 2.0, Y_FRONT)]
    for a in np.linspace(1.5 * np.pi, 2.0 * np.pi, 16):
        chain_outer.append((HALF_W - R_OUTER + R_OUTER * math.cos(a), Y_FRONT + R_OUTER + R_OUTER * math.sin(a)))
    for a in np.linspace(0.0, 0.5 * np.pi, 16):
        chain_outer.append((HALF_W - R_OUTER + R_OUTER * math.cos(a), Y_BACK - R_OUTER + R_OUTER * math.sin(a)))
    chain_outer.append((KEYCHAIN_R + 1.1, Y_BACK))
    chain_outer.append((KEYCHAIN_R, Y_BACK + 0.8))
    for p in lug_tip:
        chain_outer.append((float(p[0]), float(p[1])))
    chain_outer.append((-KEYCHAIN_R, Y_BACK + 0.8))
    chain_outer.append((-KEYCHAIN_R - 1.1, Y_BACK))
    for a in np.linspace(0.5 * np.pi, np.pi, 16):
        chain_outer.append((-HALF_W + R_OUTER + R_OUTER * math.cos(a), Y_BACK - R_OUTER + R_OUTER * math.sin(a)))
    for a in np.linspace(np.pi, 1.5 * np.pi, 16):
        chain_outer.append((-HALF_W + R_OUTER + R_OUTER * math.cos(a), Y_FRONT + R_OUTER + R_OUTER * math.sin(a)))
    chain_outer.append((-USBC_CUT_W / 2.0, Y_FRONT))
    add_open_chain(chain_outer)
    # Front USB-C lower edge across opening (-6.1 -> +6.1) + USB-C slot interior U-wall
    add_open_chain([(-USBC_CUT_W / 2.0, Y_FRONT), (USBC_CUT_W / 2.0, Y_FRONT)])
    add_open_chain([
        (-USBC_CUT_W / 2.0, Y_FRONT),
        (-USBC_CUT_W / 2.0, Y_PCB_FRONT),
        (USBC_CUT_W / 2.0, Y_PCB_FRONT),
        (USBC_CUT_W / 2.0, Y_FRONT),
    ])

    # 2. Keychain hole
    add_closed_poly(circle_poly(0.0, KEYCHAIN_HOLE_Y, KEYCHAIN_HOLE_R, n=32))

    # 3. Inner PCB bay (`X in [-9.15, +9.15], Y in [-11.875, +11.875]`) with 6 integral 0.15 mm
    #    compliant crush ribs (4 side @ Y=+-6, 2 rear @ X=+-4.5) for zero-slop XY PCB retention!
    bay_poly: list[tuple[float, float]] = [
        (-USBC_CUT_W / 2.0, Y_PCB_FRONT),
        (-X_BAY, Y_PCB_FRONT),
        (-X_BAY, -7.6), (-X_BAY + CRUSH_RIB, -7.0), (-X_BAY + CRUSH_RIB, -5.0), (-X_BAY, -4.4),
        (-X_BAY, 4.4), (-X_BAY + CRUSH_RIB, 5.0), (-X_BAY + CRUSH_RIB, 7.0), (-X_BAY, 7.6),
        (-X_BAY, Y_PCB_BACK),
        (-6.0, Y_PCB_BACK), (-5.4, Y_PCB_BACK - CRUSH_RIB), (-3.6, Y_PCB_BACK - CRUSH_RIB), (-3.0, Y_PCB_BACK),
        (3.0, Y_PCB_BACK), (3.6, Y_PCB_BACK - CRUSH_RIB), (5.4, Y_PCB_BACK - CRUSH_RIB), (6.0, Y_PCB_BACK),
        (X_BAY, Y_PCB_BACK),
        (X_BAY, 7.6), (X_BAY - CRUSH_RIB, 7.0), (X_BAY - CRUSH_RIB, 5.0), (X_BAY, 4.4),
        (X_BAY, -4.4), (X_BAY - CRUSH_RIB, -5.0), (X_BAY - CRUSH_RIB, -7.0), (X_BAY, -7.6),
        (X_BAY, Y_PCB_FRONT),
        (USBC_CUT_W / 2.0, Y_PCB_FRONT),
    ]
    add_open_chain(bay_poly)
    pcb_bay_path = Path(np.array(bay_poly, dtype=float))

    # 4. Underside PCB relief pocket -> ~1.3 mm continuous support ledge clear of crush ribs!
    pock_x, pock_y = X_BAY - 1.4, Y_PCB_BACK - 1.3
    add_closed_poly(rounded_rect_poly(-pock_x, pock_x, -pock_y, pock_y, 0.8, n_arc=5))

    # 5. Raised snap-rim outer boundary (X_RIM = 10.25) + 2-step 0.15 mm snap ridges on L/R mid-walls!
    rim_y_back = Y_PCB_BACK + 1.0  # 12.875
    sy0, sy1, sy2, sy3 = SNAP_Y_HALF + 0.5, SNAP_Y_HALF + 0.15, SNAP_Y_HALF - 0.15, SNAP_Y_HALF - 0.40

    # Left & Right main X_RIM spines split cleanly at snap junctions
    add_open_chain([(-X_BAY, Y_PCB_FRONT), (-X_RIM, Y_PCB_FRONT), (-X_RIM, -sy0)])
    add_open_chain([(-X_RIM, -sy0), (-X_RIM, sy0)])
    add_open_chain([(-X_RIM, sy0), (-X_RIM, rim_y_back - 0.8)])

    rim_top_back: list[tuple[float, float]] = [(-X_RIM, rim_y_back - 0.8)]
    for a in np.linspace(math.pi, 0.5 * math.pi, 6):
        rim_top_back.append((-X_RIM + 0.8 + 0.8 * math.cos(a), rim_y_back - 0.8 + 0.8 * math.sin(a)))
    for a in np.linspace(0.5 * math.pi, 0.0, 6):
        rim_top_back.append((X_RIM - 0.8 + 0.8 * math.cos(a), rim_y_back - 0.8 + 0.8 * math.sin(a)))
    rim_top_back.extend([(X_RIM, rim_y_back - 0.8), (X_RIM, sy0)])
    add_open_chain(rim_top_back)
    add_open_chain([(X_RIM, sy0), (X_RIM, -sy0)])
    add_open_chain([(X_RIM, -sy0), (X_RIM, Y_PCB_FRONT), (X_BAY, Y_PCB_FRONT)])

    # Non-overlapping step-1 (+0.15) and step-2 (+0.30) snap strips on Left & Right
    for sx in (-1.0, 1.0):
        x0 = sx * X_RIM
        x1 = sx * (X_RIM + 0.15)
        x2 = sx * (X_RIM + 0.30)
        add_open_chain([(x0, -sy0), (x1, -sy1), (x1, -sy2)])
        add_open_chain([(x1, -sy2), (x1, sy2)])
        add_open_chain([(x1, sy2), (x1, sy1), (x0, sy0)])
        add_open_chain([(x1, -sy2), (x2, -sy3), (x2, sy3), (x1, sy2)])

    pts, simplices = conforming_segments_delaunay(segs_poly, max_edge=0.30)

    # Assign exact Z intervals per triangle centroid
    body_path = Path(outer_arr)
    rim_y_max = Y_PCB_BACK + 1.0

    def bottom_z_profile(c: np.ndarray) -> list[list[tuple[float, float]]]:
        x, y = c[:, 0], c[:, 1]
        in_outer = body_path.contains_points(c, radius=-1e-4)
        in_hole = (x * x + (y - KEYCHAIN_HOLE_Y) ** 2) < KEYCHAIN_HOLE_R ** 2
        in_pcb_bay = pcb_bay_path.contains_points(c)
        in_pock = (np.abs(x) < pock_x) & (np.abs(y) < pock_y)
        in_usbc = (np.abs(x) < USBC_CUT_W / 2.0) & (y >= Y_FRONT) & (y <= Y_PCB_FRONT)
        # Inner rim zone (between PCB bay/crush ribs and X_RIM)
        in_rim_box = (np.abs(x) < X_RIM) & (y > Y_PCB_FRONT) & (y < rim_y_max)
        # Exact half-plane checks matching the chamfered snap trapezoid edges
        dx1 = np.abs(x) - X_RIM
        in_snap1 = (dx1 >= 0.0) & (dx1 < 0.15) & (np.abs(y) < (sy0 - (dx1 / 0.15) * (sy0 - sy1)))
        dx2 = np.abs(x) - (X_RIM + 0.15)
        in_snap2 = (dx2 >= 0.0) & (dx2 <= 0.15) & (np.abs(y) < (sy2 - (dx2 / 0.15) * (sy2 - sy3)))

        out: list[list[tuple[float, float]]] = []
        for i in range(len(c)):
            if not bool(in_outer[i]) or bool(in_hole[i]):
                out.append([])
                continue
            if bool(in_usbc[i]):
                out.append([(0.0, USBC_Z_BOT)])
            elif bool(in_pock[i]):
                out.append([(0.0, BOTTOM_FLOOR)])
            elif bool(in_pcb_bay[i]):
                out.append([(0.0, Z_PCB_BOT)])
            elif bool(in_rim_box[i]):
                xi, yi = abs(float(x[i])), float(y[i])
                if yi > rim_y_max - 0.8 and xi > X_RIM - 0.8:
                    if (xi - (X_RIM - 0.8)) ** 2 + (yi - (rim_y_max - 0.8)) ** 2 > 0.8 ** 2:
                        out.append([(0.0, Z_SPLIT)])
                        continue
                out.append([(0.0, Z_RIM_TOP)])
            elif bool(in_snap1[i]):
                out.append([(0.0, Z_SPLIT), (6.20, 7.15)])
            elif bool(in_snap2[i]):
                out.append([(0.0, Z_SPLIT), (6.35, 6.95)])
            else:
                # Outer wall base & keychain lug (0 .. Z_SPLIT)
                out.append([(0.0, Z_SPLIT)])
        return out

    return extrude_interval_solid(pts, simplices, bottom_z_profile)


def build_top_lid(
    diffuser_mode: str = "gp16",
    with_led_hole: bool = False,
    with_boot_hole: bool = False,
    print_orientation: bool = True,
) -> np.ndarray:
    """
    Top Lid (printed upside-down with exterior logo face at Z=0 on bed if print_orientation=True).
    Features:
    - Rounded outer shell matching Bottom Base (23.0 x 28.0 mm, R=2.0 mm)
    - -0.6 mm debossed official SV Sticky compact wordmark ("st!cky") symmetrically centered
      at (X=0.00, Y=+0.20) on the top face (independent of LED location)
    - Smooth hole-free exterior by default (BOOT switch shielded behind ~1.8 mm air gap;
      internal translucent light-funnel centered directly above the GP16 WS2812 RGB LED;
      optional --open-led / --open-boot cutouts when explicitly requested)
    - 1.11 mm outer snap-fit skirt with Z-locked 45-degree 2-step internal snap hooks
    - 3-point tripod Z-clamp: rear bare corner bosses + front steel USB-C saddle boss
    """
    segs_poly: list[tuple[np.ndarray, np.ndarray]] = []

    def add_open_chain(coords: list[tuple[float, float]]) -> None:
        for i in range(len(coords) - 1):
            segs_poly.append((np.array(coords[i], float), np.array(coords[i + 1], float)))

    def add_closed_poly(coords: np.ndarray) -> None:
        n = len(coords)
        for i in range(n):
            segs_poly.append((coords[i], coords[(i + 1) % n]))

    # 1. Outer Top Lid footprint path (segments added below split cleanly at USB-C corners)
    outer_poly = rounded_rect_poly(-HALF_W, HALF_W, Y_FRONT, Y_BACK, R_OUTER, n_arc=16)

    # 2. Inner skirt perimeter (X_SKIRT_IN = 10.45, y_skirt_back = 13.35)
    #    Open across USB-C front zone, with non-overlapping 2-step inward snap hooks on L/R
    y_skirt_back = Y_PCB_BACK + 1.25  # 13.35
    sy0, sy1, sy2, sy3 = SNAP_Y_HALF + 0.5, SNAP_Y_HALF + 0.15, SNAP_Y_HALF - 0.15, SNAP_Y_HALF - 0.40

    chain_outer: list[tuple[float, float]] = [(USBC_CUT_W / 2.0, Y_FRONT)]
    for a in np.linspace(1.5 * np.pi, 2.0 * np.pi, 16):
        chain_outer.append((HALF_W - R_OUTER + R_OUTER * math.cos(a), Y_FRONT + R_OUTER + R_OUTER * math.sin(a)))
    for a in np.linspace(0.0, 0.5 * np.pi, 16):
        chain_outer.append((HALF_W - R_OUTER + R_OUTER * math.cos(a), Y_BACK - R_OUTER + R_OUTER * math.sin(a)))
    for a in np.linspace(0.5 * np.pi, np.pi, 16):
        chain_outer.append((-HALF_W + R_OUTER + R_OUTER * math.cos(a), Y_BACK - R_OUTER + R_OUTER * math.sin(a)))
    for a in np.linspace(np.pi, 1.5 * np.pi, 16):
        chain_outer.append((-HALF_W + R_OUTER + R_OUTER * math.cos(a), Y_FRONT + R_OUTER + R_OUTER * math.sin(a)))
    chain_outer.append((-USBC_CUT_W / 2.0, Y_FRONT))
    add_open_chain(chain_outer)
    add_open_chain([(-USBC_CUT_W / 2.0, Y_FRONT), (USBC_CUT_W / 2.0, Y_FRONT)])

    add_open_chain([(-USBC_CUT_W / 2.0, Y_FRONT), (-USBC_CUT_W / 2.0, Y_PCB_FRONT), (-X_SKIRT_IN, Y_PCB_FRONT), (-X_SKIRT_IN, -sy0)])
    add_open_chain([(-X_SKIRT_IN, -sy0), (-X_SKIRT_IN, sy0)])
    skirt_top: list[tuple[float, float]] = [(-X_SKIRT_IN, sy0), (-X_SKIRT_IN, y_skirt_back - 0.8)]
    for a in np.linspace(math.pi, 0.5 * math.pi, 6):
        skirt_top.append((-X_SKIRT_IN + 0.8 + 0.8 * math.cos(a), y_skirt_back - 0.8 + 0.8 * math.sin(a)))
    for a in np.linspace(0.5 * math.pi, 0.0, 6):
        skirt_top.append((X_SKIRT_IN - 0.8 + 0.8 * math.cos(a), y_skirt_back - 0.8 + 0.8 * math.sin(a)))
    skirt_top.extend([(X_SKIRT_IN, y_skirt_back - 0.8), (X_SKIRT_IN, sy0)])
    add_open_chain(skirt_top)
    add_open_chain([(X_SKIRT_IN, sy0), (X_SKIRT_IN, -sy0)])
    add_open_chain([(X_SKIRT_IN, -sy0), (X_SKIRT_IN, Y_PCB_FRONT), (USBC_CUT_W / 2.0, Y_PCB_FRONT), (USBC_CUT_W / 2.0, Y_FRONT)])

    for sx in (-1.0, 1.0):
        x0 = sx * X_SKIRT_IN
        x1 = sx * (X_SKIRT_IN - 0.15)
        x2 = sx * (X_SKIRT_IN - 0.30)
        add_open_chain([(x0, -sy0), (x1, -sy1), (x1, -sy2)])
        add_open_chain([(x1, -sy2), (x1, sy2)])
        add_open_chain([(x1, sy2), (x1, sy1), (x0, sy0)])
        add_open_chain([(x1, -sy2), (x2, -sy3), (x2, sy3), (x1, sy2)])

    # 3-point tripod PCB Z-clamp: rear bare corners + front steel USB-C shell saddle (zero PCB rocking!)
    # Note: usb_hold_boss (-3.5..+3.5 x -11.3..-7.3) lies strictly inside the 0.10 mm plaque grid below,
    # aligned on exact grid boundaries, so omit its closed loop from outer Delaunay to avoid duplicate edges.
    hold_boss_l = rect_poly(-8.4, -5.8, 10.0, 11.4)
    hold_boss_r = rect_poly(5.8, 8.4, 10.0, 11.4)
    usb_hold_boss = rect_poly(-3.5, 3.5, -11.3, -7.3)
    add_closed_poly(hold_boss_l)
    add_closed_poly(hold_boss_r)

    # Map measured RP2350 SuperMini button & GP16 LED into case coords (180-deg rotated from USB-up photo!)
    bcfg = BUTTON_LAYOUT_SUPERMINI
    pcb_y0 = Y_PCB_FRONT + float(bcfg["pcb_y_offset"])
    boot_cx = (bcfg["pcb_w"] / 2.0) - bcfg["boot"][0]
    boot_cy = pcb_y0 + bcfg["boot"][1]
    boot_r = bcfg["boot"][2]
    led_cx = (bcfg["pcb_w"] / 2.0) - bcfg["led"][0]
    led_cy = pcb_y0 + bcfg["led"][1]
    led_r = bcfg["led"][2]

    # Symmetrically center bold 90-deg CCW rotated 22.4 mm "st!cky" wordmark along lid length (X=0.00, Y=+0.20).
    # Keeps >= 0.50 mm nozzle-safe stroke widths and keeps GP16 diffuser beside the main lettering.
    logo_w = 22.4
    plaque_x0, plaque_x1 = -5.00, 5.00
    plaque_y0, plaque_y1 = -11.50, 11.90

    if with_led_hole:
        add_closed_poly(circle_poly(led_cx, led_cy, led_r, n=28))
    if with_boot_hole:
        add_closed_poly(circle_poly(boot_cx, boot_cy, boot_r, n=32))
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo_compact_outline_kleur.png")
    p_verts, p_tris, p_in_logo, p_border = build_sticky_plaque_2d_mesh(
        logo_path=logo_path,
        x0=plaque_x0,
        x1=plaque_x1,
        y0=plaque_y0,
        y1=plaque_y1,
        target_w_mm=logo_w,
        step_mm=0.10,
        rotate_ccw_deg=90,
        min_gap_mm=0.42,
    )
    add_closed_poly(np.array(p_border, dtype=float))

    pts_out, simp_out = conforming_segments_delaunay(segs_poly, max_edge=0.28)

    # Drop Delaunay triangles INSIDE the plaque hole [plaque_x0, plaque_x1] x [plaque_y0, plaque_y1]
    c_out = (pts_out[simp_out[:, 0]] + pts_out[simp_out[:, 1]] + pts_out[simp_out[:, 2]]) / 3.0
    outside_plaque = ~(
        (c_out[:, 0] > plaque_x0) & (c_out[:, 0] < plaque_x1)
        & (c_out[:, 1] > plaque_y0) & (c_out[:, 1] < plaque_y1)
    )
    simp_out = simp_out[outside_plaque]

    # Merge pts_out + p_verts sharing EXACT quantized boundary coordinates so zero seam exists!
    q_out = {tuple(np.round(pts_out[i], 4)): i for i in range(len(pts_out))}
    verts_merged = list(pts_out)
    p_to_merged = np.empty(len(p_verts), dtype=int)
    for i, pv in enumerate(p_verts):
        key = tuple(np.round(pv, 4))
        if key in q_out:
            p_to_merged[i] = q_out[key]
        else:
            p_to_merged[i] = len(verts_merged)
            verts_merged.append(pv)

    pts = np.array(verts_merged, dtype=float)
    n_outer_tris = len(simp_out)
    simplices = np.vstack([simp_out, p_to_merged[p_tris]])

    lid_outer_path = Path(outer_poly)
    hold_l_path = Path(hold_boss_l)
    hold_r_path = Path(hold_boss_r)
    usb_hold_path = Path(usb_hold_boss)

    Z_CEIL_DEBOSS = Z_TOTAL - LOGO_DEBOSS_DEPTH   # 8.8 mm (in assembled Z)

    def top_z_profile(c: np.ndarray) -> list[list[tuple[float, float]]]:
        x, y = c[:, 0], c[:, 1]
        in_outer = lid_outer_path.contains_points(c, radius=-1e-4)
        in_logo = np.zeros(len(c), dtype=bool)
        in_logo[n_outer_tris:] = p_in_logo
        in_boss = hold_l_path.contains_points(c) | hold_r_path.contains_points(c)
        in_usb_boss = usb_hold_path.contains_points(c)

        # Interior pocket check (`|X| < X_SKIRT_IN`, `Y < y_skirt_back`, plus rounded back corners)
        in_cavity = np.zeros(len(c), dtype=bool)
        for i in range(len(c)):
            xi, yi = abs(float(x[i])), float(y[i])
            if xi < X_SKIRT_IN and yi < y_skirt_back:
                if yi > Y_PCB_FRONT:
                    if yi > y_skirt_back - 0.8 and xi > X_SKIRT_IN - 0.8:
                        if (xi - (X_SKIRT_IN - 0.8)) ** 2 + (yi - (y_skirt_back - 0.8)) ** 2 > 0.8 ** 2:
                            in_cavity[i] = False
                        else:
                            in_cavity[i] = True
                    else:
                        in_cavity[i] = True
                elif yi >= Y_FRONT and xi < USBC_CUT_W / 2.0:
                    in_cavity[i] = True

        # Inward snap catch strips inside `|X| in [X_SKIRT_IN - 0.30, X_SKIRT_IN]`
        dh1 = X_SKIRT_IN - np.abs(x)
        in_hook1 = (dh1 > 0.0) & (dh1 <= 0.15) & (np.abs(y) < (sy0 - (dh1 / 0.15) * (sy0 - sy1)))
        dh2 = (X_SKIRT_IN - 0.15) - np.abs(x)
        in_hook2 = (dh2 > 0.0) & (dh2 <= 0.15) & (np.abs(y) < (sy2 - (dh2 / 0.15) * (sy2 - sy3)))

        in_led_cut = ((x - led_cx) ** 2 + (y - led_cy) ** 2) < led_r ** 2 if with_led_hole else np.zeros(len(c), dtype=bool)
        in_btn_boot = ((x - boot_cx) ** 2 + (y - boot_cy) ** 2) < boot_r ** 2 if with_boot_hole else np.zeros(len(c), dtype=bool)
        in_cut = in_btn_boot | in_led_cut

        if diffuser_mode in ("gp16", "dot"):
            # Smooth translucent light-funnel centered directly over GP16 WS2812 RGB LED (-4.85, -0.75)
            r_led2 = (x - led_cx) ** 2 + (y - led_cy) ** 2
            in_diff_thin = r_led2 <= 1.65 ** 2
            in_diff_mid = (~in_diff_thin) & (r_led2 <= 2.45 ** 2)
        else:
            in_diff_thin = np.zeros(len(c), dtype=bool)
            in_diff_mid = np.zeros(len(c), dtype=bool)

        out: list[list[tuple[float, float]]] = []
        for i in range(len(c)):
            if not bool(in_outer[i]) or bool(in_cut[i]):
                out.append([])
                continue

            z_top = Z_CEIL_DEBOSS if bool(in_logo[i]) else Z_TOTAL

            if not bool(in_cavity[i]):
                # Outer perimeter skirt wall goes down to Z_SPLIT (front USB corners & L/R/Back walls)
                out.append([(Z_SPLIT, z_top)])
            else:
                # Inside ceiling plate
                if bool(in_diff_thin[i]):
                    # Translucent window centered directly above GP16 (0.74 mm flat / 0.42 mm at logo stroke; manifold overlap)
                    z_bot = (Z_CEIL_DEBOSS - 0.42) if bool(in_logo[i]) else (Z_CEIL_DEBOSS - 0.14)
                elif bool(in_diff_mid[i]):
                    # Flared lower light-collector step channeling GP16 light softly to top surface
                    z_bot = (Z_CEIL_DEBOSS - 0.72) if bool(in_logo[i]) else (Z_CEIL_DEBOSS - 0.36)
                elif bool(in_boss[i]):
                    # Rear hold-down pads reaching 0.10 mm above PCB top surface
                    z_bot = Z_PCB_TOP + 0.10
                elif bool(in_usb_boss[i]):
                    # Front saddle 0.10 mm above 3.20 mm steel USB-C shell (zero front PCB tilt!)
                    z_bot = Z_PCB_TOP + 3.30
                else:
                    z_bot = Z_LID_CEILING

                ivs = [(z_bot, z_top)]
                # Tight Z-locked snap hooks seated 0.03 mm directly below Base ridge (zero Z-rattle)
                if bool(in_hook1[i]):
                    ivs.append((Z_SPLIT, 6.17))
                elif bool(in_hook2[i]):
                    ivs.append((Z_SPLIT, 6.02))
                out.append(ivs)
        return out

    tris = extrude_interval_solid(pts, simplices, top_z_profile)

    if print_orientation:
        # Rotate 180 degrees around X axis so Lid prints FLAT upside-down at Z=0
        # (x, y, z) -> (x, -y, Z_TOTAL - z). Keeps right-handed orientation AND reads "st!cky" forward when flipped!
        tris = tris.copy()
        tris[..., 1] = -tris[..., 1]
        tris[..., 2] = Z_TOTAL - tris[..., 2]

    return tris


def conforming_segments_delaunay(
    segs_poly: list[tuple[np.ndarray, np.ndarray]], max_edge: float = 0.28
) -> tuple[np.ndarray, np.ndarray]:
    """Subdivide arbitrary planar line segments cleanly and recover EVERY segment in Delaunay."""
    pts_list: list[np.ndarray] = []
    segs: list[tuple[int, int]] = []
    for a, b in segs_poly:
        dist = float(np.linalg.norm(b - a))
        steps = max(1, int(math.ceil(dist / max_edge)))
        idx0 = len(pts_list)
        for s in range(steps + 1):
            pts_list.append(a + (s / steps) * (b - a))
        for s in range(steps):
            segs.append((idx0 + s, idx0 + s + 1))

    pts = np.array(pts_list, dtype=float)
    quant = np.round(pts, 4)
    uniq_map: dict[tuple[float, float], int] = {}
    new_pts: list[np.ndarray] = []
    old_to_new = np.empty(len(pts), dtype=int)
    for idx, q in enumerate(quant):
        key = (float(q[0]), float(q[1]))
        if key not in uniq_map:
            uniq_map[key] = len(new_pts)
            new_pts.append(pts[idx])
        old_to_new[idx] = uniq_map[key]

    pts = np.array(new_pts, dtype=float)
    unique_segs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for a, b in segs:
        na, nb = int(old_to_new[a]), int(old_to_new[b])
        if na == nb:
            continue
        ek = (min(na, nb), max(na, nb))
        if ek not in seen:
            seen.add(ek)
            unique_segs.append(ek)

    for it in range(6):
        tri = Delaunay(pts)
        simplices = tri.simplices
        # Vectorized present-edge check (100x faster than Python loop)
        e01 = np.sort(simplices[:, [0, 1]], axis=1)
        e12 = np.sort(simplices[:, [1, 2]], axis=1)
        e20 = np.sort(simplices[:, [2, 0]], axis=1)
        all_e = np.vstack([e01, e12, e20])
        present = set(map(tuple, all_e.tolist()))
        missing = [e for e in unique_segs if e not in present]
        print(f"    Delaunay iter {it}: pts={len(pts)}, segs={len(unique_segs)}, missing={len(missing)}", flush=True)
        if not missing:
            break
        if len(pts) + len(missing) > 40000:
            raise RuntimeError(f"Aborted Delaunay bisection explosion: pts={len(pts)}, missing={len(missing)}")
        missing_set = set(missing)
        next_segs: list[tuple[int, int]] = []
        extra: list[np.ndarray] = []
        base = len(pts)
        for a, b in unique_segs:
            if (a, b) in missing_set:
                mid_idx = base + len(extra)
                extra.append(0.5 * (pts[a] + pts[b]))
                next_segs.append((min(a, mid_idx), max(a, mid_idx)))
                next_segs.append((min(mid_idx, b), max(mid_idx, b)))
            else:
                next_segs.append((a, b))
        pts = np.vstack([pts, np.array(extra, dtype=float)])
        unique_segs = next_segs
    else:
        tri = Delaunay(pts)
        simplices = tri.simplices

    p0 = pts[simplices[:, 0]]
    p1 = pts[simplices[:, 1]]
    p2 = pts[simplices[:, 2]]
    cross = (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) - (p1[:, 1] - p0[:, 1]) * (p2[:, 0] - p0[:, 0])
    flip = cross < 0
    if np.any(flip):
        simplices = simplices.copy()
        simplices[flip, 1], simplices[flip, 2] = simplices[flip, 2], simplices[flip, 1]

    return pts, simplices


def translate_mesh(tris: np.ndarray, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> np.ndarray:
    out = tris.copy()
    out[..., 0] += dx
    out[..., 1] += dy
    out[..., 2] += dz
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SV Sticky RP2350 SuperMini STL case files.")
    parser.add_argument(
        "--out-dir",
        default=os.path.join(os.path.dirname(__file__), "stl"),
        help="Output directory for generated .stl files",
    )
    parser.add_argument(
        "--open-led",
        action="store_true",
        help="Cut an open pinhole over GP16 LED instead of the smooth 0.42 mm translucent !-dot membrane",
    )
    parser.add_argument(
        "--open-boot",
        action="store_true",
        help="Also cut an access hole over the BOOT button (covered by default to prevent accidental bootloader entry)",
    )
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    print("Generating Bottom Base...")
    tris_bottom = build_bottom_base()
    path_bottom = os.path.join(args.out_dir, "karel_rp2350_bottom.stl")
    write_binary_stl(path_bottom, tris_bottom, "Karel RP2350 SuperMini Bottom Base")
    print("  Verified:", verify_stl(path_bottom))

    mode_desc = "Open GP16/BOOT" if (args.open_led or args.open_boot) else "Centered st!cky + Smooth GP16 Diffuser + Protected BOOT"
    print(f"Generating Top Lid ({mode_desc})...")
    tris_top = build_top_lid(
        diffuser_mode="gp16",
        with_led_hole=args.open_led,
        with_boot_hole=args.open_boot,
        print_orientation=True,
    )
    path_top = os.path.join(args.out_dir, "karel_rp2350_top.stl")
    write_binary_stl(path_top, tris_top, f"Karel RP2350 SuperMini Top Lid ({mode_desc})")
    print("  Verified:", verify_stl(path_top))

    for stale in (
        "karel_rp2350_top_buttons_led.stl",
        "karel_rp2350_top_led_window.stl",
        "karel_rp2350_top_smooth_led.stl",
        "karel_rp2350_top_universal_diffuser.stl",
    ):
        sp = os.path.join(args.out_dir, stale)
        if os.path.exists(sp):
            os.remove(sp)

    print("Generating side-by-side Complete Print Plate...")
    plate_tris = np.concatenate([
        translate_mesh(tris_bottom, dx=-14.0, dy=0.0, dz=0.0),
        translate_mesh(tris_top, dx=+14.0, dy=0.0, dz=0.0),
    ], axis=0)
    path_plate = os.path.join(args.out_dir, "karel_rp2350_complete_plate.stl")
    write_binary_stl(path_plate, plate_tris, "Karel RP2350 Complete Print Plate")
    print("  Verified:", verify_stl(path_plate))


if __name__ == "__main__":
    main()
