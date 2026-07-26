"""Tests for the occupation gate (Point 3): blank detection, the cheap/expensive
graduation, and the hard human-sign-off boundary before irreversible work."""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from techne.config import Config                               # noqa: E402
from techne.gate import OccupationGate, CHEAP, EXPENSIVE       # noqa: E402

try:
    from PIL import Image
    _HAVE_PIL = True
except Exception:                                              # pragma: no cover
    _HAVE_PIL = False


def _png(kind: str, seed: int = 0) -> bytes:
    """A blank (solid) or non-blank (noisy) PNG. Distinct seeds give distinct
    (but each internally deterministic) noisy frames — needed by the differential
    tests, where 'these two renders differ' is the observable."""
    if _HAVE_PIL:
        if kind == "blank":
            im = Image.new("L", (64, 64), 200)
        else:
            import random
            rnd = random.Random(seed)
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


# --- differential wiring (opt-in verify-by-differential-render) -------------

# Two Shapes with DEF names the fake renderers can key on: 'Real' draws pixels,
# 'Ghost' is in the document but contributes nothing to the image.
_DIFF_SCENE = ("<X3D><Scene>"
               "<Shape DEF='Real'><Box/></Shape>"
               "<Shape DEF='Ghost'><Sphere/></Shape>"
               "</Scene></X3D>")


def _ghost_renderer(s: str) -> bytes:
    """The image depends ONLY on whether 'Real' survives: removing 'Ghost'
    changes nothing (it is absent from the render), removing 'Real' does."""
    return _png("noise") if "Real" in s else _png("noise", seed=1)


def test_differential_off_by_default_renders_exactly_once():
    calls = {"n": 0}

    def renderer(s):
        calls["n"] += 1
        return _png("noise")

    cfg = Config.from_env({})            # hermetic: ignore the real environment
    assert not cfg.differential          # OFF by default — it costs N+1 renders
    res = OccupationGate(renderer=renderer, config=cfg).check(_DIFF_SCENE, CHEAP)
    assert res.passed
    assert res.differential is None      # never attempted, not merely empty
    assert calls["n"] == 1               # only the single blank-check render


def test_differential_advises_by_default_and_blocks_only_on_opt_in():
    # DEFAULT is advisory: zero pixel change is a real signal but not proof of a defect
    # (occlusion, out-of-frustum, coincident DEF/USE all produce it for correct scenes),
    # so a finding must inform rather than refuse until an operator opts in.
    cfg = Config.from_env({"TECHNE_DIFFERENTIAL": "1"})
    assert cfg.differential and not cfg.differential_blocks
    g = OccupationGate(renderer=_ghost_renderer, config=cfg)
    res = g.check(_DIFF_SCENE, CHEAP)
    assert res.passed                                    # advisory, not a refusal
    assert any("Ghost" in n for n in res.notes)          # ...but the finding is surfaced
    assert not res.corrections                           # notes inform; corrections block

    # OPT-IN blocking still works, and carries the prescriptive correction.
    bcfg = Config.from_env({"TECHNE_DIFFERENTIAL": "block"})
    assert bcfg.differential and bcfg.differential_blocks
    res = OccupationGate(renderer=_ghost_renderer, config=bcfg).check(_DIFF_SCENE, CHEAP)
    assert not res.passed
    assert "absent from the image" in res.blocked_reason
    # findings are structured data on the result, inspectable without re-running
    assert res.differential is not None and res.differential.ran
    absent = [c.ident for c in res.differential.absent]
    assert "Ghost" in absent and "Real" not in absent
    # the error message IS the fix (differential.correction_for's contract)
    assert any("Ghost" in c and "contributes no pixels" in c
               for c in res.corrections)


def test_differential_skipped_when_scene_is_blank():
    # ordering: never spend N renders restating a failure the cheap check found
    calls = {"n": 0}

    def renderer(s):
        calls["n"] += 1
        return _png("blank")

    g = OccupationGate(renderer=renderer,
                       config=Config.from_env({"TECHNE_DIFFERENTIAL": "1"}))
    res = g.check(_DIFF_SCENE, CHEAP)
    assert not res.passed and "blank" in res.blocked_reason
    assert calls["n"] == 1               # the blank verdict cost ONE render
    assert res.differential is None


def test_differential_skipped_when_semantics_unclean():
    calls = {"n": 0}

    def renderer(s):
        calls["n"] += 1
        return _png("noise")

    g = OccupationGate(renderer=renderer,
                       semantic_validator=lambda s: "ERROR: containerField wrong",
                       config=Config.from_env({"TECHNE_DIFFERENTIAL": "1"}))
    res = g.check(_DIFF_SCENE, CHEAP)
    assert not res.passed and calls["n"] == 0 and res.differential is None


def test_differential_undecidable_never_blocks():
    # fail-safe asymmetry: the gate's own render succeeded, then the renderer
    # died under the differential — an unknown must never become a block.
    calls = {"n": 0}

    def renderer(s):
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("renderer fell over")
        return _png("noise")

    g = OccupationGate(renderer=renderer,
                       config=Config.from_env({"TECHNE_DIFFERENTIAL": "1"}))
    res = g.check(_DIFF_SCENE, CHEAP)
    # Asserted as an INVARIANT, not a mechanism. Depending on whether the caller supplied a
    # baseline render, an undecidable differential either aborts wholesale (ran=False, with a
    # result-level note) or runs and credits every node individually (ran=True, per-node notes).
    # Both are correct behaviours; what must never vary is that nothing is ACCUSED of absence and
    # the reason survives for inspection.
    assert res.passed                                       # undecidable != absent
    assert res.differential is not None
    assert not res.differential.absent                      # nothing accused => nothing blocks
    assert res.differential.note or all(
        c.note for c in res.differential.contributions)     # the why rides along, inspectable


def test_differential_blocks_before_expensive_signoff():
    # never surface a preview for architect sign-off when a deterministic check
    # can already prove it incomplete
    # (only in opt-in blocking mode; advisory findings must not gate the architect)
    g = OccupationGate(renderer=_ghost_renderer,
                       config=Config.from_env({"TECHNE_DIFFERENTIAL": "block"}))
    res = g.check(_DIFF_SCENE, EXPENSIVE)
    assert not res.passed
    assert not res.needs_human_signoff          # never ask the architect to bless a known gap
    assert "absent from the image" in res.blocked_reason


def test_differential_all_contributing_passes_with_findings_attached():
    def renderer(s):
        has_real, has_ghost = "Real" in s, "Ghost" in s
        if has_real and has_ghost:
            return _png("noise")
        return _png("noise", seed=1 if has_real else 2)

    g = OccupationGate(renderer=renderer,
                       config=Config.from_env({"TECHNE_DIFFERENTIAL": "1"}))
    res = g.check(_DIFF_SCENE, CHEAP)
    assert res.passed
    assert res.differential is not None and res.differential.ran
    assert res.differential.absent == []
    assert len(res.differential.contributions) == 2
