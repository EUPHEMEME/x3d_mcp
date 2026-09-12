#!/usr/bin/env python3
# make_broken.py v1.1 2026-08-31 — Beat A: forge the one-attribute silent failure and receipt it.
"""Beat A of the Techne live demo.

Generates two files from anatomy_explorer.x3d:

  demo/original_skeleton.x3d        — anatomy_explorer.x3d with ONE conformance
        touch-up: the <head> children reordered so <component> precedes <meta>
        (the XSD's required order; the explorer generator emitted meta first,
        which fails the schema for a reason unrelated to this demo). Scene
        content is byte-identical.
  demo/broken_skeleton_children.x3d — the SAME file with exactly one further
        change: the HAnimHumanoid skeleton root joint's containerField moved
        from 'skeleton' to 'children' (x3d.py Bug 1). The joint lands in a
        field HAnimHumanoid does not define; a conformant player silently
        drops the entire figure.

Then demonstrates the layer split:

    XSD (episteme)        : PASSES the broken file — the schema cannot see it.
    techne_gate (techne)  : FAILS it — Gate 1 names the defect and its fix;
                            Gate 2's render shows the skeleton gone.

Receipts (terminal transcripts + PNGs) land in demo/receipts/beat_a/.

Run:  cd /Users/alexander/x3d_mcp && .venv/bin/python demo/make_broken.py

Exit 0 only when every expectation held; a failed expectation is printed, never
papered over. This script asserts its own result.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

REPO = "/Users/alexander/x3d_mcp"
PY = f"{REPO}/.venv/bin/python"
SOURCE = f"{REPO}/anatomy_explorer.x3d"
ORIGINAL = f"{REPO}/demo/original_skeleton.x3d"
BROKEN = f"{REPO}/demo/broken_skeleton_children.x3d"
RECEIPTS = f"{REPO}/demo/receipts/beat_a"

sys.path.insert(0, f"{REPO}/src")
from validation.validate import validate_xml  # noqa: E402

GOOD_ATTR = 'containerField="skeleton"'
BAD_ATTR = 'containerField="children"'


def hr(title: str) -> str:
    return "=" * 66 + "\n" + title + "\n" + "=" * 66


def fix_head_order(src: str) -> str:
    """Reorder <head> children: component* before meta* (ISO 19776-1 / the XSD)."""
    head = re.search(r"<head>(.*?)</head>", src, re.S).group(1)
    comps = re.findall(r"\s*<component[^>]*/>", head)
    metas = re.findall(r"\s*<meta[^>]*/>", head)
    if not comps or not metas:
        raise SystemExit("head does not look like the explorer's (no component/meta)")
    return src.replace(head, "".join(comps) + "".join(metas) + "\n  ", 1)


def run_gate(x3d_path: str, png_out: str, transcript_out: str) -> str:
    """Run techne_gate.py as a subprocess, tee transcript to file, return stdout."""
    t0 = time.time()
    p = subprocess.run([PY, f"{REPO}/techne_gate.py", x3d_path, png_out],
                       capture_output=True, text=True, cwd=REPO, timeout=300)
    dt = time.time() - t0
    out = p.stdout + (("\n[stderr]\n" + p.stderr) if p.stderr.strip() else "")
    out += f"\n[exit code: {p.returncode}]  [wall-time: {dt:.1f}s]\n"
    with open(transcript_out, "w") as f:
        f.write(f"$ .venv/bin/python techne_gate.py {os.path.relpath(x3d_path, REPO)} "
                f"{os.path.relpath(png_out, REPO)}\n{out}")
    return out


def main() -> int:
    os.makedirs(RECEIPTS, exist_ok=True)
    failures: list[str] = []

    # ---- 1. forge the twins ---------------------------------------------------
    print(hr("STEP 1 — generate the demo original + its broken twin"))
    src = fix_head_order(open(SOURCE).read())
    open(ORIGINAL, "w").write(src)
    print(f"wrote {ORIGINAL}")
    print("  (= anatomy_explorer.x3d with <component> before <meta> in <head>,")
    print("   the order the XSD requires; scene content untouched)")
    n = src.count(GOOD_ATTR)
    if n != 1:
        print(f"ABORT: expected exactly one {GOOD_ATTR}, found {n}")
        return 2
    open(BROKEN, "w").write(src.replace(GOOD_ATTR, BAD_ATTR, 1))
    print(f"wrote {BROKEN}")
    print(f"  the ONLY further difference: {GOOD_ATTR}  ->  {BAD_ATTR}")
    print("  (the skeleton root joint now lands in HAnimHumanoid's default")
    print("   'children' slot — a field HAnimHumanoid does not define)")

    # ---- 2. XSD: the schema passes both --------------------------------------
    print("\n" + hr("STEP 2 — XSD schema validation (episteme)"))
    xsd_lines = []
    for label, path in (("original", ORIGINAL), ("broken  ", BROKEN)):
        r = validate_xml(open(path).read())
        line = (f"  {label}  ->  valid: {r['valid']}"
                + (f"   errors: {r['errors'][:2]}" if r["errors"] else ""))
        print(line)
        xsd_lines.append(line)
        if not r["valid"]:
            failures.append(f"XSD unexpectedly rejected {label.strip()}: {r['errors'][:2]}")
    if not failures:
        print("  => the XSD CANNOT tell them apart. Both are schema-valid.")
    with open(f"{RECEIPTS}/xsd_transcript.txt", "w") as f:
        f.write("XSD validation (validation.validate.validate_xml, x3d-4.1.xsd)\n"
                + "\n".join(xsd_lines)
                + "\n=> the XSD cannot tell them apart: both schema-valid.\n")

    # ---- 3. techne_gate on the ORIGINAL: must PASS ---------------------------
    print("\n" + hr("STEP 3 — techne_gate.py on the ORIGINAL (expect PASS)"))
    out = run_gate(ORIGINAL, f"{RECEIPTS}/original.png",
                   f"{RECEIPTS}/original_gate_transcript.txt")
    print(out)
    if "VERDICT: PASS" not in out:
        failures.append("techne_gate did not PASS the original")

    # ---- 4. techne_gate on the BROKEN file: must FAIL ------------------------
    print(hr("STEP 4 — techne_gate.py on the BROKEN file (expect FAIL)"))
    out = run_gate(BROKEN, f"{RECEIPTS}/broken.png",
                   f"{RECEIPTS}/broken_gate_transcript.txt")
    print(out)
    if "VERDICT: FAIL" not in out:
        failures.append("techne_gate did not FAIL the broken file")
    if "containerfield" not in out.lower():
        failures.append("Gate 1 did not name the containerField defect")

    # ---- verdict -------------------------------------------------------------
    print(hr("BEAT A SELF-ASSERTION"))
    if failures:
        for f_ in failures:
            print("  FAIL:", f_)
        print("  receipts (including the disagreeing ones) are in", RECEIPTS)
        return 1
    print("  XSD passes both; techne_gate PASSES the original and FAILS the broken")
    print("  twin, naming the exact fix. One attribute, invisible to the schema,")
    print("  kills the whole figure. receipts ->", RECEIPTS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
