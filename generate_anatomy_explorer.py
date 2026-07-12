#!/usr/bin/env python3
"""Compose the LOA5 Anatomy Explorer scene.

    studio spine   (authored call-by-call through the Technē proxy)
  + flat skeleton  (flatten_anatomy.py -- 257 addressable bones)
  + gait cycles    (the HAnim standard's own walk/run/jump)
  = anatomy_explorer.x3d

Run flatten_anatomy.py and build_anatomy_spine.py first.
"""
from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
BUILD = f"{REPO}/build_anatomy"
OUT = f"{REPO}/anatomy_explorer.x3d"


def anchor(frag: str) -> str:
    """Walk in place.

    The gait cycles drive hanim_humanoid_root.set_translation, which marches the
    figure off the stage and out of every viewpoint we authored. Strip that one
    ROUTE per cycle and the legs still cycle, in place.

    Order-agnostic on purpose: the repo's existing _anchor() in
    generate_classroom.py:293 requires toNode to precede toField, but the frags
    serialize toField first -- so it silently matches nothing.
    """
    def is_root_translation(m: str) -> bool:
        return ("toField='set_translation'" in m
                and "toNode='hanim_humanoid_root'" in m)

    return re.sub(r"\s*<ROUTE\b[^>]*/>",
                  lambda m: "" if is_root_translation(m.group(0)) else m.group(0),
                  frag)


def strip_timer(frag: str) -> str:
    """The spine already DEFs WalkTimer/RunTimer/JumpTimer. The frags DEF them
    again -- a duplicate DEF, which is a hard error, not a warning."""
    return re.sub(r"\s*<TimeSensor\b[^>]*/>", "", frag)


def main() -> None:
    spine = open(f"{BUILD}/studio_spine.x3d", encoding="utf-8").read()
    skeleton = open(f"{BUILD}/skeleton.x3dfrag", encoding="utf-8").read()

    gaits = []
    for cycle in ("walk", "run", "jump"):
        f = open(f"{REPO}/assets/loa5/{cycle}_animation.x3dfrag", encoding="utf-8").read()
        gaits.append(anchor(strip_timer(f)))
    anim = "\n".join(gaits)

    # Two header facts, either of which silently empties the scene:
    #
    # 1. The granular API always emits profile='Interchange', which contains
    #    neither HAnim nor TouchSensor nor the Lighting nodes we authored.
    # 2. NO profile includes HAnim -- it is a separate component, and a scene
    #    that uses HAnimHumanoid without declaring it gets its whole humanoid
    #    discarded by the browser. No error, no warning: a beautifully lit empty
    #    room. (The XSD says valid: true throughout -- profile/component
    #    conformance is simply not what schema validation checks.)
    #
    # Immersive + an explicit HAnim component is what the repo's working
    # classroom scene does, and it is the combination proven to render.
    scene = spine.replace("profile='Interchange' version='4.1'",
                          "profile='Immersive' version='4.0'")
    scene = scene.replace(
        "https://www.web3d.org/specifications/x3d-4.1.xsd",
        "https://www.web3d.org/specifications/x3d-4.0.xsd")

    head = (
        "\n  <head>\n"
        "    <component level='1' name='HAnim'/>\n"
        "    <meta content='LOA5 Anatomy Explorer' name='title'/>\n"
        "    <meta content='HAnim LOA5 skeleton, 257 individually addressable bones.' name='description'/>\n"
        "    <meta content='Bone meshes: Don Brutzman, Joe Williams, John Carlson, Damon Hernandez (Web3D Consortium).' name='reference'/>\n"
        "  </head>"
    )
    scene = scene.replace(">\n  <Scene>", f">{head}\n  <Scene>", 1)

    body = f"{skeleton}\n{anim}\n"
    scene = scene.replace("</Scene>", f"{body}</Scene>", 1)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(scene)

    n = lambda t, s=scene: len(re.findall(r"<" + t + r"[ />]", s))
    kept_translation = len(re.findall(
        r"<ROUTE[^>]*toField='set_translation'[^>]*toNode='hanim_humanoid_root'", scene))

    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1e6:.2f} MB)")
    print(f"  profile            : Interactive")
    print(f"  bones (TouchSensor): {n('TouchSensor')}")
    print(f"  joints             : {n('HAnimJoint')}")
    print(f"  viewpoints         : {n('Viewpoint')}")
    print(f"  lights             : {n('DirectionalLight')} directional + {n('EnvironmentLight')} environment")
    print(f"  gait timers        : {n('TimeSensor')}")
    print(f"  interpolators      : {n('OrientationInterpolator')}")
    print(f"  routes             : {n('ROUTE')}")
    print(f"  root-translation routes left (must be 0): {kept_translation}")


if __name__ == "__main__":
    main()
