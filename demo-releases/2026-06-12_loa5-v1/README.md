# HAnim LOA5 Demo — snapshot 2026-06-12 (loa5-v1)

A self-contained snapshot of both demos at this date. Everything needed to view
them is in this folder; nothing outside it is required.

## What's here
- `running_human.html` — the **runner**: a canonical HAnim LOA5 bone-mesh
  skeleton (150 joints, 243 bones) running a slalom course.
- `classroom_skeleton.html` — the **classroom**: the same skeleton on a display
  stand, with clickable chalkboard buttons.
- `*.x3d` — the X3D scenes the pages load.
- `assets/` — the bone meshes and textures the scenes use (bundled).
- `paper/x3d-mcp-hanim-demo.pdf` — the write-up of how this was built.
- `paper/visual-changelog.pdf` — one-page picture history of the project.

## How to view
**In a browser (recommended):** open `running_human.html` or
`classroom_skeleton.html`. They use the X_ITE web player (loaded from the
internet), which renders the real HAnim skeleton.
*In the classroom, click the chalkboard buttons — Walk / Run / Jump / Stand — to
switch the figure's motion.* (Click once, without dragging.)

**On the desktop:** open either `.x3d` in Castle Model Viewer for the highest-
fidelity render.

## Notes
- This is a point-in-time copy for showing the demo as it was on 2026-06-12.
  The live project continues in the parent repository; see `../README.md` for how
  these dated snapshots relate to the git history.
