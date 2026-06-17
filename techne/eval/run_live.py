"""Live-LLM scoreboard — a real model drives the tools through each stack.

    ANTHROPIC_API_KEY=... PYTHONPATH=techne .venv/bin/python techne/eval/run_live.py

For every prompt in tasks.LIVE, an agentic tool-use loop lets the model author a
scene through the raw x3d-mcp and through Technē, and we score what changed:

  * turns / tool calls to a finished scene   (efficiency),
  * input+output tokens spent                (efficiency),
  * Technē blocks the model had to act on     (where the craft layer intervened),
  * intended nodes present in the final XML   (a coarse correctness proxy),
  * final render non-blank                    (liveness).

Needs `pip install anthropic` and ANTHROPIC_API_KEY. Without them it prints how to
run it and exits 0 (skip, not fail) — the scripted scoreboard is the keyless path.
"""
import asyncio
import os
import sys
from dataclasses import dataclass, field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from eval.harness import STACKS, _env_for, text_of, _png_of, is_techne_block, _call
from eval.tasks import LIVE

MODEL = os.environ.get("TECHNE_EVAL_MODEL", "claude-sonnet-4-6")
MAX_TURNS = int(os.environ.get("TECHNE_EVAL_MAX_TURNS", "24"))
SYSTEM = ("You are authoring interactive X3D through an MCP tool surface. Look up "
          "node fields before building, validate semantically, and render before "
          "you declare the scene finished. When a tool result tells you a call was "
          "rejected, read the correction and retry. Stop when the scene is done.")


@dataclass
class LiveMetrics:
    task: str
    stack: str
    turns: int = 0
    tool_calls: int = 0
    techne_blocks: int = 0
    techne_reminders: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    expect_hits: int = 0
    expect_total: int = 0
    final_render: str = "skip"
    error: str = ""


def _to_anthropic_tools(mcp_tools):
    out = []
    for t in mcp_tools:
        out.append({"name": t.name,
                    "description": (t.description or "")[:1024],
                    "input_schema": t.inputSchema or {"type": "object", "properties": {}}})
    return out


async def _final_xml(s) -> str:
    try:
        return text_of(await _call(s, "get_scene", {}))
    except Exception:
        return ""


async def run_live_task(client, stack: str, task) -> LiveMetrics:
    m = LiveMetrics(task=task.name, stack=stack,
                    expect_total=len(task.expect_xml))
    params = StdioServerParameters(command=STACKS[stack][0], args=STACKS[stack][1:],
                                   env=_env_for(stack))
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), 40)
                tools = _to_anthropic_tools((await s.list_tools()).tools)
                messages = [{"role": "user", "content": task.prompt}]
                for _ in range(MAX_TURNS):
                    m.turns += 1
                    resp = await asyncio.to_thread(
                        client.messages.create, model=MODEL, max_tokens=4096,
                        system=SYSTEM, tools=tools, messages=messages)
                    m.tokens_in += resp.usage.input_tokens
                    m.tokens_out += resp.usage.output_tokens
                    messages.append({"role": "assistant", "content": resp.content})
                    if resp.stop_reason != "tool_use":
                        break
                    results = []
                    for blk in resp.content:
                        if getattr(blk, "type", "") != "tool_use":
                            continue
                        m.tool_calls += 1
                        try:
                            res = await _call(s, blk.name, blk.input or {}, t=90)
                        except Exception as ex:
                            results.append({"type": "tool_result", "tool_use_id": blk.id,
                                            "content": f"call error: {ex}", "is_error": True})
                            continue
                        txt = text_of(res)
                        if is_techne_block(res, txt):
                            m.techne_blocks += 1
                        if "Techn" in txt and "reminder" in txt.lower():
                            m.techne_reminders += 1
                        results.append({"type": "tool_result", "tool_use_id": blk.id,
                                        "content": txt or "(no text)",
                                        "is_error": bool(getattr(res, "isError", False))})
                    messages.append({"role": "user", "content": results})

                xml = await _final_xml(s)
                m.expect_hits = sum(1 for tok in task.expect_xml if tok in xml)
                await _score_live_render(s, m)
    except Exception as ex:
        m.error = f"{type(ex).__name__}: {ex}"
    return m


async def _score_live_render(s, m: LiveMetrics):
    try:
        sys.path.insert(0, os.environ.get("X3D_MCP_REPO", "/Users/alexander/x3d_mcp") + "/techne")
        from techne.gate import inspect_render
        res = await _call(s, "render_current_scene", {"wait_ms": 6000}, t=120)
        png = _png_of(res)
        if not png:
            m.final_render = "error"
            return
        m.final_render = "ok" if inspect_render(png).non_blank else "blank"
    except Exception:
        m.final_render = "error"


def _print(rows):
    hdr = ["task", "stack", "turns", "calls", "blocks", "remind", "tok_in", "tok_out", "intent", "render"]
    w = [22, 7, 6, 6, 7, 7, 8, 8, 7, 7]
    line = lambda c: "  ".join(str(x).ljust(wi) for x, wi in zip(c, w))
    print(line(hdr)); print(line(["-" * x for x in w]))
    for m in rows:
        intent = f"{m.expect_hits}/{m.expect_total}"
        print(line([m.task, m.stack, m.turns, m.tool_calls, m.techne_blocks,
                    m.techne_reminders, m.tokens_in, m.tokens_out, intent, m.final_render]))
    errs = [(m.task, m.stack, m.error) for m in rows if m.error]
    for t, st, e in errs:
        print(f"  [{st}/{t}] {e}")


def main():
    try:
        import anthropic
    except ImportError:
        print("live mode needs the Anthropic SDK:  .venv/bin/pip install anthropic")
        print("then:  ANTHROPIC_API_KEY=... PYTHONPATH=techne .venv/bin/python techne/eval/run_live.py")
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("live mode needs ANTHROPIC_API_KEY set. The scripted scoreboard "
              "(run_scripted.py) is the keyless path.")
        return 0
    client = anthropic.Anthropic()

    async def _run():
        rows = []
        for task in LIVE:
            for stack in ("raw", "techne"):
                print(f"… {task.name} / {stack}", file=sys.stderr)
                rows.append(await run_live_task(client, stack, task))
        rows.sort(key=lambda m: (m.task, m.stack))
        _print(rows)
        return rows
    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
