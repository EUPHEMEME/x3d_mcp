#!/usr/bin/env python3
"""
pronk.py -- "pronk" still-life scene generator
================================================================================
VERSION 15 · 2026-07-30 · EUPHEME Technologies LLC

An X3D 4.0 still life INSPIRED BY (not a record of):

    Willem Claesz Heda, "Still Life with a Gilt Cup" (1635, signed)
    Rijksmuseum, Amsterdam, SK-A-4830 -- Public Domain (CC PDM 1.0)
    https://www.rijksmuseum.nl/en/collection/SK-A-4830

v15 is the recomposition pass: the scene is built to the painting's OWN
construction, measured in research/pronk.md --
  * frame 1.283:1, camera square-on, eye ~0.50 m above the tabletop, ~2.1 m
    back, vertical FOV 0.51 rad; table-wall junction lands just below centre
  * ONE connected frieze of overlapping objects, skyline staircasing up to the
    gilt cup at x~+0.24, one step down (flagon), falling to a berkemeyer
    CROPPED by the right frame edge; shell plate OVERHANGS the front edge
  * the wall is a BAKED gradient (emissive-only quad -- values are authored,
    lights cannot wash them): bright halo behind roemer/gilt cup, dark corners
  * light: one cool window key upper-left + an authored IBL cubemap whose left
    face IS a cross-mullioned window -> every metal and glass picks up the
    window reflection the Bulletin names; warm right-wall bounce; baked
    contact + directional cast shadows (X_ITE renders no light shadows)
  * two chroma accents only: fire-gilt cup and lemon; all else grey-green-umber

Verified capability only (CAPABILITY_MATRIX.md): PBR texture set, IBL via
EnvironmentLight.specularTexture, Sheen/Iridescence extensions (raw-XML
injected), TextureTransform, TextureProperties aniso, baked shadows.
NO transmission/IOR/volume glass (dead), no light.shadows (dead).

Provenance rides IN the scene as a MetadataSet (provenance='interpretive'),
plus two in-picture carriers Heda himself used: a printed almanac page rolled
into a pepper cone, and an inscription on the crumpled napkin's hem where the
painting carries "HEDA. 1635".

Run:  python3 pronk.py            -> writes pronk.x3d next to this file
      import pronk; pronk.scene_builder(vp)  -> PATCHED X3D XML string
"""

import base64
import io
import itertools
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.expanduser("~/x3d_mcp/src"))
from x3d import x3d as X

VERSION = "15"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_X3D = os.path.join(HERE, "pronk.x3d")

# Authored Background colour (analyse() should be told this)
BG_RGB = (0.055, 0.048, 0.042)

# ---------------------------------------------------------------- world frame
# metres, life size. Painting x-fraction fx maps to world x ~ (fx-0.5)*1.30
# at the tableau's depth. Tabletop y=0.
TABLE_TOP = 0.0
TABLE_FRONT = 0.40        # z of front edge
TABLE_BACK = -0.25        # shallow: the painting compresses the tabletop wedge
TABLE_LEFT = -1.35        # exits frame left
TABLE_RIGHT = 0.66        # exits/ends at frame right (painting 0.97)
WALL_Z = -0.40            # the wall sits close behind -- a luminous backdrop

_uid = itertools.count(1)

# registries the post-serialization patch pass consumes + asserts
SHEEN_DEFS = []           # (material DEF, raw extension XML)
_TEX_SLOT_PREFIX = {      # ImageTexture DEF prefix -> containerField
    "TXB_": "baseTexture",
    "TXN_": "normalTexture",
    "TXR_": "metallicRoughnessTexture",
    "TXE_": "emissiveTexture",
}


# ---------------------------------------------------------------- textures
def _data_uri(im):
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _np_img(a):
    from PIL import Image
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


def _normal_from_height(h, strength=2.0):
    """Height field (float 0..1) -> tangent-space normal map image."""
    gy, gx = np.gradient(h.astype(float))
    nx, ny = -gx * strength, gy * strength
    nz = np.ones_like(h, dtype=float)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([(nx / n + 1) * 127.5, (ny / n + 1) * 127.5,
                    (nz / n + 1) * 127.5], axis=-1)
    return _np_img(rgb)


def _blotch(size, seed, blur_div=20):
    from PIL import Image, ImageFilter
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 1, (size, size))
    im = Image.fromarray(((a - a.min()) / (np.ptp(a) + 1e-9) * 255).astype("uint8"))
    im = im.filter(ImageFilter.GaussianBlur(size / blur_div))
    return (np.asarray(im, float) / 255.0 - 0.5) * 2.0


def _tex_wall():
    """Baked wall gradient (research 1.4): bright halo L~#8A7A6C behind the
    roemer/gilt cup, #675A4F corners, zero noise. Rendered EMISSIVE so the
    authored values survive any lighting."""
    w, h = 384, 288
    yy, xx = np.mgrid[0:h, 0:w]
    u, v = xx / w, yy / h          # v=0 is the TOP of the wall (image row 0)
    # halo centred where the roemer/bokaal stand (world x ~ +0.2, y ~ +0.5)
    d2 = ((u - 0.56) / 0.26) ** 2 + ((v - 0.58) / 0.38) ** 2
    halo = np.exp(-d2)
    bright = np.array([140, 125, 103], float)
    dark = np.array([76, 66, 55], float)
    img = dark[None, None, :] + (bright - dark)[None, None, :] * halo[..., None]
    # top corners fall further; right side behind the jug darkens (shadow side)
    corner = ((u - 0.5) ** 2 * 1.8 + (v - 0.05) ** 2 * 1.6)
    img *= (1.0 - 0.30 * np.clip(corner, 0, 1))[..., None]
    img *= (1.0 - 0.24 * np.clip((u - 0.74) * 2.8, 0, 1))[..., None]
    img *= (1.0 - 0.30 * np.clip((0.30 - u) * 2.8, 0, 1))[..., None]
    return _np_img(img)


def _tex_carpet():
    """Green wool table carpet: bottle green, napped, subtle blotch."""
    s = 256
    blotch = _blotch(s, 41, 16)
    fine = np.random.default_rng(42).normal(0, 4.0, (s, s, 1))
    base = np.array([23, 32, 21], float)
    img = base[None, None, :] * (1.0 + 0.30 * blotch[..., None]) + fine
    return _np_img(img)


def _damask_field(s, seed):
    """White damask: base + faint satin diamond figure + fine weave noise."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:s, 0:s]
    dia = (np.abs(((xx * 7 / s) % 1) - 0.5) + np.abs(((yy * 7 / s) % 1) - 0.5))
    figure = np.where(dia < 0.42, 1.0, 0.0) * 5.0        # +-5 L, white-on-white
    weave = rng.normal(0, 2.2, (s, s))
    base = np.array([233, 227, 214], float)
    img = base[None, None, :] + (figure + weave)[..., None]
    return img, figure


def _fold_shading(img, freqs_phases_amps, v_hang, depth=46.0, drop_mul=0.90):
    """Bake the hanging drop's value structure: a mid-tone knockdown plus soft
    dark valleys between the folds (v > v_hang). The a4 render proved the
    geometry alone cannot shade a face-on drop under a frontal-left key --
    the halftone must be authored."""
    s = img.shape[0]
    u = np.arange(s) / s
    f = sum(a * np.cos(2 * math.pi * u * fq + ph)
            for fq, ph, a in freqs_phases_amps)
    f = (f - f.min()) / (np.ptp(f) + 1e-9)
    v = (np.arange(s) / s)[:, None]
    fade = np.clip((v - v_hang) / 0.05, 0, 1)
    img *= (1.0 - (1.0 - drop_mul) * fade)[..., None]
    img -= ((1.0 - f)[None, :] * fade * depth)[..., None]
    return img


def _tex_napkin_spread():
    """Spread napkin: pressed crease GRID from storage (research 2.15)."""
    s = 256
    img, _ = _damask_field(s, 7)
    img = _fold_shading(img, ((3.1, 0.4, 0.55), (1.7, 2.1, 0.45)), 0.721,
                        depth=72.0, drop_mul=0.80)
    hgt = np.zeros((s, s))
    for u0 in (0.25, 0.50, 0.75):
        d = np.abs(np.arange(s) / s - u0)
        line = np.exp(-(d / 0.010) ** 2)
        img[:, :, :] -= (line * 8)[None, :, None]         # crease shadow line
        hgt -= line[None, :] * 0.5
    for v0 in (0.30, 0.62):
        d = np.abs(np.arange(s) / s - v0)
        line = np.exp(-(d / 0.010) ** 2)
        img -= (line * 6)[:, None, None]
        hgt -= line[:, None] * 0.4
    return _np_img(img), _normal_from_height(hgt, 1.6)


def _tex_napkin_crumpled():
    """Crumpled napkin + hem with drawn-thread border and the interpretive
    inscription where the painting is signed 'HEDA. 1635' (research: put ours
    there)."""
    from PIL import ImageDraw
    s = 256
    img, _ = _damask_field(s, 9)
    img = _fold_shading(img, ((2.3, 1.1, 0.6), (1.3, 0.2, 0.4)), 0.536,
                        depth=62.0, drop_mul=0.92)
    # the waterfall's own form shadow: darker toward its right side
    s_ = img.shape[0]
    u_ = (np.arange(s_) / s_)[None, :, None]
    v_ = (np.arange(s_) / s_)[:, None, None]
    img *= 1.0 - 0.16 * np.clip((u_ - 0.55) / 0.45, 0, 1) \
        * np.clip((v_ - 0.536) / 0.05, 0, 1)
    im = _np_img(img)
    d = ImageDraw.Draw(im)
    # drawn-thread hem borders (dashed) near the bottom edge of the cloth
    for y in (int(s * 0.905), int(s * 0.952)):
        for x0 in range(0, s, 9):
            d.line([(x0, y), (x0 + 4, y)], fill=(198, 191, 176), width=1)
    # the inscription -- SMALL and quiet, at the right of the hem, where the
    # painting carries "HEDA. 1635" (a6 rendered it as a printed banner)
    tiny = ImageDraw.Draw(im)
    txt = "na HEDA 1635 · SK-A-4830 · interpretive"
    from PIL import Image as _I
    tim = _I.new("RGB", (s * 2, 14), (0, 0, 0))
    td = ImageDraw.Draw(tim)
    td.text((0, 0), txt, fill=(60, 52, 40))
    tim = tim.resize((s, 7), _I.LANCZOS)
    ta = np.asarray(tim, float)
    mask = ta.sum(axis=2) > 30
    region = np.asarray(im, float)
    y0, x0 = int(s * 0.918), 0
    sub = region[y0:y0 + 7, x0:x0 + s]
    sub[mask[:, :s]] -= 46
    region[y0:y0 + 7, x0:x0 + s] = sub
    im = _np_img(region)
    hgt = _blotch(s, 11, 10) * 0.5
    return im, _normal_from_height(hgt, 1.2)


def _tex_paper():
    """Red-and-black letterpress almanac leaf -> the pepper cone. The
    in-picture provenance carrier, exactly as Heda used printed ephemera."""
    from PIL import Image, ImageDraw
    s = 256
    im = Image.new("RGB", (s, s), (238, 231, 214))
    d = ImageDraw.Draw(im)
    lines = [
        ("ALMANACH", (150, 30, 24)), ("na Willem Claesz HEDA", (20, 18, 16)),
        ("Stilleven met vergulde", (20, 18, 16)), ("bokaal · Ao 1635", (150, 30, 24)),
        ("Rijksmuseum SK-A-4830", (20, 18, 16)), ("oly-verf op paneel", (20, 18, 16)),
        ("87.8 x 112.6 duym", (20, 18, 16)), ("PUBLYCK DOMEIN", (150, 30, 24)),
        ("interpretive rendering", (20, 18, 16)), ("EUPHEME MMXXVI", (20, 18, 16)),
    ] * 2
    y = 6
    for txt, col in lines:
        d.text((12, y), txt, fill=col)
        y += 12
        if y > s - 12:
            break
    return im


def _tex_pewter_mr(seed=3, base_rough=112, ring_amp=13):
    """ORM-style map for pewter sadware: G=roughness with concentric turning
    marks (v axis = profile direction on a lathe Extrusion), B=metal."""
    s = 128
    rng = np.random.default_rng(seed)
    v = np.arange(s) / s
    rings = np.sin(v * 90.0 + rng.uniform(0, 9)) * ring_amp \
        + rng.normal(0, 7, s)
    g = np.clip(base_rough + rings, 40, 200)
    img = np.zeros((s, s, 3))
    img[..., 0] = 255
    img[..., 1] = g[:, None]
    img[..., 2] = 255
    return _np_img(img)


def _tex_gilt_mr():
    """Gilt cup: burnished ridges (rough ~0.15) vs pounced matte grounds
    (~0.4) as v-bands following the lathe profile."""
    s = 128
    v = np.arange(s) / s
    g = np.full(s, 100.0)
    for lo, hi, val in ((0.00, 0.06, 45), (0.10, 0.16, 50), (0.30, 0.36, 48),
                        (0.48, 0.54, 55), (0.68, 0.74, 45), (0.86, 1.00, 60)):
        g[(v >= lo) & (v < hi)] = val
    img = np.zeros((s, s, 3))
    img[..., 0] = 255
    img[..., 1] = g[:, None] + np.random.default_rng(5).normal(0, 6, (s, s))
    img[..., 2] = 255
    return _np_img(img)


def _tex_speckle_normal(seed=8, strength=3.0, blur=1.4):
    """Pounced/chased micro-relief: granular sparkle on gilt + silver."""
    from PIL import Image, ImageFilter
    s = 128
    rng = np.random.default_rng(seed)
    h = rng.normal(0, 1, (s, s))
    im = Image.fromarray(((h - h.min()) / np.ptp(h) * 255).astype("uint8"))
    im = im.filter(ImageFilter.GaussianBlur(blur))
    return _normal_from_height(np.asarray(im, float) / 255.0, strength)


def _tex_bread():
    s = 128
    blotch = _blotch(s, 13, 8)
    base = np.array([182, 128, 50], float)
    img = base[None, None, :] * (1.0 + 0.34 * blotch[..., None])
    img[..., 2] *= (1.0 - 0.30 * np.clip(blotch, 0, 1))     # scorch goes red-brown
    flour = np.clip(_blotch(s, 14, 5) - 0.55, 0, 1) * 110
    img += flour[..., None]
    hgt = _blotch(s, 15, 6) * 0.6 + _blotch(s, 16, 24) * 0.4
    return _np_img(img), _normal_from_height(hgt, 3.4)


def _tex_flagon():
    """Pewter flagon body: olive-dark, scratched -- with the two NAMED
    reflections baked in (research 2.10): warm gold smear of the bokaal on the
    left shoulder, cool window streak beside it. u=0 faces +x; the gilt cup
    stands to the flagon's -x, the window up-left-front."""
    from PIL import ImageFilter
    s = 256
    rng = np.random.default_rng(21)
    img = np.zeros((s, s, 3)) + np.array([128, 128, 112], float)[None, None, :]
    img *= (1.0 + 0.10 * _blotch(s, 22, 12))[..., None]
    u = (np.arange(s) / s)[None, :]
    v = (np.arange(s) / s)[:, None]
    # warm smear of the gilt cup, facing -x (u ~ 0.5), upper body (v ~ 0.55+)
    gold = np.exp(-((u - 0.50) / 0.10) ** 2) * np.exp(-((v - 0.60) / 0.26) ** 2)
    img += gold[..., None] * np.array([170, 112, 20], float)[None, None, :]
    # cool window streak, facing up-left-front (u ~ 0.33), tall and narrow
    win = np.exp(-((u - 0.33) / 0.040) ** 2) * np.exp(-((v - 0.55) / 0.32) ** 2)
    img += win[..., None] * np.array([120, 132, 138], float)[None, None, :]
    # scratches
    for _ in range(60):
        x0, y0 = rng.integers(0, s, 2)
        ln, ang = rng.integers(6, 28), rng.uniform(0, math.pi)
        for t in range(ln):
            x = int(x0 + t * math.cos(ang)) % s
            yq = int(y0 + t * math.sin(ang) * 0.2) % s
            img[yq, x] += 14
    im = _np_img(img).filter(ImageFilter.GaussianBlur(0.6))
    return im


def _tex_wincross():
    """The cross-mullioned window as a small RGBA decal -- the Bulletin's
    signature reflection, mirrored in the roemer's bowl upper-left."""
    from PIL import Image, ImageDraw, ImageFilter
    s = 48
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([6, 4, s - 6, s - 4], fill=(250, 246, 232, 210))
    d.rectangle([s // 2 - 2, 4, s // 2 + 2, s - 4], fill=(70, 66, 56, 220))
    d.rectangle([6, s // 2 - 2, s - 6, s // 2 + 2], fill=(70, 66, 56, 220))
    return im.filter(ImageFilter.GaussianBlur(1.1))


def _tex_lemon_cut():
    """Cut face: radial segments, wet. RGBA -- corners transparent so the
    Rectangle2D decal reads as a DISC on the fruit, not a floating square."""
    from PIL import Image, ImageFilter
    s = 128
    yy, xx = np.mgrid[0:s, 0:s]
    cx = cy = s / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (s / 2)
    ang = np.arctan2(yy - cy, xx - cx)
    seg = 0.5 + 0.5 * np.cos(ang * 9)
    img = np.zeros((s, s, 3)) + np.array([223, 217, 164], float)
    img += (seg * np.clip(1 - r, 0, 1))[..., None] * np.array([12, 10, -14], float)
    septa = (seg > 0.93) & (r < 0.82)
    img[septa] = np.array([238, 234, 204], float)
    img[r > 0.82] = np.array([232, 228, 212], float)      # pith ring
    img[r > 0.94] = np.array([216, 185, 60], float)       # rind edge
    rgb = _np_img(img).filter(ImageFilter.GaussianBlur(0.8)).convert("RGBA")
    a = np.asarray(rgb).copy()
    a[..., 3] = np.where(r <= 0.985, 255, 0).astype("uint8")
    return Image.fromarray(a, "RGBA")


def _tex_peel():
    """Peel ribbon: zest centre (oil-pocked), pith edges; u across width."""
    s = 128
    rng = np.random.default_rng(31)
    u = (np.arange(s) / s)[None, :]
    zest = np.exp(-((u - 0.5) / 0.30) ** 2)
    img = np.zeros((s, s, 3))
    pith = np.array([230, 224, 202], float)
    zestc = np.array([204, 172, 62], float)
    img += pith[None, None, :] + (zestc - pith)[None, None, :] * zest[..., None]
    pocks = (rng.random((s, s)) > 0.985)
    img[pocks] *= 0.8
    return _np_img(img)


def _tex_oyster_shell():
    """Exterior: flaky grey-brown laminae as concentric arcs."""
    s = 128
    yy, xx = np.mgrid[0:s, 0:s]
    r = np.sqrt((xx - s * 0.5) ** 2 + (yy - s * 0.9) ** 2) / s
    lam = 0.5 + 0.5 * np.sin(r * 60)
    img = np.zeros((s, s, 3)) + np.array([118, 108, 92], float)
    img *= (0.82 + 0.36 * lam)[..., None]
    img *= (1.0 + 0.15 * _blotch(s, 33, 10))[..., None]
    return _np_img(img)


def _cube_face(base, seed=None, window=False, cloth=False):
    """One 128px cubemap face. The left face carries the cross-mullioned
    window (research 1.4 -- it is literally painted into the roemer)."""
    from PIL import Image, ImageDraw, ImageFilter
    s = 128
    im = Image.new("RGB", (s, s), tuple(int(c) for c in base))
    d = ImageDraw.Draw(im)
    if window:
        # casement, 2x2 panes, upper-centre of the face
        x0, y0, x1, y1 = int(s * .34), int(s * .16), int(s * .74), int(s * .62)
        d.rectangle([x0, y0, x1, y1], fill=(252, 246, 228))
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        d.rectangle([mx - 3, y0, mx + 3, y1], fill=(70, 60, 48))
        d.rectangle([x0, my - 3, x1, my + 3], fill=(70, 60, 48))
        d.rectangle([x0, y0, x1, y1], outline=(60, 52, 42), width=4)
    if cloth:
        # the white napkin masses, seen from above -> what silver picks up
        d.ellipse([int(s * .05), int(s * .25), int(s * .70), int(s * .85)],
                  fill=(216, 208, 192))
    return im.filter(ImageFilter.GaussianBlur(2.2 if not window else 1.2))


_TEX = {}


def textures():
    """Build all data URIs once per process."""
    if _TEX:
        return _TEX
    t = _TEX
    t["wall"] = _data_uri(_tex_wall())
    t["carpet"] = _data_uri(_tex_carpet())
    nb, nn = _tex_napkin_spread()
    t["nap_s_b"], t["nap_s_n"] = _data_uri(nb), _data_uri(nn)
    cb, cn = _tex_napkin_crumpled()
    t["nap_c_b"], t["nap_c_n"] = _data_uri(cb), _data_uri(cn)
    t["paper"] = _data_uri(_tex_paper())
    t["pewter_mr"] = _data_uri(_tex_pewter_mr())
    t["gilt_mr"] = _data_uri(_tex_gilt_mr())
    t["speckle_n"] = _data_uri(_tex_speckle_normal())
    t["chase_n"] = _data_uri(_tex_speckle_normal(9, 2.2, 2.2))
    bb, bn = _tex_bread()
    t["bread_b"], t["bread_n"] = _data_uri(bb), _data_uri(bn)
    t["flagon_b"] = _data_uri(_tex_flagon())
    t["lemon_cut"] = _data_uri(_tex_lemon_cut())
    t["wincross"] = _data_uri(_tex_wincross())
    t["peel"] = _data_uri(_tex_peel())
    t["oyshell"] = _data_uri(_tex_oyster_shell())
    # cubemap: umber room, window on the LEFT face, cloth below
    t["cube_left"] = _data_uri(_cube_face((92, 80, 70), window=True))
    t["cube_right"] = _data_uri(_cube_face((82, 72, 58)))
    t["cube_front"] = _data_uri(_cube_face((84, 76, 66)))
    t["cube_back"] = _data_uri(_cube_face((100, 88, 76)))
    t["cube_top"] = _data_uri(_cube_face((104, 94, 80)))
    t["cube_bottom"] = _data_uri(_cube_face((90, 88, 74), cloth=True))
    return t


# ---------------------------------------------------------------- helpers
def circle(n=28, r=1.0):
    pts = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n))
           for k in range(n)]
    pts.append(pts[0])
    return pts


def lathe(profile, appearance, n=28, cap_ends=True, crease=1.2):
    """profile = [(y, radius), ...] bottom->top, as an Extrusion lathe.
    Texture v runs along the profile, u around -- concentric maps line up."""
    spine = [(0.0, y, 0.0) for (y, _r) in profile]
    scale = [(max(r, 0.0035), max(r, 0.0035)) for (_y, r) in profile]
    return X.Shape(
        appearance=appearance,
        geometry=X.Extrusion(
            crossSection=circle(n), spine=spine, scale=scale,
            beginCap=cap_ends, endCap=cap_ends,
            creaseAngle=crease, solid=True))


def _img(defprefix, uri, aniso=False, repeat=True):
    kw = dict(DEF=f"{defprefix}{next(_uid)}", url=[uri],
              repeatS=repeat, repeatT=repeat)
    if aniso:
        kw["textureProperties"] = X.TextureProperties(
            anisotropicDegree=8, generateMipMaps=True,
            minificationFilter="NICEST", magnificationFilter="NICEST")
    return X.ImageTexture(**kw)


def mat(base, metallic, rough, transparency=0.0, emissive=(0, 0, 0),
        base_tex=None, normal_tex=None, mr_tex=None, emissive_tex=None,
        sheen=None, irid=False, normal_scale=1.0, tiling=None, aniso=False):
    """PhysicalMaterial appearance. Texture slots get DEF'd ImageTextures whose
    containerField the patch pass injects (serializer omits them -- verified).
    sheen=(color, roughness) / irid register raw-XML extension injections."""
    t = textures()
    kw = dict(baseColor=base, metallic=metallic, roughness=rough,
              transparency=transparency, emissiveColor=emissive)
    if normal_scale != 1.0:
        kw["normalScale"] = normal_scale
    if base_tex:
        kw["baseTexture"] = _img("TXB_", t[base_tex], aniso=aniso)
    if normal_tex:
        kw["normalTexture"] = _img("TXN_", t[normal_tex])
    if mr_tex:
        kw["metallicRoughnessTexture"] = _img("TXR_", t[mr_tex])
    if emissive_tex:
        kw["emissiveTexture"] = _img("TXE_", t[emissive_tex])
    if sheen or irid:
        kw["DEF"] = f"PMX_{next(_uid)}"
    m = X.PhysicalMaterial(**kw)
    if sheen:
        col, rgh = sheen
        SHEEN_DEFS.append((kw["DEF"],
                           f"<SheenMaterialExtension containerField='extensions' "
                           f"sheenColor='{col[0]} {col[1]} {col[2]}' "
                           f"sheenRoughness='{rgh}'/>"))
    if irid:
        SHEEN_DEFS.append((kw["DEF"],
                           "<IridescenceMaterialExtension containerField='extensions' "
                           "iridescence='0.6' iridescenceIOR='1.3'/>"))
    akw = dict(material=m)
    if tiling:
        akw["textureTransform"] = X.TextureTransform(scale=tiling)
    return X.Appearance(**akw)


def look_at(pos, target, up=(0.0, 1.0, 0.0)):
    p = np.array(pos, float); t = np.array(target, float)
    f = t - p; f /= np.linalg.norm(f)
    r = np.cross(f, np.array(up, float)); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    m = np.array([r, u, -f]).T
    ang = math.acos(max(-1.0, min(1.0, (np.trace(m) - 1.0) / 2.0)))
    if abs(ang) < 1e-8:
        return (0.0, 1.0, 0.0, 0.0)
    ax = np.array([m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1]])
    ax /= (2.0 * math.sin(ang))
    return (float(ax[0]), float(ax[1]), float(ax[2]), float(ang))


# ---------------------------------------------------------------- materials
def M_gilt():
    return mat((0.93, 0.62, 0.22), 1.0, 0.3, mr_tex="gilt_mr",
               normal_tex="speckle_n", normal_scale=0.7)


def M_silver_dull():
    return mat((0.62, 0.61, 0.57), 1.0, 0.40, normal_tex="chase_n",
               normal_scale=0.6)


def M_silver_bright():
    return mat((0.80, 0.79, 0.74), 1.0, 0.14)


def M_pewter():
    return mat((0.68, 0.68, 0.64), 1.0, 0.42, mr_tex="pewter_mr")


def M_pewter_plain():
    return mat((0.55, 0.55, 0.52), 1.0, 0.40)


def M_pewter_dark():
    # baseColor WHITE: the texture carries the tint (multiplied otherwise)
    return mat((1.0, 1.0, 1.0), 1.0, 0.40, base_tex="flagon_b")


def M_glass_g(transp=0.50):   # Waldglas
    return mat((0.17, 0.23, 0.15), 0.0, 0.06, transparency=transp)


def M_glass_dark():
    return mat((0.10, 0.14, 0.09), 0.0, 0.05, transparency=0.25)


def M_glass_clear():
    return mat((0.55, 0.60, 0.55), 0.0, 0.04, transparency=0.62)


def M_carpet():
    return mat((1, 1, 1), 0.0, 0.85, base_tex="carpet", tiling=(3.0, 3.0),
               sheen=((0.16, 0.22, 0.14), 0.6), aniso=True)


def M_napkin_spread():
    return mat((1, 1, 1), 0.0, 0.55, base_tex="nap_s_b", normal_tex="nap_s_n",
               sheen=((0.92, 0.90, 0.84), 0.38), aniso=True)


def M_napkin_crumpled():
    return mat((1, 1, 1), 0.0, 0.55, base_tex="nap_c_b", normal_tex="nap_c_n",
               sheen=((0.92, 0.90, 0.84), 0.38), aniso=True)


def M_wall():
    # emissive-only: authored values, lights can't touch them
    return mat((0.01, 0.01, 0.01), 0.0, 1.0, emissive=(1, 1, 1),
               emissive_tex="wall")


def M_nacre():
    return mat((0.80, 0.79, 0.72), 0.1, 0.15, irid=True)


# ---------------------------------------------------------------- shadows
# X_ITE renders no light shadows (verified byte-identical) -- all occlusion is
# baked geometry. Key sits upper-LEFT, so every cast lobe falls RIGHT and
# slightly toward the viewer (research 1.4).
SHADOW_DIR = (0.72, 0.30)      # xz direction of cast shadows
_lift = itertools.count(0)


def contact(x, z, rx, rz=None, strength=0.55, lift=0.0016, height=0.0):
    """Contact core + a directional cast lobe scaled by object height."""
    rz = rz if rz is not None else rx
    lift = lift + (next(_lift) % 7) * 0.00022
    layers = []
    for i, (sc, a) in enumerate(((1.00, 0.22), (0.66, 0.38), (0.36, strength))):
        layers.append(X.Transform(
            translation=(x, lift + i * 0.0004, z),
            scale=(rx * sc, 1.0, rz * sc),
            children=[X.Shape(
                appearance=mat((0.03, 0.03, 0.025), 0.0, 1.0, transparency=1.0 - a),
                geometry=X.IndexedFaceSet(
                    coord=X.Coordinate(point=[(px, 0.0, pz) for px, pz in circle(26, 1.0)]),
                    coordIndex=list(range(26)) + [-1], solid=False))]))
    if height > 0.0:
        ln = height * 1.4
        layers.append(X.Transform(
            translation=(x + SHADOW_DIR[0] * (rx + ln * 0.45),
                         lift + 0.0013, z + SHADOW_DIR[1] * (rz + ln * 0.3)),
            rotation=(0, 1, 0, -math.atan2(SHADOW_DIR[1], SHADOW_DIR[0])),
            scale=(ln * 0.8, 1.0, rz * 0.85),
            children=[X.Shape(
                appearance=mat((0.03, 0.03, 0.025), 0.0, 1.0, transparency=0.66),
                geometry=X.IndexedFaceSet(
                    coord=X.Coordinate(point=[(px, 0.0, pz) for px, pz in circle(26, 1.0)]),
                    coordIndex=list(range(26)) + [-1], solid=False))]))
    return layers


# ---------------------------------------------------------------- props
def charger(r=0.175):
    """35 cm pewter charger: wide flat rim, shallow well, turning marks."""
    profile = [
        (0.000, r * 0.52), (0.004, r * 0.58), (0.006, r * 0.62),
        (0.010, r * 0.64), (0.014, r * 0.92), (0.020, r * 0.995), (0.022, r),
    ]
    bright = mat((0.78, 0.78, 0.73), 1.0, 0.38, mr_tex="pewter_mr")
    return lathe(profile, bright, n=48)


def plate(r=0.10):
    profile = [
        (0.000, r * 0.55), (0.004, r * 0.60), (0.006, r * 0.70),
        (0.012, r * 0.92), (0.018, r), (0.020, r * 0.985),
    ]
    return lathe(profile, M_pewter(), n=40)


def oyster(meat=True, ang=0.0):
    """Ostrea edulis half-shell, interior UP: flaky rim, nacre bowl, and (if
    not yet eaten) the wet grey body. Emptied shells keep the pearly interior
    -- a6 rendered them exterior-up, reading as tarry biscuits."""
    kids = [X.Transform(scale=(1.0, 0.22, 0.80), children=[
        X.Shape(appearance=mat((0.55, 0.50, 0.42), 0.05, 0.8, base_tex="oyshell"),
                geometry=X.Sphere(radius=0.038))]),
            X.Transform(translation=(0, 0.0060, 0), scale=(0.86, 0.13, 0.70),
                        children=[X.Shape(appearance=M_nacre(),
                                          geometry=X.Sphere(radius=0.038))])]
    if meat:
        kids.append(X.Transform(translation=(-0.004, 0.0085, 0.002),
                                scale=(0.46, 0.10, 0.34), children=[
            X.Shape(appearance=mat((0.58, 0.57, 0.46), 0.0, 0.06),
                    geometry=X.Sphere(radius=0.038))]))
    # tip the shell slightly toward the camera so the wet interior shows
    return X.Transform(rotation=(0, 1, 0, ang), children=[
        X.Transform(rotation=(1, 0, 0, 0.10), children=kids)])


def paper_cone():
    """Rolled printed page holding pepper, lying tipped on the shell plate."""
    n = 12
    spine = [(0.0, 0.0, 0.0), (0.0, 0.05, 0.0), (0.0, 0.10, 0.0),
             (0.0, 0.13, 0.0)]
    scale = [(0.004, 0.004), (0.016, 0.016), (0.030, 0.030), (0.034, 0.034)]
    cone = X.Shape(
        appearance=mat((1, 1, 1), 0.0, 0.6, base_tex="paper"),
        geometry=X.Extrusion(crossSection=circle(n), spine=spine, scale=scale,
                             beginCap=True, endCap=False, creaseAngle=1.4,
                             solid=False))
    pepper = X.Transform(translation=(0, 0.115, 0), children=[
        X.Shape(appearance=mat((0.16, 0.13, 0.10), 0.0, 0.9),
                geometry=X.Cylinder(radius=0.026, height=0.006))])
    # lies nearly horizontal, tip toward the viewer's lower-left, opening
    # up-back (a1 aimed the opening at the camera: a lollipop)
    return X.Transform(rotation=(0.80, 0.2, -0.52, 1.65),
                       translation=(0.01, 0.030, 0.01),
                       children=[cone, pepper])


def bread():
    """Torn white roll: crusted low dome + tipped torn piece, pale crumb faces
    toward the light (a1 read as two smooth eggs: flatter now, crumb showing)."""
    crumb = mat((0.92, 0.87, 0.72), 0.0, 0.95, normal_tex="bread_n",
                normal_scale=1.5)
    crust = mat((1, 1, 1), 0.0, 0.58, base_tex="bread_b",
                normal_tex="bread_n", normal_scale=2.2)
    body = X.Group(children=[
        X.Transform(scale=(1.0, 0.55, 0.82), rotation=(0, 1, 0, 0.3), children=[
            X.Shape(appearance=crust, geometry=X.Sphere(radius=0.056))]),
        # the tear: crumb face breaking through the crust on the upper-left flank
        X.Transform(translation=(-0.028, 0.017, 0.020), scale=(0.55, 0.30, 0.45),
                    rotation=(0.2, 0, 1, 0.55),
                    children=[X.Shape(appearance=crumb,
                                      geometry=X.Sphere(radius=0.049))]),
    ])
    # torn-off piece lying beside, crumb face UP-toward the light
    top = X.Transform(translation=(0.080, 0.0, 0.024), rotation=(0, 1, 0, -0.5),
                      children=[
        X.Transform(scale=(0.80, 0.38, 0.62), children=[
            X.Shape(appearance=crust, geometry=X.Sphere(radius=0.048))]),
        X.Transform(translation=(-0.006, 0.010, 0.0), scale=(0.62, 0.22, 0.46),
                    children=[X.Shape(appearance=crumb,
                                      geometry=X.Sphere(radius=0.048))])])
    return X.Group(children=[body, top])


def cruet():
    """Facon-de-Venise wrythen cruet: scalloped bulb, neck, spout, handle.
    Reads as edge-lights only (transparency + IBL) -- by design."""
    petals = 9
    cs = [( (1 + 0.13 * math.cos(petals * 2 * math.pi * k / 36)) * math.cos(2 * math.pi * k / 36),
            (1 + 0.13 * math.cos(petals * 2 * math.pi * k / 36)) * math.sin(2 * math.pi * k / 36))
          for k in range(36)]
    cs.append(cs[0])
    profile = [(0.000, 0.020), (0.006, 0.030), (0.020, 0.042), (0.040, 0.044),
               (0.062, 0.030), (0.072, 0.014), (0.095, 0.011), (0.105, 0.013),
               (0.112, 0.017)]
    spine = [(0.0, y, 0.0) for (y, _r) in profile]
    scale = [(r, r) for (_y, r) in profile]
    body = X.Shape(appearance=M_glass_clear(),
                   geometry=X.Extrusion(crossSection=cs, spine=spine,
                                        scale=scale, creaseAngle=1.4,
                                        beginCap=True, endCap=True, solid=True))
    # collar ring + spout + ear handle
    collar = X.Transform(translation=(0, 0.075, 0), children=[
        X.Shape(appearance=M_glass_clear(),
                geometry=X.Cylinder(radius=0.014, height=0.004))])
    sp = []
    for k in range(8):
        t = k / 7.0
        sp.append((0.030 + 0.030 * t, 0.045 + 0.085 * t ** 1.4, 0.0))
    spout = X.Shape(appearance=M_glass_clear(),
                    geometry=X.Extrusion(crossSection=circle(8, 0.0048),
                                         spine=sp, creaseAngle=1.2,
                                         beginCap=True, endCap=True, solid=True))
    hd = []
    for k in range(9):
        a = math.pi * (0.55 - k / 8.0)
        hd.append((-0.028 - 0.030 * math.cos(a), 0.062 + 0.034 * math.sin(a), 0.0))
    handle = X.Shape(appearance=M_glass_clear(),
                     geometry=X.Extrusion(crossSection=circle(8, 0.004),
                                          spine=hd, creaseAngle=1.2,
                                          beginCap=True, endCap=True, solid=True))
    return X.Group(children=[body, collar, spout, handle])


def salt_cellar():
    """Cylindrical chased pedestal salt, heaped with sparkling salt."""
    profile = [(0.000, 0.036), (0.008, 0.033), (0.014, 0.028), (0.020, 0.030),
               (0.075, 0.030), (0.082, 0.034), (0.088, 0.038), (0.092, 0.036)]
    drum = lathe(profile, M_silver_dull(), n=32)
    heap = X.Transform(translation=(0, 0.086, 0), scale=(1.0, 0.30, 1.0),
                       children=[X.Shape(
                           appearance=mat((0.93, 0.92, 0.88), 0.0, 0.35,
                                          normal_tex="speckle_n", normal_scale=1.4),
                           geometry=X.Sphere(radius=0.031))])
    sparks = X.Group(children=[
        X.Transform(translation=(0.014 * math.cos(a), 0.096 + 0.004 * math.sin(3 * a),
                                 0.014 * math.sin(a)),
                    children=[X.Shape(appearance=mat((1, 1, 1), 0.3, 0.03),
                                      geometry=X.Sphere(radius=0.0018))])
        for a in np.linspace(0, 2 * math.pi, 7, endpoint=False)])
    return X.Group(children=[drum, heap, sparks])


def roemer():
    """The optical centrepiece (research 2.7): Waldglas, 3 rows of raspberry
    prunts, milled collar, ball bowl with white wine. The window lives in the
    IBL's left face; a warm refracted patch is painted low-right in the wine."""
    g = X.Group()
    kids = []
    # coiled foot (mostly hidden): stack of thin tori as squashed spheres
    for i in range(4):
        kids.append(X.Transform(
            translation=(0, 0.004 + i * 0.007, 0), scale=(1.0, 0.28, 1.0),
            children=[X.Shape(appearance=M_glass_g(0.3),
                              geometry=X.Sphere(radius=0.052 - i * 0.004))]))
    # hollow cylindrical stem
    kids.append(lathe([(0.028, 0.040), (0.145, 0.040)], M_glass_g(0.30), n=24))
    # milled collar
    kids.append(X.Transform(translation=(0, 0.150, 0), children=[
        X.Shape(appearance=M_glass_g(0.15),
                geometry=X.Cylinder(radius=0.0435, height=0.007))]))
    # bowl: near-sphere, slightly incurved rim; wine fills ~55%
    kids.append(lathe([(0.152, 0.044), (0.170, 0.062), (0.195, 0.076),
                       (0.225, 0.080), (0.255, 0.072), (0.268, 0.062)],
                      M_glass_g(0.42), n=40, cap_ends=False))
    # wine: lower half of the bowl only, luminous where the window backlights it
    kids.append(X.Transform(translation=(0, 0.172, 0), scale=(1.0, 0.82, 1.0),
                            children=[
        X.Shape(appearance=mat((0.52, 0.52, 0.24), 0.0, 0.10, transparency=0.15,
                               emissive=(0.045, 0.042, 0.010)),
                geometry=X.Sphere(radius=0.067))]))
    # wine surface (the meniscus line)
    kids.append(X.Transform(translation=(0, 0.2265, 0), children=[
        X.Shape(appearance=mat((0.50, 0.48, 0.25), 0.0, 0.06,
                               emissive=(0.012, 0.011, 0.003)),
                geometry=X.Cylinder(radius=0.0645, height=0.002))]))
    # the window-cross mirrored in the bowl upper-left (Bulletin's signature
    # reflection) -- a small emissive decal riding just off the glass
    kids.append(X.Transform(translation=(-0.040, 0.243, 0.058),
                            rotation=(0.35, 0.88, 0.28, -0.62), children=[
        X.Shape(appearance=mat((1, 1, 1), 0.0, 0.4, base_tex="wincross",
                               emissive=(0.55, 0.53, 0.46),
                               emissive_tex="wincross"),
                geometry=X.Rectangle2D(size=(0.020, 0.026)))]))
    # raspberry prunts: 3 rows x 5
    for row in range(3):
        y = 0.048 + row * 0.036
        for k in range(5):
            a = 2 * math.pi * k / 5 + row * 0.55
            kids.append(X.Transform(
                translation=(0.0455 * math.cos(a), y, 0.0455 * math.sin(a)),
                children=[X.Shape(
                    appearance=mat((0.26, 0.32, 0.21), 0.1, 0.08,
                                   normal_tex="speckle_n", normal_scale=1.6),
                    geometry=X.Sphere(radius=0.0088))]))
    g.children = kids
    return g


def tazza_overturned():
    """Drinking tazza LYING ON ITS SIDE, foot toward lower-left, chased bowl
    underside facing the viewer. Bulletin contrast: DULLED bowl vs still-
    POLISHED foot interior; pendant rings hang by gravity."""
    dull, bright = M_silver_dull(), M_silver_bright()
    kids = []
    # trumpet foot: exterior dull, interior (facing viewer when tipped) bright
    kids.append(lathe([(0.000, 0.062), (0.006, 0.058), (0.020, 0.030),
                       (0.035, 0.020)], dull, n=36, cap_ends=False))
    kids.append(lathe([(0.002, 0.056), (0.008, 0.050), (0.022, 0.026),
                       (0.034, 0.018)], bright, n=36, cap_ends=False))
    # baluster stem with berry knop
    kids.append(lathe([(0.035, 0.016), (0.048, 0.024), (0.060, 0.026),
                       (0.072, 0.018), (0.085, 0.014)], dull, n=24))
    for a in (0.6, 2.7):     # two scroll brackets w/ pendant rings
        kids.append(X.Transform(
            translation=(0.024 * math.cos(a), 0.062, 0.024 * math.sin(a)),
            children=[X.Shape(appearance=dull, geometry=X.Sphere(radius=0.006))]))
    # wide shallow bowl -- underside chased: gadroon bosses around a centre boss
    kids.append(lathe([(0.078, 0.022), (0.086, 0.052), (0.094, 0.080),
                       (0.102, 0.096), (0.106, 0.100), (0.108, 0.097)],
                      dull, n=44))
    kids.append(X.Transform(translation=(0, 0.103, 0), scale=(1, 0.30, 1),
                            children=[X.Shape(appearance=dull,
                                              geometry=X.Sphere(radius=0.022))]))
    for k in range(10):
        a = 2 * math.pi * k / 10
        kids.append(X.Transform(
            translation=(0.058 * math.cos(a), 0.100, 0.058 * math.sin(a)),
            scale=(1, 0.22, 1),
            children=[X.Shape(appearance=dull, geometry=X.Sphere(radius=0.0085))]))
    dish = X.Group(children=kids)
    # lay it down: local +y (foot->bowl axis) points up-right and AWAY from the
    # camera, so the chased UNDERSIDE of the bowl faces the viewer (research 2.8)
    d = np.array([0.44, 0.30, -0.90]); d /= np.linalg.norm(d)
    up = np.array([0.0, 1.0, 0.0])
    ax = np.cross(up, d); ax /= np.linalg.norm(ax)
    ang = math.acos(float(np.dot(up, d)))
    # pendant rings dangle below the tipped stem, world-vertical (gravity cue)
    rings = []
    for dx in (-0.010, 0.008):
        pts = [(0.0, 0.007 * math.cos(t) - 0.007, 0.007 * math.sin(t))
               for t in np.linspace(0, 2 * math.pi, 12)]
        rings.append(X.Transform(
            translation=(0.018 + dx, 0.042, -0.026), children=[
                X.Shape(appearance=M_silver_bright(), geometry=X.Extrusion(
                    crossSection=circle(6, 0.0012), spine=pts,
                    creaseAngle=1.4, beginCap=False, endCap=False, solid=False))]))
    return X.Group(children=[
        X.Transform(rotation=(float(ax[0]), float(ax[1]), float(ax[2]), ang),
                    children=[dish]), *rings])


def gilt_cup():
    """The vergulde bokaal (research 2.9): ~0.44 m covered cup, the PEAK of
    the skyline. Fire-gilt orange gold; burnished bands vs pounced grounds via
    the ORM v-bands; Mars-with-pike finial reaching the top of frame."""
    profile = [
        (0.000, 0.052), (0.008, 0.048), (0.020, 0.034), (0.038, 0.020),  # foot
        (0.052, 0.017),
        (0.070, 0.030), (0.088, 0.033), (0.104, 0.022),                  # knop
        (0.118, 0.019), (0.132, 0.024), (0.146, 0.024), (0.158, 0.019),  # medallion band
        (0.172, 0.022), (0.196, 0.046), (0.230, 0.058), (0.268, 0.060),
        (0.292, 0.057),                                                  # cup
        (0.298, 0.064), (0.306, 0.065), (0.312, 0.056),                  # cover flange
        (0.336, 0.044), (0.360, 0.026), (0.372, 0.014),                  # dome
        (0.380, 0.010), (0.388, 0.013), (0.396, 0.009),                  # finial base
    ]
    cup = lathe(profile, M_gilt(), n=40)
    # medallion bosses on the stem band
    bosses = [X.Transform(
        translation=(0.0235 * math.cos(a), 0.139, 0.0235 * math.sin(a)),
        children=[X.Shape(appearance=M_gilt(), geometry=X.Sphere(radius=0.006))])
        for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    # pendant rings at the stem brackets
    rings = []
    for a in (2.2, 4.0):
        pts = [(0.0, 0.006 * math.cos(t), 0.006 * math.sin(t))
               for t in np.linspace(0, 2 * math.pi, 10)]
        rings.append(X.Transform(
            translation=(0.026 * math.cos(a), 0.118, 0.026 * math.sin(a)),
            children=[X.Shape(appearance=M_gilt(), geometry=X.Extrusion(
                crossSection=circle(6, 0.0011), spine=pts, creaseAngle=1.4,
                beginCap=False, endCap=False, solid=False))]))
    # Mars figure + pike -- the picture's highest point
    figure = X.Group(children=[
        X.Transform(translation=(0, 0.412, 0), scale=(0.6, 1.0, 0.5),
                    children=[X.Shape(appearance=M_gilt(),
                                      geometry=X.Sphere(radius=0.009))]),
        X.Transform(translation=(0, 0.426, 0),
                    children=[X.Shape(appearance=M_gilt(),
                                      geometry=X.Sphere(radius=0.0045))]),
        X.Transform(translation=(0.006, 0.432, 0), rotation=(0, 0, 1, -0.10),
                    children=[X.Shape(appearance=M_gilt(),
                                      geometry=X.Cylinder(radius=0.0013,
                                                          height=0.155))]),
    ])
    return X.Group(children=[cup, *bosses, *rings, figure])


def flagon():
    """Pear-bodied pewter flagon, hinged lid OPEN (the jug stands emptied).
    Baked reflections: gold smear of the bokaal + cool window streak."""
    profile = [
        (0.000, 0.072), (0.012, 0.080), (0.032, 0.085), (0.086, 0.086),
        (0.132, 0.078), (0.172, 0.062), (0.212, 0.048), (0.247, 0.042),
        (0.276, 0.041), (0.290, 0.044), (0.297, 0.047),
    ]
    body = lathe(profile, M_pewter_dark(), n=36)
    # open lid: flat dome hinged at the handle side (+x), tipped back ~110 deg
    # -- pivot AT the rim so the lid stays attached (a2 floated it)
    lid = X.Transform(
        translation=(0.044, 0.293, 0.0), rotation=(0, 0, 1, -1.85),
        children=[X.Transform(translation=(-0.044, 0.0, 0), children=[
            lathe([(0.0, 0.047), (0.006, 0.044), (0.012, 0.020),
                   (0.016, 0.008)], M_pewter_plain(), n=28),
        ])])
    thumb = X.Transform(translation=(0.062, 0.291, 0), children=[
        X.Shape(appearance=M_pewter_plain(), geometry=X.Sphere(radius=0.0075)),
        X.Transform(translation=(0.010, 0, 0), children=[
            X.Shape(appearance=M_pewter_plain(), geometry=X.Sphere(radius=0.0075))])])
    # strap handle hugging the +x flank
    sp = []
    for k in range(10):
        t = k / 9.0
        a = math.pi * (0.42 - t * 0.84)
        sp.append((0.058 + 0.036 * math.cos(a),
                   0.260 - 0.175 * t, 0.0))
    handle = X.Shape(appearance=M_pewter_plain(), geometry=X.Extrusion(
        crossSection=[(-0.006, -0.0022), (0.006, -0.0022), (0.006, 0.0022),
                      (-0.006, 0.0022), (-0.006, -0.0022)],
        spine=sp, creaseAngle=1.2, beginCap=True, endCap=True, solid=True))
    return X.Group(children=[body, lid, thumb, handle])


def lemon():
    """Half-peeled lemon on the green carpet; cut face toward the viewer; the
    peel ribbon drops over the front edge in one connected fall (research 2.11)."""
    g = X.Group()
    kids = [
        X.Transform(scale=(1.0, 0.94, 0.96), rotation=(0, 1, 0, 0.4), children=[
            X.Shape(appearance=mat((0.83, 0.70, 0.20), 0.0, 0.45,
                                   normal_tex="speckle_n", normal_scale=0.8),
                    geometry=X.Sphere(radius=0.036))]),
        # peeled top third: pith
        X.Transform(translation=(0.000, 0.011, 0.000), scale=(0.90, 0.74, 0.86),
                    children=[X.Shape(appearance=mat((0.88, 0.85, 0.72), 0.0, 0.9),
                                      geometry=X.Sphere(radius=0.032))]),
        # wet cut face toward the viewer
        X.Transform(translation=(0.0, 0.001, 0.0345), rotation=(1, 0, 0, -0.10),
                    children=[X.Shape(
                        appearance=mat((1, 1, 1), 0.0, 0.10, base_tex="lemon_cut"),
                        geometry=X.Rectangle2D(size=(0.058, 0.058)))]),
    ]
    # the ribbon: one short arc off the fruit's shoulder, then a mostly
    # VERTICAL dangling drop with a single slow twist (research: the peel
    # makes a dead vertical fall -- the a1 spiral read as a yellow cage)
    spine, scale = [], []
    n = 30
    for k in range(n):
        t = k / (n - 1)
        if t < 0.30:
            u = t / 0.30
            a = 1.1 + 1.9 * u
            r = 0.038
            spine.append((r * math.cos(a), 0.012 - 0.030 * u, r * math.sin(a)))
        else:
            u = (t - 0.30) / 0.70
            x0 = 0.038 * math.cos(3.0)
            if u < 0.35:               # slides forward over the carpet to the edge
                w = u / 0.35
                spine.append((x0 + 0.006 * math.sin(3 * w),
                              0.010 - 0.028 * w, 0.005 + 0.140 * w))
            else:                      # clears the edge, drops vertically, one twist
                w = (u - 0.35) / 0.65
                spine.append((x0 + 0.011 * math.sin(3.4 * w + 0.9),
                              -0.018 - 0.30 * w, 0.148 + 0.012 * math.cos(2.6 * w)))
        scale.append((1.0, 1.0))
    peel = X.Shape(
        appearance=mat((1, 1, 1), 0.0, 0.42, base_tex="peel"),
        geometry=X.Extrusion(
            crossSection=[(-0.010, -0.0016), (0.010, -0.0016),
                          (0.010, 0.0016), (-0.010, 0.0016), (-0.010, -0.0016)],
            spine=spine, scale=scale, creaseAngle=1.0,
            beginCap=True, endCap=True, solid=False))
    g.children = kids + [peel]
    return g


def berkemeyer():
    """Overturned berkemeyer, dark Waldglas, lying mouth toward lower-right,
    CROPPED by the right frame edge. One bright streak inside the cone."""
    kids = [
        lathe([(0.000, 0.032), (0.085, 0.032)], M_glass_dark(), n=20),
        lathe([(0.085, 0.033), (0.175, 0.062)], M_glass_dark(), n=24,
              cap_ends=False),
    ]
    kids[0].appearance.material.transparency = 0.35
    kids[1].appearance.material.transparency = 0.35
    for row in range(2):
        y = 0.022 + row * 0.034
        for k in range(4):
            a = 2 * math.pi * k / 4 + row * 0.7
            kids.append(X.Transform(
                translation=(0.033 * math.cos(a), y, 0.033 * math.sin(a)),
                children=[X.Shape(appearance=M_glass_dark(),
                                  geometry=X.Sphere(radius=0.006))]))
    # window streak inside the cone
    kids.append(X.Transform(translation=(0.0, 0.130, 0.012),
                            rotation=(1, 0, 0, 0.35), children=[
        X.Shape(appearance=mat((0.75, 0.78, 0.70), 0.0, 0.3, transparency=0.4,
                               emissive=(0.48, 0.50, 0.42)),
                geometry=X.Rectangle2D(size=(0.010, 0.075)))]))
    glass = X.Group(children=kids)
    # lie on side: axis -> toward lower-right-front, mouth ellipse to camera
    d = np.array([0.76, 0.10, 0.64]); d /= np.linalg.norm(d)
    up = np.array([0.0, 1.0, 0.0])
    ax = np.cross(up, d); ax /= np.linalg.norm(ax)
    ang = math.acos(float(np.dot(up, d)))
    return X.Transform(rotation=(float(ax[0]), float(ax[1]), float(ax[2]), ang),
                       translation=(0, 0.033, 0), children=[glass])


def knife():
    """Piqued knife on the green wedge, handle toward the viewer's right hand.
    Every stud its own specular point (Bulletin)."""
    dark = mat((0.09, 0.065, 0.05), 0.0, 0.25)
    kids = [
        # ricasso peeking from under the napkin
        X.Transform(translation=(-0.085, 0.004, 0), children=[
            X.Shape(appearance=mat((0.60, 0.62, 0.64), 1.0, 0.25),
                    geometry=X.Box(size=(0.05, 0.0035, 0.011)))]),
        # silver bolster
        X.Transform(translation=(-0.052, 0.006, 0), rotation=(0, 0, 1, math.pi / 2),
                    children=[X.Shape(appearance=M_silver_bright(),
                                      geometry=X.Cylinder(radius=0.0085,
                                                          height=0.014))]),
        # tortoiseshell handle
        X.Transform(translation=(0.0, 0.007, 0), rotation=(0, 0, 1, math.pi / 2),
                    children=[X.Shape(appearance=dark,
                                      geometry=X.Cylinder(radius=0.0080,
                                                          height=0.092))]),
        X.Transform(translation=(0.048, 0.007, 0), children=[
            X.Shape(appearance=dark, geometry=X.Sphere(radius=0.0088))]),
    ]
    for i in range(18):
        row = i % 3
        t = (i // 3) / 5.0
        a = (0.9, 1.9, 5.0)[row]        # three rows facing camera-up
        kids.append(X.Transform(
            translation=(-0.040 + t * 0.082,
                         0.007 + 0.0072 * math.sin(a),
                         0.0072 * math.cos(a)),
            children=[X.Shape(appearance=mat((0.95, 0.95, 0.92), 1.0, 0.04),
                              geometry=X.Sphere(radius=0.0022))]))
    return X.Group(children=kids)


def beaker():
    """Plain tumbler of red wine far back-left, almost swallowed by the wall."""
    return X.Group(children=[
        lathe([(0.000, 0.034), (0.010, 0.035), (0.090, 0.038)],
              M_glass_clear(), n=24, cap_ends=False),
        X.Transform(translation=(0, 0.026, 0), children=[
            X.Shape(appearance=mat((0.20, 0.115, 0.05), 0.0, 0.15,
                                   emissive=(0.014, 0.006, 0.002)),
                    geometry=X.Cylinder(radius=0.033, height=0.046))]),
    ])


# ---------------------------------------------------------------- cloths
def napkin_spread():
    """White damask laid over the carpet on the LEFT half, pressed crease
    grid, falling over the front edge in long straight folds."""
    nx, nt = 40, 34
    x0, x1 = -0.53, 0.06
    L_on, L_hang = 0.62, 0.24    # drop stops short of frame bottom: the dark
    # under-table strip must show (painting keeps a ~4% dark band)
    edge_z = TABLE_FRONT - 0.002
    pts, tex = [], []
    for j in range(nt):
        t = j / (nt - 1) * (L_on + L_hang)
        hang = max(0.0, t - L_on)
        for i in range(nx):
            u = i / (nx - 1)
            x = x0 + u * (x1 - x0)
            if t <= L_on:
                z = edge_z - L_on + t
                y = 0.006
                # pressed crease ridges (the grid) -- gentle triangular lifts
                for cx in (-0.415, -0.235, -0.055):
                    y += 0.009 * max(0.0, 1.0 - abs(x - cx) / 0.05)
                for cz in (edge_z - 0.44, edge_z - 0.18):
                    y += 0.007 * max(0.0, 1.0 - abs(z - cz) / 0.045)
            else:
                sag = hang / L_hang
                # long straight vertical folds -- rounded, irregularly spaced
                ph = 2 * math.pi * u
                fold = (0.55 * math.cos(ph * 3.1 + 0.4)
                        + 0.45 * math.cos(ph * 1.7 + 2.1))
                fold = (fold + 1.0) * 0.5
                z = edge_z + 0.010 + 0.058 * fold * (0.30 + 0.70 * sag)
                x += 0.026 * math.sin(ph * 3.1 + 0.4) * sag
                y = 0.006 - max(0.0, hang - 0.012) * 0.95
            pts.append((round(x, 4), round(y, 4), round(z, 4)))
            # v = 1 - t/total. PROBED (scratchpad vprobe.png): X_ITE follows
            # the spec -- v=1 samples the image TOP row -- so cloth-t growing
            # toward the hem must map to v falling toward 0, aligning the
            # authored fold shading + hem with the hanging drop.
            tex.append((round(u, 4), round(1.0 - t / (L_on + L_hang), 4)))
    idx = []
    for j in range(nt - 1):
        for i in range(nx - 1):
            a = j * nx + i
            idx += [a, a + 1, a + nx + 1, a + nx, -1]
    return X.Shape(
        appearance=M_napkin_spread(),
        geometry=X.IndexedFaceSet(
            coord=X.Coordinate(point=pts),
            texCoord=X.TextureCoordinate(point=tex),
            coordIndex=idx, solid=False, creaseAngle=1.2, ccw=True))


def napkin_crumpled():
    """Bunched napkin centre-right: carries the tazza, then cascades over the
    front edge in a bright triangular waterfall. Hem inscription rides at v~1."""
    rng = np.random.default_rng(1635)
    nx, nt = 34, 30
    x0, x1 = -0.01, 0.40
    L_on, L_hang = 0.30, 0.26
    edge_z = TABLE_FRONT - 0.002
    bumps = [(rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.85),
              rng.uniform(0.012, 0.038), rng.uniform(0.05, 0.11))
             for _ in range(9)]
    pts, tex = [], []
    for j in range(nt):
        t = j / (nt - 1) * (L_on + L_hang)
        hang = max(0.0, t - L_on)
        for i in range(nx):
            u = i / (nx - 1)
            x = x0 + u * (x1 - x0)
            if t <= L_on:
                z = edge_z - L_on + t
                y = 0.009
                for (bu, bt, amp, sig) in bumps:
                    d2 = ((u - bu) * (x1 - x0)) ** 2 + ((t / L_on - bt) * L_on) ** 2
                    y += amp * math.exp(-d2 / (sig ** 2))
                # flatten where the tazza lies and where the knife lies
                d_tz = math.sqrt((x - 0.16) ** 2 + (z - 0.14) ** 2)
                y = min(y, 0.014 + 0.16 * d_tz)
                d_kn = math.sqrt((x - 0.14) ** 2 + (z - 0.31) ** 2)
                y = min(y, 0.012 + 0.18 * d_kn)
            else:
                sag = hang / L_hang
                ph = 2 * math.pi * u
                fold = (0.6 * math.cos(ph * 2.3 + 1.1)
                        + 0.4 * math.cos(ph * 1.3 + 0.2))
                fold = (fold + 1.0) * 0.5
                z = edge_z + 0.012 + 0.062 * fold * (0.25 + 0.75 * sag) \
                    * (1.0 - 0.25 * sag)
                y = 0.010 - max(0.0, hang - 0.014) * 0.92
                x += 0.022 * math.sin(ph * 2.3 + 1.1) * sag
            pts.append((round(x, 4), round(y, 4), round(z, 4)))
            # v = 1 - t/total, probed orientation -- see napkin_spread
            tex.append((round(u, 4), round(1.0 - t / (L_on + L_hang), 4)))
    idx = []
    for j in range(nt - 1):
        for i in range(nx - 1):
            a = j * nx + i
            idx += [a, a + 1, a + nx + 1, a + nx, -1]
    return X.Shape(
        appearance=M_napkin_crumpled(),
        geometry=X.IndexedFaceSet(
            coord=X.Coordinate(point=pts),
            texCoord=X.TextureCoordinate(point=tex),
            coordIndex=idx, solid=False, creaseAngle=1.2, ccw=True))


# ---------------------------------------------------------------- stage
def table_and_wall():
    return X.Group(children=[
        # green carpet over the whole table
        X.Transform(translation=((TABLE_LEFT + TABLE_RIGHT) / 2, -0.016,
                                 (TABLE_FRONT + TABLE_BACK) / 2),
                    children=[X.Shape(
                        appearance=M_carpet(),
                        geometry=X.Box(size=(TABLE_RIGHT - TABLE_LEFT, 0.032,
                                             TABLE_FRONT - TABLE_BACK)))]),
        # carpet drop over the front edge (dark -- in shadow)
        X.Transform(translation=((TABLE_LEFT + TABLE_RIGHT) / 2, -0.19,
                                 TABLE_FRONT + 0.002),
                    children=[X.Shape(
                        appearance=mat((0.055, 0.075, 0.05), 0.0, 0.9),
                        geometry=X.Box(size=(TABLE_RIGHT - TABLE_LEFT, 0.35,
                                             0.008)))]),
        # carpet sliver over the right end of the table
        X.Transform(translation=(TABLE_RIGHT + 0.002, -0.12, 0.0),
                    children=[X.Shape(
                        appearance=mat((0.05, 0.068, 0.045), 0.0, 0.9),
                        geometry=X.Box(size=(0.008, 0.22,
                                             TABLE_FRONT - TABLE_BACK)))]),
        # under-table darkness: a flat near-black band, no floor detail
        X.Transform(translation=(0, -0.62, TABLE_FRONT - 0.06), children=[
            X.Shape(appearance=mat((0.035, 0.030, 0.026), 0.0, 1.0,
                                   emissive=(0.030, 0.026, 0.022)),
                    geometry=X.Box(size=(4.0, 0.9, 0.05)))]),
        # junction shadow: a thin dark strip where table meets wall
        X.Transform(translation=((TABLE_LEFT + TABLE_RIGHT) / 2, 0.004,
                                 TABLE_BACK + 0.012), children=[
            X.Shape(appearance=mat((0.02, 0.025, 0.018), 0.0, 1.0,
                                   transparency=0.35),
                    geometry=X.Box(size=(TABLE_RIGHT - TABLE_LEFT, 0.006,
                                         0.024)))]),
        # the wall: BAKED gradient, emissive-only (authored values). Sized to
        # the VISIBLE region so the halo actually spans the frame (a2 showed
        # a thin uniform slice of a 2.9 m-tall texture).
        X.Transform(translation=(0.0, 0.62, WALL_Z), children=[
            X.Shape(appearance=M_wall(),
                    geometry=X.Rectangle2D(size=(3.2, 1.5)))]),
    ])


# ---------------------------------------------------------------- assembly
def arrangement():
    """One connected frieze (research §4.1): every object overlaps its
    neighbour; skyline staircases to the bokaal, steps down once, falls to
    the cropped berkemeyer."""
    return X.Group(children=[
        # ---- baked shadows (light from upper-left => lobes fall right/front)
        *contact(-0.20, 0.10, 0.180, strength=0.62, lift=0.010, height=0.02),  # charger
        *contact(-0.40, 0.34, 0.105, strength=0.55, lift=0.010, height=0.02),  # shell plate
        *contact(-0.30, -0.10, 0.040, strength=0.55, height=0.09),             # beaker
        *contact(-0.15, -0.09, 0.048, strength=0.55, height=0.11),             # cruet
        *contact(-0.03, -0.07, 0.040, strength=0.60, height=0.10),             # salt
        *contact(0.065, 0.0, 0.055, strength=0.65, lift=0.008, height=0.26),   # roemer
        *contact(0.16, 0.14, 0.115, rz=0.085, strength=0.55, lift=0.030),      # tazza (on cloth)
        *contact(0.24, -0.11, 0.058, strength=0.70, height=0.42),              # gilt cup
        *contact(0.42, -0.13, 0.090, strength=0.62, height=0.30),              # flagon
        *contact(0.46, 0.26, 0.042, strength=0.55, height=0.05),               # lemon
        *contact(0.58, 0.16, 0.075, rz=0.045, strength=0.50),                  # berkemeyer
        *contact(-0.10, 0.24, 0.105, strength=0.5, lift=0.008, height=0.02),   # bread plate
        # broad soft shade over the exposed carpet right of the tableau --
        # the painting keeps that zone near-black (research 1.4 "what stays dark")
        *contact(0.38, 0.02, 0.30, rz=0.16, strength=0.34, lift=0.0008),
        *contact(0.52, 0.22, 0.22, rz=0.13, strength=0.30, lift=0.0008),

        # ---- the cloths (the stage)
        napkin_spread(),
        napkin_crumpled(),

        # ---- left-to-right frieze
        X.Transform(translation=(-0.30, 0, -0.10), children=[beaker()]),
        X.Transform(translation=(-0.20, 0.006, 0.10), children=[charger()]),
        # oysters on the charger + loose on the cloth
        X.Transform(translation=(-0.28, 0.020, 0.08), children=[oyster(ang=0.5)]),
        X.Transform(translation=(-0.18, 0.020, 0.03), children=[oyster(ang=2.2)]),
        X.Transform(translation=(-0.11, 0.020, 0.10), children=[oyster(ang=4.0)]),
        X.Transform(translation=(-0.23, 0.020, 0.16), children=[oyster(ang=1.3)]),
        X.Transform(translation=(-0.14, 0.020, 0.17), children=[oyster(ang=5.2)]),
        X.Transform(translation=(-0.34, 0.014, 0.21), children=[oyster(ang=3.1)]),
        X.Transform(translation=(-0.05, 0.012, 0.26), children=[oyster(ang=0.9)]),
        # shell plate OVERHANGING the front edge (the repoussoir)
        X.Transform(translation=(-0.40, 0.014, 0.34), rotation=(1, 0, 0, -0.04),
                    children=[
            plate(r=0.105),
            X.Transform(translation=(-0.030, 0.020, -0.020), children=[oyster(False, 1.1)]),
            X.Transform(translation=(0.030, 0.020, 0.020), children=[oyster(False, 3.9)]),
            X.Transform(translation=(0.010, 0.024, -0.045), children=[oyster(False, 5.5)]),
            X.Transform(translation=(0.015, 0.0, 0.030), children=[paper_cone()]),
        ]),
        # bread on its plate, torn open, centre-front
        X.Transform(translation=(-0.10, 0.008, 0.24), children=[
            plate(r=0.105),
            X.Transform(translation=(-0.01, 0.022, 0.0), rotation=(0, 1, 0, 0.4),
                        children=[bread()])]),
        # back row: cruet, salt (touching the roemer)
        X.Transform(translation=(-0.15, 0, -0.09), rotation=(0, 1, 0, 0.5),
                    children=[cruet()]),
        X.Transform(translation=(-0.03, 0, -0.07), children=[salt_cellar()]),
        # the roemer
        X.Transform(translation=(0.065, 0, 0.0), children=[roemer()]),
        # overturned tazza ON the crumpled napkin
        X.Transform(translation=(0.13, 0.026, 0.16), children=[tazza_overturned()]),
        # the gilt cup -- the peak
        X.Transform(translation=(0.24, 0, -0.11), children=[gilt_cup()]),
        # pewter flagon behind/right, lid open
        X.Transform(translation=(0.42, 0, -0.13), rotation=(0, 1, 0, -0.4),
                    children=[flagon()]),
        # lemon on the carpet, peel dropping over the edge
        X.Transform(translation=(0.46, 0.034, 0.26), children=[lemon()]),
        # berkemeyer, cropped by the right frame edge
        X.Transform(translation=(0.58, 0.0, 0.14), children=[berkemeyer()]),
        # knife ON the crumpled napkin, pointing at the viewer
        X.Transform(translation=(0.13, 0.020, 0.31), rotation=(0, 1, 0, -0.45),
                    children=[knife()]),
    ])


# ---------------------------------------------------------------- light
def lights():
    """One window key (cool, upper-left, soft-ish) + the authored IBL cubemap
    (reflections AND derived ambience) + a weak warm right-wall bounce."""
    t = textures()
    cube = X.ComposedCubeMapTexture(
        DEF="CUBE_ENV",
        frontTexture=_img("CMF_front_", t["cube_front"]),
        backTexture=_img("CMF_back_", t["cube_back"]),
        leftTexture=_img("CMF_left_", t["cube_left"]),
        rightTexture=_img("CMF_right_", t["cube_right"]),
        topTexture=_img("CMF_top_", t["cube_top"]),
        bottomTexture=_img("CMF_bottom_", t["cube_bottom"]))
    return X.Group(children=[
        X.EnvironmentLight(color=(1.0, 0.97, 0.92), intensity=0.82,
                           specularTexture=cube),
        # the casement key: azimuth ~40 deg left, elevation ~35 deg, cool
        X.SpotLight(location=(-1.55, 1.45, 1.15),
                    direction=(0.71, -0.55, -0.44),
                    color=(1.0, 0.965, 0.90), intensity=12.5,
                    beamWidth=0.5, cutOffAngle=0.95,
                    radius=8.0, attenuation=(0.4, 0.28, 0.0), global_=True),
        # weak warm bounce off the right wall (key:fill ~ 4:1)
        X.PointLight(location=(1.5, 0.45, 0.55), color=(1.0, 0.80, 0.58),
                     intensity=0.70, radius=5.0, attenuation=(0.7, 0.7, 0.0),
                     global_=True),
        # faint warm lift from the cloth up into the metal undersides
        X.PointLight(location=(0.1, -0.05, 0.9), color=(1.0, 0.85, 0.62),
                     intensity=0.25, radius=4.0, attenuation=(0.8, 0.9, 0.0),
                     global_=True),
    ])


# ---------------------------------------------------------------- provenance
def provenance_node():
    return X.WorldInfo(
        title="pronk -- after Heda, Still Life with a Gilt Cup (1635)",
        metadata=X.MetadataSet(
            name="provenance",
            value=[
                X.MetadataString(name="provenance", value=["interpretive"]),
                X.MetadataString(name="sourceCitation", value=[
                    "Willem Claesz Heda, 'Still Life with a Gilt Cup', 1635 "
                    "(signed), oil on panel, 87.8 x 112.6 cm, Rijksmuseum, "
                    "Amsterdam, SK-A-4830, "
                    "https://www.rijksmuseum.nl/en/collection/SK-A-4830"]),
                X.MetadataString(name="catalogId", value=["SK-A-4830"]),
                X.MetadataString(name="publicDomain", value=["true"]),
                X.MetadataString(name="generationMethod", value=[
                    "Procedurally authored with x3d.py 4.0.65.3 by Claude "
                    "(pronk.py v" + VERSION + "): composition, palette and light "
                    "rebuilt to the painting's own construction as measured in "
                    "research/pronk.md (one overlapping frieze, low horizon, "
                    "rising diagonal to the gilt cup, cropped berkemeyer, "
                    "baked wall gradient and shadows, window-key + authored "
                    "IBL cubemap). A 3D interpretation of the painting's "
                    "arrangement and light; not a measurement or scan of the "
                    "artwork. In-scene provenance carriers: printed almanac "
                    "page (pepper cone) and napkin-hem inscription, after "
                    "Heda's own signature placement."]),
            ]))


# ---------------------------------------------------------------- scene
def build_scene(viewpoint=None):
    if viewpoint is None:
        viewpoint = VIEWS[0][1]
    pos, ori, desc = viewpoint
    scene = X.Scene(children=[
        provenance_node(),
        X.NavigationInfo(headlight=False, type=["EXAMINE", "ANY"]),
        X.Background(skyColor=[BG_RGB]),
        X.Viewpoint(position=pos, orientation=ori, description=desc,
                    fieldOfView=0.454),
        lights(),
        table_and_wall(),
        arrangement(),
    ])
    return X.X3D(
        profile="Immersive", version="4.0",
        head=X.head(children=[
            X.component(name="CubeMapTexturing", level=3),
            X.component(name="Lighting", level=4),
            X.component(name="Shape", level=4),
            X.component(name="TextureProjection", level=2),
            X.meta(name="title", content="pronk.x3d"),
            X.meta(name="description",
                   content="Interpretive still life after Heda SK-A-4830"),
            X.meta(name="generator",
                   content=f"pronk.py v{VERSION}, x3d.py 4.0.65.3"),
            X.meta(name="rights", content="source painting: Public Domain "
                   "(CC PDM 1.0), Rijksmuseum SK-A-4830"),
        ]),
        Scene=scene)


# ---------------------------------------------------------------- patch pass
def _patch(xml: str) -> str:
    """Everything x3d.py cannot say, injected + ASSERTED (silent regressions
    must fail the build, not ship):
      1. <component name='X_ITE' level='1'/> -- x3d.py whitelist refuses it,
         X_ITE requires it for the glTF material extension nodes.
      2. containerField='value' on MetadataSet members (the original hole).
      3. containerField on every texture slot: PhysicalMaterial slots,
         EnvironmentLight.specularTexture, ComposedCubeMapTexture faces
         (serializer omits ALL of these and alphabetises the faces).
      4. global='true' on EnvironmentLight (default-True is omitted, X_ITE
         then scopes the light).
      5. Sheen / Iridescence extension nodes into DEF'd PhysicalMaterials."""
    # 1 -- the X_ITE component
    assert "<head>" in xml
    xml = xml.replace("<head>", "<head><component name='X_ITE' level='1'/>", 1)
    assert xml.count("component name='X_ITE'") == 1

    # 2 -- metadata containerField
    want = xml.count("<MetadataString ")
    xml = xml.replace("<MetadataString ", "<MetadataString containerField='value' ")
    assert want >= 5 and xml.count("containerField='value'") == want, \
        f"provenance patch failed: {want} MetadataString"

    # 3 -- texture slots by DEF prefix
    for prefix, slot in _TEX_SLOT_PREFIX.items():
        n = len(re.findall(rf"<ImageTexture (?=[^>]*DEF='{prefix})", xml))
        xml = re.sub(rf"<ImageTexture (?=[^>]*DEF='{prefix})",
                     f"<ImageTexture containerField='{slot}' ", xml)
        got = xml.count(f"containerField='{slot}'")
        assert got == n, f"{slot}: wanted {n}, patched {got}"
    for side in ("front", "back", "left", "right", "top", "bottom"):
        n = len(re.findall(rf"<ImageTexture (?=[^>]*DEF='CMF_{side}_)", xml))
        xml = re.sub(rf"<ImageTexture (?=[^>]*DEF='CMF_{side}_)",
                     f"<ImageTexture containerField='{side}Texture' ", xml)
        assert n == 1 and xml.count(f"containerField='{side}Texture'") == 1, \
            f"cubemap {side} face: {n}"
    n = len(re.findall(r"<ComposedCubeMapTexture (?=[^>]*DEF='CUBE_ENV')", xml))
    xml = re.sub(r"<ComposedCubeMapTexture (?=[^>]*DEF='CUBE_ENV')",
                 "<ComposedCubeMapTexture containerField='specularTexture' ", xml)
    assert n == 1 and xml.count("containerField='specularTexture'") == 1

    # 4 -- EnvironmentLight global
    n = xml.count("<EnvironmentLight ")
    xml = xml.replace("<EnvironmentLight ", "<EnvironmentLight global='true' ")
    assert n == 1 and xml.count("<EnvironmentLight global='true'") == 1

    # 5 -- material extensions
    for defname, ext in SHEEN_DEFS:
        m = re.search(rf"<PhysicalMaterial (?=[^>]*DEF='{defname}')([^>]*?)(/?)>", xml)
        assert m, f"extension target {defname} not found"
        if m.group(2) == "/":
            xml = (xml[:m.start()] + f"<PhysicalMaterial {m.group(1).rstrip()}>"
                   f"{ext}</PhysicalMaterial>" + xml[m.end():])
        else:
            xml = xml[:m.end()] + ext + xml[m.end():]
    for defname, ext in SHEEN_DEFS:
        tag = ext.split()[0]
        assert tag.lstrip("<") in xml, f"extension {tag} missing after patch"
    return xml


def scene_builder(vp):
    """lookdev.py entry point: vp=(pos, orientation, desc) -> patched XML."""
    SHEEN_DEFS.clear()
    return _patch(build_scene(vp).XML())


# camera: square-on, eye ~0.50 m over the tabletop (charger ellipse ~1:3.6),
# ~1.9 m back, vfov 26 deg -- the painting's own narrow-lens vantage. The
# narrow FOV is what compresses the tabletop into a shallow wedge while the
# pike finial grazes the top of frame (Heda's trick, measured in research 1.1)
_EYE = (0.0, 0.50, 1.93)
VIEWS = [
    ("hero", (_EYE, look_at(_EYE, (0.0, 0.065, -0.10)),
              "hero -- the painting's own vantage")),
    ("three_q", ((-0.85, 0.55, 1.55),
                 look_at((-0.85, 0.55, 1.55), (0.05, 0.10, 0.0)),
                 "three-quarter from the key side")),
    ("raking", ((1.05, 0.22, 1.30),
                look_at((1.05, 0.22, 1.30), (-0.05, 0.14, 0.0)),
                "low raking view from the shadow side")),
]


if __name__ == "__main__":
    xml = scene_builder(VIEWS[0][1])
    with open(OUT_X3D, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"pronk.py v{VERSION} -> {OUT_X3D}  ({len(xml)} bytes)")
