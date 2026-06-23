"""Tests for blender_craft — the Blender scene-graph craft inspector.

These test the inspection logic in isolation (no live Blender needed)
by faking the BlenderConnection to return known check outputs.
"""
import json
import pytest

from techne.blender_craft import (
    BlenderConnection, BlenderFinding, BlenderInspection, inspect, CHECKS,
)


class FakeConnection:
    """Returns canned responses keyed by check-name substring."""

    def __init__(self, check_outputs: dict[str, list[dict]]):
        self._outputs = check_outputs

    def execute(self, code: str) -> dict:
        for name, findings in self._outputs.items():
            if name in code or (name == "_summary" and "summary" in code):
                output = json.dumps(findings)
                return {"status": "success",
                        "result": {"executed": True, "result": output + "\n"}}
        return {"status": "success",
                "result": {"executed": True, "result": "[]\n"}}


# ── structure ─────────────────────────────────────────────────────────────

def test_clean_scene_no_findings():
    result = inspect(FakeConnection({}))
    assert not result.blocked
    assert result.findings == []


def test_notes_format():
    insp = BlenderInspection(findings=[
        BlenderFinding("rule_a", "HARD", "Cube", "fix it"),
        BlenderFinding("rule_b", "SOFT", "Sphere", "maybe fix"),
    ])
    assert insp.notes() == ["[HARD] Cube: fix it", "[SOFT] Sphere: maybe fix"]


def test_blocked_requires_hard():
    soft_only = BlenderInspection(findings=[
        BlenderFinding("x", "SOFT", "A", "msg"),
    ])
    assert not soft_only.blocked

    with_hard = BlenderInspection(findings=[
        BlenderFinding("x", "HARD", "A", "msg"),
    ])
    assert with_hard.blocked


def test_scene_summary_populated():
    summary = {"objects": 3, "meshes": 1, "lights": 1, "cameras": 1,
               "materials": 1, "images": 0, "total_verts": 8, "total_faces": 6}
    result = inspect(FakeConnection({"_summary": summary}))
    assert result.scene_summary.get("objects") == 3
    assert result.scene_summary.get("total_verts") == 8


# ── material checks ──────────────────────────────────────────────────────

def test_unassigned_texture_blocks():
    result = inspect(FakeConnection({
        "unassigned_image_texture": [{
            "rule": "unassigned_image_texture", "severity": "HARD",
            "object_name": "Cube",
            "message": 'Image Texture node in material "WoodMat" is wired '
                       'but has no image',
        }],
    }), checks=["unassigned_image_texture"])
    assert result.blocked
    assert result.findings[0].rule == "unassigned_image_texture"
    assert "WoodMat" in result.findings[0].message


def test_disconnected_material_output():
    result = inspect(FakeConnection({
        "disconnected_material_output": [{
            "rule": "disconnected_material_output", "severity": "HARD",
            "object_name": "Sphere",
            "message": 'Material "BadMat" has nothing connected',
        }],
    }), checks=["disconnected_material_output"])
    assert result.blocked
    assert "BadMat" in result.findings[0].message


def test_wrong_colorspace():
    result = inspect(FakeConnection({
        "wrong_colorspace": [{
            "rule": "wrong_colorspace", "severity": "HARD",
            "object_name": "FloorMat",
            "message": 'Image "normal.png" feeds Normal but color space is sRGB',
        }],
    }), checks=["wrong_colorspace"])
    assert result.blocked
    assert "Normal" in result.findings[0].message


def test_normal_map_missing_node():
    result = inspect(FakeConnection({
        "normal_map_missing_node": [{
            "rule": "normal_map_missing_node", "severity": "HARD",
            "object_name": "WallMat",
            "message": 'Image Texture wired directly to Normal input',
        }],
    }), checks=["normal_map_missing_node"])
    assert result.blocked


def test_alpha_no_blend_mode():
    result = inspect(FakeConnection({
        "alpha_no_blend_mode": [{
            "rule": "alpha_no_blend_mode", "severity": "HARD",
            "object_name": "Glass",
            "message": 'Material "GlassMat" has Alpha=0.30 but blend_method '
                       'is OPAQUE',
        }],
    }), checks=["alpha_no_blend_mode"])
    assert result.blocked
    assert "OPAQUE" in result.findings[0].message


def test_missing_uv_for_texture():
    result = inspect(FakeConnection({
        "missing_uv_for_texture": [{
            "rule": "missing_uv_for_texture", "severity": "HARD",
            "object_name": "Rock",
            "message": 'Object "Rock" has a textured material but no UV map',
        }],
    }), checks=["missing_uv_for_texture"])
    assert result.blocked


# ── geometry checks ───────────────────────────────────────────────────────

def test_empty_mesh():
    result = inspect(FakeConnection({
        "empty_mesh": [{
            "rule": "empty_mesh", "severity": "HARD",
            "object_name": "Ghost",
            "message": 'Mesh "Ghost" has 0 vertices',
        }],
    }), checks=["empty_mesh"])
    assert result.blocked


def test_flipped_normals():
    result = inspect(FakeConnection({
        "flipped_normals": [{
            "rule": "flipped_normals", "severity": "HARD",
            "object_name": "Sphere",
            "message": 'Mesh "Sphere" has 512/512 faces with inward-pointing '
                       'normals',
        }],
    }), checks=["flipped_normals"])
    assert result.blocked
    assert "inward" in result.findings[0].message


def test_non_manifold_soft():
    result = inspect(FakeConnection({
        "non_manifold": [{
            "rule": "non_manifold", "severity": "SOFT",
            "object_name": "Plane",
            "message": 'Mesh "Plane" has 4 non-manifold edges',
        }],
    }), checks=["non_manifold"])
    assert not result.blocked
    assert len(result.findings) == 1


def test_ngon_faces_soft():
    result = inspect(FakeConnection({
        "ngon_faces": [{
            "rule": "ngon_faces", "severity": "SOFT",
            "object_name": "Cone",
            "message": 'Mesh "Cone" has 1 n-gon faces',
        }],
    }), checks=["ngon_faces"])
    assert not result.blocked


def test_unapplied_scale():
    result = inspect(FakeConnection({
        "unapplied_scale": [{
            "rule": "unapplied_scale", "severity": "SOFT",
            "object_name": "Cube",
            "message": 'Object "Cube" has unapplied scale (2.00, 2.00, 2.00)',
        }],
    }), checks=["unapplied_scale"])
    assert not result.blocked


def test_zero_area_faces():
    result = inspect(FakeConnection({
        "zero_area_faces": [{
            "rule": "zero_area_faces", "severity": "SOFT",
            "object_name": "Mesh",
            "message": 'Mesh "Mesh" has 3 zero-area faces',
        }],
    }), checks=["zero_area_faces"])
    assert not result.blocked


# ── scene checks ──────────────────────────────────────────────────────────

def test_no_camera():
    result = inspect(FakeConnection({
        "no_camera": [{
            "rule": "no_camera", "severity": "SOFT",
            "object_name": "(scene)", "message": "No camera in scene",
        }],
    }), checks=["no_camera"])
    assert not result.blocked
    assert result.findings[0].severity == "SOFT"


def test_no_light():
    result = inspect(FakeConnection({
        "no_light": [{
            "rule": "no_light", "severity": "SOFT",
            "object_name": "(scene)", "message": "no lights",
        }],
    }), checks=["no_light"])
    assert not result.blocked


def test_no_world_shader():
    result = inspect(FakeConnection({
        "no_world_shader": [{
            "rule": "no_world_shader", "severity": "SOFT",
            "object_name": "(scene)",
            "message": "Scene has no World",
        }],
    }), checks=["no_world_shader"])
    assert not result.blocked


# ── modifier checks ──────────────────────────────────────────────────────

def test_subdiv_after_boolean():
    result = inspect(FakeConnection({
        "subdiv_after_boolean": [{
            "rule": "subdiv_after_boolean", "severity": "SOFT",
            "object_name": "BoolTarget",
            "message": 'Object "BoolTarget" has Subdivision after Boolean',
        }],
    }), checks=["subdiv_after_boolean"])
    assert not result.blocked


def test_boolean_missing_operand():
    result = inspect(FakeConnection({
        "boolean_missing_operand": [{
            "rule": "boolean_missing_operand", "severity": "HARD",
            "object_name": "Cube",
            "message": 'Boolean modifier has no operand object',
        }],
    }), checks=["boolean_missing_operand"])
    assert result.blocked


def test_mirror_with_unapplied_origin():
    result = inspect(FakeConnection({
        "mirror_with_unapplied_origin": [{
            "rule": "mirror_with_unapplied_origin", "severity": "SOFT",
            "object_name": "HalfArch",
            "message": 'Object "HalfArch" has a Mirror modifier but origin is '
                       'offset',
        }],
    }), checks=["mirror_with_unapplied_origin"])
    assert not result.blocked


def test_array_zero_offset():
    result = inspect(FakeConnection({
        "array_zero_offset": [{
            "rule": "array_zero_offset", "severity": "HARD",
            "object_name": "Fence",
            "message": 'Array modifier has zero relative offset',
        }],
    }), checks=["array_zero_offset"])
    assert result.blocked


# ── catalog completeness ─────────────────────────────────────────────────

def test_checks_catalog_has_all_entries():
    expected = {
        # material
        "unassigned_image_texture", "disconnected_material_output",
        "wrong_colorspace", "normal_map_missing_node",
        "alpha_no_blend_mode", "missing_uv_for_texture",
        # geometry
        "empty_mesh", "flipped_normals", "non_manifold",
        "ngon_faces", "unapplied_scale", "zero_area_faces",
        # scene
        "no_camera", "no_light", "no_world_shader",
        # modifier
        "subdiv_after_boolean", "boolean_missing_operand",
        "mirror_with_unapplied_origin", "array_zero_offset",
    }
    assert expected == set(CHECKS.keys())


def test_multiple_findings_mixed_severity():
    result = inspect(FakeConnection({
        "unassigned_image_texture": [{
            "rule": "unassigned_image_texture", "severity": "HARD",
            "object_name": "Plane", "message": "no image assigned",
        }],
        "no_light": [{
            "rule": "no_light", "severity": "SOFT",
            "object_name": "(scene)", "message": "no lights",
        }],
    }), checks=["unassigned_image_texture", "no_light"])
    assert result.blocked
    assert len(result.findings) == 2
    notes = result.notes()
    assert any("[HARD]" in n for n in notes)
    assert any("[SOFT]" in n for n in notes)
