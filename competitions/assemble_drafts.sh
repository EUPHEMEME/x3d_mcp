#!/bin/bash
# competitions/assemble_drafts.sh v1.1 2026-08-31 — assemble the DRAFT (silent)
# (v1.1: homebrew ffmpeg 8.1.2 has NO drawtext — the title card is rendered by
#  ImageMagick and looped by ffmpeg instead)
# Web3D 2026 competition videos from competitions/footage/ frame sequences.
# Produces: draft_hanim_120s.mp4 (turntable -> gaits -> highlights -> recon ->
# tour -> closing title card) and draft_catwalk_15s.mp4 (walk cycle alone),
# plus the two PNG snapshots copied up from footage/.
# Re-render: node competitions/capture_draft.js <url> competitions/footage 24 1
#            bash competitions/assemble_drafts.sh
set -euo pipefail
cd "$(dirname "$0")"
FPS=24
FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
SEG=footage/_segments
mkdir -p "$SEG"

echo "== assemble_drafts.sh v1.1 =="

# ---- 1. encode each shot's frame sequence to a uniform segment ----
for d in footage/0*_*/; do
  s=$(basename "$d")
  ffmpeg -y -v error -framerate $FPS -i "$d/f_%05d.jpg" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r $FPS \
    -video_track_timescale 90000 "$SEG/$s.mp4"
  echo "segment $s.mp4"
done

# ---- 2. closing title card (6 s) — ImageMagick slate, ffmpeg loop ----
magick -size 1920x1080 xc:'#0b0d12' \
  -font "$FONT" -fill '#e8eaf0' -pointsize 72 -gravity center \
  -annotate +0-60 'LOA5 Anatomy Explorer' \
  -fill '#ffb821' -pointsize 38 \
  -annotate +0+60 'authored through the Technē proxy — 48 calls, audited' \
  "$SEG/title_card.png"
ffmpeg -y -v error -loop 1 -i "$SEG/title_card.png" -t 6 \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r $FPS \
  -video_track_timescale 90000 "$SEG/10_title.mp4"
echo "segment 10_title.mp4"

# ---- 3. concat in EDIT order (numeric ids) ----
: > "$SEG/concat.txt"
for f in "$SEG"/0*_*.mp4 "$SEG/10_title.mp4"; do
  echo "file '$(basename "$f")'" >> "$SEG/concat.txt"
done
ffmpeg -y -v error -f concat -safe 0 -i "$SEG/concat.txt" -c copy draft_hanim_120s.mp4

# ---- 4. catwalk: the walk cycle alone ----
cp "$SEG/02_walk.mp4" draft_catwalk_15s.mp4

# ---- 5. snapshots ----
cp footage/still_full_skeleton.png snapshot_full_skeleton.png
cp footage/still_bone_pick_clavicle.png snapshot_bone_pick_clavicle.png

# ---- 6. verify: duration + non-blank mid-frame ----
for v in draft_hanim_120s.mp4 draft_catwalk_15s.mp4; do
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v")
  sz=$(stat -f %z "$v")
  mid=$(echo "$dur/2" | bc -l)
  ffmpeg -y -v error -ss "$mid" -i "$v" -frames:v 1 "$SEG/mid_$v.png"
  echo "VERIFY $v duration=${dur}s size=${sz}B midframe=$SEG/mid_$v.png"
done
echo "done — inspect the midframes, then human steps: music + final cut per the 2026 CFP brief."
