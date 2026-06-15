# Moose Production Pipeline — VFX Department Coverage

This procedural-CG moose (`generate_moose.py` → X3D, part of the local **mflux → X3D**
pipeline) is deliberately structured to cover **every stage of a professional VFX /
animation studio pipeline**. Because the deliverable is a real-time X3D scene, the
back half of a live-action pipeline (matchmove, roto, comp, DI) collapses — the
real-time render *is* the final image. The table maps each studio department to
where we implement it.

Department taxonomy verified against industry references (ILM/Weta/Pixar/DNEG-style
pipelines): LucidLink, CG Spectrum, MASV, On Assemble, The Rookies, SideFX.

| # | Department (aliases) | Studio responsibility | Where we do it | Status |
|---|----------------------|-----------------------|----------------|--------|
| — | **Development** | Greenlight, scope, methodology | Scene/scope decisions; `MOOSE_SCENE` (meadow/lake), render-target = "both" | ✅ |
| — | **Art / Concept** | Define the look (turnarounds, color keys) | **mflux** photoreal references (`moose_refs/moose_side.png`) drive proportions & palette | ✅ |
| — | **Previs / blocking** | Rough 3D staging & timing | `MOOSE_POSE=<0..1>` freezes any animation frame for blocking/staging stills | ✅ |
| 1 | **Layout** | Place assets, set cameras, scale | Named `Viewpoint`s (`MOOSE_VIEW`: Hero/Side/Head/Front/Top, Dive/Above), `MooseRoot` Transform | ✅ |
| 2 | **Modeling** | Build geometry, clean topology, UVs | Pure-Python primitives (`ellipsoid`/`tube`/`palmate_antler`/`cloven_hoof`) + swept **skin mesh** (`build_skin`); UVs generated per-primitive | ✅ |
| 3 | **Texturing / Surfacing** | Author albedo/roughness/normal maps | `generate_moose_textures.py` → tileable **fur PBR maps** (normal, glTF metallic-roughness, mottle albedo) | ✅ |
| 4 | **Look Development** | Materials that read under any light | `PhysicalMaterial` (metallic-roughness) per part; texture-slot wiring; lake water/lily/bulb materials | ✅ |
| 5 | **Rigging** | Skeleton + deformers + controls | **HAnim** quadruped (34 joints, LOA5-spirit) + **`skinCoord`/`skinCoordWeight`** linear-blend skinning of the whole trunk **and legs** | ✅ |
| 6 | **Animation** | Author the performance | `TimeSensor` + `OrientationInterpolator`/`PositionInterpolator` → graze cycle; researched **dive** (plunge → bottom-browse → surface) | ✅ |
| 7 | **Creature FX (CFX)** | Hair/fur/cloth/muscle sim | **Shell fur**: 4 alpha-cutout strand shells offset along normals, sharing the skinCoord so the fur *deforms with the body*; + tiling fur normal/roughness maps underneath. Cloth/muscle N/A | ✅ (fur) |
| 8 | **FX / Simulation** | Fire/water/particles/destruction | Procedural (not solver-based): **animated water surface** (CoordinateInterpolator waves), **rising bubbles**, **expanding surface ripple** | 🟡 procedural |
| 9 | **Matte Painting / Environments** | Backgrounds & full environments | `Background` sky dome; **meadow** (ground + grass field) and **lake** (pond bottom, lily pads/flowers, submerged bulbs/stems, `Fog`) | ✅ |
| 10 | **Lighting** | Light to match, set passes | `EnvironmentLight` (IBL-ish) + warm key / cool fill `DirectionalLight` + `Background` + underwater `Fog` | ✅ |
| 11 | **Rendering** | Produce final frames on the farm | **X_ITE** real-time in-browser render (interactive); deterministic stills via pose-freeze + `shot.js` | ✅ |
| 12 | **Compositing** | Combine passes/plates → final image | **mflux beauty pass**: a rendered frame is restyled to photoreal. Two modes: schnell img2img (fast) and **FLUX.1-Depth-dev depth-conditioned** generation — derives depth from the render so the photoreal output is **pose-locked** to the exact rig pose (`depth_beauty.png`) | ✅ |
| — | **Matchmove / Roto / Prep** | Integrate CG with live plates | N/A — pure CG, no live-action plates | ⚪ N/A |
| — | **Editorial / Color / DI** | Cut, conform, grade, master | N/A for a single real-time shot (the render is the master) | ⚪ N/A |
| ✲ | **Pipeline / TD** (cross-cutting) | Tools & data plumbing connecting depts | `generate_moose.py` *is* the pipeline: one parametric generator, env-var knobs, post-serialize fixers for x3d.py quirks | ✅ |
| ✲ | **Production Mgmt / R&D** | Schedule, track, research | This repo's memory + `demo-releases/`; R&D = the mflux→X3D method itself | ✅ |

## Minimal end-to-end pipeline (single CG creature) — fully covered

The smallest ordered set that still constitutes a complete production, and our coverage:

1. Concept/Design → mflux refs ✅
2. Modeling → procedural primitives + skin ✅
3. Texturing + LookDev → fur maps + PhysicalMaterial ✅
4. Rigging → HAnim + skinCoord weights ✅
5. Layout → Viewpoints + placement ✅
6. Animation → graze / dive ✅
7. Lighting + Rendering → lights + X_ITE ✅
8. Compositing (+ grade) → mflux beauty pass ✅
   - *Creature FX* (fur/water) sits between 6 and 7 as our 🟡 procedural stand-in.

## Honest gaps (where a real studio does more)
- **CFX:** shell fur gives a real strand silhouette but is not a groomed/simulated coat (no per-strand dynamics); no cloth/muscle. Some shell banding remains on the legs.
- **FX:** water/bubbles/ripple are procedural keyframed effects, not physically-solved sims.
- **Rendering:** real-time raster, not a path tracer — true photoreal comes from the offline beauty pass (now **FLUX.1-Depth-dev**, pose-locked).
- **skinNormal:** dropped — x3d.py's `Normal` node is internally inconsistent; X_ITE recomputes smooth normals from the deformed skin instead.

## Artifacts by stage
- Generators: `generate_moose.py`, `generate_moose_textures.py`
- Scenes: `moose.x3d` + `moose_x3dom.html` (meadow graze); `moose_lake.x3d` + `moose_lake.html` (lake dive)
- Textures: `assets/moose_textures/fur_{normal,mr,albedo}.png`
- Refs / stills / beauty pass: `moose_refs/`
- Screenshot harness: `shot.js` (X_ITE → PNG)
