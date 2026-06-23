# Technē — goals

**Mission: make the X3D MCP produce better results with LLMs.**

Output quality is the goal. **Coherence and efficiency are the operating
priorities.** Novelty is explicitly *not* a priority — if a known, boring
technique (a linter rule, a render check, a request sanitizer) improves the
output, we use it. Technē is the quality layer for LLM-authored X3D over the
Web3D `x3d_mcp` server; its contribution to open standards is *reliability*, not
invention.

The honest scope (set by an adversarial review, June 2026): Technē is a
deterministic repair + craft-validation + render-gate layer for one format
(X3D) with a documented bug catalog. It is a candidate best-practice and
tooling contribution to the WG's `x3d_mcp`, not "infrastructure the field already
has." Claims kept narrow on purpose.

---

## The three goals

### 1. Output quality — does the scene render *right*, not just validate?
The floor: output that passes the XSD yet renders wrong or blank. Mechanisms:
- **Craft catalog** (`rules.py`) — documented silent-failure modes turned into
  deterministic, *prescriptive* corrections ("use `containerField='baseTexture'`",
  not "invalid"). Built: containerField slots, `EnvironmentLight.global`,
  interpolator `key`/`keyValue` parity, USE-before-DEF. *Grow this as new modes
  surface.*
- **The gate, named honestly.** It is a **liveness / blank screen** — it catches
  the documented *blank-producing* bugs (a dropped `containerField` renders
  nothing) and surfaces the image for a look. It is **not** a correctness proof;
  a non-blank scene can still be mis-scaled, off-camera, or wrong-colored.
  Correctness stays the human's job. (Drop the phrase "the renderer is a
  correctness property.")
- **Look up, don't recall** — lean on `describe_node`/`autofix` so the model
  builds against the real field/containerField table, not its memory.

### 2. Coherence — is the scene internally consistent, across a long session?
LLMs *drift*: they forget the handedness of the axes, the unit, the timer
conventions, what they already DEF'd. Coherence mechanisms:
- **Standing semantics, injected not hoped** (built — `semantics.py`). The few
  invariants the model keeps losing — right-handed / +Y-up / radians-and-meters,
  `TimeSensor`-animates-only-through-ROUTEs, the `HAnimJoint` identity rest pose,
  PBR-and-the-default-headlight — ride back as a SOFT reminder on the relevant
  tool result, once per session, capped, advisory-only (never blocks). The text
  is spec-grounded and adversarially tightened (the `verify-x3d-invariants`
  workflow caught and fixed a wrong "PBR renders black" claim). Toggle with
  `TECHNE_SEMANTICS=0` for A/B isolation in the eval.
- **Cross-call consistency** — the minimal `SceneState` Technē already tracks
  (id→type, DEFs) is the seed. Enforce the few hard cross-call edges:
  USE references a real prior DEF; no orphaned nodes; consistent units. This is
  the *coherence* half of the deferred "Point 1" — built as guarded edges, not a
  full order-of-operations straitjacket.
- **Provenance coherence** — the documented-vs-interpretive tag keeps the scene's
  *claims* consistent and honest; a candidate input to the WG's metadata effort.

### 3. Efficiency — how few round-trips / tokens to a correct scene?
The expensive part of LLM authoring is the build → validate → render → debug →
retry loop. Technē earns its place by shortening it:
- **Prescriptive corrections cut retries.** "rejected: use `baseTexture`" fixes
  it in one step; "invalid" makes the model guess again. Fewer failed renders.
- **Front-load the deterministic catches** so the costly render-loop runs only on
  the things a rule *can't* settle.
- **Context efficiency** — don't make the agent load a 280 KB scene into context
  to validate it (the live smoke found `validate_x3d` wanting inline content, not
  a path — an efficiency bug, not just a correctness one).
- **Determinism = no re-teaching the craft every session.** The rules hold
  mechanically, so the craft doesn't have to be re-explained in the prompt on
  every fresh connection — token efficiency across a fleet of sessions.

---

## The spine: measure it — built (`eval/`)
"Better" must be provable, or it is just a claim (the review's sharpest demand).
The **evaluation harness** (`techne/eval/`, see its README) runs a fixed set of
X3D authoring tasks through `x3d_mcp` **with and without Technē** and reports:
- **mistakes caught vs leaked silently** (the documented silent-failure modes),
- **round-trips to a correct scene** (the efficiency column),
- **render liveness** (non-blank, via the gate — honestly *not* correctness),
- **tokens spent** (live mode).

Two modes: a deterministic **scripted** scoreboard (keyless, CI-able) and a
**live** mode where a real model authors through each stack. Scripted run (6
tasks, 5 documented mistakes): raw lets **2** pass *silently* into the scene and
rejects **3** loudly with no fix; Technē catches **5/5**, every block naming the
fix, at **+9 round-trips to a *correct* scene** — and on already-correct input
adds no blocks and no extra round-trips (no false positives in the catch/leak
columns; with reminders on, a soft coherence line may still ride along —
`TECHNE_SEMANTICS=0` restores byte-identity). Every goal above is scored against
this table. Coherence and
efficiency are the priorities precisely because they are the columns we can move
now; grow the task set as `rules.py` grows.

## Correctness is universal; policy is opt-in (`PROFILES.md`)
To stay useful to *everyone*, Technē separates **correctness** (the silent-failure
catalog, blank gate, edit post-pass — objective, always on) from **policy** (the
provenance/honesty gate — opinionated, off by default), the way ESLint splits
`recommended` from opinionated configs. `core` is the zero-config "it just renders
right" floor; `coherence` is default-on soft; `provenance` is opt-in
(`TECHNE_PROFILE`), graduated (L1 ledger-free disclosure → L2 sourcing → L3 content),
and soft-by-default. A mandatory provenance wall would make Technē niche; this keeps
it universal while preserving the slop-resistance value for those who want it.

## Out of scope (for now)
The venture / "TechnicalDiplomacy" / narrative framings belong to EUPHEME's
separate roadmap and are **not** part of Technē until deliberately specified.
Technē here is, and stays, about reliable LLM-authored X3D for Web3D.
