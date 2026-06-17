#!/usr/bin/env python3
"""Potter Creek & Samwel Caves -- the documented deposit, the mixed fauna, and an
interpretive hero.  A 'bone-horizon' stratigraphic scene that keeps the project's
one rule: documented vs interpretive never blurs, and nothing is invented.

Everything here is driven by drawings/strata_spec.json, the citation-anchored
spec distilled (by a multi-source research pass) from the PRIMARY literature:
  * Sinclair, W. J. (1904) The Exploration of the Potter Creek Cave -- the
    documented NW-fan stratigraphic column (S,A,B,C,D,E,F,G,H, in feet) and the
    DECISIVE faunal verdict: "No distinction is to be drawn between the
    collections from the different layers ... The fauna listed is a unit" (p.19).
  * Payen & Taylor (1976) -- the one Potter Creek megafaunal find with a measured
    depth AND a date: a Euceratherium radius+ulna in breccia at 170 cm,
    8250 +/- 330 14C BP (UCR-381); the polished 'bone implements' whose HUMAN
    origin they refute; the late-Holocene flake/charcoal cluster.
  * Feranec et al. (2007) -- the Samwel column (cm) and the only per-specimen
    depth dataset (four Chamber-Two AMS dates at real square+inch levels), with
    the caveat that the deposit is NOT chronologically stratified (depth != age).

So: the Potter Creek fauna get ONE honest "throughout the bone-bearing clay and
breccia -- mixed, not depth-sorted" marker plus the few genuinely depth-anchored
facts; the Shasta ground-sloth skeleton (Stock 1925, a real traced drawing) stands
beside the column as a clearly-labelled UNPROVENANCED context hero, never embedded
in a layer; Samwel's four dated specimens are pinned at their documented levels.

Run:  .venv/bin/python generate_fauna_strata.py
Out:  potter_creek_strata.x3d   (IndexedFaceSet slabs + IndexedLineSet pins +
                                  Text; X_ITE via potter_creek_strata_xite.html)
"""
import json
import math
import re
from svgpathtools import svg2paths

SPEC = json.load(open("drawings/strata_spec.json"))
CM_PER_FT = 30.48
OUT = "potter_creek_strata.x3d"

DOC = "0.10 0.10 0.12"        # documented label ink
DOC_FAINT = "0.40 0.38 0.42"  # documented sub-label
INTERP = "0.74 0.34 0.10"     # interpretive flag colour (warm rust)
PIN = "0.12 0.12 0.16"        # depth-pin ink


def esc(s):
    # Text strings sit in a single-quoted attribute with double-quoted MFString
    # items, so apostrophes AND straight double-quotes must be entity-escaped.
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))


# ---------------------------------------------------------------- X3D helpers
def slab(cx, cz, w, d, top_y, bot_y, color):
    """A coloured deposit slab (a box) spanning [bot_y, top_y] in elevation."""
    h = top_y - bot_y
    cy = (top_y + bot_y) / 2
    return (f'<Transform translation="{cx:.3f} {cy:.3f} {cz:.3f}">'
            f'<Shape><Appearance><Material diffuseColor="{color}" '
            f'ambientIntensity="0.55" specularColor="0.05 0.05 0.05"/></Appearance>'
            f'<Box size="{w:.3f} {h:.3f} {d:.3f}"/></Shape></Transform>')


def text(x, y, z, s, size, color, fam="SANS", style="", justify="MIDDLE",
         vjust="MIDDLE"):
    st = f' style="{style}"' if style else ""   # FontStyle.style is SFString (bare token)
    return (f'<Transform translation="{x:.3f} {y:.3f} {z:.3f}">'
            f'<Shape><Appearance><Material diffuseColor="{color}"/></Appearance>'
            f'<Text string=\'"{esc(s)}"\' solid="false">'
            f'<FontStyle family="{fam}"{st} size="{size:.3f}" '
            f'justify=\'"{justify}" "{vjust}"\'/></Text></Shape></Transform>')


def multitext(x, y, z, lines, size, color, fam="SANS", style="", justify="BEGIN"):
    st = f' style="{style}"' if style else ""   # FontStyle.style is SFString (bare token)
    strs = " ".join(f'"{esc(l)}"' for l in lines)
    return (f'<Transform translation="{x:.3f} {y:.3f} {z:.3f}">'
            f'<Shape><Appearance><Material diffuseColor="{color}"/></Appearance>'
            f'<Text string=\'{strs}\' solid="false">'
            f'<FontStyle family="{fam}"{st} size="{size:.3f}" spacing="1.15" '
            f'justify=\'"{justify}" "BEGIN"\'/></Text></Shape></Transform>')


def lineset(pts, color, idx=None):
    coord = " ".join(f"{x:.3f} {y:.3f} {z:.3f}" for x, y, z in pts)
    if idx is None:
        idx = " ".join(str(i) for i in range(len(pts))) + " -1"
    return (f'<Shape><Appearance><Material emissiveColor="{color}"/></Appearance>'
            f'<IndexedLineSet coordIndex="{idx}">'
            f'<Coordinate point="{coord}"/></IndexedLineSet></Shape>')


def depth_pin(face_x, z, y, label_lines, color=PIN, side=-1, lead=3.2,
              size=0.42, interp=False):
    """A tick at the layer face + a leader running out to a stacked text label.
    side=-1 → label to the left, +1 → to the right."""
    x_tip = face_x
    x_tick = face_x + side * 0.6
    x_lead = face_x + side * lead
    out = [lineset([(x_tip, y, z), (x_lead, y, z)], color)]
    lx = x_lead + side * 0.3
    just = "END" if side < 0 else "BEGIN"
    st = "ITALIC" if interp else ""
    col = INTERP if interp else color
    strs = " ".join(f'"{esc(l)}"' for l in label_lines)
    sc = f' style="{st}"' if st else ""   # FontStyle.style is SFString
    out.append(
        f'<Transform translation="{lx:.3f} {y:.3f} {z:.3f}">'
        f'<Shape><Appearance><Material diffuseColor="{col}"/></Appearance>'
        f'<Text string=\'{strs}\' solid="false">'
        f'<FontStyle family="SANS"{sc} size="{size:.3f}" spacing="1.12" '
        f'justify=\'"{just}" "MIDDLE"\'/></Text></Shape></Transform>')
    return "".join(out)


def callout_stack(items, face_x, side, x_label, y_top, y_bot, z, size=0.4,
                  leadcolor="0.5 0.5 0.55"):
    """Lay labels evenly between y_top..y_bot on one side, each with an elbow
    leader back to its TRUE depth on the column face. side=-1 left, +1 right.
    items: list of (true_y, lines, color, style)."""
    out = []
    items = sorted(items, key=lambda t: -t[0])
    n = len(items)
    for k, (ty, lines, color, style) in enumerate(items):
        ly = y_top + (y_bot - y_top) * (k / (n - 1) if n > 1 else 0)
        elbow = face_x + side * 1.0
        out.append(lineset([(face_x, ty, z), (elbow, ty, z),
                            (x_label - side * 0.4, ly, z)], leadcolor,
                           idx="0 1 2 -1"))
        just = "END" if side < 0 else "BEGIN"
        sc = f' style="{style}"' if style else ""   # FontStyle.style is SFString
        strs = " ".join(f'"{esc(l)}"' for l in lines)
        yoff = (len(lines) - 1) * size * 1.15 / 2
        out.append(
            f'<Transform translation="{x_label:.3f} {ly + yoff:.3f} {z:.3f}">'
            f'<Shape><Appearance><Material diffuseColor="{color}"/></Appearance>'
            f'<Text string=\'{strs}\' solid="false">'
            f'<FontStyle family="SANS"{sc} size="{size:.3f}" spacing="1.15" '
            f'justify=\'"{just}" "BEGIN"\'/></Text></Shape></Transform>')
    return "".join(out)


# -------------------------------------------------- hero from a traced drawing
def polylines_of(svg):
    raw = open(svg).read()
    m = re.search(r'transform="translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)"', raw)
    tx, ty, sx, sy = (tuple(float(g) for g in m.groups()) if m else (0., 0., 1., 1.))
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
                n = 2 if seg.__class__.__name__ == "Line" else 7
                for i in range(n):
                    t = i / (n - 1) if n > 1 else 0.
                    p = seg.point(t)
                    pts.append((tx + sx * p.real, ty + sy * p.imag))
            if len(pts) >= 2:
                out.append(pts)
    return out


def hero_panel(svg, real_len_ft, cx, cz, baseline_y, color):
    """Stand a traced skeletal drawing upright at life scale, baseline on y=baseline_y,
    centred at cx. Returns (x3d, width_ft, height_ft)."""
    pls = polylines_of(svg)
    xs = [x for pl in pls for x, _ in pl]
    ys = [y for pl in pls for _, y in pl]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    fpp = real_len_ft / (maxx - minx or 1.)
    w_ft, h_ft = (maxx - minx) * fpp, (maxy - miny) * fpp
    midx = (minx + maxx) / 2
    coords, index, i = [], [], 0
    for pl in pls:
        idx = []
        for x, y in pl:
            X = cx + (x - midx) * fpp
            Y = baseline_y + (maxy - y) * fpp     # page-up → +Y, baseline at maxy
            coords.append(f"{X:.3f} {Y:.3f} {cz:.3f}")
            idx.append(str(i))
            i += 1
        index.append(" ".join(idx) + " -1")
    coord = " ".join(coords)
    shape = (f'<Shape><Appearance><Material emissiveColor="{color}"/></Appearance>'
             f'<IndexedLineSet coordIndex="{" ".join(index)}">'
             f'<Coordinate point="{coord}"/></IndexedLineSet></Shape>')
    return shape, w_ft, h_ft


# ============================================================ build the scene
parts = []
COLW, COLD = 10.0, 7.0          # Potter Creek column width / depth (ft)
FACE = COLD / 2                 # front face z
PC_X = 0.0

# ---- Potter Creek documented column (top-down, depths below surface) -------
pc = SPEC["potter_creek_column"]
parts.append("<!-- DOCUMENTED: Sinclair 1904 NW-fan stratigraphic column -->")
for lyr in pc:
    top_y = -lyr["top_ft"]
    bot_y = -lyr["bottom_ft"]
    parts.append(slab(PC_X, 0, COLW, COLD, top_y, bot_y, lyr["color_hint"]))
    # layer label to the RIGHT of the column face
    mid = (top_y + bot_y) / 2
    letter = lyr["name"].split("—")[0].strip().split()[0]
    lith = lyr["name"].split("—")[-1].strip()
    th = lyr["bottom_ft"] - lyr["top_ft"]
    barren = ("ash" in lith.lower() or "H —" in lyr["name"]
              or lyr["name"].startswith("H"))
    short = lyr["name"].split("(")[0].strip()
    parts.append(multitext(
        PC_X + COLW / 2 + 0.6, mid + 0.3, FACE,
        [short,
         f"{lyr['top_ft']:.1f}–{lyr['bottom_ft']:.1f} ft"
         + ("   · BARREN (no bones)" if not lyr["bone_bearing"] else "")],
        0.46, DOC if lyr["bone_bearing"] else DOC_FAINT))

pc_base = -pc[-1]["bottom_ft"]
# bedrock line under H
parts.append(text(PC_X + COLW / 2 + 0.6, pc_base - 0.7, FACE,
                  "McCloud limestone bedrock (Carboniferous)", 0.4, DOC_FAINT,
                  style="ITALIC", justify="BEGIN"))

# ---- the ONE honest faunal statement: bone-bearing bracket (left) ----------
# bone-bearing = A..G minus C(ash); spans 0.1 .. 31 ft. A bracket + Sinclair's
# own refusal to differentiate the fauna by layer.
br_x = PC_X - COLW / 2 - 1.0
br_top, br_bot = -0.1, -31.0
parts.append(lineset([(br_x, br_top, FACE), (br_x - 0.5, br_top, FACE),
                      (br_x - 0.5, br_bot, FACE), (br_x, br_bot, FACE)], PIN,
                     idx="0 1 2 3 -1"))
parts.append(multitext(
    br_x - 0.9, (br_top + br_bot) / 2 + 2.3, FACE,
    ["BONE-BEARING — the fauna occur THROUGHOUT the",
     "clay & cemented breccia (strata A, B, D, E, F, G):",
     "a mixed, time-averaged talus / pitfall assemblage.",
     "",
     "“No distinction is to be drawn between the",
     "collections from the different layers …",
     "the fauna listed is a unit.”",
     "        — Sinclair 1904, p. 19   (52 species, 21 extinct)",
     "",
     "So NO taxon is pinned to a layer. Volcanic ash (C)",
     "and the chocolate-mud lens are the only barren beds."],
    0.46, DOC, justify="END"))

# ---- documented depth-anchored facts as an even right-side callout stack ----
# Only facts the literature gives an actual depth/level for. Evenly spaced on the
# right with leaders back to the true depth, so the clustered shallow finds read.
facts = [  # (true_depth_y_ft, lines)
    (-0.1,  ["SURFACE — Arctotherium (partial skull) + Ursus,",
             "among loose rock on the SE-fan surface.",
             "(Sinclair 1904, p. 11)"]),
    (-0.25, ["TOP 15–30 cm — dark cultural midden: basalt &",
             "obsidian tools and an atlatl / dart-shaft cache,",
             "~1900–2010 ¹⁴C BP (≈ 1st c. AD). (Payen & Taylor 1976)"]),
    (-1.0,  ["6–18 in — a chipped flake with charcoal,",
             "Euceratherium & mammoth teeth; the charcoal redates",
             "to 1910 BP — late Holocene, NOT Pleistocene."]),
    (-5.58, ["170 cm (5.6 ft) — Euceratherium collinum radius +",
             "ulna in hard breccia: 8250±330 ¹⁴C BP (UCR-381),",
             "first direct date on the species. (Payen & Taylor 1976)"]),
    (-7.9,  ["80–140 in — polished / bevelled bone pieces.",
             "Depths documented; HUMAN origin NOT established —",
             "carnivore-gnawed + water-worn. (Sinclair; P&T 1976)"]),
    (-14.25, ["gravel B — articulated squirrels, wood-rats, a",
              "snake (Crotalus) & a bat: a layer-level occurrence,",
              "not a measured depth. (Sinclair 1904, p. 11)"]),
]
cs_x = PC_X + COLW / 2 + 9.5            # callout label anchor x
face_r = PC_X + COLW / 2
parts.append(callout_stack(
    [(ty, lines, DOC, "") for ty, lines in facts],
    face_r, +1, cs_x, -1.0, -20.0, FACE, size=0.42))

# ---- INTERPRETIVE hero: the Shasta ground sloth, beside the column ----------
hero_cx = PC_X - COLW / 2 - 17.0
hero, hw, hh = hero_panel("drawings/fauna/nothrotheriops_skeleton.svg", 9.0,
                          hero_cx, FACE, 0.2, INTERP)
parts.append("<!-- INTERPRETIVE: real traced skeleton, stood as context only -->")
parts.append(hero)
parts.append(lineset([(hero_cx - hw / 2 - 1, 0, FACE),
                      (hero_cx + hw / 2 + 1, 0, FACE)], "0.6 0.55 0.5"))
parts.append(multitext(
    hero_cx, -1.1, FACE,
    ["Shasta ground sloth  Nothrotheriops shastensis",
     "— INTERPRETIVE, context only —",
     "the real skeletal drawing (Stock 1925) stood at life",
     "size (2.75 m). It is in Potter Creek’s 52-species list",
     "but is UNPROVENANCED: no recorded layer or depth.",
     "Shown beside the column, never embedded in a stratum."],
    0.45, INTERP, style="ITALIC", justify="MIDDLE"))

# ---- titles + provenance legend -------------------------------------------
parts.append(text(PC_X, 2.5, FACE,
                  "POTTER CREEK CAVE — documented deposit & mixed fauna",
                  0.66, DOC))
parts.append(text(PC_X, 3.8, FACE,
                  "depths in feet below the deposit surface", 0.42, DOC_FAINT,
                  style="ITALIC"))
parts.append(text((PC_X + hero_cx) / 2, 6.0, FACE,
                  "Bone horizons & an interpretive hero",
                  0.85, "0.15 0.15 0.2", fam="SERIF"))
# provenance legend, set below the column
leg_y = pc_base - 2.2
parts.append(multitext(
    PC_X - COLW / 2 - 2, leg_y, FACE,
    ["PROVENANCE KEY — black = DOCUMENTED (Sinclair 1904; Payen & Taylor 1976);"
     "   rust italic = INTERPRETIVE (the posed sloth);   grey = documented but barren/context.",
     "Thicknesses are Sinclair’s “greatest” values that pinch laterally, so the stacked depths are a"
     " render composite, not additive measured depths — and stratum G’s base was “not determined.”",
     "Companion: the Samwel column (samwel_strata.x3d) carries the one per-specimen dated-level dataset."],
    0.4, DOC, justify="BEGIN"))

# ---------------------------------------------------------------- assemble
# fit the whole composition to the 1200x780 render frame (fit BOTH axes).
left = hero_cx - hw / 2 - 3
right = cs_x + 14
top = 6.8
bot = leg_y - 2.2
FOV = 0.66
ASPECT = 1200 / 780
cam_x = (left + right) / 2
cam_y = (top + bot) / 2
half = max((right - left) / 2 / ASPECT, (top - bot) / 2)
cam_z = FACE + half / math.tan(FOV / 2) * 1.08

x3d = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0">
<head>
<meta name="title" content="Potter Creek &amp; Samwel Caves -- documented deposit, mixed fauna, interpretive hero"/>
<meta name="description" content="The Sinclair 1904 Potter Creek stratigraphic column and the Feranec 2007 Samwel column, with fauna pinned ONLY where the literature documents a depth. Potter Creek fauna are a mixed undifferentiated assemblage (Sinclair p.19); the Shasta ground-sloth skeleton stands beside the column as flagged-unprovenanced context. No invented depths."/>
<meta name="source" content="Sinclair 1904 (Potter Creek column + faunal unit); Payen &amp; Taylor 1976 (Euceratherium 170 cm date, refuted bone tools); Feranec et al. 2007 (Samwel dated levels). Hero drawing: Stock 1925. All public domain."/>
<meta name="rights" content="Traces/derivations of public-domain sources; documented vs interpretive kept distinct; no AI imagery, no invented geometry."/>
</head>
<Scene>
<Background skyColor="0.96 0.96 0.94"/>
<NavigationInfo type='"EXAMINE" "ANY"'/>
<Viewpoint description="Section panel" position="{cam_x:.2f} {cam_y:.2f} {cam_z:.1f}" centerOfRotation="{cam_x:.2f} {cam_y:.2f} 0" fieldOfView="0.66"/>
{chr(10).join(parts)}
</Scene>
</X3D>
"""
open(OUT, "w").write(x3d)
print(f"wrote {OUT}: PC column {len(pc)} layers (to {pc_base:.1f} ft), "
      f"{len(facts)} depth callouts, hero {hw:.1f}x{hh:.1f} ft")


# ===========================================================================
# COMPANION SCENE: Samwel Cave -- the one per-specimen dated-level dataset.
# Feranec et al. (2007): four Chamber-Two specimens carry REAL square+inch
# levels AND AMS dates -- but the deposit is NOT stratified, so depth != age
# (the shallower Lepus is OLDER than the deeper Aplodontia). The named lithic
# units and the dated specimens are NOT correlated in the source, so the dates
# are pinned by their excavation depth only, beside (not inside) the column.
# ===========================================================================
sam = SPEC["samwel_column"]
SOUT = "samwel_strata.x3d"
sp = []
SX, SW, SD = 0.0, 6.0, 4.0
SFACE = SD / 2
sp.append("<!-- DOCUMENTED: Feranec et al. 2007 Chamber-Two column (cm) -->")
sam_layer_items = []
for lyr in sam:
    ty = -lyr["top_cm"] / CM_PER_FT
    by = -lyr["bottom_cm"] / CM_PER_FT
    sp.append(slab(SX, 0, SW, SD, ty, by, lyr["color_hint"]))
    sam_layer_items.append((
        (ty + by) / 2,
        [f"{lyr['name']}  ({lyr['top_cm']:.0f}–{lyr['bottom_cm']:.0f} cm)"
         + ("" if lyr["bone_bearing"] else "  · cap")],
        DOC if lyr["bone_bearing"] else DOC_FAINT, ""))
sam_base = -sam[-1]["bottom_cm"] / CM_PER_FT
# layer labels as an even right-side callout stack (the thin caps would collide)
sp.append(callout_stack(sam_layer_items, SX + SW / 2, +1, SX + SW / 2 + 3.0,
                        -0.2, sam_base + 0.2, SFACE, size=0.34))

# the four dated specimens, by their real square + inch level (left callouts)
sam_dates = [  # (depth_cm, lines, invert_flag)
    (30.5, ["Rodentia phalanx — Chamber Two, Sec. 4, 12 in",
            "16,110 ± 130 ¹⁴C BP  (17,100–17,500 cal BC)"], False),
    (50.8, ["Lepus washingtonii jaw — Sec. 5, 20 in",
            "19,960 ± 210 ¹⁴C BP  (21,300–22,500 cal BC)",
            "← shallower, yet the OLDEST date: depth ≠ age"], True),
    (76.2, ["Aplodontia femur — Sec. 4, 30 in",
            "16,240 ± 150 ¹⁴C BP  (17,100–17,850 cal BC)"], False),
    (91.4, ["Mammalia bone — Sec. 3, 36 in",
            "20,770 ± 240 ¹⁴C BP  (22,300–23,600 cal BC)"], False),
]
sface_l = SX - SW / 2
sp.append(callout_stack(
    [(-cm / CM_PER_FT, lines, INTERP if inv else DOC, "ITALIC" if inv else "")
     for cm, lines, inv in sam_dates],
    sface_l, -1, sface_l - 3.0, -0.6, sam_base + 0.2, SFACE, size=0.36))

# the Euceratherium jaw has NO level ('na') -- shown floating, explicitly so
sp.append(multitext(
    SX + SW / 2 + 0.5, sam_base - 1.0, SFACE,
    ["Euceratherium sp. jaw (UCMP 9128): 16,310 ± 100 ¹⁴C BP —",
     "level recorded “na”, so NOT pinned to any depth here."],
    0.34, DOC_FAINT, style="ITALIC"))

sp.append(text(SX, 1.4, SFACE, "SAMWEL CAVE — Chamber Two", 0.5, DOC))
sp.append(text(SX, 2.4, SFACE,
               "the one Merriam-caves dataset with per-specimen depths",
               0.34, DOC_FAINT, style="ITALIC"))
sp.append(text(SX, 4.0, SFACE, "Depth is not age", 0.7,
               "0.15 0.15 0.2", fam="SERIF"))
sp.append(multitext(
    sface_l - 1.0, sam_base - 2.4, SFACE,
    ["Four Chamber-Two specimens (Feranec et al. 2007, Table 2) carry real",
     "square + inch excavation levels — but the fill is NOT chronologically",
     "stratified: the shallower Lepus (50.8 cm) is older than the deeper",
     "Aplodontia (76.2 cm). “The data currently do not support stratified",
     "deposition” (p. 119). Depths are excavation tags only; the source does",
     "NOT map specimens to the named lithic units. Ages are cal BC, not cal BP;",
     "all five fall within the Last Glacial Maximum.   Depths in cm below datum."],
    0.34, DOC, justify="END"))

# fit
s_left = sface_l - 19
s_right = SX + SW / 2 + 17
s_top = 4.7
s_bot = sam_base - 4.8
scam_x = (s_left + s_right) / 2
scam_y = (s_top + s_bot) / 2
shalf = max((s_right - s_left) / 2 / ASPECT, (s_top - s_bot) / 2)
scam_z = SFACE + shalf / math.tan(FOV / 2) * 1.08

sx3d = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0">
<head>
<meta name="title" content="Samwel Cave -- per-specimen dated levels (depth != age)"/>
<meta name="description" content="The Feranec et al. 2007 Chamber-Two column with the four AMS-dated specimens at their documented square+inch levels. The deposit is not chronologically stratified -- a shallower specimen (Lepus) is older than a deeper one (Aplodontia) -- so depth is an excavation tag, not an age order. The Euceratherium jaw has no recorded level and floats. No invented correlations."/>
<meta name="source" content="Feranec, Hadly, Blois, Barnosky &amp; Paytan (2007) Radiocarbon 49(1):117-121. Public domain context; figures/data cited."/>
<meta name="rights" content="Derived from a cited source; documented vs interpretive kept distinct; no AI imagery."/>
</head>
<Scene>
<Background skyColor="0.96 0.96 0.94"/>
<NavigationInfo type='"EXAMINE" "ANY"'/>
<Viewpoint description="Samwel levels" position="{scam_x:.2f} {scam_y:.2f} {scam_z:.1f}" centerOfRotation="{scam_x:.2f} {scam_y:.2f} 0" fieldOfView="0.66"/>
{chr(10).join(sp)}
</Scene>
</X3D>
"""
open(SOUT, "w").write(sx3d)
print(f"wrote {SOUT}: Samwel column {len(sam)} layers (to {sam_base:.1f} ft), "
      f"{len(sam_dates)} dated levels")
