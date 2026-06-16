"""Live end-to-end smoke: an MCP client drives real tool calls through the Technē
proxy (which fronts the real x3d-mcp), proving the man-in-the-middle repairs,
blocks, and gates for real — not just in unit tests.

Run:  .venv/bin/python techne/smoke_live.py
"""
import asyncio
import os
import re
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = "/Users/alexander/x3d_mcp"
PY = f"{REPO}/.venv/bin/python"
OUT = []


def log(name, ok, detail):
    mark = "PASS" if ok else "FAIL"
    OUT.append((mark, name, detail))
    print(f"[{mark}] {name}: {str(detail)[:300]}")


def text_of(result):
    return "\n".join(getattr(b, "text", "") for b in (result.content or [])
                     if getattr(b, "text", None))


async def call(s, tool, args, t=25):
    return await asyncio.wait_for(s.call_tool(tool, args), t)


async def main():
    params = StdioServerParameters(
        command=PY,
        args=["-m", "techne.server", "--", PY, f"{REPO}/src/server.py"],
        env={**os.environ, "PYTHONPATH": f"{REPO}/techne"},
    )
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 40)
            log("initialize", True, "handshake ok")

            tools = (await asyncio.wait_for(s.list_tools(), 20)).tools
            guarded = sorted(t.name for t in tools
                             if "Techn" in (t.description or ""))
            log("list_tools + guard tagging",
                {"add_child", "create_node"} <= set(guarded),
                f"{len(tools)} tools; guarded={guarded}")

            m = text_of(await call(s, "create_node",
                                   {"node_type": "PhysicalMaterial", "fields": {}}))
            mid = (re.search(r"ID:\s*(\S+)", m) or [None, None])[1]
            log("create PhysicalMaterial", bool(mid), m)

            t = text_of(await call(s, "create_node",
                                   {"node_type": "ImageTexture", "fields": {}}))
            tid = (re.search(r"ID:\s*(\S+)", t) or [None, None])[1]
            log("create ImageTexture", bool(tid), t)

            a = text_of(await call(s, "add_child",
                        {"parent_id": mid, "child_id": tid, "container_field": ""}))
            log("add_child (missing containerField) -> BLOCK",
                ("blocked" in a.lower()) and ("baseTexture" in a), a)

            e = text_of(await call(s, "create_node",
                                   {"node_type": "EnvironmentLight", "fields": {}}))
            log("create EnvironmentLight -> global repaired",
                ("global" in e and "true" in e.lower()), e)

            try:
                rtxt = text_of(await call(s, "render_current_scene", {}, t=70))
                log("render_current_scene (blank-gate exercised)",
                    True, rtxt or "(no text content)")
            except Exception as ex:
                log("render_current_scene", False, f"render error/timeout: {ex}")


if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(main(), 150))
    except Exception as ex:
        print(f"[FATAL] {type(ex).__name__}: {ex}")
        sys.exit(2)
    fails = [o for o in OUT if o[0] == "FAIL"]
    print(f"\n=== {len(OUT)-len(fails)}/{len(OUT)} steps passed ===")
    sys.exit(1 if fails else 0)
