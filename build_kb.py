#!/usr/bin/env python3
"""Assemble build_anatomy/anatomy_kb.json — the explorer's teaching layer.

Inputs:
  * the researched + fact-checked region data (from the anatomy-knowledge-base
    workflow), read out of its task output file
  * bone_manifest.json, for the model's own measured composition

The reconciliation ("why 257 parts, not 206 bones?") is NOT taken from the
research. It is COMPUTED here, group by group, from the model against the
canonical adult counts -- because it is the one claim in the whole demo that a
student is most likely to check, and the one an LLM is most likely to get
plausibly wrong.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.abspath(__file__))
BUILD = f"{REPO}/build_anatomy"

# Canonical adult human skeleton = 206 bones. Standard textbook breakdown.
CANON = {
    "Cranium": 8, "Facial skeleton": 14, "Auditory ossicles": 6, "Hyoid": 1,
    "Cervical vertebrae": 7, "Thoracic vertebrae": 12, "Lumbar vertebrae": 5,
    "Sacrum & coccyx": 2, "Ribs": 24, "Sternum": 1,
    "Shoulder girdle": 4, "Arm": 6, "Carpals": 16, "Metacarpals": 10,
    "Hand phalanges": 28, "Pelvic girdle": 2, "Leg": 8, "Tarsals": 14,
    "Metatarsals": 10, "Foot phalanges": 28,
}
CANON_TOTAL = sum(CANON.values())        # 206


def load_research(path: str) -> dict:
    """The workflow's result is a JSON object embedded in the task output."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    i = raw.find('{"regions"')
    if i < 0:
        i = raw.find('"regions"')
        i = raw.rfind("{", 0, i)
    dec = json.JSONDecoder()
    obj, _ = dec.raw_decode(raw[i:])
    return obj


def reconcile(bones: list[dict]) -> dict:
    """Compute the 206-vs-model difference from the model itself."""
    have = Counter(b["groupFallback"] for b in bones if b["kind"] == "bone")
    rows, deltas = [], []
    for g, c in CANON.items():
        h = have.get(g, 0)
        rows.append({"group": g, "model": h, "canonical": c, "delta": h - c})
        if h != c:
            deltas.append((g, h - c))
    return {
        "model_bones": sum(have.values()),
        "canonical_bones": CANON_TOTAL,
        "rows": rows,
        "deltas": deltas,
    }


def main() -> None:
    out_file = sys.argv[1] if len(sys.argv) > 1 else (
        "/private/tmp/claude-501/-Users-alexander/"
        "0f276d3e-096d-4fcb-b61e-7acdcdee2394/tasks/wff8gq4f1.output")

    research = load_research(out_file)
    manifest = json.load(open(f"{BUILD}/bone_manifest.json"))
    bones = manifest["bones"]
    known = {b["name"] for b in bones}

    # ---- per-bone enrichment, keyed to the model's identifiers --------------
    kb_bones: dict[str, dict] = {}
    groups: list[dict] = []
    dropped = []
    for region in research.get("regions", []):
        if not region:
            continue
        groups.append({
            "title": region.get("group_title", ""),
            "teaching": region.get("group_teaching", ""),
            "key_counts": region.get("key_counts", []),
        })
        for b in region.get("bones", []):
            n = b.get("name")
            if n not in known:          # researcher invented / mis-keyed a name
                dropped.append(n)
                continue
            kb_bones[n] = {k: v for k, v in b.items()
                           if k in ("group", "function", "articulates_with", "note") and v}

    teaching = research.get("teaching") or {}

    # ---- tours: drop any step bone the model does not actually have ---------
    tours = []
    tour_dropped = []
    for t in teaching.get("tours", []):
        steps = []
        for s in t.get("steps", []):
            keep = [b for b in s.get("bones", []) if b in known]
            tour_dropped += [b for b in s.get("bones", []) if b not in known]
            steps.append({**s, "bones": keep})
        tours.append({**t, "steps": steps})

    # ---- quiz: an unanswerable question is worse than no question -----------
    quiz, quiz_dropped = [], []
    for q in teaching.get("quiz", []):
        if q.get("answer") in known:
            q["accept"] = [a for a in q.get("accept", []) if a in known]
            quiz.append(q)
        else:
            quiz_dropped.append(q.get("answer"))

    rec = reconcile(bones)
    kinds = manifest["kinds"]

    kb = {
        "bones": kb_bones,
        "groups": groups,
        "tours": tours,
        "quiz": quiz,
        "reconciliation": {
            "headline": f"{manifest['counts']['total']} clickable parts, "
                        f"{rec['model_bones']} of them bones",
            "kinds": kinds,
            "canonical_bones": rec["canonical_bones"],
            "model_bones": rec["model_bones"],
            "rows": rec["rows"],
        },
    }
    json.dump(kb, open(f"{BUILD}/anatomy_kb.json", "w"), indent=1)

    print(f"anatomy_kb.json")
    print(f"  bones enriched : {len(kb_bones)} / {len(bones)}")
    print(f"  region essays  : {len(groups)}")
    print(f"  guided tours   : {len(tours)}  ({sum(len(t['steps']) for t in tours)} steps)")
    print(f"  quiz questions : {len(quiz)}")
    if dropped:      print(f"  dropped bones (not in model) : {sorted(set(dropped))[:6]}")
    if tour_dropped: print(f"  dropped tour refs            : {sorted(set(tour_dropped))}")
    if quiz_dropped: print(f"  dropped quiz answers         : {sorted(set(quiz_dropped))}")

    print(f"\n  RECONCILIATION (computed, not asserted)")
    print(f"    model: {rec['model_bones']} bones + "
          f"{kinds.get('tooth',0)} teeth + {kinds.get('disc',0)} discs + "
          f"{kinds.get('cartilage',0)} cartilage = {manifest['counts']['total']}")
    print(f"    canonical adult skeleton: {rec['canonical_bones']} bones")
    for g, d in rec["deltas"]:
        print(f"      {d:+d}  {g}")


if __name__ == "__main__":
    main()
