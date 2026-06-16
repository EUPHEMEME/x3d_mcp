"""Deterministic argument repair — the SAP (Schema-Aligned Parsing) move, applied
to the tool-call arguments a model emits into an MCP server (TECHNE_SPEC §1).

BAML's SAP is the productized, edit-distance version of this for LLM *output*;
here we apply the same Postel's-law principle ("be liberal in what you accept,
transform it to match the schema") to MCP *tool-call args*, which is the novel
redirection. This is intentionally conservative and deterministic — it only
unwraps and coerces shape, never invents content. The semantic craft-rules
(craft.py) run after this on the cleaned args.

When the real BAML client is generated (baml_src/), `b.parse.<Function>(json)`
can replace this with the full edit-distance engine; this module is the
dependency-free baseline so Technē runs out of the box.
"""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"^\s*```(?:json|python|tool_code)?\s*|\s*```\s*$",
                    re.IGNORECASE)
_FIRST_OBJ = re.compile(r"\{.*\}", re.DOTALL)


def _strip_preamble(s: str) -> str:
    """Drop markdown fences and any chain-of-thought before the first JSON object."""
    s = _FENCE.sub("", s.strip())
    m = _FIRST_OBJ.search(s)
    return m.group(0) if m else s


def _maybe_json(v: Any) -> Any:
    """If a string is actually JSON for a dict/list, parse it; else return as-is."""
    if not isinstance(v, str):
        return v
    t = v.strip()
    if t[:1] in "{[" or _FENCE.search(t):
        try:
            return json.loads(_strip_preamble(t))
        except (ValueError, TypeError):
            return v
    return v


def _coerce_scalar(v: Any) -> Any:
    """Coerce obvious scalar strings: 'true'/'false' -> bool, numeric -> number."""
    if not isinstance(v, str):
        return v
    t = v.strip()
    low = t.lower()
    if low in ("true", "false"):
        return low == "true"
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d*\.\d+(e-?\d+)?", t, re.IGNORECASE):
        return float(t)
    return v


# keys whose values are structured (dict/list) and worth un-stringifying
_STRUCTURED_KEYS = {"fields", "value", "arguments", "args"}


def sap_repair(args: Any) -> dict:
    """Return a cleaned argument dict. Never raises; worst case returns {} or the
    original dict so the caller can still forward."""
    if isinstance(args, str):
        try:
            parsed = json.loads(_strip_preamble(args))
            args = parsed if isinstance(parsed, dict) else {"value": parsed}
        except (ValueError, TypeError):
            return {}
    if not isinstance(args, dict):
        return {}
    out: dict = {}
    for k, v in args.items():
        if k in _STRUCTURED_KEYS:
            v = _maybe_json(v)
        if isinstance(v, dict):
            v = {kk: _maybe_json(vv) for kk, vv in v.items()}
        elif k == "global" or k.endswith("_bool"):
            v = _coerce_scalar(v)
        out[k] = v
    # coerce scalar leaves inside a 'fields' dict (e.g. "global": "true")
    if isinstance(out.get("fields"), dict):
        out["fields"] = {kk: _coerce_scalar(vv) if kk in ("global",) else vv
                         for kk, vv in out["fields"].items()}
    return out
