"""Profiles: CORRECTNESS always on, COHERENCE default, PROVENANCE opt-in. The split
that keeps Technē universally useful (no arbitrary policy gate by default)."""
from techne.config import Config
from techne.proxy import TechneProxy


def test_default_is_core_plus_coherence_no_provenance():
    c = Config.from_env({})
    assert c.coherence and not c.provenance and c.provenance_level == 1


def test_legacy_semantics_flag_still_disables_coherence():
    assert not Config.from_env({"TECHNE_SEMANTICS": "0"}).coherence


def test_explicit_profile_core_only_drops_coherence():
    c = Config.from_env({"TECHNE_PROFILE": "core"})
    assert not c.coherence and not c.provenance


def test_profile_opts_into_provenance_with_knobs():
    c = Config.from_env({"TECHNE_PROFILE": "core,coherence,provenance",
                         "TECHNE_PROVENANCE_LEVEL": "2",
                         "TECHNE_ASSET_LEDGER": "/tmp/ledger.json",
                         "TECHNE_STRICT": "1"})
    assert c.coherence and c.provenance and c.provenance_level == 2
    assert c.ledger_path == "/tmp/ledger.json" and c.strict


def test_level_is_clamped_1_to_3():
    assert Config.from_env({"TECHNE_PROVENANCE_LEVEL": "9"}).provenance_level == 3
    assert Config.from_env({"TECHNE_PROVENANCE_LEVEL": "0"}).provenance_level == 1


def test_proxy_core_only_silences_coherence_reminders():
    p = TechneProxy(config=Config.from_env({"TECHNE_PROFILE": "core"}))
    assert p.decide("create_node", {"node_type": "Viewpoint"}).reminders == []
    # but CORE correctness still fires regardless of profile
    p.state.id_to_type.update({"m": "PhysicalMaterial", "t": "ImageTexture"})
    assert p.decide("add_child", {"parent_id": "m", "child_id": "t",
                                  "container_field": ""}).blocked


def test_proxy_coherence_profile_restores_reminders():
    p = TechneProxy(config=Config.from_env({"TECHNE_PROFILE": "core,coherence"}))
    assert p.decide("create_node", {"node_type": "Viewpoint"}).reminders


def test_differential_is_off_by_default():
    # N+1 renders per check — an opt-in for the pre-commitment moment, never ambient
    c = Config.from_env({})
    assert not c.differential and c.differential_max_nodes == 0


def test_differential_flag_opts_in_even_alongside_a_profile():
    assert Config.from_env({"TECHNE_DIFFERENTIAL": "1"}).differential
    # both switches are pure opt-ins; a profile has no default-on to override
    assert Config.from_env({"TECHNE_PROFILE": "core",
                            "TECHNE_DIFFERENTIAL": "1"}).differential


def test_differential_profile_group_opts_in_with_budget_knob():
    c = Config.from_env({"TECHNE_PROFILE": "core,differential",
                         "TECHNE_DIFFERENTIAL_MAX_NODES": "3"})
    assert c.differential and c.differential_max_nodes == 3
    # a garbage budget degrades to "module default", never to a crash
    assert Config.from_env(
        {"TECHNE_DIFFERENTIAL_MAX_NODES": "lots"}).differential_max_nodes == 0
