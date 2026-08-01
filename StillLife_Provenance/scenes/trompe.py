#!/usr/bin/env python3
"""
trompe.py -- generator for trompe.x3d
================================================================================
VERSION 7 (recompose) · 2026-07-30 · EUPHEME Technologies LLC

An interpretive X3D 4.0 still life after:
  Cornelius Norbertus Gijsbrechts, "Trompe l'oeil. Board Partition with Letter
  Rack and Music Book" (1668), SMK Copenhagen, KMS3059 (public domain, CC PDM 1.0)
  https://open.smk.dk/en/artwork/image/KMS3059

v7 RECOMPOSE -- built to research/trompe.md, measured off the SMK IIIF master:
  * canvas-fraction coordinate system (1:1 natural size, 1.07 x 1.235 m);
  * flat pine board COMPLETE inside a near-black surround with gilt tack rows;
    all frame-breaking is internal (over the board's own edges), never at the
    viewport edge -- that is what makes it read as an object on a wall;
  * red linen-tape GRID (3 verticals, 3 horizontals, corner diagonal) with
    dome nails at the crossings; every paper rotated, bowed, never flat;
  * the curtain's leading edge IS the dominant diagonal (0.36,0.05)->(0.86,0.95),
    dark green silk, gold selvage, folds fanned along the drape, bellies <=10 cm;
  * one warm raking key upper-left; every shadow BAKED as a soft umber
    alpha-textured quad offset down-right ~1.7x standoff (X_ITE ignores
    light.shadows -- and hard translucent boxes read as CG);
  * IBL: one authored warm cubemap on EnvironmentLight.specularTexture
    (reflections on wax/iron/glass + derived ambience);
  * Sheen extension on the velvet comb case and the silk curtain (raw-XML
    injection, needs the X_ITE component head line).

CRAFT NOTES (hard-won, do not regress):
  * x3d.py 4.0.65.3 has NO containerField support. PhysicalMaterial texture
    slots, MetadataSet member values, EnvironmentLight.specularTexture and
    ComposedCubeMapTexture face slots are ALL emitted bare (faces also get
    alphabetically scrambled). _patch_xml() rewrites the XML with lxml after
    serialization and ASSERTS every patch count. Never remove it.
  * glTF material extensions (Sheen here) need <component name='X_ITE'
    level='1'/> which x3d.py REFUSES to emit (whitelist) -> injected.
  * Soft shadows: RGBA blob/band textures on PhysicalMaterial.baseTexture DO
    alpha-blend (probed 2026-07-30, mad 0.0032, clean soft edge). This is the
    umber-shadow path; keep shadows warm, never grey.
  * Viewpoint description is baked into headless captures as a UI toast --
    omit it on the bound viewpoint.
"""

import base64
import io
import math
import os
import random
import sys

sys.path.insert(0, os.path.expanduser("~/x3d_mcp/src"))

from x3d import x3d
from lxml import etree

VERSION = "7"
HERE = os.path.dirname(os.path.abspath(__file__))
TEXDIR = os.path.join(HERE, "textures")

BG = (0.020, 0.017, 0.014)          # authored background -- pass to analyse()

DEG = math.pi / 180.0

# ---------------------------------------------------------------- canvas frame
# Canvas at natural size: 107 cm wide x 123.5 cm tall, centered on origin,
# x right, y up, board FRONT face at z = 0. Positions in research/trompe.md are
# (fx, fy) fractions of canvas width/height, origin TOP-LEFT.
CW, CHT = 1.07, 1.235


def P(fx, fy):
    return ((fx - 0.5) * CW, (0.5 - fy) * CHT)


# board region (fractions, from the research file)
BD_L, BD_R, BD_T, BD_B = 0.055, 0.970, 0.060, 0.925


def curtain_edge_x(fy):
    """fx of the curtain's leading edge at height fy -- the dominant diagonal."""
    return 0.36 + (0.86 - 0.36) * (fy - 0.05) / 0.90


# key light direction (world): warm, upper-left, elevation ~37 deg.
KEY_DIR = (0.678, -0.547, -0.492)
# baked shadow offset per meter of standoff (shadow falls DOWN-RIGHT)
SH_DX, SH_DY = 1.35, -1.05

# ------------------------------------------------------------------ textures
_TEX = {}


def _data_uri(im):
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _save(im, name):
    os.makedirs(TEXDIR, exist_ok=True)
    im.save(os.path.join(TEXDIR, name))
    uri = _data_uri(im)
    _TEX[name] = uri
    return uri


def _font(size, italic=False):
    from PIL import ImageFont
    cands = ([
        "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    ] if italic else [
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ])
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def tex_plank_wall():
    """5 vertical deal planks with the painting's light BAKED IN: brightest
    center-left where the paper cluster lives, umber falloff to lower-right,
    darkened edges. The wall is flat, so NdotL is constant -- the vignette is
    the only way the light can 'fall' across it."""
    if "plank_wall.png" in _TEX:
        return _TEX["plank_wall.png"]
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np
    rng = random.Random(1668)
    W, H = 1024, 1024
    im = Image.new("RGB", (W, H), (214, 199, 162))
    d = ImageDraw.Draw(im)
    for x in range(W):                                   # vertical grain field
        v = int(9 * math.sin(x * 0.061) + 6 * math.sin(x * 0.017 + 2.1)
                + rng.uniform(-5, 5))
        d.line([(x, 0), (x, H)], fill=(214 + v // 2, 199 + v // 2, 162 + v // 3))
    for _ in range(120):                                 # long wavering grain
        x0 = rng.uniform(0, W)
        amp = rng.uniform(1.5, 6)
        ph = rng.uniform(0, 6.28)
        col = (188, 170, 136) if rng.random() < 0.5 else (170, 150, 116)
        pts = [(x0 + amp * math.sin(y * 0.008 + ph), y) for y in range(0, H, 8)]
        d.line(pts, fill=col, width=1)
    for kx, ky in [(150, 300), (470, 760), (860, 450), (300, 940)]:   # knots
        for r in range(12, 2, -2):
            c = 148 - (12 - r) * 8
            d.ellipse([kx - r, ky - int(r * 1.6), kx + r, ky + int(r * 1.6)],
                      outline=(c, c - 22, c - 45), width=2)
        d.ellipse([kx - 3, ky - 5, kx + 3, ky + 5], fill=(96, 74, 50))
    for _ in range(8):                                   # rubbed stains
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(40, 130)
        ov = Image.new("L", (W, H), 0)
        ImageDraw.Draw(ov).ellipse([x - r, y - r * 1.6, x + r, y + r * 1.6],
                                   fill=18)
        ov = ov.filter(ImageFilter.GaussianBlur(30))
        im = Image.composite(Image.new("RGB", (W, H), (166, 148, 116)), im, ov)
    d = ImageDraw.Draw(im)
    seam_x = [int(W * i / 5) for i in range(1, 5)]       # 4 seams -> 5 planks
    for i in range(5):
        x0 = 0 if i == 0 else seam_x[i - 1]
        x1 = W if i == 4 else seam_x[i]
        tint = rng.randint(-8, 8)
        strip = im.crop((x0, 0, x1, H)).point(
            lambda p, t=tint: max(0, min(255, p + t)))
        im.paste(strip, (x0, 0))
    d = ImageDraw.Draw(im)
    for sx in seam_x:
        d.line([(sx, 0), (sx, H)], fill=(110, 90, 64), width=3)
        d.line([(sx + 2, 0), (sx + 2, H)], fill=(198, 182, 148), width=1)
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    # --- baked light: bright zone center-left, umber falloff lower-right
    a = np.asarray(im).astype(float)
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = xx / W, yy / H
    bright = np.exp(-(((u - 0.30) ** 2) / 0.32 + ((v - 0.33) ** 2) / 0.45))
    field = 0.64 + 0.48 * bright
    edge = np.clip(1.0 - 2.4 * np.minimum.reduce(
        [u, 1 - u, v, 1 - v]), 0, 1) ** 2
    field *= (1.0 - 0.16 * edge)
    a[..., 0] *= field
    a[..., 1] *= field * (1 - 0.05 * (1 - bright))       # shadows go warm/umber
    a[..., 2] *= field * (1 - 0.12 * (1 - bright))
    im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
    return _save(im, "plank_wall.png")


def tex_plank_normal():
    """Subtle vertical-grain + seam-groove normal map for the raking key."""
    if "plank_normal.png" in _TEX:
        return _TEX["plank_normal.png"]
    from PIL import Image, ImageFilter
    import numpy as np
    rng = np.random.default_rng(1668)
    W = 512
    h = rng.normal(0, 1, (W, W))
    h = np.asarray(Image.fromarray(
        ((h - h.min()) / (np.ptp(h) + 1e-9) * 255).astype("uint8")).filter(
            ImageFilter.GaussianBlur(2)), float) / 255.0
    xx = np.arange(W)
    h += 0.35 * np.sin(xx[None, :] * 0.35)               # fine vertical grain
    for sx in [int(W * i / 5) for i in range(1, 5)]:     # seam grooves
        dist = np.abs(xx[None, :] - sx)
        h -= 0.9 * np.exp(-(dist ** 2) / 18.0)
    gx = np.gradient(h, axis=1)
    gy = np.gradient(h, axis=0)
    k = 90.0
    n = np.stack([128 - gx * k, 128 + gy * k, np.full_like(h, 255)], -1)
    im = Image.fromarray(np.clip(n, 0, 255).astype("uint8"))
    return _save(im, "plank_normal.png")


def tex_shadow_rect():
    """Soft umber rounded-rect shadow, RGBA. THE baked-shadow workhorse."""
    if "shadow_rect.png" in _TEX:
        return _TEX["shadow_rect.png"]
    from PIL import Image, ImageDraw, ImageFilter
    W = 256
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([46, 46, W - 46, W - 46], radius=34,
                        fill=(48, 30, 12, 210))
    im = im.filter(ImageFilter.GaussianBlur(20))
    return _save(im, "shadow_rect.png")


def tex_shadow_blob():
    if "shadow_blob.png" in _TEX:
        return _TEX["shadow_blob.png"]
    from PIL import Image, ImageDraw, ImageFilter
    W = 256
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([52, 62, W - 52, W - 62], fill=(48, 30, 12, 205))
    im = im.filter(ImageFilter.GaussianBlur(24))
    return _save(im, "shadow_blob.png")


def tex_shadow_band():
    """Gradient band for the curtain's broad cast shadow: strongest at the
    curtain edge (right side of texture), fading to nothing lower-left."""
    if "shadow_band.png" in _TEX:
        return _TEX["shadow_band.png"]
    from PIL import Image
    import numpy as np
    W, H = 128, 16
    a = np.zeros((H, W, 4), dtype="uint8")
    x = np.arange(W) / (W - 1)
    alpha = (np.clip((x - 0.15) / 0.85, 0, 1) ** 1.6 * 220).astype("uint8")
    a[..., 0], a[..., 1], a[..., 2] = 44, 28, 12
    a[..., 3] = alpha[None, :]
    return _save(Image.fromarray(a), "shadow_band.png")


def tex_letter(seed=7, script=True, dense=False):
    """A folded letter packet: creases, address script or letterpress, foxing."""
    name = f"letter_{seed}_{int(script)}{int(dense)}.png"
    if name in _TEX:
        return _TEX[name]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(seed)
    W, H = 256, 192
    im = Image.new("RGB", (W, H), (225, 214, 188))
    d = ImageDraw.Draw(im)
    for _ in range(350):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        v = rng.randint(-10, 6)
        d.point((x, y), fill=(225 + v, 214 + v, 188 + v))
    fy, fx = H // 2 + rng.randint(-8, 8), W // 2 + rng.randint(-10, 10)
    d.line([(0, fy), (W, fy)], fill=(198, 186, 158), width=2)
    d.line([(0, fy + 2), (W, fy + 2)], fill=(236, 228, 206), width=1)
    d.line([(fx, 0), (fx, H)], fill=(203, 191, 163), width=2)
    if dense:                                            # letterpress pamphlet
        y = 18
        while y < H - 14:
            x = 22
            while x < W - 22:
                wseg = rng.randint(6, 20)
                d.rectangle([x, y, x + wseg, y + 5], fill=(64, 54, 44))
                x += wseg + rng.randint(3, 7)
            y += 11
    elif script:                                         # iron-gall address
        y = 44
        for ln in range(3):
            x = 46 + ln * 12
            pts = []
            while x < W - 50 - ln * 10:
                pts.append((x, y + 6 * math.sin(x * 0.20 + ln)
                            * rng.uniform(0.4, 1)))
                x += 4
            d.line(pts, fill=(88, 70, 52), width=2)
            y += 28
    for _ in range(rng.randint(2, 5)):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(2, 6)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(206, 186, 150))
    d.rectangle([0, 0, W - 1, H - 1], outline=(190, 178, 150), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    return _save(im, name)


def tex_music_page(seed):
    """One page of hand-ruled staves, slightly wavy, dense notation."""
    name = f"music_{seed}.png"
    if name in _TEX:
        return _TEX[name]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(seed)
    W, H = 256, 340
    im = Image.new("RGB", (W, H), (230, 221, 196))
    d = ImageDraw.Draw(im)
    for g in range(6):                                   # 6 staff systems
        top = 22 + g * 52
        for ln in range(5):
            pts = [(x, top + ln * 5 + 1.6 * math.sin(x * 0.05 + g + ln))
                   for x in range(16, W - 16, 4)]
            d.line(pts, fill=(112, 98, 78), width=1)
        x = 24
        while x < W - 26:                                # notes + stems
            yy = top + rng.randint(-2, 22)
            d.ellipse([x - 3, yy - 2, x + 3, yy + 2], fill=(52, 42, 32))
            d.line([(x + 3, yy), (x + 3, yy - 13)], fill=(52, 42, 32), width=1)
            x += rng.randint(9, 20)
        d.line([(16, top - 2), (16, top + 22)], fill=(72, 60, 46), width=2)
    d.rectangle([0, 0, W - 1, H - 1], outline=(196, 184, 156), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    return _save(im, name)


def tex_etching():
    """The landscape etching -- the signature carrier, in-scene provenance."""
    if "etching.png" in _TEX:
        return _TEX["etching.png"]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(9)
    W, H = 340, 260
    im = Image.new("RGB", (W, H), (226, 218, 198))
    d = ImageDraw.Draw(im)
    d.rectangle([26, 22, W - 26, H - 52], outline=(60, 50, 40), width=3)
    for y in range(32, 88, 4):                           # sky hatching
        d.line([(30, y), (W - 30, y + rng.randint(-2, 2))],
               fill=(190, 178, 154), width=1)
    d.line([(30, 132), (W - 30, 126)], fill=(96, 84, 66), width=2)
    for hx, hh in [(100, 44), (200, 30), (272, 36)]:     # hatched hills
        for t in range(0, hh, 3):
            d.line([(hx - hh + t, 132 - t), (hx + hh - t, 132 - t)],
                   fill=(130, 116, 92), width=1)
    d.line([(66, 132), (66, 96)], fill=(74, 62, 48), width=3)
    d.ellipse([48, 74, 86, 102], outline=(74, 62, 48), width=2)
    d.ellipse([54, 80, 80, 98], outline=(94, 82, 64), width=1)
    for fx_, fy_ in [(150, 140), (166, 143)]:            # two staffage figures
        d.line([(fx_, fy_), (fx_, fy_ + 10)], fill=(60, 50, 40), width=2)
        d.ellipse([fx_ - 2, fy_ - 4, fx_ + 2, fy_], fill=(60, 50, 40))
    for y in range(140, H - 58, 4):                      # foreground hatch
        d.line([(30, y), (W - 30, y + rng.randint(-1, 1))],
               fill=(158, 144, 118), width=1)
    f = _font(22, italic=True)
    d.text((44, H - 46), "C.N. Gijsbrechts. F. A° 1668",
           fill=(70, 58, 46), font=f)
    im = im.filter(ImageFilter.GaussianBlur(0.4))
    return _save(im, "etching.png")


def tex_courant():
    """Oprechte Haerlemse Courant: masthead + two letterpress columns."""
    if "courant.png" in _TEX:
        return _TEX["courant.png"]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(41)
    W, H = 300, 220
    im = Image.new("RGB", (W, H), (228, 218, 192))
    d = ImageDraw.Draw(im)
    f = _font(19)
    d.text((22, 8), "Oprechte Haerlemse", fill=(40, 34, 28), font=f)
    d.text((78, 30), "COURANT", fill=(40, 34, 28), font=_font(21))
    d.line([(14, 58), (W - 14, 58)], fill=(60, 50, 42), width=2)
    d.text((22, 64), "SPANGIEN.", fill=(46, 38, 30), font=_font(13))
    for col in (0, 1):
        x0 = 16 + col * (W // 2)
        y = 86 if col == 0 else 66
        while y < H - 14:
            x = x0
            while x < x0 + W // 2 - 26:
                wseg = rng.randint(5, 16)
                d.rectangle([x, y, x + wseg, y + 4], fill=(74, 62, 50))
                x += wseg + rng.randint(3, 6)
            y += 9
    d.line([(W // 2, 62), (W // 2, H - 12)], fill=(150, 138, 114), width=1)
    d.rectangle([0, 0, W - 1, H - 1], outline=(196, 184, 156), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    return _save(im, "courant.png")


def tex_gazette():
    if "gazette.png" in _TEX:
        return _TEX["gazette.png"]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(52)
    W, H = 240, 190
    im = Image.new("RGB", (W, H), (224, 213, 186))
    d = ImageDraw.Draw(im)
    d.text((30, 8), "The Lond. Gazette", fill=(44, 36, 30), font=_font(20))
    d.line([(14, 40), (W - 14, 40)], fill=(60, 50, 42), width=2)
    y = 50
    while y < H - 14:
        x = 18
        while x < W - 26:
            wseg = rng.randint(5, 17)
            d.rectangle([x, y, x + wseg, y + 4], fill=(76, 64, 52))
            x += wseg + rng.randint(3, 6)
        y += 9
    d.rectangle([0, 0, W - 1, H - 1], outline=(192, 180, 152), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    return _save(im, "gazette.png")


def tex_almanach():
    """Red + black letterpress title page with a red seal print."""
    if "almanach.png" in _TEX:
        return _TEX["almanach.png"]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(63)
    W, H = 200, 240
    im = Image.new("RGB", (W, H), (226, 215, 188))
    d = ImageDraw.Draw(im)
    d.text((28, 12), "ALMANACH", fill=(150, 32, 22), font=_font(24))
    d.text((54, 44), "voor 't Jaer", fill=(50, 42, 34), font=_font(14))
    d.text((44, 64), "M. DC. LXVIII.", fill=(150, 32, 22), font=_font(17))
    d.line([(20, 94), (W - 20, 94)], fill=(70, 58, 46), width=2)
    y = 104
    for ln in range(7):
        x = 26 + (ln % 3) * 6
        red = ln % 3 == 1
        while x < W - 30:
            wseg = rng.randint(6, 18)
            d.rectangle([x, y, x + wseg, y + 4],
                        fill=(158, 40, 28) if red else (70, 58, 46))
            x += wseg + rng.randint(3, 6)
        y += 12
    d.ellipse([70, 190, 130, 232], outline=(170, 44, 32), width=3)
    d.ellipse([84, 200, 116, 222], outline=(170, 44, 32), width=2)
    d.rectangle([0, 0, W - 1, H - 1], outline=(194, 182, 154), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    return _save(im, "almanach.png")


def tex_calendar():
    """Rolled German calendar: woodcut frieze + blackletter title, black+red."""
    if "calendar.png" in _TEX:
        return _TEX["calendar.png"]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(74)
    W, H = 240, 300
    im = Image.new("RGB", (W, H), (223, 212, 184))
    d = ImageDraw.Draw(im)
    d.rectangle([12, 10, W - 12, 62], outline=(60, 50, 40), width=2)  # frieze
    for i in range(9):                                   # tiny woodcut figures
        x = 22 + i * 24
        d.line([(x, 54), (x, 34)], fill=(58, 48, 38), width=3)
        d.ellipse([x - 4, 24, x + 4, 34], fill=(58, 48, 38))
        d.line([(x - 6, 44), (x + 6, 40)], fill=(58, 48, 38), width=2)
    d.text((26, 70), "Alter und Neuer", fill=(46, 38, 30), font=_font(20))
    d.text((30, 96), "Zeit- und Schreib-", fill=(46, 38, 30), font=_font(18))
    d.text((48, 122), "Calender", fill=(160, 38, 26), font=_font(24))
    d.text((44, 158), "auff das Jahr", fill=(46, 38, 30), font=_font(15))
    d.text((36, 182), "M. DC. LXVIII.", fill=(160, 38, 26), font=_font(19))
    y = 218
    for ln in range(5):
        x = 26
        red = ln % 2 == 1
        while x < W - 30:
            wseg = rng.randint(6, 18)
            d.rectangle([x, y, x + wseg, y + 4],
                        fill=(160, 44, 30) if red else (66, 56, 44))
            x += wseg + rng.randint(3, 6)
        y += 13
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    return _save(im, "calendar.png")


def tex_comb(dark=True):
    """Comb with alpha-cut teeth. dark=horn, else boxwood."""
    name = f"comb_{int(dark)}.png"
    if name in _TEX:
        return _TEX[name]
    from PIL import Image, ImageDraw
    W, H = 200, 120
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if dark:
        body, stripe = (58, 42, 30, 255), (84, 62, 40, 255)
    else:
        body, stripe = (196, 156, 92, 255), (214, 178, 116, 255)
    d.rounded_rectangle([4, 8, W - 4, 52], radius=10, fill=body)
    for x in range(10, W - 10, 14):                      # horn striping
        d.line([(x, 10), (x + 6, 50)], fill=stripe, width=3)
    for x in range(8, W - 8, 8):                         # teeth (alpha gaps)
        d.rectangle([x, 50, x + 4, H - 6], fill=body)
    return _save(im, name)


def tex_curtain():
    """Dark green silk with vertical streaks; gold selvage at u=0 (leading
    edge) and hem gold at low v. u maps across the drape from the edge."""
    if "curtain.png" in _TEX:
        return _TEX["curtain.png"]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(85)
    W, H = 512, 512
    im = Image.new("RGB", (W, H), (26, 36, 30))
    d = ImageDraw.Draw(im)
    for x in range(W):                                   # vertical silk streaks
        v = int(7 * math.sin(x * 0.11) + 5 * math.sin(x * 0.031 + 1.2)
                + rng.uniform(-4, 4))
        d.line([(x, 0), (x, H)], fill=(26 + v, 36 + v, 30 + v))
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 6, H], fill=(140, 106, 46))       # selvage, u<0.012
    d.rectangle([6, 0, 8, H], fill=(84, 66, 32))
    d.rectangle([0, H - 7, W, H], fill=(132, 100, 44))   # hem (v near 0 is top
    d.rectangle([0, H - 9, W, H - 7], fill=(84, 66, 32))  # of image = bottom)
    return _save(im, "curtain.png")


def tex_velvet():
    if "velvet.png" in _TEX:
        return _TEX["velvet.png"]
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(96)
    W = 128
    im = Image.new("RGB", (W, W), (92, 22, 34))
    d = ImageDraw.Draw(im)
    for _ in range(900):
        x, y = rng.uniform(0, W), rng.uniform(0, W)
        v = rng.randint(-16, 12)
        d.point((x, y), fill=(92 + v, 22 + max(-10, v // 3), 34 + v // 2))
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    return _save(im, "velvet.png")


def tex_cube_faces():
    """Six tiny faces for the IBL cubemap: warm key glow upper-left, deep warm
    dark elsewhere -- a candle-lit chamber, not a studio."""
    if "cube_left.png" in _TEX:
        return {k: _TEX[f"cube_{k}.png"]
                for k in ("left", "right", "top", "bottom", "front", "back")}
    from PIL import Image
    import numpy as np

    def grad(c0, c1, diag=False):
        W = 48
        a = np.zeros((W, W, 3))
        t = (np.mgrid[0:W, 0:W][0] / (W - 1))[..., None]
        if diag:
            t = ((np.mgrid[0:W, 0:W][0] + np.mgrid[0:W, 0:W][1])
                 / (2 * (W - 1)))[..., None]
        a = np.array(c0) * (1 - t) + np.array(c1) * t
        return Image.fromarray(a.astype("uint8"))

    faces = {
        "left":   grad((235, 190, 130), (60, 40, 24)),     # the key side
        "top":    grad((210, 168, 112), (48, 34, 20)),
        "right":  grad((26, 18, 12), (12, 9, 7)),
        "bottom": grad((44, 30, 18), (16, 11, 8)),
        "front":  grad((150, 110, 70), (22, 15, 10), diag=True),
        "back":   grad((150, 110, 70), (22, 15, 10), diag=True),
    }
    return {k: _save(im, f"cube_{k}.png") for k, im in faces.items()}


# ------------------------------------------------------------------ materials
_counters = {"tx": 0, "mat": 0}
_sheen_reg = {}


def IT(uri, slot="base", aniso=False):
    _counters["tx"] += 1
    tag = {"base": "TXB", "norm": "TXN"}[slot]
    kw = dict(url=[uri], DEF=f"{tag}_{_counters['tx']}")
    if aniso:
        kw["textureProperties"] = x3d.TextureProperties(
            anisotropicDegree=8, generateMipMaps=True)
    return x3d.ImageTexture(**kw)


def M(base=(1, 1, 1), rough=0.85, metal=0.0, transp=0.0, tex=None, ntex=None,
      nscale=1.0, emis=(0, 0, 0), sheen=None, aniso=False):
    _counters["mat"] += 1
    kw = dict(baseColor=base, roughness=rough, metallic=metal,
              transparency=transp, emissiveColor=emis)
    if tex is not None:
        kw["baseTexture"] = IT(tex, "base", aniso=aniso)
    if ntex is not None:
        kw["normalTexture"] = IT(ntex, "norm")
        kw["normalScale"] = nscale
    if sheen is not None:
        d = f"MSHEEN_{_counters['mat']}"
        kw["DEF"] = d
        _sheen_reg[d] = sheen                # (sheenColor rgb, sheenRoughness)
    return x3d.Appearance(material=x3d.PhysicalMaterial(**kw))


def box(size, app):
    return x3d.Shape(geometry=x3d.Box(size=size), appearance=app)


def T(t=(0, 0, 0), r=None, s=None, ch=()):
    kw = dict(translation=t, children=list(ch))
    if r is not None:
        kw["rotation"] = r
    if s is not None:
        kw["scale"] = s
    return x3d.Transform(**kw)


_shz = {"n": 0}


def soft_shadow(w, h, standoff, blob=False, band=False, strength=1.0):
    """A baked umber shadow on the board plane for an object of footprint
    (w,h) standing `standoff` metres off it. Grows + travels with standoff."""
    _shz["n"] += 1
    z = 0.0008 + 0.00012 * (_shz["n"] % 9)
    grow = 1.0 + 1.5 * standoff / max(w, h, 1e-3)
    tex = tex_shadow_blob() if blob else tex_shadow_rect()
    tr = min(0.55, 0.05 + 0.5 * (1 - strength))
    return T((SH_DX * standoff, SH_DY * standoff, z), ch=[x3d.Shape(
        geometry=x3d.Rectangle2D(size=(w * grow + 0.5 * standoff,
                                       h * grow + 0.5 * standoff)),
        appearance=M((1, 1, 1), rough=1.0, transp=tr, tex=tex))])


# ------------------------------------------------------------------ props
def letter(w, h, seed, tint=(0.90, 0.86, 0.76), bend=6.0, seal=None,
           standoff=0.006, dense=False, script=True):
    """A folded letter packet: soft shadow + two bowed half-panels + wax seal.
    Outer edges curl toward the viewer; NO letter is a flat rectangle."""
    thick = 0.0035
    tx = tex_letter(seed, script=script, dense=dense)
    ch = [soft_shadow(w, h, standoff)]
    for side in (-1, 1):
        ch.append(T((side * w / 4, 0, standoff),
                    r=(0, 1, 0, -side * bend * DEG), ch=[
            box((w / 2 + 0.002, h, thick), M(tint, rough=0.9, tex=tx))]))
    if seal is not None:
        sx, sy = seal
        ch.append(T((sx * w, sy * h, standoff + thick + 0.002), ch=[x3d.Shape(
            geometry=x3d.Sphere(radius=0.0115),
            appearance=M((0.52, 0.06, 0.045), rough=0.25))],
            s=(1, 1, 0.35)))
    return ch


def dome_nail(r=0.005, iron=True):
    app = M((0.30, 0.30, 0.33), rough=0.35, metal=1.0) if iron else \
        M((0.85, 0.66, 0.28), rough=0.35, metal=1.0)
    return T(s=(1, 1, 0.55), ch=[x3d.Shape(
        geometry=x3d.Sphere(radius=r), appearance=app)])


def tape_segment(p0, p1, z, width=0.017, raised=None):
    """One straight run of red linen tape between two canvas-fraction points."""
    x0, y0 = P(*p0)
    x1, y1 = P(*p1)
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    zc = raised if raised is not None else z
    return T(((x0 + x1) / 2, (y0 + y1) / 2, zc), r=(0, 0, 1, ang), ch=[
        box((length, width, 0.003),
            M((0.50, 0.105, 0.05), rough=0.88, tex=None))])


def curtain_mesh():
    """The curtain as an IndexedFaceSet grid. Leading edge follows the
    painting's dominant diagonal; folds hang in PHYSICAL space anchored to the
    gathered right side (a1 lesson: folds parameterized on row-fraction
    compress into wiggles at the bottom); a belly swells along the leading
    edge toward the hem. Bellies <= 10 cm. Texture u: selvage at u=0."""
    rows, cols = 18, 40
    # folds by physical distance (m) from the RIGHT edge of the drape
    folds = [(0.030, 1.00), (0.085, 0.68), (0.150, 1.05), (0.225, 0.62),
             (0.320, 0.95), (0.430, 0.70), (0.560, 1.00), (0.700, 0.62),
             (0.850, 0.78)]
    pts, tcs = [], []
    fys = [0.078 + (0.965 - 0.078) * i / (rows - 1) for i in range(rows)]
    x1 = 0.995
    for fy in fys:
        x0 = curtain_edge_x(fy)
        pinch = min(1.0, (fy - 0.078) / 0.20)
        amp = 0.040 * (0.12 + 0.88 * pinch)
        belly = 0.048 * pinch * min(1.0, (fy - 0.10) / 0.55)
        row_w = (x1 - x0) * CW
        for c in range(cols):
            u = c / (cols - 1)
            fx = x0 + (x1 - x0) * u
            dR = (x1 - fx) * CW                          # metres from right
            dL = (fx - x0) * CW                          # metres from edge
            z = 0.014 + 0.003 * math.sin(dR * 70)
            for p, a in folds:
                if p < row_w * 1.1:
                    z += a * amp * math.exp(-((dR - p) ** 2)
                                            / (2 * 0.030 ** 2))
            z += belly * math.exp(-((dL / 0.075) ** 2))  # leading-edge belly
            z = min(z, 0.096)
            wx, wy = P(fx, fy)
            pts.append((round(wx, 4), round(wy, 4), round(z, 4)))
            tcs.append((round(u, 3), round(1 - fy, 3)))
    idx = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            a = r * cols + c
            b = a + 1
            cc = a + cols + 1
            dd = a + cols
            idx += [a, dd, cc, b, -1]                    # front faces +z
    geo = x3d.IndexedFaceSet(
        coord=x3d.Coordinate(point=pts),
        texCoord=x3d.TextureCoordinate(point=tcs),
        coordIndex=idx, creaseAngle=3.1, solid=False)
    app = M((1, 1, 1), rough=0.48, tex=tex_curtain(), aniso=True,
            sheen=((0.30, 0.38, 0.33), 0.45))
    return x3d.Shape(geometry=geo, appearance=app)


# ------------------------------------------------------------------ the scene
def build_scene(viewpoint=None):
    # reset per-build registries (build_scene runs once per view)
    _counters["tx"] = _counters["mat"] = 0
    _sheen_reg.clear()
    _shz["n"] = 0

    cube = tex_cube_faces()
    root = []

    # ---------------- provenance (the point of the whole exercise)
    root.append(x3d.MetadataSet(name="provenance", value=[
        x3d.MetadataString(name="provenance", value=["interpretive"]),
        x3d.MetadataString(name="sourceCitation", value=[
            "Cornelius Norbertus Gijsbrechts (Flemish, c. 1625 - after 1675), "
            "'Trompe l'oeil. Board Partition with Letter Rack and Music Book' "
            "(Danish: 'Trompe l'oeil. Brevvaeg med kamfoder og nodehaefte.'), "
            "1668, signed 'C. N. Gysbrechts. F. Ao 1668'. SMK - Statens Museum "
            "for Kunst (National Gallery of Denmark), Copenhagen, KMS3059. "
            "https://open.smk.dk/en/artwork/image/KMS3059"]),
        x3d.MetadataString(name="catalogId", value=["KMS3059"]),
        x3d.MetadataString(name="publicDomain", value=["true"]),
        x3d.MetadataString(name="rights", value=[
            "SMK API record KMS3059: 'public_domain': true, rights "
            "https://creativecommons.org/publicdomain/mark/1.0/ (CC Public "
            "Domain Mark 1.0)"]),
        x3d.MetadataString(name="generationMethod", value=[
            "Procedurally authored in Python with x3d.py 4.0.65.3 by an AI "
            "system (Claude, Anthropic); textures synthesized with PIL; an "
            "interpretive 3D re-staging of the painting's composition and "
            "light, not a scan or record of the artwork; object placement "
            "measured off the SMK IIIF master as canvas fractions; verified "
            "by headless X_ITE renders with quantitative look-dev checks."]),
    ]))

    root.append(x3d.WorldInfo(
        title="Trompe l'oeil Letter Rack (after Gijsbrechts, 1668, SMK KMS3059)",
        info=["interpretive scene; see MetadataSet 'provenance'"]))

    root.append(x3d.NavigationInfo(headlight=False, type=["EXAMINE", "ANY"]))
    root.append(x3d.Background(skyColor=[BG]))

    # ---------------- light: ONE warm raking key + authored IBL cubemap
    root.append(x3d.DirectionalLight(
        direction=KEY_DIR, color=(1.0, 0.87, 0.70), intensity=1.60,
        global_=True))
    root.append(x3d.EnvironmentLight(
        color=(1.0, 0.90, 0.76), intensity=0.20, global_=True,
        specularTexture=x3d.ComposedCubeMapTexture(
            frontTexture=x3d.ImageTexture(url=[cube["front"]], DEF="CMF_front"),
            backTexture=x3d.ImageTexture(url=[cube["back"]], DEF="CMF_back"),
            leftTexture=x3d.ImageTexture(url=[cube["left"]], DEF="CMF_left"),
            rightTexture=x3d.ImageTexture(url=[cube["right"]], DEF="CMF_right"),
            topTexture=x3d.ImageTexture(url=[cube["top"]], DEF="CMF_top"),
            bottomTexture=x3d.ImageTexture(url=[cube["bottom"]],
                                           DEF="CMF_bottom"))))

    # ---------------- the wall: near-black cloth-faced surround, gilt tacks
    root.append(T((0, 0, -0.030), ch=[
        box((3.4, 3.2, 0.012), M((0.028, 0.022, 0.015), rough=1.0))]))
    gilt = []
    for fy in (0.030, 0.960):
        fx = 0.075
        while fx < 0.94:
            wx, wy = P(fx, fy)
            gilt.append(T((wx, wy, -0.021), ch=[dome_nail(0.0042, iron=False)]))
            fx += 0.043
    root.extend(gilt)

    # ---------------- board: 5 deal planks, complete inside the surround
    bx0, by0 = P(BD_L, BD_T)
    bx1, by1 = P(BD_R, BD_B)
    bw, bh = bx1 - bx0, by0 - by1
    root.append(T(((bx0 + bx1) / 2, (by0 + by1) / 2, -0.009), ch=[
        box((bw, bh, 0.018), M((1, 1, 1), rough=0.80, tex=tex_plank_wall(),
                               ntex=tex_plank_normal(), nscale=0.6,
                               aniso=True))]))
    # bottom rail (slightly darker batten along the board's bottom edge)
    rx, ry = P(0.5125, 0.912)
    root.append(T((rx, ry, 0.0015), ch=[
        box((bw, 0.030, 0.003), M((0.42, 0.34, 0.24), rough=0.9))]))

    # ---------------- papers leaning over the board's TOP edge (frame-break 1)
    for fx, fy, w, h, ang, tilt, seed in [
            (0.395, 0.052, 0.100, 0.085, -6, 8, 3),
            (0.468, 0.048, 0.110, 0.100, 4, 13, 14),
            (0.560, 0.055, 0.088, 0.078, -9, 7, 25),
            (0.634, 0.050, 0.112, 0.092, 6, 11, 36),
            (0.716, 0.056, 0.092, 0.080, -4, 9, 47)]:
        wx, wy = P(fx, fy)
        root.append(T((wx, wy, -0.017), r=(1, 0, 0, tilt * DEG), ch=[
            T(r=(0, 0, 1, ang * DEG), ch=[
                box((w, h, 0.003), M((0.85, 0.81, 0.71), rough=0.9,
                                     tex=tex_letter(seed, script=False)))])]))

    # ---------------- red linen tape grid + iron dome nails
    tapes = []
    vxs = [0.125, 0.365, 0.600]
    hys = [0.115, 0.505, 0.720]
    for fx in vxs:
        tapes.append(tape_segment((fx, BD_T), (fx, BD_B), 0.010))
    for fy in hys:
        edges = [BD_L] + vxs + [BD_R]
        for i in range(len(edges) - 1):
            raised = None
            if fy == 0.720 and edges[i] == 0.365:        # bows over the print
                raised = 0.0165
            tapes.append(tape_segment((edges[i], fy + (0.002 if i % 2 else 0)),
                                      (edges[i + 1], fy), 0.0125,
                                      raised=raised))
    # corner diagonal, bottom-left
    tapes.append(tape_segment((0.058, 0.838), (0.168, 0.925), 0.0125))
    root.extend(tapes)
    for fx in vxs:
        for fy in hys:
            wx, wy = P(fx, fy)
            root.append(T((wx, wy, 0.0165), ch=[dome_nail()]))
    for fx, fy in [(0.10, 0.885), (0.125, BD_T + 0.006), (0.365, BD_T + 0.006),
                   (0.60, BD_T + 0.006), (0.125, BD_B - 0.006),
                   (0.365, BD_B - 0.006)]:
        wx, wy = P(fx, fy)
        root.append(T((wx, wy, 0.013), ch=[dome_nail()]))

    # ---------------- letters tucked under the tapes (the connective tissue)
    # (fx, fy, rot_deg, w, h, seed, seal, dense)
    # every letter ANCHORED to a tape line (a2 lesson: unanchored letters read
    # as confetti): tops tucked under the horizontals at 0.115/0.505/0.72 or
    # crossing the verticals at 0.365/0.60; rotations 5-30 deg per the source.
    LETTERS = [
        (0.270, 0.158, -12, 0.115, 0.085, 7, (0.24, -0.18), False),
        (0.328, 0.170, 16, 0.105, 0.078, 12, None, False),
        (0.398, 0.158, -7, 0.110, 0.082, 31, None, False),
        (0.375, 0.300, -21, 0.112, 0.084, 44, None, False),  # under vert 0.365
        (0.350, 0.345, 9, 0.125, 0.090, 55, (0.20, 0.10), False),
        (0.365, 0.445, 83, 0.108, 0.076, 66, None, False),   # sideways, tucked
        (0.520, 0.380, 12, 0.118, 0.086, 77, None, False),   # half under curtain
        (0.305, 0.535, 13, 0.120, 0.088, 88, (-0.22, -0.12), False),
        (0.280, 0.565, -24, 0.108, 0.080, 99, None, False),
        (0.425, 0.548, -16, 0.110, 0.082, 110, None, False),
        (0.598, 0.556, 7, 0.115, 0.084, 121, None, False),   # half under curtain
        (0.335, 0.605, 25, 0.100, 0.075, 132, None, True),
        (0.550, 0.752, -12, 0.110, 0.080, 143, None, False),  # under tape 0.72
    ]
    for fx, fy, ang, w, h, seed, seal, dense in LETTERS:
        wx, wy = P(fx, fy)
        root.append(T((wx, wy, 0.0), r=(0, 0, 1, ang * DEG), ch=letter(
            w, h, seed, bend=random.Random(seed).uniform(4, 9), seal=seal,
            dense=dense)))

    # ---------------- comb case (kamfoder): crimson velvet wall pocket
    case = []
    CASE_CX, CASE_W = 0.13, 0.185
    case_top, case_bot = 0.10, 0.555
    ccx, ccy = P(CASE_CX, (case_top + case_bot) / 2)
    case_h = (case_bot - case_top) * CHT
    velvet = M((1, 1, 1), rough=0.95, tex=tex_velvet(),
               sheen=((0.62, 0.15, 0.19), 0.40))
    galloon = M((0.40, 0.38, 0.33), rough=0.6, metal=0.3)
    case.append(soft_shadow(CASE_W * CW, case_h, 0.020, strength=0.9))
    case.append(T((0, 0, 0.016), ch=[
        box((CASE_W * CW, case_h, 0.010), velvet)]))
    # gable top: one flat velvet triangle (a2 lesson: two crossed boards read
    # as a notched M), galloon button at the peak
    case.append(T((0, case_h / 2 + 0.018, 0.016), s=(1.45, 1.0, 0.16), ch=[
        x3d.Shape(geometry=x3d.Cone(bottomRadius=0.070, height=0.046),
                  appearance=velvet)]))
    case.append(T((0, case_h / 2 + 0.040, 0.019), ch=[x3d.Shape(
        geometry=x3d.Sphere(radius=0.006), appearance=galloon)]))
    # 5 pocket tiers, each front sagging open at the top
    n_tiers = 5
    tier_h = case_h / n_tiers
    for i in range(n_tiers):
        yc = case_h / 2 - tier_h * (i + 0.5)
        case.append(T((0, yc - 0.004, 0.028), r=(1, 0, 0, 8 * DEG), ch=[
            box((CASE_W * CW, tier_h * 0.80, 0.006), velvet)]))
        case.append(T((0, yc + tier_h * 0.36, 0.033), r=(1, 0, 0, 8 * DEG),
                      ch=[box((CASE_W * CW, 0.013, 0.004), galloon)]))
    for sx in (-CASE_W * CW / 2 + 0.008, 0, CASE_W * CW / 2 - 0.008):
        case.append(T((sx, 0, 0.024), ch=[
            box((0.013, case_h, 0.004), galloon)]))
    # contents -- top to bottom, poking above the pocket lips
    case.append(T((0.010, case_h / 2 - 0.030, 0.024), r=(0, 0, 1, 24 * DEG),
                  ch=[box((0.100, 0.052, 0.004),
                          M((1, 1, 1), rough=0.6, tex=tex_comb(True)))]))
    case.append(T((-0.045, case_h / 2 - tier_h - 0.020, 0.022),
                  r=(0, 0, 1, 6 * DEG), ch=[
        box((0.055, 0.048, 0.016), M((0.78, 0.75, 0.68), rough=0.85))]))
    case.append(T((0.030, case_h / 2 - 2 * tier_h - 0.018, 0.022),
                  r=(0, 0, 1, -10 * DEG), ch=[
        box((0.085, 0.040, 0.004), M((0.89, 0.85, 0.75), rough=0.9,
                                     tex=tex_letter(150, script=False)))]))
    case.append(T((-0.030, case_h / 2 - 3 * tier_h - 0.014, 0.024),
                  r=(0, 0, 1, -14 * DEG), ch=[
        box((0.095, 0.050, 0.004),
            M((1, 1, 1), rough=0.55, tex=tex_comb(False)))]))
    # almanac page folded over the 4th pocket lip
    alm_y = case_h / 2 - 3 * tier_h + tier_h * 0.36
    case.append(T((0.040, alm_y + 0.012, 0.034), r=(1, 0, 0, 16 * DEG), ch=[
        box((0.062, 0.040, 0.0025), M((0.92, 0.89, 0.80), rough=0.9,
                                      tex=tex_almanach()))]))
    case.append(T((0.040, alm_y - 0.020, 0.037), r=(1, 0, 0, -24 * DEG), ch=[
        box((0.062, 0.036, 0.0025), M((0.88, 0.85, 0.76), rough=0.9))]))
    # second dark comb, lowest tier
    case.append(T((0.020, -case_h / 2 + 0.024, 0.022), r=(0, 0, 1, 8 * DEG),
                  ch=[box((0.090, 0.046, 0.004),
                          M((1, 1, 1), rough=0.6, tex=tex_comb(True)))]))
    root.append(T((ccx, ccy, 0), ch=case))

    # goose quill thrust into tier 2, pointing up-right, long raking shadow
    qwx, qwy = P(0.190, 0.250)
    quill = [
        soft_shadow(0.18, 0.04, 0.028, blob=True, strength=0.8),
        T((0, 0, 0.028), r=(0, 0, 1, -58 * DEG), ch=[
            x3d.Shape(geometry=x3d.Cylinder(radius=0.0015, height=0.155),
                      appearance=M((0.90, 0.87, 0.81), rough=0.6)),
            T((0.008, 0.052, 0), r=(0, 0, 1, -5 * DEG),
              s=(0.20, 1.0, 0.08), ch=[x3d.Shape(
                  geometry=x3d.Sphere(radius=0.050),
                  appearance=M((0.93, 0.92, 0.88), rough=0.85))]),
            T((0.014, 0.070, 0.002), r=(0, 0, 1, -11 * DEG),
              s=(0.13, 0.68, 0.06), ch=[x3d.Shape(
                  geometry=x3d.Sphere(radius=0.050),
                  appearance=M((0.95, 0.94, 0.91), rough=0.85))]),
        ])]
    root.append(T((qwx, qwy, 0), r=(0, 0, 1, 10 * DEG), ch=quill))

    # rolled German calendar hanging at (0.19, 0.45)
    cwx, cwy = P(0.19, 0.45)
    root.append(T((cwx, cwy, 0), ch=[
        soft_shadow(0.06, 0.17, 0.030, strength=0.85),
        T((0, 0.085, 0.036), ch=[box((0.004, 0.03, 0.002),
                                     M((0.30, 0.06, 0.05), rough=0.85))]),
        T((0, 0, 0.038), r=(0, 0, 1, 3 * DEG), ch=[x3d.Shape(
            geometry=x3d.Cylinder(radius=0.0205, height=0.165),
            appearance=M((1, 1, 1), rough=0.85, tex=tex_calendar()))]),
    ]))

    # great seal pendant at (0.175, 0.53): parchment boat + big red wax seal
    swx, swy = P(0.176, 0.578)
    root.append(T((swx, swy, 0), ch=[
        soft_shadow(0.08, 0.10, 0.034, blob=True, strength=0.9),
        T((0, 0.048, 0.032), r=(0, 0, 1, -4 * DEG), ch=[
            box((0.020, 0.085, 0.0022), M((0.85, 0.80, 0.68), rough=0.9))]),
        T((0, -0.012, 0.034), r=(1, 0, 0, 90 * DEG), ch=[
            x3d.Shape(geometry=x3d.Cylinder(radius=0.0335, height=0.007),
                      appearance=M((0.52, 0.065, 0.05), rough=0.22))]),
        T((0, -0.012, 0.0385), r=(1, 0, 0, 90 * DEG), ch=[
            x3d.Shape(geometry=x3d.Cylinder(radius=0.022, height=0.0018),
                      appearance=M((0.60, 0.10, 0.07), rough=0.30))]),
    ]))

    # plumb cord + silk tassel down the left side, dead vertical
    twx, twy = P(0.098, 0.60)
    cord_top_y = P(0.098, 0.075)[1]
    root.append(T((twx, (twy + cord_top_y) / 2, 0.046), ch=[
        box((0.003, cord_top_y - twy, 0.003),
            M((0.07, 0.11, 0.12), rough=0.7))]))
    root.append(T((twx, twy, 0), ch=[
        soft_shadow(0.035, 0.07, 0.040, blob=True, strength=0.85),
        T((0, 0.012, 0.046), ch=[x3d.Shape(
            geometry=x3d.Sphere(radius=0.009),
            appearance=M((0.08, 0.13, 0.14), rough=0.6))]),
        T((0, -0.016, 0.046), ch=[x3d.Shape(
            geometry=x3d.Cone(bottomRadius=0.011, height=0.045),
            appearance=M((0.07, 0.11, 0.12), rough=0.75))]),
    ]))

    # ---------------- music book, lower left: the title prop
    mwx, mwy = P(0.150, 0.640)
    bookg = [soft_shadow(0.24, 0.19, 0.014, strength=0.95)]
    bookg.append(T((0.006, -0.004, 0.007), r=(0, 0, 1, -8 * DEG), ch=[
        box((0.245, 0.180, 0.006), M((0.32, 0.24, 0.17), rough=0.85))]))
    bookg.append(T((-0.003, 0.002, 0.012), r=(0, 0, 1, -4 * DEG), ch=[
        box((0.230, 0.170, 0.007), M((0.52, 0.56, 0.60), rough=0.85))]))
    for side, seed in ((-1, 201), (1, 202)):
        bookg.append(T((side * 0.054, 0, 0.023),
                       r=(0, 1, 0, -side * 8 * DEG), ch=[
            box((0.107, 0.160, 0.004), M((1, 1, 1), rough=0.9,
                                         tex=tex_music_page(seed)))]))
    # the 360-degree page curl at the upper-left corner
    bookg.append(T((-0.096, 0.062, 0.034), r=(0, 0, 1, 14 * DEG), ch=[
        x3d.Shape(geometry=x3d.Cylinder(radius=0.019, height=0.085),
                  appearance=M((0.91, 0.88, 0.79), rough=0.88,
                               tex=tex_letter(203, script=False)))]))
    root.append(T((mwx, mwy, 0), r=(0, 0, 1, -5 * DEG), ch=bookg))

    # ---------------- letter rosette on its iron file (deepest paper stack)
    rox, roy = P(0.350, 0.815)
    rng = random.Random(1234)
    rosette = [soft_shadow(0.22, 0.20, 0.028, blob=True, strength=1.0)]
    for i in range(13):
        ang = i * (360 / 13) + rng.uniform(-6, 6)
        rad = 0.036 + (i % 3) * 0.008
        if 230 < ang % 360 < 300:                        # hang past the rail
            rad += 0.020
        lx = rad * math.cos(ang * DEG)
        ly = rad * math.sin(ang * DEG)
        w = rng.uniform(0.085, 0.115)
        h = rng.uniform(0.062, 0.085)
        z = 0.006 + i * 0.0030
        dense = i % 5 == 0
        rosette.append(T((lx, ly, z), r=(0, 0, 1, (ang + 90
                                                   + rng.uniform(-6, 6))
                                         * DEG), ch=[
            T(r=(0, 1, 0, rng.uniform(-5, 5) * DEG), ch=[
                box((w, h, 0.0035),
                    M((0.90 - 0.05 * rng.random(), 0.86 - 0.05 * rng.random(),
                       0.76 - 0.05 * rng.random()), rough=0.9,
                      tex=tex_letter(300 + i, script=not dense,
                                     dense=dense)))])]))
    rosette.append(T((0, 0, 0.052), ch=[x3d.Shape(                # spike tip
        geometry=x3d.Cone(bottomRadius=0.0035, height=0.022),
        appearance=M((0.25, 0.25, 0.27), rough=0.35, metal=1.0))]))
    root.append(T((rox, roy, 0), ch=rosette))

    # ---------------- landscape etching on its pamphlet stack (signature)
    ewx, ewy = P(0.475, 0.775)
    root.append(T((ewx, ewy, 0), ch=[
        soft_shadow(0.18, 0.14, 0.012, strength=0.95),
        T((0.004, -0.004, 0.006), ch=[
            box((0.155, 0.118, 0.009), M((0.80, 0.74, 0.62), rough=0.9))]),
        T((0, 0, 0.0125), r=(0, 0, 1, 4 * DEG), ch=[
            box((0.170, 0.130, 0.0025), M((1, 1, 1), rough=0.9,
                                          tex=tex_etching()))]),
    ]))

    # Haarlem courant above it, top edge curling forward
    hwx, hwy = P(0.475, 0.660)
    root.append(T((hwx, hwy, 0), r=(0, 0, 1, -6 * DEG), ch=[
        soft_shadow(0.15, 0.11, 0.008),
        T((0, -0.012, 0.008), ch=[
            box((0.145, 0.082, 0.003), M((1, 1, 1), rough=0.9,
                                         tex=tex_courant()))]),
        T((0, 0.036, 0.012), r=(1, 0, 0, 38 * DEG), ch=[
            box((0.145, 0.030, 0.002), M((0.87, 0.83, 0.73), rough=0.9))]),
        T((0, 0.030, 0.014), ch=[dome_nail(0.004)]),
    ]))

    # ---------------- hanging writing kit off the nail at (0.60, 0.72)
    kwx, kwy = P(0.600, 0.720)
    kit = [T((0, 0, 0.018), ch=[dome_nail(0.0055)])]
    # red cords from the nail to each piece
    for tx_, ty_, ln_ in [(-0.026, -0.045, 0.10), (0.012, -0.048, 0.105),
                          (0.038, -0.075, 0.155)]:
        ang = math.atan2(tx_, -ty_ - ln_ / 2 + 0.04)
        kit.append(T((tx_ / 2, (ty_ - 0.01) / 2, 0.040),
                     r=(0, 0, 1, -ang * 0.5), ch=[
            box((0.0028, ln_, 0.0028), M((0.42, 0.08, 0.06), rough=0.8))]))
    # squat dark-glass ink bottle
    kit.append(T((-0.027, -0.095, 0), ch=[
        soft_shadow(0.055, 0.06, 0.042, blob=True),
        T((0, 0, 0.044), ch=[
            x3d.Shape(geometry=x3d.Cylinder(radius=0.0235, height=0.052),
                      appearance=M((0.05, 0.085, 0.055), rough=0.13)),
            T((0, 0.032, 0), ch=[x3d.Shape(
                geometry=x3d.Cylinder(radius=0.010, height=0.014),
                appearance=M((0.05, 0.085, 0.055), rough=0.13))]),
            T((0, 0.041, 0), ch=[x3d.Shape(
                geometry=x3d.Cylinder(radius=0.011, height=0.006),
                appearance=M((0.55, 0.42, 0.28), rough=0.8))]),
        ]),
        T((0, 0.045, 0.044), ch=[x3d.Shape(              # red pom knot
            geometry=x3d.Sphere(radius=0.006),
            appearance=M((0.50, 0.08, 0.06), rough=0.6))])]))
    # penner: turned black leather pen case, hanging plumb
    kit.append(T((0.016, -0.135, 0), ch=[
        soft_shadow(0.035, 0.17, 0.042),
        T((0, 0, 0.044), ch=[
            x3d.Shape(geometry=x3d.Cylinder(radius=0.0125, height=0.160),
                      appearance=M((0.055, 0.048, 0.042), rough=0.35)),
            T((0, 0.070, 0), ch=[x3d.Shape(
                geometry=x3d.Cylinder(radius=0.0145, height=0.016),
                appearance=M((0.07, 0.06, 0.05), rough=0.3))]),
            T((0, -0.070, 0), ch=[x3d.Shape(
                geometry=x3d.Cylinder(radius=0.0145, height=0.016),
                appearance=M((0.07, 0.06, 0.05), rough=0.3))]),
        ])]))
    root.append(T((kwx, kwy, 0), ch=kit))

    # quill holder at (0.655, 0.83) with white quill butts fanning out
    qhx, qhy = P(0.655, 0.845)
    root.append(T((qhx, qhy, 0), ch=[
        soft_shadow(0.04, 0.11, 0.040, blob=True),
        T((0, 0, 0.042), ch=[
            x3d.Shape(geometry=x3d.Cylinder(radius=0.0145, height=0.095),
                      appearance=M((0.055, 0.048, 0.042), rough=0.35))]),
        T((0, 0.055, 0.042), r=(0, 0, 1, 8 * DEG), ch=[x3d.Shape(
            geometry=x3d.Cone(bottomRadius=0.0045, height=0.040),
            appearance=M((0.93, 0.91, 0.86), rough=0.85))]),
        T((0.007, 0.052, 0.046), r=(0, 0, 1, -14 * DEG), ch=[x3d.Shape(
            geometry=x3d.Cone(bottomRadius=0.0038, height=0.034),
            appearance=M((0.90, 0.88, 0.82), rough=0.85))]),
        T((-0.007, 0.050, 0.038), r=(0, 0, 1, 26 * DEG), ch=[x3d.Shape(
            geometry=x3d.Cone(bottomRadius=0.0035, height=0.030),
            appearance=M((0.95, 0.94, 0.90), rough=0.85))]),
    ]))

    # ---------------- sealing-wax sticks + penknife
    for fx, fy, ang in [(0.390, 0.650, 32), (0.408, 0.735, -12)]:
        wx, wy = P(fx, fy)
        root.append(T((wx, wy, 0), r=(0, 0, 1, ang * DEG), ch=[
            soft_shadow(0.10, 0.02, 0.008),
            T((0, 0, 0.009), ch=[
                box((0.096, 0.0115, 0.008), M((0.45, 0.065, 0.045),
                                              rough=0.22)),
                T((0.052, 0, 0), ch=[box((0.008, 0.0115, 0.008),
                                         M((0.16, 0.05, 0.04), rough=0.5))]),
            ])]))
    pkx, pky = P(0.240, 0.765)
    root.append(T((pkx, pky, 0), r=(0, 0, 1, -35 * DEG), ch=[
        soft_shadow(0.03, 0.16, 0.008),
        T((0, 0.045, 0.008), ch=[
            box((0.011, 0.095, 0.0025),
                M((0.68, 0.70, 0.73), rough=0.22, metal=1.0))]),
        T((0, -0.045, 0.009), ch=[x3d.Shape(
            geometry=x3d.Cylinder(radius=0.0082, height=0.075),
            appearance=M((0.12, 0.075, 0.05), rough=0.5))]),
    ]))

    # ---------------- bottom-left literacy cluster (the counterweight)
    gwx, gwy = P(0.095, 0.795)
    root.append(T((gwx, gwy, 0), r=(0, 0, 1, 9 * DEG), ch=[
        soft_shadow(0.12, 0.10, 0.006),
        T((0, 0, 0.006), ch=[box((0.115, 0.090, 0.0035),
                                 M((1, 1, 1), rough=0.9, tex=tex_gazette()))]),
        T((0.048, 0.038, 0.009), r=(0, 1, 0, -30 * DEG), ch=[   # dog-ear
            box((0.026, 0.022, 0.0015), M((0.85, 0.81, 0.71), rough=0.9))]),
    ]))
    slx, sly = P(0.075, 0.845)
    root.append(T((slx, sly, 0), r=(0, 0, 1, -14 * DEG), ch=letter(
        0.070, 0.052, 401, bend=5, seal=(0.15, 0.0), standoff=0.010)))
    awx, awy = P(0.190, 0.868)
    root.append(T((awx, awy, 0), r=(0, 0, 1, -5 * DEG), ch=[
        soft_shadow(0.085, 0.085, 0.005),
        T((0, 0, 0.005), ch=[box((0.082, 0.086, 0.003),
                                 M((1, 1, 1), rough=0.9,
                                   tex=tex_almanach()))]),
    ]))
    # single manuscript letter hanging over the rail (frame-break 2)
    rlx, rly = P(0.165, 0.930)
    root.append(T((rlx, rly, 0), r=(0, 0, 1, 11 * DEG), ch=letter(
        0.100, 0.075, 402, bend=7, standoff=0.006)))

    # ---------------- iron rod + rings (sagging, cranked at the left)
    iron = M((0.06, 0.057, 0.058), rough=0.5, metal=0.6)
    rody = P(0.5, 0.080)[1]
    rod_half = (BD_R - BD_L) * CW / 2
    for side in (-1, 1):
        root.append(T((side * rod_half / 2 + P(0.5125, 0.5)[0] - 0.007,
                       rody - 0.003, 0.030),
                      r=(0, 0, 1, (90 - side * 0.7) * DEG), ch=[
            x3d.Shape(geometry=x3d.Cylinder(radius=0.0048, height=rod_half),
                      appearance=iron)]))
    rng2 = random.Random(77)
    for i in range(11):
        fxr = 0.375 + i * 0.056 + rng2.uniform(-0.008, 0.008)
        wx, wy = P(fxr, 0.083)
        root.append(T((wx, wy - 0.004, 0.030), ch=[x3d.Shape(
            geometry=x3d.Cylinder(radius=0.0105, height=0.004),
            appearance=iron)], r=(0, 0, 1, 90 * DEG)))

    # ---------------- the curtain: shadow band first, then the silk
    # broad umber shadow hugging the leading edge, lower-left side
    e0 = P(0.36, 0.05)
    e1 = P(0.86, 0.95)
    ex, ey = (e0[0] + e1[0]) / 2, (e0[1] + e1[1]) / 2
    elen = math.hypot(e1[0] - e0[0], e1[1] - e0[1])
    eang = math.atan2(e1[1] - e0[1], e1[0] - e0[0])
    root.append(T((ex - 0.034, ey - 0.016, 0.0035), r=(0, 0, 1, eang), ch=[
        x3d.Shape(geometry=x3d.Rectangle2D(size=(elen, 0.110)),
                  appearance=M((1, 1, 1), rough=1.0,
                               tex=tex_shadow_band()))]))
    root.append(curtain_mesh())

    if viewpoint is not None:
        pos, ori, desc = viewpoint[:3]
        fov = viewpoint[3] if len(viewpoint) > 3 else 0.40
        # NOTE: no description on the Viewpoint -- X_ITE bakes a description
        # toast overlay into headless captures (found in v4 renders).
        kw = dict(position=pos, fieldOfView=fov)
        if ori is not None:
            kw["orientation"] = ori
        root.insert(0, x3d.Viewpoint(**kw))

    return x3d.X3D(profile="Immersive", version="4.0",
                   head=x3d.head(children=[
                       x3d.meta(name="title", content="trompe.x3d"),
                       x3d.meta(name="generator",
                                content=f"trompe.py v{VERSION} "
                                        "(x3d.py 4.0.65.3)"),
                       x3d.meta(name="reference",
                                content="https://open.smk.dk/en/artwork/"
                                        "image/KMS3059"),
                   ]),
                   Scene=x3d.Scene(children=root))


# ------------------------------------------------------ post-serialization
def _patch_xml(xml_str):
    """x3d.py cannot emit containerField, the X_ITE component, or extension
    nodes. Everything here is ASSERTED -- a patch that matches nothing fails
    exactly like the bug it guards against."""
    rootel = etree.fromstring(xml_str.encode())
    counts = dict(base=0, norm=0, meta=0, env=0, face=0, sheen=0, comp=0)

    FACE_SLOTS = {"CMF_front": "frontTexture", "CMF_back": "backTexture",
                  "CMF_left": "leftTexture", "CMF_right": "rightTexture",
                  "CMF_top": "topTexture", "CMF_bottom": "bottomTexture"}

    for el in rootel.iter():
        parent = el.getparent()
        if parent is None:
            continue
        d = el.get("DEF", "")
        if parent.tag == "PhysicalMaterial" and el.tag == "ImageTexture":
            if d.startswith("TXN_"):
                el.set("containerField", "normalTexture")
                counts["norm"] += 1
            else:
                el.set("containerField", "baseTexture")
                counts["base"] += 1
        if parent.tag == "MetadataSet" and el.tag.startswith("Metadata"):
            el.set("containerField", "value")
            counts["meta"] += 1
        if parent.tag == "EnvironmentLight" and \
                el.tag == "ComposedCubeMapTexture":
            el.set("containerField", "specularTexture")
            counts["env"] += 1
        if parent.tag == "ComposedCubeMapTexture" and d in FACE_SLOTS:
            el.set("containerField", FACE_SLOTS[d])
            counts["face"] += 1
        if el.tag == "PhysicalMaterial" and d in _sheen_reg:
            (sc, sr) = _sheen_reg[d]
            ext = etree.SubElement(el, "SheenMaterialExtension")
            ext.set("containerField", "extensions")
            ext.set("sheenColor", f"{sc[0]} {sc[1]} {sc[2]}")
            ext.set("sheenRoughness", str(sr))
            counts["sheen"] += 1
        if el.tag == "EnvironmentLight":
            el.set("global", "true")                     # auditability (A3)

    head = rootel.find("head")
    for name, level in (("CubeMapTexturing", "3"), ("X_ITE", "1")):
        comp = etree.Element("component")
        comp.set("name", name)
        comp.set("level", level)
        head.insert(0, comp)
        counts["comp"] += 1

    out = etree.tostring(rootel, xml_declaration=True, encoding="UTF-8",
                         doctype='<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D '
                                 '4.0//EN" "https://www.web3d.org/specifications'
                                 '/x3d-4.0.dtd">').decode()

    assert counts["base"] >= 20, f"baseTexture patches: {counts['base']}"
    assert counts["norm"] >= 1, f"normalTexture patches: {counts['norm']}"
    assert counts["meta"] == 6, f"metadata patches: {counts['meta']}"
    assert counts["env"] == 1, f"EnvironmentLight cubemap patch: {counts['env']}"
    assert counts["face"] == 6, f"cubemap face patches: {counts['face']}"
    assert counts["sheen"] >= 2, f"sheen extensions: {counts['sheen']}"
    assert counts["comp"] == 2, "head components missing"
    assert "SheenMaterialExtension" in out
    assert "<component name='X_ITE' level='1'/>" in out.replace('"', "'")
    return out


def build_xml(viewpoint=None):
    model = build_scene(viewpoint)
    return _patch_xml(model.XML())


# ------------------------------------------------------------------ views
def look_at(pos, target=(0, 0, 0)):
    d = [target[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in d))
    d = [c / n for c in d]
    f = (0.0, 0.0, -1.0)
    ax = (f[1] * d[2] - f[2] * d[1], f[2] * d[0] - f[0] * d[2],
          f[0] * d[1] - f[1] * d[0])
    axn = math.sqrt(sum(c * c for c in ax))
    ang = math.acos(max(-1, min(1, sum(f[i] * d[i] for i in range(3)))))
    if axn < 1e-9:
        return None
    return (ax[0] / axn, ax[1] / axn, ax[2] / axn, ang)


VIEWS = [
    # THE picture: dead frontal, eye at canvas centre, narrow FOV (~23 deg)
    ("frontal", ((0.005, 0.0, 3.05), None, "the wall piece, straight on",
                 0.40)),
    # relief inspection from the key side -- must stay a shallow relief
    ("raking", ((-1.30, 0.35, 1.60),
                look_at((-1.30, 0.35, 1.60), (0.10, -0.08, 0.0)),
                "grazing from the key side -- the relief", 0.55)),
    # from the curtain side
    ("three_q", ((1.15, -0.28, 1.75),
                 look_at((1.15, -0.28, 1.75), (-0.18, 0.10, 0.0)),
                 "from the curtain side", 0.60)),
]


if __name__ == "__main__":
    print(f"trompe.py v{VERSION}")
    xml = build_xml(VIEWS[0][1])
    out = os.path.join(HERE, "trompe.x3d")
    with open(out, "w") as f:
        f.write(xml)
    print(f"wrote {out} ({len(xml)} bytes)")
