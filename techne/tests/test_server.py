"""Tests for the MCP transport handlers (server.py) against a fake upstream:
guarded-tool tagging, block-without-forwarding, repaired-forward + relay, and the
cheap render blank-gate."""
import asyncio
import base64
import io
import os
import sys
import types as pytypes

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp import types                                        # noqa: E402
from techne.server import (handle_call_tool, tag_tools,      # noqa: E402
                           GUARDED_HINT)
from techne.proxy import TechneProxy                          # noqa: E402


class FakeResult:
    def __init__(self, content):
        self.content = content


class FakeUpstream:
    def __init__(self):
        self.calls = []
        self._n = 0
        self.render = None        # set to PNG bytes to make render_* return an image

    async def call_tool(self, name, args):
        self.calls.append((name, dict(args or {})))
        if name == "create_node":
            self._n += 1
            nid = "%s_%d" % (args["node_type"].lower(), self._n)
            return FakeResult([types.TextContent(
                type="text", text="Created %s with ID: %s" % (args["node_type"], nid))])
        if name in ("render_image", "render_current_scene") and self.render:
            b64 = base64.b64encode(self.render).decode()
            return FakeResult([types.ImageContent(type="image", data=b64,
                                                  mimeType="image/png")])
        return FakeResult([types.TextContent(type="text", text="ok")])


def _run(coro):
    return asyncio.run(coro)


def _png(solid: bool) -> bytes:
    from PIL import Image
    if solid:
        im = Image.new("L", (48, 48), 180)
    else:
        import random
        rnd = random.Random(1)
        im = Image.new("L", (48, 48))
        im.putdata([rnd.randint(0, 255) for _ in range(48 * 48)])
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# --- tagging ----------------------------------------------------------------

def test_guarded_tools_get_hint():
    tools = [pytypes.SimpleNamespace(name="add_child", description="x"),
             pytypes.SimpleNamespace(name="render_image", description="y")]
    tagged = tag_tools(tools)
    assert tagged[0].description.endswith(GUARDED_HINT)      # add_child guarded
    assert not tagged[1].description.endswith(GUARDED_HINT)  # render_image not


# --- block does not reach upstream -----------------------------------------

def test_blocked_call_never_forwards():
    p, up = TechneProxy(), FakeUpstream()
    _run(handle_call_tool(p, up, "create_node",
                          {"node_type": "PhysicalMaterial", "fields": {}}))
    _run(handle_call_tool(p, up, "create_node",
                          {"node_type": "ImageTexture", "fields": {}}))
    before = len(up.calls)
    out = _run(handle_call_tool(p, up, "add_child",
               {"parent_id": "physicalmaterial_1", "child_id": "imagetexture_2",
                "container_field": ""}))
    assert len(up.calls) == before                          # add_child NOT forwarded
    assert out.isError and "baseTexture" in out.content[0].text                     # prescriptive correction


# --- repaired forward + relay + state ---------------------------------------

def test_envlight_forward_advises_without_breaking_upstream():
    p, up = TechneProxy(), FakeUpstream()
    out = _run(handle_call_tool(p, up, "create_node",
               {"node_type": "EnvironmentLight", "fields": {}}))
    # NOT injected into fields (x3d.py rejects a 'global' kwarg — the smoke proved it)
    assert "global" not in up.calls[-1][1]["fields"]
    # but the advisory note is relayed
    assert any("Technē" in getattr(b, "text", "") for b in out.content)
    # state committed from the (successful) result
    assert p.state.id_to_type.get("environmentlight_1") == "EnvironmentLight"


# --- cheap render gate ------------------------------------------------------

def test_blank_render_appends_warning():
    p, up = TechneProxy(), FakeUpstream()
    up.render = _png(solid=True)                            # blank
    out = _run(handle_call_tool(p, up, "render_image", {"path": "s.x3d"}))
    assert any("BLANK" in getattr(b, "text", "") for b in out.content)


def test_non_blank_render_no_warning():
    p, up = TechneProxy(), FakeUpstream()
    up.render = _png(solid=False)                           # has geometry
    out = _run(handle_call_tool(p, up, "render_image", {"path": "s.x3d"}))
    assert not any("BLANK" in getattr(b, "text", "") for b in out.content)
