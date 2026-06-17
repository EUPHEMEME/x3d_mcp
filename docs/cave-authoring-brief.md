# Directed authoring brief — Potter Creek & Samwel Caves → honest X3D

*A story-based, technically-directed prompt for converting the documented cave
papers into an X3D 4.0 model. The **architect** (human) directs; the **draftsman**
(an LLM driving the x3d MCP) executes; **Technē** (the craft layer) enforces. This
brief is the architect's standing instruction — paste it as the system/opening
prompt for a cave-authoring session, or follow it directly.*

Ground truth lives in the repo, not in your memory: `drawings/strata_spec.json`
(the stratigraphy + bone-horizon markers + the binding `must_not_invent` list),
`drawings/archive.json` (the cited public-domain plates + their traces), the two
papers `docs/paper/merriam-caves.tex` and `docs/paper/honest-3d.tex`, and the
existing generators `generate_cave.py` / `generate_samwel.py` /
`generate_fauna_strata.py` / `generate_cave_textures.py`. **Read the source before
you build; quote a citation before you call anything documented.**

---

## 1. The story (the narrative spine)

In 1902–1906 John C. Merriam's Berkeley party dug two limestone caves in the
McCloud River canyon, Shasta County, California. **Potter Creek Cave** — a single
107-ft chamber, roof ~75 ft, ~30 ft wide, entered through a 42-ft pit, its floor
two coalescing breccia fans — gave up a 52-species Pleistocene fauna (21 extinct:
the shrub-ox *Euceratherium*, the short-faced bear *Arctotherium*, the Shasta
ground sloth *Nothrotheriops*, mammoth, horse, bison, camel) sealed in clay and a
stalagmite-cemented "false floor." **Samwel Cave** — *Sawal*, the
Winnemem Wintu's *Cave of the Magic Pools* — descends through named chambers (the
Gate, Pleistocene Hall, Chamber One, Merriam's Chamber) to a deep drop into
**Chamber Two**, at whose bottom lies the **Magic Pool**; Wintu tradition tells of
a maiden who fell ~90 ft seeking it.

Carry the human frame **in-scene, not just in a footnote**: the Winnemem Wintu
sacred status; Shasta Dam flooding the McCloud canyon (1935–45); the **contested**
gloss of *sawal* (the sources disagree — "grizzly bear" vs "holy place" — do **not**
resolve it); and **withhold the protected physical location / coordinates**.

The model is not a diorama. It is *the survey record, made spatial* — a reader
should be able to see exactly how much is measured and how much is reconstruction.

---

## 2. The honesty contract (binding — Technē enforces)

Every feature is one of three states, and every scene says which on screen:

- **documented** — to-scale geometry traceable to a cited plate/measurement
  (black labels). The Potter Creek chamber envelope, the lettered column, the
  Samwel chamber arrangement, the depth-and-date-anchored specimens.
- **legend** — explicitly flagged tradition (e.g. the Lost Maiden's ~90 ft fall);
  shown, never presented as survey.
- **interpretive** — everything the record does not fix: all speleothems, wall
  rugosity, pool extents, lighting, the scale figure, Samwel room *sizes*
  (rust-italic labels).

Hard prohibitions (verbatim from `strata_spec.json:must_not_invent` — a violation
is a provenance fault, the same severity class as a broken render):

1. **No AI imagery, no invented geometry.** Every documentary asset is a vector
   trace of a cited public-domain plate registered in `archive.json`, or a
   procedural/value-noise texture. If no real drawing exists (e.g. *Arctodus
   simus*, figured only as photographs), **omit the subject** — the gap is the
   point.
2. **No per-taxon Potter Creek depths.** Sinclair: "the fauna listed is a unit"
   (p.19). Render the 52-species assemblage as one *"fauna occur throughout the
   bone-bearing clay and breccia — not depth-sorted"* marker. Only the handful of
   individually depth-anchored facts may be placed (see §3).
3. **No bones in stratum C (volcanic ash) or the chocolate-mud lens in G** — the
   two barren deposits (p.11).
4. **Euceratherium *type* is Samwel, not Potter Creek** — and note the corpus
   contradicts itself here (`archive.json` F1 / `merriam-caves.tex` say Potter
   Creek; `must_not_invent` says Samwel M8751). Do **not** silently pick a side
   in-scene: flag it as an unresolved citation discrepancy to settle against the
   primary source (Sinclair & Furlong 1904).
5. **Samwel: depth ≠ age, and depth ≠ lithologic unit.** Place the four AMS-dated
   Chamber-Two specimens at their square+inch levels only; never map them to the
   named layers; keep the inverted Lepus(older,shallower)/Aplodontia(younger,
   deeper) pair visible; label ages **cal BC**, not cal BP.
6. **No human origin** for the polished/bevelled Potter Creek bone "implements"
   (Sinclair declined; Payen & Taylor → carnivore gnawing + water-smoothing).
7. **Potter Creek A–H cumulative depths are a render composite**, not additive
   measured depths (thicknesses are "greatest" values that pinch laterally; G's
   base is undetermined). Say so on the column.

You may not label a feature *documented* until you have the page that documents it.

---

## 3. The documented data (immovable, cited — pull from the JSON, don't retype)

**Potter Creek** (1 X3D unit = 1 foot): chamber length 107, roof ~75, width ~30
(half 15), breccia fans at x≈26 (NW) and x≈82 (SE), 42-ft entrance pit at x≈9,
a chimney above each fan apex, NW–SE trend, ~1500 ft elevation (Sinclair 1904).
Column top-down from `potter_creek_column`: **S** surface stalagmite · **A** clay
0.1–13.5 ft · **B** gravel · **C** volcanic ash *(barren)* · **D** clay ·
**E** cemented breccia ("false floor") · **F** soft clay · **G** stalagmite blocks
/ chocolate mud *(base undetermined)* · **H** stalagmite bosses (cave floor) over
McCloud limestone. Colours, depths, bone-bearing flags and citations are all in
the JSON — bind to them, never hand-type a depth.

**Samwel** (cm): the six named chambers + the deep drop to Chamber Two + the Magic
Pool; column from `samwel_column`: reddish clay → flowstone (3 cm) → gravel
(10–45) → breccia (60) → flowstone (2.5–10) → earth+breccia (30–140), excavation
to 2.5 m. Chamber *arrangement* is documented (Feranec 2007 Fig. 2, a void
outline); chamber *sizes* are interpretive.

**Depth-anchored faunal facts you MAY place** (from `bone_horizon_markers`):
*Arctotherium*+*Ursus* on the SE-fan **surface**; squirrels/woodrats/*Crotalus*/bat
in **gravel B**; the **Euceratherium radius+ulna at 170 cm** (8250±330 BP, UCR-381)
in the entrance-chamber breccia; polished bone at 80–140 in *(depths only, no human
claim)*; the late-Holocene flake/charcoal cluster *(redated 1910±150 BP — not
Pleistocene)*; the 15–30 cm cultural midden / atlatl cache *(~2000 BP, ~6000 yr
younger than the fauna)*; and the four Samwel AMS specimens at their levels.

**The hero:** pose **Euceratherium** at the Potter Creek 170-cm breccia horizon —
the one megafaunal taxon there with both a documented depth and a direct date —
flagged *"only a radius and ulna are documented at this level; the full skeleton
and pose are an interpretive reconstruction."* The Shasta ground sloth has **no**
provenance in these sources: if shown, it **floats** beside the column, labelled
unprovenanced — never embedded in a stratum.

---

## 4. The technical direction (the canonical path + the craft)

Author X3D 4.0, `profile='Immersive' version='4.0'`. **Follow the server's one
canonical path every time** — do not improvise field names or node placement:

1. **Look up before you build.** `describe_node('<Name>')` for exact fields, types,
   default containerField, and accepted child types. `list_nodes(component=…)` to
   discover. Never recall a containerField — the default only fits the usual
   parent (a texture inside `PhysicalMaterial` needs `baseTexture`/`normalTexture`/
   `metallicRoughnessTexture`; an HAnim skeleton root needs `containerField='skeleton'`).
2. **Build** (granular `create_node`/`set_field`/`add_child`/`def_node`/`use_node`,
   or the workflow tools).
3. **Validate — both, always.** `validate_x3d` (XSD shape) **and**
   `validate_semantic` (the XSD-passing silent failures: wrong containerField,
   USE-before-DEF, broken ROUTEs, interpolator key/keyValue arity). Apply the exact
   fix it names; `autofix_x3d` rewrites containerFields for you.
4. **Render and LOOK.** `render_image`/`render_current_scene` (X_ITE in headless
   Chromium). A scene that validates can still be off-camera, unlit, mis-scaled,
   or blank. **A scene is not done until `validate_semantic` is clean AND you have
   rendered it AND its provenance caption is present.**

Craft invariants Technē will keep surfacing (hold them by reflex):
- **Right-handed, +Y up, default view down −Z.** Angles in **radians**, lengths in
  **metres** (here scaled to feet/cm by an explicit unit convention — state it).
- **DEF/USE the repeats.** Define the limestone/breccia/water `Appearance` once and
  `USE` it — do not inline the same 3-texture PBR appearance on every shell (the
  current Samwel file has 39 redundant `ImageTexture` nodes).
- **Render contract:** X_ITE over loopback HTTP (`start_caves.sh` on :8099), never
  X3DOM headless, never `file://`; relative `cave_textures/` URLs; headlight off,
  dark gradient `Background` + LINEAR `Fog`; geometry is **back-half section
  (z ≤ 0)** so the chamber opens to the viewer — scenes read correctly only from
  the baked +z Viewpoints.
- **`PhysicalMaterial` for rock:** `metallic=0`, `roughness≈1`; PBR is lit by the
  default headlight, so it is **not** black with no light — add an `EnvironmentLight`
  (IBL) for *good* PBR. (Note: `x3d.py` omits the `global` default, so IBL needs the
  serialization-layer fix — Technē/autofix handles it; don't pass a bare `global`.)

Known repairs to fold in this pass (from the material study):
- **Regenerate the missing `potter_creek_strata.x3d`** (the generator writes it but
  it's absent from the tree, and `caves.html` links it).
- **One source of truth for stratigraphy:** make the in-cave column read the 9
  documented layers from `strata_spec.json` (today it's a hard-coded 3-band stub
  that contradicts the canonical column).
- **DEF/USE-deduplicate** the inlined appearances/textures.
- **Upgrade the human scale figure** from the Cylinder+Sphere proxy toward the
  project's HAnim pipeline (or at least DEF it once and label it interpretive).

---

## 5. The shot list (build order + acceptance)

Produce, in order, each ending at the acceptance gate (validate clean · rendered ·
caption present):

| # | scene | documented core | viewpoints | provenance caption |
|---|-------|-----------------|-----------|--------------------|
| 1 | **Potter Creek chamber** | 107×30×75 envelope, two fans, 42-ft pit, lettered column from JSON | Section · Hero (entrance + shaft) · Plan | documented envelope/column vs interpretive dressing |
| 2 | **Potter Creek bone-horizon panel** | to-scale S–H column + the depth-anchored facts only; 52-species "unit" marker | one framing view | "fauna is a unit, not depth-sorted"; composite-depth caveat |
| 3 | **Euceratherium hero** | placed at 170 cm breccia | Hero | "radius+ulna documented; skeleton interpretive" |
| 4 | **Samwel section** | six chambers, deep drop, Magic Pool | Section · Descent | documented arrangement vs interpretive sizes; legend flag on the drop |
| 5 | **Samwel "depth ≠ age" panel** | 6-layer column + 4 AMS specimens at levels | one framing view | depth ≠ age; cal BC; not mapped to layers |
| 6 | **Fauna plate** | F1–F3 traced line drawings (Euceratherium dental, Nothrotheriops skeleton, Canis dirus skull) | plate view | each with its `archive.json` citation; sloth = unprovenanced |

**Definition of done (the occupation gate):** every scene passes `validate_semantic`
clean, has been rendered and visually checked under X_ITE, carries its
documented/legend/interpretive caption, and cites a real plate for every
documentary claim. If you cannot cite it, it is interpretive or it does not ship.
