# Paper notes — Potter Creek & Samwel Caves in X3D

Handoff for writing a paper (companion to `docs/paper/x3d-mcp-hanim-demo.tex`,
the classroom-skeleton paper) about reconstructing **Potter Creek Cave** and
**Samwel Cave** in X3D. For the X3D-team meeting with Don Brutzman.

**Resume:** `claude --continue` on branch **`potter-creek-cave`**. Chatlog of the
build is in `sessions/` (gitignored): `.json` (raw) and `.md` (readable, ~1262
turns) — the same chatlog→LaTeX route used for the classroom paper.

---

## Working title
*Reconstructing Historic Fossil Caves in X3D from Century-Old Survey Data:
A Human–AI Case Study (Potter Creek & Samwel Caves).*

## One-paragraph abstract (draft)
We reconstruct two Pleistocene fossil caves of the McCloud River, California —
Potter Creek Cave and Samwel Cave, excavated under **John C. Merriam** in a
program running roughly **1902–06** (Potter Creek from ~1902; Samwel
~1903/1904–06) — as interactive, to-scale X3D scenes built procedurally from the
original survey literature (Sinclair 1904; Furlong 1906; Feranec et al. 2007).
The work was produced by a human–AI pair through the Web3D X3D MCP server, with a
tight author→validate→**render** loop. We contribute (i) a method for turning
historical cave surveys into standards-conformant X3D with an explicit
**provenance discipline** separating documented geometry from interpretive
dressing; (ii) PBR cave look-dev (displaced + normal-mapped limestone, god-rays,
rippled water) rendered in X\_ITE; and (iii) upstream improvements to the X3D MCP
server, including an **X\_ITE render backend** that lets the tool *see* HAnim and
PBR scenes that X3DOM cannot. A personal thread runs through it: the excavator
was the human author's great-great-grandfather, and the caves are Winnemem Wintu
sacred sites now drowned by Shasta Dam.

---

## The sites & the documented facts (with citations)

### Potter Creek Cave (Shasta County, CA)
- **107 ft** long chamber, **~30 ft** max width, roof **~75 ft** above the lowest
  floor point; **NW–SE** trend; **1500 ft** elevation, ~800 ft above the McCloud.
- Two **fan-shaped breccia deposits** sloping from the ends and **coalescing** in
  the middle; **chimney** openings above each fan apex.
- Access by a **42 ft vertical descent** (rope ladder) at the great pit.
- NW-fan stratigraphy: upper clay to **13.5 ft**, volcanic ash ~**1.5 ft**,
  cemented breccia below.
- Fauna: **~52 vertebrate species, 21 extinct.** ***Euceratherium collinum***
  (shrub-ox) — **TYPE LOCALITY here** (new genus & species, Sinclair & Furlong
  1904). Abundant
  *Arctodus simus* (giant short-faced bear); *Nothrotheriops shastensis* (Shasta
  ground sloth); *Megalonyx*; *Canis dirus*; *Mammuthus*; *Camelops*; *Equus*;
  mastodon. Polished bone + a stone chip at depth → the human-association
  question (Payen & Taylor 1976).

### Samwel Cave (~5 km N, same McCloud arm)
- Wintu **sawal / Samwel** — gloss is **contested**: variously translated
  "sacred/holy place" AND identified with the Wintu word for **grizzly bear**;
  do not assert a single meaning. Also the **Cave of the Lost Maiden**
  (the girl **Olchanolmet**) and the **Cave of the Magic Pools.**
- Branching **two-level** system, **460 m** elevation, McCloud Limestone. Named
  spaces (Furlong's plan, redrawn in Feranec et al. 2007 Fig. 2): **Entrance,
  Porcupine Entrance, Pleistocene Hall, the Gate, Chamber One, Merriam's Chamber,
  Chamber Two ("Furlong's Room")** down a deep drop.
- The maiden **fell into a ~90-foot-deep hole** — the shaft that connects the
  upper/main level to the lower level (Chamber Two). The lower level "requires
  climbing gear." **Wintu medicine men bathed in the pools for "magic strength."**
- Stratigraphy (Chambers One & Two): earth+breccia (30–140 cm) → flowstone
  (2.5–10 cm) → breccia (60 cm) → gravel (10–45 cm) → flowstone cap (3 cm) →
  reddish clay; deepest dig **2.5 m**; excavated in **4-ft² pits, 10-in levels.**
- Fauna: **45 mammal + 13 bird species**, **~1000 specimens**; radiocarbon = Last
  Glacial Maximum (**~23,600–17,100 cal BC**, oldest-first). *Note: verify the
  units (cal BC vs cal BP) and exact bounds against Feranec et al. 2007 before
  publication.* Shares *Euceratherium collinum*,
  *Arctodus*, *Nothrotheriops*, *Megalonyx*, *Canis dirus*, *Mammuthus*.
- Gated since **1972**; key from the **Shasta Lake Ranger District** (Shasta-
  Trinity NF). Winnemem Wintu sacred site; **Shasta Dam (1945)** drowned the
  McCloud homeland — both caves now sit on the Shasta Lake shore.

### Sources (for the bibliography)
- Sinclair, W.J. (1903) *A Preliminary Account of the Exploration of the Potter
  Creek Cave.* **Science** 17(435):708–712.
- Sinclair, W.J. (1904) *The Exploration of the Potter Creek Cave.* Univ. Calif.
  Publ. Amer. Arch. Ethn. **2(1).** (archive.org `explorationpott00mitrgoog`)
- Sinclair, W.J. & Furlong, E.L. (1904) *Euceratherium, a New Ungulate from the
  Quaternary Caves of California.* Univ. Calif. Publ. Bull. Dept. Geol.
  **3:411–418.** (type description of *Euceratherium collinum*)
- Sinclair, W.J. (1905) *New Mammalia from the Quaternary Caves of California.*
  Univ. Calif. Publ. Geol. 4:145–161.
- Furlong, E.L. (1906) *The Exploration of Samwel Cave.* **Am. J. Sci.**
  22(129):235–247.
- Payen, L.A. & Taylor, R.E. (1976) *Man and Pleistocene Fauna at Potter Creek
  Cave.* J. California Anthropology 3(1):51–58. (eScholarship `8zs315nk`)
- Feranec, Hadly, Blois, Barnosky & Paytan (2007) *Radiocarbon Dates from the
  Pleistocene Fossil Deposits of Samwel Cave.* **Radiocarbon** 49(1):117–121.
- UCMP, Shasta-Trinity caves overview; showcaves.com/Samwel; Winnemem Wintu —
  "Drowned Memories: The Submerged Places of the Winnemem Wintu."

---

## What we built (artifacts)
- `generate_cave.py` → `potter_creek_cave.x3d` — longitudinal **section** (back-
  half shell), to Sinclair's scale: domed roof, two coalescing breccia fans,
  chimneys, 42-ft pit, banded strata, scale figure.
- `generate_samwel.py` → `samwel_cave.x3d` — **labeled cross-section** echoing
  Furlong/Feranec Fig. 2; the corrected **~90 ft hole**; the **Magic Pool**.
- `generate_cave_textures.py` (run w/ `ALLEUPHEME/mflux-env/bin/python`) → tileable
  PBR limestone (albedo/normal/metallic-roughness) + water ripple normal in
  `cave_textures/`.
- Look-dev: stalactites/stalagmites/columns/draperies, breakdown blocks, rippled
  PBR water, layered **god-rays** + dust motes, geometric fbm displacement +
  normal-mapped `PhysicalMaterial` (metallic=0).
- Viewers: `caves.html` launcher + `*_xite.html` / `*_hero.html`; `start_caves.sh`
  (serves on 127.0.0.1:8099, auto-opens). **X\_ITE only** — X3DOM can't render PBR
  and won't draw meshes headless; `file://` is CORS-blocked, so every page guards
  with a "start the server" message. X\_ITE pinned to **15.1.4**.

## Key figures (committed in `cave_refs/`)
- `potter_creek_cave_pbr_section.png`, `potter_creek_cave_pbr_hero.png`
- `samwel_cave_pbr_section.png`, `samwel_cave_pbr_hero.png`
- **Figure-name mapping** (`cave_refs/` source → `docs/paper/figures/` in the paper):
  - `potter_creek_cave_pbr_section.png` → `docs/paper/figures/pcc_section.png`
  - `potter_creek_cave_pbr_hero.png` → `docs/paper/figures/pcc_hero.png`
  - `samwel_cave_pbr_section.png` → `docs/paper/figures/samwel_section.png`
  - `samwel_cave_pbr_hero.png` → `docs/paper/figures/samwel_hero.png`
- Iteration history (`cave_*`, `*_lookdev*`, `*_push*`) → a **visual changelog**
  (cf. `docs/paper/visual-changelog.tex`).

## Method highlights for the paper
1. **Survey-to-X3D**: profiles/stations from prose measurements; the **section /
   back-half (z≤0) cut** is what makes a cave's interior both legible *and*
   lightable on screen — the same way the 1904/1906 reports drew them.
2. **Provenance discipline**: a `PROVENANCE` block in each generator + an on-screen
   caption that states plainly what is *to scale from the survey* vs.
   *interpretive* (speleothems, lighting, rock texture). A reusable pattern for
   honest scientific/heritage reconstruction.
3. **Render-to-see loop & dogfooding**: `describe_node` before authoring,
   `validate_x3d` + `validate_semantic` (both), then **render** in X\_ITE and
   inspect. Caught real issues (off-camera, unlit, X3DOM-black, CORS).
4. **Cultural responsibility**: Winnemem Wintu sacred sites; named, credited,
   handled as context not scenery; the dam-flooding noted.

## Contributions back to the toolchain (MCP, branch `mcp-improvements`)
- **X\_ITE render backend** for `render_image`/`render_current_scene`: async
  Playwright (fixes "Sync API inside the asyncio loop"), X\_ITE over an ephemeral
  loopback server, serves the file's own dir so relative textures resolve →
  renders **HAnim + PBR** that X3DOM cannot.
- Semantic validators: containerField (with canonical suggestion), USE-before-DEF,
  interpolator key/keyValue, ROUTE checks; `autofix_x3d`; proactive server
  `instructions`. **255 tests pass.**
- `x3d.py` upstream bug report (`docs/x3dpy-bug-report.md`): dropped
  `containerField`, wrong `EnvironmentLight.global` default — for Don/Web3D.

## Proposed section outline (mirror the classroom paper)
1. Introduction — human–AI pairing; the family/heritage motivation.
2. The sites & sources — Potter Creek, Samwel, Merriam; Winnemem Wintu context.
3. Method — procedural X3D from historical surveys; sectioning; PBR textures.
4. The render loop & the X3D MCP — X\_ITE backend, validators, dogfooding, bugs.
5. Provenance discipline — documented vs. interpretive.
6. Results — figures, both caves, the 90-ft hole / Magic Pool correction.
7. Discussion — heritage responsibility, reproducibility, future (fauna from the
   digs; real survey dims; on-site photos).
8. Contributions to the toolchain.

## Status / TODO for the meeting
- [ ] Draft `docs/paper/merriam-caves.tex` from this outline (reuse the classroom
      paper's preamble/figure macros).
- [ ] Drop the four PBR figures + a visual-changelog strip.
- [ ] Decide what to **push**: branches `potter-creek-cave` and `mcp-improvements`
      are LOCAL/unpushed (standing rule). Fork-based PR to Web3DConsortium/x3d_mcp
      per `[[github-identity]]`. The `x3d.py` bug report is earmarked for Don.
- Both branches local; working tree clean as of this handoff.
