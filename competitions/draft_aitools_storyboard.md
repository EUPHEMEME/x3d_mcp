# AI Tools Competition — "Technē" 60–90 s cut — DRAFT storyboard v1.0 (2026-08-31)

Silent draft; music, VO and the final trim are human steps, cut AFTER reading the
2026 CFP brief (see `ENTRIES.md`). Every asset referenced below already exists on
disk under `demo/receipts/`; every command below is ready to run from the repo
root and needs only ffmpeg (installed; asciinema/agg are NOT installed — the
slate path below is the offline substitute for terminal capture).

Target: **~75 s**, 1920x1080, 24 fps, beats A → B → D.

| # | t (s) | beat | on screen | source asset |
|---|-------|------|-----------|--------------|
| 1 | 0–8   | title | "Technē — a deterministic craft layer for MCP servers" + one-line sub: "in-transit repair · silent-failure catalogue · verify-by-render" | drawtext slate |
| 2 | 8–16  | A | The good scene: HAnim skeleton renders, gate transcript says PASS | `demo/receipts/beat_a/original.png` (slow zoompan) + `original_gate_transcript.txt` |
| 3 | 16–28 | A | The broken scene: ONE containerField wrong → skeleton silently gone. Gate 1 names the exact fix: `HAnimHumanoid.children does not accept a HAnimJoint … Use containerField='joints'` | `demo/receipts/beat_a/broken.png` + `broken_gate_transcript.txt` (slate, error line highlighted) |
| 4 | 28–42 | B | The proxy in transit: 5 calls through the stdio proxy — 1 blocked with a prescriptive message, 1 repaired-and-forwarded, counters printed as JSON | `demo/receipts/beat_b/beat_b_transcript.txt` (scrolling slate) + `counters.json` |
| 5 | 42–62 | D | The scoreboard: 5 documented mistakes replayed raw vs Technē. Raw: 2 pass SILENTLY into the scene, 3 rejected loudly with no fix. Technē: 5/5 caught, 5/5 block texts name the fix | `demo/receipts/beat_d/scoreboard.txt` (table slate; summary block highlighted) |
| 6 | 62–75 | close | Proof-of-work card: "LOA5 Anatomy Explorer — authored through the Technē proxy: 48 calls, 0 blocked, 0 repaired" + "497 passing tests · upstream PRs #9 #10 #11" + snapshot | `competitions/snapshot_full_skeleton.png`, `build_anatomy/TRANSCRIPT.md` totals |

## Ready-to-run render commands

All output lands in `competitions/techne_cut/`. NOTE: the installed homebrew
ffmpeg 8.1.2 has **no drawtext filter** (built without freetype) — all text
slates are rendered by ImageMagick (`magick`, installed) and looped/scrolled by
ffmpeg. Same recipe `assemble_drafts.sh` v1.1 uses for the HAnim title card.

```bash
cd ~/x3d_mcp && mkdir -p competitions/techne_cut && cd competitions/techne_cut
FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
MONO="/System/Library/Fonts/Supplemental/Courier New.ttf"
ENC="-c:v libx264 -crf 18 -pix_fmt yuv420p -r 24 -video_track_timescale 90000"

# shot 1 — title slate (8 s)
magick -size 1920x1080 xc:'#0b0d12' -font "$FONT" -gravity center \
  -fill '#e8eaf0' -pointsize 58 -annotate +0-60 'Technē — a deterministic craft layer for MCP servers' \
  -fill '#ffb821' -pointsize 34 -annotate +0+40 'in-transit repair · silent-failure catalogue · verify-by-render' \
  s1.png
ffmpeg -y -loop 1 -i s1.png -t 8 $ENC seg1.mp4

# shots 2+3 — beat A: slow zoompan on the two gate renders (8 s each)
for pair in "seg2 ../../demo/receipts/beat_a/original.png" \
            "seg3 ../../demo/receipts/beat_a/broken.png"; do
  set -- $pair
  ffmpeg -y -loop 1 -i "$2" -t 8 \
    -vf "scale=2400:-2,zoompan=z='min(zoom+0.0007,1.15)':d=192:s=1920x1080:fps=24" \
    $ENC "$1.mp4"
done

# shot 3b — the gate verdict as a monospace slate (6 s): just the error + fix
grep -A2 'containerfield-type-mismatch' ../../demo/receipts/beat_a/broken_gate_transcript.txt > s3.txt
magick -size 1680x800 -background '#10131a' -fill '#ff6a5e' -font "$MONO" \
  -pointsize 30 caption:@s3.txt -gravity center -extent 1920x1080 s3.png
ffmpeg -y -loop 1 -i s3.png -t 6 $ENC seg3b.mp4

# shot 4 — beat B transcript (68 lines), rendered tall + scrolled over 14 s
magick -size 1720x -background '#10131a' -fill '#d7e0ea' -font "$MONO" \
  -pointsize 22 caption:@../../demo/receipts/beat_b/beat_b_transcript.txt \
  -bordercolor '#10131a' -border 100x100 s4_tall.png
ffmpeg -y -loop 1 -i s4_tall.png -t 14 \
  -vf "crop=1920:1080:0:'min(ih-1080,t*(ih-1080)/14)'" $ENC seg4.mp4

# shot 5 — beat D scoreboard held 20 s (it is the argument; let it sit)
magick -size 1740x960 -background '#10131a' -fill '#d7e0ea' -font "$MONO" \
  -pointsize 20 caption:@../../demo/receipts/beat_d/scoreboard.txt \
  -gravity center -extent 1920x1080 s5.png
ffmpeg -y -loop 1 -i s5.png -t 20 $ENC seg5.mp4

# shot 6 — closing proof-of-work card over the anatomy snapshot (13 s)
magick ../snapshot_full_skeleton.png -resize 1920x1080\! \
  \( -size 1920x280 xc:'#0b0d12' -alpha set -channel A -evaluate set 82% \) \
  -geometry +0+800 -composite \
  -font "$FONT" -fill '#e8eaf0' -pointsize 44 -gravity north \
  -annotate +0+860 'LOA5 Anatomy Explorer — authored through the Technē proxy' \
  -fill '#ffb821' -pointsize 30 \
  -annotate +0+940 '48 calls · 0 blocked · 0 repaired  |  497 passing tests  |  PRs #9 #10 #11' \
  s6.png
ffmpeg -y -loop 1 -i s6.png -t 13 $ENC seg6.mp4

# assemble
for f in seg1 seg2 seg3 seg3b seg4 seg5 seg6; do echo "file '$f.mp4'"; done > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy ../draft_techne_75s.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 ../draft_techne_75s.mp4
```

## Live terminal capture (optional upgrade, human step)

The judges may respond better to a LIVE run than to slates. Two paths:

1. `brew install asciinema agg` then
   `asciinema rec -c 'PYTHONPATH=techne .venv/bin/python techne/eval/run_scripted.py' beat_d.cast`
   and `agg --font-size 20 beat_d.cast beat_d.gif`, then
   `ffmpeg -i beat_d.gif -vf "scale=1920:-2,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:0x10131a" -pix_fmt yuv420p seg5_live.mp4`.
2. Screen-record Terminal.app by hand (human step — headless rule stays intact).

## Notes for the human edit

- Beat C (differential probe frames, `demo/receipts/beat_c/`) is deliberately
  out of this cut to hold 75 s; it is the strongest *research* claim (the
  zero-geometry defect found in the Consortium's own assets) — consider swapping
  it in for shot 4 if the CFP rewards novelty over completeness.
- Word the 497-test line exactly as measured 2026-08-31 (`ENTRIES.md`).
- Music: none chosen. VO script: read the beat column aloud; it is the script.
