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
    p.observe_result(d, f"Created {node_type} with ID: {nid}")
    return d, nid


# --- create_node adapters ---------------------------------------------------

def test_envlight_global_advised_not_injected_on_create():
    p = TechneProxy()
    d, _ = _create(p, "EnvironmentLight", {})
    assert not d.blocked
    assert "global" not in d.args["fields"]          # not injected (x3d.py would error)
    assert "envlight_global_set" in d.applied        # but advised
    assert any("global" in n for n in d.notes)


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


def test_unlit_material_normal_texture_is_valid():
    # UnlitMaterial defines both emissiveTexture AND normalTexture — neither blocks.
    p = TechneProxy()
    _, mid = _create(p, "UnlitMaterial", nid="u")
    _, tid = _create(p, "ImageTexture", nid="t")
    for slot in ("emissiveTexture", "normalTexture"):
        d = p.decide("add_child", {"parent_id": mid, "child_id": tid,
                                   "container_field": slot})
        assert not d.blocked, slot


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
    # def_node only commits on confirmed success (observe_result), not at decide()
    dd = p.decide("def_node", {"node_id": "n1", "name": "Hero"})
    assert "Hero" not in p.state.defined_defs            # deferred
    p.observe_result(dd, "Assigned DEF 'Hero' to n1")
    assert "Hero" in p.state.defined_defs
    d2 = p.decide("use_node", {"def_name": "Hero"})
    assert not d2.blocked


def test_failed_def_does_not_satisfy_later_use():
    p = TechneProxy()
    dd = p.decide("def_node", {"node_id": "n1", "name": "Ghost"})
    p.observe_result(dd, "Error: no node with that ID")   # upstream failed
    assert "Ghost" not in p.state.defined_defs
    assert p.decide("use_node", {"def_name": "Ghost"}).blocked


def test_use_reference_inherits_type_so_add_child_is_checked():
    p = TechneProxy()
    _, mid = _create(p, "PhysicalMaterial", nid="m")
    _, tid = _create(p, "ImageTexture", nid="t")
    dd = p.decide("def_node", {"node_id": tid, "name": "Tex"})
    p.observe_result(dd, "Assigned DEF 'Tex' to %s" % tid)
    du = p.decide("use_node", {"def_name": "Tex"})
    p.observe_result(du, "Created USE reference to 'Tex' with ID: use_9")
    assert p.state.id_to_type["use_9"] == "ImageTexture"   # USE inherits type
    # so a placement of the USE'd texture is now actually checked, not skipped
    d = p.decide("add_child", {"parent_id": mid, "child_id": "use_9",
                               "container_field": ""})
    assert d.blocked and "container_field_required" in d.applied


def test_overlapping_creates_register_correctly():
    p = TechneProxy()
    d1 = p.decide("create_node", {"node_type": "Box", "fields": {}})
    d2 = p.decide("create_node", {"node_type": "Cone", "fields": {}})
    # results arrive; each decision carries its own pending (no shared mutable)
    p.observe_result(d2, "Created Cone with ID: c2")
    p.observe_result(d1, "Created Box with ID: b1")
    assert p.state.id_to_type == {"b1": "Box", "c2": "Cone"}


def test_failed_create_is_not_registered():
    p = TechneProxy()
    d = p.decide("create_node", {"node_type": "Box", "fields": {}})
    p.observe_result(d, "Error: invalid node type")
    assert p.state.id_to_type == {}


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


# --- geometry health: coordIndex via proxy ------------------------------------

def test_create_ifs_empty_coordindex_blocks():
    p = TechneProxy()
    d = p.decide("create_node", {"node_type": "IndexedFaceSet",
                                  "fields": {"coordIndex": []}})
    assert d.blocked
    assert "empty_coordindex" in d.applied


def test_create_ifs_valid_coordindex_forwards():
    p = TechneProxy()
    d = p.decide("create_node", {"node_type": "IndexedFaceSet",
                                  "fields": {"coordIndex": [0, 1, 2, -1]}})
    assert not d.blocked


def test_set_field_coordindex_empty_blocks():
    p = TechneProxy()
    _, nid = _create(p, "IndexedFaceSet", nid="ifs_1")
    d = p.decide("set_field", {"node_id": nid, "field_name": "coordIndex",
                                "value": []})
    assert d.blocked
    assert "empty_coordindex" in d.applied


def test_set_field_coordindex_valid_forwards():
    p = TechneProxy()
    _, nid = _create(p, "IndexedFaceSet", nid="ifs_1")
    d = p.decide("set_field", {"node_id": nid, "field_name": "coordIndex",
                                "value": [0, 1, 2, -1, 2, 3, 0, -1]})
    assert not d.blocked


def test_create_ifs_no_separator_warns():
    p = TechneProxy()
    d = p.decide("create_node", {"node_type": "IndexedFaceSet",
                                  "fields": {"coordIndex": list(range(8))}})
    assert not d.blocked
    assert "coordindex_no_separator" in d.applied
