#!/usr/bin/env python3
"""
Photoreal bull moose, munching grass -- built procedurally with x3d.py.

Pipeline role
-------------
This is the *modelling + rig + lookdev + animation* stage of the
mflux -> X3D pipeline.  mflux supplies photoreal reference/lookdev and (in a
separate pass) restyles a rendered frame into a photoreal still; this script
produces the interactive, rigged, PBR X3D scene.

Design
------
  * geometry  : pure-Python primitives (ellipsoid / tapered tube / palmate
                antler / cloven hoof) emitted as IndexedFaceSet.  No ML mesh.
  * rig       : a quadruped HAnimHumanoid in the *spirit* of HAnim LOA5 --
                deep, anatomically-named articulation (spine, cervical chain,
                skull + temporomandibular jaw, ears, antlers, tail, four legs
                of five joints each).  HAnim is humanoid by spec, so the joint
                NAMES are moose anatomy; the structure/discipline is LOA5's.
                Segmented (rigid-per-segment) skinning -- adequate to animate
                the graze; smooth skinCoord weights are a later upgrade.
  * lookdev   : metallic-roughness PhysicalMaterial per part; image-based-ish
                lighting via EnvironmentLight + key/fill DirectionalLights.
  * animation : TimeSensor -> OrientationInterpolators graze loop: head dips
                to the grass, jaw chews, head lifts, idle-chews, repeat.

Outputs: moose.x3d  +  moose_x3dom.html (X_ITE viewer, real HAnim).
"""
import math
import os
import re
import subprocess

from x3d import x3d as X

# ---------------------------------------------------------------------------
# 0. small vector helpers (pure python -- no numpy dependency)
# ---------------------------------------------------------------------------
def sub(a, b):   return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
def add(a, b):   return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]
def mul(a, s):   return [a[0]*s, a[1]*s, a[2]*s]
def dot(a, b):   return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def length(a):   return math.sqrt(dot(a, a))
def norm(a):
    l = length(a)
    return [a[0]/l, a[1]/l, a[2]/l] if l > 1e-9 else [0.0, 0.0, 0.0]

def look_at(pos, target):
    """Viewpoint orientation rotating default view dir (0,0,-1) onto pos->target."""
    f = norm(sub(target, pos))
    d = [0, 0, -1]
    ax = cross(d, f)
    s = length(ax)
    c = dot(d, f)
    if s < 1e-6:
        return [0, 1, 0, 0.0] if c > 0 else [0, 1, 0, math.pi]
    ax = norm(ax)
    return [ax[0], ax[1], ax[2], math.atan2(s, c)]

# ---------------------------------------------------------------------------
# 1. materials (metallic-roughness PBR)
# ---------------------------------------------------------------------------
MATS = {
    "fur_body":  dict(baseColor=[0.17, 0.11, 0.065], roughness=0.93, metallic=0.0),
    "fur_dark":  dict(baseColor=[0.09, 0.06, 0.04],  roughness=0.9,  metallic=0.0),
    "fur_legs":  dict(baseColor=[0.30, 0.24, 0.16],  roughness=0.85, metallic=0.0),
    "muzzle":    dict(baseColor=[0.05, 0.04, 0.04],  roughness=0.45, metallic=0.0),
    "antler":    dict(baseColor=[0.52, 0.43, 0.30],  roughness=0.72, metallic=0.0),
    "hoof":      dict(baseColor=[0.04, 0.035, 0.045], roughness=0.35, metallic=0.0),
    "eye":       dict(baseColor=[0.015, 0.01, 0.01], roughness=0.12, metallic=0.0),
    "grass":     dict(baseColor=[0.16, 0.34, 0.09],  roughness=0.95, metallic=0.0),
    "grass2":    dict(baseColor=[0.22, 0.42, 0.12],  roughness=0.95, metallic=0.0),
    "ground":    dict(baseColor=[0.19, 0.15, 0.10],  roughness=1.0,  metallic=0.0),
    # --- lake scene ---
    "water":     dict(baseColor=[0.10, 0.26, 0.30],  roughness=0.08, metallic=0.0, transparency=0.55),
    "pondbottom":dict(baseColor=[0.14, 0.16, 0.11],  roughness=1.0,  metallic=0.0),
    "lilypad":   dict(baseColor=[0.13, 0.32, 0.12],  roughness=0.5,  metallic=0.0),
    "lilypad2":  dict(baseColor=[0.20, 0.40, 0.16],  roughness=0.5,  metallic=0.0),
    "lilyflower":dict(baseColor=[0.92, 0.85, 0.90],  roughness=0.5,  metallic=0.0),
    "lilycore":  dict(baseColor=[0.95, 0.80, 0.25],  roughness=0.5,  metallic=0.0),
    "lilybulb":  dict(baseColor=[0.55, 0.48, 0.30],  roughness=0.8,  metallic=0.0),
    "stem":      dict(baseColor=[0.18, 0.30, 0.14],  roughness=0.8,  metallic=0.0),
    "ripple":    dict(baseColor=[0.80, 0.88, 0.90],  roughness=0.1,  metallic=0.0, transparency=0.7),
}

# Fur materials get the tiling PBR fur maps (cheap real-time detail).
FUR = {"fur_body", "fur_legs", "fur_dark"}
TEXDIR = "assets/moose_textures"

def _imgtex(name):
    return X.ImageTexture(url=[f"{TEXDIR}/{name}"], repeatS=True, repeatT=True)

def appearance(mat, textured=False):
    m = MATS[mat]
    pm = X.PhysicalMaterial(baseColor=m["baseColor"], metallic=m["metallic"],
                            roughness=m["roughness"])
    if "transparency" in m:
        pm.transparency = m["transparency"]
    if textured:
        pm.baseTexture = _imgtex("fur_albedo.png")
        pm.normalTexture = _imgtex("fur_normal.png")
        pm.metallicRoughnessTexture = _imgtex("fur_mr.png")
    return X.Appearance(material=pm)

def shell_appearance(level):
    """Shell-fur layer: RGBA strand cutout drives the color + alpha (transparency)."""
    pm = X.PhysicalMaterial(baseColor=[1, 1, 1], metallic=0.0, roughness=0.95)
    pm.baseTexture = X.ImageTexture(url=[f"{TEXDIR}/fur_shell_{level}.png"],
                                    repeatS=True, repeatT=True)
    return X.Appearance(material=pm)

def shape(verts, faces, mat, uvs=None, tile=4.0):
    """IndexedFaceSet Shape; fur materials with uvs get tiling fur PBR maps."""
    ci = []
    for f in faces:
        ci.extend(f + [-1])
    furred = uvs is not None and mat in FUR
    ifs = X.IndexedFaceSet(
        coord=X.Coordinate(point=[list(v) for v in verts]),
        coordIndex=ci, creaseAngle=2.2, solid=False)
    if furred:
        ifs.texCoord = X.TextureCoordinate(point=[[u * tile, v * tile] for u, v in uvs])
        ifs.texCoordIndex = ci
    return X.Shape(appearance=appearance(mat, textured=furred), geometry=ifs)

# ---------------------------------------------------------------------------
# 2. geometry primitives  ->  (verts, faces)
# ---------------------------------------------------------------------------
def ellipsoid(center, radii, nu=18, nv=12, ytaper=1.0):
    cx, cy, cz = center
    rx, ry, rz = radii
    verts, faces, uvs = [], [], []
    for iv in range(nv + 1):
        th = math.pi * iv / nv
        for iu in range(nu):
            ph = 2 * math.pi * iu / nu
            x = rx * math.sin(th) * math.cos(ph)
            y = ry * math.cos(th)
            z = rz * math.sin(th) * math.sin(ph)
            # subtle pear taper (belly fuller than back)
            t = (math.cos(th) + 1) * 0.5
            sc = 1.0 + (ytaper - 1.0) * t
            verts.append([cx + x * sc, cy + y, cz + z * sc])
            uvs.append([iu / nu, iv / nv])
    for iv in range(nv):
        for iu in range(nu):
            a = iv * nu + iu
            b = iv * nu + (iu + 1) % nu
            c = (iv + 1) * nu + (iu + 1) % nu
            d = (iv + 1) * nu + iu
            faces.append([a, b, c, d])
    return verts, faces, uvs

def _frame(direction):
    d = norm(direction)
    up = [0, 1, 0] if abs(d[1]) < 0.95 else [1, 0, 0]
    s = norm(cross(up, d))
    u = cross(d, s)
    return s, u, d

def tube(p0, p1, r0, r1, n=14, bulge=1.0):
    """Tapered tube from p0(radius r0) to p1(radius r1). bulge fattens the middle."""
    s, u, _ = _frame(sub(p1, p0))
    verts, faces, uvs = [], [], []
    rings = [(0.0, r0), (0.5, (r0 + r1) * 0.5 * bulge), (1.0, r1)]
    for t, r in rings:
        c = add(p0, mul(sub(p1, p0), t))
        for iu in range(n):
            a = 2 * math.pi * iu / n
            off = add(mul(s, r * math.cos(a)), mul(u, r * math.sin(a)))
            verts.append(add(c, off))
            uvs.append([iu / n, t])
    for ri in range(2):
        for iu in range(n):
            a = ri * n + iu
            b = ri * n + (iu + 1) % n
            c = (ri + 1) * n + (iu + 1) % n
            d = (ri + 1) * n + iu
            faces.append([a, b, c, d])
    return verts, faces, uvs

def palmate_antler(base, side):
    """Broad bull-moose palm: a wide cupped fan spread laterally (out to the
       side) and slightly up/back, roughly horizontal, with tines fanning along
       the front + distal rim.  side=+1 left."""
    out = norm([side * 1.0, 0.30, 0.05])     # mostly lateral, a little up/back
    widthax = norm([0.0, 0.10, 1.0])         # front<->back palm span (~horizontal)
    upn = norm(cross(out, widthax))          # palm faces up
    if upn[1] < 0:
        upn = mul(upn, -1)
    L = 0.66
    nu, nv = 6, 6
    thick = 0.024
    verts, faces = [], []

    def W(t):
        return 0.20 + 0.66 * t               # broad rounded fan

    def grid(sign):
        idx = []
        for i in range(nu + 1):
            t = i / nu
            w = W(t)
            row = []
            for j in range(nv + 1):
                s = j / nv - 0.5
                cup = (abs(s * 2)) ** 2 * 0.05   # cup the palm upward at edges
                p = add(add(add(base, mul(out, L * t)),
                            mul(widthax, s * w * 2)),
                        mul(upn, sign * thick + cup))
                row.append(len(verts))
                verts.append(p)
            idx.append(row)
        return idx

    top, bot = grid(+1), grid(-1)
    for i in range(nu):
        for j in range(nv):
            faces.append([top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j]])
            faces.append([bot[i][j], bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1]])
    for j in range(nv):                          # distal rim
        faces.append([top[nu][j], bot[nu][j], bot[nu][j + 1], top[nu][j + 1]])
    for i in range(nu):                          # side rims
        faces.append([top[i][0], bot[i][0], bot[i + 1][0], top[i + 1][0]])
        faces.append([top[i][nv], top[i + 1][nv], bot[i + 1][nv], bot[i][nv]])
    # tines fanning out+up off the distal rim and the front edge
    tine_pts = [(nu, j) for j in range(nv + 1)] + [(i, 0) for i in range(2, nu)]
    for (i, j) in tine_pts:
        root = verts[top[i][j]]
        s = j / nv - 0.5
        dirn = norm(add(add(mul(out, 0.7), mul(upn, 0.85)), mul(widthax, s * 0.6)))
        tip = add(root, mul(dirn, 0.17))
        tv, tf, _ = tube(root, tip, 0.028, 0.006, n=5)
        off = len(verts)
        verts.extend(tv)
        faces.extend([[k + off for k in fc] for fc in tf])
    return verts, faces

def cloven_hoof(center):
    """Two small dark hoof halves."""
    verts, faces = [], []
    for sx in (-1, 1):
        c = [center[0] + sx * 0.035, center[1], center[2] - 0.02]
        v, f, _ = tube([c[0], c[1] + 0.12, c[2]], [c[0], c[1], c[2] + 0.06],
                    0.055, 0.05, n=8, bulge=1.1)
        off = len(verts)
        verts.extend(v)
        faces.extend([[i + off for i in fc] for fc in f])
    return verts, faces

# ---------------------------------------------------------------------------
# 3. rig -- quadruped joint hierarchy (LOA5-spirit), centers in metres
#    moose faces -Z (front), left = +X, up = +Y, hooves at y=0
# ---------------------------------------------------------------------------
# name: (parent, center)
JOINTS = {
    "moose_root":   (None,           [0.00, 1.55,  0.60]),   # pelvis / sacrum
    "spine_lumbar": ("moose_root",   [0.00, 1.62,  0.18]),
    "spine_thorax": ("spine_lumbar", [0.00, 1.72, -0.28]),   # withers / hump
    "neck_c1":      ("spine_thorax", [0.00, 1.74, -0.62]),
    "neck_c2":      ("neck_c1",      [0.00, 1.86, -0.96]),
    "neck_c3":      ("neck_c2",      [0.00, 2.00, -1.26]),
    "skull":        ("neck_c3",      [0.00, 2.05, -1.50]),
    "mandible":     ("skull",        [0.00, 1.95, -1.62]),
    "l_ear":        ("skull",        [0.13, 2.16, -1.46]),
    "r_ear":        ("skull",        [-0.13, 2.16, -1.46]),
    "l_antler":     ("skull",        [0.13, 2.21, -1.46]),
    "r_antler":     ("skull",        [-0.13, 2.21, -1.46]),
    "tail_1":       ("moose_root",   [0.00, 1.55,  0.82]),
    "tail_2":       ("tail_1",       [0.00, 1.42,  0.98]),
    # front left leg
    "l_shoulder":   ("spine_thorax", [0.32, 1.62, -0.30]),
    "l_f_elbow":    ("l_shoulder",   [0.34, 1.14, -0.25]),
    "l_f_knee":     ("l_f_elbow",    [0.35, 0.62, -0.30]),
    "l_f_fetlock":  ("l_f_knee",     [0.35, 0.24, -0.28]),
    "l_f_hoof":     ("l_f_fetlock",  [0.35, 0.02, -0.26]),
    # front right leg
    "r_shoulder":   ("spine_thorax", [-0.32, 1.62, -0.30]),
    "r_f_elbow":    ("r_shoulder",   [-0.34, 1.14, -0.25]),
    "r_f_knee":     ("r_f_elbow",    [-0.35, 0.62, -0.30]),
    "r_f_fetlock":  ("r_f_knee",     [-0.35, 0.24, -0.28]),
    "r_f_hoof":     ("r_f_fetlock",  [-0.35, 0.02, -0.26]),
    # hind left leg
    "l_hip":        ("moose_root",   [0.30, 1.55,  0.55]),
    "l_h_stifle":   ("l_hip",        [0.33, 1.05,  0.45]),
    "l_h_hock":     ("l_h_stifle",   [0.35, 0.60,  0.66]),
    "l_h_fetlock":  ("l_h_hock",     [0.35, 0.24,  0.58]),
    "l_h_hoof":     ("l_h_fetlock",  [0.35, 0.02,  0.56]),
    # hind right leg
    "r_hip":        ("moose_root",   [-0.30, 1.55,  0.55]),
    "r_h_stifle":   ("r_hip",        [-0.33, 1.05,  0.45]),
    "r_h_hock":     ("r_h_stifle",   [-0.35, 0.60,  0.66]),
    "r_h_fetlock":  ("r_h_hock",     [-0.35, 0.24,  0.58]),
    "r_h_hoof":     ("r_h_fetlock",  [-0.35, 0.02,  0.56]),
}
CHILDREN = {n: [] for n in JOINTS}
for n, (p, _) in JOINTS.items():
    if p:
        CHILDREN[p].append(n)
C = {n: c for n, (p, c) in JOINTS.items()}

# ---------------------------------------------------------------------------
# 3b. continuous TRUNK SKIN -- one swept mesh (snout->head->neck->torso->rump)
#     bound to the spine joints via skinCoordWeight, so it bends *smoothly*
#     (no segment seams) when the neck/body articulates. This is the HAnim
#     skin-binding upgrade over rigid-per-segment geometry.
# ---------------------------------------------------------------------------
# station: (center, rx, ry, hump)   front -> back along the spine centreline
TRUNK_STATIONS = [
    ([0.0, 1.94, -1.99], 0.10,  0.10,  0.00),   # snout tip
    ([0.0, 1.99, -1.80], 0.135, 0.125, 0.00),   # snout
    ([0.0, 2.04, -1.62], 0.16,  0.18,  0.00),   # head front
    ([0.0, 2.06, -1.45], 0.185, 0.205, 0.00),   # head / brow
    ([0.0, 2.00, -1.26], 0.20,  0.20,  0.00),   # neck c3
    ([0.0, 1.86, -0.96], 0.25,  0.25,  0.02),   # neck c2 (throat)
    ([0.0, 1.74, -0.62], 0.31,  0.31,  0.05),   # neck c1
    ([0.0, 1.73, -0.32], 0.40,  0.44,  0.22),   # withers / shoulder hump
    ([0.0, 1.56, -0.05], 0.45,  0.50,  0.06),   # chest
    ([0.0, 1.48,  0.22], 0.47,  0.52,  0.00),   # barrel
    ([0.0, 1.49,  0.48], 0.45,  0.49,  0.00),   # flank
    ([0.0, 1.53,  0.70], 0.36,  0.39,  0.00),   # hindquarter
    ([0.0, 1.50,  0.86], 0.20,  0.22,  0.00),   # rump
]
SPINE_CHAIN = ["skull", "neck_c3", "neck_c2", "neck_c1",
               "spine_thorax", "spine_lumbar", "moose_root"]

def _chain_weights(p, chain=None):
    """Project p onto a joint polyline -> blended skin weights {joint: w}."""
    chain = chain or SPINE_CHAIN
    centers = [C[j] for j in chain]
    best = (1e18, 0, 0.0)
    for i in range(len(centers) - 1):
        a, b = centers[i], centers[i + 1]
        ab = sub(b, a)
        l2 = dot(ab, ab)
        t = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, dot(sub(p, a), ab) / l2))
        d = length(sub(p, add(a, mul(ab, t))))
        if d < best[0]:
            best = (d, i, t)
    _, i, t = best
    w = {}
    if t < 0.999:
        w[chain[i]] = w.get(chain[i], 0.0) + (1 - t)
    if t > 0.001:
        w[chain[i + 1]] = w.get(chain[i + 1], 0.0) + t
    return w

# leg joint chains + per-joint ring radius (legs join the skin as continuous,
# skinned tubes -- the top ring buries inside the trunk, hiding the junction).
LEG_CHAINS = {
    "fl": ["l_shoulder", "l_f_elbow", "l_f_knee", "l_f_fetlock", "l_f_hoof"],
    "fr": ["r_shoulder", "r_f_elbow", "r_f_knee", "r_f_fetlock", "r_f_hoof"],
    "hl": ["l_hip", "l_h_stifle", "l_h_hock", "l_h_fetlock", "l_h_hoof"],
    "hr": ["r_hip", "r_h_stifle", "r_h_hock", "r_h_fetlock", "r_h_hoof"],
}
LEG_RING_R = {
    "l_shoulder": 0.18, "l_f_elbow": 0.105, "l_f_knee": 0.072, "l_f_fetlock": 0.055, "l_f_hoof": 0.05,
    "r_shoulder": 0.18, "r_f_elbow": 0.105, "r_f_knee": 0.072, "r_f_fetlock": 0.055, "r_f_hoof": 0.05,
    "l_hip": 0.20, "l_h_stifle": 0.115, "l_h_hock": 0.078, "l_h_fetlock": 0.055, "l_h_hoof": 0.05,
    "r_hip": 0.20, "r_h_stifle": 0.115, "r_h_hock": 0.078, "r_h_fetlock": 0.055, "r_h_hoof": 0.05,
}

def _vertex_normals(verts, faces):
    """Smooth (area-weighted) per-vertex normals for the bind-pose skin."""
    nrm = [[0.0, 0.0, 0.0] for _ in verts]
    for f in faces:
        for t in range(1, len(f) - 1):       # fan-triangulate the (quad/tri) face
            a, b, c = f[0], f[t], f[t + 1]
            fn = cross(sub(verts[b], verts[a]), sub(verts[c], verts[a]))
            for vi in (a, b, c):
                nrm[vi] = add(nrm[vi], fn)
    return [norm(n) if length(n) > 1e-9 else [0, 1, 0] for n in nrm]

def build_skin(nseg=18, legn=10):
    """Continuous skin = trunk (snout->rump) + four legs, all sharing one
       skinCoord. Returns verts, trunk_faces, leg_faces, uvs, normals, skinw."""
    S = TRUNK_STATIONS
    verts, trunk_f, leg_f, uvs = [], [], [], []
    vert_w = []                      # per-vertex weight dict (parallel to verts)

    # ---- trunk: elliptical rings with a top hump, swept along the spine ----
    rings = []
    for k, (c, rx, ry, hump) in enumerate(S):
        cprev = S[max(0, k - 1)][0]
        cnext = S[min(len(S) - 1, k + 1)][0]
        tan = norm(sub(cnext, cprev))
        up = [0, 1, 0] if abs(tan[1]) < 0.92 else [0, 0, 1]
        sdir = norm(cross(up, tan))
        udir = norm(cross(tan, sdir))
        w = _chain_weights(c)
        ring = []
        for j in range(nseg):
            a = 2 * math.pi * j / nseg
            uo = ry * math.sin(a) + hump * max(0.0, math.sin(a))
            p = add(add(c, mul(sdir, rx * math.cos(a))), mul(udir, uo))
            ring.append(len(verts))
            verts.append(p)
            uvs.append([j / nseg * 4.0, k / (len(S) - 1) * 9.0])
            vert_w.append(w)
        rings.append(ring)
    for k in range(len(rings) - 1):
        for j in range(nseg):
            trunk_f.append([rings[k][j], rings[k][(j + 1) % nseg],
                            rings[k + 1][(j + 1) % nseg], rings[k + 1][j]])
    for end, ring, st in ((0, rings[0], S[0]), (1, rings[-1], S[-1])):
        cen = len(verts)
        verts.append(list(st[0]))
        uvs.append([0.5, 0.0 if end == 0 else 9.0])
        vert_w.append(_chain_weights(st[0]))
        for j in range(nseg):
            a, b = ring[j], ring[(j + 1) % nseg]
            trunk_f.append([cen, b, a] if end == 0 else [cen, a, b])

    # ---- legs: circular skinned tubes following each leg joint chain ----
    for chain in LEG_CHAINS.values():
        centers = [C[j] for j in chain]
        radii = [LEG_RING_R[j] for j in chain]
        sts = []
        K = 3                                # subdivisions per bone (smooth bend)
        for i in range(len(chain) - 1):
            for kk in range(K):
                t = kk / K
                sts.append((add(centers[i], mul(sub(centers[i + 1], centers[i]), t)),
                            radii[i] * (1 - t) + radii[i + 1] * t))
        sts.append((centers[-1], radii[-1]))
        lrings = []
        for si, (c, r) in enumerate(sts):
            cprev = sts[max(0, si - 1)][0]
            cnext = sts[min(len(sts) - 1, si + 1)][0]
            tan = norm(sub(cnext, cprev))
            up = [0, 0, 1] if abs(tan[1]) > 0.92 else [0, 1, 0]
            sdir = norm(cross(up, tan))
            udir = norm(cross(tan, sdir))
            w = _chain_weights(c, chain)
            ring = []
            for j in range(legn):
                a = 2 * math.pi * j / legn
                p = add(add(c, mul(sdir, r * math.cos(a))), mul(udir, r * math.sin(a)))
                ring.append(len(verts))
                verts.append(p)
                uvs.append([j / legn * 2.0, si / (len(sts) - 1) * 6.0])
                vert_w.append(w)
            lrings.append(ring)
        for k in range(len(lrings) - 1):
            for j in range(legn):
                leg_f.append([lrings[k][j], lrings[k][(j + 1) % legn],
                              lrings[k + 1][(j + 1) % legn], lrings[k + 1][j]])

    base_normals = _vertex_normals(verts, trunk_f + leg_f)

    # ---- shell fur: NSHELL offset copies along the normals, sharing skinCoord
    #      (so they deform with the body). Each layer renders an alpha-cutout
    #      strand texture; stacked, they give a real furry silhouette. ----
    n_base = len(verts)
    shell_src = trunk_f          # fur shells on the body only (legs = short hair)
    shells = []
    for s in range(1, NSHELL + 1):
        off = SHELL_GAP * s
        for i in range(n_base):
            verts.append(add(verts[i], mul(base_normals[i], off)))
            uvs.append([uvs[i][0] * FUR_TILE, uvs[i][1] * FUR_TILE])
            vert_w.append(vert_w[i])
        shells.append(([[idx + s * n_base for idx in f] for f in shell_src], s))

    skinw = {}
    for vi, w in enumerate(vert_w):
        for joint, wt in w.items():
            if wt <= 1e-4:
                continue
            skinw.setdefault(joint, ([], []))
            skinw[joint][0].append(vi)
            skinw[joint][1].append(round(wt, 4))
    return verts, trunk_f, leg_f, uvs, base_normals, skinw, shells

NSHELL = 4          # shell-fur layers
SHELL_GAP = 0.008   # metres between shells
FUR_TILE = 6.0      # extra uv tiling so strands are fine
SKIN_V, TRUNK_F, LEG_F, SKIN_UV, SKIN_N, SKINW, SHELLS = build_skin()

# ---------------------------------------------------------------------------
# 4. which geometry hangs on which segment (authored in rest-pose world coords)
# ---------------------------------------------------------------------------
LEG_RADII = {  # joint -> (radius at this joint, radius at child) for the limb tube
    "l_shoulder": (0.15, 0.10), "l_f_elbow": (0.10, 0.075), "l_f_knee": (0.072, 0.055),
    "l_f_fetlock": (0.055, 0.05),
    "r_shoulder": (0.15, 0.10), "r_f_elbow": (0.10, 0.075), "r_f_knee": (0.072, 0.055),
    "r_f_fetlock": (0.055, 0.05),
    "l_hip": (0.17, 0.11), "l_h_stifle": (0.11, 0.08), "l_h_hock": (0.078, 0.055),
    "l_h_fetlock": (0.055, 0.05),
    "r_hip": (0.17, 0.11), "r_h_stifle": (0.11, 0.08), "r_h_hock": (0.078, 0.055),
    "r_h_fetlock": (0.055, 0.05),
}

def seg_geom(name):
    """Return list of Shapes for the HAnimSegment owned by joint `name`."""
    g = []
    # NOTE: the trunk AND legs are now the continuous skinCoord skin (build_skin),
    # so no per-segment limb tubes here.
    # NOTE: the trunk (torso, hump, neck, head, snout) is now the continuous
    # skinCoord skin bound across the spine joints -- see build_trunk_skin().
    # Only rigid appendages remain as per-segment geometry below.
    if name == "neck_c2":       # dewlap / bell hanging under the throat
        v, f, uv = ellipsoid([0.0, 1.62, -1.02], [0.10, 0.20, 0.13], nu=12, nv=9, ytaper=0.5)
        g.append(shape(v, f, "fur_body", uv, tile=2))
    if name == "skull":
        # bulbous nose (rigid -- rides the skull joint, matches the skin's snout)
        v, f, uv = ellipsoid([0.0, 1.92, -2.0], [0.115, 0.12, 0.12], nu=14, nv=10)
        g.append(shape(v, f, "muzzle"))
        for sx in (1, -1):      # eyes
            v, f, uv = ellipsoid([sx * 0.13, 2.06, -1.66], [0.035, 0.04, 0.035], nu=10, nv=8)
            g.append(shape(v, f, "eye"))
    if name == "mandible":
        v, f, uv = tube([0.0, 1.93, -1.66], [0.0, 1.9, -1.96], 0.10, 0.085, n=12, bulge=1.05)
        g.append(shape(v, f, "fur_body", uv, tile=2))
    if name in ("l_ear", "r_ear"):
        sx = 1 if name == "l_ear" else -1
        v, f, uv = ellipsoid([sx * 0.13, 2.18, -1.46], [0.05, 0.11, 0.025], nu=10, nv=8)
        g.append(shape(v, f, "fur_legs", uv, tile=2))
    if name in ("l_antler", "r_antler"):
        v, f = palmate_antler(C[name], 1 if name == "l_antler" else -1)
        g.append(shape(v, f, "antler"))
    if name in ("tail_1", "tail_2"):
        child = "tail_2" if name == "tail_1" else None
        tgt = C[child] if child else [0.0, 1.35, 1.02]
        v, f, uv = tube(C[name], tgt, 0.06, 0.03, n=8)
        g.append(shape(v, f, "fur_dark", uv, tile=2))
    if name.endswith("hoof"):
        v, f = cloven_hoof(C[name])
        g.append(shape(v, f, "hoof"))
    return g

# Baked static pose (filled when MOOSE_POSE is set) -> freezes a known frame.
BAKE_ROT = {}     # joint -> [x,y,z,angle]
BAKE_TRANS = {}   # joint -> [x,y,z]

def build_joint(name):
    seg = X.HAnimSegment(DEF=f"seg_{name}", name=name, children=seg_geom(name))
    kids = [seg] + [build_joint(ch) for ch in CHILDREN[name]]
    j = X.HAnimJoint(DEF=f"J_{name}", name=name, center=list(C[name]), children=kids)
    if name in SKINW:                       # skin vertices this joint deforms
        j.skinCoordIndex = SKINW[name][0]
        j.skinCoordWeight = SKINW[name][1]
    if name in BAKE_ROT:
        j.rotation = BAKE_ROT[name]
    if name in BAKE_TRANS:
        j.translation = BAKE_TRANS[name]
    return j

# ---------------------------------------------------------------------------
# 5. grass + ground
# ---------------------------------------------------------------------------
def _lcg(seed):
    s = seed
    while True:
        s = (1103515245 * s + 12345) & 0x7fffffff
        yield s / 0x7fffffff

def grass_patch():
    """A flat ground plus a field of blades, densest where the moose grazes."""
    shapes = []
    gv, gf, _ = ellipsoid([0, -0.02, -0.3], [6.0, 0.02, 6.0], nu=28, nv=4)
    shapes.append(shape(gv, gf, "ground"))
    rnd = _lcg(20260614)
    verts, faces, verts2, faces2 = [], [], [], []
    graze = [0.0, 0.0, -2.05]    # ground point under the muzzle
    for i in range(220):
        r = next(rnd)
        # 60% clustered at the graze spot, 40% scattered
        if next(rnd) < 0.6:
            ang = next(rnd) * 2 * math.pi
            rad = next(rnd) ** 0.5 * 0.7
            bx = graze[0] + math.cos(ang) * rad
            bz = graze[2] + math.sin(ang) * rad
            h = 0.10 + next(rnd) * 0.14
        else:
            bx = (next(rnd) - 0.5) * 7.0
            bz = -0.3 + (next(rnd) - 0.5) * 7.0
            h = 0.12 + next(rnd) * 0.22
        w = 0.012 + next(rnd) * 0.01
        bend = (next(rnd) - 0.5) * 0.12
        # blade = 2 triangles tapering to a point, slight bend at top
        v0 = [bx - w, 0.0, bz]
        v1 = [bx + w, 0.0, bz]
        v2 = [bx + bend, h, bz + bend * 0.5]
        tgt_v, tgt_f = (verts, faces) if next(rnd) < 0.5 else (verts2, faces2)
        o = len(tgt_v)
        tgt_v.extend([v0, v1, v2])
        tgt_f.append([o, o + 1, o + 2])
    shapes.append(shape(verts, faces, "grass"))
    shapes.append(shape(verts2, faces2, "grass2"))
    return shapes

def disc(center, r, n=16, notch=True):
    """Flat horizontal disc (lily pad) in the XZ plane, optional V-notch."""
    cx, cy, cz = center
    verts = [[cx, cy, cz]]
    span = (2 * math.pi) if not notch else (2 * math.pi * (1 - 1 / n))
    a0 = 0.32 if notch else 0.0
    for i in range(n + 1):
        a = a0 + span * i / n
        verts.append([cx + r * math.cos(a), cy, cz + r * math.sin(a)])
    faces = [[0, i + 1, i + 2] for i in range(n)]
    return verts, faces

def lily_flower(center):
    """A little water-lily: ring of white petals + yellow core."""
    g = []
    cx, cy, cz = center
    pv, pf = [], []
    for k in range(7):
        a = 2 * math.pi * k / 7
        tip = [cx + 0.11 * math.cos(a), cy + 0.05, cz + 0.11 * math.sin(a)]
        l = [cx + 0.03 * math.cos(a - 0.4), cy, cz + 0.03 * math.sin(a - 0.4)]
        r = [cx + 0.03 * math.cos(a + 0.4), cy, cz + 0.03 * math.sin(a + 0.4)]
        o = len(pv); pv += [l, tip, r]; pf.append([o, o + 1, o + 2])
    g.append(shape(pv, pf, "lilyflower"))
    cv, cf, _ = ellipsoid([cx, cy + 0.02, cz], [0.035, 0.02, 0.035], nu=8, nv=5)
    g.append(shape(cv, cf, "lilycore"))
    return g

def lake_env():
    """Pond bottom + submerged lily bulbs/stems + translucent surface + pads.
       The moose stands on the bottom (y=0) and dives to the bulb bed."""
    shapes = []
    # murky pond bottom
    bv, bf, _ = ellipsoid([0, -0.05, -0.6], [7.0, 0.05, 7.0], nu=30, nv=4)
    shapes.append(shape(bv, bf, "pondbottom"))

    rnd = _lcg(515)
    bed = [0.0, 0.0, -2.0]               # the bulb bed the moose dives for
    # submerged rhizomes / bulbs on the bottom (the food) + a few scattered
    for i in range(10):
        clustered = next(rnd) < 0.7
        if clustered:
            ang = next(rnd) * 2 * math.pi; rad = next(rnd) ** 0.5 * 0.75
            bx, bz = bed[0] + math.cos(ang) * rad, bed[2] + math.sin(ang) * rad
        else:
            bx, bz = (next(rnd) - 0.5) * 6, -0.6 + (next(rnd) - 0.5) * 6
        rb = 0.10 + next(rnd) * 0.06
        v, f, uv = ellipsoid([bx, 0.06 + rb * 0.4, bz], [rb, rb * 0.7, rb * 1.3], nu=10, nv=7)
        shapes.append(shape(v, f, "lilybulb"))

    # lily pads floating on the surface, with stems down to the bottom
    pads = []
    for i in range(16):
        if next(rnd) < 0.45:
            ang = next(rnd) * 2 * math.pi; rad = next(rnd) ** 0.5 * 1.4
            px, pz = bed[0] + math.cos(ang) * rad, bed[2] + math.sin(ang) * rad
        else:
            px, pz = (next(rnd) - 0.5) * 7, -0.6 + (next(rnd) - 0.5) * 7
        pr = 0.28 + next(rnd) * 0.22
        pads.append((px, pz, pr))
        dv, df = disc([px, WATER_Y + 0.012, pz], pr, n=14)
        shapes.append(shape(dv, df, "lilypad" if next(rnd) < 0.5 else "lilypad2"))
        # a thin, slightly-leaning stem on only some pads (keep it subtle)
        if next(rnd) < 0.55:
            jit = (next(rnd) - 0.5) * 0.25
            sv, sf, _ = tube([px + jit, 0.05, pz + jit], [px, WATER_Y, pz], 0.008, 0.005, n=5)
            shapes.append(shape(sv, sf, "stem"))
    # a few flowers on the larger pads
    flowers = sorted(pads, key=lambda p: -p[2])[:4]
    for (px, pz, pr) in flowers:
        for s in lily_flower([px + pr * 0.2, WATER_Y + 0.02, pz]):
            shapes.append(s)

    # translucent, gently-undulating water surface (animated grid -- see below)
    shapes.append(water_surface())
    return shapes

WATER_N = 20            # surface grid resolution
WATER_S = 9.0           # half-extent

def _water_pts(phase):
    pts = []
    for iz in range(WATER_N + 1):
        for ix in range(WATER_N + 1):
            x = -WATER_S + 2 * WATER_S * ix / WATER_N
            z = -0.6 - WATER_S + 2 * WATER_S * iz / WATER_N
            h = (0.045 * math.sin(0.8 * x + phase * 2 * math.pi)
                 + 0.04 * math.sin(0.6 * z - phase * 2 * math.pi * 1.3)
                 + 0.03 * math.sin(0.5 * (x + z) + phase * 2 * math.pi * 0.7))
            pts.append([x, WATER_Y + h, z])
    return pts

def _water_faces():
    f = []
    for iz in range(WATER_N):
        for ix in range(WATER_N):
            a = iz * (WATER_N + 1) + ix
            f.append([a, a + 1, a + WATER_N + 2, a + WATER_N + 1])
    return f

def water_surface():
    ci = []
    for f in _water_faces():
        ci.extend(f + [-1])
    return X.Shape(appearance=appearance("water"),
                   geometry=X.IndexedFaceSet(
                       coord=X.Coordinate(DEF="WaterCoord", point=_water_pts(0.0)),
                       coordIndex=ci, creaseAngle=3.0, solid=False))

def water_anim():
    """CoordinateInterpolator that rolls the surface through wave phases."""
    K = 8
    keys = [k / K for k in range(K + 1)]
    kv = []                              # concat all phase point-sets (MFVec3f)
    for k in range(K + 1):
        kv.extend(_water_pts(k / K))
    return [
        X.TimeSensor(DEF="WaterClock", cycleInterval=5.0, loop=True),
        X.CoordinateInterpolator(DEF="water_int", key=keys, keyValue=kv),
        X.ROUTE(fromNode="WaterClock", fromField="fraction_changed",
                toNode="water_int", toField="set_fraction"),
        X.ROUTE(fromNode="water_int", fromField="value_changed",
                toNode="WaterCoord", toField="set_point"),
    ]

def ripple_group():
    """Flat expanding ring at the surface where the moose breaks the water."""
    cx, cz = 0.0, -1.5
    ri, ro, n = 0.5, 0.62, 28
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        verts.append([cx + ri * math.cos(a), 0.0, cz + ri * math.sin(a)])
        verts.append([cx + ro * math.cos(a), 0.0, cz + ro * math.sin(a)])
    for i in range(n):
        a, b = 2 * i, 2 * i + 1
        c, d = (2 * ((i + 1) % n)), (2 * ((i + 1) % n) + 1)
        faces.append([a, b, d, c])
    rg = X.Transform(DEF="Ripple", translation=[0, WATER_Y + 0.02, 0],
                     scale=[0.2, 1, 0.2], children=[shape(verts, faces, "ripple")])
    return rg

def bubble_group():
    """A rising bubble stream (the moose expels air to sink -- factual)."""
    sp = []
    rnd = _lcg(99)
    for i in range(7):
        bx = 0.1 + (next(rnd) - 0.5) * 0.3
        bz = -1.7 + (next(rnd) - 0.5) * 0.4
        by = 0.4 + next(rnd) * 1.4
        r = 0.025 + next(rnd) * 0.03
        v, f, _ = ellipsoid([bx, by, bz], [r, r, r], nu=8, nv=5)
        sp.append(shape(v, f, "water"))
    return X.Transform(DEF="Bubbles", children=sp)

# ---------------------------------------------------------------------------
# 6. animation -- meadow graze OR lake dive (MOOSE_SCENE selects)
# ---------------------------------------------------------------------------
SCENE = os.environ.get("MOOSE_SCENE", "meadow")   # "meadow" | "lake"
AX = (1, 0, 0)   # pitch axis
WATER_Y = 2.45   # lake surface height (moose stands on bottom y=0)

# --- easing curves (0..1 -> 0..1): the slow-in/slow-out principle ----------
def e_lin(t): return t
def e_io(t):  return t * t * (3 - 2 * t)               # smoothstep: ease in & out
def e_in(t):  return t * t * t                         # accelerate
def e_out(t): return 1 - (1 - t) ** 3                  # decelerate / settle
def e_back(t, k=1.9):                                  # overshoot, then settle
    u = t - 1.0
    return 1 + (k + 1) * u ** 3 + k * u ** 2

def _lerp(a, b, e):
    if isinstance(a, (list, tuple)):
        return [a[i] + (b[i] - a[i]) * e for i in range(len(a))]
    return a + (b - a) * e

def bake(kfs, spp=8):
    """kfs = [(time, value, ease_to_next)] -> dense keys/vals tracing the eased
       curve. Linear storage, but the *shape* carries the easing (so any X3D
       viewer reproduces slow-in/out, anticipation, overshoot)."""
    keys, vals = [], []
    for i in range(len(kfs) - 1):
        t0, v0, ef = kfs[i]
        t1, v1 = kfs[i + 1][0], kfs[i + 1][1]
        for s in range(spp):
            f = s / spp
            keys.append(round(t0 + (t1 - t0) * f, 4))
            vals.append(_lerp(v0, v1, ef(f)))
    keys.append(round(kfs[-1][0], 4)); vals.append(kfs[-1][1])
    return keys, vals

def hold_bob(keys, vals, t0, t1, amp, cycles):
    """Moving hold: add a small sine onto a baked channel within [t0,t1]."""
    return keys, [v + (amp * math.sin((k - t0) / (t1 - t0) * cycles * 2 * math.pi)
                       if t0 <= k <= t1 else 0.0) for k, v in zip(keys, vals)]

def chew(t0, t1, n, amp):
    """Eased jaw chews -- each open/close is a smoothstep, not a linear tri-wave."""
    kfs = [(0.0, 0.0, e_io)]
    for i in range(n):
        kfs.append((t0 + (t1 - t0) * i / n, 0.0, e_io))
        kfs.append((t0 + (t1 - t0) * (i + 0.5) / n, amp, e_io))
    kfs.append((t1, 0.0, e_io)); kfs.append((1.0, 0.0, e_lin))
    return bake(kfs, spp=4)

NECK = ["neck_c1", "neck_c2", "neck_c3", "skull"]

def neck_arc(amp_map, t_down, t_hold, t_up, t_settle, stagger=0.05, antic=0.12, bob=0.0):
    """Overlapping action: the bend propagates DOWN the cervical chain (each joint
       lags its parent) so the neck curls in an arc -- with anticipation (a small
       lift before the plunge), an overshoot on arrival, and a settle on the lift."""
    specs = []
    for i, j in enumerate(NECK):
        amp = amp_map[j]
        d = i * stagger
        keys, vals = bake([
            (0.0, 0.0, e_io),
            (t_down * 0.42 + d, -antic * amp, e_back),   # anticipation -> plunge (overshoot)
            (t_down + d, amp, e_io),                     # arrive
            (t_hold + d, amp, e_io),                     # hold at the bottom
            (t_up + d, 0.0, e_out),                      # lift back (decelerate to rest)
            (t_settle, 0.0, e_lin),
        ])
        if bob and j == "skull":                         # moving hold: gentle head bob
            keys, vals = hold_bob(keys, vals, t_down + d, t_hold + d, bob, 2)
        specs.append((j, keys, vals, AX))
    return specs

if SCENE == "meadow":
    CYCLE = 7.0                                          # a touch slower -> reads heavier
    NECK_PITCH = {"neck_c1": -0.30, "neck_c2": -0.45, "neck_c3": -0.50, "skull": -0.35}

    def rot_specs():
        specs = neck_arc(NECK_PITCH, t_down=0.28, t_hold=0.56, t_up=0.74, t_settle=0.96,
                         stagger=0.05, antic=0.12, bob=0.04)
        specs.append(("mandible", *chew(0.30, 0.58, 6, -0.32), AX))
        # secondary action: ear flick (snappy, overshoot) + tail sway (lagging arc)
        specs.append(("l_ear", *bake([(0, 0, e_io), (0.40, 0, e_io), (0.46, 0.5, e_back),
                                      (0.54, 0, e_out), (1.0, 0, e_lin)], spp=5), AX))
        specs.append(("tail_1", *bake([(0, 0, e_io), (0.32, 0.18, e_io), (0.58, -0.15, e_io),
                                       (0.80, 0.10, e_io), (1.0, 0, e_io)], spp=5), (0, 1, 0)))
        return specs

    BODY_KEY, BODY_KV = bake([                            # eased weight-shift down
        (0.0, [0, 0, 0], e_io), (0.30, [0, -0.035, -0.05], e_io),
        (0.56, [0, -0.035, -0.05], e_io), (0.78, [0, 0, 0], e_out), (1.0, [0, 0, 0], e_lin)])
else:  # lake dive
    CYCLE = 11.0
    NECK_PITCH = {"neck_c1": -0.30, "neck_c2": -0.46, "neck_c3": -0.50, "skull": -0.40}

    def rot_specs():
        specs = neck_arc(NECK_PITCH, t_down=0.30, t_hold=0.55, t_up=0.74, t_settle=0.96,
                         stagger=0.05, antic=0.14, bob=0.03)
        # whole-body dive tilt: anticipatory coil (head rises a touch) -> plunge
        # with overshoot -> hold head-down -> level out
        specs.append(("moose_root", *bake([
            (0.0, 0.0, e_io), (0.16, 0.06, e_back), (0.32, -0.72, e_io),
            (0.55, -0.72, e_io), (0.76, 0.0, e_out), (1.0, 0.0, e_lin)]), AX))
        specs.append(("mandible", *chew(0.32, 0.55, 5, -0.34), AX))
        specs.append(("l_ear", *bake([(0, 0, e_io), (0.82, 0, e_io), (0.88, 0.6, e_back),
                                      (0.95, 0, e_out), (1.0, 0, e_lin)], spp=5), AX))
        specs.append(("tail_1", *bake([(0, 0, e_io), (0.30, 0.15, e_io), (0.60, -0.15, e_io),
                                       (1.0, 0, e_io)], spp=5), (0, 1, 0)))
        return specs

    BODY_KEY, BODY_KV = bake([                            # anticipatory coil then sink
        (0.0, [0, 0, 0], e_io), (0.16, [0, 0.03, 0], e_io), (0.32, [0, -0.26, -0.12], e_io),
        (0.55, [0, -0.26, -0.12], e_io), (0.76, [0, 0, 0], e_out), (1.0, [0, 0, 0], e_lin)])

def _sample(key, vals, f):
    if f <= key[0]:
        return vals[0]
    if f >= key[-1]:
        return vals[-1]
    for i in range(len(key) - 1):
        if key[i] <= f <= key[i + 1]:
            span = key[i + 1] - key[i]
            t = (f - key[i]) / span if span > 1e-9 else 0.0
            if isinstance(vals[0], (list, tuple)):
                return [vals[i][k] + (vals[i + 1][k] - vals[i][k]) * t for k in range(len(vals[0]))]
            return vals[i] + (vals[i + 1] - vals[i]) * t
    return vals[-1]

POSE = os.environ.get("MOOSE_POSE")           # e.g. "0.45" freezes the graze
SPECS = rot_specs()

def anim_nodes():
    nodes, routes = [], []
    for joint, key, angles, axis in SPECS:
        d = f"{joint}_int"
        kv = [[axis[0], axis[1], axis[2], a] for a in angles]
        nodes.append(X.OrientationInterpolator(DEF=d, key=key, keyValue=kv))
        routes.append(X.ROUTE(fromNode="MunchClock", fromField="fraction_changed",
                              toNode=d, toField="set_fraction"))
        routes.append(X.ROUTE(fromNode=d, fromField="value_changed",
                              toNode=f"J_{joint}", toField="set_rotation"))
    nodes.append(X.PositionInterpolator(DEF="body_int", key=BODY_KEY, keyValue=BODY_KV))
    routes.append(X.ROUTE(fromNode="MunchClock", fromField="fraction_changed",
                          toNode="body_int", toField="set_fraction"))
    # translate the whole FIGURE (skin + skeleton) via the outer Transform -- the
    # root-joint translation would not carry the skinCoord skin (only rigid segs).
    routes.append(X.ROUTE(fromNode="body_int", fromField="value_changed",
                          toNode="MooseRoot", toField="set_translation"))
    return nodes, routes

# ---------------------------------------------------------------------------
# 7. assemble scene
# ---------------------------------------------------------------------------
FIG_TRANS = [0, 0, 0]                          # whole-figure offset (the body sink)
if POSE is not None:                           # freeze a known frame (no clock)
    f = float(POSE)
    for joint, key, angles, axis in SPECS:
        BAKE_ROT[joint] = [axis[0], axis[1], axis[2], _sample(key, angles, f)]
    FIG_TRANS = _sample(BODY_KEY, BODY_KV, f)
    anim_int, anim_routes = [], []
    print(f"[pose-freeze] baked frame f={f}")
else:
    anim_int, anim_routes = anim_nodes()

# continuous skin = trunk Shape (fur_body) + legs Shape (fur_legs), both sharing
# one skinCoord/skinNormal/texCoord. x3d.py serialises skinCoord/skinNormal BEFORE
# skin, so the DEF (data) lives in those fields and the skin Shapes use USE.
# containerField for skin/skinCoord/skinNormal is injected post-serialize.
def _idx(faces):
    ci = []
    for f in faces:
        ci.extend(f + [-1])
    return ci
# (skinNormal is intentionally omitted: x3d.py's Normal.vector is internally
#  inconsistent -- its constructor wants a flat list but its serialiser wants
#  triples -- so X_ITE recomputes smooth normals from the deformed skin via
#  creaseAngle instead. SKIN_N is still computed for any future exporter.)
_tci, _lci = _idx(TRUNK_F), _idx(LEG_F)
skin_coord = X.Coordinate(DEF="MooseSkinCoord", point=[list(v) for v in SKIN_V])
trunk_shape = X.Shape(
    DEF="MooseSkinShape", appearance=appearance("fur_body", textured=True),
    geometry=X.IndexedFaceSet(
        coord=X.Coordinate(USE="MooseSkinCoord"), coordIndex=_tci,
        texCoord=X.TextureCoordinate(DEF="MooseSkinTC", point=[list(uv) for uv in SKIN_UV]),
        texCoordIndex=_tci, creaseAngle=2.4, solid=False))
leg_shape = X.Shape(
    DEF="MooseLegShape", appearance=appearance("fur_legs", textured=True),
    geometry=X.IndexedFaceSet(
        coord=X.Coordinate(USE="MooseSkinCoord"), coordIndex=_lci,
        texCoord=X.TextureCoordinate(USE="MooseSkinTC"),
        texCoordIndex=_lci, creaseAngle=2.4, solid=False))
# shell-fur layers (share skinCoord + texCoord; alpha-cutout strands)
shell_shapes = []
for faces, lvl in SHELLS:
    sci = _idx(faces)
    shell_shapes.append(X.Shape(
        DEF=f"MooseShell{lvl}", appearance=shell_appearance(lvl),
        geometry=X.IndexedFaceSet(
            coord=X.Coordinate(USE="MooseSkinCoord"), coordIndex=sci,
            texCoord=X.TextureCoordinate(USE="MooseSkinTC"),
            texCoordIndex=sci, solid=False)))

# NOTE: x3d.py serialises the joints/segments USE-lists *before* skeleton, which
# would put USE before DEF (invalid, and X_ITE then fails to resolve the rig).
# skeleton alone is what X_ITE renders; omit the USE bookkeeping lists.
humanoid = X.HAnimHumanoid(
    DEF="MooseHumanoid", name="moose", version="2.0",
    info=['"authoringTool=generate_moose.py"', '"humanoidVersion=moose-LOA5-spirit"'],
    skeleton=[build_joint("moose_root")],
    skin=[trunk_shape, leg_shape] + shell_shapes, skinCoord=skin_coord)

# Named cameras; MOOSE_VIEW=<name> binds one first (X_ITE binds the first VP).
if SCENE == "meadow":
    VIEWS = [
        ("Hero",  [3.4, 2.0, -3.6],  [0, 1.4, -0.9],  0.78),
        ("Side",  [5.2, 1.7, -1.4],  [0, 1.4, -0.9],  0.78),
        ("Head",  [1.6, 2.1, -2.9],  [0, 1.7, -1.85], 0.78),
        ("Front", [0.0, 2.1, -4.4],  [0, 1.7, -1.4],  0.85),
        ("Top",   [2.2, 4.6, -3.0],  [0, 1.7, -1.0],  0.9),
    ]
else:
    VIEWS = [
        ("Hero",  [4.0, 2.9, -4.4],  [0, 1.3, -1.6],  0.82),
        ("Dive",  [4.4, 1.0, -2.2],  [0, 0.7, -1.9],  0.85),
        ("Above", [2.6, 5.8, -3.8],  [0, 0.9, -1.7],  0.9),
        ("Front", [0.0, 2.7, -5.4],  [0, 1.4, -1.7],  0.85),
    ]
_want = os.environ.get("MOOSE_VIEW")
if _want:
    VIEWS.sort(key=lambda v: 0 if v[0] == _want else 1)
viewpoints = [X.Viewpoint(DEF=n, position=p, orientation=look_at(p, t),
                          description=n, fieldOfView=fov) for n, p, t, fov in VIEWS]

if SCENE == "meadow":
    title = "Photoreal Moose Munching Grass (HAnim LOA5-spirit quadruped)"
    background = X.Background(
        skyAngle=[1.07, 1.3, 1.5707], groundAngle=[1.5707],
        skyColor=[[0.27, 0.42, 0.62], [0.55, 0.68, 0.82], [0.74, 0.82, 0.88], [0.82, 0.86, 0.88]],
        groundColor=[[0.18, 0.15, 0.10], [0.30, 0.27, 0.18]])
    env_nodes = [X.Group(children=grass_patch())]
    extra_nodes = []
else:
    title = "Moose Diving for Water-Lily Bulbs (HAnim LOA5-spirit quadruped)"
    background = X.Background(
        skyAngle=[1.2, 1.5707], groundAngle=[1.5707],
        skyColor=[[0.30, 0.45, 0.60], [0.62, 0.74, 0.82], [0.80, 0.86, 0.88]],
        groundColor=[[0.08, 0.16, 0.18], [0.10, 0.22, 0.24]])
    # bluish-green underwater murk that deepens with distance
    extra_nodes = [X.Fog(color=[0.10, 0.26, 0.30], visibilityRange=16,
                         fogType='LINEAR')]
    env_nodes = [X.Group(children=lake_env()), bubble_group(), ripple_group()]

# bubbles rise + a surface ripple expands as the moose plunges
bubble_anim = []
if SCENE == "lake" and POSE is None:
    bubble_anim = [
        X.PositionInterpolator(DEF="bubble_int", key=[0, 0.12, 0.5, 1.0],
                               keyValue=[[0, 0, 0], [0, 0, 0], [0, 2.1, 0], [0, 2.1, 0]]),
        X.ROUTE(fromNode="MunchClock", fromField="fraction_changed",
                toNode="bubble_int", toField="set_fraction"),
        X.ROUTE(fromNode="bubble_int", fromField="value_changed",
                toNode="Bubbles", toField="set_translation"),
        X.PositionInterpolator(DEF="ripple_int", key=[0, 0.08, 0.4, 0.5, 1.0],
                               keyValue=[[0.2, 1, 0.2], [0.3, 1, 0.3], [3.2, 1, 3.2],
                                         [0.2, 1, 0.2], [0.2, 1, 0.2]]),
        X.ROUTE(fromNode="MunchClock", fromField="fraction_changed",
                toNode="ripple_int", toField="set_fraction"),
        X.ROUTE(fromNode="ripple_int", fromField="value_changed",
                toNode="Ripple", toField="set_scale"),
    ] + water_anim()

scene = X.Scene(children=[
    X.WorldInfo(title=title),
    background,
    X.NavigationInfo(type=['"EXAMINE"', '"ANY"'], headlight=False),
    *viewpoints,
    *extra_nodes,
    # image-based-ish lighting
    X.EnvironmentLight(ambientIntensity=0.6, intensity=0.6,
                       color=[0.85, 0.88, 0.95]),
    X.DirectionalLight(direction=[-0.4, -0.8, 0.45], intensity=2.2,
                       color=[1.0, 0.96, 0.88]),           # warm key (sun)
    X.DirectionalLight(direction=[0.6, -0.3, -0.5], intensity=0.7,
                       color=[0.6, 0.7, 0.85]),            # cool sky fill
    X.TimeSensor(DEF="MunchClock", cycleInterval=CYCLE, loop=True),
    *env_nodes,
    X.Transform(DEF="MooseRoot", translation=FIG_TRANS, children=[humanoid]),
] + anim_int + anim_routes + bubble_anim)

head_node = X.head(children=[
    X.component(name="HAnim", level=1),
    X.meta(name="title", content=title),
    X.meta(name="description",
           content=("Procedural bull moose, quadruped HAnim rig in HAnim LOA5 spirit; "
                    "metallic-roughness PBR with tiling fur maps; "
                    + ("graze/munch animation." if SCENE == "meadow"
                       else "dives from the surface to browse water-lily bulbs."))),
    X.meta(name="creator", content="generate_moose.py / mflux->X3D pipeline"),
])

x3d_doc = X.X3D(profile="Full", version="4.0", head=head_node, Scene=scene)

# ---------------------------------------------------------------------------
# 8. serialise
# ---------------------------------------------------------------------------
xml = x3d_doc.XML()
# x3d.py omits containerField='skeleton' on the HAnimHumanoid skeleton root, so
# X_ITE files the rig under the default 'children' field and never renders it.
# Inject it on the root joint (the only J_moose_root tag without it).
xml = xml.replace("<HAnimJoint DEF='J_moose_root' ",
                  "<HAnimJoint DEF='J_moose_root' containerField='skeleton' ", 1)
# x3d.py likewise drops containerField on the HAnim skin / skinCoord / skinNormal.
xml = xml.replace("DEF='MooseSkinCoord'",
                  "DEF='MooseSkinCoord' containerField='skinCoord'", 1)
xml = xml.replace("DEF='MooseSkinShape'",
                  "DEF='MooseSkinShape' containerField='skin'", 1)
xml = xml.replace("DEF='MooseLegShape'",
                  "DEF='MooseLegShape' containerField='skin'", 1)
for _lvl in range(1, NSHELL + 1):
    xml = xml.replace(f"DEF='MooseShell{_lvl}'",
                      f"DEF='MooseShell{_lvl}' containerField='skin'", 1)
# x3d.py also drops the containerField when an ImageTexture sits in a PBR slot,
# so X_ITE rejects them ("Unknown field 'texture' in PhysicalMaterial"). Inject
# the right slot per texture URL.
_TEXSLOT = {"fur_albedo": "baseTexture", "fur_normal": "normalTexture",
            "fur_mr": "metallicRoughnessTexture"}
def _fix_tex(m):
    body = m.group(1)
    if "fur_shell" in body:                      # shell-fur RGBA cutout -> baseTexture
        return f"<ImageTexture containerField='baseTexture' {body}/>"
    for key, slot in _TEXSLOT.items():
        if key in body:
            return f"<ImageTexture containerField='{slot}' {body}/>"
    return m.group(0)
xml = re.sub(r"<ImageTexture ([^>]*?)/>", _fix_tex, xml)
x3d_path = "moose.x3d" if SCENE == "meadow" else "moose_lake.x3d"
html_path = "moose_x3dom.html" if SCENE == "meadow" else "moose_lake.html"
with open(x3d_path, "w") as fh:
    fh.write(xml)
print(f"wrote {x3d_path}  ({len(xml):,} bytes, {len(JOINTS)} joints)")

# X_ITE viewer page (renders real HAnim directly -- no flatten needed).
# The scene is INLINED (not src=) so the page loads over file:// without CORS.
hdr = ("munching grass" if SCENE == "meadow"
       else "diving for water-lily bulbs")
inline_x3d = xml[xml.index("<X3D"):]
HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>""" + title + """</title>
<script src="https://create3000.github.io/code/x_ite/latest/x_ite.min.js"></script>
<style>
  html,body{margin:0;height:100%;background:#11161d;color:#cdd6e4;font-family:system-ui,sans-serif}
  #wrap{display:flex;flex-direction:column;height:100%}
  header{padding:.55rem .9rem;font-size:.92rem;border-bottom:1px solid #233}
  header b{color:#e8c87a} header span{color:#7f8da0}
  x3d-canvas{flex:1;width:100%;display:block}
</style></head>
<body><div id="wrap">
  <header><b>Moose</b> &mdash; """ + hdr + """ &nbsp;<span>HAnim LOA5-spirit quadruped rig &middot; metallic-roughness PBR + fur maps &middot; drag to orbit, number keys switch views</span></header>
  <x3d-canvas>
""" + inline_x3d + """
  </x3d-canvas>
</div></body></html>
"""
with open(html_path, "w") as fh:
    fh.write(HTML)
print(f"wrote {html_path}  (X_ITE, inline real HAnim)")
