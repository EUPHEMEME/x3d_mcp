#!/usr/bin/env bash
# Beauty / compositing pass of the mflux -> X3D moose pipeline.
# Restyles a rendered X3D frame into a photoreal still. Two modes:
#   1) schnell img2img      -- fast, loosely pose-matched
#   2) FLUX.1-Depth-dev     -- depth-conditioned, POSE-LOCKED photoreal (best)
#
# Notes:
#  * HF_TOKEN env var is stale on this box -> use `env -u HF_TOKEN` so the valid
#    token FILE (~/.cache/huggingface/token) is used (it has gated FLUX access).
#  * FLUX.1-Depth-dev (34 GB) MUST be run with `--quantize 8`; at full precision
#    it decodes to noise on this MLX build.
set -euo pipefail
ENV=ALLEUPHEME/mflux-env
PY="$ENV/bin/python"
SRC="${1:?usage: generate_beauty.sh <render.png> <out.png> [prompt] [mode=depth|img2img]}"
OUT="${2:?out png}"
PROMPT="${3:-photorealistic wildlife photograph of a large bull moose, massive palmate antlers, shoulder hump, shaggy dark brown fur, golden-hour light, National Geographic, highly detailed}"
MODE="${4:-depth}"

if [ "$MODE" = "depth" ]; then
  env -u HF_TOKEN "$PY" "$ENV/bin/mflux-generate-depth" \
    --quantize 8 --steps 20 --guidance 10 --seed 5 \
    --image-path "$SRC" --height 720 --width 1280 \
    --prompt "$PROMPT" --output "$OUT"
else
  env -u HF_TOKEN "$PY" "$ENV/bin/mflux-generate" \
    --model schnell --steps 6 --seed 42 \
    --image-path "$SRC" --image-strength 0.30 --height 720 --width 1280 \
    --prompt "$PROMPT" --output "$OUT"
fi
echo "wrote $OUT"
