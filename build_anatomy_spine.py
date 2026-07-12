#!/usr/bin/env python3
"""Author the LOA5 Anatomy Explorer's studio spine THROUGH the Technē proxy.

The 257-bone payload is bulk transcription of Web3D's own canonical meshes --
there is no craft decision in it, only volume, and it is spliced in by
flatten_anatomy.py. The *spine* is where the craft bugs actually live:
containerField slots, DEF-before-ROUTE ordering, light/viewpoint/PBR
interactions. So the spine is authored one granular tool call at a time, and
every call passes through Technē's rule engine before it reaches x3d-mcp.

Run:  .venv/bin/python build_anatomy_spine.py
Out:  build_anatomy/studio_spine.x3d   + a transcript of what Technē did
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = "/Users/alexander/x3d_mcp"
PY = f"{REPO}/.venv/bin/python"
OUT = f"{REPO}/build_anatomy"

TRANSCRIPT: list[dict] = []


def note(kind: str, **kw):
    TRANSCRIPT.append({"kind": kind, **kw})


class Techne:
    """Thin client over the proxy that records every intervention."""

    def __init__(self, session: ClientSession):
        self.s = session
        self.calls = 0
        self.blocks = 0
        self.repairs = 0
        self.reminders = 0

    async def call(self, tool: str, **args):
        self.calls += 1
        res = await self.s.call_tool(tool, args)
        text = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")

        low = text.lower()
        if res.isError or "rejected" in low or "blocked" in low:
            self.blocks += 1
            note("BLOCK", tool=tool, args=args, response=text.strip()[:400])
            print(f"  ✗ BLOCK  {tool}({_brief(args)})\n           → {text.strip()[:150]}")
        else:
            if "repair" in low:
                self.repairs += 1
                note("REPAIR", tool=tool, args=args, response=text.strip()[:300])
                print(f"  ⟳ REPAIR {tool}({_brief(args)})")
            if "reminder" in low or "note:" in low:
                self.reminders += 1
        return text

    async def node(self, node_type: str, fields: dict | None = None, defname: str | None = None):
        """create_node -> (id). def_node immediately: Technē blocks a ROUTE whose
        endpoints are not yet DEF'd, so never defer naming."""
        out = await self.call("create_node", node_type=node_type, fields=fields or {})
        nid = _extract_id(out)
        if nid is None:
            raise SystemExit(f"could not parse node id from: {out[:200]}")
        if defname:
            await self.call("def_node", node_id=nid, name=defname)
        return nid


def _brief(args: dict) -> str:
    return ", ".join(f"{k}={str(v)[:26]}" for k, v in args.items() if k != "fields")


def _extract_id(text: str) -> str | None:
    # "Created Viewpoint with ID: 5d81186b-bf35-41d9-9f06-bc5128235d2b"
    m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
    if m:
        return m.group(0)
    m = re.search(r"\b(?:id|node_id)\b[=:\s\"']*([A-Za-z0-9_\-]+)", text, re.I)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# The studio. Order is deliberate and Technē-aware:
#   viewpoints -> navinfo -> lights  (before any geometry, so the coherence
#   reminders about PBR-and-the-headlight fire once, on an empty scene, instead
#   of riding along on every later call)
# ---------------------------------------------------------------------------

# x3d.py wants real SFVec3f/SFRotation/SFColor values -- lists of floats, not
# the whitespace strings you'd write in the XML. (It rejects the string form
# outright: "0 0.95 0 has type <class 'str'> but is not a valid SFVec3f".)
#
# The figure stands ~1.7 m tall on y=0. Distances in METRES, angles in RADIANS
# -- which is exactly the standing invariant Technē reminds you of on call one.
VIEWPOINTS = [
    ("VP_Body",    "Full skeleton",   [0, 0.92, 2.75],   [0, 0.92, 0],   [0, 1, 0, 0]),
    ("VP_Skull",   "Skull",           [0, 1.62, 0.62],   [0, 1.6, 0],    [0, 1, 0, 0]),
    ("VP_Ribcage", "Rib cage",        [0.15, 1.35, 0.95], [0, 1.3, 0],   [0, 1, 0, 0.12]),
    ("VP_Spine",   "Vertebral column", [0.05, 1.15, -1.1], [0, 1.15, 0], [0, 1, 0, 3.14159]),
    ("VP_Hand",    "Left hand",       [0.42, 0.75, 0.45], [0.32, 0.72, 0], [0, 1, 0, 0.6]),
    ("VP_Foot",    "Left foot",       [0.28, 0.22, 0.62], [0.1, 0.08, 0], [0, 1, 0, 0.35]),
]

# x3d.py spells the X3D field `global` as `global_` -- `global` is a Python
# keyword. It matters: a light that is not global only lights its own sibling
# subtree, so a non-global key light leaves the whole skeleton black.
LIGHTS = [
    # key: warm, high, front-left -- the one that shapes the bone
    ("KeyLight",  {"direction": [-0.42, -0.58, -0.70], "color": [1.0, 0.94, 0.85],
                   "intensity": 1.55, "ambientIntensity": 0.0,
                   "shadows": True, "shadowIntensity": 0.62}),
    # fill: cool, opposite, soft -- lifts the shadow side without flattening it.
    # Keep it well under the key or the bone goes grey-blue and the form dies.
    ("FillLight", {"direction": [0.75, -0.18, -0.42], "color": [0.55, 0.66, 0.92],
                   "intensity": 0.30, "ambientIntensity": 0.0}),
    # rim: from behind, separates the figure from the dark backdrop
    ("RimLight",  {"direction": [0.18, -0.30, 0.94], "color": [0.95, 0.93, 1.0],
                   "intensity": 0.95, "ambientIntensity": 0.0}),
]


async def build(t: Techne) -> str:
    print("\n── authoring the studio spine through Technē ──\n")

    await t.call("create_scene",
                 description="LOA5 Anatomy Explorer — studio stage",
                 profile="Interactive")

    root = "scene"   # the granular API's implicit scene root

    async def attach(nid: str, container: str | None = None):
        # ALWAYS name the containerField where the slot is ambiguous. Technē
        # refuses to guess between e.g. HAnimHumanoid.skeleton and .joints, and
        # a wrong guess is exactly the silent-vanish bug the layer exists for.
        kw = {"parent_id": root, "child_id": nid}
        if container:
            kw["container_field"] = container
        await t.call("add_child", **kw)

    # 1. viewpoints (first bound wins: VP_Body must be created first)
    print("· viewpoints")
    for name, desc, pos, cor, orient in VIEWPOINTS:
        nid = await t.node("Viewpoint", {
            "description": desc, "position": pos, "centerOfRotation": cor,
            "orientation": orient, "fieldOfView": 0.72,
            "nearDistance": 0.01, "farDistance": 80.0,
        }, defname=name)
        await attach(nid)

    # 2. navigation — headlight OFF, or the studio rig is drowned by a flat
    #    camera-mounted lamp and every bone reads as a white cutout.
    print("· navigation")
    nid = await t.node("NavigationInfo", {
        "type": ["EXAMINE", "ANY"], "headlight": False, "speed": 1.2,
    }, defname="Nav")
    await attach(nid)

    # 3. the studio rig
    print("· lighting")
    for name, fields in LIGHTS:
        nid = await t.node("DirectionalLight",
                           {**fields, "global_": True, "on": True},
                           defname=name)
        await attach(nid)

    # ambient: without it, PBR bone on the shadow side goes to pure black.
    # EnvironmentLight has no diffuse/specular fields -- it is color+intensity
    # (plus optional cube textures we don't ship).
    nid = await t.node("EnvironmentLight", {
        "color": [0.62, 0.66, 0.78], "intensity": 0.30,
        "ambientIntensity": 0.28, "global_": True, "on": True,
    }, defname="Ambient")
    await attach(nid)

    # 4. backdrop
    print("· backdrop")
    # Two shapes x3d.py is strict about:
    #   * skyAngle/groundAngle are RADIANS from the zenith/nadir, and the spec
    #     caps groundAngle at pi/2 = 1.5708 -- 1.571 overshoots and is rejected.
    #   * MFColor is a list of TRIPLES, not a flat list of floats.
    #
    # And one that is easy to get backwards: groundAngle is measured from the
    # NADIR (0 = straight down) up toward the horizon, so groundColor[0] is the
    # color underfoot and the LAST one meets the horizon. Order them the other
    # way and the darkest ground lands against the brightest sky -- a hard seam
    # straight across the middle of the shot. The last ground color therefore
    # equals the last sky color.
    nid = await t.node("Background", {
        "skyAngle": [0.75, 1.25, 1.5707],
        "skyColor": [[0.052, 0.056, 0.070], [0.078, 0.084, 0.102],
                     [0.096, 0.101, 0.120], [0.058, 0.061, 0.072]],
        "groundAngle": [0.6, 1.5707],
        "groundColor": [[0.030, 0.031, 0.037], [0.044, 0.046, 0.055],
                        [0.058, 0.061, 0.072]],
    }, defname="Sky")
    await attach(nid)



    # 5. the three gait clocks. DEF them here so the spliced animation ROUTEs
    #    have real endpoints; enabled=false so the figure enters standing.
    print("· gait clocks")
    for name, interval in [("WalkTimer", 2.5), ("RunTimer", 1.4), ("JumpTimer", 2.0)]:
        nid = await t.node("TimeSensor",
                           {"cycleInterval": interval, "loop": True, "enabled": False},
                           defname=name)
        await attach(nid)

    print("\n· validating through the proxy")
    v = await t.call("validate_current_scene")
    print(f"  {v.strip()[:220]}")

    xml = await t.call("get_scene", encoding="xml")
    return xml


async def main():
    os.makedirs(OUT, exist_ok=True)
    params = StdioServerParameters(
        command=PY,
        args=["-m", "techne.server", "--", PY, "-m", "src.server", "--cwd", REPO],
        env={
            **os.environ,
            "PYTHONPATH": f"{REPO}/techne",
            # coherence must be named explicitly or the standing reminders
            # silently switch off (techne/config.py).
            "TECHNE_PROFILE": "core,coherence",
            "TECHNE_TRACE_DIR": f"{REPO}/techne_traces",
        },
        cwd=REPO,
    )
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            t = Techne(s)
            xml = await build(t)

    body = xml[xml.index("<X3D"):] if "<X3D" in xml else xml
    open(f"{OUT}/studio_spine.x3d", "w").write(body)
    json.dump(TRANSCRIPT, open(f"{OUT}/techne_transcript.json", "w"), indent=1)

    print(f"\n── Technē scoreboard ──")
    print(f"  tool calls  : {t.calls}")
    print(f"  blocked     : {t.blocks}")
    print(f"  repaired    : {t.repairs}")
    print(f"  → {OUT}/studio_spine.x3d  ({len(body)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
