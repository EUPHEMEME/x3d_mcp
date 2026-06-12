#!/usr/bin/env python3
"""
Generate a standards-conformant HAnim 2.0 LOA-4 running humanoid that travels
through a slalom course with turns and obstacles.

Skeleton: real HAnim nodes (HAnimHumanoid / HAnimJoint / HAnimSegment) using
the 146-joint LOA-4 hierarchy and joint centers extracted from the official
Web3D archive character HumanoidAnimation/Characters/JinLOA4.x3d
(loa4_skeleton.json, generated alongside this script).

Because HAnimJoint behaves like a Transform whose only non-default field at
rest is `center`, the rest-pose local frame of every joint equals the global
humanoid frame: all segment geometry is authored in absolute coordinates and
still articulates correctly when ancestor joints rotate.

Gait/locomotion are synchronized: course lap time is derived from stride
length / stride period so foot speed matches ground speed (no skating).

Output: running_human.x3d (X3D 4.0 XML). The X3DOM HTML page is produced via
the MCP renderer (tools.render._x3dom_page).
"""
import json
import math

# ---------------------------------------------------------------------------
# 1. LOA-4 skeleton (from JinLOA4.x3d): name -> center/parent/segment
# ---------------------------------------------------------------------------
_sk = json.load(open("loa4_skeleton.json"))
ORDER = _sk["order"]
DATA = _sk["data"]          # name -> {"center": "x y z", "parent": str|None, "segment": str}

J = {n: tuple(float(v) for v in DATA[n]["center"].split()) for n in ORDER}
PARENT = {n: DATA[n]["parent"] for n in ORDER}
SEG = {n: DATA[n]["segment"] for n in ORDER}

CHILDREN = {n: [] for n in ORDER}
for n in ORDER:
    if PARENT[n]:
        CHILDREN[PARENT[n]].append(n)

BONE = "0.95 0.91 0.82"     # bone off-white
JOINTC = "0.93 0.78 0.30"   # joint marker gold
SKIN = "0.86 0.66 0.52"     # head/hands
EYE = "0.95 0.95 0.98"      # eyeball white

# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------
def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def mid(a, b): return ((a[0]+b[0])/2, (a[1]+b[1])/2, (a[2]+b[2])/2)
def norm(v):   return math.sqrt(v[0]**2+v[1]**2+v[2]**2)

def axis_angle_from_y(d):
    """Rotation mapping the +Y axis onto direction d -> 'ax ay az angle'."""
    n = norm(d)
    if n < 1e-9:
        return "0 0 1 0"
    dx, dy, dz = d[0]/n, d[1]/n, d[2]/n
    ax, ay, az = dz, 0.0, -dx              # Y x d
    al = math.sqrt(ax*ax + az*az)
    angle = math.acos(max(-1.0, min(1.0, dy)))
    if al < 1e-9:
        return "1 0 0 0" if dy > 0 else "1 0 0 %.4f" % math.pi
    return "%.4f %.4f %.4f %.4f" % (ax/al, ay/al, az/al, angle)

def f3(v): return "%.4f %.4f %.4f" % v

def shape(geom, color, spec="0.2 0.2 0.2", shin="0.3"):
    return (f'<Shape><Appearance><Material diffuseColor="{color}" '
            f'specularColor="{spec}" shininess="{shin}"/></Appearance>{geom}</Shape>')

def sphere(center, r, color):
    return (f'<Transform translation="{f3(center)}">'
            f'{shape(f"<Sphere radius=\"{r:.4f}\"/>", color)}</Transform>')

def bone(a, b, r, color=BONE):
    d = sub(b, a)
    if norm(d) < 1e-6:
        return ""
    return (f'<Transform translation="{f3(mid(a,b))}" rotation="{axis_angle_from_y(d)}">'
            f'{shape(f"<Cylinder height=\"{norm(d):.4f}\" radius=\"{r:.4f}\"/>", color)}'
            f'</Transform>')

# ---------------------------------------------------------------------------
# per-joint sizing heuristics
# ---------------------------------------------------------------------------
_HAND = ("carpal", "carpo", "metacarp", "midcarpal")
_FOOT = ("talo", "tars", "cuneo", "calcaneo", "transversetarsal", "metatars")

def _is_hand(n):  return any(k in n for k in _HAND)
def _is_foot(n):  return any(k in n for k in _FOOT)
def _is_vert(n):  return n[0] == "v" and n[1] in "clt" or n in ("sacroiliac",)

def joint_radius(n):
    if "eyeball" in n: return 0.013
    if "eye" in n or "brow" in n: return 0.005
    if "hip" in n: return 0.040
    if "knee" in n: return 0.035
    if "shoulder" in n: return 0.032
    if "elbow" in n: return 0.028
    if n.endswith("talocrural"): return 0.024
    if "radiocarpal" in n: return 0.016
    if "clavicular" in n: return 0.014
    if _is_hand(n): return 0.0065
    if _is_foot(n): return 0.009
    if _is_vert(n): return 0.015
    if n == "temporomandibular": return 0.010
    return 0.016

def bone_radius(parent):
    if parent in ("l_hip", "r_hip"): return 0.042
    if parent in ("l_knee", "r_knee"): return 0.034
    if parent in ("l_shoulder", "r_shoulder"): return 0.027
    if parent in ("l_elbow", "r_elbow"): return 0.023
    if "radiocarpal" in parent or _is_hand(parent): return 0.0055
    if parent.endswith("talocrural") or _is_foot(parent): return 0.0075
    if _is_vert(parent) or parent in ("humanoid_root",): return 0.024
    if "clavicular" in parent: return 0.011
    return 0.012

# joints whose rotation is animated by the gait engine
GAIT_AXIS_X = "1 0 0"
GAIT_KEY = "0 0.25 0.5 0.75 1"
GAIT = {  # joint -> (axis, angles at the 5 keys)
    "l_hip":        (GAIT_AXIS_X, [-0.55, 0.15, 0.48, -0.10, -0.55]),
    "r_hip":        (GAIT_AXIS_X, [0.48, -0.10, -0.55, 0.15, 0.48]),
    "l_knee":       (GAIT_AXIS_X, [0.10, 0.85, 1.50, 0.30, 0.10]),
    "r_knee":       (GAIT_AXIS_X, [1.50, 0.30, 0.10, 0.85, 1.50]),
    "l_talocrural": (GAIT_AXIS_X, [-0.20, 0.10, 0.40, -0.15, -0.20]),
    "r_talocrural": (GAIT_AXIS_X, [0.40, -0.15, -0.20, 0.10, 0.40]),
    "l_shoulder":   (GAIT_AXIS_X, [0.40, -0.10, -0.35, 0.10, 0.40]),
    "r_shoulder":   (GAIT_AXIS_X, [-0.35, 0.10, 0.40, -0.10, -0.35]),
    "l_elbow":      (GAIT_AXIS_X, [-0.85, -1.10, -0.85, -0.65, -0.85]),
    "r_elbow":      (GAIT_AXIS_X, [-0.85, -0.65, -0.85, -1.10, -0.85]),
    # pelvis yaw sway with shoulder-girdle counter-rotation
    "sacroiliac":   ("0 1 0", [-0.10, 0.0, 0.10, 0.0, -0.10]),
    "vt6":          ("0 1 0", [0.10, 0.0, -0.10, 0.0, 0.10]),
}

# static pose: light finger curl (hands only -- metacarpophalangeal and
# carpal interphalangeal chains; thumb gets a lighter curl)
def static_rotation(n):
    if "metacarpophalangeal" in n or "carpal" in n and "interphalangeal" in n:
        if n.endswith("_1"):
            return "1 0 0 -0.25"
        return "1 0 0 -0.45"
    return None

# ---------------------------------------------------------------------------
# 2. segment geometry (absolute coords) per joint
# ---------------------------------------------------------------------------
def segment_geometry(name):
    c = J[name]
    color = EYE if "eyeball" in name else (SKIN if "eye" in name or "brow" in name else JOINTC)
    g = [sphere(c, joint_radius(name), color)]
    for ch in CHILDREN[name]:
        g.append(bone(c, J[ch], bone_radius(name)))
    if name == "skullbase":
        g.append(sphere((c[0], c[1]+0.065, c[2]+0.01), 0.092, SKIN))
    if name == "temporomandibular":  # jaw hint
        g.append(sphere((c[0], c[1]-0.02, c[2]+0.03), 0.030, SKIN))
    if name.endswith("talocrural"):  # heel
        g.append(sphere((c[0], c[1]-0.030, c[2]-0.035), 0.022, BONE))
    return "".join(g)

def build_joint(name, indent=6):
    pad = " " * indent
    seg = SEG[name]
    rot = static_rotation(name)
    rot_attr = f' rotation="{rot}"' if rot else ""
    out = [f'{pad}<HAnimJoint DEF="{name}" name="{name}" center="{f3(J[name])}"{rot_attr}>']
    out.append(f'{pad}  <HAnimSegment DEF="seg_{seg}" name="{seg}" containerField="children">')
    out.append(f'{pad}    {segment_geometry(name)}')
    out.append(f'{pad}  </HAnimSegment>')
    for ch in CHILDREN[name]:
        out.append(build_joint(ch, indent + 2))
    out.append(f'{pad}</HAnimJoint>')
    return "\n".join(out)

def use_lists():
    js = "\n".join(f'      <HAnimJoint USE="{n}" containerField="joints"/>' for n in ORDER)
    ss = "\n".join(f'      <HAnimSegment USE="seg_{SEG[n]}" containerField="segments"/>' for n in ORDER)
    return js, ss

# ---------------------------------------------------------------------------
# 3. gait animation engine
# ---------------------------------------------------------------------------
STRIDE_PERIOD = 0.7   # s per full gait cycle (two footfalls)
STRIDE_LENGTH = 2.0   # m covered per gait cycle at run cadence
SPEED = STRIDE_LENGTH / STRIDE_PERIOD   # m/s

def gait_nodes():
    interps, routes = [], []
    for joint, (axis, vals) in GAIT.items():
        d = f"{joint}_int"
        kv = "  ".join(f"{axis} {a:g}" for a in vals)
        interps.append(f'  <OrientationInterpolator DEF="{d}" key="{GAIT_KEY}" keyValue="{kv}"/>')
        routes.append(f'  <ROUTE fromNode="GaitClock" fromField="fraction_changed" '
                      f'toNode="{d}" toField="set_fraction"/>')
        routes.append(f'  <ROUTE fromNode="{d}" fromField="value_changed" '
                      f'toNode="{joint}" toField="set_rotation"/>')
    bounce = "0 0 0  0 0.045 0  0 0 0  0 0.045 0  0 0 0"
    interps.append('  <PositionInterpolator DEF="bounce_int" '
                   'key="0 0.25 0.5 0.75 1" keyValue="' + bounce + '"/>')
    routes.append('  <ROUTE fromNode="GaitClock" fromField="fraction_changed" '
                  'toNode="bounce_int" toField="set_fraction"/>')
    routes.append('  <ROUTE fromNode="bounce_int" fromField="value_changed" '
                  'toNode="humanoid_root" toField="set_translation"/>')
    return "\n".join(interps), "\n".join(routes)

# ---------------------------------------------------------------------------
# 4. course: waypoints (x,z) with turns; lap time derived from gait speed
# ---------------------------------------------------------------------------
WAYPOINTS = [(0.0,0.0),(0.0,5.0),(2.6,9.0),(-2.6,13.0),(2.6,17.0),(0.0,21.0),(0.0,28.0)]

def course_nodes():
    dists = [0.0]
    for a, b in zip(WAYPOINTS, WAYPOINTS[1:]):
        dists.append(dists[-1] + math.hypot(b[0]-a[0], b[1]-a[1]))
    total = dists[-1]
    lap = total / SPEED
    keys = [d/total for d in dists]
    pos_kv = "  ".join(f"{x:.3f} 0 {z:.3f}" for (x, z) in WAYPOINTS)
    headings = []
    for i in range(len(WAYPOINTS)):
        j = min(i, len(WAYPOINTS)-2)
        a, b = WAYPOINTS[j], WAYPOINTS[j+1]
        headings.append(math.atan2(b[0]-a[0], b[1]-a[1]))
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
    return nodes, routes, lap, total

def course_scenery():
    s = []
    s.append('  <Transform translation="0 -0.01 13">'
             + shape('<Box size="14 0.02 34"/>', "0.20 0.34 0.22") + '</Transform>')
    s.append('  <Transform translation="0 0.001 13">'
             + shape('<Box size="0.18 0.02 32"/>', "0.85 0.82 0.5") + '</Transform>')
    for z in (9.0, 13.0, 17.0):
        s.append(f'  <Transform translation="0 0.2 {z}">'
                 + shape('<Cone bottomRadius="0.18" height="0.4"/>', "0.95 0.45 0.1") + '</Transform>')
    for x in (-1.6, 1.6):
        s.append(f'  <Transform translation="{x} 0.6 0">'
                 + shape('<Box size="0.12 1.2 0.12"/>', "0.8 0.8 0.85") + '</Transform>')
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
course_int, course_routes, LAP, COURSE_LEN = course_nodes()
scenery = course_scenery()

doc = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">
<X3D profile="Immersive" version="4.0"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance"
     xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">
  <head>
    <component name="HAnim" level="1"/>
    <meta name="title" content="running_human.x3d"/>
    <meta name="description" content="HAnim 2.0 LOA-4 humanoid (146 joints, centers from Web3D JinLOA4) running a slalom course; gait cadence synchronized to ground speed."/>
    <meta name="generator" content="generate_runner.py (x3d_mcp)"/>
  </head>
  <Scene>
    <WorldInfo title="HAnim LOA-4 Running Figure"/>
    <Background skyColor="0.5 0.65 0.85 0.15 0.22 0.35" groundColor="0.12 0.16 0.12"
                skyAngle="1.2"/>
    <NavigationInfo type='"EXAMINE" "WALK" "ANY"' speed="3"/>

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
      <Viewpoint DEF="ChaseCam" position="0 1.5 -3.2" orientation="0 1 0 3.14159"
                 description="Chase cam (runner)"/>

      <HAnimHumanoid DEF="Human" name="humanoid" version="2.0" loa="4">
{skeleton.replace('<HAnimJoint DEF="humanoid_root"', '<HAnimJoint DEF="humanoid_root" containerField="skeleton"', 1)}
{joints_use}
{segs_use}
      </HAnimHumanoid>
    </Transform>

    <!-- ===================== ANIMATION ENGINE =====================
         course length {COURSE_LEN:.1f} m; speed {SPEED:.2f} m/s
         lap {LAP:.1f} s; stride {STRIDE_LENGTH} m every {STRIDE_PERIOD} s -->
    <TimeSensor DEF="GaitClock" cycleInterval="{STRIDE_PERIOD}" loop="true"/>
    <TimeSensor DEF="CourseClock" cycleInterval="{LAP:.2f}" loop="true"/>

{gait_int}
{course_int}

{gait_routes}
{course_routes}
  </Scene>
</X3D>
'''

with open("running_human.x3d", "w") as fh:
    fh.write(doc)

print(f"wrote running_human.x3d  ({len(doc)} bytes, {len(ORDER)} joints, "
      f"course {COURSE_LEN:.1f} m @ {SPEED:.2f} m/s -> lap {LAP:.1f} s)")
