"""The Technē transport — an MCP man-in-the-middle in front of x3d-mcp.

The model connects to Technē (stdio); Technē launches the real x3d-mcp as a
subprocess and connects to it as a client. Tool calls pass through the decision
core (proxy.py):

  * `list_tools` forwards the upstream surface, tagging Technē-guarded tools.
  * `call_tool` runs `proxy.decide`: a HARD violation is answered with the
    prescriptive correction (the call never reaches the real server); a repair
    forwards the rewritten args; the upstream result is relayed with any Technē
    notes, and `observe_result` updates scene state.

The decision logic is fully unit-tested in test_proxy.py; this module is the thin,
SDK-correct wiring around it. Run:

    python -m techne.server -- python /path/to/x3d-mcp/src/server.py

(everything after `--` is the command that launches the upstream MCP server).
"""
from __future__ import annotations

import os
import sys
from typing import Any

from .proxy import TechneProxy

GUARDED_HINT = "  [Technē-guarded: args are repaired/validated before forwarding.]"


def _text_of(result: Any) -> str:
    """Flatten an upstream CallToolResult's content to text (for state updates)."""
    parts = []
    for block in getattr(result, "content", None) or []:
        t = getattr(block, "text", None)
        if t:
            parts.append(t)
    return "\n".join(parts)


async def run(upstream_cmd: list[str]) -> None:
    from mcp import ClientSession, StdioServerParameters, types
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
                tools = (await upstream.list_tools()).tools
                guarded = TechneProxy._ADAPTERS
                for t in tools:
                    if t.name in guarded:
                        t.description = (t.description or "") + GUARDED_HINT
                return tools

            @server.call_tool()
            async def call_tool(name: str, arguments: dict | None) -> list:
                decision = proxy.decide(name, arguments or {})
                if decision.blocked:
                    return [types.TextContent(
                        type="text", text=proxy.correction_message(decision))]
                result = await upstream.call_tool(name, decision.args)
                proxy.observe_result(name, decision.args, _text_of(result))
                content = list(result.content or [])
                if decision.notes:
                    content.append(types.TextContent(
                        type="text",
                        text="Technē: " + "; ".join(decision.notes)))
                return content

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
    # default: x3d-mcp in this repo
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return [sys.executable, os.path.join(repo, "src", "server.py")]


def main() -> None:
    import asyncio
    upstream = _parse_upstream(sys.argv[1:])
    asyncio.run(run(upstream))


if __name__ == "__main__":
    main()
