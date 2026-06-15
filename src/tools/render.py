"""X3DOM HTML page rendering tool.

Wraps X3D scene content in a browser-viewable HTML page that loads X3DOM
from CDN. Handles X3D-to-X3DOM tag-case and attribute-case conversion
plus namespace stripping required by the HTML5 parser.

Adapted from generation.py in https://github.com/niknarra/x3d-mcp by
Nikhil Narra and Nicholas Polys (Virginia Tech / Web3D Consortium).
"""

import tempfile
from pathlib import Path

from lxml import etree

from mcp.server.fastmcp import FastMCP, Image

from x3d_utils.source import load_x3d_source


_X3DOM_CDN_CSS = "https://www.x3dom.org/download/1.8.2/x3dom.css"
_X3DOM_CDN_JS = "https://www.x3dom.org/download/1.8.2/x3dom.js"

# Software-GL flags so headless Chromium renders WebGL without a real GPU.
_RENDER_ARGS = [
    "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist", "--no-sandbox", "--hide-scrollbars",
]


def _render_html_to_png(html: str, width: int, height: int, wait_ms: int) -> bytes:
    """Render an X3DOM HTML page to PNG bytes via headless Chromium (Playwright)."""
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as td:
        page_path = Path(td) / "scene.html"
        page_path.write_text(html, encoding="utf-8")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=_RENDER_ARGS)
            try:
                page = browser.new_page(viewport={"width": width, "height": height + 90})
                page.goto(page_path.as_uri(), wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(wait_ms)        # let X3DOM init + draw a frame
                try:
                    png = page.locator("canvas").first.screenshot(timeout=5000)
                except Exception:
                    png = page.screenshot()           # fall back to the whole page
            finally:
                browser.close()
    return png


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _indent_content(content: str, spaces: int) -> str:
    prefix = " " * spaces
    lines = content.strip().split("\n")
    return "\n".join(prefix + line if line.strip() else line for line in lines)


def _element_to_x3dom_html(el: etree._Element, depth: int = 0) -> str:
    """Recursively convert an lxml element to X3DOM-friendly HTML.

    X3DOM runs inside the browser's HTML5 parser, which lowercases tag
    and attribute names and does not honor self-closing tags on non-void
    elements. This serializer normalises accordingly and strips XML
    namespace declarations / prefixed attributes.
    """
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        tag = tag.split("}", 1)[1]
    tag = tag.lower()

    attrs = []
    for attr_name, attr_val in el.attrib.items():
        if attr_name.startswith("{") or ":" in attr_name:
            continue
        # Escape for HTML attribute context -- MFString values (e.g.
        # NavigationInfo type='"EXAMINE" "ANY"') contain literal quotes.
        attr_val = attr_val.replace("&", "&amp;").replace('"', "&quot;")
        attrs.append(f'{attr_name.lower()}="{attr_val}"')

    indent = "    " * depth
    attr_str = (" " + " ".join(attrs)) if attrs else ""

    children = list(el)
    if children:
        inner = "\n".join(
            _element_to_x3dom_html(child, depth + 1) for child in children
        )
        return f"{indent}<{tag}{attr_str}>\n{inner}\n{indent}</{tag}>"

    text = (el.text or "").strip()
    if text:
        return f"{indent}<{tag}{attr_str}>{text}</{tag}>"
    return f"{indent}<{tag}{attr_str}></{tag}>"


def _local_tag(el: etree._Element) -> str:
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _extract_scene_content(x3d_content: str) -> str:
    """Extract <Scene> children from an X3D document and convert to X3DOM HTML.

    If the input is a full X3D document, parse it, find the Scene, and
    serialize each child as X3DOM HTML. If the input is already a raw
    fragment, return it as-is (assumed pre-formatted).
    """
    stripped = x3d_content.strip()

    if not stripped.startswith("<?xml") and not stripped.startswith("<X3D"):
        return _indent_content(stripped, 12)

    try:
        parser = etree.XMLParser(
            remove_blank_text=True, remove_comments=True, remove_pis=True
        )
        tree = etree.fromstring(stripped.encode(), parser)
    except etree.XMLSyntaxError:
        return _indent_content(stripped, 12)

    scene_el = None
    if _local_tag(tree) == "Scene":
        scene_el = tree
    else:
        for child in tree.iter():
            if _local_tag(child) == "Scene":
                scene_el = child
                break

    if scene_el is None:
        return _indent_content(stripped, 12)

    parts = [_element_to_x3dom_html(child, depth=0) for child in scene_el]
    return _indent_content("\n".join(parts), 12)


def _x3dom_page(
    content: str,
    title: str = "X3DOM Scene",
    width: str = "800px",
    height: str = "600px",
    show_stats: bool = False,
    show_log: bool = False,
) -> str:
    """Wrap X3D content in a complete X3DOM HTML page."""
    scene_content = _extract_scene_content(content)
    stats_attr = ' showStat="true"' if show_stats else ""
    log_attr = ' showLog="true"' if show_log else ""
    title_safe = _escape_html(title)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title_safe}</title>
    <link rel="stylesheet" href="{_X3DOM_CDN_CSS}">
    <script src="{_X3DOM_CDN_JS}"></script>
    <style>
        body {{
            margin: 0;
            font-family: sans-serif;
            background: #1a1a2e;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        h1 {{
            color: #e0e0e0;
            margin-bottom: 16px;
        }}
        x3d {{
            border: 1px solid #333;
        }}
    </style>
</head>
<body>
    <h1>{title_safe}</h1>
    <x3d width="{width}" height="{height}"{stats_attr}{log_attr}>
        <scene>
{scene_content}
        </scene>
    </x3d>
</body>
</html>"""


def _x3dom_starter(
    title: str = "X3DOM Scene",
    width: str = "800px",
    height: str = "600px",
) -> str:
    """Return a starter X3DOM HTML page with a small example scene."""
    scene_content = (
        '            <viewpoint description="Default View" position="0 0 10"></viewpoint>\n'
        '            <directionallight direction="0 -1 -1" intensity="0.8"></directionallight>\n'
        '            <transform>\n'
        '                <shape>\n'
        '                    <appearance>\n'
        '                        <material diffusecolor="0.8 0.2 0.2"></material>\n'
        '                    </appearance>\n'
        '                    <box size="2 2 2"></box>\n'
        '                </shape>\n'
        '            </transform>'
    )
    return _x3dom_page(scene_content, title=title, width=width, height=height)


def register(mcp: FastMCP):

    @mcp.tool()
    def x3dom_page(
        content: str,
        title: str = "X3DOM Scene",
        width: str = "800px",
        height: str = "600px",
        show_stats: bool = False,
        show_log: bool = False,
    ) -> str:
        """Wrap X3D scene content in a standalone X3DOM HTML page for browser viewing.

        Accepts either a full X3D XML document (will extract the <Scene> children)
        or a pre-formatted X3DOM fragment (will be embedded as-is). Tag and
        attribute names are lowercased and self-closing tags are expanded to
        match what the HTML5 parser expects.

        Args:
            content: X3D XML (full document or scene fragment).
            title: Page title.
            width: x3d element width (e.g. "800px", "100%").
            height: x3d element height (e.g. "600px", "100vh").
            show_stats: Show X3DOM frame stats overlay.
            show_log: Show X3DOM log panel.
        """
        return _x3dom_page(content, title, width, height, show_stats, show_log)

    @mcp.tool()
    def render_image(
        content: str = "",
        path: str = "",
        width: int = 720,
        height: int = 540,
        wait_ms: int = 2500,
        save_path: str = "",
    ):
        """Render an X3D scene to a PNG image and return it so you can SEE the result.

        This closes the author -> validate -> RENDER loop: a scene can pass both
        validators and still be visually wrong (off-camera, unlit, mis-scaled).
        Headlessly loads the scene in X3DOM (software WebGL) and screenshots it.

        Tip: if the image is blank, the usual causes are no/!bound Viewpoint, no
        light, or geometry outside the view -- not a render failure. Add a
        Viewpoint and a DirectionalLight and re-render.

        Args:
            content: X3D XML (full document or scene fragment), inline.
            path: Path to an X3D file to render instead of inline content.
                  Provide exactly one of `content` or `path`.
            width: Render width in pixels.
            height: Render height in pixels.
            wait_ms: Milliseconds to wait for X3DOM to initialise and draw.
            save_path: Optional path to also write the PNG to disk.
        """
        try:
            text = load_x3d_source(content, path)
        except ValueError as exc:
            return f"Input error: {exc}"
        try:
            import playwright.sync_api  # noqa: F401
        except ImportError:
            return (
                "render_image needs Playwright (one-time setup):\n"
                "  pip install playwright && python -m playwright install chromium\n"
                "Until then, use x3dom_page(content) and open the HTML in a browser."
            )
        html = _x3dom_page(text, title="X3D render",
                           width=f"{width}px", height=f"{height}px")
        try:
            png = _render_html_to_png(html, width, height, wait_ms)
        except Exception as exc:
            return f"Render failed: {exc}"
        if save_path:
            Path(save_path).expanduser().write_bytes(png)
        return Image(data=png, format="png")

    @mcp.tool()
    def render_current_scene(width: int = 720, height: int = 540, wait_ms: int = 2500,
                             save_path: str = ""):
        """Render the current granular (in-memory) scene to a PNG you can inspect.

        The granular-mode counterpart of render_image -- build with create_node/
        add_child, then SEE the result before declaring done.

        Args:
            width: Render width in pixels.
            height: Render height in pixels.
            wait_ms: Milliseconds to wait for X3DOM to initialise and draw.
            save_path: Optional path to also write the PNG to disk.
        """
        from tools.granular import _scene
        try:
            import playwright.sync_api  # noqa: F401
        except ImportError:
            return (
                "render needs Playwright (one-time setup):\n"
                "  pip install playwright && python -m playwright install chromium"
            )
        html = _x3dom_page(_scene.to_xml(), title="X3D scene",
                           width=f"{width}px", height=f"{height}px")
        try:
            png = _render_html_to_png(html, width, height, wait_ms)
        except Exception as exc:
            return f"Render failed: {exc}"
        if save_path:
            Path(save_path).expanduser().write_bytes(png)
        return Image(data=png, format="png")

    @mcp.tool()
    def x3dom_starter(
        title: str = "X3DOM Scene",
        width: str = "800px",
        height: str = "600px",
    ) -> str:
        """Return a starter X3DOM HTML page with a simple example scene.

        Useful as a known-good baseline to verify the X3DOM CDN, page chrome,
        and viewpoint defaults render correctly in a browser.

        Args:
            title: Page title.
            width: x3d element width.
            height: x3d element height.
        """
        return _x3dom_starter(title, width, height)
