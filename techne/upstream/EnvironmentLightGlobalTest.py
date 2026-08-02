#!/usr/bin/env python3
"""
EnvironmentLightGlobalTest.py

Regression test for Python-SAI issue #3 -- EnvironmentLight.global is dropped
from XML serialization, and the omission is keyed to the X3D 4.1 default while
the emitted file declares X3D 4.0.

    python3 EnvironmentLightGlobalTest.py        # exit 0 = pass, 1 = fail

WHY THIS IS NOT MERELY COSMETIC
    The two schema versions disagree on the default, which is the erratum noted
    for Web3D Mantis 1539:

        x3d-4.0.xsd   EnvironmentLight  global default = "false"
        x3d-4.1.xsd   EnvironmentLight  global default = "true"
        (PointLight is "true" and DirectionalLight is "false" in BOTH, so
         EnvironmentLight is the only node whose default moved.)

    x3d.py omits an attribute whose value equals the default it believes in. It
    believes "true" -- the 4.1 value -- so an author who sets global=True gets a
    file with no global attribute at all, while the same file's header declares
    version='4.0' and points at x3d-4.0.xsd.

    A conforming 4.0 reader then applies false and scopes the light to its
    parent. Image-based lighting disappears. Nothing errors: the document is
    schema-valid either way, because the attribute is simply absent.

    Round-tripping through x3d.py hides it, because x3d.py reads back with the
    same assumed default it wrote with. The failure only appears in a different
    conforming reader -- which is why it needs a regression test rather than a
    round-trip check.

Reported by Alexander Hoffman, 2026-06-18. Test written 2026-08-02 at
Don Brutzman's request for X3DPSAIL python/examples.
"""
import re
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


def main():
    print(f"EnvironmentLightGlobalTest v{VERSION} -- Python-SAI issue #3\n")

    # --- 1. what default does x3d.py hold? --------------------------------
    default = X.EnvironmentLight().global_
    print(f"  x3d.py in-memory default for EnvironmentLight.global : {default!r}")
    print(f"  x3d-4.0.xsd says                                     : False")
    print(f"  x3d-4.1.xsd says                                     : True\n")

    # --- 2. an explicitly authored global=True must survive ---------------
    # This is the actual defect. The author said True; the file must say True,
    # or must not claim to be 4.0.
    lit = X.EnvironmentLight(DEF="ibl", global_=True)
    xml = lit.XML()
    check("global=True is serialized (not silently dropped)",
          "global=" in xml,
          "<EnvironmentLight DEF='ibl' global='true'/>",
          xml.strip())

    # --- 3. global=False still serializes (control) -----------------------
    # If this ever fails too, the bug is broader than the default mismatch.
    lit_false = X.EnvironmentLight(DEF="ibl", global_=False)
    check("control: global=False is serialized",
          "global=" in lit_false.XML(),
          "global='false' present",
          lit_false.XML().strip())

    # --- 4. the version the document actually declares --------------------
    doc = X.X3D(profile="Immersive", version="4.0", head=X.head(),
                Scene=X.Scene(children=[X.EnvironmentLight(DEF="ibl", global_=True)]))
    out = doc.XML()
    declared = re.search(r"<X3D[^>]*version='([^']+)'", out)
    declared = declared.group(1) if declared else "(none)"
    print(f"\n  document declares X3D version : {declared}")
    print(f"  global attribute present      : {'global=' in out}")

    check("a document declaring 4.0 does not rely on the 4.1 default",
          not (declared.startswith("4.0") and "global=" not in out),
          "either global='true' is written, or the document declares 4.1",
          f"declares {declared} with global absent -- a 4.0 reader applies "
          f"false and the light becomes local")

    print("\n  --- emitted document ---")
    for line in out.splitlines():
        print("  " + line)

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + "; ".join(FAILURES))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
