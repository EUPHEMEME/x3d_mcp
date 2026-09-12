#!/usr/bin/env python3
# generate_anatomy_explorer.py v1.1 2026-08-31 — standards-native scene: in-scene
# gait buttons + viewpoint Anchors + LayerStack Switch socket + set dressing;
# head order fixed (component before meta, per the XSD sequence).
"""Compose the LOA5 Anatomy Explorer scene.

    studio spine   (authored call-by-call through the Technē proxy)
  + flat skeleton  (flatten_anatomy.py -- 257 addressable bones)
  + gait cycles    (the HAnim standard's own walk/run/jump)
  + in-scene UI    (gait buttons, viewpoint anchors, layer switch, set dressing)
  = anatomy_explorer.x3d

Run flatten_anatomy.py and build_anatomy_spine.py first.

v1.1:
  * HEAD ORDER — the XSD requires <head> content as (component*, unit*, meta*).
    v1.0 spliced its <meta> tags in right after "<head>", i.e. BEFORE the
    <component> declarations reassert_profile had appended there, which is
    XSD-invalid. The metas now go in just before "</head>".
  * Gait buttons ported from LOA5_HAnim_Project/generators/generate_classroom.py
    buttons_and_script(), restyled to the studio. NOT ported: that file's
    _anchor() -- it requires toNode to precede toField in the serialized ROUTE
    and silently matches nothing; this file's own order-agnostic anchor() stays.
  * Six <Anchor url='"#VP_*"'> labels, one per authored Viewpoint.
  * The skeleton now sits in <Switch DEF='LayerStack' whichChoice='0'>
    <Group DEF='Layer_bones'> -- the socket for the anatomical-layers roadmap.
    A BtnLayers button cycles whichChoice through the LayerCycle Script
    (a no-op ring of size 1 today, by design).
  * Set dressing: title text, a poster panel and a credits plaque behind the
    figure (textured_panel / chalk_text idiom from the classroom generator).
    The poster texture is embedded as a data: URI so the bare .x3d stays
    fully offline-resolvable wherever it is served from.
"""
from __future__ import annotations

import base64
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
BUILD = f"{REPO}/build_anatomy"
OUT = f"{REPO}/anatomy_explorer.x3d"

# studio palette (matches the spine's Sky background + rim/fill lights)
INK = "0.78 0.84 0.95"       # pale studio blue-white (labels, outlines)
FILL = "0.055 0.07 0.105"    # deep studio navy (panel fills)

# (DEF suffix, label) — DEF names are Btn<suffix>; the HTML agent drives these.
BUTTONS = (("Walk", "Walk"), ("Run", "Run"), ("Jump", "Jump"),
           ("Stand", "Stand"), ("Layers", "Layers"))

# (Viewpoint DEF, chip label) — all six authored viewpoints, order = top-down.
VIEWPOINTS = (("VP_Body", "Body"), ("VP_Skull", "Skull"),
              ("VP_Ribcage", "Ribs"), ("VP_Spine", "Spine"),
              ("VP_Hand", "Hand"), ("VP_Foot", "Foot"))


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


# --------------------------------------------------------------- set dressing
def data_uri(path: str) -> str:
    """Embed a texture so the bare .x3d resolves offline from anywhere."""
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def unlit(color: str) -> str:
    return f"<Appearance><UnlitMaterial emissiveColor='{color}'/></Appearance>"


def chalk_text(strings: list[str] | tuple[str, ...], t: str, size: float,
               color: str = INK) -> str:
    """Crisp unlit label text (the classroom generator's chalk_text idiom)."""
    s = " ".join(f'"{x}"' for x in strings)
    return (f"    <Transform translation='{t}'>\n"
            f"      <Shape>{unlit(color)}\n"
            f"        <Text string='{s}'>"
            f"<FontStyle justify='\"MIDDLE\" \"MIDDLE\"' size='{size}'/>"
            f"</Text></Shape>\n"
            f"    </Transform>")


def textured_panel(t: str, size: str, png: str, rot: str | None = None) -> str:
    """Unlit textured display panel (the classroom generator's textured_panel
    idiom), texture embedded as a data: URI."""
    rot_attr = f" rotation='{rot}'" if rot else ""
    return (f"    <Transform translation='{t}'{rot_attr}>\n"
            f"      <Shape><Appearance><UnlitMaterial emissiveColor='1 1 1'>"
            f"<ImageTexture containerField='emissiveTexture'"
            f" url='\"{data_uri(png)}\"'/>"
            f"</UnlitMaterial></Appearance><Box size='{size}'/></Shape>\n"
            f"    </Transform>")


def set_dressing() -> str:
    """Title + poster + credits plaque behind the figure. Positions sit behind
    the stage (z<=-1.6) so no authored viewpoint is blocked."""
    poster = f"{REPO}/assets/textures/poster_skeleton.png"
    parts = [
        chalk_text(["LOA5  ANATOMY  EXPLORER"], "0 2.35 -1.8", 0.16),
        textured_panel("-1.5 1.35 -1.6", "0.92 1.22 0.03", poster,
                       rot="0 1 0 0.28"),
        # credits plaque: dark panel + three unlit lines
        (f"    <Transform translation='1.5 1.3 -1.6' rotation='0 1 0 -0.28'>\n"
         f"      <Shape>{unlit(FILL)}<Box size='1.06 0.5 0.03'/></Shape>\n"
         f"      <Transform translation='0 0 0.02'>\n"
         f"        <Shape>{unlit(INK)}\n"
         f"          <Text string='\"Bone meshes: Web3D Consortium\""
         f" \"Brutzman - Williams - Carlson - Hernandez\""
         f" \"256 addressable parts - HAnim LOA5\"'>"
         f"<FontStyle justify='\"MIDDLE\" \"MIDDLE\"' size='0.062'"
         f" spacing='1.4'/></Text></Shape>\n"
         f"      </Transform>\n"
         f"    </Transform>"),
    ]
    return "\n".join(parts)


# ------------------------------------------------------------- in-scene UI
def buttons_and_script() -> str:
    """Studio-styled gait buttons + the ModeSwitch Script, ported from
    generate_classroom.py buttons_and_script(): each button is a TouchSensor
    with a solid fill panel as a generous click target, an outline, and a
    label. Restyled from chalkboard green/chalk to the studio navy/ink, and
    parked in a low row at the front edge of the stage. A fifth button,
    BtnLayers, cycles the LayerStack Switch through the LayerCycle Script."""
    hw, hh = 0.15, 0.055
    x0, step, y, z = -0.68, 0.34, 0.20, 0.55
    out = []
    for i, (d, label) in enumerate(BUTTONS):
        bx = x0 + i * step
        out.append(f"""    <Transform translation='{bx} {y} {z}'>
      <TouchSensor DEF='Btn{d}' description=''/>
      <Shape>{unlit(FILL)}<Box size='{2*hw} {2*hh} 0.012'/></Shape>
      <Shape><Appearance><UnlitMaterial emissiveColor='{INK}'/><LineProperties linewidthScaleFactor='2'/></Appearance>
        <IndexedLineSet coordIndex='0 1 2 3 0 -1'>
          <Coordinate point='{-hw} {-hh} 0.01  {hw} {-hh} 0.01  {hw} {hh} 0.01  {-hw} {hh} 0.01'/>
        </IndexedLineSet></Shape>
      <Transform translation='0 0 0.02'><Shape>{unlit(INK)}
        <Text string='"{label}"'><FontStyle justify='"MIDDLE" "MIDDLE"' size='0.062'/></Text>
      </Shape></Transform>
    </Transform>""")
    script = """    <Script DEF='ModeSwitch'>
      <field accessType='inputOnly' type='SFTime' name='walk'/>
      <field accessType='inputOnly' type='SFTime' name='run'/>
      <field accessType='inputOnly' type='SFTime' name='jump'/>
      <field accessType='inputOnly' type='SFTime' name='stand'/>
      <field accessType='outputOnly' type='SFBool' name='walkOn'/>
      <field accessType='outputOnly' type='SFBool' name='runOn'/>
      <field accessType='outputOnly' type='SFBool' name='jumpOn'/>
<![CDATA[ecmascript:
function walk(){ walkOn=true; runOn=false; jumpOn=false; }
function run(){ walkOn=false; runOn=true; jumpOn=false; }
function jump(){ walkOn=false; runOn=false; jumpOn=true; }
function stand(){ walkOn=false; runOn=false; jumpOn=false; }
]]>
    </Script>
    <Script DEF='LayerCycle'>
      <field accessType='inputOnly' type='SFTime' name='next'/>
      <field accessType='initializeOnly' type='SFInt32' name='layerCount' value='1'/>
      <field accessType='inputOutput' type='SFInt32' name='current' value='0'/>
      <field accessType='outputOnly' type='SFInt32' name='choice'/>
<![CDATA[ecmascript:
function next(){ current = (current + 1) % layerCount; choice = current; }
]]>
    </Script>"""
    routes = """
    <ROUTE fromNode='BtnWalk'  fromField='touchTime' toNode='ModeSwitch' toField='walk'/>
    <ROUTE fromNode='BtnRun'   fromField='touchTime' toNode='ModeSwitch' toField='run'/>
    <ROUTE fromNode='BtnJump'  fromField='touchTime' toNode='ModeSwitch' toField='jump'/>
    <ROUTE fromNode='BtnStand' fromField='touchTime' toNode='ModeSwitch' toField='stand'/>
    <ROUTE fromNode='ModeSwitch' fromField='walkOn' toNode='WalkTimer' toField='enabled'/>
    <ROUTE fromNode='ModeSwitch' fromField='runOn'  toNode='RunTimer'  toField='enabled'/>
    <ROUTE fromNode='ModeSwitch' fromField='jumpOn' toNode='JumpTimer' toField='enabled'/>
    <ROUTE fromNode='BtnLayers' fromField='touchTime' toNode='LayerCycle' toField='next'/>
    <ROUTE fromNode='LayerCycle' fromField='choice' toNode='LayerStack' toField='whichChoice'/>"""
    return "\n".join(out) + "\n" + script + routes


def viewpoint_anchors() -> str:
    """One <Anchor url='"#VP_*"'> chip per authored Viewpoint: standards-native
    view navigation with zero JavaScript. A slim column left of the figure."""
    out = []
    for i, (vp, label) in enumerate(VIEWPOINTS):
        y = 1.60 - i * 0.15
        out.append(f"""    <Transform translation='-1.15 {y:.2f} 0'>
      <Anchor url='"#{vp}"' description='{label} viewpoint'>
        <Shape>{unlit(FILL)}<Box size='0.36 0.105 0.012'/></Shape>
        <Transform translation='0 0 0.02'><Shape>{unlit(INK)}
          <Text string='"{label}"'><FontStyle justify='"MIDDLE" "MIDDLE"' size='0.055'/></Text>
        </Shape></Transform>
      </Anchor>
    </Transform>""")
    return "\n".join(out)


def layer_stack(skeleton: str) -> str:
    """The layer socket. One layer today (bones); the Switch + LayerCycle pair
    is the standards-native mount point for the anatomical-layers roadmap
    (muscles, organs, skin become Layer_* siblings and layerCount goes up)."""
    return (f"<Switch DEF='LayerStack' whichChoice='0'>\n"
            f"<Group DEF='Layer_bones'>\n{skeleton}\n</Group>\n</Switch>")


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

    body = "\n".join([layer_stack(skeleton), anim, buttons_and_script(),
                      viewpoint_anchors(), set_dressing()])
    scene = spine.replace("</Scene>", f"{body}\n</Scene>", 1)

    meta = (
        "\n    <meta content='LOA5 Anatomy Explorer' name='title'/>"
        "\n    <meta content='HAnim LOA5 skeleton, 256 individually addressable parts.' name='description'/>"
        "\n    <meta content='Bone meshes: Don Brutzman, Joe Williams, John Carlson, Damon Hernandez (Web3D Consortium).' name='reference'/>"
    )
    # reassert_profile appends <component> declarations directly after <head>.
    # The metas must land AFTER them: the XSD defines head as the sequence
    # (component*, unit*, meta*), so meta-before-component is schema-invalid
    # (the v1.0 bug -- it spliced meta right after "<head>").
    scene = reassert_profile(scene)                    # declares HAnim, keeps the rest
    scene = scene.replace("</head>", meta + "\n  </head>", 1)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(scene)

    n = lambda t, s=scene: len(re.findall(r"<" + t + r"[ />]", s))
    kept_translation = len(re.findall(
        r"<ROUTE[^>]*toField='set_translation'[^>]*toNode='hanim_humanoid_root'", scene))

    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1e6:.2f} MB)")
    print(f"  profile            : Interactive")
    print(f"  bones (TouchSensor): {n('TouchSensor')}  (256 bones + {len(BUTTONS)} buttons)")
    print(f"  joints             : {n('HAnimJoint')}")
    print(f"  viewpoints         : {n('Viewpoint')}  anchors: {n('Anchor')}")
    print(f"  layer socket       : Switch {n('Switch')} / Group {n('Group')} (LayerStack/Layer_bones)")
    print(f"  scripts            : {n('Script')} (ModeSwitch, LayerCycle)")
    print(f"  lights             : {n('DirectionalLight')} directional + {n('EnvironmentLight')} environment")
    print(f"  gait timers        : {n('TimeSensor')}")
    print(f"  interpolators      : {n('OrientationInterpolator')}")
    print(f"  routes             : {n('ROUTE')}")
    print(f"  root-translation routes left (must be 0): {kept_translation}")
    head = scene.split("</head>")[0]
    order_ok = head.rfind("<component") < head.find("<meta")
    print(f"  head order (component before meta): {'OK' if order_ok else 'BROKEN'}")


if __name__ == "__main__":
    main()
