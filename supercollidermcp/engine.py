"""Server-side state: one-time setup, bus allocation and streaming playback.

Node layout inside scsynth (all IDs are fixed, far above the ranges sclang uses):

    group ROOT_GROUP          (head of the root node)
      group SOURCE_GROUP      every voice and LFO
      group FX_GROUP          one mcp_fx synth per tool call that asked for effects
      synth LIMITER           mcp_limiter on the hardware outputs

Playback streams a phrase's events as timestamped OSC bundles a little ahead
of time, so scsynth does the precise scheduling and tool calls return at once.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass

from .compose import Event, Phrase
from .osc import Message, SCClient, ServerStatus
from .synthdefs import compiled_synthdefs

log = logging.getLogger(__name__)

ROOT_GROUP = 2_147_480_000
SOURCE_GROUP = ROOT_GROUP + 1
FX_GROUP = ROOT_GROUP + 2
LIMITER = ROOT_GROUP + 3

ADD_TO_HEAD, ADD_TO_TAIL, ADD_AFTER = 0, 1, 3
MAX_BUNDLE_MESSAGES = 32  # keeps every datagram comfortably small

_PLACEMENT = {
    "lfo": (ADD_TO_HEAD, SOURCE_GROUP),  # LFOs run before the voices that read their buses
    "source": (ADD_TO_TAIL, SOURCE_GROUP),
    "fx": (ADD_TO_TAIL, FX_GROUP),
}


@dataclass
class Playback:
    id: int
    summary: str
    start: float  # wall-clock time of the first event
    duration: float
    task: asyncio.Task

    def remaining(self) -> float:
        return max(0.0, self.start + self.duration - time.time())


def s_new(event: Event) -> Message:
    action, target = _PLACEMENT[event.kind]
    args: list = [event.synth, -1, action, target]
    for name, value in event.params.items():
        args += [name, value if isinstance(value, str) else float(value)]
    return "/s_new", args


class Engine:
    def __init__(
        self,
        client: SCClient,
        latency: float = 0.2,
        lookahead: float = 0.5,
        audio_buses: tuple[int, int] = (512, 1024),
        control_buses: tuple[int, int] = (8192, 16384),
    ) -> None:
        self.client = client
        self.latency = latency
        self.lookahead = lookahead
        self._audio_buses = itertools.cycle(range(audio_buses[0], audio_buses[1] - 1, 2))
        self._control_buses = itertools.cycle(range(*control_buses))
        self._playbacks: dict[int, Playback] = {}
        self._ids = itertools.count(1)
        self._setup_lock = asyncio.Lock()
        self._known_installed = False

    # ---- server setup ------------------------------------------------------

    async def ensure_ready(self) -> ServerStatus:
        """Check that scsynth answers and (re)install SynthDefs and groups if they are missing.

        Called before every tool, so a restarted server is set up again transparently.
        """
        async with self._setup_lock:
            status = await self.client.status()
            if self._known_installed and await self.client.synth_exists(LIMITER, "level"):
                return status
            if self._known_installed:
                self._known_installed = False  # the server was restarted or our nodes were freed

            # Each probe for a missing node prints a FAILURE line in the SuperCollider post
            # window, so a fresh server is detected with a single probe (for the root group).
            root_exists = await self.client.group_exists(ROOT_GROUP)
            # Upload SynthDefs even when another session already set the server up: it may
            # have been an older version of this package with different SynthDefs.
            await self._load_synthdefs()
            if not (root_exists and await self.client.synth_exists(LIMITER, "level")):
                await self._create_groups(replace=root_exists)
            self._known_installed = True
            return await self.client.status()

    async def _load_synthdefs(self) -> None:
        log.info("loading SynthDefs on %s", self.client.address)
        for data in compiled_synthdefs().values():
            await self.client.send("/d_recv", data)
        await self.client.sync()

    async def _create_groups(self, replace: bool) -> None:
        log.info("creating groups on %s", self.client.address)
        if replace:
            await self.client.send("/n_free", ROOT_GROUP)
        await self.client.send("/g_new", ROOT_GROUP, ADD_TO_HEAD, 0)
        await self.client.send("/g_new", SOURCE_GROUP, ADD_TO_HEAD, ROOT_GROUP)
        await self.client.send("/g_new", FX_GROUP, ADD_AFTER, SOURCE_GROUP)
        await self.client.send("/s_new", "mcp_limiter", LIMITER, ADD_TO_TAIL, ROOT_GROUP)
        await self.client.sync()

    # ---- buses -------------------------------------------------------------

    def audio_bus(self) -> int:
        """First channel of a private stereo bus (round robin; plenty for concurrent calls)."""
        return next(self._audio_buses)

    def control_bus(self) -> int:
        return next(self._control_buses)

    # ---- playback ----------------------------------------------------------

    def play(self, phrase: Phrase) -> Playback:
        start = time.time() + self.latency
        playback_id = next(self._ids)
        task = asyncio.get_running_loop().create_task(self._stream(phrase.events, start, phrase.duration))
        playback = Playback(playback_id, phrase.summary, start, phrase.duration, task)
        self._playbacks[playback_id] = playback
        task.add_done_callback(lambda t: self._finished(playback_id, t))
        return playback

    def _finished(self, playback_id: int, task: asyncio.Task) -> None:
        self._playbacks.pop(playback_id, None)
        if not task.cancelled() and (exc := task.exception()):
            log.error("playback %d failed: %s", playback_id, exc)
            self.client.recent_errors.append(f"playback {playback_id} failed: {exc}")

    async def _stream(self, events: Iterable[Event], start: float, duration: float) -> None:
        for offset, group in itertools.groupby(events, key=lambda e: e.time):
            due = start + offset
            wait = due - self.lookahead - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
            messages = [s_new(event) for event in group]
            for i in range(0, len(messages), MAX_BUNDLE_MESSAGES):
                await self.client.send_bundle(due, messages[i : i + MAX_BUNDLE_MESSAGES])
        # keep the playback listed until its sound has finished
        await asyncio.sleep(max(0.0, start + duration - time.time()))

    def active(self) -> list[Playback]:
        return sorted(self._playbacks.values(), key=lambda p: p.id)

    async def stop_all(self) -> int:
        """Cancel every playback and silence everything this server started."""
        stopped = len(self._playbacks)
        for playback in list(self._playbacks.values()):
            playback.task.cancel()
        await self.client.send("/clearSched")
        await self.client.send("/g_freeAll", SOURCE_GROUP)
        await self.client.send("/g_freeAll", FX_GROUP)
        return stopped
