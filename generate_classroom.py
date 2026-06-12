#!/usr/bin/env python3
"""
Generate a science-classroom scene with a real anatomical skeleton hanging
from a classic rolling display stand, assembled from the 19 regional bone
models in the Web3D HumanoidAnimation/Medical archive (NIST Visible Human
derived). The bone files share one coordinate frame (feet y=0, centered,
height 60.89 units), so plain Inlines assemble the skeleton; one Transform
scales it to 1.75 m.

Optional FLUX-generated textures (assets/textures/*.png) are applied to the
blackboard and wall posters when present; otherwise plain materials are used.

Output: classroom_skeleton.x3d
"""
import os

BONES = [
    "BonesHead", "BonesMandible", "BonesTeethTop", "BonesTeethBottom",
    "BonesSpine", "BonesChest", "BonesGirdle",
    "BonesLeftHumerus", "BonesLeftRadiusUlna", "BonesLeftHand",
    "BonesRightHumerus", "BonesRightRadiusUlna", "BonesRightHand",
    "BonesLeftFemur", "BonesLeftTibiaFibula", "BonesLeftFoot",
    "BonesRightFemur", "BonesRightTibiaFibula", "BonesRightFoot",
]

SCALE = 1.0              # each bone file already self-scales by 0.029 -> ~1.77 m
HANG = 0.12              # feet clearance above floor (m)
SKEL_X, SKEL_Z = -1.2, -1.6   # stand position (front-left, near blackboard)

TEXTURE_DIR = "assets/textures"
TEXTURES = {              # logical name -> (file, fallback diffuse color)
    "blackboard": ("blackboard.png", "0.10 0.16 0.12"),
    "poster_skeleton": ("poster_skeleton.png", "0.85 0.80 0.70"),
    "poster_anatomy": ("poster_anatomy.png", "0.75 0.80 0.85"),
}

def tex_appearance(name, roughness="0.85"):
    """Display surfaces (board/posters) use UnlitMaterial so they read clearly
    and are unaffected by lighting. (Castle's global EnvironmentLight/IBL
    suppresses textured PhysicalMaterial surfaces, so unlit is also required
    for the texture to show -- and is the right look for a chalkboard anyway.)"""
    fn, fallback = TEXTURES[name]
    path = os.path.join(TEXTURE_DIR, fn)
    if os.path.exists(path):
        return ('<Appearance><UnlitMaterial emissiveColor="1 1 1">'
                f'<ImageTexture url=\'"{path}"\' containerField="emissiveTexture"/>'
                '</UnlitMaterial></Appearance>')
    return f'<Appearance><UnlitMaterial emissiveColor="{fallback}"/></Appearance>'

def mat(color, metallic="0", roughness="0.6"):
    return (f'<Appearance><PhysicalMaterial baseColor="{color}" '
            f'metallic="{metallic}" roughness="{roughness}"/></Appearance>')

def box(x, y, z, sx, sy, sz, appearance, rot=""):
    r = f' rotation="{rot}"' if rot else ""
    return (f'<Transform translation="{x} {y} {z}"{r}>'
            f'<Shape>{appearance}<Box size="{sx} {sy} {sz}"/></Shape></Transform>')

def cyl(x, y, z, h, r, appearance, rot=""):
    rr = f' rotation="{rot}"' if rot else ""
    return (f'<Transform translation="{x} {y} {z}"{rr}>'
            f'<Shape>{appearance}<Cylinder height="{h}" radius="{r}"/></Shape></Transform>')

WOOD = mat("0.55 0.38 0.22", roughness="0.55")
WOOD_DARK = mat("0.40 0.27 0.15", roughness="0.6")
WALL = mat("0.82 0.84 0.78", roughness="0.95")
METAL = mat("0.62 0.64 0.67", metallic="0.9", roughness="0.28")
SEAT = mat("0.20 0.35 0.55", roughness="0.5")

# ---------------------------------------------------------------- skeleton
def skeleton():
    inlines = "\n        ".join(
        f'<Inline DEF="{b}" url=\'"assets/medical/{b}.x3d"\'/>' for b in BONES)
    return f'''
    <!-- assembled anatomical skeleton (19 regional NIST bone models) -->
    <Transform DEF="SkeletonStand" translation="{SKEL_X} 0 {SKEL_Z}">
      <!-- rolling base -->
      {cyl(0, 0.03, 0, 0.06, 0.34, METAL)}
      {"".join(f'<Transform translation="{0.28*dx} 0.025 {0.28*dz}"><Shape>{METAL}<Sphere radius="0.035"/></Shape></Transform>' for dx, dz in ((1,0),(-1,0),(0,1),(0,-1),(0.7,0.7)))}
      <!-- pole behind skeleton, overhead arm, hook -->
      {cyl(0, 1.05, -0.30, 2.00, 0.022, METAL)}
      {cyl(0, 2.04, -0.15, 0.32, 0.015, METAL, rot="1 0 0 1.5708")}
      {cyl(0, 1.965, 0.0, 0.12, 0.008, METAL)}
      <!-- the bones: shared frame, feet y=0, 60.89 units tall -->
      <Transform translation="0 {HANG} 0" scale="{SCALE} {SCALE} {SCALE}">
        {inlines}
      </Transform>
    </Transform>'''

# ---------------------------------------------------------------- classroom
def classroom():
    s = []
    s.append(box(0, -0.05, 0, 8, 0.1, 7, WOOD_DARK))            # floor
    s.append(box(0, 3.05, 0, 8, 0.1, 7, WALL))                  # ceiling
    s.append(box(0, 1.5, -3.5, 8, 3, 0.1, WALL))                # back wall
    s.append(box(-4.0, 1.5, 0, 0.1, 3, 7, WALL))                # left wall
    s.append(box(4.0, 1.5, 0, 0.1, 3, 7, WALL))                 # right wall
    # blackboard + chalk tray on back wall
    s.append(f'<Transform translation="0.8 1.5 -3.44"><Shape>{tex_appearance("blackboard")}<Box size="3.6 1.3 0.04"/></Shape></Transform>')
    s.append(box(0.8, 0.82, -3.41, 3.6, 0.05, 0.10, WOOD))
    # posters on side walls
    s.append(f'<Transform translation="-3.94 1.7 -1.0" rotation="0 1 0 1.5708"><Shape>{tex_appearance("poster_skeleton")}<Box size="0.9 1.2 0.02"/></Shape></Transform>')
    s.append(f'<Transform translation="3.94 1.7 -0.5" rotation="0 1 0 -1.5708"><Shape>{tex_appearance("poster_anatomy")}<Box size="0.9 1.2 0.02"/></Shape></Transform>')
    # teacher desk
    s.append(box(1.3, 0.38, -2.2, 1.6, 0.76, 0.7, WOOD))
    # student desks: 2 rows x 3
    for rz in (0.6, 2.0):
        for cx in (-2.2, 0.0, 2.2):
            s.append(box(cx, 0.36, rz, 0.6, 0.04, 0.45, WOOD))            # desktop
            s.append(box(cx, 0.18, rz, 0.05, 0.36, 0.05, METAL))          # leg
            s.append(box(cx, 0.23, rz + 0.45, 0.4, 0.04, 0.38, SEAT))     # seat
            s.append(box(cx, 0.45, rz + 0.62, 0.4, 0.45, 0.04, SEAT))     # backrest
    return "\n    ".join(s)

doc = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance"
     xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">
  <head>
    <meta name="title" content="classroom_skeleton.x3d"/>
    <meta name="description" content="Science classroom with a real anatomical skeleton (19 NIST Visible Human bone models from the Web3D HumanoidAnimation/Medical archive) hanging on a rolling display stand."/>
    <meta name="generator" content="generate_classroom.py (x3d_mcp)"/>
  </head>
  <Scene>
    <WorldInfo title="Science Classroom Skeleton"/>
    <Background skyColor="0.85 0.88 0.92"/>
    <NavigationInfo type='"WALK" "EXAMINE" "ANY"' speed="1.5" avatarSize="0.25 1.6 0.75"/>

    <Viewpoint DEF="Entry" position="0 1.6 3.2" description="Classroom entry"/>
    <Viewpoint DEF="SkeletonView" position="0.2 1.5 0.2" orientation="0 1 0 -0.45"
               description="Meet the skeleton"/>
    <Viewpoint DEF="SkullStudy" position="-0.9 1.65 -0.9" orientation="0 1 0 -0.35"
               description="Skull close-up"/>

    <!-- image-based ambient (PBR): warm-tinted global environment light -->
    <EnvironmentLight global="true" color="0.95 0.96 1.0" intensity="0.55"
                      ambientIntensity="0.35"
                      diffuseCoefficients="0.9 0.92 1.0  0.05 0.05 0.06  0 0 0  0 0 0
                                           0 0 0  0 0 0  0 0 0  0 0 0  0 0 0"/>
    <DirectionalLight direction="-0.3 -1 -0.4" intensity="0.8" ambientIntensity="0.15"/>
    <DirectionalLight direction="0.5 -0.6 0.5" intensity="0.3"/>
    <PointLight location="0 2.9 0" intensity="0.4" radius="8"/>

    {classroom()}
{skeleton()}
  </Scene>
</X3D>
'''

with open("classroom_skeleton.x3d", "w") as fh:
    fh.write(doc)

textured = [n for n, (f, _) in TEXTURES.items()
            if os.path.exists(os.path.join(TEXTURE_DIR, f))]
print(f"wrote classroom_skeleton.x3d ({len(doc)} bytes, {len(BONES)} bone inlines, "
      f"textures: {textured or 'none (plain materials)'})")
