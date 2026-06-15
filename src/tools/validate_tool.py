"""X3D validation MCP tools.

Exposes validation pipeline as MCP tools.
"""

import json
from mcp.server.fastmcp import FastMCP

from validation.validate import validate_xml, validate_json
from validation.semantic import validate_semantic as _validate_semantic
from tools.granular import _scene
from x3d_utils.source import load_x3d_source


def register(mcp: FastMCP):

    @mcp.tool()
    def validate_x3d(content: str = "", encoding: str = "xml", path: str = "") -> str:
        """Validate X3D against the X3D 4.1 schema (inline content OR a file path).

        Args:
            content: The X3D content string to validate (inline).
            encoding: Content encoding - "xml" or "json".
            path: Path to an X3D file to validate instead of inline content.
                  Provide exactly one of `content` or `path`.
        """
        try:
            text = load_x3d_source(content, path)
        except ValueError as exc:
            return json.dumps({"valid": False, "errors": [str(exc)]}, indent=2)
        if encoding == "xml":
            result = validate_xml(text)
        elif encoding == "json":
            result = validate_json(text)
        else:
            result = {"valid": False, "errors": [f"Unsupported encoding: {encoding}"]}
        return json.dumps(result, indent=2)

    @mcp.tool()
    def validate_current_scene() -> str:
        """Validate the current granular scene against the X3D 4.1 schema."""
        xml_content = _scene.to_xml()
        result = validate_xml(xml_content)
        return json.dumps(result, indent=2)

    @mcp.tool()
    def validate_semantic(content: str = "", path: str = "") -> str:
        """Run semantic checks on X3D beyond XSD schema validation (content OR path).

        Detects authoring issues XSD cannot catch and that silently break rendering:
        wrong/defaulted containerField (with the correct field suggested),
        USE-before-DEF ordering, ROUTE field/type/access-type problems, Shapes
        without geometry, empty grouping nodes, duplicate DEFs, and missing
        Viewpoints. Returns a markdown report.

        Args:
            content: The X3D XML content string to check (inline).
            path: Path to an X3D file to check instead of inline content.
                  Provide exactly one of `content` or `path`.
        """
        try:
            text = load_x3d_source(content, path)
        except ValueError as exc:
            return f"# Semantic Check: Input Error\n\n{exc}"
        return _validate_semantic(text)
