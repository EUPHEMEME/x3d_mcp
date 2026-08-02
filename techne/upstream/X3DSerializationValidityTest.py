#!/usr/bin/env python3
"""
X3DSerializationValidityTest.py

Does x3d.py's XML output validate against the schema it cites?

    python3 X3DSerializationValidityTest.py       # exit 0 = pass, 1 = fail

Requires xmllint (libxml2) and a local copy of x3d-4.0.xsd; pass the schema path
as argv[1], or set X3D_XSD.

TWO INDEPENDENT DEFECTS, isolated from each other by construction.

A. THE XMLSchema-instance NAMESPACE IS https:// AND MUST BE http://
   x3d.py emits:

       xmlns:xsd='https://www.w3.org/2001/XMLSchema-instance'

   The canonical namespace name is 'http://www.w3.org/2001/XMLSchema-instance'.
   XML namespace names are matched by literal string comparison, not resolved as
   URLs, so the https form is simply a *different* namespace. The consequence is
   that xsd:noNamespaceSchemaLocation is not recognised as the schema-instance
   attribute, and libxml2 rejects it:

       Element 'X3D', attribute
       '{https://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation':
       The attribute ... is not allowed.

   This affects EVERY document x3d.py writes, including a document containing
   nothing but a DirectionalLight. Changing the single character makes the same
   document validate, which is the isolation test below.

B. A 4.1-ONLY NODE IS EMITTED INTO A DOCUMENT DECLARED 4.0
   EnvironmentLight is deferred to X3D 4.1 -- in x3d-4.0.xsd its element is
   inside an XML comment beginning "deferred until X3D 4.1". x3d.py will place
   one in a scene whose header declares version='4.0', whose DOCTYPE is
   "ISO//Web3D//DTD X3D 4.0//EN", and which cites x3d-4.0.xsd, with no warning.
   That document cannot validate against the schema it names.

   Note this is NOT a claim about the `global` default. x3d.py's default of TRUE
   is correct for 4.1, and an author who sets it explicitly gets no attribute
   because the serializer drops default-valued fields -- correct canonicalisation
   that happens to remove the one piece of evidence that would have surfaced the
   version mismatch. The defect is the version boundary, not the default.

Reported by Alexander Hoffman. Written 2026-08-02 at Don Brutzman's request for
X3DPSAIL python/examples. Observed on x3d.py 4.0.65.3-.4, Python 3.12.
"""
import os
import subprocess
import sys
import tempfile

from x3d import x3d as X

VERSION = 1
FAILURES = []
HTTPS_NS = "https://www.w3.org/2001/XMLSchema-instance"
HTTP_NS = "http://www.w3.org/2001/XMLSchema-instance"


def validate(xml_text, xsd):
    """Return (ok, first_error_lines) from xmllint."""
    with tempfile.NamedTemporaryFile("w", suffix=".x3d", delete=False) as f:
        f.write(xml_text)
        path = f.name
    try:
        p = subprocess.run(["xmllint", "--noout", "--schema", xsd, path],
                           capture_output=True, text=True)
        return p.returncode == 0, p.stderr.strip().splitlines()
    finally:
        os.unlink(path)


def check(label, condition, detail=""):
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
    if not condition:
        for line in (detail or "").splitlines():
            print(f"         {line}")
        FAILURES.append(label)


def main():
    xsd = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("X3D_XSD", "x3d-4.0.xsd"))
    if not os.path.exists(xsd):
        print(f"schema not found: {xsd}\n"
              f"pass the path to x3d-4.0.xsd as argv[1] or set X3D_XSD")
        return 2
    print(f"X3DSerializationValidityTest v{VERSION}   schema: {xsd}\n")

    # --- A. namespace URI, on a document with nothing exotic in it ---------
    plain = X.X3D(profile="Immersive", version="4.0", head=X.head(),
                  Scene=X.Scene(children=[X.DirectionalLight(DEF="L")])).XML()

    check("emitted xmlns:xsd is the canonical http:// namespace",
          HTTPS_NS not in plain,
          f"emits  {HTTPS_NS}\nshould  {HTTP_NS}")

    ok_plain, err_plain = validate(plain, xsd)
    check("a minimal 4.0 document validates against x3d-4.0.xsd",
          ok_plain, "\n".join(err_plain[:2]))

    # isolation: the SAME bytes with only the scheme changed
    ok_fixed, _ = validate(plain.replace(HTTPS_NS, HTTP_NS), xsd)
    print(f"\n  isolation -- same document, https:// -> http:// : "
          f"{'VALIDATES' if ok_fixed else 'still fails'}")
    if ok_fixed and not ok_plain:
        print("  => the namespace URI is the sole cause of the failure above.\n")

    # --- B. version boundary ----------------------------------------------
    doc41 = X.X3D(profile="Immersive", version="4.0", head=X.head(),
                  Scene=X.Scene(children=[X.EnvironmentLight(DEF="ibl", global_=True)])).XML()
    # neutralise defect A so this tests B alone
    ok41, err41 = validate(doc41.replace(HTTPS_NS, HTTP_NS), xsd)
    check("a document declaring 4.0 contains no 4.1-only node",
          ok41,
          "\n".join(err41[:2]) +
          "\nEnvironmentLight is commented out of x3d-4.0.xsd "
          '("deferred until X3D 4.1"); x3d.py emits it into a 4.0 header '
          "with no warning.")

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + "; ".join(FAILURES))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
