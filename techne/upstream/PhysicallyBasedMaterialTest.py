#!/usr/bin/env python3
"""
PhysicallyBasedMaterialTest.py

Regression test LOCKING IN the containerField fix released in x3d.py 4.0.65.5
(SourceForge x3d ticket #117 / Python-SAI issues #2, #3).

    python3 PhysicallyBasedMaterialTest.py      # exit 0 = pass, 1 = regression

STATUS: all containerField checks below PASS on 4.0.65.5 and FAIL on 4.0.65.3.
This test exists to keep it that way, which is what Don Brutzman asked for --
a program that can live in X3DPSAIL python/examples as long-term QA.

WHAT IT COVERS

  1. PhysicalMaterial + baseTexture -- the case from the June 23 comment. An
     ImageTexture in the `baseTexture` slot must serialize with
     containerField='baseTexture'. Without it the texture reparses into the
     default `texture` slot, which PhysicalMaterial does not define, and the
     surface renders untextured with no error anywhere.

  2. The default slot must NOT carry containerField. Emitting it there would be
     redundant, and canonical X3D omits an attribute equal to its default. This
     is the control: it proves the fix is slot-aware rather than blanket.

  3. HAnimHumanoid skeleton/segments -- containerField on non-default node
     fields, and DEF ordered before USE.

  4. HAnimHumanoid.version -- STILL FAILING as of 4.0.65.5. Set on the object,
     absent from the XML. Kept in this file as an open item rather than split
     into its own, so one run reports the whole picture.

Alexander Hoffman, 2026-08-03. Verified against x3d.py 4.0.65.3 (fails 1-3) and
4.0.65.5 (passes 1-3, fails 4).
"""
import sys

from x3d import x3d as X

VERSION = 1
FAILURES = []


def check(label, ok, expected, actual):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"         expected: {expected}")
        print(f"         actual  : {actual}")
        FAILURES.append(label)


def main():
    print(f"PhysicallyBasedMaterialTest v{VERSION} -- x3d.py "
          f"{getattr(X, '__version__', '(version attribute absent)')}\n")

    # --- 1. non-default slot: baseTexture ---------------------------------
    app = X.Appearance(material=X.PhysicalMaterial(
        DEF="brick", baseTexture=X.ImageTexture(DEF="btex", url=["brick.png"])))
    xml = app.XML()
    print("  --- PhysicalMaterial with baseTexture ---")
    for line in xml.splitlines():
        print("  " + line)
    check("ImageTexture in `baseTexture` carries containerField='baseTexture'",
          "containerField='baseTexture'" in xml,
          "<ImageTexture ... containerField='baseTexture'/>",
          "no containerField -- reparses into `texture`, which "
          "PhysicalMaterial does not define; the surface renders untextured")

    # --- 2. control: the DEFAULT slot must stay bare -----------------------
    bare = X.Appearance(texture=X.ImageTexture(DEF="t2", url=["b.png"])).XML()
    check("control: default `texture` slot emits NO containerField",
          "containerField" not in bare,
          "<ImageTexture DEF='t2' url='\"b.png\"'/>", bare.strip())

    # --- 3. HAnim non-default node fields ---------------------------------
    h = X.HAnimHumanoid(
        DEF="hanim_Test", name="Test", version="2.0",
        skeleton=[X.HAnimJoint(DEF="hanim_humanoid_root", name="humanoid_root",
                               children=[X.HAnimSegment(DEF="hanim_sacrum",
                                                        name="sacrum")])],
        segments=[X.HAnimSegment(USE="hanim_sacrum")])
    hx = h.XML()
    print("\n  --- HAnimHumanoid ---")
    for line in hx.splitlines():
        print("  " + line)
    check("HAnimJoint in `skeleton` carries containerField='skeleton'",
          "containerField='skeleton'" in hx, "containerField='skeleton'",
          "absent -- the joint reparses into `children` and the skeleton "
          "stops being a skeleton")
    check("HAnimSegment in `segments` carries containerField='segments'",
          "containerField='segments'" in hx, "containerField='segments'", "absent")

    i_def, i_use = hx.find("DEF='hanim_sacrum'"), hx.find("USE='hanim_sacrum'")
    check("DEF precedes USE in document order",
          -1 < i_def < i_use, "the DEF node serializes first",
          f"DEF at {i_def}, USE at {i_use} -- USE is a forward reference")

    # --- 4. still open on 4.0.65.5 ----------------------------------------
    check("HAnimHumanoid.version='2.0' is serialized",
          "version=" in hx, "<HAnimHumanoid ... version='2.0'>",
          f"absent from XML although the object still holds "
          f"{getattr(h, 'version', None)!r}  [OPEN as of 4.0.65.5]")

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + "; ".join(FAILURES))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
