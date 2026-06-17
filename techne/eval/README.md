# Technē evaluation harness

The scoreboard behind `GOALS.md`: does fronting `x3d_mcp` with Technē actually make
an LLM's X3D output *better* — more render-correct, more coherent, cheaper to get
right? "Better" has to be a number or it is just a claim, so this runs a fixed set
of authoring tasks **with and without Technē** and tabulates the difference.

Two modes, same task set (`tasks.py`):

| mode | driver | cost | answers |
|------|--------|------|---------|
| **scripted** (`run_scripted.py`) | deterministic tool-call sequences | free, CI-able | does Technē catch the documented mistakes, and what does it cost? |
| **live** (`run_live.py`) | a real model in an agentic tool-use loop | needs an API key | does it help a model in a *natural* authoring session? |

The live table also counts **`remind`** — standing-semantics reminders surfaced
(`semantics.py`, the coherence layer). To isolate their effect, run the `techne`
stack twice with `TECHNE_SEMANTICS=1` vs `=0` and compare drift / tokens.

## Run

```bash
# scripted — no key, deterministic, the keyless path
PYTHONPATH=techne .venv/bin/python techne/eval/run_scripted.py --json out.json
PYTHONPATH=techne .venv/bin/python techne/eval/run_scripted.py --render   # also score a render (needs Playwright)

# live — a model drives both stacks
.venv/bin/pip install anthropic
ANTHROPIC_API_KEY=... PYTHONPATH=techne .venv/bin/python techne/eval/run_live.py
```

The two **stacks** (`harness.py`) expose the identical tool surface: `raw` launches
`src/server.py` directly; `techne` launches the same server with the Technē proxy
in front. Each task runs in its own fresh server process, so the scene and Technē's
state are fully isolated between tasks.

## What the scripted run shows (current task set)

```
task                  stack    calls   caught   leaked   loud    render
control-clean         raw      4       0/0      0/0      0/0     -
control-clean         techne   4       0/0      0/0      0/0     -
interpolator-parity   raw      2       0/1      1/1      0/1     -
interpolator-parity   techne   3       1/1      0/1      0/1     -
textured-material     raw      4       0/1      1/1      0/1     -
textured-material     techne   5       1/1      0/1      0/1     -
use-before-def        raw      3       0/1      0/1      1/1     -
use-before-def        techne   6       1/1      0/1      0/1     -
```

- **`caught`** — the mistake was blocked (with a prescriptive correction the agent
  applied) or silently repaired before it reached the scene.
- **`leaked`** — it passed *silently* into the scene with no error: the dangerous
  case (a dropped texture, a broken animation). Raw leaks 2/3; Technē leaks 0/3.
- **`loud`** — the server rejected it with an error but *no* actionable fix. Raw is
  loud on 1/3 (`use-before-def`); Technē turns that bare error into a named
  correction *and* auto-recovers.
- **`control-clean`** is identical on both stacks — Technē adds no blocks and no
  extra round-trips on already-correct input. No false positives.
- Cost: **+5 round-trips over 4 tasks**, every block's text named the fix (3/3).

## Honest caveats (these are load-bearing)

- **The render column is liveness, not correctness.** It reuses Technē's own blank
  detector (`gate.inspect_render`, stddev ≥ 3.0 = non-blank). A non-blank scene can
  still be mis-scaled or wrong-coloured. It is off by default here because the
  current tasks build node fragments, not full framed scenes; the **live** mode,
  where the model builds complete scenes, is where the render column earns its keep.
- **`use-before-def` is a *loud* failure on this server, not a silent one** — the
  harness says so (the `loud` column). Technē's value there is an *actionable* error
  plus auto-recovery, an efficiency/UX win, not a silent-failure catch. The genuinely
  silent modes are `textured-material` and `interpolator-parity`.
- **Small N.** Four tasks, three documented mistakes. This is a measurement *spine*,
  not a benchmark suite — the point is that the columns exist and move. Grow the task
  set as the rule catalogue (`rules.py`) grows; each new rule should arrive with a
  task that demonstrates it.

## Extending

Add a `ScriptedTask` to `tasks.py` (a `Step` with `mistake=...`, a `block_token` the
correction must name, and a `fix`/`fix_steps` the agent applies on a block) or a
`LivePrompt` for the live mode. The exit code is non-zero if Technē ever leaks a
silent mistake or breaks a clean task — wire `run_scripted.py` into CI to keep the
catalogue honest.
