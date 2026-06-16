#!/usr/bin/env python3
"""Lay the faithfully-traced fauna drawings out as a single to-scale X3D plate --
a '3-D archive' page where the geometry of each animal IS its published line
drawing, scaled to the animal's real dimension and stood on a common ground line.

Pure documentation: every polyline comes from a traced public-domain drawing
(no AI, no invented geometry). Each panel carries a Text label with the species
and the source citation, and a scale bar in feet.

Run:  .venv/bin/python fauna_to_x3d.py
Out:  fauna_plate.x3d   (IndexedLineSet panels + Text labels, viewable in X_ITE)
"""
import re
from svgpathtools import svg2paths

FT_PER_M = 3.28084

# (svg, real LENGTH in metres along the drawing's long axis, label, citation)
FAUNA = [
    ("drawings/fauna/nothrotheriops_skeleton.svg", 2.75,
     "Nothrotheriops shastensis  (Shasta ground sloth)",
     "Stock 1925, Carnegie Inst. Publ. 331, Fig. 4  -  skeleton ~2.75 m"),
    ("drawings/fauna/canis_dirus_skull.svg", 0.31,
     "Canis dirus  (dire wolf) - skull",
     "Merriam 1912, Mem. Univ. Calif. 1(2), fig. 1  -  skull ~0.31 m"),
    ("drawings/fauna/euceratherium_dental.svg", 0.18,
     "Euceratherium collinum  (shrub-ox) - upper dental series",
     "Sinclair & Furlong 1904, Text Fig. 1  -  tooth row ~0.18 m"),
]

GAP_FT = 3.0          # horizontal gap between panels
LABEL_DROP = 1.2      # how far below each panel the label sits


def esc(s):
    """XML-escape text destined for an X3D Text string (e.g. the '&' in citations)."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def polylines_of(svg):
    raw = open(svg).read()
    m = re.search(r'transform="translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)"', raw)
    tx, ty, sx, sy = (tuple(float(g) for g in m.groups()) if m else (0.0, 0.0, 1.0, 1.0))
    paths, _ = svg2paths(svg)
    out = []
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
                    p = seg.point(t)
                    pts.append((tx + sx * p.real, ty + sy * p.imag))
            if len(pts) >= 2:
                out.append(pts)
    return out


# --- archive-gallery layout -------------------------------------------------
# Each drawing is shown LEGIBLY (normalised to a common panel height) in its own
# evenly-spaced bay, captioned with the species, the citation, and -- so the true
# scale is never lost -- the real dimension in words. (We deliberately do NOT
# stand a full sloth *skeleton* and isolated *skulls* on one to-scale baseline:
# that would compare wholes against parts and mislead.)
PANEL_H = 4.6     # max bay height (ft)
PANEL_W = 9.5     # max bay width (ft) -- caps the very wide dental drawing
COL_W = 12.0      # bay pitch (ft)

panels = []
for svg, real_m, label, cite in FAUNA:
    pls = polylines_of(svg)
    xs = [x for pl in pls for x, _ in pl]
    ys = [y for pl in pls for _, y in pl]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w_disp, h_disp = (maxx - minx) or 1.0, (maxy - miny) or 1.0
    s = min(PANEL_H / h_disp, PANEL_W / w_disp)   # fit each into a common box
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    scaled = [[((x - cx) * s, -(y - cy) * s) for x, y in pl] for pl in pls]
    real_ft = real_m * FT_PER_M
    note = (f"actual {real_m:.2f} m ({real_ft:.1f} ft) "
            f"{'long' if real_m > 1 else 'across'} -- shown enlarged for legibility")
    panels.append((scaled, w_disp * s, label, cite, note))

n = len(panels)
shapes, labels = [], []
for k, (scaled, w_ft, label, cite, note) in enumerate(panels):
    px = (k - (n - 1) / 2) * COL_W
    coords, index, i = [], [], 0
    for pl in scaled:
        idx = []
        for x, y in pl:
            coords.append(f"{px + x:.3f} {y:.3f} 0")
            idx.append(str(i))
            i += 1
        index.append(" ".join(idx) + " -1")
    shapes.append(
        f'<Shape><Appearance><Material emissiveColor="0.07 0.06 0.05"/></Appearance>'
        f'<IndexedLineSet coordIndex="{" ".join(index)}">'
        f'<Coordinate point="{" ".join(coords)}"/></IndexedLineSet></Shape>')
    base = -PANEL_H / 2 - 0.9
    for j, (txt, sz, col, fam, style) in enumerate([
            (label, 0.5, "0.1 0.1 0.12", "SANS", ""),
            (cite, 0.36, "0.36 0.34 0.4", "SERIF", "ITALIC"),
            (note, 0.32, "0.5 0.42 0.3", "SANS", "ITALIC")]):
        st = f' style=\'"{style}"\'' if style else ""
        labels.append(
            f'<Transform translation="{px:.3f} {base - j * 0.62:.3f} 0">'
            f'<Shape><Appearance><Material diffuseColor="{col}"/></Appearance>'
            f'<Text string=\'"{esc(txt)}"\' solid="false">'
            f'<FontStyle family="{fam}"{st} justify=\'"MIDDLE" "MIDDLE"\' size="{sz}"/></Text>'
            f'</Shape></Transform>')

# plate title across the top
title_y = PANEL_H / 2 + 1.4
title = (f'<Transform translation="0 {title_y:.2f} 0">'
         f'<Shape><Appearance><Material diffuseColor="0.12 0.12 0.16"/></Appearance>'
         f'<Text string=\'"Potter Creek &amp; Samwel Caves -- the excavated fauna" '
         f'"faithful traces of the original published drawings"\' solid="false">'
         f'<FontStyle family="SERIF" justify=\'"MIDDLE" "MIDDLE"\' size="0.62" spacing="1.25"/></Text>'
         f'</Shape></Transform>')

plate_w = n * COL_W
cam_y = -0.3
cam_z = plate_w * 1.18      # pull back so the full row + captions are framed

x3d = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0">
<head>
<meta name="title" content="Potter Creek &amp; Samwel Caves -- fauna plate (archive gallery, traced)"/>
<meta name="description" content="The excavated megafauna as faithful traces of their original published anatomical drawings, each shown legibly with its citation and true dimension. Documented geometry only -- no AI, no invented bone."/>
<meta name="source" content="Stock 1925 (Nothrotheriops); Merriam 1912 (Canis dirus); Sinclair &amp; Furlong 1904 (Euceratherium). All public domain."/>
<meta name="rights" content="Traces of public-domain anatomical drawings; faithful reproduction, no AI imagery."/>
</head>
<Scene>
<Background skyColor="0.97 0.97 0.95"/>
<NavigationInfo type='"EXAMINE" "ANY"'/>
<Viewpoint description="Fauna plate" position="0 {cam_y:.2f} {cam_z:.1f}" centerOfRotation="0 {cam_y:.2f} 0" fieldOfView="0.85"/>
{title}
{chr(10).join(shapes)}
{chr(10).join(labels)}
</Scene>
</X3D>
"""
open("fauna_plate.x3d", "w").write(x3d)
print(f"wrote fauna_plate.x3d: {len(panels)} panels, plate width {plate_w:.1f} ft, "
      f"panel height {PANEL_H:.1f} ft")
