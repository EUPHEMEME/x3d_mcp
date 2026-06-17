"""The Technē transport — an MCP man-in-the-middle in front of x3d-mcp.

The model connects to Technē (stdio); Technē launches the real x3d-mcp as a
subprocess and connects to it as a client. Tool calls pass through the decision
core (proxy.py):

  * `list_tools` forwards the upstream surface, tagging Technē-guarded tools.
  * `call_tool` runs `proxy.decide`: a HARD violation is answered with the
    prescriptive correction (the call never reaches the real server); a repair
    forwards the rewritten args; the upstream result is relayed with any Technē
    notes; `observe_result` commits scene state on success; and for render verbs
    the cheap occupation gate appends a blank-render warning.

The decision logic and these handlers are unit-tested (test_proxy.py,
test_server.py); `run()` is the thin stdio wiring. Run:

    python -m techne.server -- python /path/to/x3d-mcp/src/server.py

(everything after `--` is the command that launches the upstream MCP server).
"""
from __future__ import annotations

import base64
import os
import sys
from typing import Any

from mcp import types

from . import gate
from .proxy import TechneProxy

GUARDED_HINT = "  [Technē-guarded: args are repaired/validated before forwarding.]"

# render verbs trigger the CHEAP occupation gate (soft, advisory): inspect the
# returned image for blankness — the silent failure only the render catches. The
# HARD expensive gate (human sign-off before an offline photoreal render) is the
# OccupationGate library; x3d-mcp has no offline-render verb to attach it to yet,
# so a host drives it explicitly (see gate.py / README).
_RENDER_VERBS = {"render_image", "render_current_scene"}


def _text_of(result: Any) -> str:
    """Flatten an upstream CallToolResult's content to text (for state updates)."""
    parts = []
    for block in getattr(result, "content", None) or []:
        t = getattr(block, "text", None)
        if t:
            parts.append(t)
    return "\n".join(parts)


def _blank_warning(result: Any) -> str | None:
    """If a render result carries a blank image, return a Technē warning, else None."""
    for block in getattr(result, "content", None) or []:
        data = getattr(block, "data", None)
        if data and getattr(block, "type", "") == "image":
            try:
                receipt = gate.inspect_render(base64.b64decode(data))
            except Exception:
                continue
            if not receipt.non_blank:
                return ("Technē occupation gate: the render looks BLANK "
                        "(stddev %.1f) — no geometry visible. Check it is on "
                        "camera, lit, and that HAnim/PBR containerFields are "
                        "correct (X_ITE, not X3DOM, for HAnim)." % receipt.stddev)
    return None


def tag_tools(tools: list) -> list:
    """Append the guarded hint to the description of each Technē-guarded tool."""
    guarded = TechneProxy._ADAPTERS
    for t in tools:
        if getattr(t, "name", None) in guarded:
            t.description = (getattr(t, "description", "") or "") + GUARDED_HINT
    return tools


async def handle_call_tool(proxy: TechneProxy, upstream: Any, name: str,
                           arguments: dict | None) -> "types.CallToolResult":
    """The decision + forward + relay logic for one tool call (testable core).

    Returns a CallToolResult directly so the SDK passes it through untouched —
    relaying the upstream's structuredContent (real FastMCP tools declare an
    outputSchema, so content-only would fail validation) and isError, while
    appending Technē notes / the blank-gate warning. A BLOCK is an isError result
    carrying the prescriptive correction."""
    decision = proxy.decide(name, arguments or {})
    if decision.blocked:
        return types.CallToolResult(
            content=[types.TextContent(
                type="text", text=proxy.correction_message(decision))],
            isError=True)
    result = await upstream.call_tool(name, decision.args)
    proxy.observe_result(decision, _text_of(result))
    content = list(getattr(result, "content", None) or [])
    structured = getattr(result, "structuredContent", None)
    if name == "autofix_x3d":
        # autofix returns corrected X3D but fixes only containerFields; also
        # re-assert the omitted EnvironmentLight 'global' (x3d.py Bug 2) so IBL works.
        from .craft import reassert_envlight_global
        content = [
            types.TextContent(type="text", text=reassert_envlight_global(b.text))
            if getattr(b, "type", "") == "text" and getattr(b, "text", None) else b
            for b in content]
        if isinstance(structured, dict) and isinstance(structured.get("result"), str):
            structured = {**structured,
                          "result": reassert_envlight_global(structured["result"])}
    if decision.notes:
        # an applied repair (args were rewritten) vs an advisory note Technē could
        # not act on — distinct markers so a consumer (and the eval) can tell them apart
        prefix = "Technē repaired: " if decision.rewrote else "Technē note: "
        content.append(types.TextContent(
            type="text", text=prefix + "; ".join(decision.notes)))
    if decision.reminders:
        content.append(types.TextContent(
            type="text", text="Technē reminder: " + " ".join(decision.reminders)))
    if name in _RENDER_VERBS:
        warn = _blank_warning(result)
        if warn:
            content.append(types.TextContent(type="text", text=warn))
    return types.CallToolResult(
        content=content,
        structuredContent=structured,
        isError=bool(getattr(result, "isError", False)))


async def run(upstream_cmd: list[str]) -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    proxy = TechneProxy()
    server = Server("techne")
    params = StdioServerParameters(command=upstream_cmd[0],
                                   args=upstream_cmd[1:], env=dict(os.environ))

    async with stdio_client(params) as (u_read, u_write):
        async with ClientSession(u_read, u_write) as upstream:
            await upstream.initialize()

            @server.list_tools()
            async def list_tools() -> list:
                return tag_tools((await upstream.list_tools()).tools)

            # validate_input=False: Technē must see the model's RAW args so its
            # SAP repair can run; the upstream server does its own validation.
            @server.call_tool(validate_input=False)
            async def call_tool(name: str, arguments: dict | None):
                return await handle_call_tool(proxy, upstream, name, arguments)

            async with stdio_server() as (r, w):
                await server.run(r, w, server.create_initialization_options())


def _parse_upstream(argv: list[str]) -> list[str]:
    if "--" in argv:
        cmd = argv[argv.index("--") + 1:]
        if cmd:
            return cmd
    env = os.environ.get("TECHNE_UPSTREAM")
    if env:
        import shlex
        return shlex.split(env)
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return [sys.executable, os.path.join(repo, "src", "server.py")]


def main() -> None:
    import asyncio
    asyncio.run(run(_parse_upstream(sys.argv[1:])))


if __name__ == "__main__":
    main()
