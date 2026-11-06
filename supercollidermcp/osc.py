"""Asynchronous OSC client for scsynth that also listens for replies.

scsynth answers on the address a command came from, so one UDP socket is used
for both sending and receiving. Replies resolve awaiting futures; `/fail`
messages are kept in `recent_errors` (and fail the request they belong to).
"""

from __future__ import annotations

import asyncio
import itertools
import logging
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_bundle_builder import OscBundleBuilder
from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

log = logging.getLogger(__name__)

OscArg = int | float | str | bytes
Message = tuple[str, Sequence[OscArg]]


class SCError(Exception):
    """A problem talking to scsynth; the message is meant for the user."""


class ServerUnreachable(SCError):
    pass


@dataclass(frozen=True)
class ServerStatus:
    ugens: int
    synths: int
    groups: int
    synthdefs: int
    avg_cpu: float
    peak_cpu: float
    nominal_sample_rate: float
    actual_sample_rate: float


def encode_message(address: str, args: Sequence[OscArg] = ()) -> OscMessage:
    builder = OscMessageBuilder(address)
    for arg in args:
        if isinstance(arg, bool):
            builder.add_arg(int(arg), "i")
        elif isinstance(arg, int):
            builder.add_arg(arg, "i")
        elif isinstance(arg, float):
            builder.add_arg(arg, "f")
        elif isinstance(arg, str):
            builder.add_arg(arg, "s")
        elif isinstance(arg, bytes):
            builder.add_arg(arg, "b")
        else:
            raise TypeError(f"unsupported OSC argument {arg!r} for {address}")
    return builder.build()


def encode_bundle(timestamp: float, messages: Sequence[Message]) -> OscBundle:
    """A bundle executed by scsynth at `timestamp` (seconds since the Unix epoch)."""
    builder = OscBundleBuilder(timestamp)
    for address, args in messages:
        builder.add_content(encode_message(address, args))
    return builder.build()


def _messages(data: bytes) -> list[OscMessage]:
    if OscBundle.dgram_is_bundle(data):
        out: list[OscMessage] = []
        for content in OscBundle(data):
            out += [content] if isinstance(content, OscMessage) else _messages(content.dgram)
        return out
    return [OscMessage(data)]


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, client: SCClient) -> None:
        self.client = client

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            messages = _messages(data)
        except Exception:  # malformed packet; nothing we can do with it
            log.debug("ignoring unparseable datagram from %s", addr)
            return
        for message in messages:
            self.client._dispatch(message.address, list(message.params))

    def error_received(self, exc: Exception) -> None:
        # On Linux a connected UDP socket reports ICMP "port unreachable" here.
        self.client._fail_all(exc)


@dataclass
class _Waiter:
    address: str
    request: str
    match: Callable[[list], bool]
    future: asyncio.Future


class SCClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 57110, timeout: float = 1.0) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.recent_errors: deque[str] = deque(maxlen=20)
        self._transport: asyncio.DatagramTransport | None = None
        self._waiters: list[_Waiter] = []
        self._sync_ids = itertools.count(1)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    async def _ensure_transport(self) -> asyncio.DatagramTransport:
        if self._transport is None or self._transport.is_closing():
            loop = asyncio.get_running_loop()
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: _Protocol(self), remote_addr=(self.host, self.port)
            )
        return self._transport

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    # ---- sending -----------------------------------------------------------

    async def send(self, address: str, *args: OscArg) -> None:
        (await self._ensure_transport()).sendto(encode_message(address, args).dgram)

    async def send_bundle(self, timestamp: float, messages: Sequence[Message]) -> None:
        (await self._ensure_transport()).sendto(encode_bundle(timestamp, messages).dgram)

    async def request(
        self,
        address: str,
        args: Sequence[OscArg],
        reply: str,
        match: Callable[[list], bool] = lambda _: True,
        timeout: float | None = None,
    ) -> list:
        """Send a command and wait for the reply `reply` whose arguments satisfy `match`."""
        transport = await self._ensure_transport()
        waiter = _Waiter(reply, address, match, asyncio.get_running_loop().create_future())
        self._waiters.append(waiter)
        try:
            transport.sendto(encode_message(address, args).dgram)
            return await asyncio.wait_for(waiter.future, timeout or self.timeout)
        except (asyncio.TimeoutError, OSError) as exc:
            raise ServerUnreachable(
                f"No reply from the SuperCollider server at {self.address}. Is scsynth running? "
                "Boot it from the SuperCollider IDE (Server > Boot Server), with s.boot in sclang, "
                f"or run `scsynth -u {self.port}`."
            ) from exc
        finally:
            if waiter in self._waiters:
                self._waiters.remove(waiter)

    # ---- receiving ---------------------------------------------------------

    def _dispatch(self, address: str, args: list) -> None:
        if address == "/fail":
            text = " ".join(str(a) for a in args)
            self.recent_errors.append(text)
            log.warning("scsynth: /fail %s", text)
            command = args[0] if args else None
            for waiter in list(self._waiters):
                if waiter.request == command and not waiter.future.done():
                    waiter.future.set_exception(SCError(f"scsynth refused {text}"))
            return
        for waiter in list(self._waiters):
            if waiter.address == address and not waiter.future.done() and waiter.match(args):
                waiter.future.set_result(args)
                return

    def _fail_all(self, exc: Exception) -> None:
        for waiter in list(self._waiters):
            if not waiter.future.done():
                waiter.future.set_exception(exc)
        # the socket is unusable after an ICMP error on some platforms; reconnect next time
        self.close()

    # ---- commands ----------------------------------------------------------

    async def status(self) -> ServerStatus:
        args = await self.request("/status", [], "/status.reply")
        return ServerStatus(*(int(a) for a in args[1:5]), *(float(a) for a in args[5:9]))

    async def version(self) -> str | None:
        """scsynth version string such as '3.13.0', or None if the server is too old to say."""
        try:
            args = await self.request("/version", [], "/version.reply", timeout=0.5)
        except SCError:
            return None
        return f"{args[1]}.{args[2]}{args[3]}" if len(args) >= 4 else None

    async def sync(self, timeout: float = 5.0) -> None:
        """Wait until scsynth has finished every asynchronous command sent before this one."""
        sync_id = next(self._sync_ids)
        await self.request("/sync", [sync_id], "/synced", lambda a: bool(a) and a[0] == sync_id, timeout)

    async def synth_exists(self, node_id: int, control: str) -> bool:
        """True if synth `node_id` exists (asked via /s_get, which always answers the sender)."""
        return await self._exists("/s_get", [node_id, control], "/n_set", node_id)

    async def group_exists(self, node_id: int) -> bool:
        """True if group `node_id` exists (asked via /g_queryTree, which always answers the sender)."""
        return await self._exists("/g_queryTree", [node_id, 0], "/g_queryTree.reply", node_id, index=1)

    async def _exists(self, address: str, args: list, reply: str, node_id: int, index: int = 0) -> bool:
        # /n_query is no use here: its /n_info reply only goes to clients registered with /notify
        try:
            await self.request(address, args, reply, lambda a: len(a) > index and a[index] == node_id)
        except ServerUnreachable:
            raise
        except SCError:
            return False
        return True
