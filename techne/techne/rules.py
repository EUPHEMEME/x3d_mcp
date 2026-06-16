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
    "UnlitMaterial": {"emissiveTexture"},
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
    "UnlitMaterial": ["emissiveTexture"],
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

# Interpolator value-components per key (keyValue length must == len(key) * this).
INTERP_COMPONENTS = {
    "OrientationInterpolator": 4,      # SFRotation
    "PositionInterpolator": 3,         # SFVec3f
    "PositionInterpolator2D": 2,
    "ColorInterpolator": 3,
    "ScalarInterpolator": 1,
    "NormalInterpolator": 3,
    # CoordinateInterpolator is per-key variable (numCoords); handled specially.
}


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
        HARD,
        "EnvironmentLight omits 'global'. The X3D 4.0 spec default is FALSE, so an "
        "omitted 'global' reads as non-global and image-based lighting silently "
        "dies. Write global='true' explicitly for scene-wide IBL. "
        "(x3d.py Bug 2: wrong EnvironmentLight.global default.)",
        "docs/x3dpy-bug-report.md#bug-2",
    ),
    "interp_lengths_match": (
        HARD,
        "{node_type} has {n_key} key fractions but {n_val} keyValue components "
        "(expected {expected} = {n_key} x {comp} per key). Mismatched key/keyValue "
        "lengths silently corrupt the animation. Make keyValue length == "
        "len(key) x {comp}.",
        "TECHNE_SPEC.md#3.2",
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
