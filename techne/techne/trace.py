"""Point-1 instrumentation — verb-order trace logging.

Records the sequence of tool calls, decisions, and render results during a
session as JSONL. The traces are the raw material for discovering cross-call
ordering constraints empirically: which verb sequences precede clean renders,
which precede blanks, and whether a partial order emerges that warrants an
automaton.

Opt-in: enabled by TECHNE_PROFILE=instrumentation (or TECHNE_TRACE=1).
Writes to TECHNE_TRACE_DIR (default: ./techne_traces/), one file per session.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field as dc_field
from pathlib import Path
from typing import Any


@dataclass
class TraceEntry:
    call_index: int
    tool: str
    action: str                          # "forward" | "block"
    node_type: str = ""
    applied: list[str] = dc_field(default_factory=list)
    rewrote: bool = False
    blocked: bool = False
    corrections: list[str] = dc_field(default_factory=list)
    notes: list[str] = dc_field(default_factory=list)
    reminders: list[str] = dc_field(default_factory=list)
    state_mutation: dict | None = None   # what observe_result committed
    render: dict | None = None           # stddev, non_blank (render verbs only)
    ts: float = 0.0


class SessionTrace:
    """Collects trace entries for one session and flushes to JSONL on close."""

    def __init__(self, trace_dir: str | Path | None = None):
        self.session_id = uuid.uuid4().hex[:12]
        self._dir = Path(trace_dir or os.environ.get(
            "TECHNE_TRACE_DIR", "./techne_traces"))
        self._entries: list[TraceEntry] = []
        self._current: dict[int, TraceEntry] = {}  # call_index -> in-flight entry

    def record_decision(self, call_index: int, tool: str, args: dict,
                        action: str, applied: list[str], rewrote: bool,
                        corrections: list[str], notes: list[str],
                        reminders: list[str]) -> None:
        node_type = args.get("node_type", "")
        entry = TraceEntry(
            call_index=call_index,
            tool=tool,
            action=action,
            node_type=node_type,
            applied=list(applied),
            rewrote=rewrote,
            blocked=bool(corrections),
            corrections=list(corrections),
            notes=list(notes),
            reminders=[r[:80] for r in reminders],
            ts=time.monotonic(),
        )
        self._current[call_index] = entry
        self._entries.append(entry)

    def record_mutation(self, call_index: int, mutation: dict) -> None:
        entry = self._current.get(call_index)
        if entry:
            entry.state_mutation = mutation

    def record_render(self, call_index: int, stddev: float,
                      non_blank: bool) -> None:
        entry = self._current.get(call_index)
        if entry:
            entry.render = {"stddev": round(stddev, 3), "non_blank": non_blank}

    @property
    def entries(self) -> list[TraceEntry]:
        return list(self._entries)

    @property
    def clean(self) -> bool:
        """A session is clean if no calls were blocked and the last render
        (if any) was non-blank."""
        if any(e.blocked for e in self._entries):
            return False
        renders = [e for e in self._entries if e.render]
        if renders and not renders[-1].render["non_blank"]:
            return False
        return True

    def verb_sequence(self) -> list[str]:
        return [e.tool for e in self._entries]

    def summary(self) -> dict:
        renders = [e for e in self._entries if e.render]
        return {
            "session_id": self.session_id,
            "n_calls": len(self._entries),
            "n_blocks": sum(1 for e in self._entries if e.blocked),
            "n_repairs": sum(1 for e in self._entries if e.rewrote),
            "n_renders": len(renders),
            "clean": self.clean,
            "verb_sequence": self.verb_sequence(),
            "rules_fired": sorted({r for e in self._entries for r in e.applied}),
        }

    def flush(self) -> Path | None:
        if not self._entries:
            return None
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"trace_{self.session_id}.jsonl"
        with open(path, "w") as f:
            for entry in self._entries:
                f.write(json.dumps(asdict(entry), default=str) + "\n")
            f.write(json.dumps({"_summary": self.summary()}) + "\n")
        return path

    def close(self) -> Path | None:
        return self.flush()
