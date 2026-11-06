"""Compatibility shim for configs written for v0.1 (`mcp run path/to/server.py`).

New setups should run the installed command instead, e.g. `uvx supercollidermcp`;
see the README.
"""

from supercollidermcp.server import create_server

mcp = create_server()
