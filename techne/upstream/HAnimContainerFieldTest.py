#!/usr/bin/env python3
"""
HAnimContainerFieldTest.py

Regression test for Python-SAI issue #2 / SourceForge x3d ticket #117 --
x3d.py XML output for HAnim omits containerField, emits USE before its DEF, and
drops HAnimHumanoid.version.

    python3 HAnimContainerFieldTest.py           # exit 0 = pass, 1 = fail

This is a 6-node reduction of the JinLOA1.py failure attached to ticket #117.
It reproduces all three problems noted there without needing the full model, so
it is cheap to run in CI.

THE THREE DEFECTS, and why each is silent

  1. containerField omitted for a node in a NON-DEFAULT slot.
     An HAnimJoint placed in HAnimHumanoid's `skeleton` field serializes with no
     containerField, so on reparse it lands in `children` -- the default slot.
     The joint is still present and the document is still schema-valid, so no
     error is raised. The skeleton simply is not a skeleton any more: nothing
     drives the joint hierarchy, and the figure renders unposed or invisible.
     This is the single most damaging case because HAnimHumanoid has SIX node
     fields (skeleton, joints, segments, sites, skin, skinCoord) and only one
     of them is the default.

  2. USE emitted BEFORE its DEF.
     XML is read in document order, so a USE that precedes its DEF is a forward
     reference to a name that does not exist yet. Readers differ: some resolve
     it late, some drop the node.

  3. HAnimHumanoid.version dropped.
     Set on the object, absent from the XML. The value is required to tell an
     HAnim 1.0 figure from a 2.0 one.

Reported by Alexander Hoffman, 2026-06-18. Test written 2026-08-02 at
Don Brutzman's request for X3DPSAIL python/examples.
"""
import sys

from x3d import x3d as X

VERSION = 1
FAILURES = []


def check(label, condition, expected, actual):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        print(f"         expected: {expected}")
        print(f"         actual  : {actual}")
        FAILURES.append(label)


def build():
    """Minimal humanoid: one joint in `skeleton`, one segment USEd in `segments`."""
    return X.HAnimHumanoid(
        DEF="hanim_Test", name="Test", version="2.0",
        skeleton=[
            X.HAnimJoint(DEF="hanim_humanoid_root", name="humanoid_root",
                         children=[X.HAnimSegment(DEF="hanim_sacrum", name="sacrum")])
        ],
        segments=[X.HAnimSegment(USE="hanim_sacrum")],
    )


def main():
    print(f"HAnimContainerFieldTest v{VERSION} -- Python-SAI #2 / SF ticket #117\n")
    xml = build().XML()

    print("  --- emitted XML ---")
    for line in xml.splitlines():
        print("  " + line)
    print()

    # --- 1. containerField on non-default slots ---------------------------
    check("HAnimJoint in `skeleton` carries containerField='skeleton'",
          "containerField='skeleton'" in xml,
          "<HAnimJoint DEF='hanim_humanoid_root' containerField='skeleton' ...>",
          "no containerField -- on reparse the joint lands in `children`")

    check("HAnimSegment in `segments` carries containerField='segments'",
          "containerField='segments'" in xml,
          "<HAnimSegment USE='hanim_sacrum' containerField='segments'/>",
          "no containerField -- on reparse the segment lands in `children`")

    # --- 2. document order: DEF must precede USE --------------------------
    i_def = xml.find("DEF='hanim_sacrum'")
    i_use = xml.find("USE='hanim_sacrum'")
    check("DEF='hanim_sacrum' appears before USE='hanim_sacrum'",
          i_def != -1 and i_use != -1 and i_def < i_use,
          "the DEF node is serialized first, then the USE reference",
          f"DEF at offset {i_def}, USE at offset {i_use} -- USE is a forward "
          f"reference to a name not yet defined")

    # --- 3. version retained ----------------------------------------------
    obj = build()
    check("HAnimHumanoid.version='2.0' is serialized",
          "version=" in xml,
          "<HAnimHumanoid ... version='2.0'>",
          f"absent from XML although the object still holds "
          f"{getattr(obj, 'version', None)!r}")

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + "; ".join(FAILURES))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
