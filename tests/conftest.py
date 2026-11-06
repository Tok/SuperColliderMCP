from __future__ import annotations

import asyncio
import contextlib

import pytest
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message import OscMessage

from supercollidermcp.osc import _messages, encode_message


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeScsynth(asyncio.DatagramProtocol):
    """Just enough of scsynth's reply behaviour to test the client and the tools.

    Records every message it receives; bundles are recorded with their timetag.
    """

    def __init__(self) -> None:
        self.messages: list[tuple[str, list]] = []
        self.bundles: list[tuple[float, list[tuple[str, list]]]] = []
        self.nodes: set[int] = set()
        self.synthdefs = 0
        self.silent = False  # True: never answer, like a server that is not running
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport) -> None:
        self.transport = transport

    @property
    def port(self) -> int:
        return self.transport.get_extra_info("sockname")[1]

    def addresses(self) -> list[str]:
        return [address for address, _ in self.messages]

    def scheduled(self) -> list[tuple[str, list]]:
        return [m for _, contents in self.bundles for m in contents]

    def datagram_received(self, data: bytes, addr) -> None:
        if data.startswith(b"#bundle"):
            contents = [(m.address, list(m.params)) for m in _messages(data)]
            self.bundles.append((OscBundle(data).timestamp, contents))
            return
        message = OscMessage(data)
        address, args = message.address, list(message.params)
        self.messages.append((address, args))
        if self.silent:
            return
        reply = self._reply(address, args)
        if reply:
            self.transport.sendto(encode_message(*reply).dgram, addr)

    def _reply(self, address: str, args: list):
        if address == "/status":
            return "/status.reply", [1, 0, 0, len(self.nodes), self.synthdefs, 1.5, 2.5, 48000.0, 48000.0]
        if address == "/version":
            return "/version.reply", ["scsynth", 3, 13, ".0", "Version-3.13.0", "abc"]
        if address == "/sync":
            return "/synced", [args[0]]
        if address == "/d_recv":
            self.synthdefs += 1
            return None
        if address in ("/g_new", "/s_new") and isinstance(args[1 if address == "/s_new" else 0], int):
            self.nodes.add(args[1] if address == "/s_new" else args[0])
            return None
        if address == "/n_free":
            self.nodes.discard(args[0])
            return None
        if address == "/s_get":
            if args[0] in self.nodes:
                return "/n_set", [args[0], args[1], 0.95]
            return "/fail", ["/s_get", f"Node {args[0]} not found"]
        if address == "/g_queryTree":
            if args[0] in self.nodes:
                return "/g_queryTree.reply", [0, args[0], 0]
            return "/fail", ["/g_queryTree", f"Node {args[0]} not found"]
        return None


@pytest.fixture
async def fake_scsynth():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(FakeScsynth, local_addr=("127.0.0.1", 0))
    yield protocol
    with contextlib.suppress(Exception):
        transport.close()
