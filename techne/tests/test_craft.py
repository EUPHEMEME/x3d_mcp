"""Tests for the deterministic craft engine — the four documented silent-failure
modes from docs/x3dpy-bug-report.md and TECHNE_SPEC §3."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from techne import (check_container_field, check_envlight_global,        # noqa: E402
                    check_interpolator, check_use_after_def, advise_texture_url,
                    MISSING)


# --- Bug 1: containerField --------------------------------------------------

def test_container_missing_is_repaired_to_field():
    r = check_container_field("HAnimJoint", "skeleton", "HAnimHumanoid",
                              MISSING, {"node_type": "HAnimJoint"})
    assert not r.blocked
    assert r.repaired["containerField"] == "skeleton"
    assert "container_field_present" in r.applied


def test_container_wrong_is_corrected():
    r = check_container_field("ImageTexture", "baseTexture", "PhysicalMaterial",
                              "texture", {})
    assert not r.blocked
    assert r.repaired["containerField"] == "baseTexture"
    assert "container_field_correct" in r.applied


def test_container_default_field_is_left_alone():
    # HAnimSegment in 'children' (its default) is correct; no repair.
    r = check_container_field("HAnimSegment", "children", "HAnimJoint",
                              MISSING, {})
    assert not r.blocked
    assert "containerField" not in r.repaired
    assert r.applied == []


def test_container_correct_value_is_noop():
    r = check_container_field("ImageTexture", "normalTexture", "PhysicalMaterial",
                              "normalTexture", {})
    assert r.applied == []


# --- Bug 2: EnvironmentLight.global ----------------------------------------

def test_envlight_global_missing_is_written_true():
    r = check_envlight_global(MISSING, {"node_type": "EnvironmentLight"})
    assert not r.blocked
    assert r.repaired["global"] is True
    assert "envlight_global_set" in r.applied


def test_envlight_global_explicit_is_kept():
    r = check_envlight_global(False, {"global": False})
    assert r.applied == []
    assert r.repaired.get("global") is False


# --- interpolator key/keyValue parity --------------------------------------

def test_orientation_interpolator_mismatch_blocks():
    # 2 keys x 4 components = 8 expected; give 6 -> block + correct.
    r = check_interpolator("OrientationInterpolator", [0.0, 1.0],
                           [0, 0, 1, 0, 0, 1], None, {})
    assert r.blocked
    assert "interp_lengths_match" in r.applied
    assert "8" in r.corrections[0] and "6" in r.corrections[0]


def test_position_interpolator_correct_passes():
    r = check_interpolator("PositionInterpolator", [0.0, 0.5, 1.0],
                           [0, 0, 0, 1, 1, 1, 2, 2, 2], None, {})
    assert not r.blocked


def test_coordinate_interpolator_uses_num_coords():
    # 2 keys x (3 * 4 coords) = 24 expected.
    r = check_interpolator("CoordinateInterpolator", [0.0, 1.0],
                           list(range(24)), 4, {})
    assert not r.blocked
    bad = check_interpolator("CoordinateInterpolator", [0.0, 1.0],
                             list(range(20)), 4, {})
    assert bad.blocked


# --- USE-after-DEF ----------------------------------------------------------

def test_use_without_def_blocks():
    r = check_use_after_def("Hero", {"Other", "Thing"}, {})
    assert r.blocked
    assert "use_after_def" in r.applied


def test_use_with_def_passes():
    r = check_use_after_def("Hero", {"Hero", "Other"}, {})
    assert not r.blocked


# --- soft advisory ----------------------------------------------------------

def test_texture_url_non_image_warns_but_does_not_block():
    r = advise_texture_url("scene.x3d", {})
    assert not r.blocked
    assert r.notes
    ok = advise_texture_url("limestone.png", {})
    assert ok.notes == []
