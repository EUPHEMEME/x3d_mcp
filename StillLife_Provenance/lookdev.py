#!/usr/bin/env python3
"""
lookdev.py -- a visual check harness worth trusting
================================================================================
VERSION 1 · 2026-07-30 · EUPHEME Technologies LLC

WHY THIS EXISTS
    A single 640x480 render tells you a scene is not blank. It does not tell you
    whether the key reads, whether the shadow terminator is mush, whether the
    darks are crushed, or whether the composition holds from any angle but one.
    Look-dev needs more than "not blank", so this renders a scene from several
    angles at working resolution, builds a contact sheet, and reports the
    numbers a colourist would ask for.

WHAT IT MEASURES, and why each one catches a real failure
    coverage        fraction of frame carrying subject rather than background.
                    Near 0 means the camera missed; near 1 means it is inside
                    the geometry.
    black clip      fraction of pixels at or near 0. High means shadow detail is
                    gone -- the classic symptom of a single hard key with no fill
                    and no ambient, which is what you get when a generator emits
                    one DirectionalLight and calls it lit.
    white clip      fraction at or near 255. High means the key is blown; PBR
                    metals do this readily.
    dynamic range   p99 minus p01 luminance. A low number on a "lit" scene is
                    flat lighting pretending to be moody.
    key ratio       mean luminance of the brightest quadrant over the darkest.
                    Around 1 means flat and directionless; very high means the
                    fill is missing.
    saturation      mean chroma. Near zero on a scene with coloured materials
                    means the lighting has washed the colour out.

    None of these replace looking. They tell you WHERE to look.
"""

import asyncio
import math
import os
import sys

sys.path.insert(0, os.path.expanduser("~/x3d_mcp/src"))

VERSION = "1"
OUT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- rendering
async def _render(xml: str, w: int, h: int, wait_ms: int) -> bytes:
    from tools.render import _render_xite_async
    return await _render_xite_async(xml, w, h, wait_ms)


def render_views(scene_builder, name, views, w=900, h=700, wait_ms=3200):
    """scene_builder(viewpoint) -> X3D XML. Renders one PNG per view."""
    paths = []
    for label, vp in views:
        xml = scene_builder(vp)
        png = asyncio.run(_render(xml, w, h, wait_ms))
        p = os.path.join(OUT, "renders", f"{name}__{label}.png")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(png)
        paths.append((label, p))
    return paths


# ---------------------------------------------------------------- measurement
def analyse(path, bg_tol=14, bg_rgb=None):
    from PIL import Image
    import numpy as np
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(float)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]

    # Background: prefer the AUTHORED colour, because corner-sampling fails the
    # moment the subject or its table reaches a corner -- which it did on the
    # very first probe, reporting coverage 0.994 for a sphere occupying a third
    # of frame. Fall back to the modal edge colour, which is still better than
    # corners alone.
    if bg_rgb is not None:
        bg = np.array(bg_rgb, dtype=float)
        if bg.max() <= 1.0:
            bg = bg * 255.0
    else:
        edge = np.concatenate([a[0, :], a[-1, :], a[:, 0], a[:, -1]])
        vals, counts = np.unique((edge // 8).astype(int), axis=0, return_counts=True)
        bg = vals[counts.argmax()] * 8.0 + 4.0
    subject = (np.abs(a - bg).sum(axis=2) > bg_tol)

    h, w = lum.shape
    quads = [lum[:h // 2, :w // 2], lum[:h // 2, w // 2:],
             lum[h // 2:, :w // 2], lum[h // 2:, w // 2:]]
    qmeans = [float(q.mean()) for q in quads]

    mx = a.max(axis=2); mn = a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)

    return {
        "coverage":      float(subject.mean()),
        "black_clip":    float((lum <= 2).mean()),
        "white_clip":    float((lum >= 253).mean()),
        "dyn_range":     float(np.percentile(lum, 99) - np.percentile(lum, 1)),
        "key_ratio":     float(max(qmeans) / max(min(qmeans), 1e-6)),
        "saturation":    float(sat[subject].mean()) if subject.any() else 0.0,
        "mean_lum":      float(lum.mean()),
        "stddev":        float(lum.std()),
    }


VERDICTS = [
    ("coverage",   0.06, 0.85, "subject fills a sane fraction of frame"),
    ("black_clip", 0.0,  0.22, "shadow detail survives"),
    ("white_clip", 0.0,  0.06, "highlights not blown"),
    ("dyn_range",  55.0, 255., "scene has range, not flat"),
    ("key_ratio",  1.25, 14.0, "lighting has direction but keeps fill"),
    ("saturation", 0.10, 0.95, "colour survives the lighting"),
]


def report(name, stats):
    print(f"\n  {name}")
    ok = True
    for k, lo, hi, why in VERDICTS:
        v = stats[k]
        good = lo <= v <= hi
        ok &= good
        print(f"    {'ok ' if good else 'FLAG'} {k:<11} {v:>8.3f}   [{lo}–{hi}]  {why}")
    return ok


def contact_sheet(paths, out_name, cols=3, label_h=26):
    from PIL import Image, ImageDraw
    ims = [(l, Image.open(p).convert("RGB")) for l, p in paths]
    w, h = ims[0][1].size
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * w, rows * (h + label_h)), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * (h + label_h)
        sheet.paste(im, (x, y + label_h))
        d.text((x + 8, y + 7), label, fill=(235, 235, 240))
    p = os.path.join(OUT, "renders", out_name)
    sheet.save(p)
    return p


if __name__ == "__main__":
    print(f"  lookdev v{VERSION} -- import render_views / analyse / report / contact_sheet")
