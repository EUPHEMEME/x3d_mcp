#!/usr/bin/env python3
# beat_e.py v1.0 2026-08-31 — Beat E: the provenance strict gate — one BLOCK, one properly-attributed PASS.
"""Beat E of the Techne live demo — provenance as an opt-in POLICY, strict.

Profile under test:  TECHNE_PROFILE=core,coherence,provenance
                     TECHNE_PROVENANCE_LEVEL=2   (sourcing: claims must resolve
                                                  in an asset ledger)
                     TECHNE_STRICT=1             (policy violations are hard stops)
                     TECHNE_ASSET_LEDGER=demo/beat_e_ledger.json

  CASE A — BLOCK.  render_image(content=...) where a Transform is tagged
      provenance='documented' with catalogId='SLOP-1' — an id that resolves to
      nothing in the ledger. Under STRICT the render is refused BEFORE it ever
      reaches Chromium: "you cannot label a feature documented until you have
      the source that documents it." The correction lists the ids the ledger
      actually holds.

  CASE A' — CONTROL (opt-in proof).  The SAME scene through a default-profile
      Technē (core,coherence — no provenance group): renders without complaint.
      Provenance is policy, not core correctness; nobody who didn't opt in
      ever sees it.

  CASE B — PASS.  The real bone mesh — assets/loa5/meshes/
      r_tarsal_distal_phalanx_5.x3d (Brutzman, Williams, Carlson & Hernandez,
      Web3D Consortium AllBonesLOA5Skeletons) — wrapped in a provenance
      MetadataSet whose catalogId='BONE-R5' resolves in the ledger to that
      citation with public_domain=true. Same strict gate: the render goes
      through, the bone draws (non-blank), no provenance note rides back.

Receipts land in demo/receipts/beat_e/.

Run:  cd /Users/alexander/x3d_mcp && .venv/bin/python demo/beat_e.py

Self-asserting: exit 0 only if A blocked-with-named-ledger-ids, A' rendered
silently, and B rendered non-blank with zero provenance text.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
import xml.etree.ElementTree as ET

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = "/Users/alexander/x3d_mcp"
PY = f"{REPO}/.venv/bin/python"
RECEIPTS = f"{REPO}/demo/receipts/beat_e"
LEDGER = f"{REPO}/demo/beat_e_ledger.json"
BONE_MESH = f"{REPO}/assets/loa5/meshes/r_tarsal_distal_phalanx_5.x3d"

LOG: list[str] = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    LOG.append(line)


def hr(title: str):
    say("=" * 66)
    say(title)
    say("=" * 66)


def texts_of(res) -> list[str]:
    return [c.text for c in res.content if getattr(c, "type", "") == "text"]


def image_of(res) -> bytes | None:
    for c in res.content:
        if getattr(c, "type", "") == "image" and getattr(c, "data", None):
            return base64.b64decode(c.data)
    return None


def bone_shape_xml() -> str:
    """Extract the real bone's <Shape> (PhysicalMaterial + IndexedFaceSet +
    Coordinate) from the shipped LOA5 asset — the demo renders the actual mesh,
    not a stand-in."""
    root = ET.parse(BONE_MESH).getroot()
    shape = root.find(".//Shape")
    assert shape is not None, "no Shape in the bone asset"
    return ET.tostring(shape, encoding="unicode")


def scene(prov_block: str, body: str) -> str:
    return f"""<X3D profile='Immersive' version='4.0'>
  <Scene>
    <Viewpoint position='0 0 0.018' nearDistance='0.001'
               description='bone close-up (mesh is ~8 mm long)'/>
    <Background skyColor='0.12 0.12 0.14'/>
    <Transform DEF='SubjectAsset'>
      <MetadataSet containerField='metadata' name='provenance'
                   reference='https://www.web3d.org/specifications/provenance/1.0'>
{prov_block}
      </MetadataSet>
{body}
    </Transform>
  </Scene>
</X3D>"""


PROV_BAD = """        <MetadataString name='provenance' value='"documented"'/>
        <MetadataString name='catalogId'  value='"SLOP-1"'/>"""

PROV_GOOD = """        <MetadataString  name='provenance'     value='"documented"'/>
        <MetadataString  name='catalogId'      value='"BONE-R5"'/>
        <MetadataString  name='sourceCitation' value='"Brutzman, Williams, Carlson &amp; Hernandez — r_tarsal_distal_phalanx_5.x3d, HAnim AllBonesLOA5Skeletons, Web3D Consortium"'/>
        <MetadataBoolean name='publicDomain'   value='true'/>"""

BOX_BODY = "      <Shape><Appearance><Material diffuseColor='0.8 0.7 0.5'/></Appearance><Box size='0.006 0.006 0.006'/></Shape>"


def params(profile_env: dict) -> StdioServerParameters:
    return StdioServerParameters(
        command=PY,
        args=["-m", "techne.server", "--", PY, "-m", "src.server", "--cwd", REPO],
        env={**os.environ, "PYTHONPATH": f"{REPO}/techne", **profile_env},
        cwd=REPO)


STRICT_ENV = {"TECHNE_PROFILE": "core,coherence,provenance",
              "TECHNE_PROVENANCE_LEVEL": "2",
              "TECHNE_STRICT": "1",
              "TECHNE_ASSET_LEDGER": LEDGER}
DEFAULT_ENV = {"TECHNE_PROFILE": "core,coherence"}


async def call_render(env: dict, content: str):
    t0 = time.time()
    async with stdio_client(params(env)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("render_image",
                                    {"content": content, "wait_ms": 8000})
    return res, time.time() - t0


async def main() -> int:
    os.makedirs(RECEIPTS, exist_ok=True)
    failures: list[str] = []
    timing: dict[str, float] = {}

    scene_bad = scene(PROV_BAD, BOX_BODY)
    scene_good = scene(PROV_GOOD, "      " + bone_shape_xml())
    open(f"{RECEIPTS}/case_a_scene.x3d", "w").write(scene_bad)
    open(f"{RECEIPTS}/case_b_scene.x3d", "w").write(scene_good)

    # ---- CASE A — strict gate, unresolvable 'documented' claim -> BLOCK ------
    hr("CASE A — provenance='documented' catalogId='SLOP-1' (not in ledger), "
       "STRICT profile  ->  expect BLOCK before any render")
    res, dt = await call_render(STRICT_ENV, scene_bad)
    timing["case_a_block_s"] = round(dt, 1)
    body = "\n".join(texts_of(res))
    say(f"isError={bool(res.isError)}   wall={dt:.1f}s")
    say(body.strip() or "(empty)")
    blocked = bool(res.isError) and "blocked" in body.lower()
    named_id = "SLOP-1" in body
    named_ledger = "BONE-R5" in body
    say(f"\n  verdict: {'BLOCKED' if blocked else 'NOT BLOCKED'}; names the bogus id: "
        f"{named_id}; lists what the ledger DOES hold: {named_ledger}")
    if not blocked:
        failures.append("CASE A was not blocked under STRICT")
    if not (named_id and named_ledger):
        failures.append("CASE A correction did not name the id + ledger contents")
    if image_of(res) is not None:
        failures.append("CASE A returned an image — the render was not prevented")

    # ---- CASE A' — same scene, default profile -> silent render --------------
    hr("CASE A' CONTROL — the SAME scene, default profile (no provenance "
       "group)  ->  expect a silent, ordinary render")
    res, dt = await call_render(DEFAULT_ENV, scene_bad)
    timing["case_a_control_render_s"] = round(dt, 1)
    body = "\n".join(texts_of(res))
    png = image_of(res)
    say(f"isError={bool(res.isError)}   image={'yes (%d bytes)' % len(png) if png else 'no'}   wall={dt:.1f}s")
    if body.strip():
        say(body.strip())
    control_ok = (not res.isError) and png is not None \
        and "provenance" not in body.lower()
    say(f"\n  verdict: {'rendered, zero provenance text' if control_ok else 'UNEXPECTED'}"
        " -- provenance is opt-in policy, not core correctness.")
    if not control_ok:
        failures.append("CONTROL: default profile did not render silently")

    # ---- CASE B — the properly-attributed real bone -> PASS ------------------
    hr("CASE B — the real Web3D bone mesh, catalogId='BONE-R5' resolving in "
       "the ledger, SAME strict profile  ->  expect render + no note")
    say(f"asset: {BONE_MESH}")
    say("attribution (from the asset's own header): Don Brutzman, Joe Williams, "
        "John Carlson, Damon Hernandez")
    res, dt = await call_render(STRICT_ENV, scene_good)
    timing["case_b_pass_render_s"] = round(dt, 1)
    body = "\n".join(texts_of(res))
    png = image_of(res)
    say(f"isError={bool(res.isError)}   image={'yes (%d bytes)' % len(png) if png else 'no'}   wall={dt:.1f}s")
    if body.strip():
        say(body.strip())
    if png:
        open(f"{RECEIPTS}/case_b_bone.png", "wb").write(png)
    passed = (not res.isError) and png is not None
    no_note = "provenance" not in body.lower()
    non_blank = "BLANK" not in body            # the cheap gate would have said so
    say(f"\n  verdict: {'PASSED' if passed else 'DID NOT RENDER'}; provenance "
        f"silent: {no_note}; render non-blank: {non_blank}")
    if not passed:
        failures.append("CASE B did not render under STRICT")
    if not no_note:
        failures.append("CASE B still drew a provenance note")
    if not non_blank:
        failures.append("CASE B rendered blank — the bone did not draw")

    # ---- scoreboard ----------------------------------------------------------
    hr("BEAT E SCOREBOARD")
    for k, v in timing.items():
        say(f"  {k:26s}: {v}s")
    say("")
    if failures:
        for f_ in failures:
            say("  FAIL: " + f_)
    else:
        say("  BEAT E SELF-ASSERTION: strict blocked the unsourced 'documented'")
        say("  claim before Chromium ever launched; the default profile proved the")
        say("  gate is opt-in; the properly-attributed Web3D bone rendered clean.")
        say("  Receipts -> " + RECEIPTS)

    with open(f"{RECEIPTS}/beat_e_transcript.txt", "w") as f:
        f.write("$ .venv/bin/python demo/beat_e.py\n" + "\n".join(LOG) + "\n")
    with open(f"{RECEIPTS}/timing.json", "w") as f:
        json.dump(timing, f, indent=1)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
