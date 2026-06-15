#!/usr/bin/env python3
"""Samwel Cave -- a labeled cross-section model, sister cave to Potter Creek.

Built from the published cross-sectional plan and stratigraphy in
Feranec, Hadly, Blois, Barnosky & Paytan (2007), "Radiocarbon Dates from
the Pleistocene Fossil Deposits of Samwel Cave" (Radiocarbon 49(1):117-121),
which reproduces Furlong's (1906) survey, and from Furlong, "The Exploration
of Samwel Cave" (Am. J. Sci. 22:235-247, 1906). Excavation 1903-1906 by
E. L. Furlong, J. C. Merriam and W. J. Sinclair.

Samwel = Wintu 'sawal', "holy / sacred place." Also the Cave of the Lost
Maiden, for the Wintu girl Olchanolmet who fell to her death in the dark
lower level; her remains were recovered before Shasta Dam (1945) flooded
the McCloud River canyon -- Winnemem Wintu homeland.

Hard facts used (1 X3D unit = 1 foot):
  * branching two-level system in the McCloud Limestone, 460 m elevation
  * named spaces (Furlong's plan): Entrance, Porcupine Entrance, Pleistocene
    Hall, the Gate, Chamber One, Merriam's Chamber, and Chamber Two
    ("Furlong's Room") down a deep drop to the lower level
  * "Cave of the Magic Pools" -- several standing water pools
  * fauna: 45 mammal + 13 bird species, LGM age (~17,000-23,600 cal BC)

Outputs:  samwel_cave.x3d   (X3D 4.0 XML)
          samwel_cave.html  (X3DOM page)  +  samwel_cave_xite.html (X_ITE)

Rendered as a longitudinal SECTION (back half, z<=0) so the chambers open
toward the viewer and read like the published figure, with floating labels.
"""

import math


def fnum(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")


def fmt_pts(pts):
    return " ".join(f"{fnum(x)} {fnum(y)} {fnum(z)}" for x, y, z in pts)


def fmt_idx(faces):
    return " ".join(" ".join(str(i) for i in f) + " -1" for f in faces)


def fmt_cols(cols):
    return " ".join(f"{fnum(r)} {fnum(g)} {fnum(b)}" for r, g, b in cols)


def fmt_uvs(uvs):
    return " ".join(f"{fnum(u)} {fnum(v)}" for u, v in uvs)


def hash01(*a):
    s = sum((i + 1) * v for i, v in enumerate(a))
    f = math.sin(s * 12.9898 + 4.1) * 43758.5453
    return f - math.floor(f)


def _vn2(x, y, seed):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi

    def h(a, b):
        return hash01(a + seed * 0.137, b - seed * 0.091)

    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    a, b = h(xi, yi), h(xi + 1, yi)
    c, d = h(xi, yi + 1), h(xi + 1, yi + 1)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, y, seed=0.0, octaves=4):
    s, amp, f, tot = 0.0, 0.5, 1.0, 0.0
    for o in range(octaves):
        s += amp * _vn2(x * f, y * f, seed + o)
        tot += amp
        amp *= 0.5
        f *= 2.0
    return s / tot


TEX_FT = 16.0          # one texture tile spans this many feet


def pbr_rock(tint):
    """PhysicalMaterial limestone (albedo + normal + metallic-roughness), as in
    Potter Creek. metallic=0; the MR texture's green channel drives roughness."""
    return (
        f'<Appearance><PhysicalMaterial baseColor="{tint}" metallic="0" '
        f'roughness="1" normalScale="1.6">'
        f'<ImageTexture url=\'"cave_textures/limestone_albedo.png"\' '
        f'containerField="baseTexture"/>'
        f'<ImageTexture url=\'"cave_textures/limestone_normal.png"\' '
        f'containerField="normalTexture"/>'
        f'<ImageTexture url=\'"cave_textures/limestone_mr.png"\' '
        f'containerField="metallicRoughnessTexture"/>'
        f'</PhysicalMaterial></Appearance>')


def ifs(points, faces, solid="false", crease=1.4, colors=None, uvs=None):
    cattr = ' colorPerVertex="true"' if colors else ''
    cnode = f'<Color color="{fmt_cols(colors)}"/>' if colors else ''
    tnode = f'<TextureCoordinate point="{fmt_uvs(uvs)}"/>' if uvs else ''
    return (f'<IndexedFaceSet solid="{solid}" creaseAngle="{crease}"{cattr} '
            f'coordIndex="{fmt_idx(faces)}">'
            f'<Coordinate point="{fmt_pts(points)}"/>{cnode}{tnode}</IndexedFaceSet>')


def dripstone(cx, cy, cz, length, radius, mat, segs=6, nc=8):
    """A tapered stalactite hanging from a chamber roof."""
    rings, pts = [], []
    for s in range(segs + 1):
        t = s / segs
        y = cy - length * t
        rad = max(radius * (1.0 - t) ** 1.3 * (1.0 + 0.18 * math.sin(6.0 * t)), 0.02)
        row = []
        for j in range(nc + 1):
            a = 2.0 * math.pi * j / nc
            row.append((cx + rad * math.cos(a), y, cz + rad * math.sin(a)))
        rings.append([len(pts) + k for k in range(len(row))])
        pts.extend(row)
    faces = []
    for s in range(segs):
        for j in range(nc):
            faces.append([rings[s][j], rings[s][j + 1],
                          rings[s + 1][j + 1], rings[s + 1][j]])
    return f'<Shape>{mat}{ifs(pts, faces, solid="true", crease=1.0)}</Shape>'


# ---------------------------------------------------------------------------
# geometry: back-half (z<=0) shells so the section opens toward the viewer
# ---------------------------------------------------------------------------

def room_mesh(cx, cy, rx, ry, rz, nv=15, nu=18, seed=0.0):
    """Back-half ellipsoidal chamber void with fractal displacement + UVs.
    Returns (points, faces, uvs)."""
    pts, uvs, grid = [], [], []
    for iv in range(nv + 1):
        phi = math.pi * iv / nv                 # 0..pi  (top to bottom)
        row = []
        for iu in range(nu + 1):
            # theta pi..2pi keeps z<=0 (the back half, open toward +z)
            theta = math.pi + math.pi * iu / nu
            rug = 1.0 + 0.05 * math.sin(3.0 * phi + seed) * math.cos(2.0 * theta + seed)
            x = cx + rx * rug * math.sin(phi) * math.cos(theta)
            y = cy + ry * rug * math.cos(phi)
            z = rz * rug * math.sin(phi) * math.sin(theta)
            # fractal displacement along the radial direction -> real relief
            d = (fbm(x * 0.08 + seed, y * 0.08, 2.0) - 0.5) * 2.0 * 1.3
            ox, oy, oz = x - cx, y - cy, z
            ol = math.sqrt(ox * ox + oy * oy + oz * oz) or 1.0
            x += d * ox / ol
            y += d * oy / ol
            z += d * oz / ol
            row.append((x, y, z))
            uvs.append((x / TEX_FT, y / TEX_FT))
        grid.append([len(pts) + j for j in range(len(row))])
        pts.extend(row)
    faces = []
    for iv in range(nv):
        for iu in range(nu):
            a, b = grid[iv][iu], grid[iv][iu + 1]
            c, d = grid[iv + 1][iu + 1], grid[iv + 1][iu]
            faces.append([a, b, c, d])
    return pts, faces, uvs


def tube_mesh(p0, p1, r0, r1=None, ns=8, nc=8):
    """Back-half tube (passage) from p0 to p1. Returns (points, faces)."""
    if r1 is None:
        r1 = r0
    ax, ay = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(ax, ay) or 1.0
    ux, uy = ax / L, ay / L            # axis direction in the section plane
    px, py = -uy, ux                   # in-plane perpendicular
    pts, grid = [], []
    for i in range(ns + 1):
        t = i / ns
        cx = p0[0] + ax * t
        cy = p0[1] + ay * t
        r = r0 + (r1 - r0) * t
        row = []
        for j in range(nc + 1):
            theta = math.pi + math.pi * j / nc          # z<=0 half
            off = r * math.cos(theta)
            z = r * math.sin(theta)
            row.append((cx + px * off, cy + py * off, z))
        grid.append([len(pts) + k for k in range(len(row))])
        pts.extend(row)
    faces = []
    for i in range(ns):
        for j in range(nc):
            a, b = grid[i][j], grid[i][j + 1]
            c, d = grid[i + 1][j + 1], grid[i + 1][j]
            faces.append([a, b, c, d])
    return pts, faces


def shell_shape(points, faces, mat):
    return f'<Shape>{mat}{ifs(points, faces)}</Shape>'


def floor_patch(cx, cy, rx, mat):
    """A small rubble/breccia floor disc at a chamber bottom."""
    return (f'<Transform translation="{fnum(cx)} {fnum(cy)} -2" '
            f'rotation="1 0 0 1.5707">'
            f'<Shape>{mat}<Cylinder height="0.6" radius="{fnum(rx)}" '
            f'top="true" side="false" bottom="false"/></Shape></Transform>')


_WATER = ('<Appearance><PhysicalMaterial baseColor="0.06 0.16 0.2" metallic="0" '
          'roughness="0.08" transparency="0.35" normalScale="0.6">'
          '<ImageTexture url=\'"cave_textures/water_normal.png"\' '
          'containerField="normalTexture"/></PhysicalMaterial></Appearance>')


def pool(cx, cy, r):
    """A standing pool -- rippled PBR water disc."""
    return (f'<Transform translation="{fnum(cx)} {fnum(cy)} -3" '
            f'rotation="1 0 0 1.5707"><Shape>{_WATER}'
            f'<Cylinder height="0.15" radius="{fnum(r)}" top="true" '
            f'side="false" bottom="false"/></Shape></Transform>')


def magic_pool(cx, cy, r):
    """The famous sacred Magic Pool -- rippled water with an inner luminous glow,
    so it reads as the restorative pool deep in the cave."""
    glow = ('<Appearance><PhysicalMaterial baseColor="0.1 0.4 0.45" metallic="0" '
            'roughness="0.06" transparency="0.25" emissiveColor="0.06 0.3 0.34" '
            'normalScale="0.7">'
            '<ImageTexture url=\'"cave_textures/water_normal.png"\' '
            'containerField="normalTexture"/></PhysicalMaterial></Appearance>')
    return (
        # a soft glow from the pool itself
        f'<PointLight location="{fnum(cx)} {fnum(cy + 3)} -3" color="0.5 0.9 1" '
        f'intensity="0.8" radius="40" attenuation="1 0.04 0.006"/>'
        f'<Transform translation="{fnum(cx)} {fnum(cy)} -3" '
        f'rotation="1 0 0 1.5707"><Shape>{glow}'
        f'<Cylinder height="0.15" radius="{fnum(r)}" top="true" '
        f'side="false" bottom="false"/></Shape></Transform>')


def god_ray(cx, cy, height):
    """A daylight shaft at an entrance: nested emissive cones + dust motes."""
    out = [f'<Transform translation="{fnum(cx)} {fnum(cy)} -2">']
    for rad, em, tr in ((6.0, "0.34 0.45 0.62", 0.94),
                        (3.8, "0.5 0.62 0.8", 0.9),
                        (2.0, "0.7 0.82 1", 0.84)):
        out.append(
            f'<Shape><Appearance><Material emissiveColor="{em}" '
            f'transparency="{tr}"/></Appearance>'
            f'<Cone bottomRadius="{fnum(rad)}" height="{fnum(height)}" '
            f'side="true" bottom="false"/></Shape>')
    out.append('</Transform>')
    for i in range(9):
        mx = cx + (hash01(i, cx) - 0.5) * 7
        my = cy - height * 0.5 + height * hash01(i, 2.2)
        mz = -2 + (hash01(i, 3.3) - 0.5) * 5
        out.append(
            f'<Transform translation="{fnum(mx)} {fnum(my)} {fnum(mz)}">'
            f'<Shape><Appearance><Material emissiveColor="0.8 0.86 1" '
            f'transparency="0.3"/></Appearance>'
            f'<Sphere radius="{fnum(0.08 + 0.1 * hash01(i, 4.4))}"/></Shape></Transform>')
    return "".join(out)


def column(cx, cy, cz, height, rmax, mat, segs=11, nc=10):
    """A floor-to-roof column (fused stalactite + stalagmite) in a chamber."""
    rings, pts = [], []
    for s in range(segs + 1):
        t = s / segs
        y = cy + height * t
        prof = 0.45 + 0.55 * abs(math.cos(math.pi * t))
        rad = max(rmax * prof * (1.0 + 0.14 * math.sin(9.0 * t + cx)), 0.05)
        row = []
        for j in range(nc + 1):
            a = 2.0 * math.pi * j / nc
            row.append((cx + rad * math.cos(a), y, cz + rad * math.sin(a)))
        rings.append([len(pts) + k for k in range(len(row))])
        pts.extend(row)
    faces = []
    for s in range(segs):
        for j in range(nc):
            faces.append([rings[s][j], rings[s][j + 1],
                          rings[s + 1][j + 1], rings[s + 1][j]])
    return f'<Shape>{mat}{ifs(pts, faces, solid="true", crease=1.0)}</Shape>'


def breakdown(cx, cy, rx, mat, n=4):
    """Angular fallen-rock blocks scattered on a chamber floor."""
    out = []
    for i in range(n):
        x = cx + (hash01(cx, i) - 0.5) * 1.4 * rx
        z = -(1.0 + 4.0 * hash01(cx, i + 2))
        s = 1.0 + 2.4 * hash01(cx, i + 3)
        sx, sy, sz = s * (0.7 + 0.5 * hash01(x, i)), s * (0.4 + 0.4 * hash01(x, i + 1)), \
            s * (0.6 + 0.5 * hash01(x, i + 4))
        ang = 6.2832 * hash01(x, i + 5)
        ax, ay, az = hash01(x, i + 6), 0.3 + hash01(x, i + 7), hash01(x, i + 8)
        out.append(
            f'<Transform translation="{fnum(x)} {fnum(cy)} {fnum(z)}" '
            f'rotation="{fnum(ax)} {fnum(ay)} {fnum(az)} {fnum(ang)}">'
            f'<Shape>{mat}<Box size="{fnum(sx)} {fnum(sy)} {fnum(sz)}"/></Shape>'
            f'</Transform>')
    return "".join(out)


def daylight_cone(cx, cy, height, mat):
    """A faint translucent shaft of daylight at an entrance."""
    return (f'<Transform translation="{fnum(cx)} {fnum(cy)} -2">'
            f'<Shape>{mat}<Cone bottomRadius="6" height="{fnum(height)}" '
            f'side="true" bottom="false"/></Shape></Transform>')


def _esc(s):
    return s.replace("&", "&amp;").replace("'", "&apos;").replace('"', "&quot;")


def label(cx, cy, text, size=3.4, col="0.93 0.88 0.72"):
    return (f'<Transform translation="{fnum(cx)} {fnum(cy)} 6"><Shape>'
            f'<Appearance><Material diffuseColor="{col}" '
            f'emissiveColor="{col}"/></Appearance>'
            f"<Text string='\"{_esc(text)}\"' solid=\"false\">"
            f'<FontStyle size="{fnum(size)}" family=\'"SANS"\' '
            f'justify=\'"MIDDLE" "MIDDLE"\'/></Text></Shape></Transform>')


def lantern(cx, cy, intensity=0.55, radius=40, col="1 0.82 0.5"):
    return (f'<PointLight location="{fnum(cx)} {fnum(cy)} -3" color="{col}" '
            f'intensity="{fnum(intensity)}" radius="{fnum(radius)}" '
            f'attenuation="1 0.035 0.005"/>')


def daylight(cx, cy, intensity=0.8, radius=55):
    return (f'<PointLight location="{fnum(cx)} {fnum(cy)} 6" color="0.7 0.8 1" '
            f'intensity="{fnum(intensity)}" radius="{fnum(radius)}" '
            f'attenuation="1 0.02 0.003"/>')


def look_orientation(eye, target):
    dx, dy, dz = (target[0] - eye[0], target[1] - eye[1], target[2] - eye[2])
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    fx, fy, fz = dx / n, dy / n, dz / n
    ax, ay, az = (fy, -fx, 0.0)                 # cross((0,0,-1), f)
    al = math.sqrt(ax * ax + ay * ay + az * az)
    if al < 1e-6:
        return "0 1 0 0"
    ax, ay, az = ax / al, ay / al, az / al
    ang = math.acos(max(-1.0, min(1.0, -fz)))
    return f"{fnum(ax)} {fnum(ay)} {fnum(az)} {fnum(ang)}"


# ---------------------------------------------------------------------------
# PROVENANCE.  DOCUMENTED: the named chambers and their arrangement (Entrance,
# Porcupine Entrance, Pleistocene Hall, Gate, Chamber One, Merriam's Chamber,
# Chamber Two down a deep drop) follow Furlong's plan as redrawn by Feranec et
# al. (2007); Chamber Two is the lower level reached only via a "~90-foot-deep
# hole" -- the shaft the maiden fell down, which connects the upper/main level
# to the lower one; the "Cave of the Magic Pools" and its sacred restorative
# pool ("Wintu medicine men bathed in the water pools to get magic strength")
# and the 460 m / McCloud-Limestone setting are documented.
# IMAGINARY/INTERPRETIVE: the individual room SIZES and the exact pit geometry
# (only its ~90 ft depth is documented), every speleothem, breakdown blocks,
# exact pool placements, the daylight shafts, lighting, and surface detail.
# ---------------------------------------------------------------------------
# the cave, laid out per Furlong's plan (x = East, y = up; section from +z)
# name: (cx, cy, rx, ry, rz)
ROOMS = {
    "Entrance":            (150, 30, 11,  9,  9),
    "Porcupine Entrance":  (168, 13,  8,  7,  7),
    "Pleistocene Hall":    (100, 23, 30, 16, 17),
    "Chamber One":         ( 54, 19, 16, 13, 13),
    "Merriam's Chamber":   ( 18, 35, 14, 11, 12),
    # the deep lower level -- reached only by the ~90 ft hole the maiden fell
    # down (sources: she "fell to her death into a 90-foot-deep hole"). The hole
    # connects the upper/main level (Chamber One) to this lower chamber.
    "Chamber Two":         ( 40, -58, 17, 12, 14),
}

PASSAGES = [
    # (p0, p1, r0, r1)
    ((139, 29), (128, 24), 5, 7),     # Entrance -> Pleistocene Hall
    ((163, 13), (150, 17), 4, 6),     # Porcupine Entrance -> Hall
    (( 72, 21), ( 68, 19), 6, 6),     # Hall -> Chamber One
    (( 41, 24), ( 30, 33), 4, 5),     # Chamber One -> Merriam's Chamber
]


def build_scene():
    # normal-mapped, displaced PBR limestone (as in Potter Creek)
    limestone = pbr_rock("0.9 0.88 0.82")
    breccia_pbr = pbr_rock("0.6 0.45 0.32")
    flowstone = ('<Appearance><Material diffuseColor="0.62 0.58 0.5" '
                 'specularColor="0.35 0.34 0.3" shininess="0.55" '
                 'ambientIntensity="0.22"/></Appearance>')
    breccia = ('<Appearance><Material diffuseColor="0.42 0.31 0.22" '
               'specularColor="0.03 0.025 0.02" ambientIntensity="0.22"/></Appearance>')
    rubble = ('<Appearance><Material diffuseColor="0.38 0.3 0.23" '
              'specularColor="0.04 0.035 0.03" ambientIntensity="0.2"/></Appearance>')

    parts = []

    # chambers: displaced PBR rock + dripstone, breakdown, a column
    drip_rooms = {"Pleistocene Hall", "Chamber One", "Merriam's Chamber", "Chamber Two"}
    col_rooms = {"Pleistocene Hall", "Chamber One"}
    for i, (name, (cx, cy, rx, ry, rz)) in enumerate(ROOMS.items()):
        p, f, uv = room_mesh(cx, cy, rx, ry, rz, seed=0.7 * i)
        parts.append(f'<Shape>{limestone}{ifs(p, f, uvs=uv)}</Shape>')
        parts.append(floor_patch(cx, cy - ry * 0.72, rx * 0.8, breccia))
        parts.append(breakdown(cx, cy - ry * 0.7, rx, rubble))
        if name in drip_rooms:
            nd = 3 + int(3 * hash01(cx, cy))
            for k in range(nd):
                dx = cx + (hash01(cx, k) - 0.5) * 1.4 * rx
                roof = cy + ry * 0.86 * math.sqrt(max(0.0, 1 - ((dx - cx) / rx) ** 2))
                dz = -(1.0 + 0.5 * rz * hash01(cy, k))
                length = ry * (0.2 + 0.4 * hash01(dx, k))
                rad = 0.3 + 0.5 * hash01(dx, k + 5)
                parts.append(dripstone(dx, roof, dz, length, rad, flowstone))
        if name in col_rooms:
            base = cy - ry * 0.7
            parts.append(column(cx - rx * 0.3, base, -(0.4 * rz),
                                 ry * 1.5, 0.5 + 0.5 * hash01(cx, 3), flowstone))

    # passages
    for p0, p1, r0, r1 in PASSAGES:
        p, f = tube_mesh(p0, p1, r0, r1)
        parts.append(shell_shape(p, f, limestone))

    # THE ~90 FT HOLE: the vertical shaft the maiden fell down, connecting the
    # upper/main level (Chamber One floor, ~y 8) to the lower level (Chamber Two,
    # ~y -46 at its roof). Built as a long, slightly-bent back-half tube.
    p, f = tube_mesh((45, 8), (42, -20), 4.0, 4.6, ns=12)
    parts.append(shell_shape(p, f, limestone))
    p, f = tube_mesh((42, -20), (40, -46), 4.6, 6.0, ns=12)
    parts.append(shell_shape(p, f, limestone))

    # standing water -- the Cave of the Magic Pools. Wintu medicine men bathed in
    # the pools for "magic strength"; the sacred pool lies deep in the cave.
    parts.append(pool(100, 23 - 16 * 0.72 + 0.4, 7))     # Pleistocene Hall
    parts.append(pool(54, 19 - 13 * 0.72 + 0.4, 4.0))    # Chamber One
    # the famous Magic Pool on the floor of the deep lower chamber
    parts.append(magic_pool(40, -58 - 12 * 0.72 + 0.5, 8))

    # shafts of daylight at the two outside entrances
    parts.append(god_ray(150, 30, 26))
    parts.append(god_ray(168, 13, 20))

    # labels
    for name, (cx, cy, rx, ry, rz) in ROOMS.items():
        parts.append(label(cx, cy + ry + 2.5, name))
    parts.append(label(66, 30, "the Gate", size=2.6, col="0.8 0.78 0.66"))
    # the ~90 ft hole and the sacred pool, marked respectfully
    parts.append(label(48, -22, "the 90 ft hole", size=2.4, col="0.8 0.78 0.66"))
    parts.append(label(40, -34, "Pit of the Lost Maiden", size=2.8,
                       col="0.85 0.8 0.7"))
    parts.append(label(40, -72, "the Magic Pool", size=3.0, col="0.7 0.92 0.95"))

    # lighting: section wash + a warm lantern per room (brighter so dripstone reads)
    lights = [
        '<DirectionalLight direction="0.1 -0.5 -1" intensity="0.55" color="0.82 0.86 0.96"/>',
        '<DirectionalLight direction="-0.2 -1 0.1" intensity="0.2" color="0.55 0.58 0.68"/>',
        daylight(152, 31, 1.0), daylight(168, 14, 0.75, 45),
        lantern(100, 19, 1.0, 60), lantern(54, 15, 0.95, 45),
        lantern(18, 32, 0.9, 42), lantern(40, -56, 0.8, 46, col="0.92 0.76 0.56"),
    ]

    # framing: front-on section, fit the whole system incl. the deep lower level
    eye = (95.0, -6.0, 238.0)
    tgt = (92.0, -12.0, -8.0)
    orient = look_orientation(eye, tgt)
    # hero: the descent -- Chamber One, the ~90 ft hole, Chamber Two + Magic Pool
    hero = (46.0, -18.0, 122.0)
    hero_o = look_orientation(hero, (42.0, -32.0, -8.0))

    title = (
        '<Transform translation="92 60 6"><Shape>'
        '<Appearance><Material diffuseColor="0.95 0.92 0.82" '
        'emissiveColor="0.95 0.92 0.82"/></Appearance>'
        "<Text string='\"Samwel Cave — Cave of the Lost Maiden\"' solid=\"false\">"
        '<FontStyle size="5.5" family=\'"SANS"\' justify=\'"MIDDLE" "MIDDLE"\'/>'
        '</Text></Shape></Transform>'
    )

    scene = (
        '<Background skyColor="0.02 0.02 0.03 0.03 0.03 0.045" '
        'groundColor="0.015 0.015 0.02" skyAngle="1.2"/>'
        '<Fog fogType="LINEAR" color="0.03 0.03 0.045" visibilityRange="620"/>'
        '<NavigationInfo type=\'"EXAMINE" "ANY"\' headlight="false" speed="14"/>'
        f'<Viewpoint DEF="Section" description="Cross-section" '
        f'position="{fnum(eye[0])} {fnum(eye[1])} {fnum(eye[2])}" '
        f'orientation="{orient}" fieldOfView="0.95"/>'
        f'<Viewpoint DEF="Hero" description="Lower level -- the drop to Chamber Two" '
        f'position="{fnum(hero[0])} {fnum(hero[1])} {fnum(hero[2])}" '
        f'orientation="{hero_o}" fieldOfView="0.95"/>'
        + "".join(lights)
        + title
        + f'<Group>{"".join(parts)}</Group>'
    )
    return scene


def x3d_doc(scene):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" '
        '"https://www.web3d.org/specifications/x3d-4.0.dtd">\n'
        '<X3D profile="Immersive" version="4.0" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance" '
        'xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">\n'
        '<head>\n'
        '<meta name="title" content="Samwel Cave — Cave of the Lost Maiden"/>\n'
        '<meta name="description" content="Labeled cross-section of Samwel Cave '
        '(Furlong 1906; Feranec et al. 2007). Sister cave to Potter Creek; '
        'McCloud River, Shasta County, California. Winnemem Wintu sacred site."/>\n'
        '<meta name="reference" content="Feranec, R.S. et al. (2007) Radiocarbon '
        '49(1):117-121; Furlong, E.L. (1906) Am. J. Sci. 22:235-247."/>\n'
        '<meta name="creator" content="x3d_mcp cave pipeline"/>\n'
        '</head>\n'
        f'<Scene>\n{scene}\n</Scene>\n</X3D>\n'
    )


XITE_VER = "15.1.4"          # pinned (was @latest)

FILE_GUARD = """<script>
if (location.protocol === 'file:') {
  window.addEventListener('DOMContentLoaded', function () {
    document.body.style.cssText = 'margin:0;height:100vh;display:flex;align-items:'
      + 'center;justify-content:center;background:#0a0a0c;color:#cdbfa6;'
      + 'font-family:Georgia,serif;text-align:center';
    document.body.innerHTML = '<div style="max-width:540px;padding:24px;line-height:1.6">'
      + '<h2 style="color:#e9d9b8">Start the local viewer</h2>'
      + '<p>This 3-D viewer loads its data over <b>http</b>. Browsers block the '
      + 'renderer from reading 3-D files over <code>file://</code>, so opening this '
      + 'page by double-click shows nothing.</p>'
      + '<p>In Terminal, from the project folder, run:</p>'
      + '<p style="background:#1d1a14;padding:10px 16px;border-radius:6px;'
      + 'display:inline-block;font-family:monospace">./start_caves.sh</p>'
      + '<p>It serves the folder and opens '
      + '<b>http://127.0.0.1:8099/caves.html</b> for you.</p></div>';
  });
}
</script>"""

SAMWEL_CAP = (
    '<b>Samwel Cave</b> &mdash; Wintu <i>sawal</i>, "sacred place," the Cave of '
    'the Lost Maiden. McCloud River, Shasta County. Surveyed by Furlong, Merriam '
    '&amp; Sinclair (1903&ndash;06); cross-section after Feranec&nbsp;et&nbsp;al. '
    '(2007). Now on the shore of Shasta Lake, on flooded Winnemem&nbsp;Wintu '
    'homeland. <span style="opacity:.8">Chamber layout, the Magic Pools, and the '
    '~90&nbsp;ft hole connecting the upper and lower levels are documented; room '
    'sizes, exact pit geometry, speleothems and lighting are interpretive.</span>'
)


def xite_html(title, src, caption):
    """A guarded, version-pinned X_ITE viewer page."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
{FILE_GUARD}
<script src="https://cdn.jsdelivr.net/npm/x_ite@{XITE_VER}/dist/x_ite.min.js"></script>
<style>
 html,body{{margin:0;background:#08080a;color:#cdbfa6;font-family:Georgia,serif}}
 x3d-canvas,canvas{{width:100vw;height:100vh;display:block}}
 .cap{{position:fixed;left:18px;bottom:14px;max-width:560px;font-size:13px;
   line-height:1.45;text-shadow:0 1px 3px #000;z-index:10}}
 .cap b{{color:#e9d9b8}}
 .home{{position:fixed;left:18px;top:14px;font-size:13px;z-index:10}}
 .home a{{color:#cdbfa6;opacity:.75;text-decoration:none}}
</style></head>
<body>
<x3d-canvas src="{src}"></x3d-canvas>
<div class="home"><a href="caves.html">&larr; all caves</a></div>
<div class="cap">{caption}</div>
</body></html>
"""


def main():
    scene = build_scene()
    with open("samwel_cave.x3d", "w") as f:
        f.write(x3d_doc(scene))
    with open("samwel_cave_xite.html", "w") as f:
        f.write(xite_html("Samwel Cave", "samwel_cave.x3d", SAMWEL_CAP))
    with open("samwel_cave_hero.html", "w") as f:
        f.write(xite_html("Samwel Cave — the descent",
                          "samwel_cave.x3d#Hero", SAMWEL_CAP))
    print("wrote samwel_cave.x3d + xite/hero viewer pages")


if __name__ == "__main__":
    main()
