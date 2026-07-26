"""Technē profiles — keep the tool universally useful by separating CORRECTNESS
from POLICY (the ESLint `recommended`-vs-opinionated split).

  * CORE (always on, not configurable here): the silent-failure craft catalog,
    the blank-render gate, the edit-tool post-pass. Objective X3D correctness --
    nobody is frustrated by "your texture would silently vanish", so it is never
    opt-out.
  * COHERENCE (default on, soft): the standing-semantics reminders. Advisory.
  * PROVENANCE (opt-in, off by default): the honesty discipline. A *policy*, not a
    fact about X3D, so it ships off -- a mandatory provenance gate would be an
    arbitrary wall most artistic workflows neither want nor need.
  * DIFFERENTIAL (opt-in, off by default): verify-by-differential-render
    (differential.py) inside the occupation gate. Off by default not because it is
    policy -- it is deterministic and correctness-shaped -- but because of COST:
    one render per candidate node, N+1 total, so it belongs before a commitment,
    not on every call.

Config sources, in order: TECHNE_PROFILE (comma list, e.g. "core,coherence,
provenance"); else the legacy TECHNE_SEMANTICS flag; plus the provenance knobs
(level, ledger, strict). The differential check is enabled by the "differential"
profile group OR the TECHNE_DIFFERENTIAL flag (both are pure opt-ins -- there is
no on-by-default state for an explicit profile to override, so either switch
turning it on is the least surprising rule), with TECHNE_DIFFERENTIAL_MAX_NODES
bounding its render budget. Provenance is graduated (see provenance.py):
  L1 disclosure (ledger-free; the universal slop-resistance rung),
  L2 sourcing (needs a ledger), L3 content rules (domain schema; not built).
Policy violations WARN by default; TECHNE_STRICT makes them block.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _flag(v: str | None) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    coherence: bool = True             # standing-semantics reminders (soft)
    provenance: bool = False           # provenance gate active?
    provenance_level: int = 1          # 1 disclosure / 2 sourcing / 3 content
    ledger_path: str = ""              # asset ledger (archive.json shape), L2+
    strict: bool = False               # policy violations block (else warn)
    instrumentation: bool = False      # Point-1 verb-order trace logging
    trace_dir: str = ""                # trace output dir (default: ./techne_traces)
    differential: bool = False         # verify-by-differential-render (N+1 renders)
    differential_max_nodes: int = 0    # render budget; 0 = differential.MAX_NODES_DEFAULT
    # Whether a differential finding BLOCKS or merely advises. Advisory by default:
    # zero pixel change is a real signal but not proof of a defect (occlusion,
    # out-of-frustum, coincident DEF/USE), so refusing on it would reject correct work.
    differential_blocks: bool = False

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Config":
        env = os.environ if env is None else env
        prof = env.get("TECHNE_PROFILE", "")
        groups = {g.strip().lower() for g in prof.split(",") if g.strip()}
        if groups:                                   # explicit profile wins
            coherence = "coherence" in groups
            provenance = "provenance" in groups
            instrumentation = "instrumentation" in groups
        else:                                        # legacy / default
            coherence = env.get("TECHNE_SEMANTICS", "1") != "0"
            provenance = False
            instrumentation = _flag(env.get("TECHNE_TRACE"))
        try:
            level = int(env.get("TECHNE_PROVENANCE_LEVEL", "1") or "1")
        except ValueError:
            level = 1
        # DIFFERENTIAL: either opt-in switch works, in both the explicit-profile
        # and legacy branches (see the module docstring for why OR, not
        # profile-wins). The budget knob defaults to 0 = "use the module default"
        # so config.py does not duplicate differential.MAX_NODES_DEFAULT.
        # "block" both ENABLES the check and makes it blocking, so an operator who has
        # judged the false-positive surface on their own scenes can opt in with one setting.
        _diff_raw = str(env.get("TECHNE_DIFFERENTIAL", "") or "").strip().lower()
        differential = "differential" in groups \
            or _flag(env.get("TECHNE_DIFFERENTIAL")) or _diff_raw == "block"
        try:
            diff_max = int(env.get("TECHNE_DIFFERENTIAL_MAX_NODES", "0") or "0")
        except ValueError:
            diff_max = 0
        return cls(
            coherence=coherence,
            provenance=provenance,
            provenance_level=max(1, min(3, level)),
            ledger_path=env.get("TECHNE_ASSET_LEDGER", "") or "",
            strict=_flag(env.get("TECHNE_STRICT")),
            instrumentation=instrumentation,
            trace_dir=env.get("TECHNE_TRACE_DIR", "") or "",
            differential=differential,
            differential_blocks=(_diff_raw == "block"),
            differential_max_nodes=max(0, diff_max),
        )
