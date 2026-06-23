"""The Technē proxy core — the transport-agnostic decision layer (TECHNE_SPEC §4).

A model connects to Technē; Technē fronts the real x3d-mcp. Per `tools/call`:

  1. SAP repair  — coerce/normalize the model's sloppy args into conforming shape.
  2. Route       — if the tool has a craft adapter, apply it; else pass through
                   (Technē is opt-in per tool: absence of a rule == no known
                   silent-failure here).
  3. Decide      — a HARD violation BLOCKS the forward and returns the prescriptive
                   correction (the error message IS the fix); a repair rewrites the
                   args and forwards them; SOFT notes ride along as warnings.

`decide()` needs node *types*, but the real add_child references nodes by *id* — so
the proxy keeps a small SceneState. Crucially, state mutations are *deferred*:
decide() only reads state and records what it *would* commit on the Decision's
`pending` slot; observe_result() commits id→type / DEF / field updates ONLY after
the upstream call is confirmed successful. That fixes the overlap race (no shared
mutable pending) and the premature-DEF problem (a failed def_node must not satisfy
a later USE). The larger order-of-operations automaton (Point 1) is deliberately
NOT built (TECHNE_SPEC §6).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field as dc_field
from typing import Any

from . import craft, repair, semantics
from .config import Config
from .craft import MISSING

_TEXTURE_NODES = craft.rules.TEXTURE_NODES


# --- scene state (the minimal cross-call memory) ---------------------------

@dataclass
class SceneState:
    id_to_type: dict[str, str] = dc_field(default_factory=dict)
    node_fields: dict[str, dict] = dc_field(default_factory=dict)
    defined_defs: set[str] = dc_field(default_factory=set)
    def_name_to_type: dict[str, str] = dc_field(default_factory=dict)
    id_to_def: dict[str, str] = dc_field(default_factory=dict)        # node id -> its DEF name
    surfaced_reminders: dict[str, int] = dc_field(default_factory=dict)  # coherence key -> last call index

    def reset(self):
        for d in (self.id_to_type, self.node_fields, self.def_name_to_type,
                  self.id_to_def, self.surfaced_reminders):
            d.clear()
        self.defined_defs.clear()


@dataclass
class Decision:
    action: str                       # "forward" | "block"
    tool: str
    args: dict                        # repaired args (forward) / original (block)
    corrections: list[str] = dc_field(default_factory=list)   # HARD (why blocked)
    notes: list[str] = dc_field(default_factory=list)         # SOFT / repairs done
    reminders: list[str] = dc_field(default_factory=list)     # SOFT / coherence standing semantics
    applied: list[str] = dc_field(default_factory=list)
    rewrote: bool = False             # did Technē actually change the forwarded args?
    pending: dict | None = None       # state to commit iff upstream succeeds

    @property
    def blocked(self) -> bool:
        return self.action == "block"


# --- response parsing -------------------------------------------------------

_CREATED_RE = re.compile(r"\bID:\s*([A-Za-z0-9_\-:]+)")
_ASSIGNED_RE = re.compile(r"Assigned DEF '([^']+)' to (\S+)")


def _is_error(text: str) -> bool:
    t = (text or "").strip().lower()
    return (not t) or t.startswith(("error", "failed", "traceback")) \
        or "error:" in t[:40] or "no node with" in t or "not found" in t


def _args_changed(emitted: dict, forwarded: dict) -> bool:
    """Did Technē actually rewrite a value the model cares about? Ignores additive
    normalization noise (an empty fields={} or container_field='' the adapters
    insert) so an advisory-only forward is not mislabeled as a repair."""
    def norm(a: dict) -> dict:
        a = {k: v for k, v in (a or {}).items()}
        if a.get("fields") == {}:
            a.pop("fields", None)
        for cf in ("container_field", "containerField"):
            if a.get(cf) in ("", None):
                a.pop(cf, None)
        return a
    return norm(emitted) != norm(forwarded)


# --- the proxy --------------------------------------------------------------

class TechneProxy:
    """Holds scene state and applies the craft adapters per tool call."""

    # re-arm a reminder this many calls after it last surfaced, so it nudges again
    # at a late-session drift point instead of firing once early and going silent.
    REMINDER_COOLDOWN = 30

    def __init__(self, semantics_on: bool = True, config: "Config | None" = None):
        self.state = SceneState()
        self.config = config or Config.from_env()
        # CORE craft (the adapters) is always on; COHERENCE follows the profile
        # (legacy TECHNE_SEMANTICS still honored) and the explicit arg can force off.
        self.semantics_on = semantics_on and self.config.coherence
        self._call_index = 0
        self._ledger: dict | None = None

    def ledger(self) -> dict:
        """The asset ledger for the provenance gate (lazy, cached). Empty unless a
        TECHNE_ASSET_LEDGER is configured -- L1 disclosure needs none."""
        if self._ledger is None:
            self._ledger = {}
            if self.config.ledger_path:
                try:
                    from . import provenance
                    self._ledger = provenance.load_ledger(self.config.ledger_path)
                except Exception:
                    self._ledger = {}
        return self._ledger

    def _semantics_for(self, tool: str, args: dict) -> list[str]:
        """Standing-semantics reminders for this call: triggered, de-duped, capped.
        Not once-*forever*: a key re-fires REMINDER_COOLDOWN calls after it last
        surfaced (the model drifts late in a session, not just at the top). Records
        the call index only for the keys actually emitted."""
        if not self.semantics_on:
            return []
        out: list[str] = []
        seen = self.state.surfaced_reminders                # key -> last call index
        for key, text in semantics.advise(tool, args, self.state):
            last = seen.get(key)
            if last is not None and self._call_index - last < self.REMINDER_COOLDOWN:
                continue
            out.append(text)
            seen[key] = self._call_index
            if len(out) >= 2:                               # never flood a single result
                break
        return out

    # -- adapters: read state + repaired args -> craft.CraftResult ----------

    def _adapt_create_node(self, args: dict) -> craft.CraftResult:
        node_type = args.get("node_type", "")
        fields = dict(args.get("fields") or {})
        res = craft.CraftResult(repaired=dict(args))
        subs = []
        if node_type == "EnvironmentLight":
            subs.append(craft.check_envlight_global(
                fields.get("global", MISSING), {"fields": fields}))
        if node_type in craft.rules.INTERP_COMPONENTS and \
                "key" in fields and "keyValue" in fields:
            subs.append(craft.check_interpolator(
                node_type, _as_list(fields["key"]), _as_list(fields["keyValue"]),
                None, {"fields": fields}))
        if node_type in _TEXTURE_NODES and fields.get("url"):
            subs.append(craft.advise_texture_url(_first(fields["url"]), {}))
        if node_type in craft.INDEXED_TYPES and "coordIndex" in fields:
            subs.append(craft.check_coordindex(
                node_type, fields["coordIndex"], {"fields": fields}))
        if node_type == "HAnimHumanoid" and "version" not in fields:
            res.notes.append(craft.rules.correction("hanim_version_explicit"))
            res.applied.append("hanim_version_explicit")
        for s in subs:
            if "global" in s.repaired:
                fields["global"] = s.repaired["global"]
            res.corrections += s.corrections
            res.notes += s.notes
            res.applied += s.applied
        res.repaired["fields"] = fields
        return res

    def _adapt_add_child(self, args: dict) -> craft.CraftResult:
        child_type = self.state.id_to_type.get(args.get("child_id", ""))
        parent_type = self.state.id_to_type.get(args.get("parent_id", ""))
        if not child_type or not parent_type:
            r = craft.CraftResult(repaired=dict(args))
            unknown = args.get("child_id") if not child_type else args.get("parent_id")
            r.notes.append(
                "Technē could not check containerField: unknown node type for "
                "%s. (Node created before Technē, or via an unguarded tool.)"
                % unknown)
            return r
        return craft.check_placement(
            parent_type, child_type, args.get("container_field", MISSING) or MISSING,
            args, cf_key="container_field")

    def _adapt_def_node(self, args: dict) -> craft.CraftResult:
        # NOTE: do not mutate defined_defs here — commit on confirmed success.
        return craft.check_duplicate_def(
            args.get("name", ""), self.state.defined_defs, args)

    def _adapt_use_node(self, args: dict) -> craft.CraftResult:
        return craft.check_use_after_def(
            args.get("def_name", ""), self.state.defined_defs, args)

    def _adapt_add_route(self, args: dict) -> craft.CraftResult:
        # the granular add_route references nodes by tracking id; both must already
        # carry a DEF (scene.add_route raises a bare error otherwise).
        return craft.check_route_defs(
            args.get("from_node", ""), args.get("to_node", ""),
            self.state.id_to_def, args)

    def _adapt_set_field(self, args: dict) -> craft.CraftResult:
        node_id = args.get("node_id", "")
        fname = args.get("field_name", "")
        node_type = self.state.id_to_type.get(node_id, "")
        if node_type in craft.rules.INTERP_COMPONENTS:
            merged = dict(self.state.node_fields.get(node_id, {}))
            merged[fname] = args.get("value")
            if "key" in merged and "keyValue" in merged:
                return craft.check_interpolator(
                    node_type, _as_list(merged["key"]),
                    _as_list(merged["keyValue"]), None, args)
        if node_type in craft.INDEXED_TYPES and fname == "coordIndex":
            return craft.check_coordindex(node_type, args.get("value"), args)
        return craft.CraftResult(repaired=dict(args))

    _ADAPTERS: dict[str, str] = {
        "create_node": "_adapt_create_node",
        "add_child": "_adapt_add_child",
        "def_node": "_adapt_def_node",
        "use_node": "_adapt_use_node",
        "set_field": "_adapt_set_field",
        "add_route": "_adapt_add_route",
    }

    # -- the public decision surface ----------------------------------------

    def decide(self, tool: str, args: dict) -> Decision:
        self._call_index += 1
        emitted = args                                 # what the model sent (pre-repair)
        args = repair.sap_repair(args)                 # step 1: deterministic repair
        adapter = self._ADAPTERS.get(tool)
        if adapter is None:                            # opt-in: unknown tool passes
            d = Decision("forward", tool, args, rewrote=_args_changed(emitted, args))
            d.reminders = self._semantics_for(tool, args)   # still nudge (e.g. add_route)
            return d
        res: craft.CraftResult = getattr(self, adapter)(args)
        if res.corrections:                            # HARD violation -> block
            return Decision("block", tool, args, corrections=res.corrections,
                            notes=res.notes, applied=res.applied)
        d = Decision("forward", tool, res.repaired, notes=res.notes,
                     applied=res.applied, rewrote=_args_changed(emitted, res.repaired))
        d.pending = self._pending_for(tool, res.repaired)
        d.reminders = self._semantics_for(tool, res.repaired)   # coherence (soft)
        return d

    @staticmethod
    def _pending_for(tool: str, args: dict) -> dict | None:
        if tool == "create_node":
            return {"kind": "create", "node_type": args.get("node_type", ""),
                    "fields": dict(args.get("fields") or {})}
        if tool == "def_node":
            return {"kind": "def", "name": args.get("name", ""),
                    "node_id": args.get("node_id", "")}
        if tool == "use_node":
            return {"kind": "use", "def_name": args.get("def_name", "")}
        if tool == "set_field":
            return {"kind": "set_field", "node_id": args.get("node_id", ""),
                    "field": args.get("field_name", ""), "value": args.get("value")}
        return None

    def observe_result(self, decision: Decision, result_text: str) -> None:
        """Commit scene state from a forwarded call's response — ONLY on success."""
        p = decision.pending
        if not p or _is_error(result_text):
            return
        st = self.state
        if p["kind"] == "create":
            m = _CREATED_RE.search(result_text)
            if m:
                st.id_to_type[m.group(1)] = p["node_type"]
                st.node_fields[m.group(1)] = dict(p["fields"])
        elif p["kind"] == "def":
            m = _ASSIGNED_RE.search(result_text)
            if m:
                name, nid = m.group(1), m.group(2)
                old = st.id_to_def.get(nid)
                if old and old != name:        # node re-DEF'd: free its old name
                    st.defined_defs.discard(old)
                    st.def_name_to_type.pop(old, None)
                st.defined_defs.add(name)
                st.id_to_def[nid] = name
                if nid in st.id_to_type:
                    st.def_name_to_type[name] = st.id_to_type[nid]
        elif p["kind"] == "use":
            m = _CREATED_RE.search(result_text)
            if m:
                t = st.def_name_to_type.get(p["def_name"])
                if t:
                    st.id_to_type[m.group(1)] = t
        elif p["kind"] == "set_field":
            st.node_fields.setdefault(p["node_id"], {})[p["field"]] = p["value"]

    def correction_message(self, decision: Decision) -> str:
        """The text returned to the model when a call is blocked — the fix itself."""
        head = ("Technē blocked this call (it would pass the schema but render "
                "wrong). Apply the correction and retry:")
        return head + "\n- " + "\n- ".join(decision.corrections)


def _as_list(v: Any) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [x for x in re.split(r"[,\s]+", v.strip()) if x != ""]
    return [v]


def _first(v: Any) -> str:
    if isinstance(v, list):
        return str(v[0]) if v else ""
    return str(v)
