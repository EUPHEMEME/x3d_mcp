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
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field as dc_field
from typing import Callable, Optional

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
    """

    def __init__(self, renderer: Callable[[str], bytes],
                 semantic_validator: Optional[Callable[[str], str]] = None,
                 human_signoff: Optional[Callable[[], bool]] = None):
        self.renderer = renderer
        self.validate = semantic_validator or (lambda scene: "")
        self.human_signoff = human_signoff or (lambda: False)

    def check(self, scene: str, cost: str = CHEAP,
              preview_path: str = "") -> GateResult:
        # 1. semantic validation — block with the errors as corrections
        errs = (self.validate(scene) or "").strip()
        if not looks_clean(errs):
            return GateResult(False, cost, "validate_semantic not clean",
                              corrections=[errs])
        # 2. render and look
        try:
            png = self.renderer(scene)
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
        # 3. graduated sign-off proportional to irreversibility
        if cost == EXPENSIVE and not self.human_signoff():
            return GateResult(
                False, EXPENSIVE, "awaiting architect sign-off", receipt=receipt,
                needs_human_signoff=True, preview_path=preview_path,
                corrections=["Preview is non-blank and validated. The expensive "
                             "offline render is irreversible — surfacing the "
                             "preview and stopping for the human architect to "
                             "sign off. The draftsman must not pour concrete "
                             "alone."])
        return GateResult(True, cost, receipt=receipt, preview_path=preview_path)
