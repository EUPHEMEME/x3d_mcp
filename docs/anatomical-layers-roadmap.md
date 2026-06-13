<!-- Earmarked for the Don Brutzman discussion: proposed anatomical-layer
     roadmap building on the LOA5 HAnim demos, as candidate ISO-draft and
     X3D MCP contributions. "Claude and Alexander", collaborative authorship. -->

# Anatomical layering roadmap — building outward from the LOA5 skeleton

The LOA5 skeleton (150 joints, ISO/IEC 19774 draft 4.1) is the load-bearing
frame. Each layer below attaches to that same joint hierarchy, so they compose:
animate the joints once and every layer follows. Ordered by dependency and
effort. Each entry names the X3D/HAnim mechanism it would use and where the MCP
pipeline already reaches.

## Layer 0 — Skeleton (done)
LOA5 HAnim humanoid; runner (generated stick geometry) + classroom (NIST bone
meshes). Real `HAnimJoint`/`HAnimSegment`, rendered in X_ITE.

## Layer 1 — Coveroids / clothing (next)
A "coveroid" is a closed surface that *covers* the figure — the simplest skin:
clothing or a body shell. Mechanism: a single `HAnimHumanoid.skin`
`IndexedFaceSet` whose vertices are bound to joints via `skinCoordIndex` /
`skinCoordWeight` (linear-blend skinning). Start with rigid garment pieces
parented to single joints (helmet→skullbase, shoes→talocrural, a tunic split
across spine joints), then graduate to weighted skin. MCP angle: generate
garment meshes parametrically; FLUX for fabric textures.

## Layer 2 — Ligaments & tendons
Connective bands spanning two joints. Mechanism: thin `Extrusion` or
`IndexedFaceSet` segments anchored at two `HAnimSite` feature points (the LOA5
skeleton already defines many sites), so they stretch as joints move — a
two-site follower. Mostly authoring + correct site references.

## Layer 3 — Muscles
Volumetric bodies that bulge. Mechanism: per-muscle `IndexedFaceSet` skinned to
the spanning joints, plus `HAnimDisplacer` nodes on the relevant segments to
drive contraction bulge as a morph. This is where `HAnimDisplacer` (already in
the X3D HAnim component) earns its place. Significant geometry work.

## Layer 4 — Organs
Mostly non-articulated meshes parented to the appropriate segment (heart/lungs→
thoracic segments, etc.). The Web3D Medical archive already has organ-adjacent
models to reference. Mechanism: segment-parented `Inline` meshes;
semi-transparent `PhysicalMaterial` for the visible-layers teaching view.

## Layer 5 — Nerve plexus / vasculature
Branching networks routed along the skeleton. Mechanism: `IndexedLineSet` or
thin extrusions following site-to-site paths; could be procedurally generated
from a graph. Good candidate for MCP/programmatic generation.

## Layer 6 — Skin
Full weighted body skin over everything. Mechanism: the canonical
`HAnimHumanoid.skin` + `skinCoord` with per-vertex joint weights — the same
LBS as Layer 1 but a complete envelope. Subsurface look via `PhysicalMaterial`.

## Layer 7 — Hair
Mechanism: card-based strips or `IndexedLineSet` tufts parented to skullbase;
optionally physics later. Lowest priority, highest polish.

## Cross-cutting
- **Toggle layers** with `Switch`/`HAnimHumanoid` visibility so a teacher peels
  from skin → muscle → skeleton (the classroom demo's natural endgame).
- **Each layer is a potential ISO-draft contribution**: the draft standardizes
  the skeleton + skin; ligament/muscle/organ/nerve conventions are open ground.
- **Viewer**: author against X_ITE (full HAnim + skinning); the X3DOM gap
  (no HAnim rendering; MutationObserver init bug) is a parallel upstream
  contribution opportunity.
