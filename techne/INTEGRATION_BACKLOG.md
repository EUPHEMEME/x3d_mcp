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
