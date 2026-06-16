#!/usr/bin/env python3
"""
Procedural tileable fur PBR maps for the moose -- the cheap real-time win.

Geometry stays untouched; these small GPU-sampled maps add the *illusion* of
shaggy fur (micro-relief + albedo mottle) at near-zero runtime cost.  Run with
the mflux-env python (has numpy+PIL):

    ALLEUPHEME/mflux-env/bin/python generate_moose_textures.py

Outputs (512x512, seamlessly tileable):
    assets/moose_textures/fur_normal.png   tangent-space normal (fur strands)
    assets/moose_textures/fur_mr.png       glTF metallic-roughness (G=rough,B=metal)
    assets/moose_textures/fur_albedo.png   subtle brown fur mottle
"""
import os
import numpy as np
from PIL import Image

N = 512
OUT = "assets/moose_textures"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

def tile_noise(cells):
    """Value noise that tiles exactly (wrap-around bilinear upsample)."""
    g = rng.standard_normal((cells, cells))
    idx = np.linspace(0, cells, N, endpoint=False)
    x0 = np.floor(idx).astype(int) % cells
    x1 = (x0 + 1) % cells
    fx = idx - np.floor(idx)
    a = g[x0, :] * (1 - fx)[:, None] + g[x1, :] * fx[:, None]
    a = a[:, x0] * (1 - fx)[None, :] + a[:, x1] * fx[None, :]
    return a

# clumpy base relief (multi-octave) + fine vertical fur strands (integer
# frequency -> tiles).  Strands run along V (down the body).
h = 1.0 * tile_noise(16) + 0.5 * tile_noise(32) + 0.25 * tile_noise(64)
h = (h - h.mean()) / (h.std() + 1e-6)
strands = np.sin(np.linspace(0, 2 * np.pi * 40, N, endpoint=False))[None, :]
strands = strands * (0.25 + 0.75 * np.abs(tile_noise(40)))   # break up the streaks
h = h + 0.5 * strands + 0.35 * tile_noise(128)

# normal map from height gradient; fur biased to lie downward (V+)
gy, gx = np.gradient(h)
strength = 1.5
nx, ny, nz = -gx * strength, -gy * strength - 0.25, np.ones_like(h)
L = np.sqrt(nx * nx + ny * ny + nz * nz)
normal = np.stack([nx / L * 0.5 + 0.5, ny / L * 0.5 + 0.5, nz / L * 0.5 + 0.5], -1)
Image.fromarray((normal * 255).astype("uint8")).save(f"{OUT}/fur_normal.png")

# metallic-roughness: R=unused, G=roughness (matte fur, slight variation), B=metal 0
hn = (h - h.min()) / (np.ptp(h) + 1e-6)
rough = np.clip(0.82 + 0.12 * (hn - 0.5), 0, 1)
mr = np.stack([np.zeros_like(h), rough, np.zeros_like(h)], -1)
Image.fromarray((mr * 255).astype("uint8")).save(f"{OUT}/fur_mr.png")

# albedo: near-WHITE grayscale mottle -- a *multiplier* on the material baseColor
# (so per-part colour is preserved; this only adds subtle light/dark fur variation)
g = np.clip(0.92 + 0.16 * (hn - 0.5), 0.7, 1.0)
alb = np.stack([g, g, g], -1)
Image.fromarray((alb * 255).astype("uint8")).save(f"{OUT}/fur_albedo.png")

print(f"wrote {OUT}/fur_normal.png, fur_mr.png, fur_albedo.png  ({N}x{N})")

# --- shell-fur cutout textures: one RGBA per shell layer ---------------------
# A tileable strand-HEIGHT field (clumpy). For shell layer s of NSHELL, a texel
# is opaque only where strand_height >= s/NSHELL, so fewer strands reach the
# outer shells (tapered fur tips). RGB lightens toward the tips.
NSHELL = 4
nz = np.abs(0.6 * tile_noise(64) + 0.4 * tile_noise(128) + 0.25 * tile_noise(256))
nz = nz / nz.max()
strand_h = np.where(nz > 0.28, nz, 0.0)            # strands where the field is high
base_col = np.array([0.20, 0.13, 0.075])
tip_col = np.array([0.34, 0.26, 0.16])
for s in range(1, NSHELL + 1):
    level = s / NSHELL
    alpha = (strand_h >= level).astype("float32")
    rgb = base_col[None, None, :] * (1 - level) + tip_col[None, None, :] * level
    rgba = np.concatenate([np.broadcast_to(rgb, (N, N, 3)),
                           alpha[:, :, None]], -1)
    Image.fromarray((rgba * 255).astype("uint8")).save(f"{OUT}/fur_shell_{s}.png")
print(f"wrote {OUT}/fur_shell_1..{NSHELL}.png  (shell-fur cutouts)")
