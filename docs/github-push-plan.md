# GitHub push & PR plan

State as of this handoff. **Nothing here is pushed automatically** --- this is the
map; you approve each step.

## Remotes
- `origin` = **Web3DConsortium/x3d_mcp** (upstream / official)
- `fork`   = **EUPHEMEME/x3d_mcp** (yours; PRs originate here)

## Already open (yours)
- **PR #9** --- `fix/render-and-semantic-validation-bugs` --- *"Fix X3DOM renderer
  crashes/escaping and ROUTE semantic-checker false positives."* OPEN.
  ✅ **Reconciliation verified (no conflict).** PR #9's `render.py` and
  `semantic.py` fixes are already byte-identical in `main` (and thus in our
  branches' ancestry); our X\_ITE work is purely *additive* and **keeps** the
  X3DOM page path (so PR #9's escaping fix stays live) and the ROUTE/HAnim-grouping
  semantic fixes. `git merge-tree --write-tree HEAD fix/render-and-semantic-validation-bugs`
  returns **0 conflicts**. Recommendation: let PR #9 merge as the self-contained
  bugfix it is; our PRs sit cleanly on top with no manual render.py/semantic.py
  reconciliation.
- PR #8 --- not ours (streamable-http transport).

## Branches and where they go
| Branch | Commits vs main | Nature | Destination |
|---|---|---|---|
| `mcp-improvements` | 7 | canonical MCP contributions | **PR(s) to origin** |
| `potter-creek-cave` | 20 (= 7 mcp-improvements + 13 cave) | creative/heritage app | fork backup + demo |
| `moose-pipeline` | creative | rigged-moose pipeline | fork backup |
| `fix/render-and-semantic-validation-bugs` | — | already PR #9 | (open) |
| `main` | ahead 29 of origin/main | prior HAnim/classroom work | discuss w/ Don |

---

## Step 1 --- Back up to your fork (low-risk, do first)
These branches are **local-only**; push so nothing is lost and they're shareable
for the meeting:
```
git push fork mcp-improvements
git push fork potter-creek-cave
git push fork moose-pipeline
```
(No PR yet --- just branches on your fork.)

## Step 2 --- PR(s) to Web3DConsortium (the canonical contributions)
Source: `mcp-improvements` (7 commits, **255 tests passing**). Recommend **two
reviewable PRs**:

**PR A --- X\_ITE rendering backend** *(flagship)*
- `render_image` / `render_current_scene` $\rightarrow$ async Playwright + X\_ITE
  over a loopback server; serves a file's own dir so relative textures resolve.
- Fixes *"Sync API inside the asyncio loop"*; renders **HAnim + PhysicalMaterial
  (PBR)** that X3DOM cannot, and that don't draw at all headless under X3DOM.
- Commits: `05be664` (initial render\_image), `903da38` (X\_ITE backend),
  `bac2d45` (serve file's directory).
- Stacks cleanly on PR #9 (verified no conflict; the X3DOM page path is retained).

**PR B --- Semantic validation + autofix + canonical guidance**
- containerField check (suggests the correct field), USE-before-DEF,
  interpolator key/keyValue length; `autofix_x3d`; granular non-default
  placement; proactive server `instructions`.
- Commits: `aee0542`, `2ea847a`, `799c6a4`, `a812bc9`.
- Retains PR #9's ROUTE/HAnim-grouping semantic fixes (verified no conflict);
  the new checks are additive.

*(Alternatively land all 7 as one "X\_ITE rendering + semantic validation" PR ---
simpler to file, larger to review.)*

## Step 3 --- `x3d.py` upstream bug report
`docs/x3dpy-bug-report.md`: dropped `containerField` on non-default fields; wrong
`EnvironmentLight.global` default. **Not a PR to this repo** --- file as an issue
on the `x3d.py` project and/or include in the note to Don.

## Step 4 --- Demo contribution + paper (per Don's invitation)
- The cave scenes + `docs/paper/merriam-caves.tex` as a demo for
  **X3dForAdvancedModeling/LargeLanguageModels/** (the venue Don invited), beside
  the classroom-skeleton demo.
- Caves are application artifacts, not MCP changes $\rightarrow$ share via the
  fork branch + the paper, not a PR to the MCP repo. Bring to the 8 am meeting.

## Not yet ready (ideas / WIP --- no push)
- Populate caves with the excavated megafauna (reuse the moose creature pipeline).
- True volumetric god-rays / refractive water in X\_ITE.
- Ground-truth Samwel room sizes from on-site photos.

## One-glance command sequence (after you approve)
```
# 1. backup
git push fork mcp-improvements potter-creek-cave moose-pipeline
# 2. open PRs from the fork (after reconciling with #9)
gh pr create --repo Web3DConsortium/x3d_mcp --base main \
  --head EUPHEMEME:mcp-improvements --title "X_ITE rendering backend for render_image" --web
```
