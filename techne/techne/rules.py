"""The craft catalog: documented X3D silent-failure modes as executable corrections.

This is the single most important hand-authored asset in Technē (TECHNE_SPEC §4).
It is `docs/x3dpy-bug-report.md` reread as a machine-usable table:

    {rule_name: (severity, prescriptive_correction, source)}

Each entry is a *known* silent failure — output that passes the XSD yet renders
wrong or blank — with its stated workaround turned into an executable correction.
The difference Technē preserves is "rejected" vs "rejected: use
containerField='baseTexture'": the error message IS the correction.

`episteme` (the XSD) is decidable and closed; `techne` (this catalog) is the
contingent craft the schema does not encode. When the schema and a real x3d-mcp
tool signature disagree, the real signature wins — but these rules are the content.
"""
from __future__ import annotations

HARD = "hard"   # blocking — BAML @@assert; the architect's sign-off boundary
SOFT = "soft"   # advisory — BAML @@check; "looks right?" warning, non-blocking


# --- the technē the XSD cannot express -------------------------------------

# A node placed into a parent FIELD whose container differs from the node type's
# DEFAULT container must carry containerField == that field name, or a conformant
# player files it into the default field and silently drops/misrenders it.
# (Bug 1.) The default container per node type:
DEFAULT_CONTAINER = {
    "HAnimJoint": "children",
    "HAnimSegment": "children",
    "HAnimSite": "children",
    "ImageTexture": "texture",
    "PixelTexture": "texture",
    "MovieTexture": "texture",
    "Coordinate": "coord",
    "Normal": "normal",
    "TextureCoordinate": "texCoord",
    "Color": "color",
}

# Fields on a parent that take a node in a NON-default slot, by parent node type.
# (Used to recognise "this placement needs an explicit containerField".)
NONDEFAULT_SLOTS = {
    "HAnimHumanoid": {"skeleton", "joints", "segments", "sites", "skinCoord",
                      "skinNormal", "skin"},
    "PhysicalMaterial": {"baseTexture", "emissiveTexture", "normalTexture",
                         "occlusionTexture", "metallicRoughnessTexture"},
    "UnlitMaterial": {"emissiveTexture", "normalTexture"},
    "Material": {"diffuseTexture", "emissiveTexture", "normalTexture",
                 "occlusionTexture", "specularTexture", "shininessTexture",
                 "ambientTexture"},
}

# Texture node types that route into a material's texture *slot* (not the default
# 'texture' container, which PBR/unlit materials do not define).
TEXTURE_NODES = {"ImageTexture", "PixelTexture", "MovieTexture"}

# The legal texture slots per material type. With several legal slots, Technē
# cannot guess WHICH (baseTexture vs normalTexture is intent) — it blocks + lists.
MATERIAL_TEXTURE_SLOTS = {
    "PhysicalMaterial": ["baseTexture", "emissiveTexture", "normalTexture",
                         "occlusionTexture", "metallicRoughnessTexture"],
    "UnlitMaterial": ["emissiveTexture", "normalTexture"],
    "Material": ["diffuseTexture", "emissiveTexture", "normalTexture",
                 "occlusionTexture", "specularTexture", "shininessTexture",
                 "ambientTexture"],
}

# Legal non-default slots for a child placed directly under an HAnimHumanoid,
# keyed by child node type.
HUMANOID_SLOTS = {
    "HAnimJoint": ["skeleton", "joints"],
    "HAnimSegment": ["segments"],
    "HAnimSite": ["sites", "viewpoints"],
    "Coordinate": ["skinCoord"],
    "Normal": ["skinNormal"],
}

# Floats per key for each interpolator's keyValue (keyValue length must be
# len(key) * arity). None = a variable multiple of a base tuple (e.g. a
# CoordinateInterpolator stores numCoords*3 per key). Mirrors the server's own
# validate_semantic._INTERP_ARITY / _INTERP_BASE so Technē's per-call check agrees
# with the authoritative whole-scene validator. (src/validation/semantic.py)
INTERP_ARITY = {
    "ScalarInterpolator": 1, "SplineScalarInterpolator": 1,
    "PositionInterpolator2D": 2, "SplinePositionInterpolator2D": 2,
    "PositionInterpolator": 3, "SplinePositionInterpolator": 3,
    "GeoPositionInterpolator": 3,
    "ColorInterpolator": 3,
    "OrientationInterpolator": 4, "SquadOrientationInterpolator": 4,
    "CoordinateInterpolator": None, "NormalInterpolator": None,
    "CoordinateInterpolator2D": None,
}
INTERP_BASE = {"CoordinateInterpolator": 3, "NormalInterpolator": 3,
               "CoordinateInterpolator2D": 2}
# back-compat alias: membership tests ("is this an interpolator?") still work.
INTERP_COMPONENTS = INTERP_ARITY


# --- the rule -> prescriptive-correction catalog ----------------------------

CATALOG = {
    "container_field_present": (
        HARD,
        "Node '{node_type}' is placed in the non-default field '{field}' but has "
        "no containerField. Set containerField='{field}' or a conformant player "
        "files it into '{node_type}'s default container ('{default}') and renders "
        "nothing. (x3d.py Bug 1: dropped containerField.)",
        "docs/x3dpy-bug-report.md#bug-1",
    ),
    "container_field_correct": (
        HARD,
        "Node '{node_type}' in field '{field}' has containerField='{got}', but it "
        "must equal the field it is placed in: set containerField='{field}'. "
        "(x3d.py Bug 1: containerField must match the slot.)",
        "docs/x3dpy-bug-report.md#bug-1",
    ),
    "container_field_required": (
        HARD,
        "Adding '{child}' to '{parent}' needs an explicit containerField, but none "
        "was given — it would default to '{default}', which '{parent}' does not "
        "define as a field, so the child is silently dropped. Specify "
        "containerField as one of: {slots}. (x3d.py Bug 1.)",
        "docs/x3dpy-bug-report.md#bug-1",
    ),
    "container_field_invalid_slot": (
        HARD,
        "containerField='{got}' is not a legal slot for '{child}' in '{parent}'. "
        "Use one of: {slots}. (x3d.py Bug 1.)",
        "docs/x3dpy-bug-report.md#bug-1",
    ),
    "envlight_global_set": (
        SOFT,
        "EnvironmentLight omits 'global'. The X3D 4.0 spec default is FALSE, so an "
        "omitted 'global' reads as non-global and image-based lighting silently "
        "dies. NOTE: x3d.py rejects a 'global' constructor kwarg (it uses 'global_') "
        "and omits its 'global_=True' default from the XML — so this cannot be "
        "fixed in the create_node args; inject global='true' into the emitted XML "
        "(serialization/autofix layer) for scene-wide IBL. (x3d.py Bug 2.)",
        "docs/x3dpy-bug-report.md#bug-2",
    ),
    "interp_lengths_match": (
        HARD,
        "{node_type}: {n_key} key fraction(s) but {n_val} keyValue value(s) -- "
        "{detail}. Mismatched key/keyValue lengths silently corrupt the animation.",
        "src/validation/semantic.py (interpolator-key-length)",
    ),
    "use_after_def": (
        HARD,
        "USE='{use}' references a DEF that is not defined earlier in the scene. A "
        "USE must follow its DEF. Define a node with DEF='{use}' before this USE "
        "(or correct the name).",
        "TECHNE_SPEC.md#3.4",
    ),
    "hanim_version_explicit": (
        SOFT,
        "HAnimHumanoid omits 'version'; HAnim files conventionally state it "
        "explicitly. Consider version='2.0'.",
        "docs/x3dpy-bug-report.md#minor-note",
    ),
    "texture_url_image_ext": (
        SOFT,
        "Texture url '{url}' does not end in a known image extension "
        "(.png/.jpg/.jpeg/.gif/.webp). Verify the path resolves.",
        "TECHNE_SPEC.md#3.1",
    ),

    # --- mirrored from the server's validate_semantic (the authoritative
    #     whole-scene validator). Technē enforces the incrementally-checkable
    #     ones per-call (see SCOPE); the rest it CATALOGS and defers to the
    #     upstream validate_semantic pass it fronts, rather than re-implementing
    #     a 596-line whole-scene engine that would drift. ----------------------

    "duplicate_def": (
        HARD,
        "Duplicate DEF name '{name}': it is already defined in this scene. DEF "
        "names must be unique. Rename this one, or USE='{name}' to reference the "
        "existing node instead of redefining it.",
        "src/validation/semantic.py (duplicate-def)",
    ),
    "route_no_def": (
        HARD,
        "ROUTE endpoint node '{node_id}' has no DEF name, but a ROUTE references "
        "nodes by DEF. def_node it (def_node('{node_id}', '<Name>')) before "
        "routing, then ROUTE from/to that name.",
        "src/validation/semantic.py (route-missing-from/to-node); scene.add_route",
    ),

    # whole-scene catalog (deferred to upstream validate_semantic; SCOPE marks these)
    "use_undefined_def": (
        HARD,
        "USE='{use}' references a DEF that does not exist in this scene. Available "
        "DEF names: {available}.",
        "src/validation/semantic.py (use-undefined-def)",
    ),
    "use_before_def": (
        HARD,
        "USE='{use}' appears before its DEF in document order. A USE must follow "
        "the DEF it references.",
        "src/validation/semantic.py (use-before-def)",
    ),
    "unused_def": (
        SOFT,
        "DEF='{name}' is defined but never USE'd. Fine if referenced via ROUTE or "
        "externally.",
        "src/validation/semantic.py (unused-def)",
    ),
    "route_missing_from_node": (
        HARD,
        "ROUTE fromNode='{node}' not found. Available DEFs: {available}.",
        "src/validation/semantic.py (route-missing-from-node)",
    ),
    "route_missing_to_node": (
        HARD,
        "ROUTE toNode='{node}' not found. Available DEFs: {available}.",
        "src/validation/semantic.py (route-missing-to-node)",
    ),
    "route_invalid_from_field": (
        HARD,
        "ROUTE fromField='{field}' does not exist on {type} (DEF='{node}').",
        "src/validation/semantic.py (route-invalid-from-field)",
    ),
    "route_invalid_to_field": (
        HARD,
        "ROUTE toField='{field}' does not exist on {type} (DEF='{node}').",
        "src/validation/semantic.py (route-invalid-to-field)",
    ),
    "route_wrong_access_type": (
        HARD,
        "ROUTE {field}='{name}' on {type} has accessType='{access}' -- a source "
        "must be outputOnly/inputOutput and a destination inputOnly/inputOutput.",
        "src/validation/semantic.py (route-wrong-access-type)",
    ),
    "route_type_mismatch": (
        HARD,
        "ROUTE type mismatch: {from_ref} is {from_type} but {to_ref} is {to_type}. "
        "ROUTE requires matching field types.",
        "src/validation/semantic.py (route-type-mismatch)",
    ),
    "shape_no_geometry": (
        SOFT,
        "Shape{label} has no geometry child. Add a geometry node like Box, Sphere, "
        "or IndexedFaceSet, or it draws nothing.",
        "src/validation/semantic.py (shape-no-geometry)",
    ),
    "shape_no_appearance": (
        SOFT,
        "Shape{label} has no Appearance; it renders with a default white material.",
        "src/validation/semantic.py (shape-no-appearance)",
    ),
    "empty_group": (
        SOFT,
        "{tag}{label} has no children. Empty grouping nodes have no effect.",
        "src/validation/semantic.py (empty-group)",
    ),
    "no_viewpoint": (
        SOFT,
        "Scene has no Viewpoint; the browser uses a default camera. Add a Viewpoint "
        "for a defined initial view.",
        "src/validation/semantic.py (no-viewpoint)",
    ),
    "containerfield_unknown": (
        HARD,
        "{child} containerField='{cf}' but {parent} has no field named '{cf}'.{suggest}",
        "src/validation/semantic.py (containerfield-unknown)",
    ),
    "containerfield_not_node": (
        HARD,
        "{child} containerField='{cf}' targets {parent}.{cf}, a value field, not a "
        "node container.{suggest}",
        "src/validation/semantic.py (containerfield-not-node)",
    ),
    "containerfield_type_mismatch": (
        HARD,
        "{parent}.{cf} does not accept a {child} (accepts: {accepts}).{suggest}",
        "src/validation/semantic.py (containerfield-type-mismatch)",
    ),
}

# Coverage map: which catalog rules Technē enforces INCREMENTALLY (per tool call,
# before the call lands) vs which it defers to the upstream whole-scene
# validate_semantic it fronts. Honest about what the proxy can and cannot see from
# a single call's arguments + its minimal SceneState.
PER_CALL = {
    "container_field_present", "container_field_correct", "container_field_required",
    "container_field_invalid_slot", "envlight_global_set", "interp_lengths_match",
    "use_after_def", "hanim_version_explicit", "texture_url_image_ext",
    "duplicate_def", "route_no_def",
}
WHOLE_SCENE = {
    "use_undefined_def", "use_before_def", "unused_def",
    "route_missing_from_node", "route_missing_to_node", "route_invalid_from_field",
    "route_invalid_to_field", "route_wrong_access_type", "route_type_mismatch",
    "shape_no_geometry", "shape_no_appearance", "empty_group", "no_viewpoint",
    "containerfield_unknown", "containerfield_not_node", "containerfield_type_mismatch",
}


def correction(rule: str, **fields) -> str:
    """Format the prescriptive correction for a failed rule.

    The returned string IS the fix, not a bare 'invalid' — that difference is the
    whole prescriptive-correction insight from the original session.
    """
    _sev, template, _src = CATALOG[rule]
    return template.format(**fields)


def severity(rule: str) -> str:
    return CATALOG[rule][0]


def source(rule: str) -> str:
    return CATALOG[rule][2]
