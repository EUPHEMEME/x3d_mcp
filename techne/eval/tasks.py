"""Eval task set — shared by the scripted and live-LLM runners.

SCRIPTED tasks are deterministic tool-call sequences. Each encodes a *naive*
authoring move (what an unguided model emits) that may contain a documented X3D
silent-failure. Run the same sequence through the raw x3d-mcp and through Technē
and the difference is the measurement:

  * raw   — the documented mistake passes the schema and reaches the scene (leak);
  * Technē — the mistake is blocked with a prescriptive correction (the agent
             applies it and retries) or silently repaired, so it never lands.

A `mistake=None` step is a clean control move; a task with no mistakes proves
Technē is transparent on already-correct input (no extra round-trips).

LIVE tasks are natural-language authoring prompts for a real model driving the
same two stacks through an agentic tool-use loop.
"""
from dataclasses import dataclass, field


@dataclass
class Step:
    tool: str
    args: dict
    capture: str | None = None        # store the returned node ID under this key
    mistake: str | None = None        # documented failure label (None = clean move)
    block_token: str | None = None    # the Technē block must name this (proves it's actionable)
    fix: dict | None = None           # arg overrides to apply, then retry, when blocked
    fix_steps: list | None = None     # corrective steps to run *before* retrying (e.g. DEF before USE)


@dataclass
class ScriptedTask:
    name: str
    summary: str
    steps: list
    caveat: str = ""                  # honest note (e.g. a metric this task can't move)


# A texture node's default containerField is `texture`; inside a PhysicalMaterial
# it must be one of several PBR slots (baseTexture, normalTexture, ...). Defaulted,
# a conforming viewer silently drops it. Several legal slots -> Technē BLOCKs and
# lists them rather than guessing.
TEXTURED_MATERIAL = ScriptedTask(
    "textured-material",
    "ImageTexture placed in PhysicalMaterial without a containerField",
    [
        Step("reset_scene", {}),
        Step("create_node", {"node_type": "PhysicalMaterial",
                             "fields": {"baseColor": [0.8, 0.3, 0.2]}}, capture="mat"),
        Step("create_node", {"node_type": "ImageTexture",
                             "fields": {"url": ["wood.png"]}}, capture="tex"),
        Step("add_child", {"parent_id": "@mat", "child_id": "@tex", "container_field": ""},
             mistake="texture in PhysicalMaterial without containerField -> texture dropped",
             block_token="baseTexture",
             fix={"container_field": "baseTexture"}),
    ],
    caveat="failure mode is a dropped texture, not a blank scene: scored by "
           "mistakes-caught, not the render column.",
)

# A USE must follow the DEF it names. Emitted early it is a dangling reference and
# the subtree renders empty. The fix is to DEF the target first, then retry.
USE_BEFORE_DEF = ScriptedTask(
    "use-before-def",
    "USE references a DEF name that has not been defined yet",
    [
        Step("reset_scene", {}),
        Step("create_node", {"node_type": "Group", "fields": {}}, capture="grp"),
        Step("use_node", {"def_name": "Hero"},
             mistake="USE 'Hero' before any DEF 'Hero' -> dangling reference, empty subtree",
             block_token="Hero",
             fix_steps=[
                 Step("create_node", {"node_type": "Shape", "fields": {}}, capture="hero"),
                 Step("def_node", {"node_id": "@hero", "name": "Hero"}),
             ]),
    ],
)

# An interpolator drives animation by mapping each key (a fraction in [0,1]) to one
# keyValue. Mismatched lengths pass the schema and break the animation silently.
INTERPOLATOR_PARITY = ScriptedTask(
    "interpolator-parity",
    "ScalarInterpolator with key/keyValue lengths that disagree",
    [
        Step("reset_scene", {}),
        Step("create_node", {"node_type": "ScalarInterpolator",
                             "fields": {"key": [0.0, 0.5, 1.0],
                                        "keyValue": [0.0, 1.0]}},
             mistake="3 keys but 2 keyValues -> animation interpolates wrong / breaks",
             block_token="key",
             fix={"fields": {"key": [0.0, 0.5, 1.0], "keyValue": [0.0, 0.5, 1.0]}}),
    ],
    caveat="failure mode is broken animation, invisible in a still: scored by "
           "mistakes-caught, not the render column.",
)

# Control: already-correct authoring. Technē must add zero blocks and zero extra
# round-trips here — if it doesn't, it has false positives.
CONTROL_CLEAN = ScriptedTask(
    "control-clean",
    "Correct authoring — texture placed with the right containerField",
    [
        Step("reset_scene", {}),
        Step("create_node", {"node_type": "PhysicalMaterial",
                             "fields": {"baseColor": [0.8, 0.3, 0.2]}}, capture="mat"),
        Step("create_node", {"node_type": "ImageTexture",
                             "fields": {"url": ["wood.png"]}}, capture="tex"),
        Step("add_child", {"parent_id": "@mat", "child_id": "@tex",
                          "container_field": "baseTexture"}),
    ],
)

SCRIPTED = [CONTROL_CLEAN, TEXTURED_MATERIAL, USE_BEFORE_DEF, INTERPOLATOR_PARITY]


@dataclass
class LivePrompt:
    name: str
    prompt: str
    # substrings whose presence in the final scene XML indicates the intended
    # result was built (a soft correctness proxy, not a full check).
    expect_xml: list = field(default_factory=list)


LIVE = [
    LivePrompt(
        "red-box-blue-sphere",
        "Build an X3D scene with a red box and a blue sphere side by side, "
        "lit and framed by a viewpoint so both are clearly visible. Validate "
        "semantically and render before you finish.",
        expect_xml=["Box", "Sphere", "Viewpoint"],
    ),
    LivePrompt(
        "textured-pbr-floor",
        "Build an X3D 4.0 scene with a flat floor whose PhysicalMaterial carries "
        "an image texture as its base colour. Make sure the texture actually "
        "shows. Validate semantically and render before you finish.",
        expect_xml=["PhysicalMaterial", "ImageTexture", "baseTexture"],
    ),
]
