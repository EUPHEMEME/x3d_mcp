#!/usr/bin/env python3
# beat_c_probe.py v1.0 2026-08-31 — Beat C: differential probe finds the bone that isn't there.
"""Beat C of the Techne live demo — per-node pixel contribution on a real asset
defect (docs/loa5-asset-findings.md finding #2):

    l_tarsal_distal_phalanx_5  (left little-toe tip)  is a ZERO-GEOMETRY asset —
    its HAnimSegment exists in the skeleton but wraps nothing.
    r_tarsal_distal_phalanx_5, its right twin, is a complete mesh.

The blank-frame gate can never see this: the frame stays populated. The
differential probe (techne/techne/differential.py) can — render the scene, then
render it again with one node removed; identical pixels means the node was
never on screen.

This script extracts BOTH little-toe joint subtrees from the flattened LOA5
skeleton (build_anatomy/skeleton.x3dfrag), cans them into a small foot
sub-scene, and runs differential.contributions() over the two HAnimSegments
with the same X_ITE renderer the server uses.

Expected: the left segment contributes 0 px in a NON-blank frame; the right
contributes well above threshold. Wall-time is measured and written into the
receipt. Receipts land in demo/receipts/beat_c/.

Run:  cd /Users/alexander/x3d_mcp && .venv/bin/python demo/beat_c_probe.py

Honesty rules (same as techne/eval/differential_probe.py): if the renderer does
not draw (blank baseline) the probe exits 2 — "could not run", never a finding.
This script asserts its own result.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import xml.etree.ElementTree as ET

REPO = "/Users/alexander/x3d_mcp"
for p in (f"{REPO}/src", f"{REPO}/techne"):
    if p not in sys.path:
        sys.path.insert(0, p)

from techne import differential                     # noqa: E402
from techne.gate import inspect_render              # noqa: E402

FRAG = f"{REPO}/build_anatomy/skeleton.x3dfrag"
RECEIPTS = f"{REPO}/demo/receipts/beat_c"
SCENE_OUT = f"{REPO}/demo/foot_probe.x3d"

W, H, WAIT_MS = 512, 384, 6000

L_JOINT = "hanim_l_tarsal_distal_interphalangeal_5"
R_JOINT = "hanim_r_tarsal_distal_interphalangeal_5"
L_SEG = "hanim_l_tarsal_distal_phalanx_5"
R_SEG = "hanim_r_tarsal_distal_phalanx_5"

# Camera on the RIGHT little toe (its mesh Transform sits at -0.1319 0.0087
# 0.0543 and spans ~±4 mm). The left twin's segment is empty, so it draws
# nothing from ANY camera — the receipt states that explicitly.
SCENE_TEMPLATE = """<X3D profile='Immersive' version='4.0'>
  <head>
    <component name='HAnim' level='1'/>
    <meta content='Techne demo beat C — little-toe differential probe' name='title'/>
  </head>
  <Scene>
    <Viewpoint DEF='VP_Toe' position='-0.1319 0.0087 0.082'
               centerOfRotation='-0.1319 0.0087 0.0543'
               nearDistance='0.002' farDistance='5'
               description='right little-toe tip, close-up'/>
    <HAnimHumanoid DEF='LittleToes' name='little_toes' version='2.0'>
      <HAnimJoint name='humanoid_root' containerField='skeleton'>
{subtrees}
      </HAnimJoint>
    </HAnimHumanoid>
  </Scene>
</X3D>"""

LOG: list[str] = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    LOG.append(line)


def hr(title: str):
    say("=" * 66)
    say(title)
    say("=" * 66)


def extract_subtrees() -> str:
    """Pull both little-toe HAnimJoint subtrees out of the flattened skeleton."""
    root = ET.parse(FRAG).getroot()
    found = {}
    for el in root.iter("HAnimJoint"):
        if el.get("DEF") in (L_JOINT, R_JOINT):
            found[el.get("DEF")] = el
    missing = [d for d in (L_JOINT, R_JOINT) if d not in found]
    if missing:
        raise SystemExit(f"could not find {missing} in {FRAG}")
    return "\n".join(
        ET.tostring(found[d], encoding="unicode") for d in (L_JOINT, R_JOINT))


class Renderer:
    """Sync facade over the server's async X_ITE renderer, with a PNG trail."""

    def __init__(self, out: str):
        self.out = out
        self.renders = 0
        self.label = "frame"

    def __call__(self, xml: str) -> bytes:
        from tools.render import _render_xite_async
        png = asyncio.run(_render_xite_async(xml, W, H, WAIT_MS))
        self.renders += 1
        with open(os.path.join(self.out, f"{self.renders:02d}_{self.label}.png"), "wb") as f:
            f.write(png)
        return png


def main() -> int:
    os.makedirs(RECEIPTS, exist_ok=True)
    t0 = time.time()
    failures: list[str] = []

    hr("BEAT C — the bone that isn't there (differential probe)")
    say(f"defect under test: {L_SEG} (zero-geometry asset, loa5-asset-findings #2)")
    say(f"healthy twin     : {R_SEG} (complete mesh)")
    say(f"renderer         : src/tools/render.py::_render_xite_async "
        f"(X_ITE + headless Chromium), {W}x{H}, wait {WAIT_MS} ms")

    subtrees = extract_subtrees()
    scene = SCENE_TEMPLATE.format(subtrees=subtrees)
    open(SCENE_OUT, "w").write(scene)
    say(f"canned sub-scene : {SCENE_OUT}  ({len(scene)} bytes — both little-toe "
        "joint subtrees, verbatim from build_anatomy/skeleton.x3dfrag)")

    render = Renderer(RECEIPTS)

    # ---- sanity: does the frame draw at all? (honesty gate) -------------------
    say("")
    render.label = "baseline"
    base_scene = differential.roundtrip(scene)
    try:
        base_png = render(base_scene)
    except Exception as e:                                       # noqa: BLE001
        say(f"COULD NOT RUN: baseline render failed: {e}")
        say("likely missing: Playwright Chromium, or network for the X_ITE CDN")
        return 2
    receipt = inspect_render(base_png)
    say(f"baseline frame   : non_blank={receipt.non_blank}  stddev={receipt.stddev:.2f}"
        f"  ({receipt.width}x{receipt.height})")
    if not receipt.non_blank:
        say("COULD NOT RUN: the baseline frame is BLANK — no verdict can be drawn "
            "about per-node contributions. Recorded as such; nothing was faked.")
        return 2

    # ---- the differential: one render per segment, vs the baseline ------------
    say("")
    say("removing each HAnimSegment in turn and re-rendering...")
    render.label = "variant"
    res = differential.contributions(
        scene, render, tags=("HAnimSegment",), base_png=base_png)
    if not res.ran:
        say(f"COULD NOT RUN: differential did not run: {res.note}")
        return 2

    thresh = int(differential.MIN_CHANGED_FRACTION * W * H)
    say("")
    say(f"  {'segment':38s} {'changed px':>10s} {'of':>8s}   verdict")
    by_ident = {}
    for c in res.contributions:
        verdict = "CONTRIBUTES" if c.contributed else "ABSENT"
        say(f"  {c.ident:38s} {c.changed_pixels:>10d} {c.total_pixels:>8d}   {verdict}"
            + (f"  [{c.note}]" if c.note else ""))
        by_ident[c.ident] = c
    say(f"  (threshold: >= {thresh} changed px of {W*H} to count as contributing)")

    l, r = by_ident.get(L_SEG), by_ident.get(R_SEG)
    if l is None or r is None:
        failures.append("probe did not test both segments")
    else:
        if l.changed_pixels != 0 or l.contributed:
            failures.append(f"left segment reported {l.changed_pixels} px "
                            "(expected exactly 0 — it wraps no geometry)")
        if not r.contributed:
            failures.append(f"right segment reported only {r.changed_pixels} px "
                            "(expected well above threshold)")

    dt = time.time() - t0
    say("")
    hr("BEAT C SELF-ASSERTION")
    if failures:
        for f_ in failures:
            say("  FAIL: " + f_)
    else:
        say(f"  {L_SEG}: 0 px in a NON-blank frame — in the document,")
        say(f"  never on screen. {R_SEG}: {r.changed_pixels} px.")
        say("  The blank gate passes this frame; only the differential sees the")
        say("  missing bone. (The left segment is empty in the ASSET, so it draws")
        say("  nothing from any camera — camera choice cannot fake this result.)")
    say(f"  wall-time: {dt:.1f}s for {render.renders} renders "
        f"({dt/max(render.renders,1):.1f}s per render)")
    say(f"  receipts -> {RECEIPTS}")

    with open(f"{RECEIPTS}/beat_c_transcript.txt", "w") as f:
        f.write("$ .venv/bin/python demo/beat_c_probe.py\n" + "\n".join(LOG) + "\n")
    with open(f"{RECEIPTS}/timing.json", "w") as f:
        json.dump({"wall_time_s": round(dt, 1), "renders": render.renders,
                   "width": W, "height": H, "wait_ms": WAIT_MS}, f, indent=1)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
