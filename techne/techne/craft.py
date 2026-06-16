"""The deterministic craft engine — the runtime form of the BAML craft-rules.

For each documented silent-failure mode it does one of two things, deterministically:

  * REPAIR — when the correct value is *determinable* (a containerField must equal
    the field it is placed in; an omitted EnvironmentLight.global must be written
    explicitly). Technē rewrites the argument and forwards the corrected call, so
    the craft holds mechanically whether or not the model comprehended it
    (TECHNE_SPEC §0).
  * BLOCK + CORRECT — when the fix needs a choice the layer cannot make (which of
    key/keyValue is wrong; what DEF a dangling USE meant). Technē refuses to
    forward and returns the *prescriptive correction* — the error message is the
    fix, not a bare "invalid" (TECHNE_SPEC §4.3).

The rule identities and correction strings live in `rules.py`; this module is the
logic that the canonical `baml_src/craft.baml` @@assert/@@check declarations mirror.
Running here is deterministic and LLM-free, honoring the spec's governing
determinism commitment.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from . import rules

MISSING = object()   # distinguishes an omitted field from an explicit None/empty


@dataclass
class CraftResult:
    repaired: dict                       # the (possibly rewritten) arguments
    corrections: list[str] = dc_field(default_factory=list)   # HARD: blocks forward
    notes: list[str] = dc_field(default_factory=list)         # SOFT / repair-applied
    applied: list[str] = dc_field(default_factory=list)       # rule names that fired

    @property
    def blocked(self) -> bool:
        return bool(self.corrections)


# --- mode 1: containerField (Bug 1) ----------------------------------------

def _needs_explicit_container(parent_type: str, parent_field: str,
                              node_type: str) -> bool:
    default = rules.DEFAULT_CONTAINER.get(node_type)
    slots = rules.NONDEFAULT_SLOTS.get(parent_type, set())
    # explicit container is required when the placement field is a known non-default
    # slot, or simply differs from the node type's default container.
    if parent_field in slots:
        return True
    return default is not None and parent_field != default


def check_container_field(node_type: str, parent_field: str, parent_type: str,
                          container_field: Any, args: dict) -> CraftResult:
    r = CraftResult(repaired=dict(args))
    if not _needs_explicit_container(parent_type, parent_field, node_type):
        return r
    default = rules.DEFAULT_CONTAINER.get(node_type, "children")
    cf = container_field
    if cf in (None, MISSING, ""):
        r.repaired["containerField"] = parent_field
        r.notes.append("Technē set " + rules.correction(
            "container_field_present", node_type=node_type, field=parent_field,
            default=default))
        r.applied.append("container_field_present")
    elif cf != parent_field:
        r.repaired["containerField"] = parent_field
        r.notes.append("Technē corrected " + rules.correction(
            "container_field_correct", node_type=node_type, field=parent_field,
            got=cf))
        r.applied.append("container_field_correct")
    return r


# --- mode 1b: slot-based placement (the real add_child path) ---------------

def legal_slots(parent_type: str, child_type: str) -> list[str] | None:
    """The legal non-default containerField slots for placing child under parent,
    or None if this combination has no known non-default rule."""
    if (parent_type in rules.MATERIAL_TEXTURE_SLOTS
            and child_type in rules.TEXTURE_NODES):
        return rules.MATERIAL_TEXTURE_SLOTS[parent_type]
    if parent_type == "HAnimHumanoid" and child_type in rules.HUMANOID_SLOTS:
        return rules.HUMANOID_SLOTS[child_type]
    return None


def check_placement(parent_type: str, child_type: str, container_field: Any,
                    args: dict, cf_key: str = "container_field") -> CraftResult:
    """Validate an add_child-style placement (child referenced into a parent).

    REPAIR only when there is exactly one legal slot (no intent to guess);
    otherwise BLOCK and list the legal slots — Technē refuses to pick baseTexture
    vs normalTexture for the model.
    """
    r = CraftResult(repaired=dict(args))
    valid = legal_slots(parent_type, child_type)
    if not valid:
        return r
    cf = container_field
    if cf in valid:
        return r                                     # explicitly correct
    if cf in (None, MISSING, ""):
        default = rules.DEFAULT_CONTAINER.get(child_type, "children")
        if len(valid) == 1:
            r.repaired[cf_key] = valid[0]
            r.notes.append("Technē set containerField='%s'. " % valid[0]
                           + rules.correction("container_field_required",
                             child=child_type, parent=parent_type, default=default,
                             slots=", ".join(valid)))
            r.applied.append("container_field_required")
        else:
            r.corrections.append(rules.correction(
                "container_field_required", child=child_type, parent=parent_type,
                default=default, slots=", ".join(valid)))
            r.applied.append("container_field_required")
    else:
        # a containerField was given but it is not a legal slot here
        r.corrections.append(rules.correction(
            "container_field_invalid_slot", got=cf, child=child_type,
            parent=parent_type, slots=", ".join(valid)))
        r.applied.append("container_field_invalid_slot")
    return r


# --- mode 2: EnvironmentLight.global (Bug 2) -------------------------------

def check_envlight_global(global_value: Any, args: dict) -> CraftResult:
    """Bug 2 is a SERIALIZATION-layer problem, not a constructor-arg one: x3d.py
    rejects a `global` kwarg (reserved word; it uses `global_`) and omits its
    `global_=True` default from the XML — so Technē cannot fix it by rewriting the
    create_node args (the live smoke proved injecting `global` errors upstream).
    At the args layer this is therefore a SOFT advisory; the hard fix belongs in
    the serialization/autofix step (the gate), which injects global='true' into
    the emitted XML."""
    r = CraftResult(repaired=dict(args))
    if global_value is MISSING:
        r.notes.append(rules.correction("envlight_global_set"))
        r.applied.append("envlight_global_set")
    return r


# --- mode 3: interpolator key / keyValue parity ----------------------------

def check_interpolator(node_type: str, key: list, key_value: list,
                       num_coords: int | None, args: dict) -> CraftResult:
    r = CraftResult(repaired=dict(args))
    comp = rules.INTERP_COMPONENTS.get(node_type)
    if comp is None:
        if node_type == "CoordinateInterpolator" and num_coords:
            comp = 3 * num_coords
        else:
            return r        # unknown interpolator type; nothing to assert
    n_key = len(key)
    n_val = len(key_value)
    expected = n_key * comp
    if n_val != expected:
        r.corrections.append(rules.correction(
            "interp_lengths_match", node_type=node_type, n_key=n_key,
            n_val=n_val, expected=expected, comp=comp))
        r.applied.append("interp_lengths_match")
    return r


# --- mode 4: USE-after-DEF (single-call form) ------------------------------

def check_use_after_def(use_name: str, defined_names: set, args: dict) -> CraftResult:
    r = CraftResult(repaired=dict(args))
    if use_name and use_name not in defined_names:
        r.corrections.append(rules.correction("use_after_def", use=use_name))
        r.applied.append("use_after_def")
    return r


# --- soft advisories --------------------------------------------------------

_IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def advise_texture_url(url: str, args: dict) -> CraftResult:
    r = CraftResult(repaired=dict(args))
    if url and not str(url).lower().split("?")[0].endswith(_IMG_EXT):
        r.notes.append(rules.correction("texture_url_image_ext", url=url))
        r.applied.append("texture_url_image_ext")
    return r


def merge(*results: CraftResult) -> CraftResult:
    """Fold several single-rule results into one (repairs compose; lists concat)."""
    out = CraftResult(repaired={})
    for res in results:
        out.repaired.update(res.repaired)
        out.corrections += res.corrections
        out.notes += res.notes
        out.applied += res.applied
    return out
