"""Standing-semantics injector — triggers fire on the right calls, once per
session, capped, advisory-only, and toggleable. The reminder TEXT is verified
separately (the verify-x3d-invariants workflow); here we pin the mechanism."""
import os

from techne import semantics
from techne.proxy import TechneProxy, SceneState, _args_changed


def keys(advice):
    return {k for k, _ in advice}


# -- triggers ---------------------------------------------------------------

def test_units_angles_on_rotation_field():
    st = SceneState()
    a = semantics.advise("create_node",
                         {"node_type": "Transform", "fields": {"rotation": [0, 1, 0, 1.57]}}, st)
    assert "units_angles" in keys(a)
    # also on a set_field of a rotation field
    b = semantics.advise("set_field", {"field_name": "orientation", "value": "0 1 0 1"}, st)
    assert "units_angles" in keys(b)


def test_handedness_on_viewpoint_and_transform():
    st = SceneState()
    assert "handedness" in keys(semantics.advise("create_node", {"node_type": "Viewpoint"}, st))
    assert "handedness" in keys(semantics.advise("create_node", {"node_type": "Transform"}, st))


def test_timesensor_routes_on_timer_interp_and_route():
    st = SceneState()
    assert "timesensor_routes" in keys(semantics.advise("create_node", {"node_type": "TimeSensor"}, st))
    assert "timesensor_routes" in keys(
        semantics.advise("create_node", {"node_type": "OrientationInterpolator",
                                          "fields": {"key": [0, 1]}}, st))
    assert "timesensor_routes" in keys(semantics.advise("add_route", {}, st))


def test_hanim_restpose_on_joint():
    st = SceneState()
    assert "hanim_restpose" in keys(semantics.advise("create_node", {"node_type": "HAnimJoint"}, st))


def test_viewpoint_missing_only_when_absent():
    st = SceneState()
    assert "viewpoint_missing" in keys(semantics.advise("create_node", {"node_type": "Shape"}, st))
    st.id_to_type["vp1"] = "Viewpoint"
    assert "viewpoint_missing" not in keys(semantics.advise("create_node", {"node_type": "Shape"}, st))


def test_pbr_lighting_only_when_unlit():
    st = SceneState()
    assert "pbr_lighting" in keys(semantics.advise("create_node", {"node_type": "PhysicalMaterial"}, st))
    st.id_to_type["L"] = "DirectionalLight"
    assert "pbr_lighting" not in keys(semantics.advise("create_node", {"node_type": "PhysicalMaterial"}, st))


def test_no_fire_on_irrelevant_call():
    st = SceneState()
    assert semantics.advise("create_node", {"node_type": "Material"}, st) == []
    assert semantics.advise("validate_semantic", {}, st) == []


def test_texturetransform_rotation_is_scalar_not_sfrotation():
    st = SceneState()
    # TextureTransform.rotation is SFFloat — must NOT get the SFRotation 4-tuple nudge
    assert "units_angles" not in keys(
        semantics.advise("create_node", {"node_type": "TextureTransform",
                                         "fields": {"rotation": 1.57}}, st))
    st.id_to_type["tt"] = "TextureTransform"
    assert "units_angles" not in keys(
        semantics.advise("set_field", {"node_id": "tt", "field_name": "rotation",
                                       "value": 1.57}, st))


def test_reminder_text_is_ascii_and_short():
    for k, v in semantics.REMINDERS.items():
        assert v.isascii(), f"{k} reminder must be ASCII"
        assert len(v) <= 240, f"{k} reminder too long ({len(v)})"


# -- proxy de-dup / cap / advisory / toggle ---------------------------------

def test_once_per_session_dedup():
    p = TechneProxy()
    d1 = p.decide("create_node", {"node_type": "Viewpoint"})
    assert any("right-handed" in r or "right-hand" in r for r in d1.reminders)
    d2 = p.decide("create_node", {"node_type": "Viewpoint"})
    assert d2.reminders == []          # within cooldown -> suppressed


def test_reminder_rearms_after_cooldown():
    p = TechneProxy()
    assert p.decide("create_node", {"node_type": "Viewpoint"}).reminders   # fires
    for _ in range(TechneProxy.REMINDER_COOLDOWN):                         # advance calls
        p.decide("list_nodes", {})
    # past the cooldown the same invariant nudges again (late-session drift)
    assert p.decide("create_node", {"node_type": "Viewpoint"}).reminders


def test_route_tool_still_gets_reminder_via_decide():
    # add_route is a passthrough tool (no adapter) — it must still nudge timer wiring
    p = TechneProxy()
    d = p.decide("add_route", {"from_node": "a", "from_field": "x",
                               "to_node": "b", "to_field": "y"})
    assert not d.blocked
    assert any("ROUTE" in r for r in d.reminders)


def test_rewrote_flag_distinguishes_repair_from_advisory():
    # _args_changed ignores additive normalisation noise...
    assert _args_changed({"node_type": "X"}, {"node_type": "X", "fields": {}}) is False
    assert _args_changed({"p": "a", "container_field": ""},
                         {"p": "a", "container_field": ""}) is False
    # ...but catches a real containerField rewrite
    assert _args_changed({"p": "a", "container_field": ""},
                         {"p": "a", "container_field": "baseTexture"}) is True
    # an EnvironmentLight.global advisory forwards UNCHANGED -> rewrote False (a 'note')
    p = TechneProxy()
    d = p.decide("create_node", {"node_type": "EnvironmentLight", "fields": {}})
    assert not d.blocked and d.notes and d.rewrote is False


def test_cap_two_per_call():
    p = TechneProxy()
    # a Transform with a rotation triggers units_angles + handedness (2), capped at 2
    d = p.decide("create_node", {"node_type": "Transform", "fields": {"rotation": [0, 1, 0, 1.57]}})
    assert len(d.reminders) <= 2


def test_reminders_never_on_a_block():
    p = TechneProxy()
    # set up a known texture node, then a blocked add_child should carry no reminders
    p.state.id_to_type["m"] = "PhysicalMaterial"
    p.state.id_to_type["t"] = "ImageTexture"
    d = p.decide("add_child", {"parent_id": "m", "child_id": "t", "container_field": ""})
    assert d.blocked
    assert d.reminders == []


def test_toggle_off_disables():
    p = TechneProxy(semantics_on=False)
    d = p.decide("create_node", {"node_type": "Viewpoint"})
    assert d.reminders == []


def test_env_toggle_off(monkeypatch):
    monkeypatch.setenv("TECHNE_SEMANTICS", "0")
    p = TechneProxy()
    d = p.decide("create_node", {"node_type": "Viewpoint"})
    assert d.reminders == []
