<!-- demo-script.md v1.1 2026-08-31 — beat-by-beat runbook for the Techne live conference demo (v1.1 appends beats D–F) -->

# Techne live demo — beat-by-beat runbook

Six beats, ~19 minutes of live terminal time (A–C the core ~10, D–F optional
extensions). Every beat was pre-run on
2026-08-31 and its full output captured; if anything goes sideways live (no
network for the X_ITE CDN, Chromium hiccup, projector panic), **switch to the
fallback receipts** — they are the real transcripts and PNGs of the same
commands, not mockups.

All commands run from the repo root:

```
cd /Users/alexander/x3d_mcp
```

Preflight (before walking on stage):

- `.venv` present with Playwright + Chromium installed (`.venv/bin/python -m playwright install chromium` if in doubt).
- Network reachable — every X_ITE render fetches the library from cdn.jsdelivr.net.
- `demo/receipts/` present (the fallbacks). Beats A and C each launch headless
  Chromium several times; nothing opens a visible window.

---

## Beat A — one attribute, invisible to the schema, kills the whole figure (3 min)

**Command**

```
.venv/bin/python demo/make_broken.py
```

**What it does** — writes `demo/original_skeleton.x3d` (the LOA5 Anatomy
Explorer, schema-conformant head order) and `demo/broken_skeleton_children.x3d`,
which differs by **exactly one attribute**: the skeleton root joint's
`containerField="skeleton"` becomes `containerField="children"` (x3d.py Bug 1).
Then it validates both against the XSD and runs both through `techne_gate.py`.

**Expected output (verified 2026-08-31)**

- STEP 2: `original -> valid: True`, `broken -> valid: True` — *the XSD cannot
  tell them apart.*
- STEP 3: original → `VERDICT: PASS — validation clean, render non-blank`
  (stddev ≈ 34, full skeleton in the PNG). ~10 s.
- STEP 4: broken → `VERDICT: FAIL — semantic validation reported 1 error(s)`,
  and Gate 1 prints the exact correction:
  `HAnimHumanoid.children does not accept a HAnimJoint ... Use containerField='joints'.`
  The rendered PNG shows the skeleton **gone** — backdrop only. ~10 s.
- Final line: `BEAT A SELF-ASSERTION` with no FAILs.

**Talking point (measured, worth saying out loud):** the broken frame is *not*
technically blank — the studio backdrop keeps its stddev at 3.89, a hair over
the 3.0 blank threshold. The blank check alone would have shrugged. It is the
**semantic gate** that names the defect here, and the **pixel side-by-side**
(original.png vs broken.png) that makes the audience gasp. The case where the
frame stays populated and one node silently vanishes is Beat C's job.

**Timing budget:** 3 min (script runs ~25 s total; the rest is talking over the
two PNGs).

**Fallback receipts:** `demo/receipts/beat_a/` —
`make_broken_full_transcript.txt`, `xsd_transcript.txt`,
`original_gate_transcript.txt`, `broken_gate_transcript.txt`,
`original.png` (full skeleton), `broken.png` (skeleton gone).

---

## Beat B — the proxy, live: one BLOCK, one silent REPAIR (3 min)

**Command**

```
.venv/bin/python demo/beat_b.py
```

**What it does** — drives real MCP tool calls through the Technē stdio proxy
(same wiring as `build_anatomy_spine.py`), plus one control call straight at
the unproxied server.

**Expected output (verified 2026-08-31)**

- **Case A (BLOCK):** `add_child` of an ImageTexture into a PhysicalMaterial
  with the containerField left to default →
  `Technē blocked this call (it would pass the schema but render wrong)` and
  the correction names **all five** legal slots: `baseTexture, emissiveTexture,
  normalTexture, occlusionTexture, metallicRoughnessTexture`. Technē refuses to
  guess intent (baseTexture vs normalTexture); the error message *is* the fix.
- **Case B (silent REPAIR):** `create_node` with `fields` sent as a
  markdown-fenced JSON **string** — the classic sloppy-model emission.
  Control first: the raw server rejects it
  (`Input should be a valid dictionary`). The same bytes through Technē:
  `Created Viewpoint with ID: …` — the SAP layer unwrapped the string and
  forwarded. The delta between those two responses is the whole point.
- Scoreboard: `calls: 5  blocked: 1  repaired_forwards: 1`, then
  `BEAT B SELF-ASSERTION` with no FAILs.

**Timing budget:** 3 min (script runs ~5 s; spend the time on the two
request/response pairs on screen).

**Fallback receipts:** `demo/receipts/beat_b/` — `beat_b_transcript.txt`
(raw requests + responses verbatim), `counters.json`.

---

## Beat C — the bone that isn't there (4 min)

**Command**

```
.venv/bin/python demo/beat_c_probe.py
```

**What it does** — a real asset defect (`docs/loa5-asset-findings.md` #2):
`l_tarsal_distal_phalanx_5` ships as a zero-geometry asset — the left little
toe's tip exists in the skeleton document and wraps nothing; its right twin is
a complete mesh. The script cans both little-toe joint subtrees from
`build_anatomy/skeleton.x3dfrag` into a small foot sub-scene
(`demo/foot_probe.x3d`) and runs `techne.differential.contributions()` over the
two HAnimSegments with the same X_ITE renderer the server uses: render, then
re-render with one node removed; identical pixels means the node was never on
screen.

**Expected output (verified 2026-08-31)**

```
baseline frame   : non_blank=True  stddev=26.45
hanim_l_tarsal_distal_phalanx_5         0 / 196608   ABSENT
hanim_r_tarsal_distal_phalanx_5      9243 / 196608   CONTRIBUTES
```

The frame is NON-blank (the right toe bone renders, close up) — the blank gate
passes it happily — and the probe still finds the left bone contributing
**exactly 0 pixels**. Because the segment is empty in the *asset*, it draws
nothing from any camera: camera choice cannot fake this result.

**Measured wall-time: 36.3 s for 3 renders (~12 s per render — each launches
headless Chromium and fetches X_ITE).** Say this out loud while it runs; it is
also why the differential is opt-in, priced at one render per candidate node,
and lives before a commitment rather than on every call.

**Timing budget:** 4 min (~40 s of render time; narrate the mechanism while
Chromium grinds).

**Fallback receipts:** `demo/receipts/beat_c/` — `beat_c_transcript.txt`,
`timing.json`, `01_baseline.png` (toe bone visible), `02_variant.png`
(left segment removed — identical), `03_variant.png` (right segment removed —
toe gone), plus `demo/foot_probe.x3d`.

---

## Framing caution — say it right

**Never say "the renderer is a correctness property."** The renderer is one
observer, with measured gaps of its own (X_ITE ignores an in-Transform
EnvironmentLight; X3DOM renders HAnim blank). The honest formula, verbatim:

> **The gate is a liveness check; the probe catches absence; correctness stays
> human.**

- The occupation gate proves the scene *draws something* — liveness, nothing
  more. Beat A's broken frame measured stddev 3.89 against a 3.0 threshold:
  the blank check is a coarse instrument and we say so.
- The differential probe proves a node *put pixels on screen* — it catches
  absence deterministically, and only absence. Zero pixels is not automatically
  a defect (occlusion, out-of-frustum, sub-threshold size are legal), which is
  exactly why the check is advisory by default.
- Neither ever certifies the scene is *right*. "Is that a moose?" — "is the
  lighting what the author meant?" — stays with the human architect. The
  expensive, irreversible render waits for human sign-off; the draftsman never
  pours concrete alone.

## Footnotes for honest Q&A

- `techne_gate.py` is at v1.1 for this demo: its printed VERDICT now covers
  both gates (validation clean AND render non-blank), matching its docstring
  and the library gate (`OccupationGate.check`); v1.0 printed the semantic
  report but based the verdict on blankness alone, and its line filter dropped
  the actual error bullets.
- `src/validation/semantic.py` gained a spec-correct fix in support of Beat A:
  the X3DUOM omits the `X3DMetadataObject` interface from Metadata\* nodes'
  inheritance chains, so a correct `<MetadataSet containerField='metadata'>`
  (present in the Anatomy Explorer) was a false-positive error. All 263 + 234
  repo tests pass after the fix.
- `demo/original_skeleton.x3d` reorders the explorer's `<head>` children
  (`component` before `meta`, the order the XSD requires) — a pre-existing
  conformance slip in the explorer generator, unrelated to the demo defect;
  scene content is untouched. The XSD demo needs a schema-valid original or
  "the XSD passes the broken file" would be an empty claim.

---

## Beat D — invisible on correct input: the scoreboard (2 min)

**Command**

```
PYTHONPATH=techne .venv/bin/python techne/eval/run_scripted.py --json demo/receipts/beat_d/scoreboard.json
```

**What it does** — the keyless evaluation harness (`techne/eval/README.md`): a
fixed set of authoring tasks driven as deterministic tool-call sequences through
**both stacks** — `raw` (the server alone) and `techne` (the same server behind
the proxy) — each task in its own fresh server process. Five documented
mistakes, one clean control.

**Expected output (verified 2026-08-31, wall-clock 4.65 s)** — the 12-row
scoreboard, then:

```
raw — passed SILENTLY into the scene     : 2/5
raw — rejected loudly, no fix offered    : 3/5
Technē — passed silently into the scene  : 0/5
Technē — caught (block or repair)        : 5/5
Technē blocks whose text named the fix   : 5/5
extra round-trips to a CORRECT scene     : +9 over 6 tasks
```

**The payoff row — say it first:**

```
control-clean         raw      4       0/0      0/0      0/0     -
control-clean         techne   4       0/0      0/0      0/0     -
```

On already-correct input Technē is **invisible**: same 4 calls as raw, zero
blocks, zero repairs, zero false positives (`scoreboard.json`: both
control-clean rows have `blocks: 0, repairs: 0`). A gate you can leave on is a
gate people actually leave on. Then read the mistake rows: raw leaks 2 of 5
silently and rejects 3 loudly with no fix; Technē catches 5/5 and every block
names the correction. The +9 round-trips is the honest price, and it includes
authoring the missing DEF, not just proxy overhead.

**Timing budget:** 2 min (the script runs ~5 s; spend the time on the
control-clean pair and one leak row, e.g. `textured-material`).

**Fallback receipts:** `demo/receipts/beat_d/` — `scoreboard.txt` (table +
summary as printed), `scoreboard.json` (per-row counters, machine-readable).

---

## Beat E — the provenance strict gate: unsourced blocks, attributed passes (3 min)

**Command**

```
.venv/bin/python demo/beat_e.py
```

**What it does** — opts into the provenance **policy** layer
(`techne/PROFILES.md`, `techne/PROVENANCE_BRIDGE.md`) at its strictest:

```
TECHNE_PROFILE=core,coherence,provenance
TECHNE_PROVENANCE_LEVEL=2          (sourcing: claims must resolve in a ledger)
TECHNE_STRICT=1                    (policy violations are hard stops)
TECHNE_ASSET_LEDGER=demo/beat_e_ledger.json
```

The ledger (`demo/beat_e_ledger.json`, same `{entries:[{id, citation,
source_url, public_domain}]}` shape as `drawings/archive.json`) holds exactly
one real asset: **BONE-R5**, the right fifth distal foot phalanx from the Web3D
Consortium `AllBonesLOA5Skeletons` bone-mesh set — **Brutzman, Williams,
Carlson & Hernandez** — citing the asset file's own `<meta creator>` header and
its web3d.org identifier URL.

**Expected output (verified 2026-08-31)**

- **Case A (BLOCK, 0.5 s):** `render_image` of a scene whose Transform is
  tagged `provenance='documented'` with `catalogId='SLOP-1'` →
  `isError=True`, no image, and the correction is the whole pitch:
  `Technē blocked this render (provenance policy, TECHNE_STRICT=1). Technē
  provenance (L2, violation): … catalogId='SLOP-1' does not resolve to any
  asset-ledger entry (have: BONE-R5). Register the asset with its
  citation/source/public-domain status, or correct the id.`
  The block fires **before Chromium ever launches** — 0.5 s against ~11 s for a
  render. *You cannot label a feature documented until you have the source that
  documents it.*
- **Case A′ (CONTROL, ~11 s):** the SAME scene through a default-profile Technē
  (`core,coherence`) renders silently — image returned, zero provenance text.
  Provenance is opt-in policy, not core correctness; nobody who didn't opt in
  ever meets this wall.
- **Case B (PASS, ~10 s):** the real bone mesh
  (`assets/loa5/meshes/r_tarsal_distal_phalanx_5.x3d`, its actual
  IndexedFaceSet extracted at runtime) wrapped in a provenance MetadataSet whose
  `catalogId='BONE-R5'` resolves → renders under the same strict gate,
  non-blank, **no provenance note at all**. Proper attribution is frictionless.
- Final line: `BEAT E SELF-ASSERTION` with no FAILs.

**Timing budget:** 3 min (script runs ~25 s; talk over the block text — the
error message IS the correction — and the bone PNG).

**Fallback receipts:** `demo/receipts/beat_e/` — `beat_e_transcript.txt`,
`timing.json`, `case_a_scene.x3d` (the blocked scene), `case_b_scene.x3d`
(the attributed scene), `case_b_bone.png` (the bone, visibly drawn).

---

## Beat F — two renderers, one scene: the humanoid X3DOM doesn't draw (4 min)

**Commands** (`tools_x3d/serve_gzip.py` must be serving the repo root on
`:8099`; `.venv/bin/python tools_x3d/serve_gzip.py &` if it isn't)

```
node demo/beat_f_shot.js http://localhost:8099/LOA5_HAnim_Project/running_human.html demo/receipts/beat_f/xite_running_human.png 15000
node demo/beat_f_shot.js http://localhost:8099/LOA5_HAnim_Project/running_human_hanim_x3dom.html demo/receipts/beat_f/x3dom_real_hanim_humanoid_missing.png 10000
node demo/beat_f_shot.js http://localhost:8099/LOA5_HAnim_Project/running_human_x3dom.html demo/receipts/beat_f/x3dom_flattened_white_runner.png 10000
```

**What it does** — `beat_f_shot.js` is `shot_plain.js` plus **offline
enforcement**: it intercepts every network request and aborts anything not
same-host, then exits non-zero if even one external request was *attempted*.
Both viewer libraries are now vendored inside the project folder
(`LOA5_HAnim_Project/vendor/x_ite/`, mirroring the repo-root X_ITE vendoring;
`LOA5_HAnim_Project/vendor/x3dom/` = X3DOM 1.8.2 js+css, whose CSS is
data-URI-only), so **both pages load fully offline** — each transcript ends
`external requests attempted: 0 -> OFFLINE-CLEAN`.

**Expected output (verified 2026-08-31, ~15–25 s per shot)**

- **X_ITE** (`running_human.html`, 539 same-host requests): the LOA-5 skeleton
  runs the slalom — bone meshes, PBR bone material, mid-stride.
- **X3DOM + the real HAnim scene** (`running_human_hanim_x3dom.html` — the
  actual `running_human.x3d`, HAnimHumanoid untouched, wrapped by the server's
  own `x3dom_page` builder): track, cones, finish banner all draw — **the
  humanoid is gone**. Sharpest number: **4 HTTP requests vs X_ITE's 539** —
  X3DOM drops the HAnim subtree so completely it never even asks for the 244
  bone-mesh Inlines. The frame is populated, so a blank check passes it
  happily; this is exactly the absence class the Beat C probe exists for.
- **X3DOM + the flattened port** (`running_human_x3dom.html`, 523 requests) —
  the honest third panel: this page draws a runner, because it contains **no
  HAnim nodes at all** (a hand-flattened port: HAnimJoint→transform,
  HAnimSegment→group). Even then it renders flat white — X3DOM drops the
  `PhysicalMaterial` inside every bone mesh. Working around the missing
  component costs you the scene's semantics *and* its materials.

**Talking point:** same scene, two conforming-looking pages, and the renderer
decides whether a humanoid exists. This is why the occupation gate names its
renderer (X_ITE, `techne/techne/gate.py`) — an X3DOM-backed gate would check a
frame the humanoid was never in — and why "renders in my viewer" is not a
correctness claim: **gate = liveness, probe = absence, correctness stays
human.**

**Timing budget:** 4 min (~50 s of shots; narrate the request-count delta while
Chromium grinds).

**Fallback receipts:** `demo/receipts/beat_f/` — `xite_running_human.png`
(skeleton mid-stride), `x3dom_real_hanim_humanoid_missing.png` (populated frame,
no humanoid), `x3dom_flattened_white_runner.png` (the workaround's white
runner), plus `offline_xite.txt`, `offline_x3dom_real_hanim.txt`,
`offline_x3dom_flattened.txt` (each ending `OFFLINE-CLEAN`, local-404 lines
counted and attributed).

## Footnotes for honest Q&A — beats D–F

- **Beat E required a real fix, disclosed:** `techne/techne/server.py` promised
  (PROFILES.md) that `TECHNE_STRICT=1` turns policy violations into hard stops,
  but the code only relabeled the advisory note "violation" and forwarded
  anyway. The strict path now blocks `render_image(content=…)` **before the
  forward** when the opt-in provenance profile finds a violation; soft mode and
  the default profile are byte-identical to before. Three new transport tests
  (`test_server.py`); the techne suite is 237/237. Edit-tool output under strict
  still gets the riding "violation" note rather than a block — by the time an
  edit's document can be checked, the edit has already been applied upstream.
- **Beat E's "documented" rules are Layer-2 (sourcing) rules and they do fire
  on this content** — the demo runs at `TECHNE_PROVENANCE_LEVEL=2` with a real
  ledger. Layer 3 (content semantics: taxon/depth/cal-BC) remains deliberately
  unbuilt (`PROVENANCE_BRIDGE.md`).
- **Beat E's ledger flag:** the bone set ships under the Web3D Consortium
  open-source license (`../license.html` in the asset set), recorded under the
  ledger's `public_domain` flag as "cleared" — stated in the entry's
  `license_note`, not silently conflated.
- **Beat F's original pitch was "X3DOM missing the humanoid vs X_ITE drawing
  it" — measured reality is subtler and better:** the project's existing
  `running_human_x3dom.html` *does* draw a runner, because it is a flattened
  non-HAnim port. The missing-humanoid receipt comes from the new
  `running_human_hanim_x3dom.html` (generated by
  `demo/beat_f_make_hanim_x3dom.py` from the real scene). Both statements are
  in the receipts; don't collapse them into "X3DOM is blank".
- **Beat F's 404s are local and pre-existing:** the AxesDisplay.x3d
  missing-asset defect (`docs/loa5-asset-findings.md` #1) fires 519/260/1
  same-host 404s across the three shots; the offline verdict counts them but
  they are not external fetches.
- **Preflight change:** the two LOA5 pages no longer need the network at all;
  the CDN lines in the preflight note above apply to beats A–C's
  `render_image`/X_ITE path only.
