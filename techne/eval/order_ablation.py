#!/usr/bin/env python3
"""Point-1, by ablation: which cross-call ordering constraints are REAL?

The paper defers the cross-call automaton and says why (§4.4): open-ended
authoring should resist a straitjacket, the likely truth is "a partial order --
a few hard edges in a large open space", and so the honest next step is to
instrument first and let usage decide, rather than legislating a total order in
advance.

`analyze_traces.py` does that by OBSERVATION: collect sessions, correlate verb
bigrams with clean renders. The trouble is that observation needs a large corpus
and, even then, only tells you what models happen to DO -- not what X3D
REQUIRES. A bigram that never appears may be forbidden, or merely unfashionable.

This does it by EXPERIMENT instead. Take an authoring program that renders. For
each candidate ordering edge A->B, emit the program with the edge VIOLATED (B
moved before A), run it through the bare x3d_mcp server, and render the result.
Then the edge is classified by what actually happens:

    LOUD    the server refuses -- an error the model already sees. No rule needed:
            the transport is the enforcement.
    SILENT  the calls all succeed, the XSD is happy, and the scene renders WRONG
            or BLANK. This is the entire Technē thesis, and each one is a
            candidate rule.
    FREE    the scene renders identically. The edge is folklore. Legislating it
            would be a false positive -- exactly the straitjacket §4.4 refuses.

The output is the partial order, measured: |HARD| edges worth an automaton, and
|FREE| edges that must stay unconstrained.

    ../.venv/bin/python -m techne.eval.order_ablation
"""
from __future__ import annotations

import asyncio
import functools
import http.server
import json
import os
import re
import socketserver
import sys
import threading
from dataclasses import dataclass, field

REPO = os.environ.get("X3D_MCP_REPO", "/Users/alexander/x3d_mcp")
PY = f"{REPO}/.venv/bin/python"
OUT = os.environ.get("ABLATION_OUT", "/tmp/techne_ablation")
PORT = int(os.environ.get("ABLATION_PORT", "8891"))

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


# --- an authoring program as reorderable steps ------------------------------

@dataclass
class Call:
    """One tool call. `out` names the node id it produces, so later steps can
    refer to it symbolically and we can move steps around without breaking ids."""
    tool: str
    args: dict
    out: str | None = None
    tag: str = ""                 # a short label, so edges can name their steps


@dataclass
class Program:
    name: str
    what: str                     # what a correct render looks like
    calls: list[Call]
    edges: list[tuple[str, str, str]] = field(default_factory=list)
    # (tag_a, tag_b, question): the claim is "a must precede b". We test it by
    # moving b before a and seeing whether anything actually breaks.


def _resolve(v, ids: dict):
    if isinstance(v, str) and v.startswith("$"):
        return ids.get(v[1:], v)
    if isinstance(v, dict):
        return {k: _resolve(x, ids) for k, x in v.items()}
    if isinstance(v, list):
        return [_resolve(x, ids) for x in v]
    return v


def violate(prog: Program, a: str, b: str) -> list[Call] | None:
    """Move step `b` to just before step `a`, violating the claim a->b.

    Returns None when the move is structurally impossible -- i.e. b would then
    precede a call that produces a node id b references. Those are not ordering
    *conventions* at all, they are dataflow, and the transport enforces them; the
    interesting edges are the ones where the move IS possible.
    """
    tags = [c.tag for c in prog.calls]
    if a not in tags or b not in tags:
        return None
    ia, ib = tags.index(a), tags.index(b)
    if ib < ia:
        return None
    moved = prog.calls[ib]
    rest = prog.calls[:ib] + prog.calls[ib + 1:]
    new = rest[:ia] + [moved] + rest[ia:]

    # dataflow check: every $ref the moved call makes must still be produced earlier
    produced: set[str] = set()
    for c in new:
        for ref in re.findall(r"\$(\w+)", json.dumps(c.args)):
            if ref not in produced:
                return None
        if c.out:
            produced.add(c.out)
    return new


# --- the programs -----------------------------------------------------------

def hanim_box() -> Program:
    c = [
        Call("create_scene", {"description": "ablation", "profile": "Interactive"}, tag="scene"),
        Call("create_node", {"node_type": "Viewpoint", "fields": {"position": [0, 0, 4]}},
             out="vp", tag="mk_vp"),
        Call("create_node", {"node_type": "HAnimHumanoid",
                             "fields": {"name": "t", "version": "2.0"}}, out="h", tag="mk_h"),
        Call("create_node", {"node_type": "HAnimJoint",
                             "fields": {"name": "humanoid_root", "center": [0, 0, 0]}},
             out="j", tag="mk_j"),
        Call("create_node", {"node_type": "HAnimSegment", "fields": {"name": "sacrum"}},
             out="sg", tag="mk_sg"),
        Call("create_node", {"node_type": "Shape"}, out="sh", tag="mk_sh"),
        Call("create_node", {"node_type": "Appearance"}, out="ap", tag="mk_ap"),
        Call("create_node", {"node_type": "Material", "fields": {"diffuseColor": [1, 1, 1]}},
             out="mt", tag="mk_mt"),
        Call("create_node", {"node_type": "Box", "fields": {"size": [1.4, 1.4, 1.4]}},
             out="bx", tag="mk_bx"),
        Call("add_child", {"parent_id": "$ap", "child_id": "$mt",
                           "container_field": "material"}, tag="ap_mt"),
        Call("add_child", {"parent_id": "$sh", "child_id": "$ap",
                           "container_field": "appearance"}, tag="sh_ap"),
        Call("add_child", {"parent_id": "$sh", "child_id": "$bx",
                           "container_field": "geometry"}, tag="sh_bx"),
        Call("add_child", {"parent_id": "$sg", "child_id": "$sh",
                           "container_field": "children"}, tag="sg_sh"),
        Call("add_child", {"parent_id": "$j", "child_id": "$sg",
                           "container_field": "children"}, tag="j_sg"),
        Call("add_child", {"parent_id": "$h", "child_id": "$j",
                           "container_field": "skeleton"}, tag="h_j"),
    ]
    return Program(
        "hanim-box", "a white box, articulated as an HAnim skeleton", c,
        edges=[
            ("sh_ap", "sh_bx", "must a Shape's appearance be attached before its geometry?"),
            ("ap_mt", "sh_ap", "must a Material be in its Appearance before the Appearance is attached?"),
            ("sg_sh", "j_sg", "must a Segment be filled before it is joined to its Joint?"),
            ("mk_vp", "mk_h", "must the Viewpoint be created before the geometry, to bind?"),
            ("mk_bx", "sh_bx", "must geometry exist before it is attached? (dataflow)"),
        ])


def routed_animation() -> Program:
    c = [
        Call("create_scene", {"description": "ablation", "profile": "Interactive"}, tag="scene"),
        Call("create_node", {"node_type": "Viewpoint", "fields": {"position": [0, 0, 6]}},
             out="vp", tag="mk_vp"),
        Call("create_node", {"node_type": "Transform"}, out="tf", tag="mk_tf"),
        Call("def_node", {"node_id": "$tf", "name": "Spinner"}, tag="def_tf"),
        Call("create_node", {"node_type": "Shape"}, out="sh", tag="mk_sh"),
        Call("create_node", {"node_type": "Appearance"}, out="ap", tag="mk_ap"),
        Call("create_node", {"node_type": "Material", "fields": {"diffuseColor": [1, 1, 1]}},
             out="mt", tag="mk_mt"),
        Call("create_node", {"node_type": "Box", "fields": {"size": [2, 2, 2]}},
             out="bx", tag="mk_bx"),
        Call("add_child", {"parent_id": "$ap", "child_id": "$mt",
                           "container_field": "material"}, tag="ap_mt"),
        Call("add_child", {"parent_id": "$sh", "child_id": "$ap",
                           "container_field": "appearance"}, tag="sh_ap"),
        Call("add_child", {"parent_id": "$sh", "child_id": "$bx",
                           "container_field": "geometry"}, tag="sh_bx"),
        Call("add_child", {"parent_id": "$tf", "child_id": "$sh",
                           "container_field": "children"}, tag="tf_sh"),
        Call("create_node", {"node_type": "TimeSensor",
                             "fields": {"cycleInterval": 4.0, "loop": True}},
             out="ts", tag="mk_ts"),
        Call("def_node", {"node_id": "$ts", "name": "Clock"}, tag="def_ts"),
        Call("create_node", {"node_type": "OrientationInterpolator",
                             "fields": {"key": [0, 0.5, 1],
                                        "keyValue": [[0, 1, 0, 0], [0, 1, 0, 3.14],
                                                     [0, 1, 0, 6.28]]}},
             out="oi", tag="mk_oi"),
        Call("def_node", {"node_id": "$oi", "name": "Spin"}, tag="def_oi"),
        Call("add_route", {"from_node": "$ts", "from_field": "fraction_changed",
                           "to_node": "$oi", "to_field": "set_fraction"}, tag="route1"),
        Call("add_route", {"from_node": "$oi", "from_field": "value_changed",
                           "to_node": "$tf", "to_field": "set_rotation"}, tag="route2"),
    ]
    return Program(
        "routed-animation", "a white box, spinning", c,
        edges=[
            ("def_ts", "route1", "must a ROUTE's source be DEF'd before the ROUTE?"),
            ("def_oi", "route1", "must a ROUTE's target be DEF'd before the ROUTE?"),
            ("def_tf", "route2", "must a ROUTE's target be DEF'd before the ROUTE?"),
            ("def_tf", "tf_sh", "must a node be DEF'd before children are attached to it?"),
            ("mk_ts", "mk_oi", "does the order of unrelated node creation matter?"),
            ("mk_oi", "def_oi", "must a node exist before it is DEF'd? (dataflow)"),
        ])


def def_use_reuse() -> Program:
    """The one place a NAME (not an opaque id) enters the tool surface.

    Everywhere else the granular API passes node ids, so an ordering constraint
    becomes a DATAFLOW constraint and the transport enforces it for free: you
    cannot reference an id you have not created. `use_node(def_name)` takes a
    STRING. That is the one edge an ordering violation can even be *expressed*
    on -- so if any silent ordering failure exists, it should be here.
    """
    c = [
        Call("create_scene", {"description": "ablation", "profile": "Interactive"}, tag="scene"),
        Call("create_node", {"node_type": "Viewpoint", "fields": {"position": [0, 0, 8]}},
             out="vp", tag="mk_vp"),
        Call("create_node", {"node_type": "Shape"}, out="sh", tag="mk_sh"),
        Call("create_node", {"node_type": "Appearance"}, out="ap", tag="mk_ap"),
        Call("create_node", {"node_type": "Material", "fields": {"diffuseColor": [1, 1, 1]}},
             out="mt", tag="mk_mt"),
        Call("create_node", {"node_type": "Box", "fields": {"size": [1.6, 1.6, 1.6]}},
             out="bx", tag="mk_bx"),
        Call("add_child", {"parent_id": "$ap", "child_id": "$mt",
                           "container_field": "material"}, tag="ap_mt"),
        Call("add_child", {"parent_id": "$sh", "child_id": "$ap",
                           "container_field": "appearance"}, tag="sh_ap"),
        Call("add_child", {"parent_id": "$sh", "child_id": "$bx",
                           "container_field": "geometry"}, tag="sh_bx"),
        Call("def_node", {"node_id": "$sh", "name": "TheBox"}, tag="def_sh"),
        # reuse it, translated aside
        Call("create_node", {"node_type": "Transform",
                             "fields": {"translation": [3, 0, 0]}}, out="tf", tag="mk_tf"),
        Call("use_node", {"def_name": "TheBox"}, out="u", tag="use_sh"),
        Call("add_child", {"parent_id": "$tf", "child_id": "$u",
                           "container_field": "children"}, tag="tf_u"),
    ]
    return Program(
        "def-use-reuse", "two white boxes: the original and a USE of it", c,
        edges=[
            ("def_sh", "use_sh", "must a DEF exist before it is USEd? (the name edge)"),
            ("sh_bx", "def_sh", "must a Shape be complete before it is DEF'd for reuse?"),
            ("mk_tf", "use_sh", "does the USE need its future parent to exist first?"),
        ])


PROGRAMS = [hanim_box, routed_animation, def_use_reuse]


# --- run a program against the bare server ----------------------------------

async def run_program(calls: list[Call]) -> tuple[str, list[str]]:
    """Execute against the RAW x3d_mcp (not Technē — we are measuring what the
    FORMAT requires, not what Technē enforces). Returns (xml, errors)."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=PY, args=["-m", "src.server", "--cwd", REPO],
                                   cwd=REPO, env={**os.environ})
    ids: dict[str, str] = {}
    errors: list[str] = []
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for c in calls:
                args = _resolve(c.args, ids)
                try:
                    res = await s.call_tool(c.tool, args)
                    txt = "\n".join(b.text for b in res.content
                                    if getattr(b, "type", "") == "text")
                except Exception as e:                       # noqa: BLE001
                    errors.append(f"{c.tag}: {e}")
                    continue
                if getattr(res, "isError", False) or txt.lower().startswith("error"):
                    errors.append(f"{c.tag}: {txt.strip()[:90]}")
                    continue
                if c.out:
                    m = _UUID.search(txt)
                    if m:
                        ids[c.out] = m.group(0)
            res = await s.call_tool("get_scene", {"encoding": "xml"})
            xml = "\n".join(b.text for b in res.content
                            if getattr(b, "type", "") == "text")
    return (xml[xml.index("<X3D"):] if "<X3D" in xml else xml), errors


# --- render + classify ------------------------------------------------------

def _serve(dirpath: str):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=dirpath)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def render_all(names: list[str]) -> dict[str, float]:
    """Lit-pixel percentage per variant. One browser, one page per variant."""
    from PIL import Image
    from playwright.sync_api import sync_playwright

    for n in names:
        open(f"{OUT}/{n}.html", "w").write(
            f"""<!doctype html><html><head><script
 src="https://cdn.jsdelivr.net/npm/x_ite@11.6.6/dist/x_ite.min.js"></script></head>
<body style="margin:0;background:#000"><x3d-canvas style="width:320px;height:240px"
 update="auto" src="{n}.x3d"></x3d-canvas></body></html>""")

    srv = _serve(OUT)
    out: dict[str, float] = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--use-angle=metal", "--enable-gpu"])
            pg = b.new_page(viewport={"width": 340, "height": 260})
            for n in names:
                pg.goto(f"http://127.0.0.1:{PORT}/{n}.html")
                pg.wait_for_timeout(3500)
                shot = f"{OUT}/{n}.png"
                pg.screenshot(path=shot)
                im = Image.open(shot).convert("L")
                px = list(im.getdata())
                out[n] = round(sum(1 for v in px if v > 40) / len(px) * 100, 1)
            b.close()
    finally:
        srv.shutdown()
    return out


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from techne.craft import reassert_envlight_global, reassert_profile

    def fix(xml: str) -> str:
        # Control for the KNOWN bugs so the experiment isolates ORDER. Bug 5 means
        # the raw server never declares <component name='HAnim'/>, so without this
        # every variant -- baseline included -- renders blank and the ablation
        # measures nothing. We are asking about ordering, so the component bug is
        # a confound to be removed, not the thing under test.
        return reassert_profile(reassert_envlight_global(xml))

    variants: list[tuple[str, str, str, str, list[str]]] = []   # prog, a, b, q, errors
    names: list[str] = []

    for make in PROGRAMS:
        prog = make()
        xml, errs = asyncio.run(run_program(prog.calls))
        base = f"{prog.name}__baseline"
        open(f"{OUT}/{base}.x3d", "w").write(fix(xml))
        names.append(base)
        variants.append((prog.name, "-", "-", "BASELINE (canonical order)", errs))

        for a, b, q in prog.edges:
            calls = violate(prog, a, b)
            if calls is None:
                variants.append((prog.name, a, b, q, ["DATAFLOW: move impossible"]))
                continue
            xml, errs = asyncio.run(run_program(calls))
            n = f"{prog.name}__{b}_before_{a}"
            open(f"{OUT}/{n}.x3d", "w").write(fix(xml))
            names.append(n)
            variants.append((prog.name, a, b, q, errs))

    lit = render_all(names)

    print("\nPOINT-1 BY ABLATION — which cross-call orderings are actually real?\n")
    print("Each row moves B before A, violating the claim 'A must precede B',")
    print("runs it through the BARE x3d_mcp, and renders the result.\n")

    rows = []
    for prog in {v[0] for v in variants}:
        baseline = lit.get(f"{prog}__baseline", 0.0)
        print(f"── {prog}   (baseline renders {baseline}% lit)")
        for p, a, b, q, errs in variants:
            if p != prog:
                continue
            if a == "-":
                continue
            key = f"{prog}__{b}_before_{a}"
            if "DATAFLOW: move impossible" in errs:
                verdict, detail = "DATAFLOW", "the transport already enforces it"
            elif errs:
                verdict, detail = "LOUD", errs[0][:52]
            else:
                got = lit.get(key, 0.0)
                same = abs(got - baseline) < 1.0
                if same and baseline > 1.0:
                    verdict, detail = "FREE", f"renders identically ({got}%)"
                else:
                    verdict, detail = "SILENT", f"no error, but renders {got}% vs {baseline}%"
            rows.append((prog, a, b, verdict))
            print(f"   {verdict:9} {b} before {a}")
            print(f"             {q}")
            print(f"             -> {detail}")
        print()

    from collections import Counter
    c = Counter(v for _, _, _, v in rows)
    print("── the partial order, measured")
    print(f"   SILENT   {c['SILENT']:2}  ← passes the schema, renders wrong. Technē's domain.")
    print(f"   LOUD     {c['LOUD']:2}  ← the server already refuses. No rule needed.")
    print(f"   DATAFLOW {c['DATAFLOW']:2}  ← ids make the move impossible. Not a convention.")
    print(f"   FREE     {c['FREE']:2}  ← renders identically. Legislating these would be")
    print(f"                 a false positive — the straitjacket §4.4 refuses.")
    json.dump([{"program": p, "must_precede": a, "moved": b, "verdict": v}
               for p, a, b, v in rows], open(f"{OUT}/ablation.json", "w"), indent=1)
    print(f"\n   -> {OUT}/ablation.json")


if __name__ == "__main__":
    main()
