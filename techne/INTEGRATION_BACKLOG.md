# Technē integration backlog

Study-grounded openings for "weighting Technē with useful integrations," from the
`know-the-material` deep study (x3d edit tools, `x3d.py`, `validate_semantic`,
X3DUOM, the cave corpus). Each is a real opening seen in the code, prioritized by
GOALS.md charter (output quality · coherence · efficiency — not novelty). Pin the
source before building; the study cited every one.

## Tier 1 — align Technē with the server's own ground truth (output quality)

1. **✅ BUILT — Mirror `validate_semantic` into `rules.py`** (commit "mirror the
   server's validate_semantic catalog"). Enforced per-call: **duplicate-def**
   (def_node), **ROUTE-needs-DEF** (new add_route adapter + `SceneState.id_to_def`),
   and the **richer interpolator arity** (`INTERP_ARITY`/`INTERP_BASE`, Spline/Geo/
   Squad/2D/variable). Catalogued + scope-mapped (`PER_CALL`/`WHOLE_SCENE`): the
   full ROUTE family, shape/group/viewpoint, use-undefined/before, containerfield
   IDs — deferred to the upstream whole-scene `validate_semantic` Technē fronts,
   rather than re-implementing (and drifting from) the 596-line engine. Two new
   eval tasks (duplicate-def, route-no-def) demonstrate it. *src/validation/semantic.py.*

2. **◐ PARTIAL — Serialization-layer default re-assertion.** Built
   `craft.reassert_envlight_global(xml)` (deterministic + idempotent; injects the
   omitted `EnvironmentLight global='true'` so IBL works) and wired it into
   `autofix_x3d`'s output. *Still open:* generalize to PointLight/SpotLight only
   where safe; the reserved-word map (`global↔global_` etc.); guarding the
   `setattr(node, cf, child)` vanish — these belong upstream in `scene.py:217-246`,
   not in the proxy. *Source: x3d.py lib map; scene.py.*

3. **Field-name + type pre-validation via X3DUOM.** `create_node`/`set_field` accept
   unknown fields loosely (an unknown field raises a raw `TypeError` from x3d.py, or
   `modify_x3d_node` writes a misspelled attribute and reports success). Add a
   Technē pre-validator using `get_node_fields(node_type)` + `get_field_types()`
   (regex/tupleSize/defaultValue) that BLOCKS with a prescriptive valid-field list.
   *Source: x3duom.py:26-40; scene_ops.py modify_x3d_node.*

## Tier 2 — extend Technē to the unguarded edit surface (output quality + coherence)

4. **✅ BUILT — Guard the content-based edit tools** (commit "guard the content-based
   edit tools via a validate post-pass"). After modify/move/remove/convert/
   add_x3d_route, Technē runs the result back through the server's own validate_x3d
   + validate_semantic and appends a "Technē post-check:" note listing what the edit
   broke (modify's typos via XSD; move's misfiled containerField via semantic; HARD
   errors only, warnings/infos skipped as noise). Error-string returns are flagged
   ("returned an error string, not a document"). convert_x3d also gets an
   element-count **drop-diff** (it leaves a valid-but-smaller doc no validator
   flags). No X3DUOM coupling, no re-impl. Verified live. *Source: scene_ops.py,
   convert.py.*

5. **Uniform error handling across granular tools.** Only `add_child` catches
   `SceneError` → friendly text; the rest let it propagate (isError). Normalize so
   the eval's `errored()` and callers see one shape. *Source: granular.py.*

6. **add_route craft adapter.** Granular `add_route` does ZERO field/access/type
   validation (unlike the serialized `add_x3d_route`). Borrow `animate._add_route`'s
   checks. Track DEF removal so `remove_node` drops the DEF and dangling ROUTEs
   warn. *Source: scene.py add_route; animate.py:182-270.*

## Tier 3 — efficiency + the caves→Technē provenance bridge

7. **✅ BUILT — DEF/USE-deduplication** (efficiency; commit "DEF/USE appearance
   dedup"). `craft.dedupe_appearances(xml)`: collapses byte-identical `Appearance`
   subtrees to one DEF + USE references — deterministic, idempotent, collision-safe,
   only touches un-DEF'd identical blocks. Verified on the real Samwel cave: **39 →
   5 inlined `ImageTexture` nodes**, 81 appearances → USE, re-parses valid. Opt-in
   (a utility for the cave pipeline / tools, NOT an automatic proxy transform — it
   would surprise model output). *Source: cave-models study.*

8. **◐ PROTOTYPE — Provenance bridge** (`techne/provenance.py`, 11 tests; see
   `techne/PROVENANCE_BRIDGE.md`). Enforces the standardized X3D provenance
   MetadataSet (from docs/provenance-metadata-proposal.md) against an archive.json-
   shaped asset ledger. **Layer 1 (sourcing) BUILT**: documented-needs-resolvable-
   citation, catalogId-resolves, public-domain-only, generated-must-disclose,
   well-formed-status — the message is the correction; demoed against the real
   archive.json. *Decision pending* (PROVENANCE_BRIDGE.md §"The decision"): bless
   the vocabulary, adopt in the cave generators (emit the blocks), wire the gate
   (opt-in TECHNE_ASSET_LEDGER), and whether to build **Layer 2** (the content-
   semantic must_not_invent rules — taxon/depth/cal-BC — needing a domain claim
   schema). Not auto-wired: a scope extension awaiting your call.
   *Source: drawings/strata_spec.json, archive.json; generate_*.py PROVENANCE blocks.*

## Tier 4 — X3DUOM depth (supports Tiers 1–2)

9. **Abstract→concrete child-type resolver** (walk `get_abstract_types()` baseType
   chains) + parse `containerFieldChoices*` so Technē can list the *exact* legal
   slots deterministically instead of approximating. Bake a static
   `{node: default containerField}` + alternate-choice table. Run
   `get_coverage_report()` at startup as a health check (flags the 4.0-tooltips /
   4.1-UOM skew). *Source: x3duom.py:199-230; describe study.*

---

**Recommended first build on resume:** Tier 1 #1 (mirror `validate_semantic`) — it
is the most charter-aligned (output quality, measurable on the eval harness) and
turns "Technē approximates the craft" into "Technē enforces the server's own
documented catalog." #2 (serialization default re-assertion) is the natural pair —
it finally closes the `EnvironmentLight.global` silent failure end to end.
