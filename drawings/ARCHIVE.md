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

---

## Fauna — anatomical drawings (in progress)

> Per the archive principle, each excavated taxon is to be represented by a **real
> published anatomical / skeletal line drawing**, traced and cited — not AI imagery.
> Hero: the type *Euceratherium collinum* skull from its original description.

### F1 · *Euceratherium collinum* (shrub-ox) — type skull
- **Original:** Sinclair, W. J. & Furlong, E. L. (1904) *Euceratherium, a new ungulate
  from the Quaternary caves of California*, **Plates 50 & 51** (type cranium, lateral
  & facial). University of California, Bulletin of the Department of Geology **3(20):
  411–418.** Type locality: **Potter Creek Cave**.
- **Source scan:** archive.org `bulletinofde319021904univ` (BHL/Smithsonian).
- **Trace:** _pending_ (leaf numbers from the fauna-drawing hunt).

_(further taxa — Nothrotheriops, Canis dirus, Arctodus, Mammuthus, Camelops — appended
as their public-domain skeletal plates are located and traced.)_
