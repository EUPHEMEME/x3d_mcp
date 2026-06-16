# Brief for the Web3D AI-X3D meeting — Tue 16 Jun 2026, 8 AM Pacific

Prep for Alexander Hoffman. Invited by Don Brutzman; "people will be interested in
your progress and assessment." WG home: <https://www.web3d.org/working-groups/ai-x3d>.
Chair: Dr. Jens Schneider (HBKU); co-chairs Anita Havele (Web3D), Aaron Bergstrom (UND).

> Framing note (per Alex): present **our** program on its own terms — we are *not*
> folding the WG charter into the paper. But the overlap is large, and there is
> real collaboration to propose.

---

## 1. Progress — what exists now (the "show", in one breath)

A single research program: **provenance-disciplined, standards-conformant X3D
authored by a human–AI pair** — "Honest 3-D at Machine Speed." Three interlocking
artifacts, all built through the open Web3D toolchain:

- **Toolchain.** Work on the X3D MCP server (the WG's own `x3d_mcp`): an async,
  loopback-served, asset-aware **X_ITE render backend**; **semantic validators**
  built from X3DUOM (containerField with the canonical fix suggested, USE-before-DEF,
  interpolator key/keyValue length) + an `autofix_x3d`; the **verify-by-render** loop.
  Headline finding: *the choice of renderer is a correctness property, not an
  aesthetic one* — X3DOM renders neither PBR nor HAnim headless; X_ITE renders both.
- **Character pipeline.** The canonical 150-joint **HAnim LOA5** figure driven by our
  own motion; a runner and a "living" classroom skeleton; a `PhysicalMaterial` PBR
  pass; locally-generated textures via **mflux** (FLUX.1 on Apple MLX).
- **Heritage archive (flagship).** Potter Creek & Samwel Caves (Shasta County),
  excavated under John C. Merriam 1903–06 — rebuilt to scale with PBR, a **documented
  3-D archive** (faithful vector traces of every published survey plate + the fauna's
  original anatomical drawings, fully cited, *no AI imagery*), and **bone-horizon
  section scenes** that pin fauna only at depths the literature records.

Deliverables ready to show: the **24-page vision paper** (`docs/paper/honest-3d.pdf`),
a **browsable gallery folder** (`Shasta_X3D_Project/index.html`), and the live scenes.

## 2. Assessment — the three claims we can defend

1. **A human–AI pair can author conformant interactive 3-D at machine speed without
   sacrificing honesty** — *if* the agent can see what it makes, integrates the actual
   ISO standards, and holds a hard provenance line. Demonstrated, not asserted.
2. **Renderer = correctness.** For an authoring agent, schema-valid ≠ correct; only an
   X3D-4.0-complete renderer (X_ITE) lets the agent verify PBR + HAnim. This is a
   concrete best-practice the WG could adopt.
3. **Provenance discipline is a transferable method.** Documented-vs-interpretive
   separation + trace-don't-invent + machine-readable citation metadata
   (`archive.json`, `strata_spec.json`) makes AI-authored heritage 3-D trustworthy.

## 3. Where our work meets the WG's stated goals (collaboration map)

| WG objective / resource (from their page) | What we already have to offer |
|---|---|
| **`x3d_mcp`** — "exposes X3D capabilities to LLMs via MCP" (their flagship tool) | X_ITE render backend, X3DUOM semantic validators + autofix, verify-by-render — upstreamable now |
| "Best practices for AI in X3D" | The *renderer-is-correctness* finding; describe→build→validate-both→render canonical path |
| "Curated training repositories … with **rich metadata**" | Provenance metadata model: `archive.json` + per-scene documented/interpretive tags + source citations |
| "Address **ethical considerations** in AI within X3D" | The whole provenance-discipline + no-AI-imagery ethic; the vision paper's ethics section |
| "X3D object creation with LLMs"; "Prompt Engineering for X3D … with LLMs" | Worked case studies (HAnim demos, caves) — candidate evaluation content / examples |
| "MCP investigation for asset cataloging" | The MCP describe/validate/render tooling and provenance-tagged catalog pattern |
| "Multimodal support (text, images …)" | The mflux image→`ImageTexture`→3-D loop |
| Upstream toolchain health | Standing bug reports vs `x3d.py` (drops containerField on non-default fields; `EnvironmentLight.global` defaults true vs spec false); X3DOM HAnim/PBR gaps |

## 4. Proposed collaboration asks (concrete, low-friction)

- Contribute the **X_ITE render backend + semantic validators** upstream to the
  WG's `x3d_mcp` (PR to Web3DConsortium) — *awaiting Alex's go-ahead.*
- Offer the **provenance/metadata schema** as input to the "rich-metadata training
  repository" effort.
- Offer **"renderer is a correctness property"** as a documented WG best-practice.
- Share the caves archive as a **provenance-tagged example/eval set**.

## 5. Talking points (≤5 min)

1. Who/what: a human–AI pair, the open Web3D stack, a personal subject (Merriam's caves).
2. The thesis in one line: *honest 3-D at machine speed.*
3. The one hard finding: renderer = correctness (X3DOM vs X_ITE, headless).
4. The discipline: documented vs interpretive, trace-don't-invent, no AI imagery — show `pcc_strata`.
5. The ask: fold our MCP backend/validators + provenance metadata into the WG's `x3d_mcp` and best-practices.

*Open items needing Alex's decision:* (a) green-light the upstream PR to
Web3DConsortium/x3d_mcp; (b) how much of the caves work to make public vs. keep the
protected cave location private (Winnemem Wintu sacred site).
