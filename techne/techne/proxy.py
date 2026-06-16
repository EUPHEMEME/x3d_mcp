"""The Technē proxy core — the transport-agnostic decision layer (TECHNE_SPEC §4).

A model connects to Technē; Technē fronts the real x3d-mcp. Per `tools/call`:

  1. SAP repair  — coerce/normalise the model's sloppy args into conforming shape.
  2. Route       — if the tool has a craft adapter, apply it; else pass through
                   (Technē is opt-in per tool: absence of a rule == no known
                   silent-failure here).
  3. Decide      — a HARD violation BLOCKS the forward and returns the prescriptive
                   correction (the error message IS the fix); a repair rewrites the
                   args and forwards them; SOFT notes ride along as warnings.

The transport (server.py) wraps `decide()` / `observe_result()`; this module is
pure and fully testable. `decide()` needs to know node *types*, but the real
add_child references nodes by *id* — so the proxy keeps a small SceneState,
populated by watching create_node results and def_node calls. This is the minimal
cross-call state Point 2 needs; the larger order-of-operations automaton (Point 1)
is deliberately NOT built (TECHNE_SPEC §6).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable

from . import craft, repair
from .craft import MISSING


# --- scene state (the minimal cross-call memory) ---------------------------

@dataclass
class SceneState:
    id_to_type: dict[str, str] = dc_field(default_factory=dict)
    node_fields: dict[str, dict] = dc_field(default_factory=dict)
    defined_defs: set[str] = dc_field(default_factory=set)

    def reset(self):
        self.id_to_type.clear()
        self.node_fields.clear()
        self.defined_defs.clear()


@dataclass
class Decision:
    action: str                       # "forward" | "block"
    tool: str
    args: dict                        # repaired args (forward) / original (block)
    corrections: list[str] = dc_field(default_factory=list)   # HARD (why blocked)
    notes: list[str] = dc_field(default_factory=list)         # SOFT / repairs done
    applied: list[str] = dc_field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.action == "block"


# --- the proxy --------------------------------------------------------------

_CREATED_RE = re.compile(r"\bID:\s*([A-Za-z0-9_\-:]+)")


class TechneProxy:
    """Holds scene state and applies the craft adapters per tool call."""

    def __init__(self):
        self.state = SceneState()
        self._last_create: dict | None = None   # remembers a pending create_node

    # -- adapters: tool name -> function(args) -> craft.CraftResult ----------

    def _adapt_create_node(self, args: dict) -> craft.CraftResult:
        node_type = args.get("node_type", "")
        fields = dict(args.get("fields") or {})
        res = craft.CraftResult(repaired=dict(args))
        sub = []
        if node_type == "EnvironmentLight":
            sub.append(craft.check_envlight_global(
                fields.get("global", MISSING), {"fields": fields}))
        if node_type in craft.rules.INTERP_COMPONENTS and \
                "key" in fields and "keyValue" in fields:
            sub.append(craft.check_interpolator(
                node_type, _as_list(fields["key"]), _as_list(fields["keyValue"]),
                None, {"fields": fields}))
        for s in sub:
            # repairs apply to fields, corrections/notes bubble up
            if "global" in s.repaired:
                fields["global"] = s.repaired["global"]
            res.corrections += s.corrections
            res.notes += s.notes
            res.applied += s.applied
        res.repaired["fields"] = fields
        # remember for state-update once the server returns the id
        self._last_create = {"node_type": node_type, "fields": fields}
        return res

    def _adapt_add_child(self, args: dict) -> craft.CraftResult:
        child_type = self.state.id_to_type.get(args.get("child_id", ""))
        parent_type = self.state.id_to_type.get(args.get("parent_id", ""))
        if not child_type or not parent_type:
            r = craft.CraftResult(repaired=dict(args))
            r.notes.append(
                "Technē could not check containerField: unknown node type for "
                "%s. (Node created before Technē, or via USE.)"
                % (args.get("child_id") if not child_type else args.get("parent_id")))
            return r
        return craft.check_placement(
            parent_type, child_type, args.get("container_field", MISSING) or MISSING,
            args, cf_key="container_field")

    def _adapt_def_node(self, args: dict) -> craft.CraftResult:
        name = args.get("name")
        if name:
            self.state.defined_defs.add(name)
        return craft.CraftResult(repaired=dict(args))

    def _adapt_use_node(self, args: dict) -> craft.CraftResult:
        return craft.check_use_after_def(
            args.get("def_name", ""), self.state.defined_defs, args)

    def _adapt_set_field(self, args: dict) -> craft.CraftResult:
        node_id = args.get("node_id", "")
        fname = args.get("field_name", "")
        val = args.get("value")
        nf = self.state.node_fields.setdefault(node_id, {})
        nf[fname] = val
        node_type = self.state.id_to_type.get(node_id, "")
        if node_type in craft.rules.INTERP_COMPONENTS and \
                "key" in nf and "keyValue" in nf:
            return craft.check_interpolator(
                node_type, _as_list(nf["key"]), _as_list(nf["keyValue"]),
                None, args)
        return craft.CraftResult(repaired=dict(args))

    _ADAPTERS: dict[str, str] = {
        "create_node": "_adapt_create_node",
        "add_child": "_adapt_add_child",
        "def_node": "_adapt_def_node",
        "use_node": "_adapt_use_node",
        "set_field": "_adapt_set_field",
    }

    # -- the public decision surface ----------------------------------------

    def decide(self, tool: str, args: dict) -> Decision:
        args = repair.sap_repair(args)                 # step 1: deterministic repair
        adapter = self._ADAPTERS.get(tool)
        if adapter is None:                            # opt-in: unknown tool passes
            return Decision("forward", tool, args)
        res: craft.CraftResult = getattr(self, adapter)(args)
        if res.corrections:                            # HARD violation -> block
            return Decision("block", tool, args, corrections=res.corrections,
                            notes=res.notes, applied=res.applied)
        return Decision("forward", tool, res.repaired, notes=res.notes,
                        applied=res.applied)

    def observe_result(self, tool: str, args: dict, result_text: str) -> None:
        """Update scene state from a forwarded call's server response."""
        if tool == "create_node" and self._last_create is not None:
            m = _CREATED_RE.search(result_text or "")
            if m:
                nid = m.group(1)
                self.state.id_to_type[nid] = self._last_create["node_type"]
                self.state.node_fields[nid] = dict(self._last_create["fields"])
            self._last_create = None

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
