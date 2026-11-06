"""Drum patterns as step strings.

Each lane is a string with one character per 16th-note step:

    X  accent      x  hit      o  ghost (quiet)      .  rest

Lanes may have different lengths; each one loops on its own, which gives
polymeters for free ("x.." against "x...").
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

Lane = Literal["kick", "snare", "hat", "open_hat", "perc"]
LANES: tuple[str, ...] = ("kick", "snare", "hat", "open_hat", "perc")

VELOCITY = {"X": 1.0, "x": 0.75, "o": 0.35, ".": 0.0}

# synthdef and base parameters for each lane
LANE_VOICES: dict[str, tuple[str, dict[str, float]]] = {
    "kick": ("mcp_kick", {"amp": 0.6}),
    "snare": ("mcp_snare", {"amp": 0.45}),
    "hat": ("mcp_hat", {"amp": 0.22, "decay": 0.05}),
    "open_hat": ("mcp_hat", {"amp": 0.2, "decay": 0.3, "freq": 6500}),
    "perc": ("mcp_blip", {"amp": 0.18, "freq": 1600}),
}


@dataclass
class DrumPattern:
    lanes: dict[str, str]
    swing: float = 0.0  # 0 = straight, 0.33 = triplet shuffle on off-beat 16ths
    steps: int = field(init=False)

    def __post_init__(self) -> None:
        if not self.lanes:
            raise ValueError("a drum pattern needs at least one lane")
        for lane, steps in self.lanes.items():
            if lane not in LANES:
                raise ValueError(f"unknown drum lane {lane!r}; lanes: {', '.join(LANES)}")
            if not steps or set(steps) - set(VELOCITY):
                raise ValueError(f"lane {lane!r} must be a non-empty string of X x o . characters, got {steps!r}")
        self.steps = max(len(s) for s in self.lanes.values())

    def hits(self, step: int) -> list[tuple[str, float]]:
        """(lane, velocity) for every hit at an absolute step index."""
        hits = []
        for lane, steps in self.lanes.items():
            velocity = VELOCITY[steps[step % len(steps)]]
            if velocity:
                hits.append((lane, velocity))
        return hits

    def copy(self) -> DrumPattern:
        return DrumPattern(dict(self.lanes), self.swing)


PatternName = Literal["four_on_floor", "breakbeat", "shuffle", "half_time", "two_step"]

PATTERNS: dict[str, DrumPattern] = {
    "four_on_floor": DrumPattern(
        {
            "kick": "X...x...X...x...",
            "snare": "....X.......X...",
            "hat": "o.x.o.x.o.x.o.x.",
            "open_hat": "..o...o...o...o.",
        }
    ),
    "breakbeat": DrumPattern({"kick": "X.x.......xx....", "snare": "....X..o.o..X..o", "hat": "x.x.x.x.x.x.x.x."}),
    "shuffle": DrumPattern(
        {"kick": "X.....x.x.......", "snare": "....X.......X...", "hat": "x.ox.ox.x.ox.ox."}, swing=0.33
    ),
    "half_time": DrumPattern({"kick": "X.......x.x.....", "snare": "........X.......", "hat": "x.x.x.x.x.x.x.x."}),
    "two_step": DrumPattern({"kick": "X.........x.....", "snare": "....X.......X...", "hat": "x.xxx.x.x.xxx.x."}),
}


def random_pattern(rng: random.Random, steps: int = 16) -> DrumPattern:
    """A random but playable pattern: kick on the downbeat, backbeat-leaning snare, busy hats."""

    def lane(weights: dict[str, float], force: dict[int, str] | None = None) -> str:
        chars = rng.choices(list(weights), list(weights.values()), k=steps)
        for index, char in (force or {}).items():
            chars[index % steps] = char
        return "".join(chars)

    return DrumPattern(
        {
            "kick": lane({"x": 0.25, ".": 0.75}, {0: "X"}),
            "snare": lane({"o": 0.15, ".": 0.85}, {4: "X", 12: "X"}),
            "hat": lane({"x": 0.55, "o": 0.25, ".": 0.2}),
        },
        swing=rng.choice([0.0, 0.0, 0.15, 0.33]),
    )


def mutate(pattern: DrumPattern, rng: random.Random, amount: float) -> DrumPattern:
    """Flip some steps; `amount` 0..1 is roughly the share of steps that change per lane."""
    lanes = {}
    for name, steps in pattern.lanes.items():
        chars = list(steps)
        for i in range(len(chars)):
            # keep the kick's downbeat as an anchor so evolved grooves stay danceable
            if (name == "kick" and i == 0) or rng.random() >= amount:
                continue
            chars[i] = rng.choice("xo") if chars[i] == "." else "."
        lanes[name] = "".join(chars)
    return DrumPattern(lanes, pattern.swing)


def step_time(step: int, step_duration: float, swing: float) -> float:
    """Onset of a 16th-note step, delaying every off-beat 16th by `swing` of a step."""
    return step * step_duration + (swing * step_duration if step % 2 else 0.0)
