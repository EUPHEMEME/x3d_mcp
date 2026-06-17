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
(X3D) with a documented bug catalogue. It is a candidate best-practice and
tooling contribution to the WG's `x3d_mcp`, not "infrastructure the field already
has." Claims kept narrow on purpose.

---

## The three goals

### 1. Output quality — does the scene render *right*, not just validate?
The floor: output that passes the XSD yet renders wrong or blank. Mechanisms:
- **Craft catalogue** (`rules.py`) — documented silent-failure modes turned into
  deterministic, *prescriptive* corrections ("use `containerField='baseTexture'`",
  not "invalid"). Built: containerField slots, `EnvironmentLight.global`,
  interpolator `key`/`keyValue` parity, USE-before-DEF. *Grow this as new modes
  surface.*
- **The gate, named honestly.** It is a **liveness / blank screen** — it catches
  the documented *blank-producing* bugs (a dropped `containerField` renders
  nothing) and surfaces the image for a look. It is **not** a correctness proof;
  a non-blank scene can still be mis-scaled, off-camera, or wrong-coloured.
  Correctness stays the human's job. (Drop the phrase "the renderer is a
  correctness property.")
- **Look up, don't recall** — lean on `describe_node`/`autofix` so the model
  builds against the real field/containerField table, not its memory.

### 2. Coherence — is the scene internally consistent, across a long session?
LLMs *drift*: they forget the handedness of the axes, the unit, the timer
conventions, what they already DEF'd. Coherence mechanisms:
- **Standing semantics, injected not hoped.** The few invariants the model keeps
  losing — coordinate system / handedness, default units, `TimeSensor`
  conventions, that an `HAnimJoint` rest pose is identity — surfaced
  deterministically every relevant call, so they hold by mechanism rather than by
  a prompt the model may not re-read. *(To build.)*
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

## The spine: measure it
"Better" must be provable, or it is just a claim (the review's sharpest demand).
The next build is an **evaluation harness**: run a fixed set of X3D authoring
tasks through `x3d_mcp` **with and without Technē**, and report:
- **first-pass render-correctness** (fraction non-blank / passing on the first try),
- **round-trips to a correct scene** (tool calls / render attempts),
- **silent failures caught** (blank renders / dropped containerFields prevented),
- **tokens / context spent**.

Every goal above is scored against these. Coherence and efficiency are the
priorities precisely because they are the columns of this table we can move now.

## Out of scope (for now)
The venture / "TechnicalDiplomacy" / narrative framings belong to EUPHEME's
separate roadmap and are **not** part of Technē until deliberately specified.
Technē here is, and stays, about reliable LLM-authored X3D for Web3D.
