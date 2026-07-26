#!/usr/bin/env python3
"""differential_probe.py — does verify-by-differential-render catch the documented
silent failures against the REAL renderer? (techne/techne/differential.py, end-to-end)

The unit tests prove the differential mechanism against a fake renderer. This probe is
the decisive end-to-end question: matched PAIRS of small X3D 4.0 scenes — identical
except for ONE documented defect — rendered by the same X_ITE + headless-Chromium path
the x3d_mcp server uses, with differential.contributions() asked to say which nodes put
pixels on screen. The result that matters: the defective variant must report its node
contributing ZERO (or sub-threshold) pixels while the correct variant reports it
contributing, and the all-correct control must produce no false positives.

RENDERER — reused, not reimplemented: `src/tools/render.py::_render_xite_async`, the
exact function behind the server's `render_image` / `render_current_scene` MCP tools
(X_ITE fetched from CDN into headless Chromium under SwiftShader, scene served over
loopback, canvas screenshotted). Each render launches a fresh browser and fetches the
X_ITE library from the network, so this probe needs Playwright + Chromium + network and
takes minutes. That is why it is a script here and not a pytest test.

THE PAIRS
  1. HAnim (x3d.py Bug 1): skeleton root joint with containerField='skeleton' vs the
     attribute dropped, so the joint lands in the humanoid's default 'children' slot —
     a field HAnimHumanoid does not define — and the whole figure silently vanishes
     from an otherwise-populated frame. The case the Web3D reviewer named; the blank-
     frame gate (gate.py) cannot see it, because the pedestal keeps the frame non-blank.
     CONFOUND, controlled: Bug 5 (the raw server never emits <component name='HAnim'/>,
     so HAnim scenes render blank REGARDLESS of containerField). Both members of the
     pair pass through craft.reassert_profile, which injects the component declaration
     into each identically — what remains between the variants is Bug 1 alone.
  2. PBR texture: ImageTexture with containerField='baseTexture' on a PhysicalMaterial
     vs the default 'texture' slot, which PhysicalMaterial does not define — the
     texture silently never applies. (The texture is a data: URI so nothing depends on
     the served directory's contents.)
  3. Lighting (x3d.py Bug 2): EnvironmentLight with global='true' vs the attribute
     dropped. The light sits inside an otherwise-empty Transform ("light rig") because
     scoping is the only position where `global` can matter at all: a ROOT-level
     light's scope is already the whole Scene, global or not — the probe measures that
     too (see the root-scope note it prints).
     Measured reality of THIS renderer (X_ITE 15.1.12, measured 2026-07-25, and why
     this pair may honestly fail to separate): X_ITE does not apply an EnvironmentLight
     that sits inside a Transform even when global='true' (a root-level one with plain
     color+intensity does light, and on='false' kills it — so the node itself works).
     When the correct variant's light is as absent from the image as the defective
     one's, the pair is NOT SEPARABLE and the probe says so rather than pretending.
  3b. Same defect class, implemented scoping: DirectionalLight global='true' vs
     dropped, in the same light-rig pattern. X_ITE honors `global` for DirectionalLight,
     so this pair shows the differential separating the dropped-global defect whenever
     the renderer implements scoping — pinning the case-3 outcome on the renderer's
     EnvironmentLight gap, not on the check.
  C. CONTROL: an entirely correct scene (scoped DirectionalLight, textured Material —
     the ImageTexture correctly in Appearance's default 'texture' slot). Every
     significant node must be reported as contributing: no false positives.

HONESTY RULES. The probe refuses to conclude anything when the renderer itself did not
draw: it first renders a known-good scene and checks it non-blank (gate.inspect_render);
a blank there means "could not run" (exit 2, with what is missing), never a finding. It
also renders one identical frame twice and reports the pixel noise between them, so the
zero-vs-nonzero verdicts can be read against the renderer's actual determinism.

Run:
    cd /Users/alexander/x3d_mcp/techne && ../.venv/bin/python eval/differential_probe.py

Knobs (env): DIFFPROBE_OUT (artifact dir; default: a fresh temp dir), DIFFPROBE_W/H
(frame size, default 512x384), DIFFPROBE_WAIT_MS (X_ITE settle time, default 6000),
X3D_MCP_REPO (repo root, default: inferred from this file's location).

Exit codes: 0 = ran, control clean, no defect was MISSED (a truly-invisible node
credited as contributing); 1 = a false positive or a miss; 2 = could not run at all.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PROBE_VERSION = "differential_probe v1.0 (2026-07-25)"

# --- locate the repo and make BOTH packages importable ----------------------
# The probe lives at <repo>/techne/eval/; the renderer lives at <repo>/src/tools/ and
# the check at <repo>/techne/techne/. Neither is installed into the venv as a package,
# so the path bootstrap is explicit rather than implied by the working directory.
_HERE = Path(__file__).resolve()
REPO = Path(os.environ.get("X3D_MCP_REPO", _HERE.parents[2]))
for p in (str(REPO / "src"), str(REPO / "techne")):
    if p not in sys.path:
        sys.path.insert(0, p)

WIDTH = int(os.environ.get("DIFFPROBE_W", "512"))
HEIGHT = int(os.environ.get("DIFFPROBE_H", "384"))
WAIT_MS = int(os.environ.get("DIFFPROBE_WAIT_MS", "6000"))

# An 8x8 magenta/yellow checker as a data: URI, so the texture pair depends on nothing
# outside the scene string (the renderer serves a temp dir containing only the scene).
_CHECKER = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAA"
            "G0lEQVR4nGN4prHl1x0NTJIBq+gzjS0Mg1IHAAQJeAFKrmHgAAAAAElFTkSuQmCC")

# --- the matched pairs ------------------------------------------------------
# One template per case with a single {defect} slot, so "identical except for one
# defect" is enforced by construction rather than by careful copying.

HANIM_TEMPLATE = """<X3D profile='Immersive' version='4.0'>
  <Scene>
    <Viewpoint DEF='V' position='0 0 7' description='differential probe'/>
    <Transform translation='0 -1.6 0'>
      <Shape DEF='Pedestal'>
        <Appearance><Material diffuseColor='0.25 0.55 0.3'/></Appearance>
        <Box size='4 0.2 4'/>
      </Shape>
    </Transform>
    <HAnimHumanoid DEF='Human' name='probe_human' version='2.0'>
      <HAnimJoint name='humanoid_root'{defect}>
        <HAnimSegment name='sacrum'>
          <Shape DEF='Torso'>
            <Appearance><Material diffuseColor='0.95 0.95 0.95'/></Appearance>
            <Box size='1.2 1.2 1.2'/>
          </Shape>
        </HAnimSegment>
      </HAnimJoint>
    </HAnimHumanoid>
  </Scene>
</X3D>"""

PBR_TEMPLATE = """<X3D profile='Immersive' version='4.0'>
  <Scene>
    <Viewpoint DEF='V' position='0 0 5' description='differential probe'/>
    <Shape DEF='TexturedBox'>
      <Appearance>
        <PhysicalMaterial baseColor='1 1 1'>
          <ImageTexture DEF='BaseTex'{defect} url='"%s"'/>
        </PhysicalMaterial>
      </Appearance>
      <Box size='2.4 2.4 2.4'/>
    </Shape>
  </Scene>
</X3D>""" % _CHECKER

# The emissive Beacon keeps the frame non-blank even when the main box goes dark, so
# every defective variant in the lighting cases is a frame the blank gate PASSES —
# the differential is being tested exactly where the gate is blind.
ENVLIGHT_TEMPLATE = """<X3D profile='Immersive' version='4.0'>
  <Scene>
    <NavigationInfo headlight='false'/>
    <Viewpoint DEF='V' position='0 0 6' description='differential probe'/>
    <Transform DEF='LightRig'>
      <EnvironmentLight DEF='IBL'{defect} color='1 1 1' intensity='1'/>
    </Transform>
    <Shape DEF='LitBox'>
      <Appearance><PhysicalMaterial baseColor='0.9 0.35 0.15'/></Appearance>
      <Box size='2.4 2.4 2.4'/>
    </Shape>
    <Transform translation='-2.2 -1.5 1'>
      <Shape DEF='Beacon'>
        <Appearance><Material emissiveColor='0.15 0.4 0.95'/></Appearance>
        <Box size='0.5 0.5 0.5'/>
      </Shape>
    </Transform>
  </Scene>
</X3D>"""

DIRLIGHT_TEMPLATE = """<X3D profile='Immersive' version='4.0'>
  <Scene>
    <NavigationInfo headlight='false'/>
    <Viewpoint DEF='V' position='0 0 6' description='differential probe'/>
    <Transform DEF='LightRig'>
      <DirectionalLight DEF='Key'{defect} direction='-0.3 -0.4 -1' intensity='1'/>
    </Transform>
    <Shape DEF='LitBox'>
      <Appearance><Material diffuseColor='0.9 0.35 0.15'/></Appearance>
      <Box size='2.4 2.4 2.4'/>
    </Shape>
    <Transform translation='-2.2 -1.5 1'>
      <Shape DEF='Beacon'>
        <Appearance><Material emissiveColor='0.15 0.4 0.95'/></Appearance>
        <Box size='0.5 0.5 0.5'/>
      </Shape>
    </Transform>
  </Scene>
</X3D>"""

# Root-scope companion measurement for case 3: at Scene root, a light's scope is the
# whole Scene whether global is present or not, so Bug 2 SHOULD be visually inert
# there — the probe measures it instead of asserting it.
ENVLIGHT_ROOT_TEMPLATE = """<X3D profile='Immersive' version='4.0'>
  <Scene>
    <NavigationInfo headlight='false'/>
    <Viewpoint DEF='V' position='0 0 6' description='differential probe'/>
    <EnvironmentLight DEF='IBL'{defect} color='1 1 1' intensity='1'/>
    <Shape DEF='LitBox'>
      <Appearance><PhysicalMaterial baseColor='0.9 0.35 0.15'/></Appearance>
      <Box size='2.4 2.4 2.4'/>
    </Shape>
  </Scene>
</X3D>"""

CONTROL_SCENE = """<X3D profile='Immersive' version='4.0'>
  <Scene>
    <NavigationInfo headlight='false'/>
    <Viewpoint DEF='V' position='0 0 6' description='differential probe'/>
    <DirectionalLight DEF='KeyLight' global='true' direction='-0.3 -0.5 -1' intensity='1'/>
    <Shape DEF='Subject'>
      <Appearance>
        <Material diffuseColor='1 1 1'/>
        <ImageTexture DEF='ControlTex' url='"%s"'/>
      </Appearance>
      <Box size='2.2 2.2 2.2'/>
    </Shape>
  </Scene>
</X3D>""" % _CHECKER


@dataclass
class Case:
    name: str
    bug: str                      # the documented defect this pair isolates
    template: str
    correct: str                  # text for the {defect} slot, correct variant
    defective: str                # text for the {defect} slot, defective variant
    defect_ident: str             # DEF name of the node whose pixels are in question
    note: str = ""                # printed with the case, for known confounds


CASES = [
    Case("1. HAnim skeleton containerField",
         "x3d.py Bug 1 — joint routed into 'children' instead of 'skeleton'",
         HANIM_TEMPLATE, " containerField='skeleton'", "", "Human",
         note=("Bug 5 is controlled: craft.reassert_profile injected the HAnim "
               "component declaration into BOTH variants (shown above), so the only "
               "difference left inside the pair is the containerField. 'Torso' rides "
               "inside the discarded joint, so expect it absent too in the defective "
               "variant — same root cause, two reported nodes.")),
    Case("2. PBR baseTexture containerField",
         "ImageTexture in the default 'texture' slot, which PhysicalMaterial does not define",
         PBR_TEMPLATE, " containerField='baseTexture'", "", "BaseTex"),
    Case("3. EnvironmentLight global (in a light rig)",
         "x3d.py Bug 2 — the serializer drops global='true'",
         ENVLIGHT_TEMPLATE, " global='true'", "", "IBL",
         note=("Measured X_ITE 15.1.12 reality: an in-Transform EnvironmentLight is "
               "not applied even with global='true', so the correct variant's light "
               "may be reported absent too — a true 'in the document, not in the "
               "image' finding, but then the pair does NOT separate on `global` and "
               "the verdict below must say so. Case 3b covers the same defect class "
               "with a light whose scoping X_ITE does implement.")),
    Case("3b. DirectionalLight global (same rig pattern)",
         "the dropped-global defect class, on a light X_ITE scopes correctly",
         DIRLIGHT_TEMPLATE, " global='true'", "", "Key"),
]


# --- the renderer, wrapped --------------------------------------------------

@dataclass
class Renderer:
    """Sync facade over the server's async X_ITE renderer, with a PNG artifact trail
    and a cache. The cache exists because differential.contributions() re-renders the
    round-tripped baseline the probe has already rendered for its gate receipt — at
    many seconds per render the duplicate is worth eliding, and byte-identical input
    makes it sound."""
    out: Path
    label: str = "scene"
    renders: int = 0
    _cache: dict = field(default_factory=dict)

    def __call__(self, xml: str) -> bytes:
        png = self._cache.get(xml)
        if png is None:
            from tools.render import _render_xite_async
            png = asyncio.run(_render_xite_async(xml, WIDTH, HEIGHT, WAIT_MS))
            self._cache[xml] = png
            self.renders += 1
            (self.out / ("%02d_%s.png" % (self.renders, self.label))).write_bytes(png)
        return png

    def render_fresh(self, xml: str, label: str) -> bytes:
        """Bypass the cache — used exactly once, to measure renderer determinism."""
        from tools.render import _render_xite_async
        png = asyncio.run(_render_xite_async(xml, WIDTH, HEIGHT, WAIT_MS))
        self.renders += 1
        (self.out / ("%02d_%s.png" % (self.renders, label))).write_bytes(png)
        return png


# --- reporting helpers ------------------------------------------------------

def _components_in(xml: str) -> list[str]:
    return re.findall(r"<component[^>]*/>", xml)


def print_contribs(result, min_fraction: float) -> None:
    if not result.ran:
        print("      differential DID NOT RUN: %s" % result.note)
        return
    for c in result.contributions:
        verdict = "CONTRIBUTES" if c.contributed else "ABSENT"
        frac = "%6.2f%%" % (100.0 * c.changed_fraction)
        extra = ("  [%s]" % c.note) if c.note else ""
        print("      %-17s %-11s %8d / %-7d px  %s  -> %s%s"
              % (c.tag, c.ident, c.changed_pixels, c.total_pixels, frac, verdict, extra))
    thresh = int(min_fraction * WIDTH * HEIGHT)
    print("      (threshold: >= %d changed px of %d to count as contributing)"
          % (thresh, WIDTH * HEIGHT))


def find(result, ident):
    for c in result.contributions:
        if c.ident == ident:
            return c
    return None


def pair_verdict(ok, bad) -> tuple[str, str]:
    """(verdict, explanation) for the defect node's contributions in the correct (ok)
    and defective (bad) variants. Only 'MISSED' indicts the check itself; a node the
    renderer never draws even when authored correctly is a renderer limitation the
    probe reports rather than papers over."""
    if ok is None or bad is None:
        return ("UNDECIDED", "defect node was not among the tested candidates")
    if ok.contributed and not bad.contributed:
        return ("SEPARATED",
                "correct variant contributes %d px; defective contributes %d px — the "
                "differential catches this defect deterministically"
                % (ok.changed_pixels, bad.changed_pixels))
    if not ok.contributed:
        return ("NOT SEPARABLE (renderer)",
                "the node is absent from the image even when authored correctly "
                "(%d px) — a true differential finding, but this renderer gives the "
                "pair nothing to separate on" % ok.changed_pixels)
    return ("MISSED",
            "the defective variant's node still contributes %d px — the defect has no "
            "visual consequence here, or the check failed" % bad.changed_pixels)


# --- main -------------------------------------------------------------------

def main() -> int:
    print(PROBE_VERSION)
    print("renderer: src/tools/render.py::_render_xite_async  (X_ITE + Playwright "
          "headless Chromium — the same function behind the render_image MCP tool)")
    print("frame: %dx%d, wait %d ms, repo %s" % (WIDTH, HEIGHT, WAIT_MS, REPO))

    # Preflight: the two abilities the probe cannot fake. Missing either is exit 2 —
    # "could not run" is a valid outcome, a synthetic fallback is not.
    try:
        import playwright.async_api  # noqa: F401
    except ImportError:
        print("\nCOULD NOT RUN: Playwright is not installed in the venv.")
        print("  fix: .venv/bin/pip install playwright && "
              ".venv/bin/python -m playwright install chromium")
        return 2
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("\nCOULD NOT RUN: Pillow is missing, so changed-pixel counts would "
              "degrade to byte-compares and every verdict would be 'undecidable'.")
        print("  fix: .venv/bin/pip install Pillow")
        return 2

    from techne import differential
    from techne.craft import reassert_profile
    from techne.gate import inspect_render

    out = Path(os.environ.get("DIFFPROBE_OUT")
               or tempfile.mkdtemp(prefix="techne_diffprobe_"))
    out.mkdir(parents=True, exist_ok=True)
    print("artifacts: %s\n" % out)

    render = Renderer(out)
    min_fraction = differential.MIN_CHANGED_FRACTION

    # Every scene passes through reassert_profile — the repo's Bug 5 control — and
    # deliberately NOT through reassert_envlight_global, which would inject the very
    # global='true' whose absence case 3 exists to test.
    def build(template: str, slot: str, fname: str) -> str:
        xml = reassert_profile(template.format(defect=slot))
        (out / fname).write_text(xml, encoding="utf-8")
        return xml

    control_xml = reassert_profile(CONTROL_SCENE)
    (out / "control.x3d").write_text(control_xml, encoding="utf-8")

    # -- sanity: does this renderer draw AT ALL, and how deterministically? ----
    base = differential.roundtrip(control_xml)
    render.label = "control_baseline"
    try:
        png1 = render(base)
    except Exception as e:                                      # noqa: BLE001
        print("COULD NOT RUN: baseline render failed: %s" % e)
        print("Likely missing: network access for the X_ITE CDN "
              "(cdn.jsdelivr.net), or the Playwright Chromium install.")
        return 2
    receipt = inspect_render(png1)
    if not receipt.non_blank:
        print("COULD NOT RUN: the known-good control scene rendered BLANK "
              "(stddev %.2f). The renderer is not actually drawing here — most "
              "likely the X_ITE CDN was unreachable (each render fetches it) or "
              "software WebGL is unavailable. No verdicts can be drawn; a human "
              "should run:\n  cd %s/techne && ../.venv/bin/python "
              "eval/differential_probe.py" % (receipt.stddev, REPO))
        return 2
    png2 = render.render_fresh(base, "control_determinism_rerun")
    noise, total, _ = differential.compare(png1, png2)
    print("sanity: control renders non-blank (stddev %.1f); identical scene rendered "
          "twice differs by %d/%d px (renderer noise floor; the contribution "
          "threshold is %d px)\n"
          % (receipt.stddev, max(noise, 0), total, int(min_fraction * WIDTH * HEIGHT)))

    failures: list[str] = []

    # -- control: no false positives ------------------------------------------
    print("── CONTROL — entirely correct scene: every node must contribute")
    print("   components injected by reassert_profile: %s"
          % (_components_in(control_xml) or "none"))
    render.label = "control"
    ctrl = differential.contributions(control_xml, render)
    print_contribs(ctrl, min_fraction)
    if not ctrl.ran:
        failures.append("control: differential did not run (%s)" % ctrl.note)
    elif ctrl.absent:
        names = ", ".join("%s '%s'" % (c.tag, c.ident) for c in ctrl.absent)
        print("   verdict: FALSE POSITIVES — %s reported absent in a correct scene" % names)
        failures.append("control false positives: %s" % names)
    else:
        print("   verdict: CLEAN — no false positives")
    print()

    # -- the pairs -------------------------------------------------------------
    for case in CASES:
        slug = case.name.split(".")[0].strip().replace(" ", "_")
        ok_xml = build(case.template, case.correct, "case%s_correct.x3d" % slug)
        bad_xml = build(case.template, case.defective, "case%s_defective.x3d" % slug)

        print("── CASE %s" % case.name)
        print("   defect: %s" % case.bug)
        print("   components injected by reassert_profile: %s"
              % (_components_in(ok_xml) or "none"))
        if case.note:
            print("   note: %s" % case.note)

        results = {}
        for variant, xml in (("correct", ok_xml), ("defective", bad_xml)):
            render.label = "case%s_%s" % (slug, variant)
            frame = render(differential.roundtrip(xml))
            rec = inspect_render(frame)
            print("   variant: %-9s  (frame non-blank: %s, stddev %.1f — the blank "
                  "gate %s this frame)"
                  % (variant, rec.non_blank, rec.stddev,
                     "passes" if rec.non_blank else "would already block"))
            res = differential.contributions(xml, render)
            print_contribs(res, min_fraction)
            results[variant] = res

        ok_c = find(results["correct"], case.defect_ident) if results["correct"].ran else None
        bad_c = find(results["defective"], case.defect_ident) if results["defective"].ran else None
        verdict, why = pair_verdict(ok_c, bad_c)
        print("   pair verdict: %s — %s" % (verdict, why))
        if bad_c is not None and not bad_c.contributed:
            print("   correction the check would emit:\n      %s"
                  % differential.correction_for(bad_c))
        if verdict == "MISSED":
            failures.append("case %s: %s" % (case.name, why))
        if verdict == "UNDECIDED":
            failures.append("case %s: undecided (%s)" % (case.name, why))
        print()

    # -- root-scope note for case 3 -------------------------------------------
    # Not a differential run — a direct A/B of the two root-scope scenes, because the
    # question is about the DEFECT's visibility, not a node's.
    print("── ROOT-SCOPE NOTE (case 3 context)")
    render.label = "env_root_global"
    root_ok = render(differential.roundtrip(
        reassert_profile(ENVLIGHT_ROOT_TEMPLATE.format(defect=" global='true'"))))
    render.label = "env_root_dropped"
    root_bad = render(differential.roundtrip(
        reassert_profile(ENVLIGHT_ROOT_TEMPLATE.format(defect=""))))
    changed, total, note = differential.compare(root_ok, root_bad)
    print("   EnvironmentLight at Scene ROOT, global='true' vs dropped: frames differ "
          "by %d/%d px%s" % (max(changed, 0), total, (" [%s]" % note) if note else ""))
    print("   -> at root scope the light's reach already covers the Scene, so Bug 2 "
          "has %s visual consequence there in this renderer."
          % ("NO" if 0 <= changed < int(min_fraction * WIDTH * HEIGHT) else "A"))
    print()

    print("── SUMMARY  (%d renders total)" % render.renders)
    if failures:
        for f in failures:
            print("   FAIL: %s" % f)
        return 1
    print("   control clean, no defect missed. Where a pair did not separate, the "
          "reason is printed above and is a property of the renderer, not the check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
