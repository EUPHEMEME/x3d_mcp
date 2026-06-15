#!/usr/bin/env python3
"""Tileable PBR textures for the cave look-dev (limestone + water).

Run with the numpy/PIL environment:
    ALLEUPHEME/mflux-env/bin/python generate_cave_textures.py

Writes cave_textures/{limestone_albedo,limestone_normal,limestone_mr,
water_normal}.png  -- a metallic-roughness PBR set (glTF convention: MR texture
green=roughness, blue=metallic) used by the X3D PhysicalMaterial walls/floor.

All maps are seamlessly tileable (value noise on wrapping integer lattices;
gradients via np.roll), so they repeat across the large cave surfaces without
visible seams. The textures are interpretive surface detail, not survey data.
"""
import os
import numpy as np
from PIL import Image

SIZE = 512
OUT = "cave_textures"
os.makedirs(OUT, exist_ok=True)


def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def vnoise(size, period, seed):
    """Tileable value noise: random wrapping lattice, smooth (separable) interp."""
    rng = np.random.default_rng(seed)
    lat = rng.random((period, period))
    u = np.arange(size) / size * period
    i = np.floor(u).astype(int)
    f = fade(u - np.floor(u))
    i0, i1 = i % period, (i + 1) % period
    rowx = lat[:, i0] * (1 - f) + lat[:, i1] * f          # interp columns
    out = rowx[i0, :] * (1 - f)[:, None] + rowx[i1, :] * f[:, None]  # interp rows
    return out


def fractal(size, base, octaves, seed):
    h, amp, tot = np.zeros((size, size)), 1.0, 0.0
    for o in range(octaves):
        h += amp * vnoise(size, base * (2 ** o), seed + o)
        tot += amp
        amp *= 0.5
    h /= tot
    return (h - h.min()) / (h.max() - h.min() + 1e-9)


def to_normal(h, strength):
    """Tileable tangent-space normal map from a height field."""
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], -1)
    return (n * 255).astype("uint8")


def save(arr, name):
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8")).save(f"{OUT}/{name}")


# --- limestone ------------------------------------------------------------
h = fractal(SIZE, 6, 6, 1)                       # bedrock relief
cracks = fractal(SIZE, 22, 3, 7)
crackmask = (cracks < 0.13).astype(float)        # thin solution cracks
h = np.clip(h - 0.3 * crackmask, 0, 1)

stain = fractal(SIZE, 4, 3, 13)                  # iron / organic staining
albedo = np.stack([
    0.58 + 0.20 * h + 0.12 * stain,              # R (warm)
    0.55 + 0.18 * h + 0.05 * stain,              # G
    0.49 + 0.15 * h + 0.00 * stain,              # B (cool)
], -1) * (1 - 0.55 * crackmask)[..., None]
save(albedo, "limestone_albedo.png")

Image.fromarray(to_normal(h, 3.0)).save(f"{OUT}/limestone_normal.png")

rough = np.clip(0.70 + 0.24 * (1 - h) + 0.12 * crackmask, 0, 1)   # rougher in pits
mr = np.stack([np.zeros_like(h), rough, np.zeros_like(h)], -1)    # G=rough, B=metal0
save(mr, "limestone_mr.png")

# --- water ripples (normal only) ------------------------------------------
yy, xx = np.mgrid[0:SIZE, 0:SIZE] / SIZE
wh = (np.sin(xx * 2 * np.pi * 6 + np.sin(yy * 2 * np.pi * 3)) * 0.5
      + np.sin(yy * 2 * np.pi * 7 + np.cos(xx * 2 * np.pi * 4)) * 0.5)
wh += 0.6 * fractal(SIZE, 10, 3, 31)
wh = (wh - wh.min()) / (wh.max() - wh.min())
Image.fromarray(to_normal(wh, 1.2)).save(f"{OUT}/water_normal.png")

print(f"wrote 4 textures to {OUT}/")
