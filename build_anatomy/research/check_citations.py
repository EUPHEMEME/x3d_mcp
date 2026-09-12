#!/usr/bin/env python3
# check_citations.py v1.1 2026-08-31 — verify grays1918:<anchor> citations in a research batch JSON against ref/grays1918.txt
"""Citation checker for anatomy research batches.

Usage:  python check_citations.py <batch_XXX.json> [--ref ref/grays1918.txt]

For every bone entry carrying  "source": "grays1918:<anchor-text>"  it verifies
that:
  1. the anchor text actually occurs in ref/grays1918.txt (whitespace- and
     case-insensitive, OCR-tolerant matching), and
  2. one of the bone's key anatomical terms (its display name, its Latin/TA
     name, or a listed synonym from ref/ta_terms.txt) occurs within the cited
     section's vicinity (a +/- VICINITY-char window around the anchor).

Prints a per-bone PASS/FAIL/UNCITED table and exits nonzero on any FAIL.
Entries without "source" are UNCITED — a warning, not a failure (batch_000
predates the citation rule).
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DEFAULT = os.path.join(HERE, "ref", "grays1918.txt")
TA_TERMS = os.path.join(HERE, "ref", "ta_terms.txt")
MANIFEST = os.path.join(HERE, "..", "bone_manifest.json")
VICINITY = 6000  # chars either side of the anchor counted as "the cited section"


def norm(s: str) -> str:
    """Lowercase and collapse every non-alphanumeric run to one space (OCR-tolerant)."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load_ta_terms(path: str):
    """Return list of (english, latin, [synonyms]) with {n} left as a literal marker."""
    rows = []
    if not os.path.exists(path):
        return rows
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        english, latin = parts[0], parts[1]
        syns = [s.strip() for s in parts[2].split(";")] if len(parts) > 2 else []
        rows.append((english, latin, syns))
    return rows


def base_name(display: str) -> str:
    """'L. Carpal Distal Phalanx 3' -> 'carpal distal phalanx'."""
    d = re.sub(r"^[LR]\.\s+", "", display)
    d = re.sub(r"\s+\d+$", "", d)
    return d.strip().lower()


def key_terms(bone_name: str, manifest_display: dict, ta_rows) -> list[str]:
    """Search terms for one bone: display base name + TA english/latin/synonyms."""
    display = manifest_display.get(bone_name.lower(), bone_name.replace("_", " "))
    b = base_name(display)
    terms = {b}
    for english, latin, syns in ta_rows:
        pool = [english, latin] + syns
        pool_n = [re.sub(r"\{n\}", "", p).strip().lower() for p in pool]
        if any(b == p or (len(p) >= 4 and b.startswith(p)) or (len(b) >= 4 and p.startswith(b))
               for p in pool_n):
            terms.update(p for p in pool_n if p)
    # vertebra/rib shorthand: 'c1' -> also try 'atlas' handled by ta rows via synonym C1
    for english, latin, syns in ta_rows:
        if any(norm(re.sub(r"\{n\}", "", s)) == norm(re.sub(r"(\d+)$", "", b) or b)
               for s in syns):
            terms.update(norm(x) for x in [english, latin] if x)
    return sorted(t for t in terms if len(t) >= 2)


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    batch_path = args[0]
    ref_path = REF_DEFAULT
    if "--ref" in args:
        ref_path = args[args.index("--ref") + 1]

    batch = json.load(open(batch_path, encoding="utf-8"))
    raw = open(ref_path, encoding="utf-8", errors="replace").read()
    text = norm(raw)

    manifest_display = {}
    if os.path.exists(MANIFEST):
        m = json.load(open(MANIFEST, encoding="utf-8"))
        manifest_display = {b["name"].lower(): b.get("display", b["name"])
                            for b in m.get("bones", [])}
    ta_rows = load_ta_terms(TA_TERMS)

    n_pass = n_fail = n_uncited = 0
    rows = []
    for region in batch.get("regions", []):
        for bone in region.get("bones", []):
            name = bone.get("name", "?")
            src = bone.get("source")
            if not src:
                rows.append((name, "UNCITED", "no source field (pre-rule batch)"))
                n_uncited += 1
                continue
            if not src.startswith("grays1918:"):
                rows.append((name, "FAIL", f"unknown source scheme: {src[:40]}"))
                n_fail += 1
                continue
            anchor = norm(src.split(":", 1)[1])
            if len(anchor) < 4:
                rows.append((name, "FAIL", "anchor too short to be checkable"))
                n_fail += 1
                continue
            pos = text.find(anchor)
            if pos < 0:
                rows.append((name, "FAIL", f"anchor not found in Gray's 1918: '{anchor[:50]}'"))
                n_fail += 1
                continue
            lo = max(0, pos - VICINITY)
            hi = min(len(text), pos + len(anchor) + VICINITY)
            window = text[lo:hi]
            terms = key_terms(name, manifest_display, ta_rows)
            hit = next((t for t in terms if t in window), None)
            if hit:
                rows.append((name, "PASS", f"anchor@{pos}, term '{hit}' in vicinity"))
                n_pass += 1
            else:
                rows.append((name, "FAIL",
                             f"anchor found but none of {terms[:4]}... in +/-{VICINITY} chars"))
                n_fail += 1

    w = max((len(r[0]) for r in rows), default=4)
    print(f"check_citations.py v1.1 — batch: {os.path.basename(batch_path)}  "
          f"ref: {os.path.basename(ref_path)} ({len(raw):,} chars)")
    print("-" * (w + 60))
    for name, verdict, detail in rows:
        print(f"{name:<{w}}  {verdict:<7}  {detail}")
    print("-" * (w + 60))
    print(f"TOTAL {len(rows)}: {n_pass} PASS, {n_fail} FAIL, {n_uncited} UNCITED (warning only)")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
