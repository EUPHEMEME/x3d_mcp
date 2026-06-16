"""Technē — a deterministic craft layer for MCP servers.

It makes a model's tool-call arguments *conform* to a format's unwritten
conventions (the craft the schema doesn't encode), and holds a render-and-sign-off
gate before expensive irreversible work — so the craft holds mechanically,
regardless of whether the model comprehended it. The schema is the rules; Technē
is the craft.

τέχνη — craft-knowledge-with-an-account, from PIE *teks-, "to weave/construct"
(cognate with text/texture) — the weaving of disparate elements into an ordered
whole. A scene graph, literally.
"""
from .craft import (CraftResult, check_container_field, check_placement,
                    legal_slots, check_envlight_global, check_interpolator,
                    check_use_after_def, advise_texture_url, merge, MISSING)
from . import rules

__all__ = ["CraftResult", "check_container_field", "check_placement",
           "legal_slots", "check_envlight_global", "check_interpolator",
           "check_use_after_def", "advise_texture_url", "merge", "MISSING",
           "rules"]
