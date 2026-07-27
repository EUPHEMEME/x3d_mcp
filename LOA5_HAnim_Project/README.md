# HAnim LOA5 — runner & living-classroom demos (X3D)

A standards-conformant HAnim **Level-of-Articulation 5** humanoid (150 joints, 243
bone meshes from the Web3D `AllBonesLOA5Skeletons` model), driven by the standard's
own Walk/Run/Jump cycles, in two interactive X3D scenes.

- `running_human.x3d` / `.html` — the figure running a slalom course (gait locked to ground speed).
- `classroom_skeleton.x3d` / `.html` — a "living" classroom skeleton with PBR bones,
  FLUX-generated chalkboard/posters, and clickable Walk/Run/Jump/Stand buttons.
- `assets/loa5/` — the canonical bone meshes the scenes inline.
- `images/` — rendered figures.  `paper/` — the case-study write-up (DRAFT).
- `generators/` — the Python that builds the scenes.

Live 3-D: open the `.html` in a browser via a local web server (X_ITE renders the
HAnim skeleton + PBR directly; the `_x3dom.html` variants are the X3DOM build).
Built with the X3D MCP toolchain — see the companion repo `x3d_mcp`.
