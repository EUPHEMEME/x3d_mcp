"""Point-1 trace analyzer — discover verb-order patterns from JSONL traces.

Reads trace files written by SessionTrace.flush(), separates clean from
unclean sessions, extracts verb bigrams, and reports which orderings
correlate with failures.  Pure discovery tool, no dependencies beyond stdlib.

Usage:
    python -m techne.analyze_traces [trace_dir]

If trace_dir is omitted, defaults to ./techne_traces/.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ParsedSession:
    """One trace file parsed into its useful parts."""
    path: str
    entries: list[dict]
    summary: dict
    clean: bool
    verbs: list[str]
    bigrams: list[tuple[str, str]]


def _bigrams(verbs: list[str]) -> list[tuple[str, str]]:
    return [(verbs[i], verbs[i + 1]) for i in range(len(verbs) - 1)]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_session(path: Path) -> ParsedSession | None:
    """Parse a single .jsonl trace file.  Returns None on bad data."""
    entries: list[dict] = []
    summary: dict = {}
    try:
        text = path.read_text()
    except OSError:
        return None
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "_summary" in obj:
            summary = obj["_summary"]
        else:
            entries.append(obj)
    if not entries:
        return None

    # Derive clean flag from summary if present, otherwise recompute.
    if summary:
        clean = summary.get("clean", True)
        verbs = summary.get("verb_sequence", [e.get("tool", "") for e in entries])
    else:
        has_block = any(e.get("blocked") for e in entries)
        renders = [e for e in entries if e.get("render")]
        last_render_blank = (renders and not renders[-1]["render"].get("non_blank", True))
        clean = not has_block and not last_render_blank
        verbs = [e.get("tool", "") for e in entries]

    return ParsedSession(
        path=str(path),
        entries=entries,
        summary=summary,
        clean=clean,
        verbs=verbs,
        bigrams=_bigrams(verbs),
    )


def load_all(trace_dir: str | Path) -> list[ParsedSession]:
    """Load every .jsonl file in trace_dir."""
    d = Path(trace_dir)
    if not d.is_dir():
        return []
    sessions = []
    for p in sorted(d.glob("*.jsonl")):
        s = load_session(p)
        if s is not None:
            sessions.append(s)
    return sessions


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    total: int = 0
    clean_count: int = 0
    unclean_count: int = 0
    clean_bigrams: Counter = dc_field(default_factory=Counter)
    unclean_bigrams: Counter = dc_field(default_factory=Counter)
    unclean_only_bigrams: set = dc_field(default_factory=set)
    pre_render_sequences: Counter = dc_field(default_factory=Counter)


def _pre_render_verbs(verbs: list[str], window: int = 3) -> list[str]:
    """Return verb windows that immediately precede a render verb."""
    results = []
    for i, v in enumerate(verbs):
        if v == "render_image":
            start = max(0, i - window)
            prefix = tuple(verbs[start:i])
            if prefix:
                results.append(prefix)
    return results


def analyze(sessions: list[ParsedSession]) -> AnalysisResult:
    """Run the full analysis across a list of parsed sessions."""
    r = AnalysisResult(total=len(sessions))

    for s in sessions:
        if s.clean:
            r.clean_count += 1
            for bg in s.bigrams:
                r.clean_bigrams[bg] += 1
        else:
            r.unclean_count += 1
            for bg in s.bigrams:
                r.unclean_bigrams[bg] += 1

        # Pre-render sequences only from clean sessions (successful renders).
        if s.clean:
            for prefix in _pre_render_verbs(s.verbs):
                r.pre_render_sequences[prefix] += 1

    r.unclean_only_bigrams = set(r.unclean_bigrams) - set(r.clean_bigrams)
    return r


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_report(r: AnalysisResult) -> str:
    lines: list[str] = []
    lines.append(f"Sessions: {r.total}  (clean: {r.clean_count}, unclean: {r.unclean_count})")
    lines.append("")

    # Unclean-only bigrams
    lines.append("--- Bigrams ONLY in unclean sessions (candidate ordering constraints) ---")
    if r.unclean_only_bigrams:
        for bg in sorted(r.unclean_only_bigrams):
            lines.append(f"  {bg[0]} -> {bg[1]}  (x{r.unclean_bigrams[bg]})")
    else:
        lines.append("  (none)")
    lines.append("")

    # Pre-render sequences
    lines.append("--- Verb sequences preceding successful renders ---")
    if r.pre_render_sequences:
        for seq, count in r.pre_render_sequences.most_common(20):
            arrow = " -> ".join(seq)
            lines.append(f"  {arrow} -> render_image  (x{count})")
    else:
        lines.append("  (none)")
    lines.append("")

    # All bigram tallies
    all_bigrams = r.clean_bigrams + r.unclean_bigrams
    lines.append("--- All bigrams (combined) ---")
    for bg, count in all_bigrams.most_common(30):
        tag = ""
        if bg in r.unclean_only_bigrams:
            tag = "  [UNCLEAN-ONLY]"
        elif bg not in r.clean_bigrams:
            tag = "  [unclean-only]"
        lines.append(f"  {bg[0]} -> {bg[1]}  (x{count}){tag}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    trace_dir = args[0] if args else "./techne_traces"
    sessions = load_all(trace_dir)
    if not sessions:
        print(f"No trace files found in {trace_dir}")
        sys.exit(1)
    result = analyze(sessions)
    print(format_report(result))


if __name__ == "__main__":
    main()
