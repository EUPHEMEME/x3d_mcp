#!/usr/bin/env python3
"""
PhysicallyBasedMaterialTest.py

Regression test LOCKING IN the containerField fix released in x3d.py 4.0.65.5
(SourceForge x3d ticket #117 / Python-SAI issues #2, #3).

    python3 PhysicallyBasedMaterialTest.py           # 0 = no regression
    python3 PhysicallyBasedMaterialTest.py --strict  # also fail on open items

EXIT STATUS IS DELIBERATE. On 4.0.65.5 this exits 0 even though item 4 below is
still broken, because item 4 is KNOWN-OPEN upstream rather than a regression. A
QA test that is permanently red because of an unfixed issue stops being a signal
-- the build is already broken, so a real regression changes nothing visible.
Items 1-3 are the lock: if any of them starts failing, the fix has regressed and
the exit status goes to 1.

    4.0.65.3  ->  exit 1  (items 1-3 fail: the pre-fix behaviour)
    4.0.65.5  ->  exit 0  (items 1-3 pass, item 4 reported as OPEN)

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

  3b. ComposedCubeMapTexture -- SIX children, all the same element type, all in
     different named slots, and NO default slot. The hardest instance of this
     defect in the object model: without containerField the six faces are
     indistinguishable. Case contributed by John Carlson (ballx_ite.py in
     coderextreme/X3DJSONLD).

     FIELD NAMES ARE X3D 4.0, NOT 3.x -- frontTexture, not front. Passing
     front= raises TypeError. Per John Carlson: this is deliberate, not an
     alias gap. x3d.py "started at version 4, to be compatible with X3DUOM
     version 4, X3D architecture 4.0 and SAI version 4", and is "definitely
     incompatible with X3DUOM 3.X, unless aliases have been added ... a full
     version upgrade" -- the same clean break as C++ 3.3 to 4.0. So a
     TypeError here is the library working correctly, and a test written
     against 3.x field names is testing the wrong standard.

  4. HAnimHumanoid.version -- STILL FAILING as of 4.0.65.5. Set on the object,
     absent from the XML. Kept in this file as an open item rather than split
     into its own, so one run reports the whole picture.

Alexander Hoffman, 2026-08-03. Verified against x3d.py 4.0.65.3 (fails 1-3) and
4.0.65.5 (passes 1-3, fails 4).
"""
import re
import sys

from x3d import x3d as X

VERSION = 2
FAILURES = []      # a REGRESSION -- the build should go red
OPEN = []          # a known-open defect -- reported, does not fail the run


def check(label, ok, expected, actual, open_issue=False):
    """open_issue=True marks a defect that is KNOWN-OPEN upstream.

    It is reported but does not fail the run. A QA regression test that is
    permanently red because of an unfixed issue stops being a signal -- the
    build is already broken, so a real regression changes nothing visible.
    Run with --strict to fail on open items too.
    """
    tag = 'OPEN' if (not ok and open_issue) else ('PASS' if ok else 'FAIL')
    print(f"  [{tag}] {label}")
    if not ok:
        print(f"         expected: {expected}")
        print(f"         actual  : {actual}")
        (OPEN if open_issue else FAILURES).append(label)


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

    # --- 3b. John Carlson's case: SIX non-default slots, no default at all --
    # ComposedCubeMapTexture is the hardest instance of this defect in the whole
    # object model. Every one of its six children is the SAME element type
    # (ImageTexture), each sits in a DIFFERENT named field, and there is no
    # default slot to fall back to -- so without containerField the six faces
    # are indistinguishable and the cube map cannot be reconstructed at all.
    # Construction matches ballx_ite.py in coderextreme/X3DJSONLD.
    FACES = ["backTexture", "bottomTexture", "frontTexture",
             "leftTexture", "rightTexture", "topTexture"]
    cube = X.ComposedCubeMapTexture(DEF="cube", **{
        f: X.ImageTexture(url=["%s.png" % f[0]]) for f in FACES})
    cx = cube.XML()
    print("\n  --- ComposedCubeMapTexture (6 faces) ---")
    for line in cx.splitlines():
        print("  " + line)
    got = sorted(re.findall(r"containerField='(\w+)'", cx))
    check("all six cube-map faces carry their containerField",
          got == sorted(FACES),
          "one containerField per face: " + ", ".join(sorted(FACES)),
          ("emitted " + (", ".join(got) if got else "NONE")) +
          " -- without them the six faces are indistinguishable and the cube "
          "map cannot be reconstructed")

    # --- 4. still open on 4.0.65.5 ----------------------------------------
    check("HAnimHumanoid.version='2.0' is serialized",
          "version=" in hx, "<HAnimHumanoid ... version='2.0'>",
          f"absent from XML although the object still holds "
          f"{getattr(h, 'version', None)!r}",
          open_issue=True)

    strict = "--strict" in sys.argv
    print()
    if OPEN:
        print(f"KNOWN-OPEN ({len(OPEN)}), not counted as regressions: "
              + "; ".join(OPEN))
    if FAILURES:
        print(f"REGRESSION ({len(FAILURES)}): " + "; ".join(FAILURES))
        return 1
    if OPEN and strict:
        print("--strict: failing on known-open items.")
        return 1
    print("No regressions." + (" Known-open items above." if OPEN else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
