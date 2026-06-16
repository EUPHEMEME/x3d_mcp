# Technē — a deterministic craft layer for MCP servers

> **Technē** makes a model's tool-call arguments *conform* to a format's unwritten
> conventions — the craft the schema doesn't encode — and holds a render-and-sign-off
> gate before expensive irreversible work, so the craft holds **mechanically**,
> regardless of whether the model comprehended it. The schema is the rules; Technē
> is the craft.

τέχνη (*technē*) — craft-knowledge-with-an-account: the contingent know-how of making
something come out *right*, as distinct from the necessary formal truths of its
structure (*epistēmē*). The root is PIE \*teks-, "to weave / construct" — cognate with
*text* and *texture*. A scene graph, literally.

## The problem

An MCP server over a format like X3D exposes a flat tool+node surface, and a model
can drive it to emit output that is **structurally valid but semantically dead**:

- `containerField` dropped, so an HAnim humanoid renders **invisible**;
- `EnvironmentLight.global` left wrong, so image-based lighting **silently dies**;
- interpolator `key`/`keyValue` lengths mismatched, so an animation **corrupts**.

None of these throw. They pass the XSD. They fail only when you render and *look*.
That is the gap between **epistēmē** (the XSD — decidable, closed) and **technē**
(the contingent craft — which `containerField` for which slot, the order of
operations — that the schema does not encode). A DCC app supplies technē through its
verbs and enforced order of operations; X3D-the-format has only epistēmē. Technē
(the layer) supplies the missing technē.

The governing commitment is **determinism**: craft-rules in prose `instructions` are
advisory (the model *probably* applies them, and the dice reset each session).
Technē instead makes the craft hold *mechanically* — the model's tool-call arguments
pass through a layer that repairs and validates them deterministically before the
real server runs them. Hindsight becomes **mechanism**, not text to re-read.

## Architecture

```
  model  ──tool_call(args)──►  TECHNĒ PROXY  ──forwarded(repaired)──►  x3d-mcp
 (draftsman) ◄──result/        1 SAP repair                            (real server)
            prescriptive       2 craft @@assert/@@check
            correction         3 occupation gate: render + human look
```

Three insertion points, in dependency order:

| Point | What | Status |
|---|---|---|
| **2 — argument repair + structural validation** | per tool-call SAP repair + craft-rules | **built** (`craft.py`, `proxy.py`, `repair.py`, `baml_src/`) |
| **3 — occupation gate** | not done until validated AND rendered-non-blank AND (for expensive renders) the architect has looked | **built** (`gate.py`; uses the X_ITE backend) |
| **1 — cross-call craft-automaton** | order-of-operations state machine | **deliberately NOT built** — instrument first, let usage vote (TECHNE_SPEC §6) |

The roles (classical building practice): the **human is the Architect** — holds
intent, signs off, never automated. **Claude is the draftsman** — fast, knows the
conventions, reports back. **Technē is the draftsman's discipline plus the commitment
gate** — it makes the draft conform, and holds the hard boundary between cheap
reversible drafting and costly irreversible building. You do not pour concrete until
the architect has looked.

## What's here

- **`techne/rules.py`** — the rule→fix catalog: `docs/x3dpy-bug-report.md` reread as
  `{rule_name: (severity, prescriptive_correction, source)}`. The error message IS
  the fix.
- **`techne/craft.py`** — the deterministic craft engine: the four documented
  silent-failure modes. Determinable rules **repair**; unrepairable ones **block +
  return the correction**.
- **`techne/repair.py`** — deterministic SAP-style argument repair (the dependency-free
  baseline for BAML's `b.parse`).
- **`techne/proxy.py`** — the stateful decision core (scene state from `create_node`
  results; per-tool adapters; `decide()`/`observe_result()`).
- **`techne/gate.py`** — the occupation gate, graduated by irreversibility.
- **`techne/server.py`** — the MCP man-in-the-middle transport.
- **`baml_src/`** — the canonical BAML declaration of the craft-rules (block-level
  `@@assert`/`@@check`, each named back to the catalog).
- **`tests/`** — 31 tests, all green.

## On BAML

We build **on** [BAML](https://github.com/BoundaryML/baml): its Schema-Aligned Parsing
is deterministic argument-repair, and its `@@assert`/`@@check` are validation as
language constructs. `baml_src/` is the canonical rule declaration. The **runtime**
validation here is a deterministic Python mirror so Technē runs out of the box without
a per-call LLM round-trip — faithful to the determinism commitment. To wire the BAML
SAP engine, `baml-cli generate` the client and call `b.parse.ValidateX(json_str)` (no
LLM call) on the repair path. Two BAML gotchas honored: only block-level `@@` fires
(single `@` silently no-ops); and `BamlValidationError` blurs *which* assertion threw,
so every assertion is **named** and mapped back to its prescriptive correction.

## Run

```sh
pip install -e .            # baml-py, mcp, Pillow
python -m techne.server -- python /path/to/x3d-mcp/src/server.py
# the model connects to Technē; everything after `--` launches the upstream server.
```

## Provenance

The X3D silent-failure modes this layer enforces against are **already documented** in
`docs/x3dpy-bug-report.md`, earmarked for Don Brutzman at the Web3D Consortium. Technē
does not *discover* the craft by watching usage — for a known craft with a written bug
catalog, the canon already exists. Technē **converts documented craft-knowledge into
enforced mechanism**: the bug report's stated workarounds become executable
corrections. The instrumentation (Point 1, §6) only surfaces the *next* undocumented
silent-failure mode for promotion.
