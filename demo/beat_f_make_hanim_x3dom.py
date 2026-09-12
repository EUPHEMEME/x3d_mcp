#!/usr/bin/env python3
# beat_f_make_hanim_x3dom.py v1.0 2026-08-31 — Beat F: put the REAL HAnim runner scene into an X3DOM page.
"""Beat F support script.

`LOA5_HAnim_Project/running_human_x3dom.html` is a hand-FLATTENED port (HAnimJoint
-> transform, HAnimSegment -> group) — X3DOM draws that. The renderer-gap claim
("X3DOM renders HAnim blank", techne/techne/gate.py) is about the real HAnim scene,
so this script wraps the actual `running_human.x3d` (HAnimHumanoid + skeleton
containerField, untouched) with the server's own x3dom_page builder, points it at
the locally vendored X3DOM, and writes
`LOA5_HAnim_Project/running_human_hanim_x3dom.html` (inside the project folder so
the relative mesh Inlines resolve identically to the X_ITE page).

Run:  cd /Users/alexander/x3d_mcp && .venv/bin/python demo/beat_f_make_hanim_x3dom.py
Self-asserts: output exists, references only local vendor libs, and still contains
the hanimhumanoid tag.
"""
import sys

sys.path.insert(0, "/Users/alexander/x3d_mcp")

from src.tools.render import _x3dom_page, _X3DOM_CDN_CSS, _X3DOM_CDN_JS  # noqa: E402

SRC = "/Users/alexander/x3d_mcp/LOA5_HAnim_Project/running_human.x3d"
OUT = "/Users/alexander/x3d_mcp/LOA5_HAnim_Project/running_human_hanim_x3dom.html"

xml = open(SRC).read()
page = _x3dom_page(xml, title="HAnim LOA-5 Runner — real HAnim scene in X3DOM")
page = page.replace(_X3DOM_CDN_CSS, "vendor/x3dom/x3dom.css")
page = page.replace(_X3DOM_CDN_JS, "vendor/x3dom/x3dom.js")
open(OUT, "w").write(page)

ok = ("vendor/x3dom/x3dom.js" in page and "https://" not in
      page.split("<body")[0].replace("https://www.w3.org", "")
      and "hanimhumanoid" in page.lower())
print(f"wrote {OUT} ({len(page)} bytes); local-libs+hanim present: {ok}")
sys.exit(0 if ok else 1)
