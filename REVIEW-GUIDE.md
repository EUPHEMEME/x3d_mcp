# Review Guide — the x3d_mcp project (offline / NetBeans)

*This branch (`paper/web3d-2026-revision`) holds all three pillars. Open the folder
`x3d_mcp` in NetBeans and everything below is in the tree. **Don't switch git branches
on the plane** — this one has everything, and switching can drop generated `.x3d` files.*

---

## What this project is

**Honest 3-D at machine speed** — a human + AI pair authoring standards-conformant,
interactive Web3D *fast*, without giving up correctness or honesty.

The thesis: a schema certifies the *shape* of a model's output, not whether it is
*conventionally correct*. That gap is **epistēmē** (the closed, decidable schema) vs
**technē** (the contingent craft the schema can't encode). A model can emit tool calls
that pass the X3D XSD in full and still render mis-lit, mis-animated, or blank —
*structurally valid yet semantically dead.*

The frame we sharpened on the way out: this is **non-deterministic composition of
deterministic parts.** The model is a *stochastic department* in an otherwise
deterministic org; correctness and provenance must **traverse the layers**, and the
dangerous failures live in the **seams** between them (a dropped `containerField` is
well-formed where it's emitted and dead two rungs down at the pixels). The discipline is
**graduated** twice: graduated abstraction (the rungs) and graduated verification (a
glance for cheap work, a human signature for irreversible work). "Sourced" = the chain of
custody has to hold all the way down.

Everything in the repo is one of three things: the **mechanism** that closes the gap
(Techne), the **paper** that argues it, or the **artifacts** that prove it (the caves +
HAnim demos).

---

## Pillar 1 — Techne (the deterministic craft layer)  →  `techne/`

An MCP man-in-the-middle proxy: repairs + validates a model's tool-call arguments against
the unwritten craft, returns the *prescriptive correction* as the error, and gates renders
by actually looking at the pixels. **105 passing tests.**

- `techne/techne/` — the package:
  - `proxy.py` — the stateful decision core (start here: `decide()` / `observe_result()`)
  - `rules.py` — the rule→fix catalogue (the documented silent-failure modes)
  - `craft.py` — the deterministic engine; `repair.py` — SAP-style argument repair
  - `gate.py` — **verify-by-render** (the occupation gate, graduated by irreversibility)
  - `provenance.py` — the documented/interpretive/generated honesty gate (the bridge to the caves)
  - `semantics.py` — standing-invariant reminders; `config.py` — profiles; `server.py` — transport
- `techne/tests/` — 105 tests across 9 files · `techne/eval/` — raw-vs-Techne measurement harness
- `techne/baml_src/` — canonical BAML rules · charter docs: `techne/GOALS.md`, `techne/PROFILES.md`

**Read order:** GOALS.md → proxy.py → gate.py → provenance.py.

---

## Pillar 2 — the paper  →  `docs/paper/techne-paper/`

"Technē: A Deterministic Craft Layer for Model Context Protocol Servers, Grounded in
LLM-Authored X3D." **Web3D 2026 Full Papers track — deadline 25 June 2026, 11 PM PDT.**
9 pp of content (exclusive of references), anonymized double-blind build.

- **`techne.pdf`** — read this.
- `techne.tex` — source (build offline with `tectonic techne.tex`)
- `EASYCHAIR-SUBMISSION.md` — the upload packet: title, abstract, keywords, dates
- `innovation-statement.md` — the *separate* AI-Tools competition entry (deadline 30 Aug)
- Backed up to a **private** repo (EUPHEMEME/techne-paper) — double-blind safe, not public.

---

## Pillar 3 — the artifacts (caves + HAnim)

The proof the discipline produces real, honest, navigable Web3D. Both are clean,
self-contained bundles — open them in X3D-Edit.

**`Shasta_X3D_Project/`** — the Merriam caves (Potter Creek + Samwel), to scale from the
digitized survey plates.
- `scenes/potter_creek_cave.x3d`, `potter_creek_floor.x3d`, `potter_creek_plan.x3d`,
  `potter_creek_strata.x3d`, `samwel_strata.x3d`, `fauna_plate.x3d`
- `index.html` + `scenes/*_xite.html` (in-browser viewers) · README inside

**`LOA5_HAnim_Project/`** — the HAnim LOA5 character pipeline.
- `running_human.x3d`, `classroom_skeleton.x3d` (the LOA5 skeleton; ~280 bone meshes)
- viewer `.html`, `paper/x3d-mcp-hanim-demo.pdf`, `images/` · README inside

**The Walk-In Archive** (playable FPS cave, the live demo) — source at repo root:
`build_walk_in_archive.py`, `walk_in_archive.html`, `cave_rooms_manifest.json`,
`start_caves.sh`. Live at euphememe.github.io/shasta-caves (needs internet).

---

## How to review it in NetBeans (offline)

1. **The X3D bundles (easiest):** File → Open File / Open Project → `Shasta_X3D_Project/`
   or `LOA5_HAnim_Project/`. With **X3D-Edit** installed (the Web3D NetBeans module),
   double-click a `.x3d` — you get the validating scene-graph tree, the palette, and
   *Validate*. Walk the tree; check `containerField`s on textures/HAnim joints. Without
   X3D-Edit they open as plain XML (still readable).

2. **The code + paper:** open the `x3d_mcp` folder; use **Window → Files** to browse.
   Open `.py` / `.tex` / `.md` as text. (Full Python code-intelligence needs the legacy
   Python plugin, which can't install offline — but reading works fine.)

3. **Review the build history (the story, fully offline):** right-click the repo →
   **Git → Show History** (or **Team → History**). Git is local; every commit + diff is
   readable on the plane. The recent commits walk the paper revision, the typography pass,
   Techne's build, and the caves.

4. **The paper PDF:** open `docs/paper/techne-paper/techne.pdf`.

---

## Status (as of departure)

- **Paper:** submission-ready; deadline 25 Jun. EasyChair upload is the one remaining step (your login).
- **Techne:** 105 tests green; Points 2 + 3 built; provenance / semantics / edit-post-pass built;
  Point 1 (cross-call automaton) deliberately *not* built (instrument first).
- **Upstream PRs** to Web3DConsortium/x3d_mcp: #9 (render/semantic fixes), #10 (X_ITE backend + validators, draft).
- **Demo:** lean walk-in archive deployed (PBR + streaming). **HELD for Winnemem Wintu review —
  do not publish:** the cultural framing card + the "Magic Pool" reframe.
