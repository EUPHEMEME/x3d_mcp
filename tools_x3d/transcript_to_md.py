#!/usr/bin/env python3
# transcript_to_md.py v1.0 2026-08-31 — render a Technē build transcript JSON as a one-page markdown audit appendix
"""Render build_anatomy/techne_transcript.json (HEADER/CALL/BLOCK/REPAIR
entries, written by build_anatomy_spine.py) as a one-page markdown appendix:
run header, totals, and a table of every proxied call with any repairs'
before/after args and blocks' prescriptive messages inlined.

Usage:
    python tools_x3d/transcript_to_md.py [transcript.json] [out.md]
Defaults:
    build_anatomy/techne_transcript.json -> build_anatomy/TRANSCRIPT.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_IN = REPO / "build_anatomy" / "techne_transcript.json"
DEFAULT_OUT = REPO / "build_anatomy" / "TRANSCRIPT.md"


def _cell(s: object, limit: int = 120) -> str:
    """One markdown table cell: flatten, escape pipes, cap length."""
    text = " ".join(str(s).split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|") or "—"


def _args_str(args: object) -> str:
    """BLOCK/REPAIR entries carry raw arg dicts; CALL entries a brief string."""
    if isinstance(args, dict):
        return ", ".join(f"{k}={v}" for k, v in args.items())
    return str(args)


def render(entries: list[dict]) -> str:
    header = next((e for e in entries if e.get("kind") == "HEADER"), {})
    calls = [e for e in entries if e.get("kind") == "CALL"]
    blocks = [e for e in entries if e.get("kind") == "BLOCK"]
    repairs = [e for e in entries if e.get("kind") == "REPAIR"]

    lines: list[str] = []
    lines.append("# Technē build transcript — studio spine")
    lines.append("")
    lines.append("Audit log of `build_anatomy_spine.py` authoring "
                 "`build_anatomy/studio_spine.x3d` call-by-call through the "
                 "Technē stdio proxy.")
    lines.append("")

    lines.append("## Run header")
    lines.append("")
    if header:
        lines.append(f"- **Timestamp:** {header.get('timestamp', '—')}")
        lines.append(f"- **Technē git SHA:** `{header.get('techne_sha', '—')}`")
        lines.append(f"- **TECHNE_PROFILE:** `{header.get('techne_profile', '—')}`")
    else:
        lines.append("- *No HEADER entry — transcript predates v1.1 logging "
                     "or the run never started.*")
    lines.append("")

    lines.append("## Totals")
    lines.append("")
    lines.append("| tool calls | blocked | repaired |")
    lines.append("|---:|---:|---:|")
    lines.append(f"| {len(calls)} | {len(blocks)} | {len(repairs)} |")
    lines.append("")
    if not blocks and not repairs:
        lines.append("Clean run: every call passed the rule engine unmodified.")
        lines.append("")

    # Interventions first — they are the point of the audit.
    if blocks:
        lines.append("## Blocks")
        lines.append("")
        lines.append("| # | tool | args | prescriptive message |")
        lines.append("|---:|---|---|---|")
        for i, b in enumerate(blocks, 1):
            lines.append(f"| {i} | `{_cell(b.get('tool'))}` "
                         f"| {_cell(_args_str(b.get('args')))} "
                         f"| {_cell(b.get('response'), 400)} |")
        lines.append("")

    if repairs:
        lines.append("## Repairs")
        lines.append("")
        lines.append("| # | tool | args as sent (before) | proxy response (after) |")
        lines.append("|---:|---|---|---|")
        for i, r in enumerate(repairs, 1):
            lines.append(f"| {i} | `{_cell(r.get('tool'))}` "
                         f"| {_cell(_args_str(r.get('args')), 200)} "
                         f"| {_cell(r.get('response'), 300)} |")
        lines.append("")

    lines.append("## Calls")
    lines.append("")
    lines.append("| # | tool | args |")
    lines.append("|---:|---|---|")
    for i, c in enumerate(calls, 1):
        lines.append(f"| {i} | `{_cell(c.get('tool'))}` "
                     f"| {_cell(_args_str(c.get('args')), 160)} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    src = Path(argv[1]) if len(argv) > 1 else DEFAULT_IN
    dst = Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT
    entries = json.loads(src.read_text())
    if not isinstance(entries, list):
        print(f"error: {src} is not a JSON list", file=sys.stderr)
        return 1
    md = render(entries)
    dst.write_text(md)
    n = sum(1 for e in entries if e.get("kind") == "CALL")
    print(f"{dst}  ({len(md)} bytes; {n} calls, "
          f"{sum(1 for e in entries if e.get('kind') == 'BLOCK')} blocks, "
          f"{sum(1 for e in entries if e.get('kind') == 'REPAIR')} repairs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
