# Potter Creek & Samwel Caves — a 3-D archive of the survey record

Every item here is a **faithful vector trace of a real published drawing**, with its
full citation and source — no AI imagery, no invented geometry. Each original is
reproduced identically (`trace_drawing.sh`: pdftoppm → crop → threshold → potrace →
SVG), and several are lifted to to-scale X3D (`svg_to_x3d.py`, `extrude_contours.py`).
Catalogue is machine-readable in `archive.json`.

---

## Cave survey drawings

### A1 · Potter Creek Cave — topographic plan of the chamber floor
- **Original:** Sinclair, W. J. (1904) *The Exploration of the Potter Creek Cave*,
  **Plate 14** ("Topographic map of the floor of the main chamber… contour interval
  6 inches"). University of California Publications, American Archaeology and
  Ethnology **2(1):1–27**.
- **Source scan:** UC Berkeley anthpubs `ucp002-003.pdf` (p.40); also archive.org
  `explorationpott00mitrgoog` (Plates 12–13 missing from that Google scan).
- **Trace:** `pcc_plan_plate14.svg` · **3-D:** `potter_creek_plan.x3d` (IndexedLineSet,
  to scale) · **topography:** `potter_creek_floor.x3d` (contours extruded, A5).

### A2 · Potter Creek Cave — longitudinal section of the buried gallery
- **Original:** Sinclair (1904), **Plate 11** ("Longitudinal section of the buried
  gallery, showing the relation of its deposits to the beds in the main chamber").
- **Source scan:** archive.org `explorationpott00mitrgoog`, leaf n55
  (`/download/explorationpott00mitrgoog/page/n55_w3884.jpg`).
- **Trace:** `pcc_section_plate11.svg`

### A3 · Potter Creek Cave — deposit cross-sections 1–6
- **Original:** Sinclair (1904), **Plates 12–13** (cross-sections of the cave deposit
  along the numbered section lines).
- **Source scan:** UC Berkeley anthpubs `ucp002-003.pdf` (pp. 38–39).
- **Trace:** `pcc_xsec_plate12.svg`, `pcc_xsec_plate13.svg` (gitignored — large;
  regenerable via `trace_drawing.sh`).

### A4 · Samwel Cave — cross-sectional view
- **Original:** Feranec, R. S., Hadly, E. A., Blois, J. L., Barnosky, A. D. & Paytan,
  A. (2007) *Radiocarbon Dates from the Pleistocene Fossil Deposits of Samwel Cave*,
  **Figure 2** ("Cross-sectional view of Samwel Cave"). **Radiocarbon 49(1):117–121.**
  (Furlong's 1906 report itself carries no plan/section drawing — only photographs.)
- **Source:** ib.berkeley.edu Barnosky lab PDF.
- **Trace:** `samwel_fig2.svg`

### A5 · Potter Creek Cave — 3-D floor topography (derived)
- **Derived from** A1 (Sinclair 1904, Plate 14) by lifting each contour by its nesting
  depth × the surveyed 6-inch interval and triangulating (`extrude_contours.py`).
- **Model:** `potter_creek_floor.x3d` (8× vertical exaggeration).

### A6 · Potter Creek Cave — bone-horizon section + interpretive hero (derived)
- **What:** Sinclair's documented NW-fan column (S,A,B,C,D,E,F,G,H, to scale in feet)
  with the fauna pinned **only where the literature gives a depth**. The mixed
  assemblage gets one honest "fauna occur *throughout* the bone-bearing clay &
  breccia — not depth-sorted" marker (Sinclair's *"the fauna listed is a unit,"*
  p.19); the genuinely depth-anchored facts (Euceratherium radius+ulna at 170 cm,
  8250±330 BP; polished bone 80–140 in with **human origin refuted**; the
  late-Holocene flake; the cultural midden) are callouts. The Shasta ground-sloth
  skeleton (F2) stands beside the column as a flagged **interpretive, unprovenanced**
  hero — never embedded in a layer.
- **Sources:** Sinclair 1904 (column + faunal unit); Payen & Taylor 1976 (170 cm
  Euceratherium date; refuted bone tools). Grounding catalogued in `strata_spec.json`.
- **Build:** `generate_fauna_strata.py` → `potter_creek_strata.x3d` (preview
  `potter_creek_strata_preview.png`).

### A7 · Samwel Cave — per-specimen dated levels, "depth ≠ age" (derived)
- **What:** the Feranec et al. (2007) Chamber-Two column (cm) with the four AMS-dated
  specimens at their real square+inch levels — the **one** Merriam-caves dataset
  with per-specimen depth. The deposit is *not* chronologically stratified: the
  shallower *Lepus* (50.8 cm) is **older** than the deeper *Aplodontia* (76.2 cm),
  highlighted as the teaching point. Ages are cal BC, not cal BP.
- **Source:** Feranec et al. 2007 (Radiocarbon 49(1):117–121), Table 2.
- **Build:** `generate_fauna_strata.py` → `samwel_strata.x3d` (preview
  `samwel_strata_preview.png`).

---

## Fauna — real anatomical drawings (traced, public-domain; no AI)

> Each excavated taxon is represented by a **real published anatomical / skeletal
> line drawing**, traced and cited. Honesty note: the *Euceratherium* type skull
> (Pls. 50-51) is published only as **photographs**, so the genuine published *line
> drawing* of the type animal is its **dental** Text Fig. 1. The Shasta ground sloth,
> by contrast, has a full lateral **skeletal** line drawing.
>
> **3-D:** the three traces are assembled into an X3D archive plate,
> `fauna_plate.x3d` (`fauna_to_x3d.py` → IndexedLineSet, viewable in X_ITE;
> preview `fauna_plate_preview.png`). Each bay is shown legibly with its citation
> and **true dimension stated in words** — we deliberately do *not* stand a full
> sloth *skeleton* beside isolated *skulls* on one to-scale baseline, which would
> compare wholes against parts and mislead.

### F1 - *Euceratherium collinum* (shrub-ox) - left superior dental series
- **Original:** Sinclair, W.J. & Furlong, E.L. (1904) *Euceratherium, a new ungulate
  from the Quaternary caves of California*, **Text Fig. 1** ("Left superior dental
  series, x1/3"). Univ. Calif. Bull. Dept. Geology **3(20):411-418.** Type locality:
  **Potter Creek Cave** (type cranium UCMP 8751). [Plates 50-51 are halftone photos.]
- **Source:** archive.org `bulletinofde319021904univ`, leaf n598. Public domain (1904).
- **Trace:** `fauna/euceratherium_dental.svg`

### F2 - *Nothrotheriops shastensis* (Shasta ground sloth) - lateral skeleton
- **Original:** Stock, C. (1925) *Cenozoic Gravigrade Edentates of Western North
  America*, **Fig. 4** (skeleton in lateral view). Carnegie Institution of Washington,
  Publication **331**, p. 33. (Ground sloth first named: Sinclair 1905.)
- **Source:** BHL item 275982 / archive.org `cenozoicgravigra00stoc`, leaf 57. US work
  pub. 1925 -> public domain in the US.
- **Trace:** `fauna/nothrotheriops_skeleton.svg`  *(the hero - a full articulated skeleton)*

### F3 - *Canis dirus* (dire wolf) - lateral skull
- **Original:** Merriam, J.C. (1912) *The Fauna of Rancho La Brea, Part II: Canidae*,
  **text-fig. 1** (skull no. 10834, lateral, x1/2). Memoirs of the University of
  California **1(2)**, p. 224. (Pen line drawing, not a photograph.)
- **Source:** archive.org `faunaofrancholab02merr`, leaf 12. Public domain (1912).
- **Trace:** `fauna/canis_dirus_skull.svg`

### Located, not yet traced
- ***Mammuthus*** - lateral skeletal line drawings: Osborn, H.F. (1942) *Proboscidea*
  vol. 2, Figs. 996-998, p. 1130 (archive.org `proboscideamonog02osbo`, leaf 364).
- ***Camelops*** - from the same hunt; exact figure pending.
- ***Arctodus simus*** - **no line drawing exists**; Merriam & Stock (1925), Carnegie
  Publ. 347, figures the skull/skeleton only as **photographs**. Skipped under the
  no-AI / real-drawing rule.
