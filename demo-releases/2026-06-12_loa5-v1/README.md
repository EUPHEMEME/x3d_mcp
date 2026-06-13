# HAnim LOA5 Demo — snapshot 2026-06-12 (loa5-v1)

A self-contained snapshot of both demos at this date. Everything needed to view
them is in this folder; nothing outside it is required.

## What's here
- `view-demos.command` — **double-click this to view the demos in a browser.**
- `index.html` — landing page linking both demos and the PDFs.
- `running_human.html` — the **runner**: a canonical HAnim LOA5 bone-mesh
  skeleton (~277 bones) running a slalom course.
- `classroom_skeleton.html` — the **classroom**: the same skeleton on a display
  stand, with clickable chalkboard buttons.
- `*.x3d` — the X3D scenes the pages load.
- `assets/` — the bone meshes and textures the scenes use (bundled).
- `paper/x3d-mcp-hanim-demo.pdf` — the write-up of how this was built.
- `paper/visual-changelog.pdf` — one-page picture history of the project.

## How to view
**In a browser (recommended): double-click `view-demos.command`.** It starts a
tiny local web server and opens the demos. (Do NOT just double-click the `.html`
files — browsers block X3D players from reading the bone meshes over a `file://`
URL, so they fail to load. The launcher serves them over `http://localhost`,
which works.) First time, macOS may warn it's from an unidentified developer:
right-click the file → **Open** → **Open**. Close the Terminal window when done.

*In the classroom, click the chalkboard buttons — Walk / Run / Jump / Stand — to
switch the figure's motion (click once, without dragging).* Each demo takes a few
seconds to load all the bones.

**On the desktop (no server needed):** open either `.x3d` in Castle Model Viewer
for the highest-fidelity render.

## Notes
- This is a point-in-time copy for showing the demo as it was on 2026-06-12.
  The live project continues in the parent repository; see `../README.md` for how
  these dated snapshots relate to the git history.
