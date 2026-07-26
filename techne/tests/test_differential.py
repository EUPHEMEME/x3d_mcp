"""Tests for verify-by-differential-render (differential.py): candidate discovery,
scene surgery, the serialization-not-a-confound guarantee, pixel-comparison
fail-safes, and the central contributed/absent verdicts.

All rendering is FAKED with a deterministic scene-string -> PNG-bytes function
(mirroring test_gate.py's synthesized PNGs), so the tests need no browser and
every pixel count is exact: each marker name present in the scene string paints
its own disjoint block of known size, so removing the node that carries the
marker changes exactly that many pixels — and removing a node with no footprint
changes exactly zero, which is the silent failure this module exists to catch."""
import io
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402

from techne.differential import (                              # noqa: E402
    NodeContribution,
    candidates,
    compare,
    contributions,
    correction_for,
    roundtrip,
    scene_without,
)

try:
    from PIL import Image
    _HAVE_PIL = True
except Exception:                                              # pragma: no cover
    _HAVE_PIL = False

# Pixel-count assertions need a real decoder; without Pillow, compare() falls
# back to byte identity and the flag-level tests below still exercise the logic.
needs_pil = pytest.mark.skipif(not _HAVE_PIL, reason="pixel counting needs Pillow")

W = H = 64
BG = 40


def _fake_renderer(footprints):
    """A deterministic scene->PNG function. `footprints` maps marker name ->
    pixel count; every marker present in the scene string paints that many
    pixels in its own 4-row band (disjoint per marker, so diffs never overlap).
    Without Pillow, the fallback returns bytes identical iff the same markers
    are present — exactly what compare()'s byte-identity fallback needs."""
    order = sorted(footprints)

    def render(scene_xml: str) -> bytes:
        if _HAVE_PIL:
            data = [BG] * (W * H)
            for k, name in enumerate(order):
                if name in scene_xml:
                    start = k * 4 * W          # this marker's private band
                    for j in range(footprints[name]):
                        data[start + j] = 255
            im = Image.new("L", (W, H))
            im.putdata(data)
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return buf.getvalue()
        present = ",".join(n for n in order if n in scene_xml)
        return b"fake-png:" + present.encode()

    return render


# The workhorse scene, written in ElementTree's own output style (double quotes,
# space before "/>") so roundtrip(SCENE) == SCENE exactly. Document-order walk:
# X3D[0] Scene[1] Shape[2] Box[3] Shape[4] Sphere[5] HAnimHumanoid[6]
# ImageTexture[7] DirectionalLight[8].
SCENE = (
    '<X3D><Scene>'
    '<Shape DEF="VIS_A"><Box /></Shape>'
    '<Shape DEF="GHOST"><Sphere /></Shape>'
    '<HAnimHumanoid name="HUMAN" />'
    '<ImageTexture DEF="SKIN" url="skin.png" />'
    '<DirectionalLight DEF="SUN" />'
    '</Scene></X3D>'
)

# GHOST deliberately has NO footprint: it is in the document, absent from the
# image — the exact case the differential check exists to catch.
FOOTPRINTS = {"VIS_A": 64, "HUMAN": 64, "SKIN": 64, "SUN": 64}


def _by_ident(result, ident):
    return next(c for c in result.contributions if c.ident == ident)


# --- candidates() ------------------------------------------------------------

def test_candidates_finds_all_significant_nodes():
    # Shapes, the humanoid, the texture, and the light — with document-order
    # indices matching the walk that scene_without() removes by.
    assert candidates(SCENE) == [
        (2, "Shape", "VIS_A"),
        (4, "Shape", "GHOST"),
        (6, "HAnimHumanoid", "HUMAN"),
        (7, "ImageTexture", "SKIN"),
        (8, "DirectionalLight", "SUN"),
    ]


def test_candidates_max_nodes_and_tag_filter():
    assert candidates(SCENE, max_nodes=2) == [
        (2, "Shape", "VIS_A"),
        (4, "Shape", "GHOST"),
    ]
    assert candidates(SCENE, tags=("ImageTexture",)) == [(7, "ImageTexture", "SKIN")]


def test_candidates_unparseable_returns_empty():
    assert candidates("<X3D><oops") == []
    assert candidates("") == []
    assert candidates("plain prose, not XML") == []


def test_candidates_ident_prefers_def_then_name_then_position():
    scene = ('<X3D><Scene>'
             '<Shape DEF="D" name="n" />'        # DEF wins over name
             '<HAnimHumanoid name="justname" />'  # name when no DEF
             '<Shape />'                          # nothing: positional fallback
             '</Scene></X3D>')
    cands = candidates(scene)
    assert cands[0][2] == "D"
    assert cands[1][2] == "justname"
    i, tag, ident = cands[2]
    # the fallback handle encodes the SAME document-order index the candidate
    # reports, so it stays a stable pointer into the walk
    assert ident == "%s[%d]" % (tag, i)


def test_candidates_strips_xml_namespace():
    ns = '<X3D xmlns="urn:web3d:x3d"><Scene><Shape DEF="NS" /></Scene></X3D>'
    assert candidates(ns) == [(2, "Shape", "NS")]


# --- scene_without() ---------------------------------------------------------

def test_scene_without_removes_the_whole_subtree():
    out = scene_without(SCENE, 2)                # the VIS_A Shape, child Box
    assert out is not None
    assert "VIS_A" not in out and "Box" not in out   # node AND its child gone
    for marker in ("GHOST", "Sphere", "HUMAN", "SKIN", "SUN"):
        assert marker in out                     # everything else survives
    ET.fromstring(out)                           # still well-formed XML


def test_scene_without_root_and_out_of_range_return_none():
    assert scene_without(SCENE, 0) is None       # the root has no parent
    assert scene_without(SCENE, -3) is None
    n = len(list(ET.fromstring(SCENE).iter()))
    assert scene_without(SCENE, n) is None       # one past the end
    assert scene_without(SCENE, 999) is None


def test_scene_without_bad_xml_returns_none():
    assert scene_without("<X3D><broken", 1) is None


# --- roundtrip() and the anti-confound guarantee -----------------------------

def test_roundtrip_reserializes_and_is_idempotent():
    # SCENE is written in ET's output style, so the roundtrip is exact
    assert roundtrip(SCENE) == SCENE
    # messier authoring (single quotes, whitespace) reaches a stable fixed
    # point after ONE roundtrip — which is why contributions() renders the
    # round-tripped baseline, never the original string
    messy = "<X3D><Scene>\n  <Shape DEF='Q'/>\n</Scene></X3D>"
    once = roundtrip(messy)
    assert once is not None
    ET.fromstring(once)
    assert roundtrip(once) == once


def test_roundtrip_bad_xml_returns_none():
    assert roundtrip("<X3D><unclosed") is None
    assert roundtrip("not xml at all") is None


def test_removal_differs_only_by_the_removed_subtree():
    """THE anti-confound guarantee: comparing render(roundtrip(x)) against
    render(scene_without(x, i)) is only sound if the two strings differ by
    nothing but the removed subtree — never by serializer normalization."""
    idx = 4                                      # the GHOST Shape
    base = roundtrip(SCENE)
    removed = scene_without(SCENE, idx)
    assert base is not None and removed is not None
    # 1. serialization is stable: removing from the round-tripped string
    #    yields the very same string as removing from the original
    assert scene_without(base, idx) == removed
    # 2. exact surgery: manually deleting that one subtree from the parsed
    #    baseline reproduces scene_without()'s output byte-for-byte, so the
    #    subtree is provably the ONLY difference
    root = ET.fromstring(base)
    target = list(root.iter())[idx]
    parent = next(p for p in root.iter() if target in list(p))
    parent.remove(target)
    assert ET.tostring(root, encoding="unicode") == removed
    # 3. the subtree (node and child) is gone; every other marker survives
    assert "GHOST" not in removed and "Sphere" not in removed
    for marker in ("VIS_A", "Box", "HUMAN", "SKIN", "SUN"):
        assert marker in base and marker in removed


# --- compare() ---------------------------------------------------------------

@needs_pil
def test_compare_identical_zero_and_different_positive():
    r = _fake_renderer({"MARK": 64})
    p_with = r("MARK present")
    p_without = r("nothing here")
    assert compare(p_with, p_with) == (0, W * H, "")
    changed, total, note = compare(p_with, p_without)
    assert changed == 64 and total == W * H and note == ""


def test_compare_missing_or_undecodable_fails_safe():
    # missing input: the documented (-1, -1, note), never a crash
    r = _fake_renderer({"MARK": 64})
    p = r("MARK")
    assert compare(b"", p) == (-1, -1, "missing render")
    assert compare(p, b"") == (-1, -1, "missing render")
    # undecodable bytes: falls back to byte identity and says so
    changed, total, note = compare(b"garbage-one", b"garbage-two")
    assert (changed, total) == (-1, -1)
    assert "no decoder" in note
    # byte-identical garbage is still recognizably unchanged
    changed, _, _ = compare(b"same-garbage", b"same-garbage")
    assert changed == 0


# --- contributions(): the central behaviours ---------------------------------

def test_contributing_and_absent_nodes():
    # (a) removal changes the image -> contributed; (b) removal changes
    # nothing -> the finding, listed in .absent
    res = contributions(SCENE, _fake_renderer(FOOTPRINTS))
    assert res.ran
    assert len(res.contributions) == 5
    for ident in ("VIS_A", "HUMAN", "SKIN", "SUN"):
        assert _by_ident(res, ident).contributed
    ghost = _by_ident(res, "GHOST")
    assert not ghost.contributed
    assert [c.ident for c in res.absent] == ["GHOST"]


@needs_pil
def test_contribution_reports_exact_pixel_counts():
    res = contributions(SCENE, _fake_renderer(FOOTPRINTS))
    vis = _by_ident(res, "VIS_A")
    assert (vis.changed_pixels, vis.total_pixels) == (64, W * H)
    assert abs(vis.changed_fraction - 64 / (W * H)) < 1e-12
    ghost = _by_ident(res, "GHOST")
    assert (ghost.changed_pixels, ghost.total_pixels) == (0, W * H)


def test_variant_render_failure_credits_the_node():
    # (c) fail-safe: if the render for ONE variant blows up, that node is
    # credited (never accused) and the sweep keeps going
    inner = _fake_renderer({"VIS_A": 64})

    def renderer(scene_xml):
        if "POISON" not in scene_xml:            # only the variant WITHOUT it
            raise RuntimeError("browser crashed")
        return inner(scene_xml)

    scene = ('<X3D><Scene>'
             '<Shape DEF="VIS_A" /><Shape DEF="POISON" />'
             '</Scene></X3D>')
    res = contributions(scene, renderer)
    assert res.ran
    poison = _by_ident(res, "POISON")
    assert poison.contributed
    assert "render failed" in poison.note and "browser crashed" in poison.note
    assert all(c.ident != "POISON" for c in res.absent)   # not a finding
    assert _by_ident(res, "VIS_A").contributed            # sweep continued


def test_baseline_render_failure_is_not_an_accusation():
    # (d) no baseline, no verdicts: ran=False with a note, zero findings
    def renderer(scene_xml):
        raise RuntimeError("no browser")

    res = contributions(SCENE, renderer)
    assert not res.ran
    assert res.contributions == [] and res.absent == []
    assert "baseline render failed" in res.note and "no browser" in res.note


def test_undecidable_comparison_credits_not_accuses():
    # decodable images of DIFFERENT sizes cannot be compared pixelwise;
    # compare() reports -1 and contributions() credits the node with a note
    def renderer(scene_xml):
        full = "VIS_A" in scene_xml              # the variant renders smaller
        if _HAVE_PIL:
            im = Image.new("L", (W, H) if full else (W // 2, H // 2), BG)
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return buf.getvalue()
        return b"big" if full else b"small"      # pragma: no cover

    scene = '<X3D><Scene><Shape DEF="VIS_A" /></Scene></X3D>'
    res = contributions(scene, renderer)
    assert res.ran
    c = _by_ident(res, "VIS_A")
    assert c.contributed and c.note              # credited, and it says why
    assert res.absent == []


@needs_pil
def test_min_fraction_separates_noise_from_contribution():
    # (e) a 4-pixel change out of 4096 (~0.098%): below a high threshold it is
    # renderer noise (NOT credit), above a low one it is a real contribution
    scene = '<X3D><Scene><Shape DEF="TINY" /></Scene></X3D>'
    r = _fake_renderer({"TINY": 4})
    below = contributions(scene, r, min_fraction=0.01)
    tiny = _by_ident(below, "TINY")
    assert not tiny.contributed
    assert tiny.changed_pixels == 4              # the count is still reported
    assert [c.ident for c in below.absent] == ["TINY"]
    above = contributions(scene, r, min_fraction=1e-6)
    assert _by_ident(above, "TINY").contributed


def test_unparseable_scene_and_no_candidates_do_not_run():
    res = contributions("<X3D><broken", _fake_renderer(FOOTPRINTS))
    assert not res.ran and "not parseable" in res.note
    res = contributions('<X3D><Scene><Transform /></Scene></X3D>',
                        _fake_renderer(FOOTPRINTS))
    assert not res.ran and "no significant nodes" in res.note


def test_render_budget_is_candidates_plus_one():
    # the documented cost model: N variants + 1 baseline, bounded by max_nodes
    calls = {"n": 0}
    inner = _fake_renderer(FOOTPRINTS)

    def counting(scene_xml):
        calls["n"] += 1
        return inner(scene_xml)

    contributions(SCENE, counting)
    assert calls["n"] == len(candidates(SCENE)) + 1
    calls["n"] = 0
    contributions(SCENE, counting, max_nodes=1)
    assert calls["n"] == 2


# --- correction_for(): the error message IS the fix --------------------------

def _nc(tag, ident="X"):
    return NodeContribution(tag, ident, False)


def test_correction_imagetexture_names_the_slot_fix():
    msg = correction_for(_nc("ImageTexture", "SKIN"))
    assert "SKIN" in msg
    # the remedy: the containerField slot the material actually defines + url
    assert "containerField" in msg and "baseTexture" in msg
    assert "PhysicalMaterial" in msg and "url" in msg


def test_correction_lights_name_the_lighting_fix():
    for tag in ("EnvironmentLight", "DirectionalLight", "PointLight", "SpotLight"):
        msg = correction_for(_nc(tag, "SUN"))
        assert "SUN" in msg and tag in msg
        # the remedy: the global flag surviving serialization, and intensity/scope
        assert "global" in msg and "intensity" in msg


def test_correction_humanoid_names_the_skeleton_fix():
    msg = correction_for(_nc("HAnimHumanoid", "HUMAN"))
    assert "HUMAN" in msg
    # the remedy: skeleton routing, the documented x3d.py Bug 1
    assert "containerField='skeleton'" in msg and "HAnim" in msg


def test_correction_generic_fallback_names_the_usual_suspects():
    msg = correction_for(_nc("Shape", "S1"))
    assert "S1" in msg
    assert "on-camera" in msg and "containerField" in msg


def test_corrections_are_distinct_per_type():
    msgs = {correction_for(_nc(t))
            for t in ("ImageTexture", "PointLight", "HAnimHumanoid", "Shape")}
    assert len(msgs) == 4


# --- dataclass guards --------------------------------------------------------

def test_changed_fraction_zero_total_guard():
    assert NodeContribution("Shape", "x", True).changed_fraction == 0.0
    assert NodeContribution("Shape", "x", True, 32, 64).changed_fraction == 0.5
