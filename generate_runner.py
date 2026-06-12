#!/usr/bin/env python3
"""
Generate a standards-conformant HAnim 2.0 (LOA-1) running humanoid that travels
through a slalom course with turns and obstacles.

Skeleton: real HAnim nodes (HAnimHumanoid / HAnimJoint / HAnimSegment) using the
official HAnim 2.0 LOA-1 default joint centers taken from the Web3D archive file
HumanoidAnimation/Templates/DiamondManLOA1.x3d.

Because HAnimJoint behaves like a Transform whose only non-default field at rest
is `center`, the rest-pose local frame of every joint equals the global humanoid
frame. That means all segment geometry can be authored in *absolute* humanoid
coordinates and still articulate correctly when an ancestor joint rotates.

Output: running_human.x3d  (X3D 4.0 XML, validates against x3d-4.0/4.1 schema)
The X3DOM HTML viewer page is produced separately via the x3d MCP x3dom_page tool.
"""
import math

# ---------------------------------------------------------------------------
# 1. HAnim 2.0 LOA-1 standard joint centers (absolute, metres; 1.7m figure)
#    name -> (center, parent)   parent=None for root
# ---------------------------------------------------------------------------
J = {
    "humanoid_root":           ((0.0,     0.824,  0.0277),  None),
    "sacroiliac":              ((0.0,     0.9149, 0.0016),  "humanoid_root"),
    # left leg
    "l_hip":                   ((0.0961,  0.9124, -0.0001), "sacroiliac"),
    "l_knee":                  ((0.104,   0.4867, 0.0308),  "l_hip"),
    "l_talocrural":            ((0.1101,  0.0656, -0.0736), "l_knee"),
    "l_metatarsophalangeal_2": ((0.1086,  0.0001, 0.0368),  "l_talocrural"),
    # right leg
    "r_hip":                   ((-0.095,  0.9171, 0.0029),  "sacroiliac"),
    "r_knee":                  ((-0.0867, 0.4913, 0.0318),  "r_hip"),
    "r_talocrural":            ((-0.0801, 0.0712, -0.0766), "r_knee"),
    "r_metatarsophalangeal_2": ((-0.0801, 0.0,    0.0368),  "r_talocrural"),
    # spine -> neck -> head
    "vl5":                     ((0.0028,  1.0568, -0.0776), "sacroiliac"),
    "vl1":                     ((-0.004,  1.07,   -0.0275), "vl5"),
    "vc4":                     ((0.0,     1.43,   -0.0458), "vl1"),
    "skullbase":               ((0.0044,  1.6209, 0.0236),  "vc4"),
    # left arm
    "l_shoulder":              ((0.2029,  1.4376, -0.0387), "vc4"),
    "l_elbow":                 ((0.2014,  1.1357, -0.0682), "l_shoulder"),
    "l_radiocarpal":           ((0.1984,  0.8663, -0.0583), "l_elbow"),
    # right arm
    "r_shoulder":              ((-0.1907, 1.4407, -0.0325), "vc4"),
    "r_elbow":                 ((-0.1949, 1.1388, -0.062),  "r_shoulder"),
    "r_radiocarpal":           ((-0.1959, 0.8694, -0.0521), "r_elbow"),
}

# HAnim segment name carried by each joint (segment = bone distal to the joint)
SEG = {
    "humanoid_root": "sacrum",      "sacroiliac": "pelvis",
    "l_hip": "l_thigh", "l_knee": "l_calf", "l_talocrural": "l_hindfoot",
    "l_metatarsophalangeal_2": "l_forefoot",
    "r_hip": "r_thigh", "r_knee": "r_calf", "r_talocrural": "r_hindfoot",
    "r_metatarsophalangeal_2": "r_forefoot",
    "vl5": "l5", "vl1": "l1", "vc4": "c4", "skullbase": "skull",
    "l_shoulder": "l_upperarm", "l_elbow": "l_forearm", "l_radiocarpal": "l_hand",
    "r_shoulder": "r_upperarm", "r_elbow": "r_forearm", "r_radiocarpal": "r_hand",
}

# children lookup
CHILDREN = {name: [] for name in J}
for name, (_, parent) in J.items():
    if parent:
        CHILDREN[parent].append(name)

BONE = "0.95 0.91 0.82"     # bone-ish off white
JOINTC = "0.93 0.78 0.30"   # joint marker gold
SKIN = "0.86 0.66 0.52"     # head/hands

# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------
def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def mid(a, b): return ((a[0]+b[0])/2, (a[1]+b[1])/2, (a[2]+b[2])/2)
def norm(v):   return math.sqrt(v[0]**2+v[1]**2+v[2]**2)

def axis_angle_from_y(d):
    """Rotation that maps the +Y axis onto direction d. Returns 'ax ay az angle'."""
    n = norm(d)
    if n < 1e-9:
        return "0 0 1 0"
    dx, dy, dz = d[0]/n, d[1]/n, d[2]/n
    # axis = Y x d
    ax, ay, az = (1*dz - 0*dy), (0*dx - 0*dz), (0*dy - 1*dx)   # = (dz, 0, -dx)
    al = math.sqrt(ax*ax+ay*ay+az*az)
    angle = math.acos(max(-1.0, min(1.0, dy)))
    if al < 1e-9:                       # parallel to Y
        return "1 0 0 0" if dy > 0 else "1 0 0 %.4f" % math.pi
    return "%.4f %.4f %.4f %.4f" % (ax/al, ay/al, az/al, angle)

def f3(v): return "%.4f %.4f %.4f" % v

def shape(geom, color, spec="0.2 0.2 0.2", shin="0.3"):
    return (f'<Shape><Appearance><Material diffuseColor="{color}" '
            f'specularColor="{spec}" shininess="{shin}"/></Appearance>{geom}</Shape>')

def sphere(center, r, color):
    return (f'<Transform translation="{f3(center)}">'
            f'{shape(f"<Sphere radius=\"{r:.4f}\"/>", color)}</Transform>')

def bone(a, b, r, color):
    d = sub(b, a)
    return (f'<Transform translation="{f3(mid(a,b))}" rotation="{axis_angle_from_y(d)}">'
            f'{shape(f"<Cylinder height=\"{norm(d):.4f}\" radius=\"{r:.4f}\"/>", color)}'
            f'</Transform>')

def box_at(center, size, color, rot="0 0 1 0"):
    return (f'<Transform translation="{f3(center)}" rotation="{rot}">'
            f'{shape(f"<Box size=\"{size}\"/>", color)}</Transform>')

# bone / joint radii per region
BONE_R = {"thigh":0.045,"calf":0.038,"upperarm":0.030,"forearm":0.026,
          "spine":0.045,"neck":0.028,"foot":0.022,"default":0.030}
JOINT_R = {"hip":0.045,"knee":0.040,"talocrural":0.035,"shoulder":0.038,
           "elbow":0.032,"radiocarpal":0.026,"default":0.028}

def region_of(name):
    for k in ("thigh","calf","upperarm","forearm"):
        if k in SEG[name]: return k
    if name in ("vl5","vl1"): return "spine"
    if name in ("vc4","skullbase"): return "neck"
    if "foot" in SEG[name]: return "foot"
    return "default"

def joint_radius(name):
    for k in JOINT_R:
        if k in name: return JOINT_R[k]
    return JOINT_R["default"]

# ---------------------------------------------------------------------------
# 2. build segment geometry (absolute coords) for each joint
# ---------------------------------------------------------------------------
def segment_geometry(name):
    c = J[name][0]
    g = [sphere(c, joint_radius(name), JOINTC)]
    # bones to children
    for ch in CHILDREN[name]:
        g.append(bone(c, J[ch][0], BONE_R.get(region_of(name), 0.03), BONE))
    # terminal / special geometry
    if name == "skullbase":
        head = (c[0]+0.003, c[1]+0.07, c[2]+0.015)
        g.append(sphere(head, 0.105, SKIN))
    if name in ("l_radiocarpal", "r_radiocarpal"):
        hand = (c[0], c[1]-0.05, c[2])
        g.append(sphere(hand, 0.035, SKIN))
    if name in ("l_talocrural", "r_talocrural"):
        # flat foot box extending forward (+Z) from ankle, resting on ground
        side = 1 if name.startswith("l_") else -1
        foot_c = (c[0], 0.025, c[2] + 0.10)
        g.append(box_at(foot_c, "0.085 0.05 0.22", BONE))
    return "".join(g)

def build_joint(name, indent=4):
    pad = " " * indent
    seg = SEG[name]
    geo = segment_geometry(name)
    out = [f'{pad}<HAnimJoint DEF="{name}" name="{name}" center="{f3(J[name][0])}">']
    out.append(f'{pad}  <HAnimSegment DEF="seg_{seg}" name="{seg}" containerField="children">')
    out.append(f'{pad}    {geo}')
    out.append(f'{pad}  </HAnimSegment>')
    for ch in CHILDREN[name]:
        out.append(build_joint(ch, indent + 2))
    out.append(f'{pad}</HAnimJoint>')
    return "\n".join(out)

# flat USE lists for HAnim conformance (joints + segments fields)
def use_lists():
    js = "\n".join(f'      <HAnimJoint USE="{n}" containerField="joints"/>' for n in J)
    ss = "\n".join(f'      <HAnimSegment USE="seg_{SEG[n]}" containerField="segments"/>' for n in J)
    return js, ss

# ---------------------------------------------------------------------------
# 3. running gait : OrientationInterpolators (rotation about X = flexion)
# ---------------------------------------------------------------------------
GAIT_KEY = "0 0.25 0.5 0.75 1"
def rot_kv(vals):           # list of X-axis angles -> SFRotation keyValue
    return "  ".join(f"1 0 0 {a:g}" for a in vals)

GAIT = {
    "l_hip":        [-0.55, 0.15, 0.48, -0.10, -0.55],
    "r_hip":        [0.48, -0.10, -0.55, 0.15, 0.48],
    "l_knee":       [0.10, 0.85, 1.50, 0.30, 0.10],
    "r_knee":       [1.50, 0.30, 0.10, 0.85, 1.50],
    "l_talocrural": [-0.20, 0.10, 0.40, -0.15, -0.20],
    "r_talocrural": [0.40, -0.15, -0.20, 0.10, 0.40],
    "l_shoulder":   [0.40, -0.10, -0.35, 0.10, 0.40],
    "r_shoulder":   [-0.35, 0.10, 0.40, -0.10, -0.35],
    "l_elbow":      [-0.85, -1.10, -0.85, -0.65, -0.85],
    "r_elbow":      [-0.85, -0.65, -0.85, -1.10, -0.85],
}

def gait_nodes():
    interps, routes = [], []
    for joint, vals in GAIT.items():
        d = f"{joint}_int"
        interps.append(f'  <OrientationInterpolator DEF="{d}" key="{GAIT_KEY}" '
                       f'keyValue="{rot_kv(vals)}"/>')
        routes.append(f'  <ROUTE fromNode="GaitClock" fromField="fraction_changed" '
                      f'toNode="{d}" toField="set_fraction"/>')
        routes.append(f'  <ROUTE fromNode="{d}" fromField="value_changed" '
                      f'toNode="{joint}" toField="set_rotation"/>')
    # vertical pelvis bounce (2 per stride) on humanoid_root translation
    bounce = "0 0 0  0 0.045 0  0 0 0  0 0.045 0  0 0 0"
    interps.append('  <PositionInterpolator DEF="bounce_int" '
                   'key="0 0.25 0.5 0.75 1" keyValue="' + bounce + '"/>')
    routes.append('  <ROUTE fromNode="GaitClock" fromField="fraction_changed" '
                  'toNode="bounce_int" toField="set_fraction"/>')
    routes.append('  <ROUTE fromNode="bounce_int" fromField="value_changed" '
                  'toNode="humanoid_root" toField="set_translation"/>')
    return "\n".join(interps), "\n".join(routes)

# ---------------------------------------------------------------------------
# 4. course : waypoints (x,z) with turns -> Traveler translation + heading
# ---------------------------------------------------------------------------
WAYPOINTS = [(0.0,0.0),(0.0,5.0),(2.6,9.0),(-2.6,13.0),(2.6,17.0),(0.0,21.0),(0.0,28.0)]

def course_nodes():
    # arc-length parametrisation for ~constant speed
    dists = [0.0]
    for i in range(1, len(WAYPOINTS)):
        a, b = WAYPOINTS[i-1], WAYPOINTS[i]
        dists.append(dists[-1] + math.hypot(b[0]-a[0], b[1]-a[1]))
    total = dists[-1]
    keys = [d/total for d in dists]
    pos_kv = "  ".join(f"{x:.3f} 0 {z:.3f}" for (x, z) in WAYPOINTS)
    # heading of the segment leaving each waypoint (last reuses previous)
    headings = []
    for i in range(len(WAYPOINTS)):
        j = min(i, len(WAYPOINTS)-2)
        a, b = WAYPOINTS[j], WAYPOINTS[j+1]
        headings.append(math.atan2(b[0]-a[0], b[1]-a[1]))   # face +Z baseline
    head_kv = "  ".join(f"0 1 0 {h:.4f}" for h in headings)
    key_str = " ".join(f"{k:.4f}" for k in keys)
    nodes = (
        f'  <PositionInterpolator DEF="path_int" key="{key_str}" keyValue="{pos_kv}"/>\n'
        f'  <OrientationInterpolator DEF="heading_int" key="{key_str}" keyValue="{head_kv}"/>'
    )
    routes = (
        '  <ROUTE fromNode="CourseClock" fromField="fraction_changed" toNode="path_int" toField="set_fraction"/>\n'
        '  <ROUTE fromNode="CourseClock" fromField="fraction_changed" toNode="heading_int" toField="set_fraction"/>\n'
        '  <ROUTE fromNode="path_int" fromField="value_changed" toNode="Traveler" toField="set_translation"/>\n'
        '  <ROUTE fromNode="heading_int" fromField="value_changed" toNode="Traveler" toField="set_rotation"/>'
    )
    return nodes, routes

def course_scenery():
    s = []
    # ground track
    s.append('  <Transform translation="0 -0.01 13">'
             + shape('<Box size="14 0.02 34"/>', "0.20 0.34 0.22") + '</Transform>')
    # centre lane stripe
    s.append('  <Transform translation="0 0.001 13">'
             + shape('<Box size="0.18 0.02 32"/>', "0.85 0.82 0.5") + '</Transform>')
    # slalom cones the runner weaves around (on the centre line)
    for z in (9.0, 13.0, 17.0):
        s.append(f'  <Transform translation="0 0.2 {z}">'
                 + shape('<Cone bottomRadius="0.18" height="0.4"/>', "0.95 0.45 0.1") + '</Transform>')
    # start gate posts
    for x in (-1.6, 1.6):
        s.append(f'  <Transform translation="{x} 0.6 0">'
                 + shape('<Box size="0.12 1.2 0.12"/>', "0.8 0.8 0.85") + '</Transform>')
    # finish banner
    s.append('  <Transform translation="0 1.9 28">'
             + shape('<Box size="3.4 0.45 0.08"/>', "0.85 0.15 0.15") + '</Transform>')
    for x in (-1.6, 1.6):
        s.append(f'  <Transform translation="{x} 0.9 28">'
                 + shape('<Box size="0.12 1.8 0.12"/>', "0.8 0.8 0.85") + '</Transform>')
    return "\n".join(s)

# ---------------------------------------------------------------------------
# assemble document
# ---------------------------------------------------------------------------
skeleton = build_joint("humanoid_root", indent=6)
joints_use, segs_use = use_lists()
gait_int, gait_routes = gait_nodes()
course_int, course_routes = course_nodes()
scenery = course_scenery()

doc = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance"
     xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">
  <head>
    <component name="HAnim" level="1"/>
    <meta name="title" content="running_human.x3d"/>
    <meta name="description" content="HAnim 2.0 LOA-1 humanoid running through a slalom course with turns and obstacles. Joint centers from Web3D DiamondManLOA1 template."/>
    <meta name="generator" content="generate_runner.py (x3d_mcp)"/>
  </head>
  <Scene>
    <WorldInfo title="HAnim LOA-1 Running Figure"/>
    <Background skyColor="0.5 0.65 0.85 0.15 0.22 0.35" groundColor="0.12 0.16 0.12"
                skyAngle="1.2"/>
    <NavigationInfo type='"EXAMINE" "WALK" "ANY"' speed="3"/>

    <!-- viewpoints -->
    <Viewpoint DEF="Overview" position="9 7 -6" orientation="0.2 0.95 0.2 2.5"
               description="Course overview"/>
    <Viewpoint DEF="StartLine" position="3.5 1.5 -3" orientation="0 1 0 0.7"
               description="Start line"/>

    <DirectionalLight direction="-0.4 -1 -0.5" intensity="0.9" ambientIntensity="0.4"/>
    <DirectionalLight direction="0.6 -0.4 0.6" intensity="0.4"/>

    <!-- ===================== COURSE / LEVEL ===================== -->
{scenery}

    <!-- ===================== TRAVELLER (path + heading) ===================== -->
    <Transform DEF="Traveler">
      <!-- chase camera rides with the runner -->
      <Viewpoint DEF="ChaseCam" position="0 1.7 -3.2" orientation="0 1 0 3.14159"
                 description="Chase cam (runner)"/>

      <HAnimHumanoid DEF="Human" name="humanoid" version="2.0" loa="1">
        <!-- skeleton (rendered hierarchy) -->
{skeleton.replace('<HAnimJoint DEF="humanoid_root"', '<HAnimJoint DEF="humanoid_root" containerField="skeleton"', 1)}
        <!-- flat conformance lists -->
{joints_use}
{segs_use}
      </HAnimHumanoid>
    </Transform>

    <!-- ===================== ANIMATION ENGINE ===================== -->
    <TimeSensor DEF="GaitClock" cycleInterval="0.7" loop="true"/>
    <TimeSensor DEF="CourseClock" cycleInterval="22" loop="true"/>

{gait_int}
{course_int}

{gait_routes}
{course_routes}
  </Scene>
</X3D>
'''

with open("running_human.x3d", "w") as fh:
    fh.write(doc)

print("wrote running_human.x3d  (%d bytes, %d joints)" % (len(doc), len(J)))
