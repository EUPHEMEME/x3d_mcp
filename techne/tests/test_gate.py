"""Tests for the occupation gate (Point 3): blank detection, the cheap/expensive
graduation, and the hard human-sign-off boundary before irreversible work."""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from techne.gate import OccupationGate, CHEAP, EXPENSIVE       # noqa: E402

try:
    from PIL import Image
    _HAVE_PIL = True
except Exception:                                              # pragma: no cover
    _HAVE_PIL = False


def _png(kind: str) -> bytes:
    """A blank (solid) or non-blank (noisy) PNG."""
    if _HAVE_PIL:
        if kind == "blank":
            im = Image.new("L", (64, 64), 200)
        else:
            import random
            rnd = random.Random(0)
            im = Image.new("L", (64, 64))
            im.putdata([rnd.randint(0, 255) for _ in range(64 * 64)])
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()
    return b"\x89PNG\r\n\x1a\n"          # degenerate; fallback path handles it


def test_blank_render_is_blocked():
    g = OccupationGate(renderer=lambda s: _png("blank"))
    res = g.check("scene", CHEAP)
    assert not res.passed
    assert "blank" in res.blocked_reason
    assert res.corrections


def test_non_blank_cheap_passes():
    g = OccupationGate(renderer=lambda s: _png("noise"))
    res = g.check("scene", CHEAP)
    assert res.passed
    assert res.receipt and res.receipt.non_blank


def test_expensive_without_signoff_awaits_architect():
    g = OccupationGate(renderer=lambda s: _png("noise"))
    res = g.check("scene", EXPENSIVE, preview_path="/tmp/p.png")
    assert not res.passed
    assert res.awaiting_architect
    assert res.needs_human_signoff
    assert res.preview_path == "/tmp/p.png"


def test_expensive_with_signoff_passes():
    g = OccupationGate(renderer=lambda s: _png("noise"),
                       human_signoff=lambda: True)
    res = g.check("scene", EXPENSIVE)
    assert res.passed


def test_unclean_semantic_blocks_before_render():
    rendered = {"called": False}

    def renderer(s):
        rendered["called"] = True
        return _png("noise")

    g = OccupationGate(renderer=renderer,
                       semantic_validator=lambda s: "ERROR: containerField wrong")
    res = g.check("scene", CHEAP)
    assert not res.passed
    assert "not clean" in res.blocked_reason
    assert not rendered["called"]        # never rendered a known-bad scene


def test_clean_semantic_proceeds():
    g = OccupationGate(renderer=lambda s: _png("noise"),
                       semantic_validator=lambda s: "No issues found; scene is clean")
    res = g.check("scene", CHEAP)
    assert res.passed


def test_real_validator_all_clear_output_passes():
    # the actual x3d-mcp validate_semantic clean string (note: "Clear", not "clean")
    clean = "# Semantic Check: All Clear\n\nNo semantic issues found in the scene."
    g = OccupationGate(renderer=lambda s: _png("noise"),
                       semantic_validator=lambda s: clean)
    assert g.check("scene", CHEAP).passed


def test_real_validator_issue_output_blocks():
    dirty = ("# Semantic Check\n\n2 issues found:\n"
             "- containerField on HAnimJoint should be 'skeleton'")
    g = OccupationGate(renderer=lambda s: _png("noise"),
                       semantic_validator=lambda s: dirty)
    assert not g.check("scene", CHEAP).passed
