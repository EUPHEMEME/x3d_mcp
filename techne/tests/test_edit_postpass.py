"""Tier-2: Technē post-validates the content-based edit tools (modify/move/remove/
convert) through the server's own validators, since those tools validate almost
nothing themselves. Drives handle_call_tool against a fake upstream."""
import asyncio

from mcp import types
from techne.server import handle_call_tool, tag_tools, POSTCHECK_HINT
from techne.proxy import TechneProxy


class FakeResult:
    def __init__(self, content):
        self.content = content


class EditUpstream:
    """Returns `doc` for any edit verb, and canned verdicts for the validators."""
    def __init__(self, doc, vx='{"valid": true, "errors": []}', vs="# Semantic Check: All Clear"):
        self.doc, self.vx, self.vs = doc, vx, vs
        self.calls = []

    async def call_tool(self, name, args):
        self.calls.append(name)
        text = {"validate_x3d": self.vx, "validate_semantic": self.vs}.get(name, self.doc)
        return FakeResult([types.TextContent(type="text", text=text)])


def _run(coro):
    return asyncio.run(coro)


def _text(res):
    return "\n".join(b.text for b in res.content if getattr(b, "text", None))


def test_edit_verbs_get_postcheck_hint():
    import types as pyt
    tagged = tag_tools([pyt.SimpleNamespace(name="modify_x3d_node", description="x")])
    assert tagged[0].description.endswith(POSTCHECK_HINT)


def test_modify_surfaces_schema_error():
    # modify_x3d_node writes a misspelled attribute and reports success; the XSD
    # post-pass catches it.
    up = EditUpstream(
        doc="<?xml version='1.0'?><X3D><Scene><Shape DEF='S'/></Scene></X3D>",
        vx='{"valid": false, "errors": ["Line 1: attribute \'diffusColor\': not allowed"]}')
    res = _run(handle_call_tool(TechneProxy(), up, "modify_x3d_node",
                                {"def_name": "S", "field_changes": "{}"}))
    txt = _text(res)
    assert "Technē post-check" in txt and "validate_x3d" in txt and "diffusColor" in txt
    assert "validate_x3d" in up.calls and "validate_semantic" in up.calls


def test_move_surfaces_semantic_error():
    # move_x3d_node never re-checks containerField; the semantic post-pass does.
    up = EditUpstream(
        doc="<?xml version='1.0'?><X3D><Scene><Shape/></Scene></X3D>",
        vs="# Semantic Check Report\n\nFound 1 error(s).\n\n## Errors\n\n"
           "- **[containerfield-type-mismatch]** PhysicalMaterial.baseTexture does "
           "not accept a Box.\n")
    res = _run(handle_call_tool(TechneProxy(), up, "move_x3d_node",
                                {"def_name": "S", "new_parent_def": "M"}))
    txt = _text(res)
    assert "post-check" in txt and "validate_semantic" in txt and "does not accept" in txt


def test_clean_edit_is_quiet():
    up = EditUpstream(doc="<?xml version='1.0'?><X3D><Scene><Shape/></Scene></X3D>")
    res = _run(handle_call_tool(TechneProxy(), up, "remove_x3d_node",
                                {"def_name": "S"}))
    assert "post-check" not in _text(res)


def test_error_string_flagged_without_validating():
    up = EditUpstream(doc="No node with DEF=Foo found. Available DEFs: Bar.")
    res = _run(handle_call_tool(TechneProxy(), up, "modify_x3d_node",
                                {"def_name": "Foo", "field_changes": "{}"}))
    txt = _text(res)
    assert "returned an error string" in txt and "did not apply" in txt
    assert "validate_x3d" not in up.calls          # don't validate a non-document
