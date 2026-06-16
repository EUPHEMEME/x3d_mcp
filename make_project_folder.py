#!/usr/bin/env python3
"""Assemble a clean, browsable folder of EVERYTHING this project has produced --
so a human can open one place and see the whole thing without the dev clutter
(node_modules, ML scratch, source tree).

Builds  ./Shasta_X3D_Project/  with:
  index.html        a dark gallery linking every render, drawing, paper & tool
  README.md         orientation
  images/           rendered PNGs of every 3-D scene + the survey/fauna sheets
  scenes/           the .x3d models + their X_ITE viewer pages
  drawings/         the faithful vector traces (SVG) + B&W sheets (PDF)
  papers/           the write-ups (PDF)
  generators/       the Python/shell that builds it all

Re-run any time:  python make_project_folder.py
Live 3-D needs the local server (./start_caves.sh); the PNGs here are static.
"""
import os
import shutil
import html

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "Shasta_X3D_Project")
RENDERS = "/tmp/exp_renders"          # freshly rendered scene PNGs
FIG = os.path.join(ROOT, "docs/paper/figures")
DRW = os.path.join(ROOT, "drawings")


def cp(src, dst_dir, rename=None):
    if not os.path.exists(src):
        return None
    os.makedirs(dst_dir, exist_ok=True)
    name = rename or os.path.basename(src)
    shutil.copyfile(src, os.path.join(dst_dir, name))
    return name


# ---- reset output ----------------------------------------------------------
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
for sub in ("images", "scenes", "drawings", "papers", "generators"):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)

# ---- gallery model: sections of cards -------------------------------------
# each card = (image_src, title, caption, link)  link relative to OUT
SECTIONS = []

# 1 — the immersive caves
caves = []
for img, x3d, viewer, title, cap in [
    (f"{RENDERS}/potter_creek_cave_xite.png", "potter_creek_cave.x3d",
     "potter_creek_cave_xite.html", "Potter Creek Cave — longitudinal section",
     "The 107 ft chamber as a cut-away, to Sinclair's (1904) measurements: domed "
     "roof, two coalescing breccia fans, chimneys, the 42 ft entrance pit. PBR "
     "limestone; speleothems flagged interpretive."),
    (f"{ROOT}/docs/paper/figures/pcc_hero.png", None, None,
     "Potter Creek Cave — hero view",
     "Down the great pit: god-ray, dripstone, pools — a living cave whose geometry "
     "stays faithful to the survey."),
    (f"{RENDERS}/samwel_cave_xite.png", "samwel_cave.x3d", "samwel_cave_xite.html",
     "Samwel Cave — labelled section",
     "The branching two-level system after Furlong (1906) / Feranec (2007): "
     "Pleistocene Hall, Chamber One, Merriam's Chamber, the deep drop."),
    (f"{ROOT}/docs/paper/figures/samwel_hero.png", None, None,
     "Samwel Cave — the descent & the Magic Pool",
     "The ~90 ft hole of legend joining the upper level to Chamber Two and its "
     "glowing sacred pool."),
]:
    caves.append((img, x3d, viewer, title, cap))
SECTIONS.append(("The caves — immersive reconstructions",
                 "Two Shasta County fossil caves the user's forebear John C. "
                 "Merriam excavated (1903–06), rebuilt to scale in standards "
                 "X3D 4.0 with PBR materials. Documented geometry vs. interpretive "
                 "dressing is labelled in every scene.", caves))

# 2 — the documented 3-D archive
arch = [
    (f"{RENDERS}/potter_creek_plan_xite.png", "potter_creek_plan.x3d",
     "potter_creek_plan_xite.html", "Documented plan (Plate 14, to scale)",
     "Sinclair's contour map of the chamber floor, traced identically and lifted "
     "to a to-scale X3D IndexedLineSet — the model IS the survey."),
    (f"{RENDERS}/potter_creek_floor_xite.png", "potter_creek_floor.x3d",
     "potter_creek_floor_xite.html", "3-D floor topography (derived)",
     "The floor extruded from the documented 6-inch contours: basins sink, "
     "stalagmite bosses rise (8× vertical exaggeration)."),
    (f"{DRW}/cave_drawings_sheet.png", None, None, "Survey drawings — B&W sheet",
     "Every published plate traced to clean vector: Potter Creek plan & sections "
     "(Sinclair 1904), Samwel cross-section (Feranec 2007)."),
]
SECTIONS.append(("The documented 3-D archive",
                 "Each item is a faithful vector trace of a real published drawing, "
                 "fully cited — no AI imagery, no invented geometry. "
                 "(trace_drawing.sh → svg_to_x3d.py / extrude_contours.py.)", arch))

# 3 — the excavated fauna
fauna = [
    (f"{RENDERS}/fauna_plate_xite.png", "fauna_plate.x3d", "fauna_plate_xite.html",
     "Fauna plate — 3-D archive gallery",
     "The Shasta ground sloth (Stock 1925), dire-wolf skull (Merriam 1912) and "
     "Euceratherium dental series (Sinclair & Furlong 1904) as to-scale traces."),
    (f"{DRW}/fauna_sheet.png", None, None, "Fauna drawings — B&W sheet",
     "Faithful traces of the original anatomical drawings; Arctodus omitted "
     "(photo-only, no line drawing exists). No AI imagery."),
]
SECTIONS.append(("The excavated fauna — real anatomical drawings",
                 "The megafauna traced from their ORIGINAL published drawings, "
                 "never from AI imagery, each carrying its full citation.", fauna))

# 4 — bone horizons (the hybrid)
bone = [
    (f"{RENDERS}/potter_creek_strata_xite.png", "potter_creek_strata.x3d",
     "potter_creek_strata_xite.html", "Potter Creek — bone horizons & hero",
     "Sinclair's column (S–H) with fauna pinned ONLY at documented depths "
     "(Euceratherium at 170 cm; polished bone with human origin refuted). The "
     "sloth stands beside it, flagged interpretive & unprovenanced."),
    (f"{RENDERS}/samwel_strata_xite.png", "samwel_strata.x3d",
     "samwel_strata_xite.html", "Samwel — depth is not age",
     "The four AMS-dated Chamber-Two specimens at their real square+inch levels "
     "(Feranec 2007): the shallower Lepus is older than the deeper Aplodontia."),
]
SECTIONS.append(("Bone horizons — the deposit & its fauna",
                 "The hardest place to stay honest: the join between deposit and "
                 "fauna. Taxa are pinned only where the literature records a depth; "
                 "the mixed assemblage is shown as Sinclair himself described it — "
                 "“the fauna listed is a unit.”", bone))

# 5 — the wider program (characters, creatures, the MCP toolchain)
prog = [
    (f"{FIG}/fig_canonical_skeleton.png", None, None, "HAnim LOA-5 skeleton",
     "A standards-conformant Humanoid Animation skeleton — the articulation target "
     "for rigged characters."),
    (f"{FIG}/fig_runner_xite_course.png", None, None, "Rigged runner (X_ITE)",
     "An animated HAnim runner on a course — the classroom demo built on the same "
     "pipeline."),
    (f"{FIG}/fig_pbr_torso.png", None, None, "PBR character lookdev",
     "PhysicalMaterial (metallic-roughness) skin — the material model X_ITE renders "
     "and X3DOM cannot."),
    (f"{FIG}/fig_flux_blackboard.png", None, None, "mflux → X3D reference pipeline",
     "Locally-generated image references driving model + lookdev toward rigged, "
     "animated creatures (the moose pipeline)."),
    (f"{FIG}/x3dom_vs_xite.png", None, None, "Why the renderer is a correctness property",
     "Same scene: X3DOM draws nothing under headless software WebGL; X_ITE renders "
     "PBR + HAnim. An agent must see what it makes."),
]
SECTIONS.append(("The wider program — characters & the X3D toolchain",
                 "The caves are the flagship application of a broader effort: "
                 "AI-assisted authoring of standards-conformant, provenance-"
                 "disciplined 3-D — a reusable MCP toolchain, a creature/character "
                 "pipeline, and contributions back to the Web3D toolchain.", prog))

# ---- copy images & build cards --------------------------------------------
def slug(s):
    return "".join(c if c.isalnum() else "_" for c in s.lower())[:48]


cards_html = []
for title, blurb, cards in SECTIONS:
    rows = []
    for i, (img, x3d, viewer, ctitle, cap) in enumerate(cards):
        imgname = cp(img, os.path.join(OUT, "images"),
                     rename=f"{slug(ctitle)}.png") if img else None
        if x3d:
            cp(os.path.join(ROOT, x3d), os.path.join(OUT, "scenes"))
        if viewer:
            cp(os.path.join(ROOT, viewer), os.path.join(OUT, "scenes"))
        link = f"images/{imgname}" if imgname else "#"
        imgtag = (f'<img src="images/{imgname}" alt="{html.escape(ctitle)}">'
                  if imgname else '<div class="noimg">—</div>')
        rows.append(
            f'<a class="card" href="{link}" target="_blank">{imgtag}'
            f'<div class="cap"><b>{html.escape(ctitle)}</b>'
            f'<span>{html.escape(cap)}</span></div></a>')
    cards_html.append(
        f'<h2>{html.escape(title)}</h2><p class="blurb">{html.escape(blurb)}</p>'
        f'<div class="grid">{"".join(rows)}</div>')

# ---- papers & generators ---------------------------------------------------
papers = [
    ("merriam-caves.pdf", "Potter Creek & Samwel Caves — the heritage 3-D archive",
     "The caves write-up (provenance discipline, the render loop, the fauna & "
     "bone-horizon work). NOTE: being superseded by a broader vision paper."),
    ("x3d-mcp-hanim-demo.pdf", "AI-aided X3D authoring — the HAnim classroom demo",
     "The companion paper on the MCP toolchain and the rigged-skeleton classroom "
     "demo."),
    ("visual-changelog.pdf", "Visual changelog",
     "A picture history of the build."),
]
paper_rows = []
for fn, t, c in papers:
    got = cp(os.path.join(ROOT, "docs/paper", fn), os.path.join(OUT, "papers"))
    if got:
        paper_rows.append(
            f'<a class="card paper" href="papers/{fn}" target="_blank">'
            f'<div class="cap"><b>📄 {html.escape(t)}</b>'
            f'<span>{html.escape(c)}</span></div></a>')
paper_html = ('<h2>Papers</h2><p class="blurb">The write-ups (PDF).</p>'
              f'<div class="grid">{"".join(paper_rows)}</div>')

# drawings (svg traces) + generators copied wholesale
for f in os.listdir(DRW):
    if f.endswith(".svg") or f.endswith("_sheet.pdf"):
        cp(os.path.join(DRW, f), os.path.join(OUT, "drawings"))
faunadir = os.path.join(DRW, "fauna")
if os.path.isdir(faunadir):
    for f in os.listdir(faunadir):
        if f.endswith(".svg"):
            cp(os.path.join(faunadir, f), os.path.join(OUT, "drawings"))

GENS = ["generate_cave.py", "generate_cave_textures.py", "generate_samwel.py",
        "trace_drawing.sh", "svg_to_x3d.py", "extrude_contours.py",
        "fauna_to_x3d.py", "generate_fauna_strata.py", "generate_runner.py",
        "generate_classroom.py", "scrape_session.py", "make_project_folder.py"]
gen_items = []
for g in GENS:
    got = cp(os.path.join(ROOT, g), os.path.join(OUT, "generators"))
    if got:
        gen_items.append(f"<li><code>{html.escape(g)}</code></li>")
gen_html = ('<h2>How it is made — generators</h2>'
            '<p class="blurb">Every scene is procedural and reproducible; every '
            'drawing is a faithful trace. Sources in <code>generators/</code>.</p>'
            f'<ul class="gens">{"".join(gen_items)}</ul>')

# ---- index.html ------------------------------------------------------------
INDEX = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Potter Creek &amp; Samwel Caves — an X3D heritage archive</title>
<style>
 :root{{color-scheme:dark}}
 html,body{{margin:0;background:#0e0f12;color:#d7d2c6;
   font-family:-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.5}}
 .wrap{{max-width:1180px;margin:0 auto;padding:40px 24px 90px}}
 h1{{font-size:30px;margin:0 0 6px;color:#f1e9d6;font-weight:680;letter-spacing:.2px}}
 .lede{{font-size:15.5px;opacity:.82;max-width:860px;margin:0 0 6px}}
 .meta{{font-size:12.5px;opacity:.5;margin-bottom:18px}}
 h2{{font-size:21px;color:#ece0c4;font-weight:620;margin:42px 0 2px}}
 .blurb{{font-size:13.5px;opacity:.72;max-width:880px;margin:2px 0 4px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
   gap:16px;margin-top:14px}}
 .card{{display:block;background:#16171c;border:1px solid #25272f;border-radius:11px;
   overflow:hidden;text-decoration:none;color:inherit;transition:border-color .15s,transform .15s}}
 .card:hover{{border-color:#4a4f5e;transform:translateY(-2px)}}
 .card img{{width:100%;display:block;aspect-ratio:16/10;object-fit:cover;background:#fff}}
 .noimg{{aspect-ratio:16/10;display:flex;align-items:center;justify-content:center;color:#444}}
 .cap{{padding:11px 14px 14px}}
 .cap b{{color:#f1e9d6;font-size:14px;display:block;margin-bottom:3px}}
 .cap span{{font-size:12.5px;opacity:.68}}
 .card.paper{{background:#1a1620}}
 ul.gens{{columns:2;font-size:13px;opacity:.85;margin-top:12px}}
 ul.gens code{{background:#1c1e25;padding:1px 6px;border-radius:4px}}
 .note{{margin-top:40px;font-size:12.5px;opacity:.6;border-top:1px solid #25272f;padding-top:16px;line-height:1.7}}
 code{{background:#1c1e25;padding:1px 6px;border-radius:4px}}
</style></head><body><div class="wrap">
 <h1>Potter Creek &amp; Samwel Caves — an X3D heritage archive</h1>
 <p class="lede">Two Pleistocene fossil caves that John C. Merriam opened a hundred
  and twenty years ago, rebuilt as honest, inspectable, standards-conformant 3-D —
  and the wider effort it belongs to: AI-assisted authoring of provenance-disciplined
  X3D, from a reusable toolchain to a character pipeline to this archive.</p>
 <p class="meta">Everything here is procedural or a faithful trace of a public-domain
  drawing — no AI imagery, no invented geometry. Click any tile for the full render.
  Live 3-D viewers (the <code>scenes/</code> folder) need the local server
  (<code>./start_caves.sh</code>); the images here are static captures.</p>
 {''.join(cards_html)}
 {paper_html}
 {gen_html}
 <p class="note">Built by a human and Claude (Claude Code) working as a pair, entirely
  through the open Web3D toolchain. Both caves are Winnemem Wintu sacred sites on the
  flooded McCloud River, treated with care, not as scenery. — assembled by
  <code>make_project_folder.py</code>.</p>
</div></body></html>
"""
open(os.path.join(OUT, "index.html"), "w").write(INDEX)

README = """# Potter Creek & Samwel Caves — X3D heritage archive (project folder)

Open **index.html** in a browser to see everything.

- `images/`     — rendered captures of every 3-D scene + the B&W drawing/fauna sheets
- `scenes/`     — the X3D models (.x3d) and their X_ITE viewer pages
- `drawings/`   — the faithful vector traces (SVG) of the published survey & fauna drawings
- `papers/`     — the write-ups (PDF)
- `generators/` — the Python/shell that builds it all (every scene is reproducible)

The static PNGs open anywhere. The live, navigable 3-D viewers need a local web
server (X_ITE fetches the .x3d by HTTP); in the source repo run `./start_caves.sh`.

No AI imagery and no invented geometry: every scene is procedural and to scale, and
every drawing is a faithful trace of a public-domain original, fully cited.
"""
open(os.path.join(OUT, "README.md"), "w").write(README)

# ---- report ----------------------------------------------------------------
nimg = len(os.listdir(os.path.join(OUT, "images")))
nsc = len(os.listdir(os.path.join(OUT, "scenes")))
ndr = len(os.listdir(os.path.join(OUT, "drawings")))
npa = len(os.listdir(os.path.join(OUT, "papers")))
ng = len(os.listdir(os.path.join(OUT, "generators")))
print(f"built {OUT}")
print(f"  images:{nimg}  scenes:{nsc}  drawings:{ndr}  papers:{npa}  generators:{ng}")
