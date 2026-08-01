#!/usr/bin/env python3
"""
build_gallery.py -- a local page for exploring the still-life outputs
================================================================================
VERSION 1 · 2026-07-30 · EUPHEME Technologies LLC

    python3 build_gallery.py   ->   gallery.html   (open it directly, file://)

Reads what is actually on disk -- the renders, the shipped .x3d provenance, the
failure-mode notes -- rather than a hand-maintained list, so re-running it after
another look-dev pass picks the new work up. Regenerable, not a snapshot.
"""

import glob
import html
import json
import os
import re

VERSION = "1"
HERE = os.path.dirname(os.path.abspath(__file__))

SCENES = [
    ("pronk", "Willem Claesz Heda", "Still Life with a Gilt Cup", "1635",
     "Rijksmuseum, Amsterdam"),
    ("trompe", "Cornelis Norbertus Gijsbrechts", "Trompe l'oeil. Board Partition "
     "with Letter Rack and Music Book", "1668", "SMK, Copenhagen"),
    ("antiquity", "Unknown Pompeian painter (Fourth Style)", "Still Life with Glass "
     "Bowl of Fruit and Vases", "c. AD 62–79", "MANN, Naples"),
]

# look-dev progressions, newest last. Only entries whose file exists are shown.
PROGRESS = {
    "pronk": [("v12", "renders/pronk_sheet.png", "first build — poster-green cloth, "
               "clipped linen, objects floating"),
              ("v13", "renders/pronk_v13_sheet.png", "palette desaturated toward Heda's "
               "tonal range; gilt left as the only saturated element"),
              ("v14", "renders/pronk_v14_sheet.png", "contact occlusion baked and "
               "widened — the objects finally sit on the table")],
    "antiquity": [(f"r{i}", f"renders/antiquity_r{i}_sheet.png", "") for i in (1, 2, 3, 4)]
                 + [("v3 final", "renders/antiquity_final_sheet.png",
                     "v3: objects spread across the room like a product shot — "
                     "the round that prompted the recomposition"),
                    ("a1", "renders/antiquity_a1_sheet.png",
                     "v4 recompose to the fresco's measured panel-space table; the "
                     "fictive maroon border built as a real cropping proscenium; "
                     "ledge-height frontal camera, bowl tilted to open the rim"),
                    ("a3", "renders/antiquity_a3_sheet.png",
                     "the painter's glass devices land: drawn rim ellipses, darkened "
                     "interior fruit, the grape bunch re-massed over the rim, the "
                     "pomegranate split turned to the light"),
                    ("a8 — final", "renders/antiquity_a8_sheet.png",
                     "grounded: squashed-ellipsoid shadow tongues that survive the "
                     "near-grazing camera, one-lathe amphora with plugged mouth, "
                     "tonal key pulled to the fresco's measured mid-key (panel mean "
                     "104 vs measured 116, p5 68 vs 70)")],
    "trompe": [("v6", "renders/trompe_sheet.png", "pre-recompose: objects spread "
                "across the board, flat daylight, vertical curtain"),
               ("a1", "renders/trompe_a1_sheet.png", "recompose to the painting's "
                "measured construction — surround too bright, curtain edge blazing"),
               ("a2", "renders/trompe_a2_sheet.png", "black surround + low key land; "
                "letters still confetti, rosette a loose pile"),
               ("a3", "renders/trompe_a3_sheet.png", "letters anchored to the tape "
                "grid, rosette fanned, pendant clear of the book"),
               ("a4", "renders/trompe_a4_sheet.png", "vermilion deepened, wax sticks "
                "separated from the tape red, far folds added"),
               ("final", "renders/trompe_a5_sheet.png", "crimson velvet reads; "
                "shipped state")],
}


def provenance(key):
    p = os.path.join(HERE, "scenes", f"{key}.x3d")
    if not os.path.exists(p):
        return {}
    s = open(p, encoding="utf-8", errors="replace").read()
    d = {}
    for q in ("'", '"'):
        o = '"' if q == "'" else "'"
        for m in re.finditer(rf"<MetadataString[^>]*name={q}([^{q}]+){q}[^>]*"
                             rf"value={q}{o}?(.*?){o}?{q}\s*/>", s):
            d.setdefault(m.group(1), html.unescape(m.group(2)))
    return d


def exists(rel):
    return os.path.exists(os.path.join(HERE, rel))


CSS = """
:root{--bg:#0e0e10;--panel:#16161a;--line:#2a2a30;--ink:#e8e6e1;--dim:#9b978f;
      --gilt:#c8963e;--flag:#b8564a;--ok:#5c8f6e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:15px/1.6 "Iowan Old Style",Palatino,Georgia,serif}
header{padding:44px 40px 26px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:30px;font-weight:500;letter-spacing:.01em}
.sub{color:var(--dim);max-width:62ch}
main{padding:0 40px 80px}
section{padding:38px 0;border-bottom:1px solid var(--line)}
h2{font-size:22px;font-weight:500;margin:0 0 4px}
h2 .k{font:11px ui-monospace,Menlo,monospace;color:var(--gilt);
      letter-spacing:.14em;text-transform:uppercase;margin-right:12px}
.src{color:var(--dim);font-size:14px;margin-bottom:20px}
.src em{color:var(--ink);font-style:italic}
figure{margin:0 0 22px}
figure img{width:100%;border:1px solid var(--line);border-radius:3px;display:block}
figcaption{color:var(--dim);font-size:13px;padding-top:8px}
.rev{display:grid;gap:26px}
.tag{display:inline-block;font:10px ui-monospace,Menlo,monospace;letter-spacing:.12em;
     text-transform:uppercase;color:var(--gilt);border:1px solid var(--line);
     border-radius:2px;padding:2px 7px;margin-right:9px}
table.prov{width:100%;border-collapse:collapse;margin-top:6px;
           font:12.5px/1.55 ui-monospace,Menlo,monospace}
table.prov td{padding:7px 10px;border-top:1px solid var(--line);vertical-align:top}
table.prov td:first-child{color:var(--gilt);white-space:nowrap;width:1%}
.note{background:var(--panel);border-left:2px solid var(--gilt);
      padding:14px 18px;margin:20px 0;max-width:80ch}
.note b{color:var(--gilt);font-weight:500}
a{color:var(--gilt)}
@media (prefers-color-scheme:light){
 :root{--bg:#f6f5f2;--panel:#eceae5;--line:#d8d5cd;--ink:#1c1b19;--dim:#6b675f}}
"""


def build():
    parts = [f"<style>{CSS}</style>", """
<header>
  <h1>Still life, with provenance</h1>
  <div class="sub">Three scenes authored in X3D&nbsp;4.0, each grounded in a named
  public-domain painting and each carrying its own provenance in-scene. They are
  <em>interpretive</em> — inspired by the paintings, not reproductions of them —
  and the scenes say so in their own metadata rather than in a caption.</div>
</header><main>"""]

    for key, artist, title, date, coll in SCENES:
        d = provenance(key)
        parts.append(f'<section><h2><span class="k">{key}</span>{html.escape(title)}</h2>')
        parts.append(f'<div class="src">{html.escape(artist)} · {html.escape(date)} · '
                     f'{html.escape(coll)}</div>')

        revs = [(t, p, c) for t, p, c in PROGRESS.get(key, []) if exists(p)]
        if revs:
            parts.append('<div class="rev">')
            for tag, path, cap in revs:
                parts.append(f'<figure><img src="{path}" alt="{key} {tag}">'
                             f'<figcaption><span class="tag">{tag}</span>'
                             f'{html.escape(cap)}</figcaption></figure>')
            parts.append("</div>")

        if d:
            parts.append('<table class="prov">')
            for k in ("provenance", "catalogId", "publicDomain", "sourceCitation",
                      "rights", "generationMethod"):
                if k in d:
                    parts.append(f"<tr><td>{k}</td><td>{html.escape(d[k])}</td></tr>")
            parts.append("</table>")
        parts.append("</section>")

    fm = os.path.join(HERE, "FAILURE_MODES.md")
    if os.path.exists(fm):
        n = len(re.findall(r"^#{2,3}\s", open(fm, encoding="utf-8",
                                              errors="replace").read(), re.M))
        parts.append(f"""<section><h2>What silently failed</h2>
<div class="note"><b>{n} documented failure modes.</b> The ones that matter are those
where the XML validated and the render was still wrong — no schema catches those.
Two examples from this build: X_ITE ignores the <code>shadows</code> field on lights
entirely (verified by rendering the same scene with it on and off and getting
byte-identical output), and x3d.py's serializer omits
<code>containerField='value'</code> on MetadataSet members, so the provenance payload
itself shipped misparented until it was patched and asserted.</div>
<div class="src">Full notes: <a href="FAILURE_MODES.md">FAILURE_MODES.md</a> ·
<a href="README.md">README.md</a></div></section>""")

    parts.append("</main>")
    out = os.path.join(HERE, "gallery.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset=utf-8>"
                "<meta name=viewport content='width=device-width,initial-scale=1'>"
                "<title>Still life, with provenance</title>" + "".join(parts))
    return out


if __name__ == "__main__":
    p = build()
    print(f"  gallery v{VERSION} -> {p}  ({os.path.getsize(p)} bytes)")
