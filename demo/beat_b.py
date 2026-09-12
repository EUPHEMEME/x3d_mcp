#!/usr/bin/env python3
# beat_b.py v1.0 2026-08-31 — Beat B: two live Technē proxy calls — one BLOCK, one silent REPAIR.
"""Beat B of the Techne live demo — the proxy, live, on two defects from the
craft catalog (techne/techne/rules.py):

  CASE A — BLOCK.  add_child of an ImageTexture into a PhysicalMaterial with the
      containerField left to default. The default is 'texture' — a field
      PhysicalMaterial does not define — so a conformant player silently drops
      the texture (x3d.py Bug 1). Technē cannot guess WHICH slot was meant
      (baseTexture vs normalTexture is intent), so it BLOCKS and lists every
      legal slot. The error message IS the correction.

  CASE B — silent REPAIR.  create_node with `fields` sent as a markdown-fenced
      JSON *string* instead of an object — the classic sloppy-model emission.
      Technē's SAP (Schema-Aligned Parsing) layer unwraps it deterministically
      and forwards; the call just works. As the control, the SAME raw call is
      first sent straight to the unproxied x3d-mcp server, where it errors —
      proving the repair is Technē's doing, not upstream tolerance.

Prints raw request, response, and the proxy scoreboard.
Receipts land in demo/receipts/beat_b/.

Run:  cd /Users/alexander/x3d_mcp && .venv/bin/python demo/beat_b.py

This script asserts its own result (exit 0 only if A blocked with all five
slots named, and B errored raw but succeeded through Technē).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = "/Users/alexander/x3d_mcp"
PY = f"{REPO}/.venv/bin/python"
RECEIPTS = f"{REPO}/demo/receipts/beat_b"

PBR_SLOTS = ["baseTexture", "emissiveTexture", "normalTexture",
             "occlusionTexture", "metallicRoughnessTexture"]

LOG: list[str] = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    LOG.append(line)


def hr(title: str):
    say("=" * 66)
    say(title)
    say("=" * 66)


def text_of(res) -> str:
    return "\n".join(c.text for c in res.content
                     if getattr(c, "type", "") == "text")


def show_call(label: str, tool: str, args: dict, res) -> str:
    say(f"\n>>> RAW REQUEST ({label})")
    say(json.dumps({"tool": tool, "arguments": args}, indent=2))
    body = text_of(res)
    say(f"<<< RESPONSE  (isError={bool(res.isError)})")
    say(body.strip() or "(empty)")
    return body


def extract_id(text: str) -> str | None:
    import re
    m = re.search(r"ID:\s*([0-9a-f\-]{8,})", text)
    return m.group(1) if m else None


# The sloppy emission for CASE B: fields as a fenced JSON string, not an object.
CASE_B_ARGS = {
    "node_type": "Viewpoint",
    "fields": "```json\n{\"description\": \"SAP repair demo\", "
              "\"position\": [0, 1.6, 3.0]}\n```",
}


async def main() -> int:
    os.makedirs(RECEIPTS, exist_ok=True)
    failures: list[str] = []
    counters = {"calls": 0, "blocked": 0, "repaired_forwards": 0}

    techne_params = StdioServerParameters(
        command=PY,
        args=["-m", "techne.server", "--", PY, "-m", "src.server", "--cwd", REPO],
        env={**os.environ, "PYTHONPATH": f"{REPO}/techne",
             "TECHNE_PROFILE": "core,coherence",
             "TECHNE_TRACE_DIR": f"{REPO}/techne_traces"},
        cwd=REPO)
    raw_params = StdioServerParameters(
        command=PY, args=["-m", "src.server", "--cwd", REPO],
        env=dict(os.environ), cwd=REPO)

    # ---------- CONTROL for CASE B: the raw, unproxied server -----------------
    hr("CASE B CONTROL — same sloppy call, straight at the RAW x3d-mcp server")
    async with stdio_client(raw_params) as (r, w):
        async with ClientSession(r, w) as raw:
            await raw.initialize()
            await raw.call_tool("create_scene",
                                {"description": "beat B control", "profile": "Interactive"})
            res = await raw.call_tool("create_node", CASE_B_ARGS)
            body = show_call("raw server, no Technē", "create_node", CASE_B_ARGS, res)
            raw_errored = bool(res.isError) or "error" in body.lower()
            say(f"\n  control verdict: raw server {'ERRORS' if raw_errored else 'accepted it'} "
                "-- `fields` must be an object, and no one unwrapped the string.")
            if not raw_errored:
                failures.append("CONTROL: raw server unexpectedly accepted string fields")

    # ---------- the Technē-proxied session ------------------------------------
    async with stdio_client(techne_params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            async def call(tool, args):
                counters["calls"] += 1
                return await s.call_tool(tool, args)

            await call("create_scene",
                       {"description": "Techne demo — beat B", "profile": "Interactive"})

            # ---- CASE A — the BLOCK ------------------------------------------
            hr("CASE A — ImageTexture into PhysicalMaterial, containerField "
               "left to default  ->  expect BLOCK naming every legal slot")
            res = await call("create_node",
                             {"node_type": "PhysicalMaterial",
                              "fields": {"baseColor": [0.92, 0.87, 0.80]}})
            mat_id = extract_id(text_of(res))
            res = await call("create_node",
                             {"node_type": "ImageTexture",
                              "fields": {"url": ["bone_diffuse.png"]}})
            tex_id = extract_id(text_of(res))
            if not mat_id or not tex_id:
                say("ABORT: could not create the two nodes")
                return 2

            args_a = {"parent_id": mat_id, "child_id": tex_id}
            res = await call("add_child", args_a)
            body = show_call("through Technē", "add_child", args_a, res)
            blocked = bool(res.isError) or "blocked" in body.lower()
            slots_named = [sl for sl in PBR_SLOTS if sl in body]
            if blocked:
                counters["blocked"] += 1
            say(f"\n  verdict: {'BLOCKED' if blocked else 'NOT BLOCKED'}; "
                f"legal slots named in the correction: {len(slots_named)}/5 "
                f"({', '.join(slots_named) or 'none'})")
            say("  the defaulted containerField would have been 'texture' — a field")
            say("  PhysicalMaterial does not define; the texture would silently vanish.")
            if not blocked:
                failures.append("CASE A was not blocked")
            if len(slots_named) != 5:
                failures.append(f"CASE A correction named {len(slots_named)}/5 slots")

            # ---- CASE B — the silent REPAIR ----------------------------------
            hr("CASE B — the SAME sloppy call, through Technē  ->  expect "
               "silent SAP repair + forward")
            res = await call("create_node", CASE_B_ARGS)
            body = show_call("through Technē", "create_node", CASE_B_ARGS, res)
            repaired_ok = (not res.isError) and "Created Viewpoint" in body
            if repaired_ok:
                counters["repaired_forwards"] += 1
            say(f"\n  verdict: {'FORWARDED — node created' if repaired_ok else 'DID NOT forward'}")
            say("  Technē unwrapped the fenced JSON string into the object the schema")
            say("  wants and forwarded; the model never saw an error. Same bytes, raw")
            say("  server: error (see control above). That delta IS the SAP layer.")
            if not repaired_ok:
                failures.append("CASE B did not repair+forward")

    # ---------- scoreboard -----------------------------------------------------
    hr("TECHNĒ SCOREBOARD")
    for k, v in counters.items():
        say(f"  {k:18s}: {v}")
    say("")
    if failures:
        for f_ in failures:
            say("  FAIL: " + f_)
    else:
        say("  BEAT B SELF-ASSERTION: block named all 5 legal slots; the SAP repair")
        say("  forwarded a call the raw server rejects. Receipts -> " + RECEIPTS)

    with open(f"{RECEIPTS}/beat_b_transcript.txt", "w") as f:
        f.write("$ .venv/bin/python demo/beat_b.py\n" + "\n".join(LOG) + "\n")
    with open(f"{RECEIPTS}/counters.json", "w") as f:
        json.dump(counters, f, indent=1)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
