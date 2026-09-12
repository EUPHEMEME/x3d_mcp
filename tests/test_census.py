#!/usr/bin/env python3
# test_census.py v1.1 2026-08-31 — census extended for the standards-native UI
# (gait buttons + ModeSwitch/LayerCycle Scripts, viewpoint Anchors, LayerStack
# Switch, set dressing) and for the head order + bone-framing manifest fields.
"""Census the shipped Anatomy Explorer scene.

The counting idiom is lifted from generate_anatomy_explorer.py main():

    n = lambda t, s=scene: len(re.findall(r"<" + t + r"[ />]", s))

These are the measured counts of the certified 2026-08 build. If a count moves,
a build stage regressed (or the skeleton genuinely changed — then re-certify
and update here, deliberately).

Runs under pytest, or standalone:  python tests/test_census.py
"""
from __future__ import annotations

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENE = os.path.join(REPO, "anatomy_explorer.x3d")

EXPECTED = {
    "HAnimHumanoid": 1,
    "HAnimJoint": 150,
    "HAnimSegment": 251,
    "TouchSensor": 261,          # 256 bones + BtnWalk/Run/Jump/Stand/Layers
    "OrientationInterpolator": 438,
    "Viewpoint": 6,
    "TimeSensor": 3,
    "Anchor": 6,                 # one per authored Viewpoint (url='#VP_*')
    "Switch": 1,                 # LayerStack — the anatomical-layers socket
    "Group": 1,                  # Layer_bones inside it
    "Script": 2,                 # ModeSwitch + LayerCycle
    "ROUTE": 888,                # 879 gait/bone + 9 UI (buttons, timers, layers)
    "Text": 13,                  # 5 button + 6 anchor labels, title, credits
    "ImageTexture": 1,           # title poster, embedded as a data: URI
}

UI_DEFS = ("BtnWalk", "BtnRun", "BtnJump", "BtnStand", "BtnLayers",
           "ModeSwitch", "LayerCycle", "LayerStack", "Layer_bones")


def _scene() -> str:
    return open(SCENE, encoding="utf-8").read()


def test_node_census():
    scene = _scene()
    n = lambda t, s=scene: len(re.findall(r"<" + t + r"[ />]", s))
    got = {tag: n(tag) for tag in EXPECTED}
    assert got == EXPECTED, f"node census drifted: {got} != {EXPECTED}"


def test_addressable_bone_defs():
    """Every bone carries the naming triple's sensor + material DEFs."""
    scene = _scene()
    ts = len(re.findall(r"<TouchSensor\b[^>]*DEF=[\"']TS_", scene))
    mat = len(re.findall(r"<PhysicalMaterial\b[^>]*DEF=[\"']MAT_", scene))
    assert ts == 256, f"expected 256 DEF TS_* TouchSensors, got {ts}"
    assert mat == 256, f"expected 256 DEF MAT_* PhysicalMaterials, got {mat}"


def test_hanim_component_declared():
    """Bug 5: without <component name='HAnim'/> the whole humanoid is silently
    discarded on load while the XSD keeps reporting valid:true."""
    scene = _scene()
    assert re.search(r"<component\s+name=[\"']HAnim[\"']", scene), \
        "missing <component name='HAnim'> declaration"


def test_walks_in_place():
    """anchor(): no gait cycle may drive hanim_humanoid_root.set_translation —
    that ROUTE marches the figure off the stage. Attribute-order-agnostic."""
    scene = _scene()
    kept = [m for m in re.findall(r"<ROUTE\b[^>]*/>", scene)
            if "toField='set_translation'" in m.replace('"', "'")
            and "toNode='hanim_humanoid_root'" in m.replace('"', "'")]
    assert kept == [], f"root-translation ROUTEs survived: {kept}"


def test_ui_defs_present():
    """The in-scene UI contract the HTML host page drives."""
    scene = _scene()
    missing = [d for d in UI_DEFS
               if not re.search(r"DEF=[\"']" + d + r"[\"']", scene)]
    assert missing == [], f"missing UI DEFs: {missing}"


def test_head_order_component_before_meta():
    """XSD: <head> content is the sequence (component*, unit*, meta*). The
    v1.0 generator spliced meta first, which was schema-invalid."""
    head = _scene().split("</head>")[0]
    assert "<component" in head and "<meta" in head
    assert head.rfind("<component") < head.find("<meta"), \
        "head order regressed: <meta> precedes <component>"


def test_offline_texture():
    """Set-dressing textures must be data: URIs — no file to 404 offline."""
    scene = _scene()
    texs = re.findall(r"<ImageTexture\b[^>]*url='\"([^\"]{0,24})", scene)
    assert texs and all(u.startswith("data:image/") for u in texs), \
        f"non-embedded texture urls: {texs}"


def test_bone_manifest_framing():
    """flatten_anatomy.py must emit center + radius per bone (camera framing)."""
    import json
    m = json.load(open(os.path.join(REPO, "build_anatomy", "bone_manifest.json")))
    bones = m["bones"]
    assert len(bones) == 256, f"expected 256 manifest bones, got {len(bones)}"
    bad = [b["name"] for b in bones
           if len(b.get("center", [])) != 3 or not b.get("radius", 0) > 0]
    assert bad == [], f"bones without valid center/radius: {bad}"


def main() -> None:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok {name}")
    print("census PASS")


if __name__ == "__main__":
    main()
