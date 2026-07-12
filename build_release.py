#!/usr/bin/env python3
"""Package the LOA5 Anatomy Explorer as a dated, self-contained demo release.

Matches the convention in demo-releases/README.md: drop into the folder, run the
server script, open the page. No build step, no dependence on the rest of the repo.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-07-12"
DEST = f"{REPO}/demo-releases/{DATE}_anatomy-explorer"

FILES = [
    ("anatomy_explorer.html", "anatomy_explorer.html"),
    ("anatomy_explorer.x3d",  "anatomy_explorer.x3d"),
    ("build_anatomy/bone_manifest.json", "build_anatomy/bone_manifest.json"),
    ("build_anatomy/anatomy_kb.json",    "build_anatomy/anatomy_kb.json"),
]

SERVE = """#!/bin/sh
# The scene is a 10 MB .x3d and the page fetches two JSON files, so it must be
# served over HTTP -- opening the .html straight off disk trips CORS.
cd "$(dirname "$0")"
echo "LOA5 Anatomy Explorer -> http://localhost:8080/anatomy_explorer.html"
python3 -m http.server 8080 >/dev/null 2>&1 &
sleep 1
open "http://localhost:8080/anatomy_explorer.html" 2>/dev/null || \\
  echo "open http://localhost:8080/anatomy_explorer.html"
wait
"""


def main() -> None:
    os.makedirs(f"{DEST}/build_anatomy", exist_ok=True)
    for src, dst in FILES:
        shutil.copy(f"{REPO}/{src}", f"{DEST}/{dst}")

    with open(f"{DEST}/view-demo.command", "w") as fh:
        fh.write(SERVE)
    os.chmod(f"{DEST}/view-demo.command", 0o755)

    man = json.load(open(f"{DEST}/build_anatomy/bone_manifest.json"))
    kb = json.load(open(f"{DEST}/build_anatomy/anatomy_kb.json"))
    k = man["kinds"]
    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(DEST) for f in fs) / 1e6

    readme = f"""# LOA5 Anatomy Explorer — {DATE}

An interactive, studio-lit HAnim **Level-of-Articulation 5** skeleton in which
**every one of the {man['counts']['total']} parts can be clicked, named and explained**.

Open `view-demo.command` (or serve this folder and open `anatomy_explorer.html`).

## What it does

- **Click any bone** — it lights gold and names itself, with its group, what it
  *does*, what it articulates with, and a clinical note.
- **Explore** — browse by anatomical group; opening a group lights all of it at
  once (all 24 ribs, all 8 carpals).
- **Learn** — {len(kb['tours'])} guided lessons ({sum(len(t['steps']) for t in kb['tours'])} steps), each flying the camera and
  lighting the bones as it teaches.
- **Quiz** — {len(kb['quiz'])} find-the-bone questions that ask what a bone *does*, not what it
  is called. Click the answer on the skeleton.
- **Gait** — Stand / Walk / Run / Jump, driven by the HAnim standard's own cycles.
  Bones stay clickable *while the figure is moving*.

## Why {man['counts']['total']} parts and not 206 bones?

The number every student memorises is 206. This model has {man['counts']['total']} clickable parts:

| | |
|---|---|
| bones | {k.get('bone', 0)} |
| teeth | {k.get('tooth', 0)} |
| intervertebral discs | {k.get('disc', 0)} |
| cartilage | {k.get('cartilage', 0)} |

Teeth, discs and cartilage are modelled but **are not bones**. Strip them out and
{k.get('bone', 0)} bones remain — still 7 short of 206. Every one of those 7 is accounted for
in the app's *Learn → Why 257, not 206?* panel, and three of them are **real defects
in the source asset set**, not facts about the human body:

- the **auditory ossicles** (6) were never modelled;
- the **hyoid** (1) was never modelled;
- **`l_tarsal_distal_phalanx_5`** — the left little toe's tip — is an empty file
  (its right-side twin has a full mesh), so the left foot is one bone short;
- the **ethmoid**, a single midline bone, is built as a left and a right half (+1).

See `../../docs/loa5-asset-findings.md`.

## Provenance

- Bone meshes and the anatomical prose inside them: **Don Brutzman, Joe Williams,
  John Carlson, Damon Hernandez** — Web3D Consortium HAnim `AllBonesLOA5Skeletons`.
- Skeleton, joints and the Walk/Run/Jump cycles: the HAnim 2.0 standard's own
  `loa5_humanoid.x3dfrag` and `*_animation.x3dfrag`.
- The studio scene (viewpoints, 3-point rig, backdrop, gait clocks) was authored
  **one tool call at a time through the Technē craft proxy** in front of the Web3D
  `x3d_mcp` server.
- Anatomy teaching layer: researched and fact-checked against standard references;
  the 206-vs-{k.get('bone', 0)} reconciliation is **computed from the model**, group by group, not
  asserted.
- Rendered in the browser by **X_ITE 11.6.6**. No build step.

Size: {size:.1f} MB.
"""
    open(f"{DEST}/README.md", "w").write(readme)

    print(f"release -> {DEST}  ({size:.1f} MB)")
    for r, _, fs in os.walk(DEST):
        for f in sorted(fs):
            p = os.path.join(r, f)
            print(f"  {os.path.relpath(p, DEST):42} {os.path.getsize(p)/1e3:8.1f} KB")


if __name__ == "__main__":
    main()
