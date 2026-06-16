#!/usr/bin/env python3
"""Convert a potrace SVG (a faithfully-traced B&W survey drawing) into an X3D
IndexedLineSet -- a 'documented' line model whose geometry IS the drawing,
laid flat in the X-Z plane as a plan and scaled to real feet.

Usage:  svg_to_x3d.py <in.svg> <out.x3d> <real_width_ft> "<title>"

Run with the venv that has svgpathtools:  .venv/bin/python svg_to_x3d.py ...
"""
import sys
import re
from svgpathtools import svg2paths

SVG, OUT, REAL_W = sys.argv[1], sys.argv[2], float(sys.argv[3])
TITLE = sys.argv[4] if len(sys.argv) > 4 else ""
SOURCE = sys.argv[5] if len(sys.argv) > 5 else TITLE   # full citation for the archive

raw = open(SVG).read()
# potrace wraps everything in <g transform="translate(tx,ty) scale(sx,sy)">
m = re.search(r'transform="translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)"', raw)
tx, ty, sx, sy = (tuple(float(g) for g in m.groups()) if m else (0.0, 0.0, 1.0, 1.0))

paths, _ = svg2paths(SVG)


def disp(p):
    """path coordinate -> on-page display coordinate (apply the g transform)."""
    return (tx + sx * p.real, ty + sy * p.imag)


# flatten every continuous subpath to a polyline of display points
polylines = []
for path in paths:
    try:
        subs = path.continuous_subpaths()
    except Exception:
        subs = [path]
    for sub in subs:
        pts = []
        for seg in sub:
            n = 2 if seg.__class__.__name__ == "Line" else 8
            for i in range(n):
                t = i / (n - 1) if n > 1 else 0.0
                pts.append(disp(seg.point(t)))
        if len(pts) >= 2:
            polylines.append(pts)

xs = [x for pl in polylines for x, _ in pl]
ys = [y for pl in polylines for _, y in pl]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
fpp = REAL_W / (maxx - minx or 1.0)          # feet per display unit
cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

coords, index, i = [], [], 0
for pl in polylines:
    idx = []
    for x, y in pl:
        # lay the drawing upright in the X-Y plane (page-up -> +Y) so it reads
        # exactly as printed; rotate into the ground plane later to extrude.
        X = (x - cx) * fpp
        Y = -(y - cy) * fpp
        coords.append(f"{X:.2f} {Y:.2f} 0")
        idx.append(str(i))
        i += 1
    index.append(" ".join(idx) + " -1")

W_ft = (maxx - minx) * fpp
H_ft = (maxy - miny) * fpp
cam = max(W_ft, H_ft) * 1.15

x3d = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0">
<head>
<meta name="title" content="{TITLE}"/>
<meta name="description" content="Documented line model traced from the original survey drawing; geometry to scale ({W_ft:.0f} x {H_ft:.0f} ft)."/>
<meta name="source" content="{SOURCE}"/>
<meta name="rights" content="Trace of a public-domain survey drawing; faithful reproduction, no AI imagery."/>
</head>
<Scene>
<Background skyColor="1 1 1"/>
<NavigationInfo type='"EXAMINE" "ANY"'/>
<Viewpoint description="Plan (face-on)" position="0 0 {cam:.1f}" centerOfRotation="0 0 0" fieldOfView="0.9"/>
<Shape>
<Appearance><Material emissiveColor="0 0 0"/></Appearance>
<IndexedLineSet coordIndex="{' '.join(index)}">
<Coordinate point="{' '.join(coords)}"/>
</IndexedLineSet>
</Shape>
</Scene>
</X3D>
"""
open(OUT, "w").write(x3d)
print(f"wrote {OUT}: {len(polylines)} polylines, {i} points, "
      f"to scale {W_ft:.0f} x {H_ft:.0f} ft")
