# Web3D 2026 AI + Web3D Innovation Competition — Entry Draft

> Status: ready-to-review draft. Verified against the live competition page
> (fetched 2026-06-16) and against the repository. Items the author still
> needs to do before submitting are in the checklist at the bottom.

---

## Title

**Honest 3-D at Machine Speed: a deterministic craft layer and a fully-cited
X3D archive of the Merriam caves**

(Alternate, shorter: *Technē — repairing LLM-authored X3D against the craft the
schema can't encode.*)

## Author

Alexander Hoffman (GitHub **EUPHEMEME**, alex@euphe.me). Solo entry.

Anthropic's Claude (Claude Code) was used as a tool under the author's
direction. Per the ACM Policy on Authorship the AI is not an author; its use is
disclosed here and credit is the author's alone.

---

## Abstract (≈190 words)

Large language models can emit X3D that passes XSD validation yet renders blank,
because the schema cannot encode the *craft*: the dropped `containerField`, the
`EnvironmentLight.global` flag, interpolator `key`/`keyValue` parity, USE-before-DEF.
This entry presents two coupled artifacts. **Technē** is a deterministic
man-in-the-middle (built on BAML) that sits between a model and the `x3d-mcp`
server, intercepts the model's tool-call arguments, and repairs or rejects them
against those unwritten rules — returning the prescriptive correction *as* the
error — then gates "done" behind a render-and-sign-off occupation. It is
smoke-verified end-to-end and covered by 43 unit tests. The second artifact is
what the pipeline produced: a documented, to-scale X3D 4.0 / PBR reconstruction
of the Potter Creek and Samwel caves (excavated 1903–06 under John C. Merriam),
rendered live in X_ITE. Every surface is a faithful vector trace of a published
survey plate or the excavated fauna's original anatomical drawings, fully cited;
fauna are pinned only at literature-documented bone horizons. No AI imagery, no
invented geometry. Together they show AI accelerating Web3D authoring while a
deterministic layer keeps the output honest.

(Word count ~190 — under the 500-word Innovation Statement cap; trim or expand
to taste.)

---

## What it demonstrates (mapped to the judging rubric)

The published rubric weights five criteria. Mapping our evidence to each:

### Innovation & Originality — 30%
- A **craft layer** is a genuinely new framing: not another "LLM writes X3D"
  demo, but a deterministic interceptor that encodes the tacit knowledge an XSD
  *structurally cannot* express, and hands the model the fix rather than a
  diagnostic. It is an MCP man-in-the-middle, not a prompt trick.
- The **trace-don't-invent** discipline (pdftoppm → crop → threshold → potrace →
  SVG → X3D) is an unusual, defensible answer to the "AI hallucinates geometry"
  problem: the AI drives tooling; the geometry comes from the literature.
- The subject matter — a cited 3-D archive of a real, culturally significant
  excavation — is unlike a typical tech-demo entry.

### Technical Excellence — 25%
- Standards X3D 4.0 with PBR, rendered in X_ITE (X3DOM-headless fails; the
  X_ITE-over-HTTP recipe is documented).
- Technē: BAML-defined craft rules, a render-and-sign-off gate, **43 unit
  tests**, end-to-end live smoke test (`smoke_live.py`).
- Two upstream pull requests to the canonical server harden the same path:
  **PR #9** (X3DOM render crashes/escaping + ROUTE semantic false positives) and
  **PR #10** (X_ITE render backend + X3DUOM semantic validators + autofix).

### AI Integration — 20%
- The whole point is *governed* AI authoring: a model proposes X3D tool calls;
  Technē repairs/validates them deterministically; a render gate signs off.
- Machine-readable provenance (`archive.json` catalog, citation-anchored
  `strata_spec.json`) is exactly the "curated training repository with rich
  metadata" the Web3D AI-X3D Working Group has called for — and this work is
  already slated for the X3D Example Archives (X3D4AM).

### User Experience — 15%
- A live, browser-based site with interactive X_ITE viewers and the papers:
  **https://euphememe.github.io/shasta-caves/** — satisfies the "working
  prototype accessible via URL" requirement directly.
- Every scene labels *documented vs. interpretive* on-screen, so a viewer always
  knows what is evidence and what is reconstruction.

### Impact & Scalability — 10%
- The craft layer generalizes to any LLM + MCP X3D pipeline, not just these
  scenes.
- A reusable, cited provenance pattern (label-on-screen + `archive.json` +
  `strata_spec.json`) is a template for honest cultural-heritage 3-D.
- Direct relevance to a standards body: x3d_mcp is the flagship resource of the
  Web3D AI-X3D Working Group.

---

## Artifacts and links to submit

| Required material (per rules) | What we submit |
|---|---|
| Working prototype (browser URL) | **https://euphememe.github.io/shasta-caves/** — live X_ITE viewers + papers |
| Source code (GitHub repo) | **github.com/EUPHEMEME/x3d_mcp** — branch `techne` (Technē craft layer, `techne/`), branch `potter-creek-cave` (caves + HAnim work) |
| Documentation | The three papers below + repo READMEs + this entry |
| Demo video (3–5 min) | **TODO — not yet produced** (see checklist) |
| Innovation Statement (≤500 words) | The Abstract above (≈190 words), expandable |

Supporting documentation (drafts, in `docs/paper/`):
- `honest-3d.pdf` — "Honest 3-D at Machine Speed" (vision paper)
- `merriam-caves.pdf` — the caves
- `x3d-mcp-hanim-demo.pdf` — the HAnim classroom demo

Upstream pull requests (both open against Web3DConsortium/x3d_mcp):
- PR #9 — render / semantic bug fixes
- PR #10 — X_ITE render backend + X3DUOM semantic validators + autofix

Additional components that strengthen the entry (all in-repo): an HAnim LOA5
runner + "living classroom skeleton", a rigged PBR moose (mflux → X3D), and
Technē itself.

---

## Why it advances "AI + Web3D"

Most AI-3D work optimizes for plausible-looking output. This entry optimizes for
*honest, standards-valid, reproducible* output and treats the failure mode
seriously: the gap between "validates" and "renders correctly," and the gap
between "looks right" and "is documented." Technē closes the first with
deterministic repair; the trace-don't-invent + on-screen-provenance discipline
closes the second. The result is a concrete pattern for using AI to build Web3D
content you can actually cite — and it feeds directly into the Web3D
community's stated goal of curated, richly-annotated X3D training repositories.

---

## Honest assessment: effort vs. polish

- **Solid:** Technē (43 tests, live smoke-verified); the caves render live in
  X_ITE on a public site; PRs #9/#10 are real, open, and reviewable; provenance
  metadata exists and is cited.
- **Drafts, not final:** the three papers are marked DRAFT. They are readable
  but not camera-ready.
- **Missing:** the **3–5 minute demo video is required and does not yet exist.**
  This is the single biggest gap to submission.
- **Scope honesty:** this is a research/heritage system, not a consumer product;
  the "User Experience" and "Scalability" criteria are where we are thinnest and
  should be argued, not overclaimed.

---

## Submission checklist (what Alex still needs to do)

Verified facts from the competition page (fetched 2026-06-16):
- **Deadline: September 30, 2026.** Winners + awards: October 15, 2026
  (virtual & in-person).
- **Submit via EasyChair**, through the Web3D 2026 Competitions portal.
- **Contact:** competition@web3d.org.
- Eligibility: open worldwide; individuals or teams up to 5; multiple categories
  allowed.

> ⚠️ **Prize discrepancy — confirm.** The brief said "up to $2,500 in tokens."
> The live page states cash: **Grand Prize $1,000 USD, Second $500 USD**, plus
> honorable-mention recognition / promo / developer-community access. Verify the
> actual prize and form of payment with the organizers before relying on it.

To-do, in order:
1. [ ] **Record the 3–5 min demo video** (required). Suggested arc: the
   blank-render problem → Technē repairing a tool call → live X_ITE flythrough of
   a cave with the documented/interpretive labels visible → the `archive.json`
   provenance. Host on YouTube/Vimeo, unlisted is fine.
2. [ ] **Finalize the Innovation Statement** (≤500 words) — start from the
   Abstract; lead with the craft-layer novelty.
3. [ ] **Confirm repo access for judges** — branches `techne` and
   `potter-creek-cave` are public; ensure the README points judges to both and to
   the live site.
4. [ ] **Create / log into an EasyChair account** and find the Web3D 2026
   Competitions track.
5. [ ] **Pick the category/categories** (the page allows multiple entries) — map
   this work to the best-fitting one(s).
6. [ ] **Confirm team size = 1** and the AI-as-tool disclosure wording is
   acceptable to the organizers.
7. [ ] **Polish at least one paper** (likely `honest-3d.pdf`) to attach as the
   technical documentation, or write a standalone technical overview.
8. [ ] **Verify the live site renders for a cold visitor** (no local files) on a
   stock browser before submitting the URL.
9. [ ] **Email competition@web3d.org** if any rule (prize, eligibility, AI
   disclosure) is unclear.
10. [ ] **Submit before September 30, 2026.**

---

### Source notes
- Competition rules above are quoted/paraphrased from
  https://web3d.siggraph.org/2026/ai-web3d-innovation-competition/ (fetched
  2026-06-16). The page was reachable and specific; no rule was inferred.
- Repo facts verified on 2026-06-16: `techne` branch contains `techne/` with
  `baml_src/` and a `tests/` suite of **43** `def test_` functions; PRs #9 and
  #10 are OPEN against Web3DConsortium/x3d_mcp; the three papers (+ a visual
  changelog) exist as PDFs in `docs/paper/`.
