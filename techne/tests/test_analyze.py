"""Tests for techne.analyze_traces — synthetic trace data, no MCP needed."""
import json
import tempfile
from pathlib import Path

from techne.analyze_traces import (
    AnalysisResult,
    ParsedSession,
    analyze,
    load_all,
    load_session,
)


# ---------------------------------------------------------------------------
# helpers — write synthetic JSONL trace files
# ---------------------------------------------------------------------------

def _entry(tool: str, action: str = "forward", blocked: bool = False,
           render: dict | None = None, node_type: str = "") -> dict:
    return {
        "call_index": 0,
        "tool": tool,
        "action": action,
        "node_type": node_type,
        "applied": [],
        "rewrote": False,
        "blocked": blocked,
        "corrections": [],
        "notes": [],
        "reminders": [],
        "state_mutation": None,
        "render": render,
        "ts": 0.0,
    }


def _summary(entries: list[dict], clean: bool) -> dict:
    verbs = [e["tool"] for e in entries]
    return {
        "_summary": {
            "session_id": "test",
            "n_calls": len(entries),
            "n_blocks": sum(1 for e in entries if e["blocked"]),
            "n_repairs": 0,
            "n_renders": sum(1 for e in entries if e.get("render")),
            "clean": clean,
            "verb_sequence": verbs,
            "rules_fired": [],
        }
    }


def _write_trace(tmp: Path, name: str, entries: list[dict], clean: bool) -> Path:
    p = tmp / name
    lines = [json.dumps(e) for e in entries]
    lines.append(json.dumps(_summary(entries, clean)))
    p.write_text("\n".join(lines) + "\n")
    return p


# ---------------------------------------------------------------------------
# A clean session: create_node -> create_node -> render_image (non-blank)
# ---------------------------------------------------------------------------

CLEAN_ENTRIES = [
    _entry("create_node", node_type="Box"),
    _entry("create_node", node_type="PhysicalMaterial"),
    _entry("render_image", render={"stddev": 42.5, "non_blank": True}),
]

# ---------------------------------------------------------------------------
# An unclean session: create_node -> bad interpolator (blocked) -> render
# ---------------------------------------------------------------------------

UNCLEAN_ENTRIES = [
    _entry("create_node", node_type="Box"),
    _entry("create_node", action="block", blocked=True,
           node_type="OrientationInterpolator"),
    _entry("render_image", render={"stddev": 1.2, "non_blank": False}),
]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def test_load_session_clean():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_trace(Path(tmp), "trace_clean.jsonl", CLEAN_ENTRIES, True)
        s = load_session(p)
        assert s is not None
        assert s.clean is True
        assert len(s.entries) == 3
        assert s.verbs == ["create_node", "create_node", "render_image"]


def test_load_session_unclean():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_trace(Path(tmp), "trace_unclean.jsonl", UNCLEAN_ENTRIES, False)
        s = load_session(p)
        assert s is not None
        assert s.clean is False
        assert len(s.entries) == 3


def test_load_all_finds_both():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _write_trace(tmp, "trace_a.jsonl", CLEAN_ENTRIES, True)
        _write_trace(tmp, "trace_b.jsonl", UNCLEAN_ENTRIES, False)
        sessions = load_all(tmp)
        assert len(sessions) == 2
        clean = [s for s in sessions if s.clean]
        unclean = [s for s in sessions if not s.clean]
        assert len(clean) == 1
        assert len(unclean) == 1


def test_load_skips_non_jsonl():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "readme.txt").write_text("not a trace")
        _write_trace(tmp, "trace_ok.jsonl", CLEAN_ENTRIES, True)
        sessions = load_all(tmp)
        assert len(sessions) == 1


def test_load_empty_dir():
    with tempfile.TemporaryDirectory() as tmp:
        sessions = load_all(tmp)
        assert sessions == []


# ---------------------------------------------------------------------------
# Bigram extraction
# ---------------------------------------------------------------------------

def test_bigrams_clean():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_trace(Path(tmp), "trace_c.jsonl", CLEAN_ENTRIES, True)
        s = load_session(p)
        assert s.bigrams == [
            ("create_node", "create_node"),
            ("create_node", "render_image"),
        ]


def test_bigrams_unclean():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_trace(Path(tmp), "trace_d.jsonl", UNCLEAN_ENTRIES, False)
        s = load_session(p)
        assert s.bigrams == [
            ("create_node", "create_node"),
            ("create_node", "render_image"),
        ]


# ---------------------------------------------------------------------------
# Analysis — separation and unclean-only detection
# ---------------------------------------------------------------------------

def test_analyze_separates_clean_unclean():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _write_trace(tmp, "trace_e.jsonl", CLEAN_ENTRIES, True)
        _write_trace(tmp, "trace_f.jsonl", UNCLEAN_ENTRIES, False)
        sessions = load_all(tmp)
        result = analyze(sessions)
        assert result.total == 2
        assert result.clean_count == 1
        assert result.unclean_count == 1


def test_analyze_finds_unclean_only_bigrams():
    """When a bigram appears ONLY in unclean sessions, flag it."""
    # Build a scenario where unclean has a unique bigram.
    unclean_entries = [
        _entry("set_field"),                    # unique verb for unclean
        _entry("create_node", blocked=True),    # block
        _entry("render_image", render={"stddev": 1.0, "non_blank": False}),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _write_trace(tmp, "trace_clean.jsonl", CLEAN_ENTRIES, True)
        _write_trace(tmp, "trace_bad.jsonl", unclean_entries, False)
        sessions = load_all(tmp)
        result = analyze(sessions)
        # (set_field, create_node) only appears in the unclean session
        assert ("set_field", "create_node") in result.unclean_only_bigrams
        # (create_node, create_node) appears in both, so NOT unclean-only
        assert ("create_node", "create_node") not in result.unclean_only_bigrams


def test_analyze_pre_render_sequences():
    """Pre-render verb windows are extracted only from clean sessions."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _write_trace(tmp, "trace_g.jsonl", CLEAN_ENTRIES, True)
        _write_trace(tmp, "trace_h.jsonl", UNCLEAN_ENTRIES, False)
        sessions = load_all(tmp)
        result = analyze(sessions)
        # Clean session: [create_node, create_node] -> render_image
        assert ("create_node", "create_node") in result.pre_render_sequences
        assert result.pre_render_sequences[("create_node", "create_node")] == 1


def test_analyze_all_clean():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _write_trace(tmp, "trace_i.jsonl", CLEAN_ENTRIES, True)
        _write_trace(tmp, "trace_j.jsonl", CLEAN_ENTRIES, True)
        sessions = load_all(tmp)
        result = analyze(sessions)
        assert result.clean_count == 2
        assert result.unclean_count == 0
        assert result.unclean_only_bigrams == set()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_single_entry_no_bigrams():
    """A session with one entry has no bigrams."""
    entries = [_entry("create_node", node_type="Sphere")]
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_trace(Path(tmp), "trace_k.jsonl", entries, True)
        s = load_session(p)
        assert s.bigrams == []


def test_load_session_no_summary_line():
    """Trace file without a _summary line still loads (recomputes clean)."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "trace_nosummary.jsonl"
        lines = [json.dumps(e) for e in CLEAN_ENTRIES]
        p.write_text("\n".join(lines) + "\n")
        s = load_session(p)
        assert s is not None
        assert s.clean is True
        assert s.verbs == ["create_node", "create_node", "render_image"]
