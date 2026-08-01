# FAILURE_MODES.md — StillLife_Provenance

Every failure mode hit while building the three scenes (`antiquity`, `pronk`,
`trompe`), 2026-07-30. Consolidated and de-duplicated across the three builders'
reports and re-verified against the files on disk where possible.

Format per entry: **emitted** (what the generator produced) / **schema** (what
validation said) / **renderer** (what X_ITE actually did) / **detected** /
**fix**.

---

## A. THE XML WAS VALID AND THE RENDER WAS WRONG

These are the ones that matter. No validator catches any of them.

### A1. `containerField` silently dropped on PhysicalMaterial textures — STRUCTURAL, hits every textured scene
- **emitted:** `x3d.py` 4.0.65.3 serializes `PhysicalMaterial(baseTexture=ImageTexture(...))`
  with **no** `containerField` attribute. The library has no `containerField`
  kwarg (TypeError if passed — trompe), and setting `.containerField` as a
  plain attribute is ignored by `.XML()` (antiquity). There is no in-library
  way to emit it.
- **schema:** valid either way — `containerField` has a default (`texture` for
  ImageTexture), so its absence is legal XML.
- **renderer:** X_ITE parents the texture into the default field, which
  PhysicalMaterial does not use → texture **silently dropped**, object renders
  untextured.
- **detected:** grep of the output file for `containerField='baseTexture'`
  after the render looked flat/untextured.
- **fix:** post-serialization injection. antiquity: regex `_fix_xml()`;
  trompe: lxml `_patch_container_fields()` **with asserts on patch counts**
  (21 baseTexture) — the assert version is the one to copy, because a regex
  that matches nothing fails silently in exactly the same way the bug does.
  Verified in shipped files: antiquity.x3d 3×, trompe.x3d 21×. pronk has no
  textures, so never exercised this slot.

### A2. Same bug on MetadataSet children — and pronk SHIPPED WITH IT UNFIXED
- **emitted:** `MetadataString` children of a `MetadataSet` serialize without
  `containerField='value'`.
- **schema:** valid — default containerField for a metadata node is `metadata`.
- **renderer:** children parent into the set's `metadata` field, not `value` —
  the provenance strings are attached to the wrong slot and an X3D-aware
  consumer reading `MetadataSet.value` finds it empty. For a provenance
  project this is the payload failing, invisibly.
- **detected:** by inspection of the serialized XML (antiquity, trompe), and
  — for pronk — only during the writing of this document: grep shows
  antiquity.x3d has 5 `containerField='value'` injections, trompe.x3d 6,
  **pronk.x3d 0**. pronk.py contains no patching code at all.
- **fix:** same injection as A1. **OPEN ITEM: pronk.x3d needs the patch
  applied and re-shipped.**

### A3. `EnvironmentLight.global` invisible when set — intent cannot be read from the XML
- **emitted:** Python `global_=True`; the serializer omits any field equal to
  its default, and `global` defaults True, so the attribute vanishes.
- **schema:** valid; semantically identical in this case.
- **renderer:** behaves correctly — the failure is *auditability*: the shipped
  XML cannot show the value was deliberate, exactly as the project notes
  warned. Same class: `NavigationInfo type` (pronk).
- **detected:** grep of the output.
- **fix:** antiquity and trompe inject `global='true'` explicitly (verified in
  both shipped files). pronk did not — behavior is fine (value equals
  default) but the intent lives only in pronk.py. Minor open item.

### A4. All metrics green, image flat — ambient swamping the key. Hit INDEPENDENTLY in all three scenes
- **emitted:** valid lights: antiquity r1 (foggy wash, 5/6 metrics passing),
  pronk pass 1 (EnvironmentLight 0.9 → uniformly pastel, every metric
  passing), trompe v4 (ambient 0.55 → flat daylight, every threshold passing).
- **schema/renderer:** nothing wrong anywhere. The scene is simply not lit as
  a picture.
- **detected:** **only by reading the PNG.** The lookdev metrics genuinely
  cannot see this — key_ratio and dyn_range can pass while the image is a
  wash.
- **fix:** drop ambient hard (antiquity 0.28→0.13, pronk →0.20, trompe
  0.55→0.12) and let one raking shadow-casting key dominate. Three-for-three
  says this is the default failure state of a first lighting pass, not a
  fluke: **budget a light-balance round in every scene.**

### A5. "Shadows are broken" that wasn't (antiquity)
- **emitted:** correct `shadows='true'`, `shadowIntensity='0.95'`.
- **renderer:** shadows were being cast — but washed out by ambient at sheet
  scale, so round 2 *looked* shadowless.
- **detected:** a minimal probe scene proved X_ITE shadows work with
  EnvironmentLight + fill present; a crop of the real render then showed the
  shadows faintly there.
- **fix:** light balance (key 8→27, ambient down), not shadow plumbing.
  Lesson: **probe-isolate before blaming the feature.** (Trompe instead chose
  authored translucent shadow quads and never relied on shadow mapping — a
  valid alternative that trades realism for determinism.)

### A6. PBR metals read as matte porcelain/glass without a dominant directional key (pronk)
- **emitted:** correct `metallic=1.0` materials; silver jug rendered like a
  carafe of water under a big ambient bed.
- **detected:** looking. Metrics indifferent.
- **fix:** ambient →0.2, darker base colors, key dominates. Metal is a
  *lighting* outcome, not a material flag.

### A7. Geometry interpenetration / occlusion — the largest family by count, all caught only visually
All valid XML; the renderer draws exactly what was asked; the ask was wrong.
- **pronk napkin, 3 distinct bugs:** ribbon-tear (negative fold offsets pushed
  the hang behind the table-front panel → clipped white strips); green hole #1
  (signed fold amplitude dipped below the tabletop); green hole #2 (first hang
  row below y=0 while its quad still crossed the table corner — needed a 3×
  crop to diagnose). Fixes: strictly-positive offset/height formulas; delay
  the drop until the hang clears the corner.
- **pronk lemon-peel helix:** coil radius 0.040 < fruit radius 0.047 → the
  entire peel invisibly *inside* the lemon; later variants gave a Saturn ring
  and floating-debris arcs. Fix: tight low coil in front of the fruit, above
  the plate.
- **pronk plate-through-napkin:** fold peaks above the plate's base disc → a
  dark dash surfacing through white cloth. Fix: raise plate 10 mm.
- **trompe:** curtain spine stopped at y=−0.58 leaving lit board exposed
  beneath (→ −0.68); iron rod floated off the board edge and collided with
  the brass-nail row (rod moved/darkened, nail row relocated).
- **antiquity floating amphora:** leaning on its cone tip into empty space it
  read as airborne. Fix is instructive: lean it *toward the wall* so the key
  throws its shadow onto the wall — the cast shadow is what grounds it —
  plus a dark contact patch.
- **antiquity transparency draw order:** the glass bowl must be emitted LAST
  in document order or alpha blending discards the fruit inside it. Document
  order is load-bearing for transparency; no validator knows that.

### A8. Viewpoint `description` baked into headless captures as a UI toast (trompe)
- **emitted:** a described Viewpoint (good practice, required elsewhere).
- **renderer:** X_ITE burns the description into the capture as a yellow pill,
  upper right — all v4 renders carried "the wall piece, straight on" as
  in-image UI. Metrics never noticed.
- **fix:** omit the description on the *bound* viewpoint when rendering
  headless. (Antiquity ships described viewpoints and did not hit this —
  interaction is specific to which viewpoint the capture binds.)

### A9. Texture scale vs geometry scale (antiquity)
- **emitted:** a 192 px craquelure texture across a 3.9-unit wall → giant
  cartoon meanders.
- **fix:** TextureTransform tiling (2.6×1.9) + contrast tune; the random-walk
  cracks wrap mod size so the texture tiles seamlessly. Hit once; the fix is
  general.

### A10. Default headlight flattens chiaroscuro (trompe, from the probe-scene note)
- `NavigationInfo headlight=false` is load-bearing for any dark scene.
  Authored from the start in trompe/pronk because the probe scene had already
  paid for the lesson; never actually re-hit. Recording it because the default
  is wrong for this genre.

### A11. Coverage metric vs wall-backed composition (metric-model limitation, not a scene bug)
- A painting-faithful framing fills the frame with the back wall, so no
  authored skyColor is visible and `analyse()` falls back to modal-edge
  sampling → spurious coverage FLAGs (pronk hero 0.878, raking 0.976).
  Antiquity instead narrowed the ground slab / pulled cameras back, which
  also genuinely improved the framing. Judgment call per scene; the flag is
  advisory for this composition class.

### A12. Baked highlights authored as detached geometry read as debris (pronk flagon, antiquity glass bowl) — NEW this round
- **emitted:** the sanctioned workaround for no-transmission/no-shadows —
  "bake the highlights" — implemented as *separate meshes*: a white curved
  strip floating beside the pewter flagon, white capsule "sparkle" sticks
  around the antiquity bowl rim (imitating the fresco's painted dashes).
- **schema/renderer:** valid, drawn exactly as asked.
- **detected:** reading the PNG. The flagon "highlight" hangs in air a full
  object-width off the body; the bowl dashes read as toothpicks/debris from
  every viewpoint, worse off-axis (any parallax detaches them).
- **fix:** bake highlight strokes into the object's own UV textures
  (emissiveTexture with non-black emissiveColor, or lightened baseTexture) so
  they are welded to the surface at every angle. Never freestanding
  highlight geometry.

### A13. Liquid modeled as disconnected fill-disc + body (pronk roemer)
- **emitted:** wine = a pale opaque surface disc near the rim **plus** a
  separate liquid sphere lower down, neither touching the glass walls.
- **renderer:** exactly that — two liquids and an air gap; the surface disc,
  being lighter than the body, reads as mayonnaise.
- **detected:** hero crop.
- **fix:** ONE liquid mesh, meniscus disc as its top cap at the same height,
  radius matched to the inner glass wall; top surface *darker* than the lit
  body (Heda's wine is dark olive with a single crescent highlight — bake
  that crescent per A12).

### A14. Physically impossible prop pose passes everything (pronk tazza)
- **emitted:** the overturned silver tazza standing vertically on its rim
  like a coin/wheel, foot forward.
- **schema/renderer/metrics:** all indifferent. Only the source painting
  says a tazza lies bowl-down at a shallow diagonal.
- **fix:** lay it down (rotate ~80° toward the cloth, foot up-right as in
  SK-A-4830) + baked contact ellipse. General rule: every prop pose needs a
  "could it rest like this on a real table" check against the source.

### A15. Armature/finial escaping the frame reads as a suspension wire (pronk gilt cup)
- **emitted:** the covered cup's finial modeled as a thin rod that continues
  past the top frame edge in ALL three views.
- **renderer:** correct; but a vertical line exiting frame overhead reads as
  the cup *hanging from a wire* — instant CG tell.
- **fix:** terminate the finial with a knop/figure INSIDE the frame with
  headroom (the painting gives the cup air above it); recompose camera or
  shorten the rod.

### A16. Unlit backfaces/board edge occupying the frame (trompe three_q)
- **emitted:** three_q camera positioned so the board's unlit edge/back —
  untextured, pure black — fills the left half of the capture.
- **renderer:** correct: nothing lights it, nothing textures it.
- **detected:** the sheet; the view is a wasted panel that reads as junk.
- **fix:** either give the board side/back a lit wood material (it is a
  *board partition*, its edge is part of the fiction) or move the off-axis
  camera to the curtain side. A view that ships must earn its panel.

### A17. Trompe-l'oeil premise defeated by margins (trompe frontal)
- **emitted:** board floating in a black void with wide margins on all sides.
- **renderer:** fine. But KMS3059's entire premise is the partition filling
  the picture plane edge-to-edge — surrounded by void it demotes back to "an
  object", which is this project's core failure being reproduced at the
  composition level.
- **fix:** frontal camera framed so the board bleeds past all four edges
  (or to a painted-frame crop). The void must never read.

### A18. Baked shadow with a ruler-straight edge reads as geometry (trompe curtain shadow)
- **emitted:** the curtain's authored shadow on the board = a uniform darker
  wedge with a dead-straight, hard boundary.
- **renderer:** as asked; it reads as a different-material panel, not shadow.
- **fix:** bake penumbra — gradient the wedge edge over ~5% of board width
  and let its darkness fall off with distance from the curtain. Authored
  shadows need authored softness.

### A19. Tonal key never compared against the source — all three scenes drifted, metrics blind
- pronk renders ~a stop too LIGHT and flat (wall luminous, no deep darks —
  Heda is dark ground + white cloth + specular accents); trompe ~1–2 stops
  too DARK overall with tan papers (the painting's papers are near-white,
  its curtain near-black: the render compresses both toward the middle);
  antiquity is pastel haze (the fresco is earthy, saturated, dark-grounded).
- **detected:** only by side-by-side with the reference images
  (scratchpad `ref_heda/ref_kms/ref_mann`). No lookdev metric references the
  source.
- **fix:** make the source thumbnail part of every contact sheet round —
  judge key against IT, not against the previous render. (Candidate harness
  feature: paste the reference into the sheet margin.)

### A20. Serializer containerField hole is wider than A1 recorded (capability probe)
- Also hits **EnvironmentLight texture slots** and **ComposedCubeMapTexture
  face slots** — and the serializer *alphabetically reorders* children, so
  cubemap faces scramble silently without injection. Same class as A1/A2,
  same fix (post-serialization injection + asserted patch counts). Recorded
  in CAPABILITY_MATRIX.md; repeated here so the next builder greps one file.

---

## B. Caught immediately by Python/tooling (not render-wrong; listed for completeness, all trivial)

- **numpy 2.x:** `ndarray.ptp()` removed → `np.ptp(a)`. Hit once.
- **x3d.py reserved-word suffixing is inconsistent:** `global_` and `class_`
  take the underscore; `NavigationInfo` takes `type=`, **not** `type_`. Hit in
  two scenes, seconds to fix, but worth one line because it is per-field
  inconsistency, not a rule you can learn once.
- **x3d.py has no `containerField` kwarg** — TypeError if passed (see A1 for
  the consequence).

---

## C. Open items surfaced by this audit

1. **pronk.x3d ships with unpatched MetadataSet children** (A2) — the
   provenance payload is misparented. Apply the trompe-style lxml patch with
   asserts and re-emit.
2. pronk.x3d's EnvironmentLight carries no explicit `global` attribute (A3) —
   harmless at runtime, but the file cannot attest the intent. Inject on the
   next re-emit.

## The one-sentence version

The failures that cost time were never schema failures: they were a serializer
that legally omits meaning (A1–A3), lighting whose flatness every metric
approves (A4–A6), and geometry that is exactly as wrong as it was specified
(A7). The countermeasures that worked: post-serialization patching **with
asserted patch counts**, probe-isolation before blaming a renderer feature,
and reading the PNG every round — the metrics tell you where to look, never
whether it is right.
