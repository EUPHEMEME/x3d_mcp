"""Tier-1 integration: Technē's catalog mirrors the server's validate_semantic.

Covers the newly-enforced per-call checks (duplicate-def, ROUTE-needs-DEF, the
richer interpolator arity matching semantic.py), the serialization-layer
EnvironmentLight.global re-assertion, and the catalog/coverage map."""
from techne import rules
from techne.craft import (check_interpolator, check_duplicate_def,
                          check_route_defs, reassert_envlight_global)
from techne.proxy import TechneProxy


# -- catalog coverage -------------------------------------------------------

def test_every_catalog_rule_is_scoped():
    # every rule is classified as per-call (Technē enforces) or whole-scene
    # (deferred to the upstream validate_semantic) — no rule left unclassified.
    assert set(rules.CATALOG) == (rules.PER_CALL | rules.WHOLE_SCENE)
    assert not (rules.PER_CALL & rules.WHOLE_SCENE)


def test_interp_tables_match_semantic_py():
    # the arity table is the server's, verbatim (fixed-arity + variable base)
    assert rules.INTERP_ARITY["OrientationInterpolator"] == 4
    assert rules.INTERP_ARITY["SquadOrientationInterpolator"] == 4
    assert rules.INTERP_ARITY["CoordinateInterpolator"] is None
    assert rules.INTERP_BASE["CoordinateInterpolator2D"] == 2


# -- richer interpolator arity ----------------------------------------------

def test_squad_orientation_ok_and_mismatch():
    ok = check_interpolator("SquadOrientationInterpolator", [0.0, 1.0],
                            [0, 0, 1, 0, 0, 1, 0, 0], None, {})   # 2x4
    assert not ok.blocked
    bad = check_interpolator("SquadOrientationInterpolator", [0.0, 1.0],
                             [0, 0, 1, 0, 0, 1], None, {})        # 2x3
    assert bad.blocked and "interp_lengths_match" in bad.applied


def test_spline_scalar_non_divisible_blocks():
    bad = check_interpolator("SplineScalarInterpolator", [0.0, 1.0],
                             [0, 1, 2], None, {})                 # 3 not divisible by 2
    assert bad.blocked


def test_coordinate_interpolator_2d_base_two():
    ok = check_interpolator("CoordinateInterpolator2D", [0.0, 1.0],
                            [0, 0, 1, 1, 2, 2, 3, 3], None, {})   # per key 4 = mult of 2
    assert not ok.blocked
    bad = check_interpolator("CoordinateInterpolator2D", [0.0, 1.0],
                             [0, 0, 1, 2, 2, 3], None, {})        # per key 3, not mult of 2
    assert bad.blocked


def test_unknown_interpolator_no_fire():
    assert not check_interpolator("NotAnInterpolator", [0.0, 1.0], [0, 1], None, {}).blocked


# -- duplicate-def ----------------------------------------------------------

def test_check_duplicate_def():
    assert check_duplicate_def("Hero", {"Hero", "X"}, {}).blocked
    assert not check_duplicate_def("Hero", {"X", "Y"}, {}).blocked


def test_proxy_def_node_duplicate_blocks():
    p = TechneProxy()
    d = p.decide("def_node", {"node_id": "n1", "name": "Hero"})
    p.observe_result(d, "Assigned DEF 'Hero' to n1")
    d2 = p.decide("def_node", {"node_id": "n2", "name": "Hero"})
    assert d2.blocked and "duplicate_def" in d2.applied


def test_proxy_redef_frees_old_name():
    p = TechneProxy()
    p.observe_result(p.decide("def_node", {"node_id": "n1", "name": "Hero"}),
                     "Assigned DEF 'Hero' to n1")
    # re-DEF node n1 to a new name: 'Hero' is freed (mirrors scene._def_to_id)
    p.observe_result(p.decide("def_node", {"node_id": "n1", "name": "Champ"}),
                     "Assigned DEF 'Champ' to n1")
    assert "Hero" not in p.state.defined_defs and "Champ" in p.state.defined_defs
    # so reusing 'Hero' on another node is not a false duplicate
    assert not p.decide("def_node", {"node_id": "n2", "name": "Hero"}).blocked


# -- ROUTE needs DEFs -------------------------------------------------------

def test_check_route_defs():
    assert check_route_defs("a", "b", {"a": "A"}, {}).blocked         # b has no DEF
    assert not check_route_defs("a", "b", {"a": "A", "b": "B"}, {}).blocked


def test_proxy_add_route_requires_defs():
    p = TechneProxy()
    d = p.decide("add_route", {"from_node": "n1", "from_field": "fraction_changed",
                               "to_node": "n2", "to_field": "set_fraction"})
    assert d.blocked and "route_no_def" in d.applied
    for nid, name in (("n1", "Timer"), ("n2", "Interp")):
        p.observe_result(p.decide("def_node", {"node_id": nid, "name": name}),
                         f"Assigned DEF '{name}' to {nid}")
    d2 = p.decide("add_route", {"from_node": "n1", "from_field": "fraction_changed",
                                "to_node": "n2", "to_field": "set_fraction"})
    assert not d2.blocked


# -- serialization-layer EnvironmentLight.global ----------------------------

def test_reassert_envlight_global_injects_and_is_idempotent():
    out = reassert_envlight_global("<EnvironmentLight diffuseColor='1 1 1'/>")
    assert "global='true'" in out
    assert reassert_envlight_global(out) == out            # idempotent


def test_reassert_leaves_explicit_global_and_pointlight_alone():
    assert reassert_envlight_global("<EnvironmentLight global='false'/>") == \
        "<EnvironmentLight global='false'/>"
    multi = reassert_envlight_global("<EnvironmentLight/><PointLight/><EnvironmentLight/>")
    assert multi.count("global='true'") == 2 and "<PointLight/>" in multi


def test_reassert_handles_open_tag():
    out = reassert_envlight_global(
        "<EnvironmentLight rotation='0 1 0 0'></EnvironmentLight>")
    assert "global='true'" in out and out.endswith("</EnvironmentLight>")
