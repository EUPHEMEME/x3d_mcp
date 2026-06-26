"""Scripted scoreboard — run every task through both stacks and tabulate.

    PYTHONPATH=techne .venv/bin/python techne/eval/run_scripted.py [--render] [--json out.json]

Deterministic, no API key, CI-able. The render column is opt-in (needs Playwright)
and only meaningful for tasks that build a full renderable scene; the current set
is scored on the deterministic columns (mistakes caught/leaked, round-trips).
"""
import argparse
import asyncio
import json
import sys

from eval.harness import run_scripted_task, metrics_to_dict, _want_trace
from eval.tasks import SCRIPTED


def _fmt_row(cells, widths):
    return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))


def print_table(rows):
    hdr = ["task", "stack", "calls", "caught", "leaked", "loud", "render"]
    widths = [20, 7, 6, 7, 7, 6, 7]
    print(_fmt_row(hdr, widths))
    print(_fmt_row(["-" * w for w in widths], widths))
    for m in rows:
        n = m.mistakes_planned
        caught = f"{m.mistakes_caught}/{n}"
        leaked = f"{m.leaked_silent}/{n}"
        loud = f"{m.rejected_loud}/{n}"
        render = m.final_render if m.final_render != "skip" else "-"
        print(_fmt_row([m.task, m.stack, m.tool_calls, caught, leaked, loud, render], widths))


def summarize(rows):
    planned = sum(m.mistakes_planned for m in rows if m.stack == "raw")
    raw_silent = sum(m.leaked_silent for m in rows if m.stack == "raw")
    raw_loud = sum(m.rejected_loud for m in rows if m.stack == "raw")
    tec_silent = sum(m.leaked_silent for m in rows if m.stack == "techne")
    tec_caught = sum(m.mistakes_caught for m in rows if m.stack == "techne")
    named = sum(m.correction_named_fix for m in rows if m.stack == "techne")
    extra = (sum(m.tool_calls for m in rows if m.stack == "techne")
             - sum(m.tool_calls for m in rows if m.stack == "raw"))
    print("\nsummary")
    print(f"  documented mistakes planned              : {planned}")
    print(f"  raw — passed SILENTLY into the scene     : {raw_silent}/{planned}")
    print(f"  raw — rejected loudly, no fix offered    : {raw_loud}/{planned}")
    print(f"  Technē — passed silently into the scene  : {tec_silent}/{planned}")
    print(f"  Technē — caught (block or repair)        : {tec_caught}/{planned}")
    print(f"  Technē blocks whose text named the fix   : {named}/{tec_caught}")
    print(f"  extra round-trips to a CORRECT scene     : +{extra} over {len(SCRIPTED)} tasks")
    print(f"    (incl. authoring the missing DEF; raw used fewer calls but shipped")
    print(f"     {raw_silent} silently-wrong + {raw_loud} loudly-rejected/broken scenes)")
    traces = [(m.task, m.trace_path) for m in rows if m.trace_path]
    if traces:
        print("  traces:")
        for t, p in traces:
            print(f"    {t}: {p}")
    errs = [(m.task, m.stack, e) for m in rows for e in m.errors]
    if errs:
        print("  notes / errors:")
        for t, st, e in errs:
            print(f"    [{st}/{t}] {e}")


async def main(render: bool, json_out: str | None, trace: bool = False):
    rows = []
    for task in SCRIPTED:
        for stack in ("raw", "techne"):
            rows.append(await run_scripted_task(stack, task, render=render, trace=trace))
    rows.sort(key=lambda m: (m.task, m.stack))
    print_table(rows)
    summarize(rows)
    if json_out:
        json.dump([metrics_to_dict(m) for m in rows], open(json_out, "w"), indent=2)
        print(f"\nwrote {json_out}")
    # exit non-zero if Technē ever leaked a mistake or broke a clean task
    bad = [m for m in rows if m.stack == "techne" and (m.leaked_silent or not m.completed)]
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="also score a final render (needs Playwright)")
    ap.add_argument("--trace", action="store_true",
                    help="enable Point-1 instrumentation (also via TECHNE_TRACE=1)")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()
    trace = args.trace or _want_trace()
    sys.exit(asyncio.run(main(args.render, args.json_out, trace=trace)))
