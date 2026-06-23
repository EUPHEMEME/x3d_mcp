"""Blender scene-graph craft inspector — post-execution validation.

Unlike X3D Techne (which intercepts structured tool-call arguments in transit),
BlenderMCP's primary tool is execute_blender_code — arbitrary Python. We cannot
pre-validate arbitrary code. Instead, we inspect the resulting Blender scene graph
for known silent-failure patterns after each execution, and report prescriptive
corrections the same way X3D Techne does: the error message is the fix.

The inspection runs inside Blender via the same socket the MCP server uses.
Each check is a small Python snippet that returns structured findings.
"""
from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field


@dataclass
class BlenderFinding:
    rule: str
    severity: str          # "HARD" or "SOFT"
    object_name: str
    message: str           # prescriptive — the fix, not just the problem


@dataclass
class BlenderInspection:
    findings: list[BlenderFinding] = field(default_factory=list)
    scene_summary: dict = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return any(f.severity == "HARD" for f in self.findings)

    def notes(self) -> list[str]:
        return [f"[{f.severity}] {f.object_name}: {f.message}" for f in self.findings]


def _mat_users_snippet(indent=8):
    """Helper: Python source to find mesh objects using a given material."""
    pad = " " * indent
    return (
        f"{pad}users = [o.name for o in bpy.data.objects\n"
        f"{pad}         if o.type == 'MESH' and mat.name in\n"
        f"{pad}         [s.name for s in o.data.materials if s]]\n"
    )


# ---------------------------------------------------------------------------
# Craft catalog.
#
# Each check is a Python snippet that runs inside Blender and prints a JSON
# array of {{rule, severity, object_name, message}}.  The message is
# prescriptive: it names the fix, not just the symptom.
#
# Organized by domain:
#   MATERIAL  — shader graph wiring, texture setup, transparency
#   GEOMETRY  — mesh health, normals, topology
#   SCENE     — camera, lights, world
#   MODIFIER  — modifier stack ordering
# ---------------------------------------------------------------------------

CHECKS: dict[str, str] = {

    # ── MATERIAL ──────────────────────────────────────────────────────────

    "unassigned_image_texture": """
import bpy, json
findings = []
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image is None:
            if any(link for out in node.outputs for link in out.links):
                users = [o.name for o in bpy.data.objects
                         if o.type == 'MESH' and mat.name in
                         [s.name for s in o.data.materials if s]]
                for u in (users or ['(unused material)']):
                    findings.append({
                        'rule': 'unassigned_image_texture',
                        'severity': 'HARD',
                        'object_name': u,
                        'message': 'Image Texture node in material "%s" is wired '
                                   'but has no image -- assign one: '
                                   'node.image = bpy.data.images.load(path)' % mat.name
                    })
print(json.dumps(findings))
""",

    "disconnected_material_output": """
import bpy, json
findings = []
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    output = None
    for node in mat.node_tree.nodes:
        if node.type == 'OUTPUT_MATERIAL' and node.is_active_output:
            output = node
            break
    if output is None: continue
    surface_in = output.inputs.get('Surface')
    if surface_in and not surface_in.links:
        users = [o.name for o in bpy.data.objects
                 if o.type == 'MESH' and mat.name in
                 [s.name for s in o.data.materials if s]]
        for u in (users or ['(unused material)']):
            findings.append({
                'rule': 'disconnected_material_output',
                'severity': 'HARD',
                'object_name': u,
                'message': 'Material "%s" has nothing connected to Material '
                           'Output Surface -- connect a Principled BSDF or '
                           'other shader node' % mat.name
            })
print(json.dumps(findings))
""",

    "wrong_colorspace": """
import bpy, json
findings = []
NON_COLOR_INPUTS = {'Normal', 'Roughness', 'Metallic', 'Specular IOR Level',
                     'Displacement', 'Bump', 'Height', 'Clearcoat Roughness',
                     'Ambient Occlusion'}
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    for node in mat.node_tree.nodes:
        if node.type != 'TEX_IMAGE' or node.image is None: continue
        cs = node.image.colorspace_settings.name
        for out in node.outputs:
            for link in out.links:
                target_name = link.to_socket.name
                if target_name in NON_COLOR_INPUTS and cs != 'Non-Color':
                    findings.append({
                        'rule': 'wrong_colorspace',
                        'severity': 'HARD',
                        'object_name': mat.name,
                        'message': 'Image "%s" feeds %s input but color space '
                                   'is "%s" -- set to Non-Color: '
                                   'image.colorspace_settings.name = "Non-Color"'
                                   % (node.image.name, target_name, cs)
                    })
                elif target_name == 'Base Color' and cs == 'Non-Color':
                    findings.append({
                        'rule': 'wrong_colorspace',
                        'severity': 'HARD',
                        'object_name': mat.name,
                        'message': 'Image "%s" feeds Base Color but color space '
                                   'is Non-Color -- set to sRGB: '
                                   'image.colorspace_settings.name = "sRGB"'
                                   % node.image.name
                    })
print(json.dumps(findings))
""",

    "normal_map_missing_node": """
import bpy, json
findings = []
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    tree = mat.node_tree
    for node in tree.nodes:
        if node.type != 'TEX_IMAGE': continue
        for out in node.outputs:
            for link in out.links:
                if link.to_node.type == 'BSDF_PRINCIPLED' and link.to_socket.name == 'Normal':
                    findings.append({
                        'rule': 'normal_map_missing_node',
                        'severity': 'HARD',
                        'object_name': mat.name,
                        'message': 'Image Texture wired directly to Principled '
                                   'BSDF Normal input in "%s" -- insert a Normal '
                                   'Map node between them (Texture.Color -> '
                                   'NormalMap.Color -> BSDF.Normal)' % mat.name
                    })
print(json.dumps(findings))
""",

    "alpha_no_blend_mode": """
import bpy, json
findings = []
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    for node in mat.node_tree.nodes:
        if node.type != 'BSDF_PRINCIPLED': continue
        alpha_input = node.inputs.get('Alpha')
        if alpha_input is None: continue
        alpha_val = alpha_input.default_value
        has_alpha_link = bool(alpha_input.links)
        if (alpha_val < 0.99 or has_alpha_link) and mat.blend_method == 'OPAQUE':
            users = [o.name for o in bpy.data.objects
                     if o.type == 'MESH' and mat.name in
                     [s.name for s in o.data.materials if s]]
            for u in (users or ['(unused material)']):
                findings.append({
                    'rule': 'alpha_no_blend_mode',
                    'severity': 'HARD',
                    'object_name': u,
                    'message': 'Material "%s" has Alpha=%.2f but blend_method is '
                               'OPAQUE -- transparency will not render. Set: '
                               'mat.blend_method = "BLEND" or "HASHED"'
                               % (mat.name, alpha_val)
                })
print(json.dumps(findings))
""",

    "missing_uv_for_texture": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    if not obj.data.uv_layers:
        has_tex = False
        for slot in obj.material_slots:
            mat = slot.material
            if mat and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        has_tex = True
                        break
            if has_tex: break
        if has_tex:
            findings.append({
                'rule': 'missing_uv_for_texture',
                'severity': 'HARD',
                'object_name': obj.name,
                'message': 'Object "%s" has a textured material but no UV map '
                           '-- texture will not map correctly. Unwrap: '
                           'bpy.ops.uv.smart_project()' % obj.name
            })
print(json.dumps(findings))
""",

    # ── GEOMETRY ──────────────────────────────────────────────────────────

    "empty_mesh": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    if len(obj.data.vertices) == 0:
        findings.append({
            'rule': 'empty_mesh',
            'severity': 'HARD',
            'object_name': obj.name,
            'message': 'Mesh "%s" has 0 vertices -- renders invisible. '
                       'Add geometry or delete it.' % obj.name
        })
print(json.dumps(findings))
""",

    "flipped_normals": """
import bpy, bmesh, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    flipped = 0
    total = len(bm.faces)
    if total == 0:
        bm.free()
        continue
    for face in bm.faces:
        center = face.calc_center_median()
        if center.length > 0.001:
            if face.normal.dot(center.normalized()) < 0:
                flipped += 1
    bm.free()
    ratio = flipped / total if total else 0
    if ratio > 0.5:
        findings.append({
            'rule': 'flipped_normals',
            'severity': 'HARD',
            'object_name': obj.name,
            'message': 'Mesh "%s" has %d/%d faces with inward-pointing normals '
                       '-- object will render inside-out or black. Recalculate: '
                       'select object, Edit Mode, Mesh > Normals > Recalculate '
                       'Outside' % (obj.name, flipped, total)
        })
print(json.dumps(findings))
""",

    "non_manifold": """
import bpy, bmesh, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    bm.free()
    total_edges = len(obj.data.edges)
    if total_edges == 0: continue
    if non_manifold > total_edges * 0.1:
        findings.append({
            'rule': 'non_manifold',
            'severity': 'SOFT',
            'object_name': obj.name,
            'message': 'Mesh "%s" has %d non-manifold edges (%.0f%%) -- may '
                       'cause shading artifacts and boolean failures. Clean up: '
                       'Edit Mode, Select > All by Trait > Non Manifold, then '
                       'merge or fill' % (obj.name, non_manifold,
                                          100 * non_manifold / total_edges)
        })
    if loose_verts > 0:
        findings.append({
            'rule': 'non_manifold',
            'severity': 'SOFT',
            'object_name': obj.name,
            'message': 'Mesh "%s" has %d loose vertices -- delete them: '
                       'Edit Mode, Select > All by Trait > Loose Vertices, '
                       'Delete' % (obj.name, loose_verts)
        })
print(json.dumps(findings))
""",

    "ngon_faces": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    ngons = sum(1 for p in obj.data.polygons if len(p.vertices) > 4)
    if ngons:
        findings.append({
            'rule': 'ngon_faces',
            'severity': 'SOFT',
            'object_name': obj.name,
            'message': 'Mesh "%s" has %d n-gon faces (>4 verts) -- may cause '
                       'shading artifacts and export problems. Triangulate: '
                       'select mesh, Edit Mode, Face > Triangulate Faces'
                       % (obj.name, ngons)
        })
print(json.dumps(findings))
""",

    "unapplied_scale": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    scl = obj.scale
    if any(abs(v - 1.0) > 0.001 for v in scl):
        findings.append({
            'rule': 'unapplied_scale',
            'severity': 'SOFT',
            'object_name': obj.name,
            'message': 'Object "%s" has unapplied scale (%.2f, %.2f, %.2f) -- '
                       'normals, physics, and modifiers will behave unexpectedly. '
                       'Apply: select object, Ctrl+A > Scale'
                       % (obj.name, scl.x, scl.y, scl.z)
        })
print(json.dumps(findings))
""",

    "zero_area_faces": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    zero = sum(1 for p in obj.data.polygons if p.area < 1e-8)
    if zero > 0:
        findings.append({
            'rule': 'zero_area_faces',
            'severity': 'SOFT',
            'object_name': obj.name,
            'message': 'Mesh "%s" has %d zero-area faces -- cause shading '
                       'artifacts and NaN normals. Select in Edit Mode: '
                       'Select > All by Trait > Face Area, set Max to 0.0001, '
                       'then delete' % (obj.name, zero)
        })
print(json.dumps(findings))
""",

    # ── SCENE ─────────────────────────────────────────────────────────────

    "no_camera": """
import bpy, json
findings = []
if not any(o.type == 'CAMERA' for o in bpy.data.objects):
    findings.append({
        'rule': 'no_camera',
        'severity': 'SOFT',
        'object_name': '(scene)',
        'message': 'No camera in scene -- renders will fail. '
                   'Add one: bpy.ops.object.camera_add(location=(7, -6, 5))'
    })
print(json.dumps(findings))
""",

    "no_light": """
import bpy, json
findings = []
if not any(o.type == 'LIGHT' for o in bpy.data.objects):
    meshes = sum(1 for o in bpy.data.objects if o.type == 'MESH')
    if meshes:
        findings.append({
            'rule': 'no_light',
            'severity': 'SOFT',
            'object_name': '(scene)',
            'message': 'Scene has %d mesh objects but no lights -- renders '
                       'will be dark. Add a sun: '
                       'bpy.ops.object.light_add(type="SUN")' % meshes
        })
print(json.dumps(findings))
""",

    "no_world_shader": """
import bpy, json
findings = []
scene = bpy.context.scene
world = scene.world
if world is None:
    findings.append({
        'rule': 'no_world_shader',
        'severity': 'SOFT',
        'object_name': '(scene)',
        'message': 'Scene has no World -- background will be solid gray and '
                   'environment lighting will be absent. Assign one: '
                   'bpy.context.scene.world = bpy.data.worlds.new("World")'
    })
elif world.use_nodes:
    bg = None
    for node in world.node_tree.nodes:
        if node.type == 'BACKGROUND':
            bg = node
            break
    if bg and not bg.inputs['Color'].links:
        c = bg.inputs['Color'].default_value
        strength = bg.inputs['Strength'].default_value
        if strength < 0.01:
            findings.append({
                'rule': 'no_world_shader',
                'severity': 'SOFT',
                'object_name': '(scene)',
                'message': 'World background strength is %.3f -- environment '
                           'lighting is effectively off. Set: '
                           'bg_node.inputs["Strength"].default_value = 1.0'
                           % strength
            })
print(json.dumps(findings))
""",

    # ── MODIFIER ──────────────────────────────────────────────────────────

    "subdiv_after_boolean": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    mods = list(obj.modifiers)
    for i, mod in enumerate(mods):
        if mod.type == 'SUBSURF':
            for j in range(i):
                if mods[j].type == 'BOOLEAN':
                    findings.append({
                        'rule': 'subdiv_after_boolean',
                        'severity': 'SOFT',
                        'object_name': obj.name,
                        'message': 'Object "%s" has Subdivision Surface after '
                                   'Boolean -- will produce shading artifacts '
                                   'around cut edges. Move Subdivision before '
                                   'Boolean, or add supporting edge loops around '
                                   'the boolean cut' % obj.name
                    })
                    break
print(json.dumps(findings))
""",

    "boolean_missing_operand": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    for mod in obj.modifiers:
        if mod.type == 'BOOLEAN' and mod.object is None:
            findings.append({
                'rule': 'boolean_missing_operand',
                'severity': 'HARD',
                'object_name': obj.name,
                'message': 'Boolean modifier "%s" on "%s" has no operand object '
                           '-- the modifier does nothing. Set mod.object to a '
                           'mesh object, or remove the modifier'
                           % (mod.name, obj.name)
            })
print(json.dumps(findings))
""",

    "mirror_with_unapplied_origin": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    for mod in obj.modifiers:
        if mod.type != 'MIRROR': continue
        loc = obj.location
        if any(abs(v) > 0.001 for v in loc) and mod.mirror_object is None:
            findings.append({
                'rule': 'mirror_with_unapplied_origin',
                'severity': 'SOFT',
                'object_name': obj.name,
                'message': 'Object "%s" has a Mirror modifier but its origin is '
                           'offset from world center (%.2f, %.2f, %.2f) with no '
                           'mirror object set -- mirror axis will be wrong. '
                           'Either set the origin to geometry center or assign '
                           'a mirror object' % (obj.name, loc.x, loc.y, loc.z)
            })
print(json.dumps(findings))
""",

    "array_zero_offset": """
import bpy, json
findings = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    for mod in obj.modifiers:
        if mod.type != 'ARRAY': continue
        if mod.use_relative_offset:
            d = mod.relative_offset_displace
            if all(abs(v) < 0.001 for v in d):
                findings.append({
                    'rule': 'array_zero_offset',
                    'severity': 'HARD',
                    'object_name': obj.name,
                    'message': 'Array modifier "%s" on "%s" has zero relative '
                               'offset -- all copies will overlap at the same '
                               'position. Set an offset: '
                               'mod.relative_offset_displace = (1, 0, 0)'
                               % (mod.name, obj.name)
                })
print(json.dumps(findings))
""",
}


SCENE_SUMMARY_CODE = """
import bpy, json
summary = {
    'objects': len(bpy.data.objects),
    'meshes': len([o for o in bpy.data.objects if o.type == 'MESH']),
    'lights': len([o for o in bpy.data.objects if o.type == 'LIGHT']),
    'cameras': len([o for o in bpy.data.objects if o.type == 'CAMERA']),
    'materials': len(bpy.data.materials),
    'images': len(bpy.data.images),
    'total_verts': sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH'),
    'total_faces': sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH'),
}
print(json.dumps(summary))
"""


class BlenderConnection:
    """Thin wrapper around the BlenderMCP addon's TCP socket."""

    def __init__(self, host: str = "localhost", port: int = 9876, timeout: float = 10):
        self.host = host
        self.port = port
        self.timeout = timeout

    def execute(self, code: str) -> dict:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        s.settimeout(self.timeout)
        try:
            cmd = json.dumps({"type": "execute_code", "params": {"code": code}})
            s.sendall(cmd.encode())
            chunks = []
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    return json.loads(b"".join(chunks).decode())
                except json.JSONDecodeError:
                    continue
            return json.loads(b"".join(chunks).decode())
        finally:
            s.close()

    def get_scene_info(self) -> dict:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        s.settimeout(self.timeout)
        try:
            cmd = json.dumps({"type": "get_scene_info", "params": {}})
            s.sendall(cmd.encode())
            data = s.recv(65536)
            return json.loads(data.decode())
        finally:
            s.close()


def inspect(conn: BlenderConnection, checks: list[str] | None = None) -> BlenderInspection:
    """Run craft checks against the live Blender scene. Returns findings."""
    check_names = checks or list(CHECKS.keys())
    result = BlenderInspection()

    # Scene summary
    resp = conn.execute(SCENE_SUMMARY_CODE)
    output = resp.get("result", {}).get("result", "")
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                result.scene_summary = json.loads(line)
            except json.JSONDecodeError:
                pass
            break

    # Run each check
    for name in check_names:
        if name not in CHECKS:
            continue
        resp = conn.execute(CHECKS[name])
        output = resp.get("result", {}).get("result", "")
        if resp.get("status") == "error":
            continue
        for line in output.strip().splitlines():
            line = line.strip()
            if not line.startswith("["):
                continue
            try:
                findings = json.loads(line)
                for f in findings:
                    result.findings.append(BlenderFinding(**f))
            except (json.JSONDecodeError, TypeError):
                pass

    return result
