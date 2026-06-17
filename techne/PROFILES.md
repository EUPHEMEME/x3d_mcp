# Technē profiles — correctness is universal, policy is opt-in

The design rule that keeps Technē useful to *everyone*, not just provenance-minded
heritage projects: **separate correctness from policy**, the way mature linters do.
ESLint ships a `recommended` config of "rules everyone should use to avoid errors"
(objective, default-on) and keeps "always opinionated" rules in *separate opt-in*
configs; typescript-eslint frames them as "two complementary layers." Technē adopts
the same split.

## The three groups

| group | what | default | rationale |
|-------|------|---------|-----------|
| **core** | the silent-failure craft catalog, the blank-render gate, the edit-tool post-pass | **always on** | objective X3D correctness — nobody is frustrated by "your texture would silently vanish" |
| **coherence** | the standing-semantics reminders | **on** (soft) | advisory nudges; never block; `TECHNE_SEMANTICS=0` or a profile without it turns them off |
| **provenance** | the documented/interpretive honesty gate | **off** | a *policy*, not a fact about X3D — a mandatory provenance wall would frustrate most artistic workflows |

`core` is never opt-out: it is the "front the x3d-mcp with Technē and your output
just renders correctly, zero config" experience that makes the tool universally
worth adopting. Everything opinionated sits on top, off by default.

## Configuration

```
TECHNE_PROFILE=core,coherence            # the default (provenance off)
TECHNE_PROFILE=core,coherence,provenance # opt into the honesty gate
TECHNE_PROVENANCE_LEVEL=1                 # 1 disclosure (default) / 2 sourcing / 3 content
TECHNE_ASSET_LEDGER=drawings/archive.json # needed for level >= 2
TECHNE_STRICT=1                           # policy violations BLOCK (default: warn)
```

The legacy `TECHNE_SEMANTICS=0` still disables coherence. `Config.from_env()` is the
single source of truth (`config.py`); the proxy and the server read it.

## Provenance is graduated, and its floor is universal

Provenance is not a switch — it mirrors C2PA / Content Credentials, where provenance
ranges from a minimal "this is AI-generated" disclosure up to full source history.
So the cheapest rung is genuinely useful to *anyone* shipping into a shared library
or training set:

- **L1 — disclosure** *(ledger-free; the universal slop-resistance rung)*: keep any
  provenance tags well-formed and require `generated` assets to disclose how
  (`generationMethod`). No ledger, near-zero friction.
- **L2 — sourcing**: `documented` claims must resolve to a cited, public-domain asset
  in the ledger. For curated / training repositories.
- **L3 — content**: the domain `must_not_invent` rules (taxon/depth/cal-BC) — needs a
  structured claim schema; **not built** (deliberately deferred).

## Graduated enforcement — warn, don't wall

Even when a policy is *on*, it defaults to the **softest useful tier**: a
`Technē provenance (Ln, note): …` advisory rides back on the relevant result and
never blocks. Only `TECHNE_STRICT=1` turns policy violations into hard stops. Nudge
unless asked — so opting in is low-regret.

## Verified

`core` correctness fires under every profile (a missing containerField is blocked
even with `TECHNE_PROFILE=core`). The provenance gate is silent by default and fires
only when the profile opts in — proven live: with `core,coherence,provenance`, an
undisclosed `generated` asset trips an L1 soft note through the real transport; with
the default profile it stays silent (smoke 8/8). See `test_config.py`,
`test_provenance.py`, `test_edit_postpass.py`.
