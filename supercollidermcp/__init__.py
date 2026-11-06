"""SuperColliderMCP: an MCP server for making sound with SuperCollider over OSC."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("supercollider-mcp")
except PackageNotFoundError:  # running from a source checkout without installing
    __version__ = "0.0.0+unknown"
