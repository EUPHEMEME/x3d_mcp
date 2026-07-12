# LOA5 Anatomy Explorer — 2026-07-12

An interactive, studio-lit HAnim **Level-of-Articulation 5** skeleton in which
**every one of the 256 parts can be clicked, named and explained**.

Open `view-demo.command` (or serve this folder and open `anatomy_explorer.html`).

## What it does

- **Click any bone** — it lights gold and names itself, with its group, what it
  *does*, what it articulates with, and a clinical note.
- **Explore** — browse by anatomical group; opening a group lights all of it at
  once (all 24 ribs, all 8 carpals).
- **Learn** — 6 guided lessons (41 steps), each flying the camera and
  lighting the bones as it teaches.
- **Quiz** — 20 find-the-bone questions that ask what a bone *does*, not what it
  is called. Click the answer on the skeleton.
- **Gait** — Stand / Walk / Run / Jump, driven by the HAnim standard's own cycles.
  Bones stay clickable *while the figure is moving*.

## Why 256 parts and not 206 bones?

The number every student memorises is 206. This model has 256 clickable parts:

| | |
|---|---|
| bones | 198 |
| teeth | 32 |
| intervertebral discs | 23 |
| cartilage | 3 |

Teeth, discs and cartilage are modelled but **are not bones**. Strip them out and
198 bones remain — still 7 short of 206. Every one of those 7 is accounted for
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
  the 206-vs-198 reconciliation is **computed from the model**, group by group, not
  asserted.
- Rendered in the browser by **X_ITE 11.6.6**. No build step.

Size: 10.8 MB.
