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
import re
import sys
from typing import Any

from mcp import types

from . import gate
from .proxy import TechneProxy

GUARDED_HINT = "  [Technē-guarded: args are repaired/validated before forwarding.]"
POSTCHECK_HINT = "  [Technē-guarded: output re-validated through the server's own validators.]"

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


# content-based edit tools operate on a whole serialized X3D document and validate
# almost nothing (modify writes unvalidated attributes; move never re-checks
# containerField; convert silently drops nodes; all return errors as plain strings
# indistinguishable from a success document). Technē post-validates their output
# through the server's OWN validators — the authoritative pass it already fronts —
# and surfaces what the edit broke, without re-implementing or coupling to X3DUOM.
_EDIT_VERBS = {"modify_x3d_node", "move_x3d_node", "remove_x3d_node",
               "add_x3d_route", "convert_x3d"}


def _looks_like_doc(text: str) -> bool:
    return (text or "").lstrip().startswith(("<?xml", "<X3D", "<!DOCTYPE", "<Scene"))


_TAG_RE = re.compile(r"<([A-Za-z][\w.\-]*)\b")


def _node_count(xml: str) -> int:
    """Cheap element-tag count (dependency-free) for the convert drop-diff."""
    return len(_TAG_RE.findall(xml or ""))


def _is_error_like(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(t) and (t.startswith(("error", "no node", "invalid", "failed"))
                        or "not found" in t or "error:" in t[:60])


def _vx_errors(vx: str) -> str:
    """Best-effort schema-error summary from a validate_x3d result (robust to the
    tool's nested-JSON framing — substring detection, not strict parsing)."""
    if '"valid": true' in vx or '"valid":true' in vx:
        return ""
    if '"valid": false' in vx or '"valid":false' in vx:
        errs = re.findall(r'"(Line \d+:[^"]*)"', vx)
        return "; ".join(e.replace('\\"', "'") for e in errs[:3]) or "schema invalid"
    return ""                                   # unparseable -> fail safe (no alarm)


def _vs_errors(vs: str) -> str:
    """Surface only HARD semantic errors (skip warnings/infos like no-viewpoint and
    unused-def, which the study flagged as noise)."""
    if "## Errors" not in vs:
        return ""
    section = vs.split("## Errors", 1)[1].split("\n## ", 1)[0]
    bullets = re.findall(r'- \*\*\[[^\]]+\]\*\*\s*(.+)', section)
    return "; ".join(b.strip()[:120] for b in bullets[:3])


def _provenance_note(proxy: TechneProxy, xml: str) -> "types.TextContent | None":
    """Opt-in provenance gate (only when the profile enables it). Soft by default —
    appends a 'Technē provenance:' WARN note, never blocks (don't wall artistic
    workflows that don't opt in; even when on, nudge unless TECHNE_STRICT)."""
    if not getattr(proxy, "config", None) or not proxy.config.provenance:
        return None
    from . import provenance
    issues = provenance.check_scene_provenance(
        xml, proxy.ledger(), proxy.config.provenance_level)
    if not issues:
        return None
    tag = "violation" if proxy.config.strict else "note"
    return types.TextContent(type="text", text=(
        f"Technē provenance (L{proxy.config.provenance_level}, {tag}): "
        + "; ".join(issues[:5])))


async def _post_validate_edit(upstream: Any, doc: str) -> list[str]:
    """Run an edited document back through the server's validators; return problem
    lines (empty if clean). Catches modify's unvalidated attributes (XSD) and move's
    misfiled containerFields (semantic) -- the silent failures the edit tools miss."""
    out: list[str] = []
    try:
        e = _vx_errors(_text_of(await upstream.call_tool("validate_x3d", {"content": doc})))
        if e:
            out.append("validate_x3d -> " + e)
    except Exception:
        pass
    try:
        e = _vs_errors(_text_of(await upstream.call_tool("validate_semantic", {"content": doc})))
        if e:
            out.append("validate_semantic -> " + e)
    except Exception:
        pass
    return out


def tag_tools(tools: list) -> list:
    """Append the appropriate guarded hint per Technē-guarded tool: arg-repair for
    the granular adapters, output-revalidation for the content-based edit tools."""
    adapters = set(TechneProxy._ADAPTERS)
    for t in tools:
        n = getattr(t, "name", None)
        if n in adapters:
            t.description = (getattr(t, "description", "") or "") + GUARDED_HINT
        elif n in _EDIT_VERBS:
            t.description = (getattr(t, "description", "") or "") + POSTCHECK_HINT
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
    if name == "render_image" and (arguments or {}).get("content"):
        pnote = _provenance_note(proxy, arguments["content"])   # opt-in policy
        if pnote:
            content.append(pnote)
    if name in _EDIT_VERBS and not getattr(result, "isError", False):
        doc = _text_of(result)
        if _looks_like_doc(doc):
            probs = await _post_validate_edit(upstream, doc)
            if probs:
                content.append(types.TextContent(
                    type="text", text="Technē post-check: the edited document has "
                    "issues the edit tool did not catch -- " + "; ".join(probs)))
            if name == "convert_x3d":
                # convert silently skips unknown nodes/attrs -> a valid but smaller
                # doc that no validator flags. Surface the element-count drop.
                before, after = _node_count((arguments or {}).get("content", "")), _node_count(doc)
                if before and after < before:
                    content.append(types.TextContent(
                        type="text", text=f"Technē: convert kept {after} of {before} "
                        "elements -- convert_x3d silently drops unknown nodes/"
                        "attributes; verify nothing important was lost."))
            pnote = _provenance_note(proxy, doc)          # opt-in policy (off by default)
            if pnote:
                content.append(pnote)
        elif _is_error_like(doc):
            content.append(types.TextContent(
                type="text", text="Technē: this edit returned an error string, not "
                "a document -- the edit did not apply: " + doc[:200]))
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
