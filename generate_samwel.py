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


def hash01(*a):
    s = sum((i + 1) * v for i, v in enumerate(a))
    f = math.sin(s * 12.9898 + 4.1) * 43758.5453
    return f - math.floor(f)


def rock_color(x, y, phi, base=(0.66, 0.62, 0.55)):
    """Mottled, faintly iron-stained limestone; darker toward the floor."""
    n = 0.84 + 0.26 * hash01(x * 0.7, phi * 1.3, y * 0.5)
    stain = 0.5 + 0.5 * math.sin(0.35 * x + 1.7 * phi)
    r, g, b = base[0] * n + 0.06 * stain, base[1] * n + 0.03 * stain, base[2] * n
    if phi > 2.4:                       # near the chamber floor
        k = 0.78 + 0.22 * (math.pi - phi) / (math.pi - 2.4)
        r, g, b = r * k, g * k, b * k
    return (round(r, 3), round(g, 3), round(b, 3))


def ifs(points, faces, solid="false", crease=1.4, colors=None):
    cattr = ' colorPerVertex="true"' if colors else ''
    cnode = f'<Color color="{fmt_cols(colors)}"/>' if colors else ''
    return (f'<IndexedFaceSet solid="{solid}" creaseAngle="{crease}"{cattr} '
            f'coordIndex="{fmt_idx(faces)}">'
            f'<Coordinate point="{fmt_pts(points)}"/>{cnode}</IndexedFaceSet>')


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

def room_mesh(cx, cy, rx, ry, rz, nv=11, nu=14, seed=0.0):
    """Back-half ellipsoidal chamber void. Returns (points, faces, colors)."""
    pts, cols, grid = [], [], []
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
            row.append((x, y, z))
            cols.append(rock_color(x, y, phi))
        grid.append([len(pts) + j for j in range(len(row))])
        pts.extend(row)
    faces = []
    for iv in range(nv):
        for iu in range(nu):
            a, b = grid[iv][iu], grid[iv][iu + 1]
            c, d = grid[iv + 1][iu + 1], grid[iv + 1][iu]
            faces.append([a, b, c, d])
    return pts, faces, cols


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


def pool(cx, cy, r):
    """A standing 'Magic Pool' -- a thin translucent water disc."""
    return (f'<Transform translation="{fnum(cx)} {fnum(cy)} -3" '
            f'rotation="1 0 0 1.5707"><Shape>'
            f'<Appearance><Material diffuseColor="0.1 0.3 0.45" '
            f'specularColor="0.4 0.5 0.6" transparency="0.45"/></Appearance>'
            f'<Cylinder height="0.2" radius="{fnum(r)}" top="true" '
            f'side="false" bottom="false"/></Shape></Transform>')


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
# the cave, laid out per Furlong's plan (x = East, y = up; section from +z)
# ---------------------------------------------------------------------------
# name: (cx, cy, rx, ry, rz)
ROOMS = {
    "Entrance":            (150, 30, 11,  9,  9),
    "Porcupine Entrance":  (168, 13,  8,  7,  7),
    "Pleistocene Hall":    (100, 23, 30, 16, 17),
    "Chamber One":         ( 54, 19, 16, 13, 13),
    "Merriam's Chamber":   ( 18, 35, 14, 11, 12),
    # the deep lower level -- the drop where the Lost Maiden fell
    "Chamber Two":         ( 34, -12, 15, 10, 12),
}

PASSAGES = [
    # (p0, p1, r0, r1)
    ((139, 29), (128, 24), 5, 7),     # Entrance -> Pleistocene Hall
    ((163, 13), (150, 17), 4, 6),     # Porcupine Entrance -> Hall
    (( 72, 21), ( 68, 19), 6, 6),     # Hall -> Chamber One
    (( 41, 24), ( 30, 33), 4, 5),     # Chamber One -> Merriam's Chamber
    (( 44, 10), ( 37,  -3), 4, 4),    # Chamber One -> pit head
]


def build_scene():
    limestone = ('<Appearance><Material diffuseColor="0.5 0.48 0.43" '
                 'specularColor="0.05 0.05 0.045" ambientIntensity="0.18"/></Appearance>')
    # neutral material: the chamber colour comes from per-vertex rock_color
    limestone_vc = ('<Appearance><Material diffuseColor="1 1 1" '
                    'specularColor="0.08 0.08 0.07" shininess="0.12" '
                    'ambientIntensity="0.2"/></Appearance>')
    flowstone = ('<Appearance><Material diffuseColor="0.62 0.58 0.5" '
                 'specularColor="0.35 0.34 0.3" shininess="0.55" '
                 'ambientIntensity="0.22"/></Appearance>')
    breccia = ('<Appearance><Material diffuseColor="0.42 0.31 0.22" '
               'specularColor="0.03 0.025 0.02" ambientIntensity="0.22"/></Appearance>')

    parts = []

    # chambers (mottled rock via vertex colour) + a little dripstone in the big rooms
    drip_rooms = {"Pleistocene Hall", "Chamber One", "Merriam's Chamber", "Chamber Two"}
    for i, (name, (cx, cy, rx, ry, rz)) in enumerate(ROOMS.items()):
        p, f, c = room_mesh(cx, cy, rx, ry, rz, seed=0.7 * i)
        parts.append(f'<Shape>{limestone_vc}{ifs(p, f, colors=c)}</Shape>')
        parts.append(floor_patch(cx, cy - ry * 0.72, rx * 0.8, breccia))
        if name in drip_rooms:
            nd = 3 + int(3 * hash01(cx, cy))
            for k in range(nd):
                dx = cx + (hash01(cx, k) - 0.5) * 1.4 * rx
                roof = cy + ry * 0.86 * math.sqrt(max(0.0, 1 - ((dx - cx) / rx) ** 2))
                dz = -(1.0 + 0.5 * rz * hash01(cy, k))
                length = ry * (0.2 + 0.4 * hash01(dx, k))
                rad = 0.3 + 0.5 * hash01(dx, k + 5)
                parts.append(dripstone(dx, roof, dz, length, rad, flowstone))

    # passages
    for p0, p1, r0, r1 in PASSAGES:
        p, f = tube_mesh(p0, p1, r0, r1)
        parts.append(shell_shape(p, f, limestone))

    # the deep pit / drop to Chamber Two -- the lower level
    p, f = tube_mesh((37, 6), (34, -4), 4.5, 5.5, ns=10)
    parts.append(shell_shape(p, f, limestone))

    # standing water (Cave of the Magic Pools)
    parts.append(pool(100, 23 - 16 * 0.72 + 0.4, 9))     # Pleistocene Hall
    parts.append(pool(54, 19 - 13 * 0.72 + 0.4, 4.5))    # Chamber One
    parts.append(pool(34, -12 - 10 * 0.72 + 0.4, 5))     # Chamber Two

    # labels
    for name, (cx, cy, rx, ry, rz) in ROOMS.items():
        parts.append(label(cx, cy + ry + 2.5, name))
    parts.append(label(66, 30, "the Gate", size=2.6, col="0.8 0.78 0.66"))
    # respectful marker at the place of the Lost Maiden
    parts.append(label(34, -27, "Pit of the Lost Maiden", size=2.8,
                       col="0.85 0.8 0.7"))

    # lighting: dim section wash + a warm lantern per room + cool entrance light
    lights = [
        '<DirectionalLight direction="0.1 -0.5 -1" intensity="0.44" color="0.8 0.84 0.95"/>',
        '<DirectionalLight direction="-0.2 -1 0.1" intensity="0.16" color="0.55 0.58 0.68"/>',
        daylight(155, 31), daylight(170, 14, 0.6, 45),
        lantern(100, 20, 0.8, 55), lantern(54, 16, 0.75), lantern(18, 33, 0.7),
        lantern(34, -14, 0.65, 40, col="0.9 0.74 0.56"),
    ]

    # framing: front-on section, fit the whole branching system
    eye = (92.0, 22.0, 215.0)
    tgt = (92.0, 14.0, -8.0)
    orient = look_orientation(eye, tgt)

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
        f'<Viewpoint description="Cross-section" '
        f'position="{fnum(eye[0])} {fnum(eye[1])} {fnum(eye[2])}" '
        f'orientation="{orient}" fieldOfView="0.95"/>'
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


def html_doc(scene, xite=False):
    head_lib = ('<script src="https://cdn.jsdelivr.net/npm/x_ite@latest/dist/x_ite.min.js"></script>'
                if xite else
                '<script src="https://x3dom.org/release/x3dom.js"></script>'
                '<link rel="stylesheet" href="https://x3dom.org/release/x3dom.css">')
    body = ('<x3d-canvas src="samwel_cave.x3d"></x3d-canvas>' if xite
            else f'<x3d><Scene>{scene}</Scene></x3d>')
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Samwel Cave</title>
{head_lib}
<style>
 html,body{{margin:0;background:#08080a;color:#cdbfa6;font-family:Georgia,serif}}
 x3d,x3d-canvas,canvas{{width:100vw;height:100vh;display:block}}
 .cap{{position:fixed;left:18px;bottom:14px;max-width:560px;font-size:13px;
   line-height:1.45;text-shadow:0 1px 3px #000;z-index:10}}
 .cap b{{color:#e9d9b8}}
</style></head>
<body>
{body}
<div class="cap"><b>Samwel Cave</b> &mdash; Wintu <i>sawal</i>, "sacred place,"
the Cave of the Lost Maiden. McCloud River, Shasta County. Surveyed by
Furlong, Merriam &amp; Sinclair (1903&ndash;06); cross-section after
Feranec&nbsp;et&nbsp;al.&nbsp;(2007). Sister cave to Potter Creek. Now on the
shore of Shasta Lake, on flooded Winnemem&nbsp;Wintu homeland.</div>
</body></html>
"""


def main():
    scene = build_scene()
    with open("samwel_cave.x3d", "w") as f:
        f.write(x3d_doc(scene))
    with open("samwel_cave.html", "w") as f:
        f.write(html_doc(scene, xite=False))
    with open("samwel_cave_xite.html", "w") as f:
        f.write(html_doc(scene, xite=True))
    print("wrote samwel_cave.x3d, samwel_cave.html, samwel_cave_xite.html")


if __name__ == "__main__":
    main()
