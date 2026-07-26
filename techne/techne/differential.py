"""differential.py — verify-by-differential-render: does each node actually put pixels on screen?

The occupation gate (gate.py) answers ONE question: is the frame blank? That catches a scene
that renders to nothing, and it is the failure mode the documented catalog produces most often.
But it is silent on the case a Web3D 2026 reviewer named exactly: a humanoid missing from an
otherwise-populated scene renders a perfectly non-blank frame and passes.

This module answers the next question up the ladder — *did this particular node contribute
anything?* — and it answers it DETERMINISTICALLY, with no model in the loop:

    render(scene)  vs  render(scene without node N)

If the two images are pixel-identical, N contributed nothing. It is in the document, it passed
the XSD, the craft rules admitted it, the frame is non-blank — and it is not on screen. That is
precisely the shape of every silent failure in the catalog:

  * an HAnimJoint routed into `children` instead of `skeleton`  -> the humanoid never draws
  * an ImageTexture in a slot PhysicalMaterial does not define  -> the texture never applies
  * an EnvironmentLight whose `global` flag the serializer drops -> the light never lights

One mechanism catches all three, because all three share the same observable: a node that is
present in the document and absent from the image.

WHY THIS STAYS HARD (blocking) RATHER THAN ADVISORY. The check introduces no learned model and
no probabilistic judgement. It is a comparison of two byte arrays produced by the same renderer
from two inputs differing by one subtree. Determinism — the governing commitment of the layer —
is preserved, so a violation may block. Semantic questions ("is that a *moose*?") necessarily
require a model and therefore belong in the SOFT tier; they are not this module's business.

COST. Each candidate costs one render, so a scene with N candidates costs N+1. This is why the
check is opt-in and bounded by `max_nodes`: it belongs before a commitment, not on every call.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable, Optional

# Node types whose presence should be observable in a render. Each is a documented
# silent-failure site: geometry that may never draw, a texture that may never apply,
# a light that may never light.
SIGNIFICANT_TAGS = (
    "Shape",
    "HAnimHumanoid",
    "ImageTexture",
    "EnvironmentLight",
    "DirectionalLight",
    "PointLight",
    "SpotLight",
)

# A render is a lossy observation: anti-aliasing and dithering can flip a handful of pixels
# between otherwise-identical frames. A node must move at least this fraction of the frame to
# count as contributing, so the check does not credit a node for renderer noise.
MIN_CHANGED_FRACTION = 0.0005          # 0.05% of pixels — ~500 px in a 1000x1000 frame

MAX_NODES_DEFAULT = 12                 # bound the render budget


@dataclass
class NodeContribution:
    """One node's verdict: did removing it change the image?"""
    tag: str
    ident: str                          # DEF name if present, else a positional path
    contributed: bool
    changed_pixels: int = 0
    total_pixels: int = 0
    note: str = ""

    @property
    def changed_fraction(self) -> float:
        return (self.changed_pixels / self.total_pixels) if self.total_pixels else 0.0


@dataclass
class DifferentialResult:
    ran: bool
    contributions: list                  # list[NodeContribution]
    note: str = ""

    @property
    def absent(self) -> list:
        """Nodes present in the document but absent from the image — the finding."""
        return [c for c in self.contributions if not c.contributed]


# --- scene surgery ----------------------------------------------------------

def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _serialize(root) -> str:
    """Serialize preserving the DEFAULT namespace form the document arrived in.

    ElementTree otherwise rewrites `<X3D xmlns="...x3d-4.0.xsd">` as `<ns0:X3D xmlns:ns0="...">`,
    which is namespace-equivalent XML but a different byte-form — and a namespace-unaware X3D
    parser may simply refuse it. That matters twice over here: the gate may render this string for
    its blank check, and EVERY variant is produced this way, so a rejected prefix form would blank
    all of them and make every node look absent. Registering the default prefix keeps the output in
    the form the renderer already accepted."""
    uri = root.tag[1:root.tag.index("}")] if root.tag.startswith("{") else ""
    if uri:
        ET.register_namespace("", uri)
    return ET.tostring(root, encoding="unicode")


def _ident(el, index: int) -> str:
    """A stable, human-readable handle: the DEF name when the author gave one."""
    for key in ("DEF", "name", "USE"):
        v = el.get(key)
        if v:
            return v
    return "%s[%d]" % (_strip_ns(el.tag), index)


def candidates(scene_xml: str, tags=SIGNIFICANT_TAGS, max_nodes: int = MAX_NODES_DEFAULT):
    """Every node worth testing, as (index, tag, ident). Index is the position in a
    document-order walk, which is what `scene_without` removes by — stable for a fixed
    document and independent of DEF naming."""
    try:
        root = ET.fromstring(scene_xml)
    except ET.ParseError:
        return []
    out = []
    for i, el in enumerate(root.iter()):
        t = _strip_ns(el.tag)
        if t in tags:
            out.append((i, t, _ident(el, i)))
            if len(out) >= max_nodes:
                break
    return out


def scene_without(scene_xml: str, index: int) -> Optional[str]:
    """Re-serialize the scene with the node at document-order `index` removed (subtree and all).

    Returns None if the index is not removable — notably the root, which has no parent. Attribute
    order and whitespace may normalize; that is harmless here because BOTH sides of the comparison
    are re-serialized the same way (see `contributions`, which renders a round-tripped baseline
    rather than the original string, so serialization is not a confound)."""
    try:
        root = ET.fromstring(scene_xml)
    except ET.ParseError:
        return None
    parent_of = {}
    for parent in root.iter():
        for child in parent:
            parent_of[id(child)] = parent
    nodes = list(root.iter())
    if index <= 0 or index >= len(nodes):
        return None
    target = nodes[index]
    parent = parent_of.get(id(target))
    if parent is None:
        return None
    parent.remove(target)
    return _serialize(root)


def roundtrip(scene_xml: str) -> Optional[str]:
    """The scene parsed and re-serialized WITHOUT removing anything — the honest baseline.
    Comparing a removal against this (rather than against the original string) ensures the
    only difference between the two renders is the missing node, never the serializer."""
    try:
        return _serialize(ET.fromstring(scene_xml))
    except ET.ParseError:
        return None


# --- pixel comparison -------------------------------------------------------

def _gray(png: bytes):
    """Decode to a flat grayscale sequence (one value per pixel). Pillow when available;
    otherwise None, and the caller falls back to byte comparison (sound for a deterministic
    renderer, just coarser).

    Uses tobytes() rather than getdata(): for mode "L" that is exactly one byte per pixel, it
    iterates as ints, and it avoids Image.getdata(), which Pillow has deprecated for removal in
    Pillow 14. It is also materially faster on large frames, which matters when the differential
    check decodes N+1 of them."""
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("L")
        return im.tobytes()
    except Exception:
        return None


def compare(a_png: bytes, b_png: bytes) -> tuple:
    """(changed_pixels, total_pixels, exact_note). Falls back to a byte-identity test when the
    image cannot be decoded, in which case counts are reported as -1 rather than invented."""
    if not a_png or not b_png:
        return (-1, -1, "missing render")
    ga, gb = _gray(a_png), _gray(b_png)
    if ga is None or gb is None or len(ga) != len(gb):
        return (0 if a_png == b_png else -1, -1, "byte comparison (no decoder)")
    changed = sum(1 for x, y in zip(ga, gb) if x != y)
    return (changed, len(ga), "")


# --- the check ---------------------------------------------------------------

def contributions(scene_xml: str, renderer: Callable[[str], bytes],
                  tags=SIGNIFICANT_TAGS, max_nodes: int = MAX_NODES_DEFAULT,
                  min_fraction: float = MIN_CHANGED_FRACTION,
                  base_png: Optional[bytes] = None) -> DifferentialResult:
    """Render the scene once, then once per candidate with that candidate removed, and report
    which candidates changed nothing. FAIL-SAFE, matching the gate's own asymmetry: if a render
    or a decode fails we do NOT claim a node is absent — an unknown is reported as a note, never
    as a finding, because a false accusation of invisibility is worse than a missed one here.

    `base_png` lets a caller that has ALREADY rendered the baseline pass it in, so the whole check
    costs N+1 renders rather than N+2. The contract is exact and the caller must honour it: the
    bytes must be a render of `roundtrip(scene_xml)`, NOT of the original string. Every variant is
    produced by re-serializing through ElementTree, so a baseline rendered from the raw string
    would differ from the variants by serialization as well as by the removed node — and that
    difference would be silently attributed to the node. When in doubt, omit it and pay the extra
    render; correctness is worth more than one frame."""
    base_scene = roundtrip(scene_xml)
    if base_scene is None:
        return DifferentialResult(False, [], "scene is not parseable XML")
    cands = candidates(scene_xml, tags=tags, max_nodes=max_nodes)
    if not cands:
        return DifferentialResult(False, [], "no significant nodes to test")
    if base_png is None:
        try:
            base_png = renderer(base_scene)
        except Exception as e:
            return DifferentialResult(False, [], "baseline render failed: %s" % e)

    out = []
    for index, tag, ident in cands:
        variant = scene_without(scene_xml, index)
        if variant is None:
            continue
        try:
            var_png = renderer(variant)
        except Exception as e:
            out.append(NodeContribution(tag, ident, True, note="render failed: %s" % e))
            continue
        changed, total, note = compare(base_png, var_png)
        if changed < 0:
            # undecidable — credit the node rather than accuse it
            out.append(NodeContribution(tag, ident, True, note=note or "undecidable"))
            continue
        frac = (changed / total) if total > 0 else (1.0 if changed else 0.0)
        out.append(NodeContribution(tag, ident, frac >= min_fraction,
                                    changed, max(total, 0), note))
    return DifferentialResult(True, out)


def correction_for(c: NodeContribution) -> str:
    """The prescriptive correction for a node that is in the document but not in the image —
    the error message IS the fix, matching rules.py's contract. The remedies are ordered by how
    often the catalog says they are the cause."""
    if c.tag == "ImageTexture":
        return ("'%s' (%s) is in the document but contributes no pixels: the texture is not "
                "reaching the surface. Check its containerField names a slot the material "
                "actually defines (baseTexture/emissiveTexture/normalTexture/... for "
                "PhysicalMaterial — NOT the default 'texture'), and that its url resolves."
                % (c.ident, c.tag))
    if c.tag in ("EnvironmentLight", "DirectionalLight", "PointLight", "SpotLight"):
        return ("'%s' (%s) is in the document but changes nothing in the render: the light is "
                "not lighting. For EnvironmentLight check that global='true' survived "
                "serialization (x3d.py drops it, Bug 2); otherwise check intensity, colour, "
                "and that the light is in scope for the geometry."
                % (c.ident, c.tag))
    if c.tag == "HAnimHumanoid":
        return ("'%s' (%s) is in the document but draws nothing: the humanoid is invisible. The "
                "usual cause is a skeleton root joint routed into 'children' instead of "
                "containerField='skeleton' (x3d.py Bug 1); also check the HAnim component is "
                "declared and that skin/segments carry geometry."
                % (c.ident, c.tag))
    return ("'%s' (%s) is in the document but contributes no pixels. Check that it is on-camera, "
            "lit, non-degenerate, and attached through the containerField its parent defines."
            % (c.ident, c.tag))
