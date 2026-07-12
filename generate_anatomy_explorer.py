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

    # The spine already comes back from the proxy with its profile restored and
    # the components its own nodes need declared. This step splices in HAnim nodes
    # the spine never had, so the document needs one more component -- and rather
    # than hand-write it (this generator used to hardcode <component name='HAnim'/>
    # and a profile bump), we run the composed document back through the same
    # function the proxy uses. The generator does not need to know that HAnim is a
    # component at all.
    #
    # This is Bug 5, and it is the reason it matters: a scene using HAnimHumanoid
    # without an explicit <component name='HAnim'/> has its whole humanoid
    # DISCARDED on load -- a beautifully lit empty room, with the XSD reporting
    # valid:true throughout. No profile below Full admits HAnim; raising the
    # profile does not help. See docs/x3dpy-bug-report.md#bug-5.
    sys.path.insert(0, f"{REPO}/techne")
    from techne.craft import reassert_profile

    scene = spine.replace("</Scene>", f"{skeleton}\n{anim}\n</Scene>", 1)

    meta = (
        "\n    <meta content='LOA5 Anatomy Explorer' name='title'/>"
        "\n    <meta content='HAnim LOA5 skeleton, 256 individually addressable parts.' name='description'/>"
        "\n    <meta content='Bone meshes: Don Brutzman, Joe Williams, John Carlson, Damon Hernandez (Web3D Consortium).' name='reference'/>"
    )
    scene = reassert_profile(scene)                    # declares HAnim, keeps the rest
    scene = scene.replace("<head>", "<head>" + meta, 1)

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
