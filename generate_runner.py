#!/usr/bin/env python3
"""
HAnim 2.0 LOA-4 running humanoid on a slalom course -- built with the canonical
Web3D pipeline:

  * generation : the official x3d.py package (real HAnimHumanoid/HAnimJoint/
                 HAnimSegment node objects; containerField is assigned
                 automatically from the field a node is placed in)
  * authoring  : running_human.x3d  (X3D 4.0 XML, validates against the schema)
  * web        : running_human.html via the official X3dToX3dom.xslt stylesheet
                 (run through Saxon).  Because current X3DOM cannot render an
                 HAnim skeleton in the browser, the stylesheet is fed a
                 flattened twin (HAnim nodes -> Transform/Group); the authored
                 .x3d keeps real HAnim nodes for X3D-Edit / desktop players.

Skeleton joint centers come from the Web3D archive character JinLOA4.x3d
(loa4_skeleton.json).  Gait cadence is synchronized to ground speed.
"""
import json
import math
import os
import subprocess

from x3d import x3d as X

# ---------------------------------------------------------------------------
# 1. LOA-4 skeleton data
# ---------------------------------------------------------------------------
_sk = json.load(open("loa5_skeleton.json"))
ORDER = _sk["order"]
DATA = _sk["data"]

J = {n: [float(v) for v in DATA[n]["center"].split()] for n in ORDER}
PARENT = {n: DATA[n]["parent"] for n in ORDER}
SEG = {n: DATA[n]["segment"] for n in ORDER}
CHILDREN = {n: [] for n in ORDER}
for n in ORDER:
    if PARENT[n]:
        CHILDREN[PARENT[n]].append(n)

BONE = [0.95, 0.91, 0.82]
JOINTC = [0.93, 0.78, 0.30]
SKIN = [0.86, 0.66, 0.52]
EYE = [0.95, 0.95, 0.98]

# ---------------------------------------------------------------------------
# geometry helpers (return x3d.py node objects)
# ---------------------------------------------------------------------------
def sub(a, b): return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
def mid(a, b): return [(a[0]+b[0])/2, (a[1]+b[1])/2, (a[2]+b[2])/2]
def norm(v):   return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def aa_from_y(d):
    """Axis-angle [ax,ay,az,angle] mapping +Y onto direction d."""
    n = norm(d)
    if n < 1e-9:
        return [0, 0, 1, 0]
    dx, dy, dz = d[0]/n, d[1]/n, d[2]/n
    ax, az = dz, -dx
    al = math.sqrt(ax*ax + az*az)
    angle = math.acos(max(-1.0, min(1.0, dy)))
    if al < 1e-9:
        return [1, 0, 0, 0] if dy > 0 else [1, 0, 0, math.pi]
    return [ax/al, 0.0, az/al, angle]

def shape(geom, color):
    return X.Shape(
        appearance=X.Appearance(material=X.Material(
            diffuseColor=color, specularColor=[0.2, 0.2, 0.2], shininess=0.3)),
        geometry=geom)

def sphere(center, r, color):
    return X.Transform(translation=list(center),
                       children=[shape(X.Sphere(radius=r), color)])

def bone(a, b, r, color=BONE):
    d = sub(b, a)
    if norm(d) < 1e-6:
        return None
    return X.Transform(translation=mid(a, b), rotation=aa_from_y(d),
                       children=[shape(X.Cylinder(height=norm(d), radius=r), color)])

# ---------------------------------------------------------------------------
# per-joint sizing
# ---------------------------------------------------------------------------
_FINGER_KEYS = ("metacarp", "phalang", "midcarpal", "carpometacarpal")
def is_finger(n):
    return any(k in n for k in _FINGER_KEYS) or ("carpal_" in n and "interphalangeal" in n)

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
    if n[0] == "v" and len(n) > 1 and n[1] in "clt" or n == "sacroiliac": return 0.015
    if n == "temporomandibular": return 0.010
    return 0.016

def bone_radius(parent):
    if parent in ("l_hip", "r_hip"): return 0.042
    if parent in ("l_knee", "r_knee"): return 0.034
    if parent in ("l_shoulder", "r_shoulder"): return 0.027
    if parent in ("l_elbow", "r_elbow"): return 0.023
    if parent in ("l_radiocarpal", "r_radiocarpal"): return 0.0055
    if parent.endswith("talocrural"): return 0.0075
    if parent[0] == "v" or parent in ("humanoid_root", "sacroiliac"): return 0.024
    if "clavicular" in parent: return 0.011
    return 0.012

def static_rotation(n):
    if n == "vl5":
        return [1, 0, 0, 0.12]   # forward running lean
    return None

# ---------------------------------------------------------------------------
# 2. segment geometry + joint tree
# ---------------------------------------------------------------------------
def segment_geometry(name):
    if is_finger(name):
        return []
    c = J[name]
    color = EYE if "eyeball" in name else (SKIN if ("eye" in name or "brow" in name) else JOINTC)
    g = [sphere(c, joint_radius(name), color)]
    for ch in CHILDREN[name]:
        if is_finger(ch):
            continue
        b = bone(c, J[ch], bone_radius(name))
        if b is not None:
            g.append(b)
    if name in ("l_radiocarpal", "r_radiocarpal"):
        side = "l" if name.startswith("l_") else "r"
        knuckle = J.get(f"{side}_metacarpophalangeal_3")
        if knuckle:
            b = bone(c, knuckle, 0.022, SKIN)
            if b is not None:
                g.append(b)
            g.append(sphere(knuckle, 0.052, SKIN))
    if name == "skullbase":
        g.append(sphere([c[0]+0.003, c[1]+0.065, c[2]+0.015], 0.092, SKIN))
    if name == "temporomandibular":
        g.append(sphere([c[0], c[1]-0.02, c[2]+0.03], 0.030, SKIN))
    if name.endswith("talocrural"):
        g.append(sphere([c[0], c[1]-0.030, c[2]-0.035], 0.022, BONE))
    return g

def build_joint(name):
    seg = X.HAnimSegment(DEF=f"seg_{SEG[name]}", name=SEG[name],
                         children=segment_geometry(name))
    kids = [seg] + [build_joint(ch) for ch in CHILDREN[name]]
    rot = static_rotation(name)
    j = X.HAnimJoint(DEF=name, name=name, center=list(J[name]), children=kids)
    if rot:
        j.rotation = rot
    return j

# ---------------------------------------------------------------------------
# 3. gait
# ---------------------------------------------------------------------------
STRIDE_PERIOD = 0.7
STRIDE_LENGTH = 2.0
SPEED = STRIDE_LENGTH / STRIDE_PERIOD

GAIT_KEY = [0, 0.25, 0.5, 0.75, 1]
AX = (1, 0, 0)
AY = (0, 1, 0)
GAIT = {
    "l_hip":        (AX, [-0.55, 0.15, 0.48, -0.10, -0.55]),
    "r_hip":        (AX, [0.48, -0.10, -0.55, 0.15, 0.48]),
    "l_knee":       (AX, [0.10, 0.85, 1.50, 0.30, 0.10]),
    "r_knee":       (AX, [1.50, 0.30, 0.10, 0.85, 1.50]),
    "l_talocrural": (AX, [-0.20, 0.10, 0.40, -0.15, -0.20]),
    "r_talocrural": (AX, [0.40, -0.15, -0.20, 0.10, 0.40]),
    "l_shoulder":   (AX, [0.40, -0.10, -0.35, 0.10, 0.40]),
    "r_shoulder":   (AX, [-0.35, 0.10, 0.40, -0.10, -0.35]),
    "l_elbow":      (AX, [-0.85, -1.10, -0.85, -0.65, -0.85]),
    "r_elbow":      (AX, [-0.85, -0.65, -0.85, -1.10, -0.85]),
    "sacroiliac":   (AY, [-0.10, 0.0, 0.10, 0.0, -0.10]),
    "vt6":          (AY, [0.10, 0.0, -0.10, 0.0, 0.10]),
}

def gait_nodes():
    nodes, routes = [], []
    for joint, (axis, vals) in GAIT.items():
        d = f"{joint}_int"
        kv = [[axis[0], axis[1], axis[2], a] for a in vals]
        nodes.append(X.OrientationInterpolator(DEF=d, key=GAIT_KEY, keyValue=kv))
        routes.append(X.ROUTE(fromNode="GaitClock", fromField="fraction_changed",
                              toNode=d, toField="set_fraction"))
        routes.append(X.ROUTE(fromNode=d, fromField="value_changed",
                              toNode=joint, toField="set_rotation"))
    bounce = [[0,0,0], [0,0.045,0], [0,0,0], [0,0.045,0], [0,0,0]]
    nodes.append(X.PositionInterpolator(DEF="bounce_int", key=GAIT_KEY, keyValue=bounce))
    routes.append(X.ROUTE(fromNode="GaitClock", fromField="fraction_changed",
                          toNode="bounce_int", toField="set_fraction"))
    routes.append(X.ROUTE(fromNode="bounce_int", fromField="value_changed",
                          toNode="humanoid_root", toField="set_translation"))
    return nodes, routes

# ---------------------------------------------------------------------------
# 4. course
# ---------------------------------------------------------------------------
WAYPOINTS = [(0.0,0.0),(0.0,5.0),(2.6,9.0),(-2.6,13.0),(2.6,17.0),(0.0,21.0),(0.0,28.0)]

def course_nodes():
    dists = [0.0]
    for a, b in zip(WAYPOINTS, WAYPOINTS[1:]):
        dists.append(dists[-1] + math.hypot(b[0]-a[0], b[1]-a[1]))
    total = dists[-1]
    lap = total / SPEED
    keys = [d/total for d in dists]
    pos_kv = [[x, 0, z] for x, z in WAYPOINTS]
    head_kv = []
    for i in range(len(WAYPOINTS)):
        j = min(i, len(WAYPOINTS)-2)
        a, b = WAYPOINTS[j], WAYPOINTS[j+1]
        head_kv.append([0, 1, 0, math.atan2(b[0]-a[0], b[1]-a[1])])
    nodes = [
        X.PositionInterpolator(DEF="path_int", key=keys, keyValue=pos_kv),
        X.OrientationInterpolator(DEF="heading_int", key=keys, keyValue=head_kv),
    ]
    routes = [
        X.ROUTE(fromNode="CourseClock", fromField="fraction_changed", toNode="path_int", toField="set_fraction"),
        X.ROUTE(fromNode="CourseClock", fromField="fraction_changed", toNode="heading_int", toField="set_fraction"),
        X.ROUTE(fromNode="path_int", fromField="value_changed", toNode="Traveler", toField="set_translation"),
        X.ROUTE(fromNode="heading_int", fromField="value_changed", toNode="Traveler", toField="set_rotation"),
    ]
    return nodes, routes, lap, total

def box(t, size, color):
    return X.Transform(translation=t, children=[shape(X.Box(size=size), color)])

def scenery():
    s = [box([0,-0.01,13], [14,0.02,34], [0.20,0.34,0.22]),
         box([0,0.001,13], [0.18,0.02,32], [0.85,0.82,0.5])]
    for z in (9.0, 13.0, 17.0):
        s.append(X.Transform(translation=[0,0.2,z], children=[
            shape(X.Cone(bottomRadius=0.18, height=0.4), [0.95,0.45,0.1])]))
    for x in (-1.6, 1.6):
        s.append(box([x,0.6,0], [0.12,1.2,0.12], [0.8,0.8,0.85]))
    s.append(box([0,1.9,28], [3.4,0.45,0.08], [0.85,0.15,0.15]))
    for x in (-1.6, 1.6):
        s.append(box([x,0.9,28], [0.12,1.8,0.12], [0.8,0.8,0.85]))
    return s

# ---------------------------------------------------------------------------
# assemble with x3d.py
# ---------------------------------------------------------------------------
gait_int, gait_routes = gait_nodes()
course_int, course_routes, LAP, COURSE_LEN = course_nodes()

# Only the skeleton field is populated. x3d.py serializes the joints/segments
# fields *before* skeleton, which would place every USE before its DEF
# (unresolvable). The flat lists are optional bookkeeping, so we omit them.
_root = build_joint("humanoid_root")
_root.containerField = "skeleton"   # x3d.py omits it otherwise; Castle needs it
humanoid = X.HAnimHumanoid(
    DEF="Human", name="humanoid", version="2.0", loa=5,
    skeleton=[_root])

traveler = X.Transform(DEF="Traveler", children=[
    X.Viewpoint(DEF="ChaseCam", position=[0,1.5,-3.2], orientation=[0,1,0,3.14159],
                description="Chase cam (runner)"),
    humanoid])

scene = X.Scene(children=[
    X.WorldInfo(title="HAnim LOA-4 Running Figure"),
    X.Background(skyColor=[[0.5,0.65,0.85], [0.15,0.22,0.35]], skyAngle=[1.2],
                 groundColor=[[0.12,0.16,0.12]]),
    X.NavigationInfo(type=["EXAMINE","WALK","ANY"], speed=3),
    X.Viewpoint(DEF="Overview", position=[9,7,-6], orientation=[0.2,0.95,0.2,2.5],
                description="Course overview"),
    X.Viewpoint(DEF="StartLine", position=[3.5,1.5,-3], orientation=[0,1,0,0.7],
                description="Start line"),
    X.DirectionalLight(direction=[-0.4,-1,-0.5], intensity=0.9, ambientIntensity=0.4),
    X.DirectionalLight(direction=[0.6,-0.4,0.6], intensity=0.4),
    *scenery(),
    traveler,
    X.TimeSensor(DEF="GaitClock", cycleInterval=STRIDE_PERIOD, loop=True),
    X.TimeSensor(DEF="CourseClock", cycleInterval=round(LAP, 2), loop=True),
    *gait_int, *course_int,
    *gait_routes, *course_routes,
])

doc = X.X3D(profile="Immersive", version="4.0",
            head=X.head(children=[
                X.component(name="HAnim", level=1),
                X.meta(name="title", content="running_human.x3d"),
                X.meta(name="description",
                       content=("HAnim 2.0 LOA-5 humanoid (150 joints, centers from the "
                                "Web3D AllBonesLOA5Skeletons draft) running a slalom "
                                "course; gait cadence synchronized to ground speed. "
                                "Built with x3d.py.")),
                X.meta(name="generator", content="generate_runner.py (x3d.py canonical pipeline)"),
            ]),
            Scene=scene)

xml = doc.XML()
# x3d.py drops two HAnim attributes on output: the skeleton field's
# containerField (Castle renders the humanoid only via skeleton, not children)
# and HAnimHumanoid version. Restore both.
xml = xml.replace("<HAnimHumanoid DEF='Human'",
                  "<HAnimHumanoid DEF='Human' version='2.0'", 1)
xml = xml.replace("<HAnimJoint DEF='humanoid_root'",
                  "<HAnimJoint DEF='humanoid_root' containerField='skeleton'", 1)
# Drop the DOCTYPE: the external DTD reference makes web players (X_ITE) stall
# fetching it on load. The file stays valid X3D 4.0 via the XSD schemaLocation.
xml = "\n".join(l for l in xml.splitlines() if not l.startswith("<!DOCTYPE"))
with open("running_human.x3d", "w") as fh:
    fh.write(xml)
print(f"wrote running_human.x3d via x3d.py ({len(xml)} bytes, {len(ORDER)} joints, "
      f"course {COURSE_LEN:.1f} m @ {SPEED:.2f} m/s -> lap {LAP:.1f} s)")

# ---------------------------------------------------------------------------
# web page: flatten HAnim -> core nodes, then official X3dToX3dom.xslt (Saxon)
# ---------------------------------------------------------------------------
SAXON = "tools_x3d/saxon9he.jar"
XSLT = "tools_x3d/X3dToX3dom.xslt"
STABLE_X3DOM = "https://x3dom.org/download/1.8.3"

def flatten_hanim(xml_text):
    from lxml import etree
    root = etree.fromstring(xml_text.encode(),
                            etree.XMLParser(remove_comments=True))
    TAGMAP = {"HAnimHumanoid": "Transform", "HAnimJoint": "Transform",
              "HAnimSite": "Transform", "HAnimSegment": "Group"}
    for el in list(root.iter()):
        if el.get("USE") and el.get("containerField") in ("joints", "segments"):
            el.getparent().remove(el)
    KEEP = {"DEF", "USE", "center", "rotation", "translation", "scale"}
    for el in root.iter():
        if el.tag in TAGMAP:
            el.tag = TAGMAP[el.tag]
            for a in list(el.attrib):
                if a not in KEEP:
                    del el.attrib[a]
    return etree.tostring(root, encoding="unicode")

XITE_JS = "https://cdn.jsdelivr.net/npm/x_ite@latest/dist/x_ite.min.js"

def write_xite_page():
    """Primary browser page: X_ITE renders the real-HAnim .x3d directly (X_ITE
    has full HAnim support, unlike X3DOM -- no flattening needed)."""
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>HAnim LOA-5 Runner — Slalom Course</title>
  <script src="{XITE_JS}"></script>
  <style>
    html,body {{ margin:0; height:100%; background:#10131a; }}
    x3d-canvas {{ width:100vw; height:100vh; display:block; }}
  </style>
</head>
<body>
  <x3d-canvas src="running_human.x3d"></x3d-canvas>
</body>
</html>
"""
    with open("running_human.html", "w") as fh:
        fh.write(page)
    print("wrote running_human.html (X_ITE, renders real HAnim LOA-5)")

def write_x3dom_fallback():
    """X3DOM fallback via the MCP renderer on a flattened twin (X3DOM can't
    render HAnim). Kept until the X3DOM HAnim gap is addressed upstream."""
    try:
        import sys
        sys.path.insert(0, "src")
        from tools.render import _x3dom_page
        page = _x3dom_page(flatten_hanim(xml),
                           title="HAnim LOA-5 Runner — Slalom Course",
                           width="100%", height="100vh")
        open("running_human_x3dom.html", "w").write(page)
        print("wrote running_human_x3dom.html (X3DOM fallback, flattened twin)")
    except Exception as e:
        print(f"skipped X3DOM fallback: {e}")

write_xite_page()
write_x3dom_fallback()
