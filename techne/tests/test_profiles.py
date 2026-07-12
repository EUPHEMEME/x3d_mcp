"""Profile/component conformance — the fifth documented silent-failure mode.

The claim under test is not a schema claim, so it is not tested against a schema.
It was established by RENDERING a minimal HAnim figure under every combination of
profile and component declaration in X_ITE 11.6.6 and measuring lit pixels:

    profile      <component HAnim>   result
    -----------  ------------------  --------
    Interchange  -                   VANISHES
    Interchange  yes                 renders
    Interactive  -                   VANISHES
    Immersive    -                   VANISHES     <- the trap
    Immersive    yes                 renders
    Full         -                   renders

No profile below Full admits HAnim. Raising the profile is NOT the fix; declaring
the component is. The reproduction harness is scratchpad/isolate_hanim.py.
"""
from __future__ import annotations

import re

from techne import craft, profiles as P
from techne.rules import CATALOG, SERIALIZATION_REPAIRED, SOFT, severity


# --- the tables are transcribed from the spec, not invented -----------------

def test_hanim_is_outside_every_profile_below_full():
    for prof in ("Core", "Interchange", "Interactive", "Immersive"):
        assert "HAnimHumanoid" not in P.PROFILE_NODES[prof], prof
    assert "HAnimHumanoid" in P.PROFILE_NODES["Full"]


def test_node_component_lookup():
    assert P.NODE_COMPONENT["HAnimHumanoid"][0] == "HAnim"
    assert P.NODE_COMPONENT["TouchSensor"][0] == "PointingDeviceSensor"
    assert P.NODE_COMPONENT["PhysicalMaterial"][0] == "Shape"


def test_missing_components_names_hanim_under_immersive():
    """The trap: Immersive sounds like it covers everything. It does not."""
    need = dict(P.missing_components(["HAnimHumanoid", "HAnimJoint"], "Immersive"))
    assert "HAnim" in need


def test_full_profile_needs_nothing():
    assert P.missing_components(["HAnimHumanoid", "TouchSensor"], "Full") == []


def test_in_profile_nodes_need_nothing():
    # Box/Shape/Transform are all admitted by Interchange
    assert P.missing_components(["Box", "Shape", "Transform"], "Interchange") == []


# --- the serialization repair ----------------------------------------------

HANIM_DOC = (
    "<?xml version='1.0' encoding='UTF-8'?>\n"
    "<X3D profile='Interchange' version='4.0'>\n"
    "  <Scene>\n"
    "    <HAnimHumanoid DEF='H' name='t'>\n"
    "      <HAnimJoint containerField='skeleton' name='humanoid_root'/>\n"
    "    </HAnimHumanoid>\n"
    "  </Scene>\n"
    "</X3D>\n"
)


def test_reassert_profile_declares_the_hanim_component():
    out = craft.reassert_profile(HANIM_DOC)
    assert re.search(r"<component\s+name='HAnim'\s+level='\d+'\s*/>", out)


def test_reassert_profile_restores_the_dropped_profile():
    """create_scene(profile='Interactive') is serialized as Interchange."""
    out = craft.reassert_profile(HANIM_DOC, requested="Interactive")
    assert "profile='Interactive'" in out
    assert "profile='Interchange'" not in out


def test_reassert_profile_is_idempotent():
    once = craft.reassert_profile(HANIM_DOC, requested="Interactive")
    twice = craft.reassert_profile(once, requested="Interactive")
    assert once == twice
    assert once.count("name='HAnim'") == 1


def test_reassert_profile_never_removes_an_existing_declaration():
    doc = HANIM_DOC.replace(
        "<Scene>", "</head><Scene>").replace(
        "<X3D profile='Interchange' version='4.0'>",
        "<X3D profile='Interchange' version='4.0'>\n  <head>"
        "<component name='HAnim' level='1'/>")
    out = craft.reassert_profile(doc)
    assert out.count("name='HAnim'") == 1        # not duplicated


def test_reassert_profile_leaves_a_conformant_scene_alone():
    """No false positives: a scene that only uses Interchange nodes is untouched."""
    doc = ("<X3D profile='Interchange' version='4.0'><Scene>"
           "<Shape><Box size='1 1 1'/></Shape></Scene></X3D>")
    assert craft.reassert_profile(doc) == doc


def test_full_profile_scene_is_untouched():
    doc = HANIM_DOC.replace("Interchange", "Full")
    assert craft.reassert_profile(doc) == doc


def test_used_node_types_ignores_the_x3d_root_and_lowercase_statements():
    t = craft.used_node_types(HANIM_DOC)
    assert "HAnimHumanoid" in t and "Scene" in t
    assert "X3D" not in t


# --- the catalog contract ---------------------------------------------------

def test_rules_are_soft_because_the_model_cannot_comply():
    """create_scene takes no component list, so blocking would be a false positive.
    Both rules are advisory at the wire and repaired at serialization."""
    for rule in ("component_not_in_profile", "profile_dropped"):
        assert rule in CATALOG
        assert severity(rule) == SOFT
        assert rule in SERIALIZATION_REPAIRED


def test_correction_names_the_fix_not_just_the_fault():
    msg = CATALOG["component_not_in_profile"][1].format(
        node_type="HAnimHumanoid", component="HAnim", level=1, profile="Immersive")
    assert "<component name='HAnim' level='1'/>" in msg
    assert "Raising the profile does NOT fix this" in msg
