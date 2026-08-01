#!/usr/bin/env python3
"""
antiquity.py -- xenia still life after the Pompeian glass-bowl fresco (MANN 8611)
================================================================================
VERSION 4 · 2026-07-30 · EUPHEME Technologies LLC

An X3D 4.0 still life INSPIRED BY (not a record of):

    Unknown Pompeian painter (Fourth Style workshop), "Still Life with Glass
    Bowl of Fruit and Vases" (xenia panel from the Praedia of Julia Felix,
    Pompeii II.4.3), c. AD 62-79, fresco. Museo Archeologico Nazionale di
    Napoli, inv. 8611. Public domain.

V4 is a full recomposition against research/antiquity.md (measured coordinate
table, palette, tonal key). The construction:

  * PANEL SPACE. The fresco panel is W:H = 1.54:1; world units are panel
    fractions (x = (fx-0.5)*1.54, y = 1-fy). Every object lands where the
    painter put it. The fictive maroon frame + teal fillet is built as a real
    proscenium IN FRONT of the ledge, so the left border genuinely amputates
    the pomegranate debris and the bottom border crops the ledge face.
  * THE GLASS: the painter's four devices, not renderer refraction (which
    X_ITE does not have -- transmission/IOR/volume are verified dead):
    wall reads through the empty glass (alpha shell), fruit INSIDE is darker/
    desaturated/rougher than fruit above the rim, BOTH rim ellipses are drawn
    (a slate-teal torus), speculars are discrete warm-white dashes + one long
    belly streak (emissive geometry), never gradients.
  * Deliberately inconsistent perspective, kept: ledge seen at ~5deg (camera
    at ledge height) but the bowl TILTED ~17deg toward camera to open the rim.
  * One warm key from the viewer's left (az ~255deg, el ~40deg); IBL ambience
    from an authored gradient cubemap (EnvironmentLight.specularTexture -- the
    only live IBL slot); shadows are BAKED contact tongues to the right,
    <=0.4x object height, because X_ITE ignores light.shadows entirely.
  * Compressed mid-key target (fresco measures p5 70 / p95 157 / mean 116).

Serializer traps this file works around (all injected post-serialization AND
ASSERTED -- see _fix_xml):
  * containerField dropped on PhysicalMaterial texture slots (base/normal).
  * containerField='value' dropped on MetadataSet members.
  * <component name='X_ITE' level='1'/> refused by x3d.py's whitelist -- needed
    for the Sheen extension (grape/prune bloom); injected raw.
  * SheenMaterialExtension has no x3d.py class -- injected raw into the DEF'd
    materials.
  * EnvironmentLight specularTexture slot + ComposedCubeMapTexture face slots
    lose containerField and the faces get alphabetically scrambled -- the whole
    IBL block is authored as raw XML with explicit containerFields.
"""

import base64
import io
import math
import os
import re
import sys

VERSION = "4"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/x3d_mcp/src"))
from x3d import x3d as X  # noqa: E402  (x3d.py 4.0.65.3)

# ---------------------------------------------------------------------------
# panel geometry -- world units are fresco-panel fractions (research table)
# ---------------------------------------------------------------------------
PANEL_W, PANEL_H = 1.54, 1.00

def px(fx):  # panel fraction x -> world
    return (fx - 0.5) * PANEL_W

def py(fy):  # panel fraction y (top->bottom) -> world
    return 1.0 - fy

LEDGE_TOP = 0.25          # main block top surface (fresco front edge y=0.755)
SHELF_TOP = 0.19          # right shelf, lower and RECESSED
LEDGE_FRONT_Z = 0.22
SHELF_FRONT_Z = 0.06
STEP_X = 0.22             # the step corner (fresco x ~0.63)
WALL_Z = -0.34            # wall CLOSE behind -- a wall, not a void
WALL_FACE_Z = WALL_Z + 0.025
FRAME_Z = 0.30            # the fictive-frame proscenium plane

# ---------------------------------------------------------------------------
# palette -- reconciled photo measurements (research section 4: the wall is
# pale warm grey-white, NOT ochre, NOT cyan; warmth lives in the objects)
# ---------------------------------------------------------------------------
WALL_LIT   = (0.835, 0.823, 0.788)   # d5d2c9
WALL_SHD   = (0.549, 0.514, 0.475)   # 8c8379
WALL_HALO  = (0.753, 0.639, 0.482)   # c0a37b
STONE_TOP  = (0.725, 0.702, 0.651)   # b9b3a6
STONE_FRT  = (0.490, 0.416, 0.384)   # 7d6a62
STONE_DARK = (0.365, 0.286, 0.282)   # 5d4948
MAROON     = (0.373, 0.227, 0.235)   # 5f3a3c
TEAL_FIL   = (0.310, 0.478, 0.502)   # 4f7a80
PALE_LINE  = (0.80, 0.78, 0.72)
SURROUND   = (0.42, 0.355, 0.30)     # weathered frieze plaster beyond the border
GLASS      = (0.60, 0.71, 0.67)      # blue-green soda-lime, thin wall
GLASS_RIM  = (0.235, 0.290, 0.290)   # 3c4a4a drawn rim line
DASH       = (0.910, 0.894, 0.847)   # e8e4d8 specular dashes
APPLE      = (0.788, 0.647, 0.267)   # c9a544
BLUSH      = (0.616, 0.353, 0.227)   # 9d5a3a
PALE_FRUIT = (0.718, 0.690, 0.514)   # b7b083
GRAPE      = (0.431, 0.278, 0.220)   # 6e4738 red-brown/amber, not purple
GRAPE_LT   = (0.769, 0.604, 0.416)   # c49a6a
TWIG       = (0.30, 0.17, 0.12)
POM_SKIN   = (0.478, 0.231, 0.227)   # 7a3b3a
POM_SEED   = (0.627, 0.290, 0.282)   # a04a48
POM_FLESH  = (0.788, 0.639, 0.486)   # c9a37c
CLAY_AMPH  = (0.722, 0.604, 0.365)   # c8a95f buff Campanian clay
CLAY_OLLA  = (0.615, 0.385, 0.275)   # deeper orange-red coarse ware (a2 pink)
CLAY_LID   = (0.545, 0.345, 0.255)
PRUNE      = (0.424, 0.278, 0.212)   # 6c4736
SKY        = (0.12, 0.10, 0.085)     # authored Background (rarely visible)

# interior-fruit versions: 20-30% darker, desaturated, rougher (device #2)
def _behind_glass(c, k=0.75, grey=0.16):
    g = (c[0] + c[1] + c[2]) / 3.0
    return tuple(k * ((1 - grey) * v + grey * g) for v in c)


# ---------------------------------------------------------------------------
# procedural textures (PIL/numpy) -> data URIs
# ---------------------------------------------------------------------------
def _np():
    import numpy as np
    return np

def _blur(a, r):
    from PIL import Image, ImageFilter
    np = _np()
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), dtype=float) / 255.0

def _mottle(w, h, base, amp, seed, crack=0.0):
    """Tileable warm mottle; optional faint craquelure (mod-wrap walks)."""
    np = _np()
    rng = np.random.default_rng(seed)
    n = _blur(rng.random((h, w)), min(w, h) / 22.0)
    n = (n - n.mean()) / (n.std() + 1e-9)
    rgb = np.zeros((h, w, 3))
    for c in range(3):
        rgb[..., c] = base[c] + n * amp[c]
    rgb += rng.normal(0, 0.010, (h, w, 1))
    if crack > 0:
        for _ in range(int(crack)):
            x, y = rng.integers(0, w), rng.integers(0, h)
            ang = rng.uniform(0, 2 * math.pi)
            for _s in range(int(rng.integers(min(w, h) // 4, min(w, h)))):
                ang += rng.normal(0, 0.28)
                x = (x + math.cos(ang)) % w
                y = (y + math.sin(ang)) % h
                rgb[int(y), int(x)] *= 0.955
    return rgb

def _to_uri(rgb):
    from PIL import Image
    np = _np()
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype("uint8"), "RGB")
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def _normal_from_height(hmap, strength):
    np = _np()
    gy, gx = np.gradient(hmap * strength)
    nz = np.ones_like(hmap)
    ln = np.sqrt(gx * gx + gy * gy + nz * nz)
    n = np.stack([-gx / ln, gy / ln, nz / ln], axis=-1)
    return (n + 1.0) / 2.0

def make_wall_texture(w=512, h=352):
    """The fresco's tonal geography baked in: lit warm-grey upper-left falling
    to grey-olive upper-right, a warm luminous halo just above the ledge
    (strongest behind amphora/olla), a soft diagonal darkening where the
    amphora leans (its 'shadow' -- painted, as the painter painted his), and
    mottle + faint craquelure. Mapped ONCE across the wall (no tiling: the
    gradient is the point)."""
    np = _np()
    u = np.linspace(0, 1, w)[None, :]
    v = np.linspace(0, 1, h)[:, None]          # v=0 top of wall
    rgb = np.zeros((h, w, 3))
    t = np.clip((u - 0.15) / 0.85, 0, 1) * np.clip((1 - v) * 1.6, 0, 1)
    for c in range(3):
        rgb[..., c] = WALL_LIT[c] * (1 - t) + WALL_SHD[c] * t
    # warm halo above the ledge line (wall v ~0.72 at ledge top, see mapping)
    halo = np.exp(-(((v - 0.72) / 0.12) ** 2)) * np.exp(-(((u - 0.62) / 0.34) ** 2))
    for c in range(3):
        rgb[..., c] = rgb[..., c] * (1 - 0.24 * halo) + WALL_HALO[c] * 0.24 * halo
    # painted lean-shadow of the amphora: soft diagonal blob, right of centre
    du, dv = u - 0.640, v - 0.52
    dd = np.exp(-(((du * 0.86 + dv * 0.50) / 0.050) ** 2)
                - (((-du * 0.50 + dv * 0.86) / 0.18) ** 2))
    rgb *= (1 - 0.11 * dd)[..., None]
    m = _mottle(w, h, (0, 0, 0), (0.040, 0.038, 0.042), seed=7, crack=10)
    rgb += m
    return rgb

def make_textures():
    T = {}
    T["wall"] = _to_uri(make_wall_texture())
    T["stone_top"] = _to_uri(_mottle(160, 160, STONE_TOP, (0.050, 0.046, 0.042), 21, crack=4))
    T["stone_front"] = _to_uri(_mottle(160, 160, STONE_FRT, (0.045, 0.040, 0.038), 22, crack=5))
    T["stone_dark"] = _to_uri(_mottle(128, 128, STONE_DARK, (0.035, 0.030, 0.030), 23))
    T["maroon"] = _to_uri(_mottle(128, 128, MAROON, (0.055, 0.045, 0.045), 31, crack=3))
    T["surround"] = _to_uri(_mottle(160, 160, SURROUND, (0.060, 0.052, 0.046), 33, crack=6))
    # fruit: satin body + red-brown blush patch (research 1.2)
    np = _np()
    for name, base, blush, bamp in (("apple", APPLE, BLUSH, 0.85),
                                    ("pale", PALE_FRUIT, (0.55, 0.50, 0.34), 0.45),
                                    ("quince", (0.777, 0.635, 0.247), BLUSH, 0.35)):
        w = h = 96
        u = np.linspace(0, 1, w)[None, :]
        v = np.linspace(0, 1, h)[:, None]
        rgb = np.zeros((h, w, 3))
        for c in range(3):
            rgb[..., c] = base[c]
        blob = np.exp(-(((u - 0.62) / 0.20) ** 2) - (((v - 0.42) / 0.26) ** 2)) * bamp
        for c in range(3):
            rgb[..., c] = rgb[..., c] * (1 - blob) + blush[c] * blob
        rgb += _mottle(w, h, (0, 0, 0), (0.03, 0.03, 0.02), seed=hash(name) % 999)
        T[name] = _to_uri(rgb)
    # amphora wheel-tooling ridges: faint horizontal bands -> normal map
    # (a1 verdict: strength 2.2 / freq 15 rendered a beehive, not tooling)
    v = np.linspace(0, 1, 96)[:, None] * np.ones((1, 96))
    rng = np.random.default_rng(5)
    hmap = 0.5 + 0.5 * np.sin(v * 2 * math.pi * 9 + rng.normal(0, 0.25, (96, 96)) * 0.4)
    hmap = _blur(hmap, 1.6)
    T["ripple_n"] = _to_uri(_normal_from_height(hmap, 0.55))
    # plaster undulation normal (subtle)
    hmap = _blur(rng.random((192, 192)), 14.0)
    T["plaster_n"] = _to_uri(_normal_from_height(hmap, 3.0))
    return T

def make_cubemap():
    """Authored ambience cubemap: bright warm from the key side (left/top),
    dim grey-olive right, warm ledge-bounce below. Smooth gradients so the
    glass picks up a soft sheen, never a picture-postcard reflection."""
    np = _np()
    def face(top, bottom, w=48):
        v = np.linspace(0, 1, w)[:, None]
        rgb = np.zeros((w, w, 3))
        for c in range(3):
            rgb[..., c] = (top[c] * (1 - v) + bottom[c] * v) / 255.0
        rgb += np.random.default_rng(1).normal(0, 0.008, (w, w, 1))
        return _to_uri(rgb)
    return {
        "left":   face((238, 224, 194), (206, 182, 150)),
        "top":    face((240, 228, 200), (225, 210, 180)),
        "right":  face((126, 118, 106), (104, 96, 86)),
        "front":  face((186, 173, 150), (150, 136, 116)),
        "back":   face((186, 173, 150), (150, 136, 116)),
        "bottom": face((168, 138, 104), (122, 102, 80)),
    }


# ---------------------------------------------------------------------------
# small builders
# ---------------------------------------------------------------------------
_DEF_SEEN = None  # reset per build

def matp(color, rough=0.75, metal=0.0, transp=0.0, emissive=None, DEF=None):
    global _DEF_SEEN
    if DEF is not None and DEF in _DEF_SEEN:
        return X.Appearance(material=X.PhysicalMaterial(USE=DEF))
    kw = dict(baseColor=color, roughness=rough, metallic=metal)
    if transp:
        kw["transparency"] = transp
    if emissive:
        kw["emissiveColor"] = emissive
    if DEF is not None:
        _DEF_SEEN.add(DEF)
        kw["DEF"] = DEF
    return X.Appearance(material=X.PhysicalMaterial(**kw))

def tex_app(key, uri, rough=0.75, tile=None, normal=None, normal_uri=None,
            aniso=False):
    """Textured appearance. DEF/USE dedup on the ImageTexture; the DEF prefix
    (BT_/NT_) tells _fix_xml which containerField to inject."""
    global _DEF_SEEN
    def img(prefix, k, u):
        d = prefix + k.upper()
        if d in _DEF_SEEN:
            return X.ImageTexture(USE=d)
        _DEF_SEEN.add(d)
        kw = dict(DEF=d, url=[u])
        if aniso:
            kw["textureProperties"] = X.TextureProperties(
                generateMipMaps=True, anisotropicDegree=8.0)
        return X.ImageTexture(**kw)
    m = dict(baseColor=(1, 1, 1), roughness=rough, metallic=0.0,
             baseTexture=img("BT_", key, uri))
    if normal:
        m["normalTexture"] = img("NT_", normal, normal_uri)
    app = X.Appearance(material=X.PhysicalMaterial(**m))
    if tile:
        app.textureTransform = X.TextureTransform(scale=tile)
    return app

def ball(x, y, z, r, app, scale=None, rot=None):
    t = X.Transform(translation=(x, y, z),
                    children=[X.Shape(geometry=X.Sphere(radius=r), appearance=app)])
    if scale:
        t.scale = scale
    if rot:
        t.rotation = rot
    return t

def box(center, size, app):
    return X.Transform(translation=center,
                       children=[X.Shape(geometry=X.Box(size=size), appearance=app)])

def circle(n=28, r=1.0):
    pts = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n))
           for k in range(n)]
    pts.append(pts[0])
    return pts

def lathe(profile, app, n=32, caps=True, crease=1.2, solid=True):
    spine = [(0.0, y, 0.0) for (y, _r) in profile]
    scale = [(max(r, 0.003), max(r, 0.003)) for (_y, r) in profile]
    return X.Shape(appearance=app,
                   geometry=X.Extrusion(crossSection=circle(n), spine=spine,
                                        scale=scale, beginCap=caps, endCap=caps,
                                        creaseAngle=crease, solid=solid))

def torus(R, r, app, n=48, m=10):
    spine = [(R * math.cos(2 * math.pi * k / n), 0.0, R * math.sin(2 * math.pi * k / n))
             for k in range(n)]
    spine.append(spine[0])
    return X.Shape(appearance=app,
                   geometry=X.Extrusion(crossSection=circle(m, r), spine=spine,
                                        beginCap=False, endCap=False,
                                        creaseAngle=1.2, solid=True))

def look_at(pos, target, up=(0.0, 1.0, 0.0)):
    import numpy as np
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

def _norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


# ---------------------------------------------------------------------------
# baked contact shadows -- X_ITE ignores light.shadows entirely (verified:
# byte-identical renders). The fresco's own shadows are conventional short
# soft tongues to the RIGHT, <=0.4x object height -- period-accurate baking.
# ---------------------------------------------------------------------------
SHADOW_DIR = (0.9, 0.25)   # +x (key is from the left), slightly toward viewer

def contact(x, z, rx, y, rz=None, strength=0.55, stretch=1.8, lift=0.0):
    """Squashed translucent dark ellipsoids, half-buried in the surface.
    (a1-a3 used flat discs, which foreshorten to an invisible LINE at this
    scene's near-grazing ~4deg camera -- the fresco painter drew his shadow
    tongues from a higher viewpoint than his ledge, and so must we.)"""
    rz = rz if rz is not None else rx * 0.62
    ox = SHADOW_DIR[0] * rx * 0.55
    oz = SHADOW_DIR[1] * rz * 0.55
    layers = []
    for sc, a, h in ((1.00, 0.30, 0.011), (0.55, min(0.9, strength + 0.1), 0.017)):
        layers.append(X.Transform(
            translation=(x + ox * (1 - sc * 0.5), y + lift + 0.001,
                         z + oz * (1 - sc * 0.5)),
            scale=(rx * sc * stretch, h, rz * sc),
            children=[X.Shape(
                appearance=matp((0.11, 0.088, 0.075), rough=1.0, transp=1.0 - a),
                geometry=X.Sphere(radius=1.0))]))
    return layers


# ---------------------------------------------------------------------------
# the props
# ---------------------------------------------------------------------------
def pomegranate(T):
    """Burst pomegranate at the LEFT frame edge, split open (ClipPlane cut),
    seed mass behind the cut, debris trailing left until the border amputates
    it (research 1.3: 'the memento at the picture's entry point')."""
    cx, cy, cz = px(0.145), LEDGE_TOP + 0.074, 0.08
    # the split faces the camera (a1: a cut facing up-left showed only skin)
    open_dir = _norm((0.30, 0.28, 0.92))
    kids = []
    # skin sphere, cap clipped off toward open_dir
    kids.append(X.Transform(translation=(cx, cy, cz), children=[X.Group(children=[
        X.ClipPlane(plane=(-open_dir[0], -open_dir[1], -open_dir[2], 0.026)),
        X.Shape(geometry=X.Sphere(radius=0.082),
                appearance=matp((0.44, 0.20, 0.19), rough=0.55))])]))
    # seed mass filling the aperture -- must contrast the skin or the split
    # vanishes (a2: near-identical salmon, read as one ball)
    kids.append(ball(cx + open_dir[0] * 0.014, cy + open_dir[1] * 0.014,
                     cz + open_dir[2] * 0.014, 0.072,
                     matp((0.60, 0.185, 0.145), rough=0.30)))
    # a few individual seeds proud of the mass at the lip
    import random as _r
    _rs = _r.Random(4)
    for i in range(6):
        a = _rs.uniform(0, 2 * math.pi)
        rr = _rs.uniform(0.015, 0.045)
        p = _norm((open_dir[0] + 0.4 * math.cos(a) * 0.3,
                   open_dir[1] + 0.4 * math.sin(a) * 0.3, open_dir[2]))
        kids.append(ball(cx + p[0] * 0.066 + rr * math.cos(a) * 0.3,
                         cy + p[1] * 0.066 + rr * math.sin(a) * 0.2,
                         cz + p[2] * 0.066, 0.011,
                         matp((0.70, 0.33, 0.30), rough=0.30)))
    # debris: loose seeds + juice smear trailing LEFT to the frame
    import random
    rnd = random.Random(8611)
    for i in range(8):
        dx = -0.02 - 0.20 * (i / 7.0) - rnd.uniform(0, 0.02)
        dz = rnd.uniform(-0.03, 0.05)
        kids.append(ball(cx + dx, LEDGE_TOP + 0.012, cz + dz, 0.0125,
                         matp(POM_SEED, rough=0.4)))
    kids.append(X.Transform(
        translation=(cx - 0.12, LEDGE_TOP + 0.004, cz + 0.01), scale=(2.4, 1, 1),
        children=[X.Shape(geometry=X.Cylinder(radius=0.038, height=0.005),
                          appearance=matp((0.40, 0.14, 0.11), rough=0.35))]))
    # the thin dark twig beside the debris
    kids.append(X.Transform(translation=(cx - 0.16, LEDGE_TOP + 0.008, cz + 0.05),
                            rotation=(0, 0, 1, 1.45),
                            children=[X.Shape(geometry=X.Cylinder(radius=0.003, height=0.14),
                                              appearance=matp(TWIG, rough=0.9))]))
    return kids


def quince(T):
    """The lone quince at panel centre-bottom -- the compositional hinge."""
    return [ball(px(0.525), LEDGE_TOP + 0.066, 0.10, 0.068,
                 tex_app("quince", T["quince"], rough=0.42),
                 rot=(0, 1, 0, 2.1))]


def amphora(T):
    """Buff-clay table amphora, sealed and tied, leaning ~30deg mouth-up-right,
    toe on the main ledge behind the quince, upper body propped against the
    wall (the lean is frankly improbable in the fresco; kept)."""
    clay = (0.655, 0.525, 0.295)     # deeper ochre than a2's pale cream
    parts = []
    # ONE smooth lathe, blunt toe to rim (a2's cone+sphere stack showed its
    # seams as a soft-serve fold at the toe)
    profile = [(0.000, 0.010), (0.015, 0.024), (0.050, 0.044), (0.100, 0.062),
               (0.160, 0.086), (0.230, 0.108), (0.320, 0.122), (0.380, 0.118),
               (0.430, 0.098), (0.462, 0.070), (0.482, 0.052), (0.492, 0.047),
               (0.558, 0.045), (0.570, 0.052), (0.580, 0.056)]
    parts.append(lathe(profile, matp(clay, rough=0.82), n=36))
    # plug the mouth: Extrusion endCap silently fails to draw here (a4's mouth
    # rendered as an open ring with the wall showing through the neck)
    parts.append(X.Transform(translation=(0, 0.578, 0),
                             children=[X.Shape(geometry=X.Cylinder(radius=0.055, height=0.007),
                                               appearance=matp(clay, rough=0.82))]))
    # stopper + cord tie (ancientrome.ru reads it sealed); the stopper must
    # FILL the rim or the open mouth reads as a floating ring (a3)
    parts.append(X.Transform(translation=(0, 0.586, 0),
                             children=[X.Shape(geometry=X.Cylinder(radius=0.032, height=0.020),
                                               appearance=matp((0.72, 0.65, 0.52), rough=0.9))]))
    parts.append(X.Transform(translation=(0, 0.532, 0),
                             children=[torus(0.051, 0.0065, matp((0.42, 0.33, 0.22), rough=0.95),
                                             n=24, m=8)]))
    # two loop handles, shoulder to rim, in the picture plane
    for sx in (-1, 1):
        spine = []
        for k in range(9):
            t = k / 8.0
            ang = math.pi * (1.0 - t)
            spine.append((sx * (0.054 + 0.046 * math.sin(ang)),
                          0.425 + 0.138 * t, 0.0))
        parts.append(X.Shape(appearance=matp(clay, rough=0.82),
                             geometry=X.Extrusion(crossSection=circle(8, 0.011),
                                                  spine=spine, creaseAngle=1.2,
                                                  beginCap=True, endCap=True, solid=True)))
    # lean: back toward the wall, then 30deg off vertical to the right; the
    # toe lands just behind the quince (a2's toe sat a whole depth-plane back;
    # a3's -0.30 back-lean foreshortened the vessel into a flat gourd)
    inner = X.Transform(rotation=(1, 0, 0, -0.12), children=parts)
    return X.Transform(translation=(0.105, LEDGE_TOP + 0.004, -0.06),
                       rotation=(0, 0, 1, -0.52), children=[inner])


def olla(T):
    """Orange-red coarse-ware olla on the lower recessed shelf, heaped with
    dried prunes; ovoid terracotta lid leaning against its front-left."""
    ox, oz = px(0.83), -0.17
    kids = []
    kids.append(X.Transform(translation=(ox, SHELF_TOP + 0.108, oz), scale=(1, 0.80, 1),
                            children=[X.Shape(geometry=X.Sphere(radius=0.130),
                                              appearance=matp(CLAY_OLLA, rough=0.72))]))
    # short neck + everted rim
    kids.append(X.Transform(translation=(ox, SHELF_TOP + 0.208, oz),
                            children=[X.Shape(geometry=X.Cylinder(radius=0.084, height=0.030),
                                              appearance=matp(CLAY_OLLA, rough=0.72))]))
    kids.append(X.Transform(translation=(ox, SHELF_TOP + 0.226, oz),
                            children=[torus(0.094, 0.014, matp((0.60, 0.38, 0.28), rough=0.7),
                                            n=32, m=8)]))
    # dried prunes heaped over the rim (matte wrinkled lumps; sheen = bloom)
    import random
    rnd = random.Random(3)
    for i in range(14):
        an = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, 0.066)
        kids.append(ball(ox + r * math.cos(an),
                         SHELF_TOP + 0.238 + rnd.uniform(0, 0.050) - r * 0.35,
                         oz + r * math.sin(an), 0.030,
                         matp(PRUNE, rough=0.85, DEF="M_PRUNE"),
                         scale=(1, 0.80, 1),
                         rot=(rnd.random(), 1, rnd.random(), rnd.uniform(0, 3))))
    # the lid: ovoid terracotta disc leaning front-left of the pot, read
    # nearly edge-on (a1: a big frontal disc read as a second pot)
    kids.append(X.Transform(
        translation=(px(0.745), SHELF_TOP + 0.082, oz + 0.090),
        rotation=(0, 0, 1, 0.50),
        children=[X.Transform(rotation=(0, 1, 0, 0.55),
                              children=[X.Transform(
                                  rotation=(1, 0, 0, -0.30), scale=(1.0, 1.28, 0.14),
                                  children=[X.Shape(geometry=X.Sphere(radius=0.078),
                                                    appearance=matp(CLAY_LID, rough=0.78))])])]))
    return kids


def glass_bowl(T):
    """The glass krater -- the earliest convincing painted glass, rebuilt by
    the painter's own four devices. Returns ONE tilted Transform whose child
    order is load-bearing: interior fruit first, heap, grapes, twig, then the
    alpha glass shell LAST, then the drawn rim + specular dashes."""
    bx, bz = px(0.30), -0.10
    TILT = 0.34           # ~19deg toward camera: opens the rim ellipse the
    #                       fresco insists on while the ledge stays at ~5deg
    kids = []
    import random
    rnd = random.Random(79)

    # shell profile (shared by geometry and the grape-spill fit)
    shell = [(0.075, 0.070), (0.100, 0.150), (0.160, 0.225), (0.240, 0.272),
             (0.330, 0.288), (0.420, 0.282), (0.455, 0.286), (0.478, 0.298)]
    def shell_r(y):
        for (y0, r0), (y1, r1) in zip(shell, shell[1:]):
            if y0 <= y <= y1:
                t = (y - y0) / (y1 - y0)
                return r0 + t * (r1 - r0)
        return shell[-1][1]

    # --- fruit INSIDE (device 2: darker, desaturated, soft = rougher) -----
    inside = [(-0.10, 0.30, 0.03, 0.080, APPLE), (0.07, 0.28, 0.08, 0.075, PALE_FRUIT),
              (0.00, 0.27, -0.09, 0.078, BLUSH), (0.14, 0.31, -0.03, 0.072, APPLE),
              (-0.15, 0.29, -0.06, 0.070, (0.777, 0.635, 0.247)),
              (-0.02, 0.40, 0.05, 0.076, PALE_FRUIT), (0.09, 0.41, -0.08, 0.070, APPLE),
              (-0.11, 0.42, -0.04, 0.068, BLUSH)]
    # tint the interior fruit toward the blue-green of the glass as well as
    # darkening it -- a2's neutral desaturation read as grey cue balls
    for dx, y, dz, r, c in inside:
        g = _behind_glass(c, k=0.55, grey=0.15)
        g = (g[0] * 0.96, g[1] * 1.0, g[2] * 0.95)
        kids.append(ball(dx, y, dz, r, matp(g, rough=0.85),
                         rot=(0, 1, 0, rnd.uniform(0, 3))))

    # --- heap ABOVE the rim (lit, saturated, textured) --------------------
    heap = [(-0.17, 0.52, 0.02, 0.088, "apple", True), (0.00, 0.55, 0.09, 0.082, "apple", False),
            (0.05, 0.54, -0.08, 0.085, "apple", False), (-0.07, 0.60, -0.02, 0.078, "quince", True),
            (-0.20, 0.56, -0.08, 0.070, "pale", False), (0.12, 0.50, 0.05, 0.070, "apple", False),
            (-0.26, 0.50, 0.03, 0.072, "quince", False)]
    for dx, y, dz, r, key, stem in heap:
        kids.append(ball(dx, y, dz, r, tex_app(key, T[key], rough=0.42),
                         rot=(0, 1, 0, rnd.uniform(0, 6))))
        if stem:
            kids.append(X.Transform(translation=(dx, y + r + 0.006, dz),
                                    rotation=(0.2, 0, 1, rnd.uniform(-0.3, 0.3)),
                                    children=[X.Shape(geometry=X.Cylinder(radius=0.003, height=0.018),
                                                      appearance=matp(TWIG, rough=0.9))]))

    # --- the double grape bunch over the RIGHT rim ------------------------
    # In the fresco the bunch is a broad MASS rising ABOVE the heap on the
    # right and bulging over the rim edge; it dangles only a short way down
    # the outer wall (a2's long single-file cascade read as a bead chain).
    def berry(dx, y, dz, r):
        return ball(dx, y, dz, r, matp(GRAPE, rough=0.55, DEF="M_GRAPE"))
    for i in range(34):                  # the mound -- packed, rises to ~0.64
        a = rnd.uniform(0, 2 * math.pi)
        rr = 0.095 * math.sqrt(rnd.random())
        cy = 0.545 + 0.075 * (1 - (rr / 0.095) ** 2) - abs(rr * math.cos(a)) * 0.25
        kids.append(berry(0.205 + rr * math.cos(a) * 1.2 + rnd.uniform(-0.006, 0.006),
                          cy + rnd.uniform(-0.012, 0.012),
                          rr * math.sin(a) * 0.72 - 0.02, rnd.uniform(0.022, 0.027)))
    for i in range(9):                   # bulge riding the rim edge itself
        a = 0.55 + 0.09 * i
        rr = 0.295
        kids.append(berry(rr * math.sin(a) * 0.98 + rnd.uniform(-0.008, 0.008),
                          0.485 + rnd.uniform(-0.014, 0.010),
                          rr * math.cos(a) * 0.85 + rnd.uniform(-0.010, 0.010),
                          rnd.uniform(0.022, 0.026)))
    for i in range(8):                   # the short outside dangle, two wide
        t = i / 7.0
        yb = 0.455 - 0.115 * t
        rr = shell_r(yb) + 0.018
        ab = 0.80 + 0.22 * t + (0.10 if i % 2 else -0.04)
        kids.append(berry(rr * math.sin(ab), yb + rnd.uniform(-0.008, 0.008),
                          rr * math.cos(ab) * 0.9,
                          rnd.uniform(0.020, 0.025) * (1 - 0.2 * t)))
    # a few pale top-light dots read as berry highlights
    for i in range(6):
        a = rnd.uniform(0, 2 * math.pi)
        kids.append(ball(0.205 + 0.055 * math.cos(a), 0.615 + rnd.uniform(0, 0.02),
                         0.055 * math.sin(a) * 0.7, 0.0055, matp(GRAPE_LT, rough=0.5)))

    # --- the dry vine twig -- a delicate forked scribble, highest mark ----
    kids.append(X.Transform(translation=(0.09, 0.65, -0.02), rotation=(0.15, 0, 1, -0.38),
                            children=[X.Shape(geometry=X.Cylinder(radius=0.0030, height=0.26),
                                              appearance=matp(TWIG, rough=0.9))]))
    kids.append(X.Transform(translation=(0.035, 0.71, 0.00), rotation=(0.1, 0, 1, 0.62),
                            children=[X.Shape(geometry=X.Cylinder(radius=0.0026, height=0.13),
                                              appearance=matp(TWIG, rough=0.9))]))
    kids.append(X.Transform(translation=(0.13, 0.72, -0.03), rotation=(-0.2, 0, 1, -0.95),
                            children=[X.Shape(geometry=X.Cylinder(radius=0.0024, height=0.09),
                                              appearance=matp(TWIG, rough=0.9))]))

    # --- the glass itself, LAST (alpha draw order is load-bearing) --------
    # foot: low splayed pedestal, dark teal, thick glass reads nearly opaque
    kids.append(lathe([(0.000, 0.115), (0.012, 0.104), (0.030, 0.066), (0.078, 0.058)],
                      matp((0.235, 0.315, 0.305), rough=0.30), n=36))
    kids.append(X.Transform(translation=(0, 0.006, 0),
                            children=[torus(0.113, 0.0050,
                                            matp(GLASS_RIM, rough=0.5, transp=0.10))]))
    # thin-walled shell
    kids.append(lathe(shell, matp(GLASS, rough=0.05, transp=0.70),
                      n=44, caps=False, solid=False))
    # device 3: BOTH rim ellipses drawn -- the slate-teal torus is the line
    kids.append(X.Transform(translation=(0, 0.478, 0),
                            children=[torus(0.298, 0.0062,
                                            matp(GLASS_RIM, rough=0.5, transp=0.10))]))
    # device 4: discrete warm-white dashes lying TANGENT along the front-left
    # rim (a2 left the cylinders on their y axis: four white pins)
    for ang, ln in ((1.95, 0.040), (2.22, 0.028), (2.50, 0.034), (2.78, 0.022)):
        kids.append(X.Transform(
            translation=(0.296 * math.cos(ang), 0.478, 0.296 * math.sin(ang)),
            rotation=(0, 1, 0, -ang),
            children=[X.Transform(rotation=(0, 0, 1, math.pi / 2), children=[
                X.Shape(geometry=X.Cylinder(radius=0.0030, height=ln),
                        appearance=matp(DASH, rough=0.3,
                                        emissive=(0.27, 0.26, 0.24)))])]))
    # ...and ONE long diagonal streak on the upper-left belly, on the glass
    # surface, clear of the pomegranate below (a2: read as a straw into it)
    kids.append(X.Transform(
        translation=(-0.150, 0.360, 0.248), rotation=(0.12, 0.06, 0.99, 0.24),
        children=[X.Shape(geometry=X.Cylinder(radius=0.0030, height=0.085),
                          appearance=matp(DASH, rough=0.3,
                                          emissive=(0.21, 0.20, 0.18)))]))
    return X.Transform(translation=(bx, LEDGE_TOP - 0.012, bz),
                       rotation=(1, 0, 0, TILT), children=kids)


# ---------------------------------------------------------------------------
# architecture: ledges, wall, fictive frame (a real proscenium)
# ---------------------------------------------------------------------------
def ledges(T):
    kids = []
    # main block (left): body + textured lit top slab + front + DARK right face
    kids.append(box((-0.54, -0.05, -0.06), (1.52, 0.60, 0.56), matp(STONE_FRT, 0.9)))
    kids.append(box((-0.54, LEDGE_TOP - 0.005, -0.06), (1.52, 0.010, 0.56),
                    tex_app("stone_top", T["stone_top"], rough=0.62,
                            tile=(2.6, 1.0), aniso=True)))
    kids.append(box((-0.54, -0.05, LEDGE_FRONT_Z - 0.005), (1.52, 0.60, 0.012),
                    tex_app("stone_front", T["stone_front"], rough=0.85, tile=(2.6, 1.1))))
    kids.append(box((STEP_X + 0.005, -0.05, -0.06), (0.012, 0.60, 0.56),
                    tex_app("stone_dark", T["stone_dark"], rough=0.95)))
    # right shelf: lower AND recessed
    kids.append(box((0.76, -0.08, -0.14), (1.08, 0.54, 0.40), matp(STONE_FRT, 0.9)))
    kids.append(box((0.76, SHELF_TOP - 0.005, -0.14), (1.08, 0.010, 0.40),
                    tex_app("stone_top", T["stone_top"], rough=0.62,
                            tile=(1.9, 0.8), aniso=True)))
    kids.append(box((0.76, -0.08, SHELF_FRONT_Z - 0.005), (1.08, 0.54, 0.012),
                    tex_app("stone_front", T["stone_front"], rough=0.85, tile=(1.9, 1.0))))
    # ground shadow slab far below (visible only off-axis)
    kids.append(box((0, -0.37, 0.2), (4.4, 0.02, 3.0), matp((0.16, 0.14, 0.12), 0.95)))
    return kids


def wall(T):
    """Pale warm grey-white plaster CLOSE behind -- with the tonal geography
    (fall to grey-olive upper right, warm halo over the ledge) baked into a
    single untiled texture."""
    return [X.Transform(translation=(0, 0.70, WALL_Z), children=[X.Shape(
        geometry=X.Box(size=(2.8, 2.0, 0.05)),
        appearance=X.Appearance(material=X.PhysicalMaterial(
            baseColor=(1, 1, 1), roughness=0.55, metallic=0.0,
            baseTexture=X.ImageTexture(DEF="BT_WALL", url=[T["wall"]]),
            normalTexture=X.ImageTexture(DEF="NT_PLASTER", url=[T["plaster_n"]]))))])]


def fictive_frame(T):
    """Maroon border + teal fillet + pale inner line, built as a proscenium in
    FRONT of the ledge: it is what turns the arrangement into a picture, and
    it genuinely crops the scene (pomegranate debris left, ledge face below)."""
    mm = tex_app("maroon", T["maroon"], rough=0.9, tile=(3.0, 0.5))
    kids = []
    # maroon bands (opening x +-0.72, y 0.03..0.97; fresco sides are
    # NARROWER than top/bottom -- research 1.8)
    kids.append(box((0, 1.015, FRAME_Z), (1.70, 0.09, 0.02), mm))
    kids.append(box((0, -0.015, FRAME_Z), (1.70, 0.09, 0.02),
                    tex_app("maroon", T["maroon"], rough=0.9, tile=(3.0, 0.5))))
    kids.append(box((-0.748, 0.50, FRAME_Z), (0.056, 1.12, 0.02), mm))
    kids.append(box((0.748, 0.50, FRAME_Z), (0.056, 1.12, 0.02), mm))
    # teal fillet (muted grey-teal, not paint-fresh)
    fil = matp((0.28, 0.42, 0.44), rough=0.85)
    kids.append(box((0, 0.980, FRAME_Z + 0.004), (1.48, 0.020, 0.014), fil))
    kids.append(box((0, 0.020, FRAME_Z + 0.004), (1.48, 0.020, 0.014), fil))
    kids.append(box((-0.730, 0.50, FRAME_Z + 0.004), (0.020, 0.98, 0.014), fil))
    kids.append(box((0.730, 0.50, FRAME_Z + 0.004), (0.020, 0.98, 0.014), fil))
    # thin pale inner line
    pl = matp(PALE_LINE, rough=0.8)
    kids.append(box((0, 0.966, FRAME_Z + 0.007), (1.44, 0.007, 0.010), pl))
    kids.append(box((0, 0.034, FRAME_Z + 0.007), (1.44, 0.007, 0.010), pl))
    kids.append(box((-0.717, 0.50, FRAME_Z + 0.007), (0.007, 0.94, 0.010), pl))
    kids.append(box((0.717, 0.50, FRAME_Z + 0.007), (0.007, 0.94, 0.010), pl))
    # weathered frieze plaster beyond the border (the panel is a window onto
    # a longer shelf; the frieze visibly continues). z staggered per slab --
    # coplanar corners z-fought into checkering in a1.
    sr = tex_app("surround", T["surround"], rough=0.95, tile=(4.0, 4.0))
    kids.append(box((-1.60, 0.50, FRAME_Z - 0.018), (1.66, 3.2, 0.012), sr))
    kids.append(box((1.60, 0.50, FRAME_Z - 0.024), (1.66, 3.2, 0.012),
                    tex_app("surround", T["surround"], rough=0.95, tile=(4.0, 4.0))))
    kids.append(box((0, 1.645, FRAME_Z - 0.030), (4.8, 1.17, 0.012), sr))
    kids.append(box((0, -0.645, FRAME_Z - 0.036), (4.8, 1.17, 0.012), sr))
    return kids


# ---------------------------------------------------------------------------
# light -- one warm key from the viewer's left (az ~255deg, el ~40deg), IBL
# ambience (raw-injected), warm right fill so the shadow side stays open.
# The fresco is compressed mid-key: darkness that is dark but open.
# ---------------------------------------------------------------------------
def lights():
    key_pos = (-2.6, 2.1, 2.7)
    key_aim = (0.15, 0.35, -0.15)
    return [
        X.SpotLight(DEF="KEY", location=key_pos,
                    direction=_norm(tuple(a - p for a, p in zip(key_aim, key_pos))),
                    color=(1.0, 0.95, 0.86), intensity=20.5,
                    beamWidth=0.55, cutOffAngle=1.2,
                    radius=40.0, attenuation=(1, 0.12, 0.02), global_=True),
        X.PointLight(DEF="FILL", location=(1.8, 0.75, 2.1), color=(1.0, 0.85, 0.68),
                     intensity=0.42, attenuation=(1, 0.35, 0.10), radius=20.0,
                     global_=True),
        X.PointLight(DEF="BOUNCE", location=(0.0, 0.05, 1.1), color=(1.0, 0.82, 0.60),
                     intensity=0.25, attenuation=(1, 0.5, 0.2), radius=10.0,
                     global_=True),
    ]


# ---------------------------------------------------------------------------
# provenance -- the honest label, in the scene itself
# ---------------------------------------------------------------------------
def provenance_nodes():
    return [
        X.MetadataSet(name="provenance", value=[
            X.MetadataString(name="provenance", value=["interpretive"]),
            X.MetadataString(name="sourceCitation", value=[
                "Unknown Pompeian painter (Fourth Style workshop), 'Still Life "
                "with Glass Bowl of Fruit and Vases' (xenia panel from the "
                "Praedia of Julia Felix, Pompeii II.4.3, tablinum 92, excavated "
                "6 July 1755), c. AD 62-79, fresco, 114 x 74 cm. Museo "
                "Archeologico Nazionale di Napoli (MANN), inv. 8611. "
                "Reproduction: Wikimedia Commons, "
                "File:Pompejanischer_Maler_um_70_001.jpg (Yorck Project)."]),
            X.MetadataString(name="catalogId", value=["MANN inv. 8611"]),
            X.MetadataString(name="publicDomain", value=["true"]),
            X.MetadataString(name="generationMethod", value=[
                "Machine-authored X3D 4.0 via x3d.py 4.0.65.3 (antiquity.py v"
                + VERSION + "). Composition set to the fresco's own measured "
                "construction (panel-fraction coordinate table); the glass "
                "rendered by the painter's four devices (alpha shell, darkened "
                "interior fruit, drawn rim ellipses, discrete specular dashes); "
                "fictive border built as a cropping proscenium; contact shadows "
                "baked as the fresco's short rightward tongues; plaster/stone/"
                "fruit textures procedurally generated (PIL) and embedded as "
                "data URIs; IBL ambience from an authored gradient cubemap. "
                "No source-image pixels reproduced."]),
        ]),
        X.WorldInfo(title="Xenia after MANN 8611 (interpretive)",
                    info=["EUPHEME still-life provenance capstone",
                          "antiquity.py v" + VERSION]),
    ]


# ---------------------------------------------------------------------------
# views -- ledge-height, frontal, long lens (the fresco's own vantage)
# ---------------------------------------------------------------------------
def canonical_views():
    return [
        ("hero", ((0.0, 0.42, 2.32), look_at((0.0, 0.42, 2.32), (0.0, 0.47, 0.0)),
                  "hero -- frontal at ledge height, the whole framed panel")),
        ("three_q", ((-0.85, 0.62, 1.72),
                     look_at((-0.85, 0.62, 1.72), (0.05, 0.40, -0.10)),
                     "three-quarter from the key side, through the proscenium")),
        ("raking", ((-1.22, 0.40, 0.86),
                    look_at((-1.22, 0.40, 0.86), (0.28, 0.34, -0.12)),
                    "raking along the two ledges")),
    ]

VIEWS = canonical_views()


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------
def build_scene(view, T):
    global _DEF_SEEN
    _DEF_SEEN = set()
    children = []
    children += provenance_nodes()
    children.append(X.NavigationInfo(headlight=False, type=["EXAMINE", "ANY"]))
    children.append(X.Background(skyColor=[SKY]))
    if view is not None:
        pos, ori, _desc = view
        # description deliberately empty: X_ITE burns a described bound
        # viewpoint into headless captures as a UI toast (FAILURE_MODES A8)
        children.append(X.Viewpoint(position=pos, orientation=ori,
                                    fieldOfView=0.60, description=""))
    else:
        for _label, (pos, ori, desc) in [(l, v) for l, v in canonical_views()]:
            children.append(X.Viewpoint(position=pos, orientation=ori,
                                        fieldOfView=0.60, description=desc))
    children += lights()
    children += wall(T)
    children += ledges(T)
    children += fictive_frame(T)
    # contact tongues (before the objects is fine -- they are transparent
    # overlays on opaque stone, and everything opaque depth-tests correctly)
    children += contact(px(0.30), -0.02, 0.135, LEDGE_TOP, strength=0.50, stretch=2.6)
    children += contact(px(0.30) + 0.22, -0.04, 0.10, LEDGE_TOP, strength=0.28,
                        stretch=2.2)                      # the bowl's long smear
    children += contact(px(0.145), 0.08, 0.088, LEDGE_TOP, strength=0.5)
    children += contact(px(0.525), 0.10, 0.070, LEDGE_TOP, strength=0.5)
    children += contact(0.105, -0.055, 0.085, LEDGE_TOP, strength=0.55, stretch=2.0)
    children += contact(px(0.83), -0.17, 0.135, SHELF_TOP, strength=0.55)
    children += contact(px(0.735), -0.06, 0.090, SHELF_TOP, strength=0.40)
    # the objects, back-to-front-ish; the alpha glass bowl group goes LAST
    children.append(amphora(T))
    children += olla(T)
    children += pomegranate(T)
    children += quince(T)
    children.append(glass_bowl(T))
    return X.X3D(
        profile="Full", version="4.0",
        head=X.head(children=[
            X.component(name="Lighting", level=4),
            X.component(name="Shape", level=4),
            X.component(name="CubeMapTexturing", level=3),
            X.meta(name="title", content="antiquity.x3d"),
            X.meta(name="description",
                   content="Interpretive xenia still life after MANN inv. 8611"),
            X.meta(name="generator",
                   content="antiquity.py v" + VERSION + " + x3d.py 4.0.65.3"),
            X.meta(name="rights", content="public domain source; scene CC0"),
        ]),
        Scene=X.Scene(children=children))


# ---------------------------------------------------------------------------
# serializer repair + raw feature injection -- every patch ASSERTED
# ---------------------------------------------------------------------------
def _ibl_xml(C):
    faces = "\n".join(
        f"      <ImageTexture containerField='{k}Texture' url='\"{C[k]}\"'/>"
        for k in ("front", "back", "left", "right", "top", "bottom"))
    return ("  <EnvironmentLight global='true' color='1 0.97 0.92' intensity='0.62'>\n"
            "    <ComposedCubeMapTexture containerField='specularTexture'>\n"
            + faces + "\n"
            "    </ComposedCubeMapTexture>\n"
            "  </EnvironmentLight>\n")

SHEEN = {  # dusty bloom on grapes and dried prunes -- verified extension
    "M_GRAPE": ("0.60 0.50 0.40", "0.55"),
    "M_PRUNE": ("0.52 0.44 0.36", "0.60"),
}

def _fix_xml(xml, C):
    # 1. the X_ITE component line x3d.py refuses to emit (glTF extensions)
    assert "<head>" in xml
    xml = xml.replace("<head>", "<head>\n    <component name='X_ITE' level='1'/>", 1)
    assert "<component name='X_ITE' level='1'/>" in xml
    # 2. MetadataSet members belong in the value field
    want = xml.count("<MetadataString ")
    xml = xml.replace("<MetadataString ", "<MetadataString containerField='value' ")
    got = xml.count("containerField='value'")
    assert want == 5 and got == want, (want, got)
    # 3. PhysicalMaterial texture slots: DEF/USE prefix -> containerField
    def _slot(m):
        kind, name = m.group(1), m.group(2)
        slot = "normalTexture" if name.startswith("NT_") else "baseTexture"
        return f"<ImageTexture {kind}='{name}' containerField='{slot}'"
    n_tex = xml.count("<ImageTexture ")
    xml, n_sub = re.subn(r"<ImageTexture (DEF|USE)='([A-Za-z0-9_]+)'", _slot, xml)
    assert n_sub == n_tex and n_tex > 0, (n_sub, n_tex)
    # 4. Sheen extension into the DEF'd materials (raw: x3d.py has no class)
    for d, (sc, sr) in SHEEN.items():
        xml, n = re.subn(
            rf"(<PhysicalMaterial DEF='{d}'[^>]*?)/>",
            rf"\1><SheenMaterialExtension containerField='extensions' "
            rf"sheenColor='{sc}' sheenRoughness='{sr}'/></PhysicalMaterial>",
            xml, count=1)
        assert n == 1, (d, "sheen injection failed -- material not found/self-closed")
    # 5. the IBL block, raw (EnvironmentLight slot + cubemap faces both lose
    #    containerField under the serializer, faces get alphabetized)
    assert "<Scene>" in xml
    xml = xml.replace("<Scene>", "<Scene>\n" + _ibl_xml(C), 1)
    for k in ("front", "back", "left", "right", "top", "bottom"):
        assert xml.count(f"containerField='{k}Texture'") == 1, k
    assert xml.count("containerField='specularTexture'") == 1
    assert "global='true'" in xml
    return xml


_CACHE = {}

def scene_xml(view=None):
    if "T" not in _CACHE:
        _CACHE["T"] = make_textures()
        _CACHE["C"] = make_cubemap()
    model = build_scene(view, _CACHE["T"])
    return _fix_xml(model.XML(), _CACHE["C"])


def builder(vp):
    """lookdev entry point: vp = (pos, orientation, desc) -> X3D XML string."""
    return scene_xml(view=vp)

scene_builder = builder   # parity with pronk's entry-point name


def main():
    out = os.path.join(HERE, "antiquity.x3d")
    xml = scene_xml(view=None)
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"antiquity.py v{VERSION} wrote {out} ({len(xml)} bytes)")


if __name__ == "__main__":
    main()
