#!/usr/bin/env python3
"""
Science-classroom scene with a real anatomical skeleton (19 NIST Visible Human
bone models from the Web3D HumanoidAnimation/Medical archive) on a rolling
display stand -- alive: a raised waving arm, a turning head, and a talking jaw.

Canonical Web3D pipeline:
  * generation : the official x3d.py package (PhysicalMaterial PBR surfaces,
                 EnvironmentLight image-based ambient, UnlitMaterial textured
                 displays, animated pivot groups regrouping the rigid bone
                 Inlines around measured joint centers)
  * authoring  : classroom_skeleton.x3d  (X3D 4.0 XML)
  * web        : classroom_skeleton.html via the official X3dToX3dom.xslt
                 (Saxon); MCP-renderer fallback classroom_skeleton_x3dom.html

Textures (assets/textures/*.png) are FLUX-generated; the generator falls back
to plain colors when absent.
"""
import os
import re
import subprocess

from x3d import x3d as X

# ------------------------------------------------------------------ assets
BONES = [
    "BonesHead", "BonesMandible", "BonesTeethTop", "BonesTeethBottom",
    "BonesSpine", "BonesChest", "BonesGirdle",
    "BonesLeftHumerus", "BonesLeftRadiusUlna", "BonesLeftHand",
    "BonesRightHumerus", "BonesRightRadiusUlna", "BonesRightHand",
    "BonesLeftFemur", "BonesLeftTibiaFibula", "BonesLeftFoot",
    "BonesRightFemur", "BonesRightTibiaFibula", "BonesRightFoot",
]
HANG = 0.12
SKEL_X, SKEL_Z = -1.2, -1.6

TEXTURE_DIR = "assets/textures"
TEXTURES = {
    "blackboard": ("chalkboard_clean.png", [0.10, 0.16, 0.12]),  # clean board; text via Text nodes
    "poster_skeleton": ("poster_skeleton.png", [0.85, 0.80, 0.70]),
    "poster_anatomy": ("poster_anatomy.png", [0.75, 0.80, 0.85]),
}
# room-surface textures, rendered as lit PBR (baseTexture); tiled
ROOM_TEX = {"floor_wood.png", "wall_plaster.png", "ceiling_tile.png"}
CHALK = [0.92, 0.94, 0.86]   # chalk white

# ------------------------------------------------------------------ materials
# (color, metallic, roughness)
WOOD = ([0.55, 0.38, 0.22], 0, 0.55)
WOOD_DARK = ([0.40, 0.27, 0.15], 0, 0.6)
WALL = ([0.82, 0.84, 0.78], 0, 0.95)
METAL = ([0.62, 0.64, 0.67], 0.9, 0.28)
SEAT = ([0.20, 0.35, 0.55], 0, 0.5)

def pbr(spec):
    color, metallic, roughness = spec
    return X.Appearance(material=X.PhysicalMaterial(
        baseColor=color, metallic=metallic, roughness=roughness))

def tex_appearance(name):
    """Display surfaces use UnlitMaterial: legible from any angle and immune to
    the X3DOM IBL-vs-textured-PBR quirk; the right look for a chalkboard."""
    fn, fallback = TEXTURES[name]
    path = os.path.join(TEXTURE_DIR, fn)
    if os.path.exists(path):
        return X.Appearance(material=X.UnlitMaterial(
            emissiveColor=[1, 1, 1],
            emissiveTexture=X.ImageTexture(url=[path])))
    return X.Appearance(material=X.UnlitMaterial(emissiveColor=fallback))

def box(t, size, spec, rot=None):
    tr = X.Transform(translation=t, children=[
        X.Shape(appearance=pbr(spec), geometry=X.Box(size=size))])
    if rot:
        tr.rotation = rot
    return tr

def cyl(t, h, r, spec, rot=None):
    tr = X.Transform(translation=t, children=[
        X.Shape(appearance=pbr(spec), geometry=X.Cylinder(height=h, radius=r))])
    if rot:
        tr.rotation = rot
    return tr

def textured_panel(t, size, name, rot=None):
    tr = X.Transform(translation=t, children=[
        X.Shape(appearance=tex_appearance(name), geometry=X.Box(size=size))])
    if rot:
        tr.rotation = rot
    return tr

def tex_pbr(fn, tile=1.0):
    """Tiled textured surface for floor/walls/ceiling. Castle only applies
    textures via UnlitMaterial.emissiveTexture (not classic Material.texture nor
    PhysicalMaterial.baseTexture), so use that. Unlit (flat) but the texture
    shows reliably in both Castle and X_ITE. Dimmed so it reads as a surface."""
    path = os.path.join(TEXTURE_DIR, fn)
    if not os.path.exists(path):
        return X.Appearance(material=X.UnlitMaterial(emissiveColor=[0.7,0.7,0.7]))
    app = X.Appearance(material=X.UnlitMaterial(
        emissiveColor=[0.78,0.78,0.78], emissiveTexture=X.ImageTexture(url=[path])))
    if tile != 1.0:
        app.textureTransform = X.TextureTransform(scale=[tile, tile])
    return app

def box_tex(t, size, fn, tile=1.0, rot=None):
    tr = X.Transform(translation=t, children=[
        X.Shape(appearance=tex_pbr(fn, tile), geometry=X.Box(size=size))])
    if rot:
        tr.rotation = rot
    return tr

def chalk_text(s, t, size=0.22):
    """Crisp chalk-white text via a real font (X3D Text), unlit."""
    return X.Transform(translation=t, children=[X.Shape(
        appearance=X.Appearance(material=X.UnlitMaterial(emissiveColor=CHALK)),
        geometry=X.Text(string=[s], fontStyle=X.FontStyle(
            justify=["MIDDLE","MIDDLE"], size=size, family=["SANS"])))])

# ------------------------------------------------------------------ skeleton
# The hanging figure is the canonical AllBonesLOA5 bone-mesh humanoid, embedded
# (not Inlined) so its hanim_<joint> DEFs are in scope for the wave/head/jaw
# ROUTEs. A placeholder Group marks where the fragment is spliced in.
HUMANOID_FRAGMENT = open("assets/loa5/loa5_humanoid.x3dfrag").read()
# Canonical LOA5 locomotion cycles (each = a TimeSensor + 147 interpolators +
# routes targeting hanim_<joint>), extracted from
# AllBonesLOA5SkeletonsInlineAnimation.x3d. Timers default enabled='false' so
# the figure starts at rest; chalkboard buttons enable one mode at a time.
WALK_FRAGMENT = open("assets/loa5/walk_animation.x3dfrag").read()
RUN_FRAGMENT  = open("assets/loa5/run_animation.x3dfrag").read()
JUMP_FRAGMENT = open("assets/loa5/jump_animation.x3dfrag").read()

def buttons_and_script():
    """Chalk-styled chalkboard buttons (blend into the board: dark-green fill +
    chalk-white drawn outline + chalk label) wired to a Script that enables
    exactly one locomotion TimeSensor at a time (Stand disables all). Each button
    is a TouchSensor with a solid fill panel as a generous click target."""
    btns = ["Walk", "Run", "Jump", "Stand"]
    CHALK = "0.92 0.94 0.86"      # chalk white, matches the board's writing
    FILL = "0.08 0.13 0.10"       # chalkboard green (blends in)
    hw, hh = 0.31, 0.15
    out = []
    x0, y, z = -0.55, 2.55, -3.40   # row on the wall ABOVE the blackboard
    for i, label in enumerate(btns):
        bx = x0 + i * 0.7
        out.append(f"""    <Transform translation='{bx} {y} {z}'>
      <TouchSensor DEF='Btn{label}'/>
      <Shape><Appearance><Material diffuseColor='{FILL}' emissiveColor='{FILL}'/></Appearance>
        <Box size='{2*hw} {2*hh} 0.012'/></Shape>
      <Shape><Appearance><Material emissiveColor='{CHALK}'/><LineProperties linewidthScaleFactor='2'/></Appearance>
        <IndexedLineSet coordIndex='0 1 2 3 0 -1'>
          <Coordinate point='{-hw} {-hh} 0.01  {hw} {-hh} 0.01  {hw} {hh} 0.01  {-hw} {hh} 0.01'/>
        </IndexedLineSet></Shape>
      <Transform translation='0 0 0.02'><Shape>
        <Appearance><Material diffuseColor='{CHALK}' emissiveColor='{CHALK}'/></Appearance>
        <Text string='"{label}"'><FontStyle justify='"MIDDLE" "MIDDLE"' size='0.15'/></Text>
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
    </Script>"""
    routes = """
    <ROUTE fromNode='BtnWalk'  fromField='touchTime' toNode='ModeSwitch' toField='walk'/>
    <ROUTE fromNode='BtnRun'   fromField='touchTime' toNode='ModeSwitch' toField='run'/>
    <ROUTE fromNode='BtnJump'  fromField='touchTime' toNode='ModeSwitch' toField='jump'/>
    <ROUTE fromNode='BtnStand' fromField='touchTime' toNode='ModeSwitch' toField='stand'/>
    <ROUTE fromNode='ModeSwitch' fromField='walkOn' toNode='WalkTimer' toField='enabled'/>
    <ROUTE fromNode='ModeSwitch' fromField='runOn'  toNode='RunTimer'  toField='enabled'/>
    <ROUTE fromNode='ModeSwitch' fromField='jumpOn' toNode='JumpTimer' toField='enabled'/>"""
    return "\n".join(out) + "\n" + script + routes

def skeleton():
    base = [cyl([0, 0.03, 0], 0.06, 0.34, METAL)]
    for dx, dz in ((1,0),(-1,0),(0,1),(0,-1),(0.7,0.7)):
        base.append(X.Transform(translation=[0.28*dx, 0.025, 0.28*dz], children=[
            X.Shape(appearance=pbr(METAL), geometry=X.Sphere(radius=0.035))]))
    pole = [cyl([0, 1.05, -0.30], 2.00, 0.022, METAL),
            cyl([0, 2.04, -0.15], 0.32, 0.015, METAL, rot=[1,0,0,1.5708]),
            cyl([0, 1.965, 0.0], 0.12, 0.008, METAL)]
    bones_group = X.Transform(translation=[0, HANG, 0],
                              children=[X.Group(DEF="HumanoidSlot")])
    return X.Transform(DEF="SkeletonStand", translation=[SKEL_X, 0, SKEL_Z],
                       children=base + pole + [bones_group])

# ------------------------------------------------------------------ classroom
def classroom():
    # textured shell. In X3D, solid geometry already collides with the avatar in
    # WALK mode by default, so the viewer can't pass through these walls/floor.
    s = [box_tex([0,-0.05,0], [8,0.1,7], "floor_wood.png", tile=4),
         box_tex([0,3.05,0], [8,0.1,7], "ceiling_tile.png", tile=4),
         box_tex([0,1.5,-3.5], [8,3,0.1], "wall_plaster.png", tile=3),
         box_tex([-4.0,1.5,0], [0.1,3,7], "wall_plaster.png", tile=3),
         box_tex([4.0,1.5,0], [0.1,3,7], "wall_plaster.png", tile=3),
         textured_panel([0.8,1.5,-3.44], [3.6,1.3,0.04], "blackboard"),
         box([0.8,0.82,-3.41], [3.6,0.05,0.10], WOOD),               # chalk tray
         chalk_text("The Human Skeleton", [0.8,1.78,-3.41], 0.26),
         chalk_text("206 Bones", [0.8,1.40,-3.41], 0.30),
         textured_panel([-3.94,1.7,-1.0], [0.9,1.2,0.02], "poster_skeleton", rot=[0,1,0,1.5708]),
         textured_panel([3.94,1.7,-0.5], [0.9,1.2,0.02], "poster_anatomy", rot=[0,1,0,-1.5708]),
         box([1.3,0.38,-2.2], [1.6,0.76,0.7], WOOD)]
    for rz in (0.6, 2.0):
        for cx in (-2.2, 0.0, 2.2):
            s += [box([cx,0.36,rz], [0.6,0.04,0.45], WOOD),
                  box([cx,0.18,rz], [0.05,0.36,0.05], METAL),
                  box([cx,0.23,rz+0.45], [0.4,0.04,0.38], SEAT),
                  box([cx,0.45,rz+0.62], [0.4,0.45,0.04], SEAT)]
    return s

# ------------------------------------------------------------------ animation
def animation():
    # Arm stays at natural rest (no waving). Subtle life: slow head turn + a
    # gently talking jaw. (Walk/run/jump cycles to be added next.)
    nodes = [
        X.TimeSensor(DEF="JawClock", cycleInterval=0.42, loop=True),
        X.TimeSensor(DEF="HeadClock", cycleInterval=7.0, loop=True),
        X.OrientationInterpolator(DEF="JawTalk", key=[0,0.5,1],
            keyValue=[[1,0,0,0],[1,0,0,0.32],[1,0,0,0]]),
        X.OrientationInterpolator(DEF="HeadTurn", key=[0,0.25,0.5,0.75,1],
            keyValue=[[0,1,0,0],[0,1,0,0.30],[0,1,0,0],[0,1,0,-0.30],[0,1,0,0]]),
    ]
    R = X.ROUTE
    routes = [
        R(fromNode="JawClock", fromField="fraction_changed", toNode="JawTalk", toField="set_fraction"),
        R(fromNode="HeadClock", fromField="fraction_changed", toNode="HeadTurn", toField="set_fraction"),
        R(fromNode="JawTalk", fromField="value_changed", toNode="hanim_temporomandibular", toField="set_rotation"),
        R(fromNode="HeadTurn", fromField="value_changed", toNode="hanim_skullbase", toField="set_rotation"),
    ]
    return nodes + routes

# ------------------------------------------------------------------ assemble
scene = X.Scene(children=[
    X.WorldInfo(title="Science Classroom Skeleton"),
    X.Background(skyColor=[[0.85, 0.88, 0.92]]),
    X.NavigationInfo(type=["WALK","EXAMINE","ANY"], speed=1.5, avatarSize=[0.25,1.6,0.75]),
    X.Viewpoint(DEF="Entry", position=[0,1.6,3.2], description="Classroom entry"),
    X.Viewpoint(DEF="SkeletonView", position=[0.2,1.5,0.2], orientation=[0,1,0,-0.45],
                description="Meet the skeleton"),
    X.Viewpoint(DEF="SkullStudy", position=[-0.9,1.65,-0.9], orientation=[0,1,0,-0.35],
                description="Skull close-up"),
    # Direct lighting only: EnvironmentLight (image-based) leaves classic textured
    # Material surfaces black in Castle. Keep ambient low so the pale wood/plaster
    # textures don't wash out; directional shading reveals their detail.
    X.DirectionalLight(direction=[-0.3,-1,-0.4], intensity=0.85, ambientIntensity=0.18),
    X.DirectionalLight(direction=[0.5,-0.5,0.6], intensity=0.5, ambientIntensity=0.10),
    X.DirectionalLight(direction=[0.2,-0.4,-0.8], intensity=0.35, ambientIntensity=0.05),
    X.PointLight(location=[0,2.9,0], intensity=0.45, radius=10),
    *classroom(),
    skeleton(),
    # walk animation injected post-serialize (raw fragment, see below)
])

doc = X.X3D(profile="Immersive", version="4.0",
            head=X.head(children=[
                X.component(name="HAnim", level=1),  # X_ITE needs this to build HAnim nodes
                X.meta(name="title", content="classroom_skeleton.x3d"),
                X.meta(name="description",
                       content=("Science classroom with a real anatomical skeleton "
                                "(19 NIST bone models) on a rolling stand -- waving, "
                                "head-turning, talking. PBR + EnvironmentLight. Built with x3d.py.")),
                X.meta(name="generator", content="generate_classroom.py (x3d.py canonical pipeline)"),
            ]),
            Scene=scene)

xml = doc.XML()
# x3d.py drops two containerFields on output: EnvironmentLight's global, and
# x3d.py drops the texture containerField; assign per file: room surfaces are
# lit PBR (baseTexture), display panels (board/posters) are unlit (emissiveTexture).
# every texture in the scene is now an emissiveTexture (room + display panels);
# x3d.py drops the containerField, so restore it on all of them.
xml = xml.replace("<ImageTexture ", "<ImageTexture containerField='emissiveTexture' ")
# splice the canonical bone-mesh humanoid into the stand placeholder
xml = re.sub(r"<Group DEF='HumanoidSlot'\s*/>|<Group DEF='HumanoidSlot'>\s*</Group>",
             HUMANOID_FRAGMENT, xml, count=1)
# default the walk cycle to play on load (articulation visible immediately);
# Run/Jump stay off until their button is clicked.
walk_on = WALK_FRAGMENT.replace("DEF='WalkTimer' cycleInterval='2.5' loop='true' enabled='false'",
                                "DEF='WalkTimer' cycleInterval='2.5' loop='true' enabled='true'")
# Anchor the figure on its stand: drop the root TRANSLATION routes from every
# cycle so the skeleton articulates in place and never translates through the
# floor or ceiling (X3D collision governs the camera, not keyframed animation).
def _anchor(frag):
    return re.sub(r"\s*<ROUTE\b[^>]*toNode='hanim_humanoid_root'[^>]*toField='set_translation'[^>]*/>", "", frag)
_anim = "\n      ".join(_anchor(f) for f in (walk_on, RUN_FRAGMENT, JUMP_FRAGMENT))
xml = xml.replace("</Scene>", f"  {_anim}\n{buttons_and_script()}\n  </Scene>", 1)
# drop DOCTYPE so web players (X_ITE) and Saxon don't fetch the external DTD
xml = "\n".join(l for l in xml.splitlines() if not l.startswith("<!DOCTYPE"))
with open("classroom_skeleton.x3d", "w") as fh:
    fh.write(xml)
textured = [n for n,(f,_) in TEXTURES.items() if os.path.exists(os.path.join(TEXTURE_DIR,f))]
print(f"wrote classroom_skeleton.x3d ({len(xml)} bytes, canonical AllBonesLOA5 "
      f"bone-mesh humanoid; textures: {textured or 'none'})")

# ------------------------------------------------------------------ web pages
XITE_JS = "https://cdn.jsdelivr.net/npm/x_ite@latest/dist/x_ite.min.js"

def write_xite_page():
    """Primary page: X_ITE loads the real .x3d (renders PBR + the bone Inlines)."""
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Science Classroom — Living Skeleton</title>
  <script src="{XITE_JS}"></script>
  <style>
    html,body {{ margin:0; height:100%; background:#1a1a2e; }}
    x3d-canvas {{ width:100vw; height:100vh; display:block; }}
  </style>
</head>
<body>
  <x3d-canvas src="classroom_skeleton.x3d"></x3d-canvas>
</body>
</html>
"""
    with open("classroom_skeleton.html", "w") as fh:
        fh.write(page)
    print("wrote classroom_skeleton.html (X_ITE)")
    try:
        import sys; sys.path.insert(0, "src")
        from tools.render import _x3dom_page
        open("classroom_skeleton_x3dom.html", "w").write(_x3dom_page(
            xml, title="Science Classroom — Living Skeleton", width="100%", height="100vh"))
        print("wrote classroom_skeleton_x3dom.html (X3DOM fallback)")
    except Exception as e:
        print(f"skipped X3DOM fallback: {e}")

write_xite_page()
