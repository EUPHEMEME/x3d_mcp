"""Point-1 instrumentation — trace logging records verb order, decisions,
state mutations, and render results so cross-call ordering constraints can
be discovered empirically."""
import json
import os
import tempfile

from techne.proxy import TechneProxy, Decision
from techne.config import Config
from techne.trace import SessionTrace, TraceEntry


def _traced_proxy(tmp):
    cfg = Config(instrumentation=True, trace_dir=tmp)
    return TechneProxy(config=cfg)


def _create(p, node_type, fields=None, nid=None):
    d = p.decide("create_node", {"node_type": node_type, "fields": fields or {}})
    nid = nid or (node_type.lower() + "_1")
    p.observe_result(d, f"Created {node_type} with ID: {nid}")
    return d, nid


# -- trace records decisions ---------------------------------------------------

def test_trace_records_decisions():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box")
        _create(p, "PhysicalMaterial")
        assert p.trace is not None
        assert len(p.trace.entries) == 2
        assert p.trace.entries[0].tool == "create_node"
        assert p.trace.entries[0].node_type == "Box"
        assert p.trace.entries[1].node_type == "PhysicalMaterial"


def test_trace_records_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        d = p.decide("create_node", {"node_type": "OrientationInterpolator",
                      "fields": {"key": [0, 1], "keyValue": [0, 0, 1, 0, 0, 1]}})
        assert d.blocked
        assert p.trace.entries[0].blocked
        assert "interp_lengths_match" in p.trace.entries[0].applied


def test_trace_records_mutations():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box", nid="b1")
        entry = p.trace.entries[0]
        assert entry.state_mutation is not None
        assert entry.state_mutation["create"] == "Box"
        assert entry.state_mutation["id"] == "b1"


def test_trace_records_def_mutation():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box", nid="b1")
        d = p.decide("def_node", {"node_id": "b1", "name": "MyBox"})
        p.observe_result(d, "Assigned DEF 'MyBox' to b1")
        entry = p.trace.entries[1]
        assert entry.state_mutation["def"] == "MyBox"


def test_trace_records_render():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box")
        p.decide("render_image", {"path": "scene.x3d"})
        p.record_render(42.5, True)
        renders = [e for e in p.trace.entries if e.render]
        assert len(renders) == 1
        assert renders[0].render["non_blank"] is True
        assert renders[0].render["stddev"] == 42.5


# -- verb sequence and clean session ------------------------------------------

def test_verb_sequence():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box")
        _create(p, "Sphere")
        p.decide("render_image", {"path": "scene.x3d"})
        seq = p.trace.verb_sequence()
        assert seq == ["create_node", "create_node", "render_image"]


def test_clean_session_no_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box")
        p.decide("render_image", {"path": "scene.x3d"})
        p.record_render(50.0, True)
        assert p.trace.clean is True


def test_unclean_session_with_block():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        p.decide("create_node", {"node_type": "OrientationInterpolator",
                  "fields": {"key": [0, 1], "keyValue": [0, 0, 1, 0, 0, 1]}})
        assert p.trace.clean is False


def test_unclean_session_blank_render():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box")
        p.decide("render_image", {"path": "scene.x3d"})
        p.record_render(1.2, False)
        assert p.trace.clean is False


# -- summary and flush --------------------------------------------------------

def test_summary():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box")
        _create(p, "PhysicalMaterial")
        p.decide("render_image", {"path": "scene.x3d"})
        p.record_render(50.0, True)
        s = p.trace.summary()
        assert s["n_calls"] == 3
        assert s["n_blocks"] == 0
        assert s["n_renders"] == 1
        assert s["clean"] is True
        assert s["verb_sequence"] == ["create_node", "create_node", "render_image"]


def test_flush_writes_jsonl():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box", nid="b1")
        _create(p, "Sphere", nid="s1")
        path = p.trace.flush()
        assert path is not None
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 3  # 2 entries + 1 summary
        entry = json.loads(lines[0])
        assert entry["tool"] == "create_node"
        assert entry["node_type"] == "Box"
        summary = json.loads(lines[2])
        assert "_summary" in summary
        assert summary["_summary"]["n_calls"] == 2


def test_close_writes_and_returns_path():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        _create(p, "Box")
        path = p.close()
        assert path is not None
        assert path.exists()
        assert path.suffix == ".jsonl"


def test_no_trace_when_disabled():
    p = TechneProxy()
    assert p.trace is None
    _create(p, "Box")  # should not crash


# -- passthrough tools are traced too -----------------------------------------

def test_passthrough_traced():
    with tempfile.TemporaryDirectory() as tmp:
        p = _traced_proxy(tmp)
        p.decide("render_image", {"path": "scene.x3d"})
        assert len(p.trace.entries) == 1
        assert p.trace.entries[0].tool == "render_image"
        assert p.trace.entries[0].action == "forward"


# -- config knobs -------------------------------------------------------------

def test_env_techne_trace_enables(monkeypatch):
    monkeypatch.setenv("TECHNE_TRACE", "1")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TECHNE_TRACE_DIR", tmp)
        p = TechneProxy()
        assert p.trace is not None


def test_profile_instrumentation_enables(monkeypatch):
    monkeypatch.setenv("TECHNE_PROFILE", "core,instrumentation")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TECHNE_TRACE_DIR", tmp)
        p = TechneProxy()
        assert p.trace is not None
