"""The provenance bridge — enforce the documented/interpretive honesty discipline
as deterministic checks (the caves <-> Technē bridge; a SCOPE EXTENSION beyond X3D
correctness — see GOALS.md and docs/provenance-metadata-proposal.md).

Technē already turns documented X3D *craft* into mechanism; this turns the
documented *provenance* discipline into mechanism too. The convention is the
standardized X3D provenance MetadataSet from the proposal: every cataloged asset
carries

    <MetadataSet name='provenance'>
      <MetadataString name='provenance'  value='"documented"'/>   (|interpretive|generated)
      <MetadataString name='catalogId'   value='"F2"'/>           (key into an asset ledger)
      <MetadataString name='sourceCitation' value='"Stock 1925 Fig.4"'/>
      <MetadataBoolean name='publicDomain' value='true'/>
      <MetadataString name='generationMethod' value='"trace:potrace"'/>
    </MetadataSet>

and Technē checks each block against the ledger (an archive.json-shaped catalog),
turning "you cannot label a feature documented until you have the page that
documents it" into a gate. Pure + dependency-light (stdlib XML); the rules live
here, not in rules.py, to mark provenance as an opt-in extension, not core craft.

NOT auto-wired into the proxy: it is a whole-scene gate that needs the scene XML
and a configured ledger, both of which are the host's choice. Expose
`check_scene_provenance(xml, ledger)` and let the gate / a render post-pass call it.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

HARD = "hard"
SOFT = "soft"

PROV_VALUES = {"documented", "interpretive", "generated"}

# Provenance is GRADUATED so it stays universally useful (see PROVENANCE_BRIDGE.md):
#   L1 disclosure  — keep any provenance tags well-formed + AI content disclosed.
#                    Ledger-free, near-zero friction; the universal slop-resistance
#                    rung (cf. C2PA "is this AI?" content credentials).
#   L2 sourcing    — documented claims must resolve to a cited, public-domain asset
#                    in a ledger. For curated / training repositories.
#   L3 content     — the domain must_not_invent rules (taxon/depth/cal-BC): needs a
#                    structured claim schema; NOT built (deliberately deferred).
RULE_LEVEL = {
    "provenance_invalid_status": 1,
    "provenance_generated_undisclosed": 1,
    "provenance_documented_uncited": 2,
    "provenance_catalogid_unresolved": 2,
    "provenance_not_public_domain": 2,
}

# the provenance rule catalog (kept separate from rules.CATALOG: different domain)
RULES = {
    "provenance_documented_uncited": (
        HARD,
        "{host} is tagged provenance='documented' but carries no catalogId or "
        "sourceCitation. You cannot label a feature documented until you have the "
        "source that documents it -- add a catalogId into the asset ledger or a "
        "sourceCitation.",
    ),
    "provenance_catalogid_unresolved": (
        HARD,
        "{host}: catalogId='{id}' does not resolve to any asset-ledger entry "
        "(have: {available}). Register the asset with its citation/source/"
        "public-domain status, or correct the id.",
    ),
    "provenance_not_public_domain": (
        HARD,
        "{host}: documentary asset catalogId='{id}' is not public-domain in the "
        "ledger. A documentary claim must cite a public-domain (or cleared) source "
        "-- no AI imagery, no uncleared assets presented as record.",
    ),
    "provenance_generated_undisclosed": (
        HARD,
        "{host} is tagged provenance='generated' but discloses no generationMethod. "
        "Generated geometry must say how it was made (e.g. generationMethod="
        "'llm:<model>') so it is never mistaken for a documented record.",
    ),
    "provenance_invalid_status": (
        HARD,
        "{host}: provenance='{status}' is not one of documented|interpretive|generated.",
    ),
}


def correction(rule: str, **f) -> str:
    return RULES[rule][1].format(**f)


# --- ledger ----------------------------------------------------------------

def load_ledger(path: str) -> dict:
    """id -> entry, from an archive.json-shaped catalog ({entries:[{id, ...}]})."""
    data = json.load(open(path))
    return {e["id"]: e for e in data.get("entries", []) if e.get("id")}


# --- parsing ---------------------------------------------------------------

def _local(tag) -> str:
    return tag.split("}", 1)[1] if isinstance(tag, str) and tag.startswith("{") else tag


def _first_val(v):
    """An X3D MetadataString value is MFString ('"documented"'); take the first
    token. MetadataBoolean values ('true') are unquoted and pass through."""
    if v is None:
        return None
    m = re.findall(r'"([^"]*)"', v)
    return m[0] if m else v.strip()


def parse_provenance_blocks(xml: str) -> list[dict]:
    """Every <MetadataSet name='provenance'> as a flat {field: value} dict, plus
    the host node it is attached to (_host tag, _def name). Tolerant parse."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    parent = {c: p for p in root.iter() for c in p}
    blocks = []
    for el in root.iter():
        if _local(el.tag) != "MetadataSet" or el.get("name") != "provenance":
            continue
        prov = {}
        for child in el:
            if _local(child.tag).startswith("Metadata") and child.get("name"):
                prov[child.get("name")] = _first_val(child.get("value"))
        host = parent.get(el)
        prov["_host"] = _local(host.tag) if host is not None else "Scene"
        prov["_def"] = (host.get("DEF") if host is not None else "") or ""
        blocks.append(prov)
    return blocks


# --- checks ----------------------------------------------------------------

def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def check_block(prov: dict, ledger: dict | None = None, level: int = 2) -> list[str]:
    """Validate one provenance block at the given level. Only rules whose
    RULE_LEVEL <= level apply, so L1 (disclosure) needs no ledger and never flags an
    uncited documented claim — that is an L2 (sourcing) concern."""
    ledger = ledger or {}
    host = "%s%s" % (prov.get("_host", "node"),
                     " (DEF=%s)" % prov["_def"] if prov.get("_def") else "")
    status = (prov.get("provenance") or "").strip()
    out: list[str] = []

    def emit(rule, **f):
        if RULE_LEVEL[rule] <= level:
            out.append(correction(rule, host=host, **f))

    if status and status not in PROV_VALUES:
        emit("provenance_invalid_status", status=status)
        return out
    if status == "generated":
        if not prov.get("generationMethod"):
            emit("provenance_generated_undisclosed")
    elif status == "documented":
        cid, cite = prov.get("catalogId"), prov.get("sourceCitation")
        if not cid and not cite:
            emit("provenance_documented_uncited")
        elif cid and cid not in ledger:
            avail = ", ".join(sorted(ledger)[:8]) or "(empty ledger)"
            emit("provenance_catalogid_unresolved", id=cid, available=avail)
        elif cid and not _truthy(ledger[cid].get("public_domain")):
            emit("provenance_not_public_domain", id=cid)
    return out


def check_scene_provenance(xml: str, ledger: dict | None = None,
                           level: int = 2) -> list[str]:
    """Run the provenance gate over a whole scene at `level` (1 disclosure /
    2 sourcing / 3 content). Returns all violations (empty = clean). The host wires
    this into the occupation gate / a render post-pass when the profile enables it."""
    issues: list[str] = []
    for prov in parse_provenance_blocks(xml):
        issues += check_block(prov, ledger, level)
    return issues
