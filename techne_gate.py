#!/usr/bin/env python3
# techne_gate.py v1.1 2026-08-31 — CLI for Technē's two gates; verdict now covers BOTH gates.
"""Gate any X3D file through Technē's two gates before declaring it done:
   (1) semantic validation   (2) render-and-look occupation gate.
Usage:  .venv/bin/python techne_gate.py <scene.x3d>  [out.png]

v1.1: the printed VERDICT now matches the docstring above and the library gate
(techne.gate.OccupationGate.check): a scene FAILS if semantic validation reports
errors OR the render is blank. v1.0 printed the semantic report but based the
verdict on blankness alone — and its line filter dropped the actual error
bullets (they contain the rule text, not the word "error")."""
import asyncio
import os
import sys

REPO = "/Users/alexander/x3d_mcp"
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "techne"))

from validation.semantic import validate_semantic     # noqa: E402
from tools import render                               # noqa: E402
from techne import gate                                # noqa: E402

X3D = os.path.abspath(sys.argv[1])
PNG = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else X3D.rsplit(".", 1)[0] + ".png"

print("=" * 66, "\nGATE 1 — SEMANTIC VALIDATION\n" + "=" * 66)
report = validate_semantic(open(X3D).read())
# print the header plus the Errors/Warnings sections (not the info firehose)
n_errors = 0
section = ""
for ln in report.splitlines():
    if ln.startswith("Found"):
        print(ln)
        n_errors = int(ln.split()[1])
        continue
    if ln.startswith("## "):
        section = ln.strip("# ").lower()
        if section in ("errors", "warnings"):
            print(ln)
        continue
    if section in ("errors", "warnings") and ln.strip():
        print(ln)
gate1_ok = n_errors == 0
print("gate 1    :", "clean" if gate1_ok else f"{n_errors} error(s) — see corrections above")

print("=" * 66, "\nGATE 2 — OCCUPATION GATE (render under X_ITE + look)\n" + "=" * 66)
png = asyncio.run(render._render_xite_path_async(X3D, 1200, 860, 4000))
open(PNG, "wb").write(png)
r = gate.inspect_render(png)
print(f"rendered  -> {PNG}  ({len(png)//1024} KB)")
print(f"non_blank : {r.non_blank}   dims {r.width}x{r.height}   stddev {r.stddev:.2f}")

if gate1_ok and r.non_blank:
    print("VERDICT: PASS — validation clean, render non-blank")
    sys.exit(0)
reasons = []
if not gate1_ok:
    reasons.append(f"semantic validation reported {n_errors} error(s)")
if not r.non_blank:
    reasons.append("render is blank")
print("VERDICT: FAIL —", "; ".join(reasons))
sys.exit(1)
