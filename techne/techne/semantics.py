"""Standing-semantics injector — the coherence layer (GOALS.md §2).

LLMs drift over a session: they forget X3D is right-handed and metres-and-radians,
that a TimeSensor animates only through ROUTEs, that an HAnimJoint's rest pose is
identity. These invariants are few, well-documented, and exactly the ones a prompt
read once at the top of a session stops holding. So Technē surfaces them
*deterministically* — riding back as a SOFT reminder on the relevant tool result,
so the model re-sees the invariant precisely when it is acting on it, by mechanism
rather than by a prompt it may not re-read.

`advise(tool, args, state)` is pure: it returns every (key, text) whose trigger the
call matches. The proxy is responsible for once-per-session de-duplication (it owns
`SceneState.surfaced_reminders`) and the per-call cap, so this stays trivially
testable. A reminder NEVER blocks and never rewrites args — it is advisory only.

The reminder TEXT is verified against ISO/IEC 19775-1 (X3D 4.0) and ISO/IEC 19774
(HAnim); see techne/eval and the verify-x3d-invariants workflow. Keep each line
short and ASCII — it costs tokens on every relevant result.
"""
from __future__ import annotations

from . import craft

ROTATION_FIELDS = {"rotation", "orientation"}
# nodes whose `rotation` is a scalar SFFloat (radians), NOT an SFRotation 4-tuple,
# so the axis-angle units_angles reminder would give wrong value-shape guidance.
SCALAR_ROTATION_TYPES = {"TextureTransform"}
LIGHT_TYPES = {"DirectionalLight", "PointLight", "SpotLight", "EnvironmentLight"}
VIEWPOINT_TYPES = {"Viewpoint", "OrthoViewpoint", "GeoViewpoint"}
HANIM_TYPES = {"HAnimHumanoid", "HAnimJoint", "HAnimSegment", "HAnimSite",
               "HAnimDisplacer"}
GEOMETRY_TYPES = {"Shape", "Box", "Sphere", "Cone", "Cylinder", "IndexedFaceSet",
                  "IndexedTriangleSet", "TriangleSet", "TriangleStripSet",
                  "Extrusion", "ElevationGrid", "Text", "PointSet", "LineSet",
                  "IndexedLineSet", "GeoElevationGrid", "NurbsPatchSurface"}
ROUTE_TOOLS = {"add_route", "add_x3d_route"}
TRANSFORM_TYPES = {"Transform", "HAnimHumanoid", "HAnimJoint", "HAnimSite"}

# key -> reminder text. Verbatim from the verify-x3d-invariants workflow's
# adversarially-tightened, spec-grounded final_text (ISO/IEC 19775-1, 19774).
# Notably the pbr_lighting reminder was *corrected* there: X3D's default headlight
# (NavigationInfo headlight=TRUE) lights PhysicalMaterial, so PBR is NOT black with
# no light node — the real guidance is to add EnvironmentLight (IBL) for good PBR.
REMINDERS: dict[str, str] = {
    "units_angles":
        "Use RADIANS for X3D angles, METERS for lengths (root UNIT statement may "
        "override). SFRotation is axisX axisY axisZ angle, right-handed, axis "
        "normalized: 0 1 0 1.5708 = 90deg +Y, never 0 1 0 90",
    "handedness":
        "X3D is right-handed: +X right, +Y up, +Z toward viewer; default view "
        "looks down -Z at origin. Default Viewpoint position 0 0 10, orientation "
        "0 0 1 0. Angles in radians, lengths in metres.",
    "timesensor_routes":
        "Wire animation via ROUTEs: TimeSensor.fraction_changed->Interpolator."
        "set_fraction, then value_changed->target.field. Match interpolator type "
        "to target field. cycleInterval>0s; loop=true to repeat.",
    "hanim_restpose":
        "HAnimJoint rotation defaults to identity (0 0 1 0); set each joint's "
        "center to its rest location, pose via rotation. Attach root with "
        "containerField='skeleton', USE every joint in 'joints'.",
    "viewpoint_missing":
        "If no Viewpoint is bound, the default camera sits at 0 0 10 looking down "
        "-Z (+Y up, right-handed), so shapes far from origin can render blank/"
        "off-screen -- add one that frames your geometry.",
    "pbr_lighting":
        "PhysicalMaterial is lit by all lights incl. the default headlight "
        "(NavigationInfo headlight=TRUE), so not black with no light node. Add "
        "EnvironmentLight (IBL) for good PBR; metallic needs IBL.",
}


def _has_type(state, types_set) -> bool:
    return any(t in types_set for t in getattr(state, "id_to_type", {}).values())


def advise(tool: str, args: dict, state) -> list[tuple[str, str]]:
    """Every (key, reminder) whose trigger this call matches. Pure; no de-dup."""
    args = args or {}
    node_type = args.get("node_type", "")
    fields = args.get("fields") or {}
    out: list[tuple[str, str]] = []

    def fire(key):
        out.append((key, REMINDERS[key]))

    # radians/metres — a rotation-bearing SFRotation field is being authored
    # (skip nodes whose rotation is a scalar SFFloat, e.g. TextureTransform)
    set_field_nt = getattr(state, "id_to_type", {}).get(args.get("node_id", ""), "")
    if (tool == "create_node" and node_type not in SCALAR_ROTATION_TYPES
            and (set(fields) & ROTATION_FIELDS or node_type == "OrientationInterpolator")) \
            or (tool == "set_field" and args.get("field_name") in ROTATION_FIELDS
                and set_field_nt not in SCALAR_ROTATION_TYPES):
        fire("units_angles")

    # handedness — first spatial framing node
    if tool == "create_node" and node_type in (VIEWPOINT_TYPES | {"Transform"}):
        fire("handedness")

    # timer/animation wiring
    if (tool == "create_node" and (node_type == "TimeSensor"
                                   or node_type in craft.rules.INTERP_COMPONENTS)) \
            or tool in ROUTE_TOOLS:
        fire("timesensor_routes")

    # HAnim rest pose
    if tool == "create_node" and node_type in HANIM_TYPES:
        fire("hanim_restpose")

    # geometry authored before any Viewpoint exists
    if tool == "create_node" and node_type in GEOMETRY_TYPES \
            and not _has_type(state, VIEWPOINT_TYPES):
        fire("viewpoint_missing")

    # PBR material authored before any light exists
    if tool == "create_node" and node_type == "PhysicalMaterial" \
            and not _has_type(state, LIGHT_TYPES):
        fire("pbr_lighting")

    return out
