# Technē — Implementation Specification

**A deterministic craft layer for MCP servers, built on BAML.**

*Status: design spec, ready to implement. Target repo: EUPHEMEME (GitHub).*
*Audience: the x3d-mcp Claude Code session. You have the real repo in front of you; this document has the reasoning and the shape. Where this spec and the actual `x3d-mcp` tool signatures disagree, the real signatures win — but preserve the architecture below.*

---

## 0. Read this first: what you are building and why

You (a previous instance, in a long session) built an MCP server over X3D and discovered the hard way that a flat tool+node surface lets a model emit **structurally valid but semantically dead** output — `containerField` dropped so an HAnim humanoid renders invisible, `EnvironmentLight.global` left wrong so image-based lighting silently dies, interpolator `key`/`keyValue` lengths mismatched so an animation corrupts. None of these throw. They pass the XSD. They fail only when you render and *look*.

That whole class of failure has a name in the philosophy of craft: it is the gap between **epistēmē** (the necessary, formal structure — the XSD, which is decidable and closed) and **technē** (the contingent craft-knowledge of making the thing come out *right* — the order of operations, the conventions, the "which containerField for which slot" that the schema does not encode). A schema is epistēmē. A DCC application like Cinema 4D or ZBrush supplies technē through its *verbs* and its *enforced order of operations*. X3D-the-format has only epistēmē and assumes the technē lives elsewhere. **Technē (the layer) supplies the missing technē.**

The governing design commitment is **determinism**. Putting craft-rules in prose `instructions` is advisory — the model *probably* reads them, *probably* applies them. That is rolling dice every session, and the dice reset when a fresh model connects. Technē instead makes the craft hold *mechanically*, whether or not the model comprehended it: the model's tool-call arguments pass *through* a layer that repairs and validates them deterministically before the real server ever runs them. The hindsight from one session becomes *mechanism* the next model cannot route around, rather than text it must re-read and re-honor.

A useful frame from classical building practice. The production chain is: **Architect/Réalisateur → draftsmen → draft → review → redraft → report back to architect → source materials → hire labor → build → occupy.** Map the roles:

- **The human (you, Alexander) is the Architect/Réalisateur.** Holds *intent* — "photoreal moose munching grass." Decides what is true. Signs off. This is the decisive-moment layer; no automaton authors it, and Technē never reaches into it.
- **Claude is the draftsman.** Brilliant, fast, knows the conventions — but does not originate intent and does not sign off on the build. The draftsman *reports back*.
- **Technē is the draftsman's discipline plus the commitment gate.** It makes the draft *conform* (deterministic repair + validation of tool-call arguments) and it *holds the sign-off gate* — the hard, expensive, irreversible boundary between cheap reversible drafting (paper, revisions, delete-and-redraw) and costly irreversible building (sourcing materials, hiring labor, pouring concrete — or here: the hours-long offline photoreal render). You do not pour concrete until the architect has looked.

Technē does **not** try to make Claude into the architect. Trying to make a state machine originate intent — trying to make Cartier-Bresson jump out of the JPEG codec — is a category error. The codec's whole dignity is that it is *faithful*: it carries what the eye composed without silently corrupting it. Technē is the faithful codec, the loom that does not drop threads. The eye that decides, and the eye that occupies, stay human.

---

## 1. Why BAML, and exactly where the seam is

We build **on** [BAML](https://github.com/BoundaryML/baml) (BoundaryML), not from scratch, because BAML already *is* the codec layer, productized, by people who share this exact philosophy. Concretely:

- BAML's **Schema-Aligned Parsing (SAP)** is deterministic argument-repair. It follows Postel's Law — "be liberal in what you accept, transform it to match your schema using edit-distance" — fixing broken JSON, markdown-wrapping, chain-of-thought preambles, and coercing types. That is exactly the "repair the model's sloppy output into a conforming draft" move that `autofix_x3d` did by hand, generalized into a Rust engine.
- BAML's **`@@assert` / `@@check`** are validation as first-class language constructs. `@@assert` is *blocking* — it throws a `BamlValidationError` at runtime if the predicate fails. `@@check` is *non-blocking* — the data is returned either way and you can read whether the check passed. These map directly onto our two gates: `@@assert` is the **hard** gate (the architect's sign-off before pouring concrete), `@@check` is the **soft** "looks right?" advisory gate.
- BAML's founding thesis *is* the epistēmē/technē split: "turn prompt engineering into schema engineering." They built the tooling on the epistēmē side and left exactly the parts we need to add.

**What BAML covers (use it, do not rebuild it):**

| Concern | BAML construct |
|---|---|
| Repair sloppy tool-call arguments into conforming shape | SAP (automatic) |
| Validate structural craft-rules (containerField correct, key/keyValue parity, USE-after-DEF present, `global` set) | `@@assert` (throws) / `@@check` (flags) |
| Graduated soft vs hard gate | `@@check` vs `@@assert` |

**What BAML does NOT cover — these are Technē's original layer, yours to build above BAML:**

1. **MCP topology.** BAML sits where *your code calls a model* (app → model). The X3D problem is the inverse: *a model calls tools* (model → tool). Nobody has pointed SAP-style repair at the **tool-call arguments a model emits into an MCP server, intercepted in-transport.** That redirection is the novel core.
2. **The render-and-occupy sign-off.** BAML `@@assert` is a Jinja predicate over an already-parsed *value*. It **cannot execute a renderer**, get an image back, and assert the pixels are non-blank. The occupation gate — *did the moose render as a moose* — is side-effecting computation outside assertion scope. BAML can assert *that a render receipt is non-empty* if you feed the receipt in as a field; the *act of rendering and the human look* are your layer.
3. **The cross-call craft-automaton.** BAML is stateless-per-function; its assertions are scoped to one call's output. There is no construct for "what state is the scene in across calls" or "which transition is legal next." The order-of-operations / partial-order logic is entirely yours.

**Critical BAML gotcha — do not reproduce the bug we are trying to kill.** BAML itself has a silent-failure trap: field-level `@assert` (single `@`) inside test blocks is accepted by the linter but *silently ignored at runtime* — tests appear to pass while validating nothing. Only block-level `@@assert` / `@@check` (double `@`) actually fire. **Always use the double-`@` block-level form.** Separately, when an assertion fails, BAML's `BamlValidationError` currently blurs *which* assertion threw (per-assertion detail is discarded upstream). Since the entire value of the bug catalog is knowing *which* silent-failure occurred ("containerField on line 12", not just "draft rejected"), **wrap the `BamlValidationError` and re-attach the rule identity yourself** — give every assertion a custom name and map it back to a prescriptive correction string. That difference — "rejected" vs "rejected: use `containerField='baseTexture'`" — is the whole prescriptive-correction insight from the original session; preserve it.

---

## 2. Architecture

```
   ┌─────────────┐   tool_call(args)   ┌──────────────────────────────┐   forwarded(repaired args)   ┌───────────────┐
   │   Claude    │ ──────────────────► │        TECHNĒ PROXY          │ ───────────────────────────► │   x3d-mcp     │
   │ (draftsman) │                     │   (MCP man-in-the-middle)    │                              │  real server  │
   └─────────────┘ ◄────────────────── │                              │ ◄─────────────────────────── └───────────────┘
                     result /          │  per call:                   │       server result
                     prescriptive      │  1. route args through BAML  │
                     correction        │     fn  → SAP repair         │
                                       │  2. BAML @@assert/@@check     │
                                       │     craft-rules (throws/flags)│
                                       │  3. (on relevant verbs) gate: │
                                       │     state-machine legal-next  │
                                       │  4. (on completion) occupation│
                                       │     gate: render + human look │
                                       └──────────────────────────────┘
```

Three insertion points, in dependency order:

- **Point 2 — in-call argument repair + structural validation.** Deterministic. Sequence-agnostic (works even if X3D authoring turns out not to sequence at all). This is **BAML per tool-call** + the proxy that routes through it. *Build first — it is mostly configuration of an existing engine, and it handles the largest fraction of documented pain.*
- **Point 3 — completion / occupation gate.** "Not done until `validate_semantic` is clean AND render returned a non-blank image AND (for expensive renders) the architect has looked." Also sequence-agnostic. **Requires the X_ITE render backend** (see §5 — the original session already flagged this as highest-value because X3DOM returns *blank* for HAnim, the flagship case). *Build second; it is the first genuinely original piece.*
- **Point 1 — the cross-call craft-automaton.** Tracks scene state, enforces legal next-transitions on the *few* hard edges. **This is the part we are NOT sure is needed** — see §6. *Build last, after your own usage has voted on whether the craft sequences. Do not build it speculatively.*

---

## 3. The per-tool pattern (Point 2) — the concrete first artifact

For **each** x3d-mcp tool that can produce a silent-failure, define a BAML function whose input type mirrors the tool's arguments. SAP repairs the model's args; `@@assert`/`@@check` enforce the craft-rules.

Below is the pattern for a texture-attachment verb. **Adapt names to the real tool signature in the repo** — the real tool may be `create_texture` / `set_texture` / a generic node-builder with a `containerField` parameter; the rule table below is the *content*, the BAML shape is the *form*.

```baml
// techne/baml_src/attach_texture.baml
//
// Craft layer for X3D texture attachment.
// Source of truth for the rules: docs/x3dpy-bug-report.md (Bug 1: dropped containerField).
// The known-correct containerField per texture slot is the technē the XSD does not encode.

class TextureAttachment {
  // The node this texture binds onto (e.g. an Appearance).
  parent_node     string

  // The texture node type being attached.
  texture_type    string

  // THE craft-critical field. x3d.py drops this for non-default placement,
  // yielding flat/invisible PBR. It MUST be present and MUST match the slot.
  container_field string

  // The image/url source for the texture.
  url             string
}

// Function the proxy calls with the model's raw tool-call args.
// SAP repairs shape/JSON/coercion automatically before assertions run.
function ValidateTextureAttachment(raw: TextureAttachment) -> TextureAttachment {
  client CustomFast        // any configured client; this fn is validation-shaped
  prompt #"
    Return the texture attachment unchanged. {{ ctx.output_format }}
    {{ raw }}
  "#
}

// --- Craft-rules as BLOCK-LEVEL assertions (double @@, so they actually fire) ---
// Each @@assert has a custom name -> the proxy maps that name to a prescriptive fix.

class TextureAttachment {
  parent_node     string
  texture_type    string
  container_field string
  url             string

  // HARD rule: containerField must be present (non-empty). Dropping it is Bug 1.
  @@assert(container_field_present, {{ this.container_field|length > 0 }})

  // HARD rule: the containerField must be the correct slot for the texture type.
  // This is the lookup the XSD cannot express. Encode the known table.
  // (Example mapping — REPLACE with the authoritative slot table from the spec/repo.)
  @@assert(container_field_correct, {{
       (this.texture_type == "PhysicalMaterial.baseTexture"        and this.container_field == "baseTexture")
    or (this.texture_type == "PhysicalMaterial.normalTexture"      and this.container_field == "normalTexture")
    or (this.texture_type == "PhysicalMaterial.emissiveTexture"    and this.container_field == "emissiveTexture")
    or (this.texture_type == "PhysicalMaterial.occlusionTexture"   and this.container_field == "occlusionTexture")
    or (this.texture_type == "PhysicalMaterial.metallicRoughnessTexture" and this.container_field == "metallicRoughnessTexture")
  }})

  // SOFT advisory: url should resolve to a known image extension. Flag, don't block.
  @@check(url_has_image_ext, {{
       this.url|lower is endingwith(".png")
    or this.url|lower is endingwith(".jpg")
    or this.url|lower is endingwith(".jpeg")
  }})
}
```

Repeat this pattern for the other documented silent-failure modes. At minimum, ship BAML functions for:

1. **Texture / containerField** (Bug 1 — above).
2. **Interpolator `key`/`keyValue` length parity.** `@@assert(interp_lengths_match, {{ this.key|length == this.key_value|length / this.components_per_key }})` — adapt the arithmetic to how the tool represents keyValue (it is flattened; divide by the per-key component count for the interpolator type). This is a *silent animation-corruption* bug; the original session risked exactly this baking the moose.
3. **`EnvironmentLight.global`.** x3d.py defaults `global` to `True` but the spec default is `false`, so x3d.py *omits* it and image-based lighting silently dies. `@@assert(envlight_global_set, {{ this.global is defined }})` — and on repair, *write the field explicitly* rather than relying on the default. The moose almost certainly had dead IBL because of this.
4. **DEF-before-USE ordering.** For any tool that emits a `USE`, assert the referenced `DEF` name has already been defined in the scene-so-far. NOTE: this one *needs cross-call state* (it depends on what was defined earlier) — so it straddles Point 2 and Point 1. Implement the *single-call* form here (USE references a name present in the current call's payload) and defer the *cross-call* form (USE references a DEF from an earlier call) to the automaton in §6.

---

## 4. The proxy handoff (Point 2 plumbing)

The proxy is an MCP server that fronts the real `x3d-mcp` — a transport-level man-in-the-middle. The model connects to **Technē**; Technē connects to **x3d-mcp**.

Per `tools/call` it receives:

1. **Identify the tool.** If the tool has a registered BAML craft-function, route its arguments through that function. If not, forward unchanged (Technē is opt-in per tool; absence of a rule means "no known silent-failure here, pass through").
2. **SAP repair.** The BAML call repairs the arguments into conforming shape. Capture the repaired args.
3. **Assertions.** If a `@@assert` throws `BamlValidationError`: **do not forward to the real server.** Instead return a *prescriptive correction* to the model — look up the failed assertion's custom name in a rule→fix map and return the exact fix string (e.g. `container_field_correct` → "Use containerField='baseTexture' for PhysicalMaterial.baseTexture"). This is the rail-back-onto-the-path move; the error message is the correction, not a bare "invalid". `@@check` failures attach as *warnings* alongside a forwarded call (advisory, non-blocking).
4. **Forward.** On clean assertions, forward the *repaired* args to the real x3d-mcp and relay its result back.

Implementation notes:

- **Language:** BAML generates a native client in Python or TypeScript. Match whatever `x3d-mcp` is written in so the proxy can be one process. (If x3d-mcp is Python, generate the Python `baml_client`.)
- **The rule→fix map** is the single most important hand-authored asset and it is *small*. It is the bug catalog (`docs/x3dpy-bug-report.md`) reread as `{assertion_name: prescriptive_correction_string}`. Keep it in one file. Every entry is a documented silent-failure with its stated workaround turned into an executable correction.
- **Do NOT** put craft guidance only in the proxy's prose `instructions`. The whole point is mechanism over advice. Instructions may *describe* the path for the model's benefit, but the *enforcement* is the BAML assertion + the prescriptive return, which holds regardless of whether the model read the instructions.

---

## 5. The occupation gate (Point 3) — build the eyes

The completion gate is "not done until validated AND rendered-non-blank AND (for expensive renders) architect has looked." BAML cannot do the rendering (side-effecting), so this is your layer, and it has a hard prerequisite the original session already identified:

**The render backend must be X_ITE, not X3DOM.** The HAnim conformance paper in the repo states plainly that **X3DOM cannot render an HAnim skeleton; X_ITE can.** The existing `render_image` is X3DOM-based, so it returns a *blank* for exactly the HAnim humanoids this project exists to showcase — meaning the completion gate would be checking a blank and passing it. **Build an X_ITE render backend** (headless browser with `--allow-file-access-from-files` so it can fetch the scene) so the gate has working eyes. This was already the #1 recommended next build for independent reasons; it is also the precondition for Point 3 having any teeth.

The gate logic (your layer, around BAML):

1. On a completion signal (model declares the artifact done), run `validate_semantic`. If not clean → block, return the validation errors as prescriptive corrections.
2. Render via X_ITE. If the returned image is blank/empty (all-background, no geometry) → block; this is a silent-failure that *only* the render catches. Feed the render *receipt* (non-blank boolean, dimensions, maybe a luminance-variance number) into a BAML `@@assert(render_non_blank, ...)` if you want the check itself to live in BAML — but the *act* of rendering is your code.
3. **Graduated by cost.** This is the commitment-gate-proportional-to-irreversibility idea. There are (at least) two gates:
   - **Cheap gate** (before the fast X3DOM/X_ITE preview render): soft, automatic, "looks non-blank?" — `@@check`-style, advisory.
   - **Expensive gate** (before the hours-long *offline photoreal* render — the "source materials / hire labor / pour concrete" moment): **hard**, requires the *architect* (the human) to look at the preview and sign off. The draftsman (Claude) must never trigger the expensive irreversible render on its own authority. Surface the preview image and *stop*, waiting for human sign-off, before committing the expensive build.

The principle: the sign-off discipline fires *proportional to what is downstream*. A light "looks right?" before cheap reversible work; a hard "architect, sign here" before expensive irreversible work.

---

## 6. The craft-automaton (Point 1) — DO NOT build yet; instrument instead

This is the cross-call state machine that would enforce order-of-operations — "geometry before bind-material", "DEF before USE across calls". **We are genuinely unsure whether X3D authoring sequences cleanly enough to justify it.** Building a state machine that straitjackets open-ended authoring would be the category error from §0 — trying to make the codec author the decisive moment. The breadth of "what scene to build, where to place things" *should* resist sequencing; that is the architect's free field, not a defect.

So treat sequencing as an **empirical question your own usage answers**, not a thing to decide up front:

- The likely truth is a **partial order**, not a total order: a *few* hard edges with real precedence (cross them and the render silently dies), and a large open space where any order is fine. The bug catalog already names the first hard edges — containerField (the texture edge), USE-after-DEF (the reference edge). You do not need the whole automaton; you need the two or three edges that, when crossed, render silently wrong.
- **Instrument first.** As scenes are built through the Point-2/Point-3 layer, log the *order of verbs that produced a clean, non-blank render*. After ~10 scenes, inspect:
  - **Variance-with-convergence** (different scenes, same verb sequence) → the craft sequences; the automaton is real; build it, enforcing only the hard edges.
  - **Variance-without-convergence** (successful scenes show genuinely different orders) → it resists; the automaton is the wrong move; you correctly did not build a straitjacket. Keep only the *cross-call assertions* (USE-references-an-earlier-DEF) as stateful checks, without a full transition automaton.

The logging is a near-free byproduct of using the layer. Let the data vote before committing to Point 1.

---

## 7. Build order (the dependency-ordered plan)

1. **Repo scaffold.** `techne/` in EUPHEMEME. `techne/baml_src/` for BAML functions; generate `baml_client` in the language matching x3d-mcp. Add BAML as a dependency. Wire CI to run BAML tests (using block-level `@@assert`/`@@check` — the single-`@` form silently no-ops in tests).
2. **Rule→fix map.** Transcribe `docs/x3dpy-bug-report.md` into `{assertion_name: prescriptive_correction}`. This is the catalog as executable corrections. Small file, high value.
3. **Point 2 — BAML craft-functions** for the four documented modes (texture/containerField, interpolator parity, `EnvironmentLight.global`, single-call DEF/USE). Each `@@assert` named and mapped to a fix.
4. **Point 2 — the proxy.** MCP man-in-the-middle: route args → SAP repair → assertions → prescriptive-correction-on-fail / forward-on-pass. Opt-in per tool.
5. **Point 3 — X_ITE render backend.** Replace/augment X3DOM `render_image` so HAnim renders non-blank. This unblocks the occupation gate AND was already the top independent priority.
6. **Point 3 — occupation gate**, graduated: cheap soft gate before preview render; hard human-sign-off gate before expensive offline photoreal render.
7. **Instrument for Point 1.** Log verb-order-to-clean-render. Do not build the automaton. Let ~10 scenes vote (§6), then decide.

Commit each numbered step separately with a message naming which Technē point it implements, so the git history reads as the architecture.

---

## 8. Naming and framing for the repo

The layer is **Technē** (τέχνη) — Greek for craft-knowledge-with-an-account, the contingent know-how of making something come out right, as distinct from the necessary formal truths of its structure (epistēmē). Etymology runs through the PIE root *\*teks-*, "to weave/fabricate/construct" — cognate with *téktōn* (carpenter/builder) and with *text*/*texture* — so the weaving-disparate-elements-into-an-ordered-whole image is literally a scene graph. The schema is the epistēmē, enforced by the XSD; Technē is the contingent craft, enforced by the layer.

One-line description for the README:

> **Technē** — a deterministic craft layer for MCP servers, built on BAML. It makes a model's tool-call arguments *conform* to a format's unwritten conventions (the craft the schema doesn't encode), and holds a render-and-sign-off gate before expensive irreversible work — so the craft holds mechanically, regardless of whether the model comprehended it. The schema is the rules; Technē is the craft.

Provenance note worth putting in the repo (it is the strongest validation of the whole effort): the X3D silent-failure modes this layer enforces against are *already documented* in `docs/x3dpy-bug-report.md`, earmarked for Don Brutzman at the Web3D Consortium. Technē does not *discover* the craft by watching usage — for a known craft with a written bug catalog, the canon already exists. Technē *converts documented craft-knowledge into enforced mechanism*: the bug report's stated workarounds become executable corrections. The layer's job at the margins (the instrumentation in §6) is only to surface the *next* undocumented silent-failure mode for promotion — the next catalog entry, found in the wild.

---

## 9. What NOT to do (the traps, collected)

- **Do not** put craft-enforcement only in prose `instructions`. Advisory ≠ deterministic. Enforce in BAML assertions + prescriptive returns.
- **Do not** use single-`@` `@assert`/`@check` in test blocks — they silently no-op. Use `@@`.
- **Do not** let `BamlValidationError` blur which rule failed — name every assertion, map names to prescriptive fixes, re-attach identity when you catch.
- **Do not** rebuild SAP — it is BAML's battle-tested core. Stand on it.
- **Do not** build the craft-automaton (Point 1) speculatively. Instrument, let usage vote.
- **Do not** make the gate check a blank render — build X_ITE first so the eyes work for HAnim.
- **Do not** let the draftsman (Claude) trigger the expensive offline render on its own authority — hard human sign-off gates the irreversible-expensive boundary.
- **Do not** try to make the layer originate intent or author scenes. It is the faithful codec, not the architect's eye. It carries the decisive moment; it does not compose it.
