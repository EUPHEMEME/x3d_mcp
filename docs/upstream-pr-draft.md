# Staged upstream PR — toolchain only (NOT yet opened)

Branch pushed to the fork: **`EUPHEMEME:feat/xite-render-backend-validators`**
(off `Web3DConsortium/x3d_mcp` `main`). Tests: **67 passing**. Diff: **15 files,
1,023 insertions** — pure MCP toolchain, **no caves / personal / heritage content**.

Status: **staged, not opened** (deliberately discreet). Open it only on your word.

## What's in it (everything going upstream)

| File | What it adds |
|---|---|
| `src/tools/render.py` (+203) | `render_image` / `render_current_scene`: async Playwright **X_ITE** backend that renders PBR + HAnim (X3DOM leaves these blank headless); path inputs served over an ephemeral loopback HTTP server so relative assets resolve |
| `src/validation/semantic.py` (+219) | `containerField` checks (X3DUOM-derived, names the canonical field), USE-before-DEF order, interpolator `key`/`keyValue` length |
| `src/validation/autofix.py` (+91, new) | `autofix_x3d`: rewrites wrong/defaulted containerFields, returns the corrected document |
| `src/tools/validate_tool.py` (+83) | wires the semantic checks into the MCP validate tool |
| `src/tools/granular.py` (+14) | granular-mode parity for non-default containerField placement |
| `src/tools/prompts.py` (+10), `src/server.py` (+37) | proactive `instructions`: the describe → build → validate-both → render canonical path |
| `src/x3d_utils/scene.py` (+92), `src/x3d_utils/source.py` (+37, new) | scene/source plumbing the above needs |
| `tests/test_{autofix,semantic,scene,source,render}.py` (+292, new) | coverage |
| `pyproject.toml` (+5) | the Playwright dep for the render backend |

## What is deliberately NOT in it (kept private / out of scope)
- The **caves heritage work** — every `generate_*cave*`, `drawings/`, the fauna,
  the bone-horizon scenes, both cave papers, the project folder.
- The **HAnim demo content** (runner/classroom scenes, LOA5 bone-mesh assets,
  the `x3d-mcp-hanim-demo` paper) — these can be a separate, later contribution.
- The vendored `tools_x3d/X3dToX3dom.xslt` — a Web3D asset the render backend
  does not use, and the consortium already maintains.
- The protected cave **location** — never published anywhere.

## Already open
**PR #9** — "Fix X3DOM renderer crashes/escaping and ROUTE semantic-checker false
positives" (branch `fix/render-and-semantic-validation-bugs`) is already OPEN
upstream. This new branch is the larger feature contribution that builds on it.

## To open it (when you say go)
```sh
gh pr create --repo Web3DConsortium/x3d_mcp \
  --head EUPHEMEME:feat/xite-render-backend-validators --base main \
  --title "X_ITE render backend, semantic validators, and autofix for the X3D MCP" \
  --body-file docs/upstream-pr-draft-body.md          # or paste the commit body
```
(or open as a **draft** PR with `--draft` to stay discreet while it's reviewed).
