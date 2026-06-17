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

Config sources, in order: TECHNE_PROFILE (comma list, e.g. "core,coherence,
provenance"); else the legacy TECHNE_SEMANTICS flag; plus the provenance knobs
(level, ledger, strict). Provenance is graduated (see provenance.py):
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

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Config":
        env = os.environ if env is None else env
        prof = env.get("TECHNE_PROFILE", "")
        groups = {g.strip().lower() for g in prof.split(",") if g.strip()}
        if groups:                                   # explicit profile wins
            coherence = "coherence" in groups
            provenance = "provenance" in groups
        else:                                        # legacy / default
            coherence = env.get("TECHNE_SEMANTICS", "1") != "0"
            provenance = False
        try:
            level = int(env.get("TECHNE_PROVENANCE_LEVEL", "1") or "1")
        except ValueError:
            level = 1
        return cls(
            coherence=coherence,
            provenance=provenance,
            provenance_level=max(1, min(3, level)),
            ledger_path=env.get("TECHNE_ASSET_LEDGER", "") or "",
            strict=_flag(env.get("TECHNE_STRICT")),
        )
