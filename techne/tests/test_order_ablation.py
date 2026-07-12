"""The order-ablation harness itself — the part that must not lie.

The experiment's whole value is that a FREE verdict means "renders identically"
and a SILENT verdict means "renders wrong". Both depend on `violate()` producing a
program that is (a) actually reordered and (b) still legal. If it quietly returned
the original program, every edge would come back FREE and the result would be a
fabrication. So: test the mover, not the servers.
"""
from __future__ import annotations

import json

from eval.order_ablation import (PROGRAMS, Program, Call, violate, _resolve)


def _tags(calls):
    return [c.tag for c in calls]


def test_violate_actually_moves_the_step():
    prog = [p for p in PROGRAMS if p().name == "hanim-box"][0]()
    out = violate(prog, "sh_ap", "sh_bx")
    assert out is not None
    before, after = _tags(prog.calls), _tags(out)
    assert before != after                                  # something moved
    assert after.index("sh_bx") < after.index("sh_ap")      # and the RIGHT way
    assert sorted(before) == sorted(after)                  # nothing lost or duplicated


def test_violate_refuses_a_move_that_breaks_dataflow():
    """Moving a call before the call that mints the id it references is not an
    ordering violation — it is nonsense. It must be reported as DATAFLOW, never
    silently executed."""
    prog = [p for p in PROGRAMS if p().name == "hanim-box"][0]()
    # sh_bx references $bx, produced by mk_bx. Moving it before mk_bx is impossible.
    assert violate(prog, "mk_bx", "sh_bx") is None


def test_violate_is_a_noop_when_b_already_precedes_a():
    prog = [p for p in PROGRAMS if p().name == "hanim-box"][0]()
    assert violate(prog, "sh_bx", "sh_ap") is None          # already in that order


def test_every_declared_edge_is_resolvable():
    """An edge naming a tag that does not exist would silently never be tested."""
    for make in PROGRAMS:
        prog = make()
        tags = set(_tags(prog.calls))
        for a, b, _q in prog.edges:
            assert a in tags, f"{prog.name}: unknown tag {a}"
            assert b in tags, f"{prog.name}: unknown tag {b}"


def test_no_program_references_a_scene_root_id():
    """There is no scene-root node id: a node with no parent IS a root
    (src/x3d_utils/scene.py). add_child(parent_id='scene') always errors, and an
    earlier version of this harness did it in every variant — which made every
    edge look LOUD for a reason that had nothing to do with ordering."""
    for make in PROGRAMS:
        for c in make().calls:
            assert c.args.get("parent_id") != "scene", make().name


def test_add_route_passes_node_ids_not_def_names():
    """add_route takes node IDs and resolves each node's DEF name at serialization
    ('Source node has no DEF name'). Passing DEF names made the BASELINE fail, so
    every variant looked LOUD."""
    for make in PROGRAMS:
        for c in make().calls:
            if c.tool == "add_route":
                for k in ("from_node", "to_node"):
                    assert c.args[k].startswith("$"), f"{c.tag}: {k} must be a node id"


def test_resolve_substitutes_ids():
    ids = {"a": "uuid-a"}
    assert _resolve({"parent_id": "$a", "n": 1}, ids) == {"parent_id": "uuid-a", "n": 1}
    assert _resolve("$missing", ids) == "$missing"          # left visible, not blanked
