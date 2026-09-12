# competitions/ — Web3D 2026 draft assets

<!-- README.md v1.0 2026-08-31 -->

Draft (SILENT) competition videos + snapshots for the two Web3D 2026 entries
described in `ENTRIES.md`. Everything here was produced headlessly (puppeteer +
SwiftShader against `tools_x3d/serve_gzip.py` on :8099) with a deterministic
virtual-clock capture, so the footage is exactly 24 fps regardless of render
speed and every re-render is frame-for-frame reproducible.

## What exists (drafts, machine-made)

| file | what | duration | size |
|---|---|---|---|
| `draft_hanim_120s.mp4` | HAnim entry draft: turntable → Walk/Run/Jump → search+select clavicle → tooth → ethmoid (frame-camera moves) → "Why 256, not 206?" panel → guided-tour steps → closing title card ("authored through the Technē proxy — 48 calls, audited") | ~102 s | see below |
| `draft_catwalk_15s.mp4` | one clean walk cycle (6 × 2.5 s cycles), full body | 15 s | see below |
| `snapshot_full_skeleton.png` | full skeleton in the studio, neutral pose, 1920×1080 | — | — |
| `snapshot_bone_pick_clavicle.png` | bone-picked close-up: L. Clavicle selected (gold) + detail panel | — | — |
| `draft_aitools_storyboard.md` | shot list + ready-to-run ffmpeg commands for the 60–90 s Technē cut (beats A/B/D from `demo/receipts/`) | — | — |
| `footage/` | raw 1080p frame sequences (JPEG, per-shot dirs) + `manifest.json` + the segment mp4s in `footage/_segments/` | — | — |
| `capture_draft.js` | the capture tool (virtual-clock frame capture, v1.1) | — | — |
| `assemble_drafts.sh` | the assembly tool (segments → drafts, v1.0) | — | — |

Exact measured durations/sizes are printed by `assemble_drafts.sh` (VERIFY
lines) and recorded at the bottom of this file.

## What remains HUMAN (do not skip)

1. **The 2026 CFP brief** — pull the exact competition brief from
   https://easychair.org/cfp/web3d26 (EasyChair, competitions track) BEFORE any
   final edit: required video length/format, snapshot specs, word limits,
   judging criteria. Everything here assumes the generic track shape.
2. **Music** — none chosen, drafts are silent by design.
3. **VO / captions** — the storyboard's beat column doubles as the VO script.
4. **Final cut** — trim to the brief's length; the draft is deliberately loose.
   The Technē cut (`draft_aitools_storyboard.md`) has not been rendered at all —
   its commands are ready but the human chooses slates vs live terminal capture.
5. **Filing** — both entries submitted on EasyChair by **Sep 24** (hard deadline
   Sep 30). Steps in `ENTRIES.md`.

## How to re-render

```bash
cd ~/x3d_mcp
.venv/bin/python tools_x3d/serve_gzip.py &          # if :8099 is not already up
node competitions/capture_draft.js http://localhost:8099/anatomy_explorer.html \
     competitions/footage 24 1                       # ~10 min, ~2200 frames
bash competitions/assemble_drafts.sh                 # segments + drafts + VERIFY
```

Smoke run first if the page changed: append `24 0.15` → 0.15× durations.
Capture order ≠ edit order on purpose: ModeSwitch 'stand' freezes the current
pose rather than re-neutralizing, so neutral-pose shots are captured before any
gait runs (see capture_draft.js v1.1 banner).

## Measured verification (2026-08-31, this render)

| check | result |
|---|---|
| `draft_hanim_120s.mp4` | 102.000 s, 30,458,057 B, h264 1920x1080 @ 24 fps, 2448 frames |
| `draft_catwalk_15s.mp4` | 15.000 s, 4,391,063 B, h264 1920x1080 @ 24 fps, 360 frames |
| mid-frame extracts | both NON-BLANK (luma mean 33.8 / 34.4, max 254/255); hanim mid = jump apex, catwalk mid = mid-stride |
| end card (t=99 s) | title card present, "authored through the Technē proxy — 48 calls, audited" legible (luma mean 13.9, NON-BLANK) |
| capture | 2304 frames over 9 shots + 2 PNG stills, 256/256 bones hooked, zero page errors (`footage_capture.log`) |
| shots eyeballed | turntable rear view, walk mid-stride (Walk lit), jump crouch (Jump lit), search dropdown ("collarbon" → L./R. Clavicle), clavicle gold + detail panel, recon panel, tour step 2 (cervical isolate) |

Known draft-quality notes for the human edit: the in-scene studio furniture
(3D title text, poster, in-scene Walk/Run/Jump buttons) is visible from behind
during the turntable — either embrace it or restrict the orbit; the tour's
isolate steps show a mostly-empty frame by design (authored behavior).
