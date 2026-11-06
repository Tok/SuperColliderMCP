"""End-to-end tests against a real, running scsynth.

Skipped unless SC_TEST_PORT is set. To run them without hearing anything, boot a
server with no hardware outputs:

    scsynth -u 57199 -i 0 -o 0 &
    SC_TEST_PORT=57199 uv run pytest tests/test_live_server.py
"""

from __future__ import annotations

import asyncio
import os

import pytest
from mcp import Client

from supercollidermcp.engine import Engine
from supercollidermcp.osc import SCClient
from supercollidermcp.server import create_server
from supercollidermcp.synthdefs import compiled_synthdefs
from tests.test_server import EVERY_TOOL

PORT = os.environ.get("SC_TEST_PORT")
pytestmark = [pytest.mark.anyio, pytest.mark.skipif(not PORT, reason="set SC_TEST_PORT to a running scsynth")]


async def test_every_tool_against_real_scsynth():
    client = SCClient(os.environ.get("SC_TEST_HOST", "127.0.0.1"), int(PORT or 0))
    engine = Engine(client)
    async with Client(create_server(engine)) as mcp:
        for name, args in EVERY_TOOL.items():
            result = await mcp.call_tool(name, args)
            assert not result.is_error, f"{name}: {result.content[0].text}"

        await asyncio.sleep(0.8)
        status = await client.status()
        assert status.synthdefs >= len(compiled_synthdefs())
        assert status.synths > 5, "voices should be playing"
        setup_errors = len(client.recent_errors)  # existence probes on a fresh server may log /fail

        result = await mcp.call_tool("stop_all", {})
        assert not result.is_error
        await asyncio.sleep(0.5)
        assert (await client.status()).synths == 1, "only the limiter should remain after stop_all"
        assert list(client.recent_errors)[setup_errors:] == [], "scsynth reported errors"
    client.close()
