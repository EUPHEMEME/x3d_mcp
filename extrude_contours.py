#!/usr/bin/env python3
"""Extrude Sinclair's (1904, Plate 14) topographic contour plan of the Potter
Creek chamber floor into a true 3-D documented surface.

Each traced contour loop is lifted by its NESTING DEPTH x the documented 6-inch
contour interval -- compact, deeply-nested loops (the stalagmite bosses) rise as
mounds; the broad depression contours sink as a basin. A Delaunay surface over
the lifted points, clipped to the cave outline, gives the floor. Vertical
exaggeration is applied so the few feet of relief read at chamber scale.

Run:  .venv/bin/python extrude_contours.py
Out:  potter_creek_floor.x3d   (IndexedFaceSet floor + IndexedLineSet contours)
"""
import re
import math
import numpy as np
from svgpathtools import svg2paths
from scipy.spatial import Delaunay

SVG = "drawings/pcc_contours.svg"
OUT = "potter_creek_floor.x3d"
CHAMBER_FT = 107.0      # documented chamber length -> sets the horizontal scale
INTERVAL_FT = 0.5       # documented contour interval (6 inches)
VEXAG = 8.0             # vertical exaggeration so the relief reads


def look_orientation(eye, tgt):
    dx, dy, dz = (tgt[0] - eye[0], tgt[1] - eye[1], tgt[2] - eye[2])
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    fx, fy, fz = dx / n, dy / n, dz / n
    ax, ay, az = (fy, -fx, 0.0)
    al = math.sqrt(ax * ax + ay * ay + az * az)
    if al < 1e-6:
        return "0 1 0 0"
    ang = math.acos(max(-1.0, min(1.0, -fz)))
    return f"{ax/al:.4f} {ay/al:.4f} {az/al:.4f} {ang:.4f}"

raw = open(SVG).read()
m = re.search(r'translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)', raw)
tx, ty, sx, sy = (float(g) for g in m.groups())
paths, _ = svg2paths(SVG)


def disp(p):
    return (tx + sx * p.real, ty + sy * p.imag)


loops = []
for path in paths:
    subs = path.continuous_subpaths() if hasattr(path, "continuous_subpaths") else [path]
    for sub in subs:
        pts = []
        for seg in sub:
            n = 2 if seg.__class__.__name__ == "Line" else 5
            for k in range(n):
                t = k / (n - 1) if n > 1 else 0.0
                pts.append(disp(seg.point(t)))
        if len(pts) >= 6:
            loops.append(np.array(pts))

areas, cents, bb = [], [], []
for pl in loops:
    x, y = pl[:, 0], pl[:, 1]
    a = abs(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
    areas.append(a)
    cents.append((x.mean(), y.mean()))
    bb.append((x.min(), x.max(), y.min(), y.max()))
areas = np.array(areas)


def pip(poly, pt):
    """ray-cast point-in-polygon (poly: Nx2 array)."""
    x, y = pt
    xs, ys = poly[:, 0], poly[:, 1]
    xj, yj = np.roll(xs, 1), np.roll(ys, 1)
    cond = ((ys > y) != (yj > y)) & (x < (xj - xs) * (y - ys) / (yj - ys + 1e-12) + xs)
    return np.count_nonzero(cond) % 2 == 1


oi = int(np.argmax(areas))                       # outline = largest loop
ox0, ox1, oy0, oy1 = bb[oi]
fpp = CHAMBER_FT / (ox1 - ox0)
ocx, ocy = (ox0 + ox1) / 2, (oy0 + oy1) / 2

# filter out text specks and the straight section lines
keep = []
for i in range(len(loops)):
    x0, x1, y0, y1 = bb[i]
    w, h = x1 - x0, y1 - y0
    if areas[i] < areas[oi] * 6e-4:        # drop text specks + tiniest boss rings
        continue
    if max(w, h) / (min(w, h) + 1e-6) > 12 and areas[i] < areas[oi] * 0.01:
        continue
    keep.append(i)

# nesting depth = number of larger kept loops whose interior holds this centroid
depth = {}
for i in keep:
    d = 0
    for j in keep:
        if j != i and areas[j] > areas[i] and pip(loops[j], cents[i]):
            d += 1
    depth[i] = d

BOSS_AREA = areas[oi] * 0.012
coords, lines = [], []
all_xz = []
for i in keep:
    d = depth[i]
    boss = d >= 3 and areas[i] < BOSS_AREA
    z = INTERVAL_FT * VEXAG * (min(d, 4) if boss else -d)   # cap boss spikes
    line_idx = []
    for (x, y) in loops[i]:
        X = (x - ocx) * fpp
        Zm = (y - ocy) * fpp           # footprint depth (X-Z ground plane)
        coords.append((X, z, Zm))      # Y = elevation (terrain config)
        all_xz.append((X, Zm))
        line_idx.append(len(coords) - 1)
    lines.append(line_idx)

# outline polygon in feet (for clipping the surface), in the ground plane
outline_ft = np.array([[(x - ocx) * fpp, (y - ocy) * fpp] for x, y in loops[oi]])

pts = np.array(coords)
xz = np.array(all_xz)
tri = Delaunay(xz)
faces = []
for s in tri.simplices:
    c = xz[s].mean(axis=0)
    if pip(outline_ft, (c[0], c[1])):
        faces.append(s)

coord_str = " ".join(f"{X:.2f} {Y:.2f} {Z:.2f}" for X, Y, Z in coords)
face_str = " ".join(f"{a} {b} {c} -1" for a, b, c in faces)
line_str = " ".join(" ".join(str(k) for k in ln) + " -1" for ln in lines)
span = CHAMBER_FT
eye = (0.0, span * 0.85, span * 0.42)    # steep oblique aerial (~63 deg down)
orient = "1 0 0 -1.1"

# elevation colour ramp (deep basin -> rim -> mound); relief is the Y component
ys = pts[:, 1]
zmin, zmax = float(ys.min()), float(ys.max())


def ramp(y):
    t = (y - zmin) / (zmax - zmin + 1e-9)
    lo, mid, hi = (0.16, 0.22, 0.34), (0.72, 0.63, 0.46), (0.97, 0.92, 0.8)
    if t < 0.5:
        u = t / 0.5
        c = [lo[k] + (mid[k] - lo[k]) * u for k in range(3)]
    else:
        u = (t - 0.5) / 0.5
        c = [mid[k] + (hi[k] - mid[k]) * u for k in range(3)]
    return f"{c[0]:.3f} {c[1]:.3f} {c[2]:.3f}"


col_str = " ".join(ramp(Y) for (_, Y, _) in coords)

x3d = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0">
<head>
<meta name="title" content="Potter Creek Cave -- documented floor topography (Sinclair 1904, Pl. 14)"/>
<meta name="description" content="3D surface extruded from the documented 6-inch contour plan; vertical exaggeration {VEXAG:g}x."/>
</head>
<Scene>
<Background skyColor="0.93 0.93 0.95 0.82 0.84 0.9" groundColor="0.5 0.5 0.52" skyAngle="1.2"/>
<NavigationInfo type='"EXAMINE" "ANY"'/>
<Viewpoint description="3/4 aerial" position="{eye[0]:.1f} {eye[1]:.1f} {eye[2]:.1f}" orientation="{orient}" centerOfRotation="0 0 0" fieldOfView="0.8"/>
<DirectionalLight direction="0.35 -0.55 -0.4" intensity="0.95" color="1 0.98 0.92"/>
<DirectionalLight direction="-0.4 -0.3 0.5" intensity="0.4" color="0.7 0.75 0.85"/>
<Shape>
<Appearance><Material diffuseColor="1 1 1" specularColor="0.08 0.08 0.08" ambientIntensity="0.45"/></Appearance>
<IndexedFaceSet solid="false" colorPerVertex="true" creaseAngle="1.4" coordIndex="{face_str}">
<Coordinate point="{coord_str}"/>
<Color color="{col_str}"/>
</IndexedFaceSet>
</Shape>
<Shape>
<Appearance><Material emissiveColor="0.12 0.1 0.08"/></Appearance>
<IndexedLineSet coordIndex="{line_str}"><Coordinate point="{coord_str}"/></IndexedLineSet>
</Shape>
</Scene>
</X3D>
"""
open(OUT, "w").write(x3d)
print(f"wrote {OUT}: {len(keep)} contours, {len(coords)} pts, {len(faces)} faces; "
      f"depth max {max(depth.values())}, relief +-{max(depth.values())*INTERVAL_FT:.1f} ft "
      f"(x{VEXAG:g} exag)")
