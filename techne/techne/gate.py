"""The occupation gate (TECHNE_SPEC §5) — "not done until validated AND
rendered-non-blank AND (for expensive renders) the architect has looked."

This is the genuinely original piece BAML cannot do: BAML `@@assert` is a predicate
over an already-parsed value; it cannot *execute a renderer*, get pixels back, and
assert they are non-blank. The act of rendering and the human look are this layer.

The gate is graduated by irreversibility (the architect/draftsman frame, §0):

  * CHEAP gate  — before a fast preview render: soft, automatic, "looks non-blank?"
  * EXPENSIVE gate — before the hours-long offline photoreal render (the "pour
    concrete" moment): HARD. The draftsman (the model) must never trigger the
    expensive irreversible render on its own authority; the gate surfaces the
    preview and STOPS, awaiting the human architect's sign-off.

A hard prerequisite, already satisfied in this repo: the renderer must be X_ITE,
not X3DOM — X3DOM returns *blank* for HAnim, so an X3DOM gate would check a blank
and pass it. `renderer` defaults to the x3d-mcp X_ITE backend when wired.

One rung above blankness, OPT-IN (config.differential / TECHNE_DIFFERENTIAL):
the differential-render check (differential.py) asks whether each significant
node individually put pixels on screen — the humanoid-missing-from-a-populated-
frame case blankness cannot see. It is ADVISORY by default: adversarial review
established that zero pixel change does not imply an authoring defect (occlusion,
out-of-frustum placement, coincident DEF/USE, and sub-threshold size all produce it
for correct scenes), so a finding informs rather than refuses unless the operator
opts in with TECHNE_DIFFERENTIAL=block. Off entirely by default: N+1 renders.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field as dc_field
from typing import Callable, Optional

from . import differential
from .config import Config

CHEAP = "cheap"
EXPENSIVE = "expensive"

# below this grayscale standard deviation an image is treated as effectively blank
# (all-background, no geometry) — the silent failure only the render catches.
BLANK_STDDEV = 3.0

# markers the real x3d-mcp validate_semantic emits when a scene is clean, e.g.
# "# Semantic Check: All Clear\n\nNo semantic issues found ...". The gate treats
# an empty validator string OR any of these as clean; anything else is dirty.
CLEAN_MARKERS = ("all clear", "no semantic issues", "no issues found", "no issues")


def looks_clean(validator_output: str) -> bool:
    s = (validator_output or "").strip().lower()
    return (not s) or any(m in s for m in CLEAN_MARKERS)


def inspect_render(png_bytes: bytes) -> "RenderReceipt":
    """Public: inspect an already-rendered PNG for blankness (no geometry)."""
    return _png_dims_and_stddev(png_bytes or b"")


@dataclass
class RenderReceipt:
    non_blank: bool
    width: int = 0
    height: int = 0
    stddev: float = 0.0           # luminance spread; ~0 == flat/blank
    note: str = ""


@dataclass
class GateResult:
    passed: bool
    cost: str
    blocked_reason: str = ""
    corrections: list[str] = dc_field(default_factory=list)
    receipt: Optional[RenderReceipt] = None
    needs_human_signoff: bool = False
    preview_path: str = ""
    # The per-node differential findings, when the opt-in differential check ran —
    # a structured DifferentialResult, so a caller can inspect exactly which nodes
    # did (or did not) contribute pixels WITHOUT re-running any renders. Findings
    # ride here as data; corrections carry only the prescriptive text.
    differential: Optional[differential.DifferentialResult] = None
    # SOFT advisories that ride along with a PASSING result (differential findings when
    # the check is advisory). Corrections block; notes inform.
    notes: list[str] = dc_field(default_factory=list)

    @property
    def awaiting_architect(self) -> bool:
        return self.needs_human_signoff and not self.passed


# --- blank detection (dependency-light) ------------------------------------

def _png_dims_and_stddev(data: bytes) -> RenderReceipt:
    """Estimate image dimensions and grayscale stddev from PNG bytes.

    Uses Pillow if present (accurate); otherwise reads the PNG IHDR for size and
    samples the decompressed scanlines for a coarse variance. Never raises.
    """
    try:
        from PIL import Image            # type: ignore
        import io
        im = Image.open(io.BytesIO(data)).convert("L")
        px = im.tobytes()                 # one byte per pixel in "L" mode
        n = len(px) or 1
        mean = sum(px) / n
        var = sum((p - mean) ** 2 for p in px) / n
        sd = var ** 0.5
        return RenderReceipt(sd >= BLANK_STDDEV, im.width, im.height, sd)
    except Exception:
        pass
    # fallback (PIL absent): IHDR for size; sample raw scanlines, skipping the
    # per-scanline PNG filter byte so it does not inject artificial variance.
    try:
        w, h = struct.unpack(">II", data[16:24])
        bit_depth, color_type = data[24], data[25]
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 1)
        stride = 1 + w * channels * (bit_depth // 8 or 1)   # 1 filter byte + row
        idat = b"".join(
            data[i + 8:i + 8 + struct.unpack(">I", data[i:i + 4])[0]]
            for i in _png_chunks(data, b"IDAT"))
        raw = zlib.decompress(idat) if idat else b""
        if not raw:
            return RenderReceipt(False, w, h, 0.0, "no IDAT")
        pix = bytearray()                                   # drop filter bytes
        for off in range(0, len(raw), stride):
            pix += raw[off + 1:off + stride]
        if not pix:
            return RenderReceipt(False, w, h, 0.0, "no pixels")
        sample = pix[:: max(1, len(pix) // 4096)]
        m = sum(sample) / len(sample)
        sd = (sum((b - m) ** 2 for b in sample) / len(sample)) ** 0.5
        return RenderReceipt(sd >= BLANK_STDDEV, w, h, sd, "fallback estimate")
    except Exception as e:
        # fail SAFE: an image we cannot inspect is treated as blank (blocks),
        # never as non-blank (which would pass a possibly-blank render).
        return RenderReceipt(False, 0, 0, 0.0, "could not inspect (%s)" % e)


def _png_chunks(data: bytes, kind: bytes):
    i = 8
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        if data[i + 4:i + 8] == kind:
            yield i + 4
        i += 12 + ln


# --- the gate ---------------------------------------------------------------

class OccupationGate:
    """Holds the render-and-sign-off boundary before forwarding a 'done' signal.

    renderer(scene) -> PNG bytes (default: wire to the x3d-mcp X_ITE backend).
    semantic_validator(scene) -> "" if clean else error text.
    human_signoff() -> bool: returns True only when the architect has approved
      the surfaced preview. Default returns False (so expensive work always stops
      and waits — the draftsman never pours concrete alone).
    config: profile knobs (default: from the environment). When
      config.differential is on (TECHNE_DIFFERENTIAL / profile "differential"),
      the gate also runs verify-by-differential-render (differential.py) — a HARD
      deterministic check that each significant node actually put pixels on
      screen. OFF by default because it costs one render per candidate node
      (N+1 total): it belongs before a commitment, not on every call.
    """

    def __init__(self, renderer: Callable[[str], bytes],
                 semantic_validator: Optional[Callable[[str], str]] = None,
                 human_signoff: Optional[Callable[[], bool]] = None,
                 config: Optional[Config] = None):
        self.renderer = renderer
        self.validate = semantic_validator or (lambda scene: "")
        self.human_signoff = human_signoff or (lambda: False)
        self.config = config or Config.from_env()

    def check(self, scene: str, cost: str = CHEAP,
              preview_path: str = "") -> GateResult:
        # 1. semantic validation — block with the errors as corrections
        notes: list[str] = []
        errs = (self.validate(scene) or "").strip()
        if not looks_clean(errs):
            return GateResult(False, cost, "validate_semantic not clean",
                              corrections=[errs])
        # 2. render and look.
        #    When the differential check is enabled we render the ROUND-TRIPPED scene here rather
        #    than the raw string, so this one frame can serve as both the blankness observation and
        #    the differential's baseline (N+1 renders instead of N+2). The round-trip is a
        #    semantics-preserving re-serialization of the same elements and attributes, so the
        #    blank verdict is unaffected; what it buys is that the baseline and every variant are
        #    serialized identically, which is exactly the confound differential.contributions()
        #    warns about. If the scene will not parse, roundtrip() returns None and we fall back to
        #    the original string — the differential will then decline to run for the same reason.
        render_scene = scene
        if self.config.differential:
            render_scene = differential.roundtrip(scene) or scene
        try:
            png = self.renderer(render_scene)
        except Exception as e:
            return GateResult(False, cost, "render failed: %s" % e)
        receipt = _png_dims_and_stddev(png or b"")
        if not receipt.non_blank:
            return GateResult(
                False, cost, "render is blank (no geometry) — a silent failure "
                "only the render catches", receipt=receipt,
                corrections=["The scene rendered blank. Check that geometry is "
                             "present, lit, on-camera, and that HAnim/PBR "
                             "containerFields are correct (render via X_ITE, not "
                             "X3DOM, which is blank for HAnim)."])
        # 3. differential render (OPT-IN — costs N+1 renders). The ORDER here is
        #    load-bearing: semantic validation, then blank-frame, then this. A
        #    scene that failed validation never rendered at all; a blank scene was
        #    caught by a single render. Running the differential on either would
        #    spend N more renders to restate a failure the cheap check already
        #    found. The differential exists for the one case those checks CANNOT
        #    see — a non-blank, validated frame from which a single node is
        #    silently missing — so it runs only once that case is reachable. It
        #    also runs BEFORE the sign-off boundary: never ask the architect to
        #    approve a preview a deterministic check can prove incomplete.
        dr: Optional[differential.DifferentialResult] = None
        if self.config.differential:
            dr = differential.contributions(
                scene, self.renderer,
                max_nodes=(self.config.differential_max_nodes
                           or differential.MAX_NODES_DEFAULT),
                # reuse the frame from step 2 — it was rendered from the round-tripped
                # scene precisely so it satisfies this parameter's contract
                base_png=(png if render_scene is not scene else None))
            # SOFT BY DEFAULT — advisory, not blocking. This was wired HARD and demoted after
            # adversarial review found that "zero pixel change" and "authoring defect" are NOT
            # the same proposition for a correctly-authored scene. A node can legitimately move
            # zero pixels when it is occluded, outside the bound viewpoint's frustum, duplicated
            # by a coincident DEF/USE (removing either changes nothing, so BOTH get accused), or
            # simply smaller on screen than the noise threshold. Those are routine in navigable
            # X3D, and blocking on them would refuse correct work — the one cost this layer must
            # not impose. The signal is real and worth surfacing; the inference is not sound
            # enough to carry a refusal, so it advises unless the operator explicitly opts in to
            # blocking via TECHNE_DIFFERENTIAL=block after judging it on their own scenes.
            if dr.ran and dr.absent:
                findings = [differential.correction_for(c) for c in dr.absent]
                if self.config.differential_blocks:
                    return GateResult(
                        False, cost,
                        "differential render: %d node(s) present in the document but "
                        "absent from the image" % len(dr.absent),
                        corrections=findings, receipt=receipt, differential=dr)
                notes.extend(findings)
        # 4. graduated sign-off proportional to irreversibility
        if cost == EXPENSIVE and not self.human_signoff():
            return GateResult(
                False, EXPENSIVE, "awaiting architect sign-off", receipt=receipt,
                needs_human_signoff=True, preview_path=preview_path,
                corrections=["Preview is non-blank and validated. The expensive "
                             "offline render is irreversible — surfacing the "
                             "preview and stopping for the human architect to "
                             "sign off. The draftsman must not pour concrete "
                             "alone."], differential=dr)
        return GateResult(True, cost, receipt=receipt, preview_path=preview_path,
                          notes=notes,
                          differential=dr)
