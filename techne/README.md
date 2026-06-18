# Technē — a deterministic craft layer for MCP servers

> **Technē** makes a model's tool-call arguments *conform* to a format's unwritten
> conventions — the craft the schema doesn't encode — and holds a render-and-look
> gate before declaring work done, so the craft holds **mechanically**, regardless
> of whether the model comprehended it. The schema is the rules; Technē is the craft.

τέχνη (*technē*) — craft-knowledge-with-an-account: the contingent know-how of making
something come out *right*, as distinct from the necessary formal truths of its
structure (*epistēmē*). The root is PIE \*teks-, "to weave / construct" — cognate with
*text* and *texture*. A scene graph, literally.

**Mission** (see [`GOALS.md`](GOALS.md)): make the X3D MCP produce better results with
LLMs. Output quality is the goal; **coherence and efficiency** are the operating
priorities; **novelty is not**. Technē is the quality layer for LLM-authored X3D over
the Web3D Consortium `x3d_mcp` server — its contribution is *reliability*, not invention.

## The problem

An MCP server over a format like X3D exposes a flat tool+node surface, and a model can
drive it to emit output that is **structurally valid but semantically dead**:

- a `containerField` dropped, so a texture or an HAnim humanoid **silently vanishes**;
- a ROUTE wired to a field that doesn't exist, so an animation **never fires**;
- interpolator `key`/`keyValue` lengths mismatched, so motion **corrupts**;
- a scene that passes every validator and still renders **blank**.

None of these throw. They pass the XSD. They fail only when you render and *look*. That
is the gap between **epistēmē** (the XSD — decidable, closed) and **technē** (the
contingent craft — which `containerField` for which slot, the order of operations — that
the schema does not encode). A DCC app supplies technē through its verbs and enforced
order; X3D-the-format has only epistēmē. Technē (the layer) supplies the missing technē.

The governing commitment is **determinism**. Craft-rules in a prose system prompt are
advisory — the model *probably* applies them, and the dice reset every session. Technē
instead makes the craft hold *mechanically*: the model's tool-call arguments pass through
a layer that repairs and validates them deterministically, at **runtime, LLM-free**,
before the real server runs them. Hindsight becomes **mechanism**, not text to re-read.
(This is the opposite of "fix it in post.")

## Architecture

```
  model  ──tool_call(args)──►  TECHNĒ PROXY  ──forwarded(repaired)──►  x3d-mcp
 (draftsman) ◄── result /      1 SAP repair                            (real server)
            prescriptive       2 craft rules: repair, or block + correction
            correction         3 occupation gate: render + look
```

A transparent man-in-the-middle: the model connects to Technē; Technē launches the real
`x3d-mcp` behind it and relays every call, intervening only where it has something to
add. On already-correct input the **core** is silent — same calls, no blocks, no false
positives. (The default coherence reminders are soft and advisory; `TECHNE_SEMANTICS=0`.)

## Correctness is universal; policy is opt-in

The design rule that keeps Technē useful to *everyone*, not just provenance-minded
projects — the [ESLint](https://eslint.org) split of `recommended` (objective, default-on)
from opinionated configs (opt-in). See [`PROFILES.md`](PROFILES.md).

| profile | what it does | default |
|---|---|---|
| **core** | the silent-failure craft catalog, the blank-render gate, the edit-tool post-pass | **always on** |
| **coherence** | standing-semantics reminders (axes, units, timers, HAnim, PBR) | **on** (soft) |
| **provenance** | the documented/interpretive honesty gate | **off** (opt-in) |

`core` is never opt-out: it is the "front the `x3d-mcp` with Technē and your output just
renders correctly, zero config" floor. Everything opinionated sits on top, off by default.
Configured via `TECHNE_PROFILE` (+ `TECHNE_SEMANTICS`, `TECHNE_PROVENANCE_LEVEL`,
`TECHNE_ASSET_LEDGER`, `TECHNE_STRICT`); `Config.from_env()` is the single source of truth.

## What's here

**Core correctness** (always on):
- **`rules.py`** — the rule→fix catalog: `{rule: (severity, prescriptive_correction, source)}`,
  **27 rules**. The error message *is* the fix. **Mirrors the server's own
  `validate_semantic`** (containerField, duplicate-DEF, USE/ROUTE, interpolator arity,
  shape/group/viewpoint): **11 enforced per-call**, 16 catalogued and deferred to the
  upstream whole-scene validator rather than re-implemented (so it can't drift).
- **`craft.py`** — the deterministic engine. Determinable rules **repair** the args;
  unrepairable ones **block + return the correction**. Also `reassert_envlight_global`
  (the serialization-layer fix x3d.py needs) and `dedupe_appearances` (a DEF/USE
  efficiency utility).
- **`repair.py`** — SAP-style argument repair (the dependency-free baseline for BAML's
  `b.parse`).
- **`proxy.py`** — the stateful decision core: minimal scene state (id→type, DEFs,
  id→DEF) committed only on confirmed upstream success; per-tool adapters;
  `decide()` / `observe_result()`.
- **`server.py`** — the MCP man-in-the-middle transport. Relays results, appends
  notes/reminders, and **post-validates the content-based edit tools** (`modify`/`move`/
  `remove`/`convert`/`add_route`) through the server's own validators — they validate
  almost nothing themselves.

**Coherence** (default-on, soft) — **`semantics.py`**: a few invariants the model keeps
losing (right-handed/+Y-up/radians-and-metres, TimeSensor-via-ROUTEs, the HAnim identity
rest pose, PBR-and-the-headlight) surfaced as a SOFT reminder on the relevant call,
de-duped with a re-arm cooldown. Never blocks. The text is spec-grounded and adversarially
verified.

**The occupation gate** — **`gate.py`**: a scene is not done until it renders **non-blank**
under X_ITE (verify-by-render — the silent failure only a render catches), graduated by
irreversibility toward a human sign-off before expensive work.

**Policy** (opt-in) — **`provenance.py`**: enforce the documented/interpretive honesty
discipline against an *optional* asset ledger (ledger-free at L1), graduated
L1 disclosure → L2 sourcing (L3 content rules deferred). A scope extension, off by default. See [`PROVENANCE_BRIDGE.md`](PROVENANCE_BRIDGE.md).

**Configuration** — **`config.py`**: the profile/policy source of truth.

**`eval/`** — the measurement spine (below). **`baml_src/`** — the canonical BAML rule
declaration. **`tests/`** — **105 tests**, all green, + a live end-to-end smoke (8/8).

The roles (classical building practice): the **human is the Architect** — holds intent,
signs off, never automated. **The model is the draftsman** — fast, knows the conventions,
reports back. **Technē is the draftsman's discipline plus the commitment gate.** You do
not pour concrete until the architect has looked.

## Measured, not asserted

"Better" has to be a number, or it's a claim. `eval/run_scripted.py` runs a fixed set of
authoring tasks through `x3d-mcp` **with and without Technē** and tabulates the difference
(deterministic, keyless, CI-able); `eval/run_live.py` does the same with a real model in an
agentic loop (needs an API key). First scripted run (6 tasks, 5 documented mistakes):

> raw lets **2 pass silently** into the scene (the dangerous case) and rejects **3 loudly**
> with no fix; **Technē catches 5/5, every block naming the fix**, at +9 round-trips to a
> *correct* scene — and is invisible on already-correct input (no false positives).

## Run

```sh
pip install -e .            # mcp, Pillow   (baml-py optional: pip install -e .[baml])
python -m techne.server -- python /path/to/x3d-mcp/src/server.py
# the model connects to Technē; everything after `--` launches the upstream server.

# profiles (default = core + coherence; provenance off):
TECHNE_PROFILE=core,coherence,provenance TECHNE_ASSET_LEDGER=drawings/archive.json \
  python -m techne.server -- python /path/to/x3d-mcp/src/server.py
```

## On BAML

We build **on** [BAML](https://github.com/BoundaryML/baml): its Schema-Aligned Parsing is
deterministic argument-repair, and its `@@assert`/`@@check` are validation as language
constructs. `baml_src/` is the canonical rule declaration. The **runtime** validation here
is a deterministic Python mirror, so Technē runs out of the box without a per-call LLM
round-trip — faithful to the determinism commitment. Two BAML gotchas honored: only
block-level `@@` fires (single `@` silently no-ops); and `BamlValidationError` blurs *which*
assertion threw, so every assertion is **named** and mapped back to its correction.

## Provenance of the craft

The X3D silent-failure modes this layer enforces against are **already documented** — in
`docs/x3dpy-bug-report.md` (earmarked for the Web3D Consortium) and in the server's own
`validate_semantic`, which Technē's catalog now mirrors. Technē does not *discover* the
craft by watching usage; for a known craft with a written canon, the canon already exists.
It **converts documented craft-knowledge into enforced mechanism** — the stated workarounds
become executable corrections — and catches the silent failures the validators run *after*
the fact, *before* the call lands.

## Honest scope

Kept narrow on purpose (after an adversarial review): the occupation gate is a
**liveness / blank screen**, not a correctness proof — a non-blank scene can still be
mis-scaled or wrong-coloured; the catalogue is **seeded**, not a community flywheel;
"format-agnostic" is a **hypothesis** (only X3D is built); and the eval is a measurement
*spine* (small N), not a benchmark suite. The cross-call order-of-operations automaton is
**deliberately not built** — instrument first, let usage vote.

Licensed under the [Web3D Consortium Open-Source License](https://www.web3d.org/license),
matching the upstream `x3d_mcp` it contributes to. See also
[`GOALS.md`](GOALS.md) · [`PROFILES.md`](PROFILES.md) · [`PROVENANCE_BRIDGE.md`](PROVENANCE_BRIDGE.md)
· [`INTEGRATION_BACKLOG.md`](INTEGRATION_BACKLOG.md).
