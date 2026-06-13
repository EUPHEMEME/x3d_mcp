# Demo releases — dated snapshots

Each subfolder here is a **self-contained, openable snapshot** of the demos at a
point in time, named `YYYY-MM-DD_label`. Drop into any one and open its
`.html` files to show the demos exactly as they were on that date — no build
step, no dependence on the rest of the repository.

This is deliberately *outside* the git commit history: git tracks every tiny
change, but these folders are the handful of milestones worth showing. Over the
coming months, new milestones get a new dated folder here, so you can flip
through the project's evolution by opening folders rather than reading commits.

| Snapshot | Date | Highlights |
|---|---|---|
| `2026-06-12_loa5-v1` | 2026-06-12 | First LOA5 release: canonical bone-mesh runner + interactive classroom (Walk/Run/Jump), PBR, X_ITE. Paper + visual changelog included. |

To add the next snapshot, copy the current demo outputs (`*.html`, `*.x3d`,
`assets/`) plus the latest paper/changelog into a new dated folder.
