"""Tests for the Technē proxy core: state tracking, the per-tool adapters, and
the decide/observe split. The create_node -> observe_result -> add_child flow is
the crux, because add_child references nodes by id."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from techne.proxy import TechneProxy             # noqa: E402
from techne import repair                        # noqa: E402


def _create(p, node_type, fields=None, nid=None):
    """Helper: run create_node through decide + observe with a fake server reply."""
    d = p.decide("create_node", {"node_type": node_type, "fields": fields or {}})
    nid = nid or (node_type.lower() + "_1")
    p.observe_result("create_node", d.args, f"Created {node_type} with ID: {nid}")
    return d, nid


# --- create_node adapters ---------------------------------------------------

def test_envlight_global_repaired_on_create():
    p = TechneProxy()
    d, _ = _create(p, "EnvironmentLight", {})
    assert not d.blocked
    assert d.args["fields"]["global"] is True
    assert "envlight_global_set" in d.applied


def test_interpolator_mismatch_blocks_on_create():
    p = TechneProxy()
    d = p.decide("create_node", {"node_type": "OrientationInterpolator",
                 "fields": {"key": [0, 1], "keyValue": [0, 0, 1, 0, 0, 1]}})
    assert d.blocked
    assert "interp_lengths_match" in d.applied
    msg = p.correction_message(d)
    assert "keyValue" in msg


def test_create_registers_id_to_type():
    p = TechneProxy()
    _create(p, "PhysicalMaterial", {}, nid="mat_7")
    assert p.state.id_to_type["mat_7"] == "PhysicalMaterial"


# --- add_child placement ----------------------------------------------------

def test_add_segment_to_humanoid_single_slot_is_repaired():
    p = TechneProxy()
    _, hid = _create(p, "HAnimHumanoid", nid="h")
    _, sid = _create(p, "HAnimSegment", nid="s")
    d = p.decide("add_child", {"parent_id": hid, "child_id": sid,
                               "container_field": ""})
    assert not d.blocked
    assert d.args["container_field"] == "segments"   # one legal slot -> repaired


def test_add_texture_to_pbr_multi_slot_blocks():
    p = TechneProxy()
    _, mid = _create(p, "PhysicalMaterial", nid="m")
    _, tid = _create(p, "ImageTexture", nid="t")
    d = p.decide("add_child", {"parent_id": mid, "child_id": tid,
                               "container_field": ""})
    assert d.blocked                                  # baseTexture vs normal -> can't guess
    assert "container_field_required" in d.applied
    assert "baseTexture" in p.correction_message(d)


def test_add_texture_with_valid_slot_forwards():
    p = TechneProxy()
    _, mid = _create(p, "PhysicalMaterial", nid="m")
    _, tid = _create(p, "ImageTexture", nid="t")
    d = p.decide("add_child", {"parent_id": mid, "child_id": tid,
                               "container_field": "baseTexture"})
    assert not d.blocked


def test_add_texture_with_wrong_slot_blocks():
    p = TechneProxy()
    _, mid = _create(p, "PhysicalMaterial", nid="m")
    _, tid = _create(p, "ImageTexture", nid="t")
    d = p.decide("add_child", {"parent_id": mid, "child_id": tid,
                               "container_field": "texture"})
    assert d.blocked
    assert "container_field_invalid_slot" in d.applied


def test_add_child_unknown_type_passes_with_note():
    p = TechneProxy()
    d = p.decide("add_child", {"parent_id": "x", "child_id": "y",
                               "container_field": ""})
    assert not d.blocked
    assert d.notes and "could not check" in d.notes[0]


# --- def / use --------------------------------------------------------------

def test_use_before_def_blocks_then_passes():
    p = TechneProxy()
    d = p.decide("use_node", {"def_name": "Hero"})
    assert d.blocked
    p.decide("def_node", {"node_id": "n1", "name": "Hero"})
    d2 = p.decide("use_node", {"def_name": "Hero"})
    assert not d2.blocked


# --- opt-in passthrough -----------------------------------------------------

def test_unknown_tool_passes_through():
    p = TechneProxy()
    d = p.decide("render_image", {"path": "scene.x3d"})
    assert not d.blocked and d.action == "forward"


# --- SAP repair -------------------------------------------------------------

def test_sap_repair_unwraps_stringified_fields():
    out = repair.sap_repair({"node_type": "EnvironmentLight",
                             "fields": '{"global": "true"}'})
    assert out["fields"] == {"global": True}


def test_sap_repair_strips_markdown_and_preamble():
    out = repair.sap_repair('Here you go:\n```json\n{"node_type": "Box"}\n```')
    assert out == {"node_type": "Box"}


def test_sap_repair_never_raises():
    assert repair.sap_repair("not json at all") == {}
    assert repair.sap_repair(None) == {}
