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

import re
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
    """key/keyValue arity, mirroring the server's validate_semantic exactly:
    fixed-arity interpolators need `arity` floats per key; variable-arity ones
    (Coordinate/Normal) need a whole multiple of a base tuple per key."""
    r = CraftResult(repaired=dict(args))
    if node_type not in rules.INTERP_ARITY:
        return r                              # not a known interpolator
    n_key, n_val = len(key), len(key_value)
    if n_key == 0:
        return r

    def fail(detail):
        r.corrections.append(rules.correction(
            "interp_lengths_match", node_type=node_type, n_key=n_key,
            n_val=n_val, detail=detail))
        r.applied.append("interp_lengths_match")

    if n_val % n_key != 0:
        fail(f"{n_val} is not divisible by the {n_key} key(s); each key needs a "
             f"whole keyValue entry")
        return r
    per = n_val // n_key
    arity = rules.INTERP_ARITY[node_type]
    if arity is not None:
        if per != arity:
            fail(f"expected {arity} per key ({n_key} keys -> {n_key * arity}), "
                 f"got {per} per key")
    else:
        base = rules.INTERP_BASE.get(node_type, 1)
        if per % base != 0:
            fail(f"{per} per key is not a multiple of {base} "
                 f"(one coordinate is {base} floats)")
    return r


def check_duplicate_def(name: str, defined_names: set, args: dict) -> CraftResult:
    """A DEF name must be unique within a scene (validate_semantic duplicate-def)."""
    r = CraftResult(repaired=dict(args))
    if name and name in defined_names:
        r.corrections.append(rules.correction("duplicate_def", name=name))
        r.applied.append("duplicate_def")
    return r


def check_route_defs(from_id: str, to_id: str, id_to_def: dict,
                     args: dict) -> CraftResult:
    """A ROUTE references nodes by DEF; both endpoints must already have one
    (validate_semantic route-missing-from/to-node; scene.add_route raises bare)."""
    r = CraftResult(repaired=dict(args))
    for nid in (from_id, to_id):
        if nid and nid not in id_to_def:
            r.corrections.append(rules.correction("route_no_def", node_id=nid))
            r.applied.append("route_no_def")
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


# --- serialization layer: re-assert omitted-but-required defaults ----------
# x3d.py drops any field left at its library default from the XML. For
# EnvironmentLight that means an omitted `global` (so image-based lighting reads
# as non-global and silently dies). This cannot be fixed at the create_node args
# layer (x3d.py rejects a `global` kwarg) -- it is a post-serialization string
# pass, applied where Technē has the emitted XML in hand (autofix output, a
# fetched scene, or the gate's pre-render step).

_APPEARANCE_RE = re.compile(r"<Appearance\b[^>]*?(?:/>|>.*?</Appearance>)", re.DOTALL)


def dedupe_appearances(xml: str) -> str:
    """Collapse byte-identical <Appearance> subtrees to one DEF + USE references —
    an efficiency win (the Samwel cave inlines the same 3-texture PBR appearance 39
    times, re-binding the textures each time). Deterministic and SAFE: only groups
    verbatim-identical appearances that carry no DEF/USE already, assigns a fresh
    DEF (avoiding existing names) to the first, and replaces the rest with
    <Appearance USE='..'/>. Opt-in (not an automatic proxy transform). Idempotent."""
    matches = list(_APPEARANCE_RE.finditer(xml))
    if not matches:
        return xml
    existing = set(re.findall(r"\bDEF=['\"]([^'\"]+)['\"]", xml))
    groups: dict[str, list] = {}
    for m in matches:
        block = m.group(0)
        if re.search(r"\b(?:DEF|USE)=", block):
            continue                                   # already named — leave it
        groups.setdefault(block, []).append(m)

    repl: dict[tuple, str] = {}
    n = 0
    for block, occ in groups.items():
        if len(occ) < 2:
            continue
        n += 1
        name = f"App{n}"
        while name in existing:
            n += 1
            name = f"App{n}"
        existing.add(name)
        repl[occ[0].span()] = re.sub(r"^<Appearance\b",
                                     f"<Appearance DEF='{name}'", block, count=1)
        for m in occ[1:]:
            repl[m.span()] = f"<Appearance USE='{name}'/>"
    if not repl:
        return xml

    out, last = [], 0
    for m in matches:
        if m.span() in repl:
            out.append(xml[last:m.start()])
            out.append(repl[m.span()])
            last = m.end()
    out.append(xml[last:])
    return "".join(out)


_ENVLIGHT_TAG = re.compile(r"<EnvironmentLight\b([^>]*?)(/?>)")


def reassert_envlight_global(xml: str) -> str:
    """Inject global='true' on any EnvironmentLight start-tag lacking a `global`
    attribute, so scene-wide IBL actually renders (x3d.py Bug 2). Deterministic
    and idempotent; only touches EnvironmentLight (changing a PointLight/SpotLight
    scope would alter lighting semantics, so those are left alone)."""
    def fix(m: "re.Match") -> str:
        attrs, close = m.group(1), m.group(2)
        if re.search(r"\bglobal\s*=", attrs):
            return m.group(0)                  # already set -> idempotent
        return f"<EnvironmentLight global='true'{attrs}{close}"
    return _ENVLIGHT_TAG.sub(fix, xml)
