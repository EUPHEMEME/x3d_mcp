"""The provenance bridge: enforce the documented/interpretive honesty discipline
against an asset ledger. The convention is the X3D provenance MetadataSet from
docs/provenance-metadata-proposal.md."""
import os

from techne import provenance as P

LEDGER = {
    "F2": {"public_domain": True, "citation": "Stock 1925 Fig.4"},
    "X9": {"public_domain": False, "citation": "uncleared scan"},
}


def _block(def_name, *pairs, mset="provenance"):
    meta = "".join(f"<MetadataString name='{n}' value='\"{v}\"'/>" for n, v in pairs)
    return f"<Transform DEF='{def_name}'><MetadataSet name='{mset}'>{meta}</MetadataSet></Transform>"


def _scene(*transforms):
    return "<X3D><Scene>" + "".join(transforms) + "</Scene></X3D>"


# -- parsing ----------------------------------------------------------------

def test_parse_extracts_block_and_host():
    xml = _scene(_block("Hero", ("provenance", "documented"), ("catalogId", "F2")))
    blocks = P.parse_provenance_blocks(xml)
    assert len(blocks) == 1
    b = blocks[0]
    assert b["provenance"] == "documented" and b["catalogId"] == "F2"
    assert b["_host"] == "Transform" and b["_def"] == "Hero"


def test_parse_ignores_non_provenance_metadata():
    xml = _scene(_block("X", ("foo", "bar"), mset="other"))
    assert P.parse_provenance_blocks(xml) == []


# -- the rules --------------------------------------------------------------

def test_documented_with_resolvable_public_domain_is_clean():
    b = {"provenance": "documented", "catalogId": "F2", "_host": "Transform", "_def": "Hero"}
    assert P.check_block(b, LEDGER) == []


def test_documented_without_citation_blocks():
    b = {"provenance": "documented", "_host": "Shape", "_def": ""}
    issues = P.check_block(b, LEDGER)
    assert issues and "documented" in issues[0] and "no catalogId" in issues[0]


def test_documented_with_unresolved_id_blocks():
    b = {"provenance": "documented", "catalogId": "Z9", "_host": "Shape", "_def": ""}
    issues = P.check_block(b, LEDGER)
    assert issues and "does not resolve" in issues[0] and "F2" in issues[0]


def test_documented_citing_non_public_domain_blocks():
    b = {"provenance": "documented", "catalogId": "X9", "_host": "Shape", "_def": ""}
    issues = P.check_block(b, LEDGER)
    assert issues and "not public-domain" in issues[0]


def test_generated_must_disclose_method():
    bad = {"provenance": "generated", "_host": "Shape", "_def": ""}
    assert P.check_block(bad, LEDGER) and "generationMethod" in P.check_block(bad, LEDGER)[0]
    ok = {"provenance": "generated", "generationMethod": "llm:claude", "_host": "Shape"}
    assert P.check_block(ok, LEDGER) == []


def test_interpretive_is_unconstrained():
    assert P.check_block({"provenance": "interpretive", "_host": "Shape"}, LEDGER) == []


def test_invalid_status_blocks():
    issues = P.check_block({"provenance": "surveyed", "_host": "Shape"}, LEDGER)
    assert issues and "not one of" in issues[0]


def test_check_scene_aggregates():
    xml = _scene(
        _block("Good", ("provenance", "documented"), ("catalogId", "F2")),
        _block("Uncited", ("provenance", "documented")),
        _block("BadRef", ("provenance", "documented"), ("catalogId", "Z9")),
    )
    issues = P.check_scene_provenance(xml, LEDGER)
    assert len(issues) == 2          # Good passes; Uncited + BadRef fail


# -- against the real archive.json ledger -----------------------------------

def test_real_archive_ledger_resolves_f2():
    repo = os.environ.get("X3D_MCP_REPO", "/Users/alexander/x3d_mcp")
    path = os.path.join(repo, "drawings", "archive.json")
    if not os.path.exists(path):
        return                       # skip if the caves data isn't present
    ledger = P.load_ledger(path)
    assert "F2" in ledger and ledger["F2"].get("public_domain") is True
    # F2 (Nothrotheriops, Stock 1925, public domain) is a clean documented claim
    b = {"provenance": "documented", "catalogId": "F2", "_host": "Transform", "_def": "Sloth"}
    assert P.check_block(b, ledger) == []
