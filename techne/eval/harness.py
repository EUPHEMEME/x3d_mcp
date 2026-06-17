"""Eval harness core — the scoreboard.

Two *stacks* expose the identical MCP tool surface:

  * raw    — the production x3d-mcp server, launched directly;
  * techne — the same server with the Technē proxy in front of it.

`run_scripted_task` drives a task through one stack with a fixed *agent policy*:
issue each planned (possibly mistaken) call; if Technē blocks it with a
prescriptive correction, apply the correction and retry (that retry is the
round-trip Technē costs); if Technē silently repairs it, take the win; on the raw
stack the mistake just lands. The returned `Metrics` is what we tabulate.

Render scoring is optional (`render=True`) and reuses Technē's own blank detector
(`gate.inspect_render`) — honest about what it measures: non-blank, not correct.
"""
import asyncio
import os
import re
import sys
from dataclasses import dataclass, field, asdict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = os.environ.get("X3D_MCP_REPO", "/Users/alexander/x3d_mcp")
PY = f"{REPO}/.venv/bin/python"
_ID_RE = re.compile(r"\bID:\s*([A-Za-z0-9_\-:]+)")

# The two stacks, as (command, args) for StdioServerParameters.
STACKS = {
    "raw": [PY, f"{REPO}/src/server.py"],
    "techne": [PY, "-m", "techne.server", "--", PY, f"{REPO}/src/server.py"],
}


def _env_for(stack: str) -> dict:
    env = dict(os.environ)
    if stack == "techne":
        env["PYTHONPATH"] = f"{REPO}/techne" + os.pathsep + env.get("PYTHONPATH", "")
    return env


def text_of(result) -> str:
    return "\n".join(getattr(b, "text", "") for b in (getattr(result, "content", None) or [])
                     if getattr(b, "text", None))


def _png_of(result):
    for b in getattr(result, "content", None) or []:
        data = getattr(b, "data", None)
        if data and getattr(b, "type", "") == "image":
            import base64
            return base64.b64decode(data) if isinstance(data, str) else data
    return None


def is_techne_block(result, txt: str) -> bool:
    """A Technē block is an isError result whose text is the prescriptive correction."""
    return bool(getattr(result, "isError", False)) and "Techn" in txt and "block" in txt.lower()


def is_techne_repair(txt: str) -> bool:
    """A repair / soft-advisory rides back as a 'Technē: ...' note *appended after*
    the upstream content (so it is mid-text, not leading). Distinct from a
    'Technē reminder: ...' coherence line (note the 'ē: ' vs 'ē reminder:')."""
    return "Technē: " in txt and "block" not in txt.lower()


@dataclass
class Metrics:
    task: str
    stack: str
    tool_calls: int = 0            # calls issued, incl. retries (the efficiency column)
    blocks: int = 0               # Technē hard blocks hit
    repairs: int = 0              # Technē silent repairs taken
    mistakes_planned: int = 0
    mistakes_caught: int = 0      # blocked or repaired before reaching the scene
    leaked_silent: int = 0        # passed INTO the scene with no error (the dangerous case)
    rejected_loud: int = 0        # upstream errored, but with no prescriptive guidance
    correction_named_fix: int = 0  # blocks whose text contained the expected fix token
    final_render: str = "skip"    # ok | blank | error | skip
    render_stddev: float = 0.0
    completed: bool = True        # the task built its intended end-state
    errors: list = field(default_factory=list)


async def _call(s, tool, args, t=30):
    return await asyncio.wait_for(s.call_tool(tool, args), t)


def _resolve(args: dict, caps: dict) -> dict:
    """Replace @name placeholders with captured node IDs."""
    out = {}
    for k, v in args.items():
        out[k] = caps.get(v[1:], v) if isinstance(v, str) and v.startswith("@") else v
    return out


async def _do_step(s, step, caps, m: Metrics):
    """Issue one (non-mistaken or already-corrected) step; capture its ID."""
    res = await _call(s, step.tool, _resolve(step.args, caps))
    m.tool_calls += 1
    txt = text_of(res)
    if step.capture:
        hit = _ID_RE.search(txt)
        if hit:
            caps[step.capture] = hit.group(1)
    return res, txt


async def run_scripted_task(stack: str, task, render=False) -> Metrics:
    m = Metrics(task=task.name, stack=stack)
    params = StdioServerParameters(command=STACKS[stack][0], args=STACKS[stack][1:],
                                   env=_env_for(stack))
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), 40)
                caps: dict = {}
                for step in task.steps:
                    if step.mistake:
                        m.mistakes_planned += 1
                    res, txt = await _do_step(s, step, caps, m)

                    if step.mistake and is_techne_block(res, txt):
                        m.blocks += 1
                        m.mistakes_caught += 1
                        if step.block_token and step.block_token in txt:
                            m.correction_named_fix += 1
                        # agent reads the correction, applies it, retries
                        for fstep in (step.fix_steps or []):
                            await _do_step(s, fstep, caps, m)
                        if step.fix is not None:
                            retry = {**_resolve(step.args, caps), **step.fix}
                            rr = await _call(s, step.tool, retry)
                            m.tool_calls += 1
                            if getattr(rr, "isError", False):
                                m.errors.append(f"retry of {step.tool} still errored")
                                m.completed = False
                        elif step.fix_steps:
                            rr = await _call(s, step.tool, _resolve(step.args, caps))
                            m.tool_calls += 1
                            if getattr(rr, "isError", False):
                                m.errors.append(f"retry of {step.tool} still errored")
                                m.completed = False
                    elif step.mistake and is_techne_repair(txt):
                        m.repairs += 1
                        m.mistakes_caught += 1
                    elif step.mistake:
                        # no Technē block, no Technē repair: how did the stack react?
                        if getattr(res, "isError", False):
                            # the server rejected it loudly — safe, but no fix offered
                            m.rejected_loud += 1
                        else:
                            # it passed straight into the scene: the dangerous mode
                            m.leaked_silent += 1
                    else:
                        if getattr(res, "isError", False):
                            m.errors.append(f"clean step {step.tool} errored: {txt[:120]}")
                            m.completed = False

                if render:
                    await _score_render(s, m)
    except Exception as ex:
        m.completed = False
        m.errors.append(f"{type(ex).__name__}: {ex}")
    return m


async def _score_render(s, m: Metrics):
    try:
        sys.path.insert(0, f"{REPO}/techne")
        from techne.gate import inspect_render
        res = await _call(s, "render_current_scene", {"wait_ms": 6000}, t=90)
        png = _png_of(res)
        if not png:
            m.final_render = "error"
            return
        rec = inspect_render(png)
        m.final_render = "ok" if rec.non_blank else "blank"
        m.render_stddev = round(rec.stddev, 2)
    except Exception as ex:
        m.final_render = "error"
        m.errors.append(f"render: {type(ex).__name__}: {ex}")


def metrics_to_dict(m: Metrics) -> dict:
    return asdict(m)
