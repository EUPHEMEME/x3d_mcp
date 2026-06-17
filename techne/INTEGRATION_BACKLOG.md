# Technē integration backlog

Study-grounded openings for "weighting Technē with useful integrations," from the
`know-the-material` deep study (x3d edit tools, `x3d.py`, `validate_semantic`,
X3DUOM, the cave corpus). Each is a real opening seen in the code, prioritized by
GOALS.md charter (output quality · coherence · efficiency — not novelty). Pin the
source before building; the study cited every one.

## Tier 1 — align Technē with the server's own ground truth (output quality)

1. **Mirror `validate_semantic` into `rules.py`.** The server's validator runs 9
   checks / 18 check-IDs; Technē's catalog mirrors only a subset. Port the
   **ROUTE-validity family** (missing from/to-node, invalid from/to-field, wrong
   access-type, type-mismatch), **duplicate-def** (HARD), **shape-no-geometry /
   shape-no-appearance / empty-group / no-viewpoint** (SOFT), and replace
   `INTERP_COMPONENTS` with semantic.py's richer `_INTERP_ARITY`/`_INTERP_BASE`
   (Spline/Geo/Squad, 2D, variable-arity Coordinate). Split `use_after_def` into
   `use-undefined-def` vs `use-before-def`. *Source: src/validation/semantic.py.*
   → This is the single highest-value move: it makes Technē match the authoritative
   validator instead of approximating it.

2. **Serialization-layer default re-assertion** (the real fix for silent-failure
   #2). `x3d.py` omits any field left at its library default, so
   `EnvironmentLight/PointLight/SpotLight global='true'` (default True) can *never*
   appear in output → IBL silently dies. Add a string pass in `scene.to_xml()`
   (sibling to the existing `autofix_containerfields`) that force-injects the
   omitted-but-semantically-required defaults. Centralize the reserved-word map
   (`global↔global_`, `class↔class_`, `id↔id_`, `style↔style_`). Guard the
   `setattr(node, cf, child)` bridge: a cf that isn't a real field name silently
   vanishes at serialization (no `__slots__`). *Source: x3d.py lib map; scene.py:217-246.*

3. **Field-name + type pre-validation via X3DUOM.** `create_node`/`set_field` accept
   unknown fields loosely (an unknown field raises a raw `TypeError` from x3d.py, or
   `modify_x3d_node` writes a misspelled attribute and reports success). Add a
   Technē pre-validator using `get_node_fields(node_type)` + `get_field_types()`
   (regex/tupleSize/defaultValue) that BLOCKS with a prescriptive valid-field list.
   *Source: x3duom.py:26-40; scene_ops.py modify_x3d_node.*

## Tier 2 — extend Technē to the unguarded edit surface (output quality + coherence)

4. **Guard the content-based edit tools.** `modify_x3d_node` (no field/type/
   containerField validation — writes typos as success), `move_x3d_node` (never
   sets containerField → reparenting misfiles), `convert_x3d` (silently drops
   unknown nodes/attributes/containerFields). Add adapters: validate fields on
   modify, re-assert containerField on move, and a convert node/attr-count diff
   that reports drops. Also: these return errors as **plain strings** indistinguishable
   from success — add the leading-`<?xml` sniff so Technē/callers can tell.
   *Source: scene_ops.py, convert.py.*

5. **Uniform error handling across granular tools.** Only `add_child` catches
   `SceneError` → friendly text; the rest let it propagate (isError). Normalize so
   the eval's `errored()` and callers see one shape. *Source: granular.py.*

6. **add_route craft adapter.** Granular `add_route` does ZERO field/access/type
   validation (unlike the serialized `add_x3d_route`). Borrow `animate._add_route`'s
   checks. Track DEF removal so `remove_node` drops the DEF and dangling ROUTEs
   warn. *Source: scene.py add_route; animate.py:182-270.*

## Tier 3 — efficiency + the caves→Technē provenance bridge

7. **DEF/USE-deduplication pass** (efficiency). Collapse repeated identical
   `Appearance`/texture blocks into one DEF + USE — the Samwel cave inlines the same
   3-texture PBR appearance 39× (39 `ImageTexture` nodes for 4 files). A pure-win
   deterministic post-processor. *Source: cave-models study.*

8. **Provenance rule-set from `must_not_invent`** (the integration the cave work
   *reveals*). Load the 12-clause `strata_spec.json:must_not_invent` into `rules.py`
   as HARD provenance rules (the clause text IS the correction, with its citation),
   and extend `gate.py` so a scene can't pass unless geometry/caption carries a
   `documented|interpretive` tag. Optionally an `archive.json` asset-allowlist:
   a documentary texture must resolve to a cited public-domain entry.
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
