"""Turn musical requests into timed synth events.

Everything here is pure: functions take parameters (and a seeded RNG where
randomness is involved) and return a :class:`Phrase`, a time-ordered stream of
:class:`Event` objects. Nothing touches the network, so it is all unit-testable;
:mod:`supercollidermcp.engine` turns events into scheduled OSC bundles.
"""

from __future__ import annotations

import math
import random
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from typing import Literal

from pydantic import BaseModel, Field

from . import patterns as pt
from .theory import SCALES, midi_to_freq, note_name, parse_chord, parse_note, scale_note, split_symbols

EventKind = Literal["source", "lfo", "fx"]


@dataclass(frozen=True)
class Event:
    """Start synth `synth` with `params`, `time` seconds after the phrase starts."""

    time: float
    synth: str
    params: dict[str, float | int | str]
    kind: EventKind = "source"


@dataclass
class Phrase:
    events: Iterable[Event]  # in time order; may be a lazy generator
    duration: float  # seconds until the last sound has died away
    summary: str
    details: list[str] = field(default_factory=list)


# ---- synth voices ----------------------------------------------------------

SynthType = Literal["sine", "saw", "square", "noise", "fm", "pad", "pluck"]
FILTER_SYNTHS = frozenset({"saw", "square", "pad", "pluck"})

# default (attack, release) and a loudness trim so synth types sound roughly equally loud
_VOICE: dict[str, tuple[float, float, float]] = {
    "sine": (0.01, 0.15, 0.8),
    "saw": (0.01, 0.2, 1.2),
    "square": (0.01, 0.2, 1.0),
    "noise": (0.01, 0.2, 1.2),
    "fm": (0.005, 0.4, 0.8),
    "pad": (0.6, 1.5, 1.0),
    "pluck": (0.001, 0.3, 0.9),
}
BASE_AMP = 0.7  # amplitude of one voice at volume 1.0 (before the per-synth trim)


def synthdef(synth: str) -> str:
    return f"mcp_{synth}"


def note(
    time: float,
    synth: str,
    freq: float,
    length: float,
    volume: float,
    pan: float = 0.0,
    legato: float = 0.9,
    attack: float | None = None,
    release: float | None = None,
    **extra: float,
) -> Event:
    """One pitched note held for `length * legato` seconds, then released.

    `attack` and `release` default to the synth's own envelope (the attack is
    shortened so that it never takes more than 40% of a short note).
    """
    default_attack, default_release, trim = _VOICE[synth]
    hold = max(0.005, length * legato)
    attack = min(default_attack if attack is None else attack, hold * 0.4 if attack is None else hold)
    if release is None:
        release = min(default_release, max(0.05, length))
    params: dict[str, float | int | str] = {
        "freq": freq,
        "amp": BASE_AMP * volume * trim,
        "pan": max(-1.0, min(1.0, pan)),
        "attack": attack,
        "sustain": hold - attack,
        "release": release,
    }
    if synth == "pluck":
        params["decay"] = max(0.5, length * 2)
    params.update(extra)
    return Event(time, synthdef(synth), params)


def release_of(synth: str) -> float:
    return _VOICE[synth][1]


# ---- effects ---------------------------------------------------------------


class Effects(BaseModel):
    """Effect chain applied to everything one tool call plays. All amounts are 0..1; 0 = off."""

    reverb: float = Field(0.0, ge=0, le=1, description="Reverb amount")
    delay: float = Field(0.0, ge=0, le=1, description="Echo amount")
    delay_time: float | None = Field(
        None, ge=0.01, le=2, description="Echo time in seconds (default: 3/4 of a beat, or 0.375 s)"
    )
    distortion: float = Field(0.0, ge=0, le=1, description="Saturation / overdrive amount")
    filter: float = Field(0.0, ge=0, le=1, description="Low-pass darkening: 0 = open, 1 = very dark")

    def active(self) -> bool:
        return any((self.reverb, self.delay, self.distortion, self.filter))

    def tail(self) -> float:
        """Seconds the effect keeps sounding after the last note ends."""
        return max(0.3, 4.0 if self.reverb else 0.0, 3.5 if self.delay else 0.0)

    def describe(self) -> str:
        parts = [
            f"{name} {value:.2f}"
            for name in ("reverb", "delay", "distortion", "filter")
            if (value := getattr(self, name))
        ]
        return ", ".join(parts)


def with_effects(phrase: Phrase, effects: Effects | None, bus: int, beat: float | None = None) -> Phrase:
    """Route a phrase's sources to private bus `bus` and add an fx synth that plays it out."""
    if effects is None or not effects.active():
        return phrase
    delay_time = effects.delay_time or (beat * 0.75 if beat else 0.375)
    total = phrase.duration + effects.tail()
    fx = Event(
        0.0,
        "mcp_fx",
        {
            "in": bus,
            "out": 0,
            "sustain": total,
            "reverb": effects.reverb,
            "room": 0.6 + 0.35 * effects.reverb,
            "delay": effects.delay * 0.7,
            "delaytime": delay_time,
            "decaytime": 1.0 + 4.0 * effects.delay,
            "distortion": effects.distortion,
            # 0 -> 20 kHz (open), 1 -> 200 Hz, exponentially
            "cutoff": 20000.0 * (0.01**effects.filter),
        },
        kind="fx",
    )

    def events() -> Iterator[Event]:
        yield fx
        for event in phrase.events:
            yield replace(event, params={**event.params, "out": bus}) if event.kind == "source" else event

    summary = f"{phrase.summary} with {effects.describe()}"
    return Phrase(events(), total, summary, phrase.details)


# ---- tools -----------------------------------------------------------------


def example() -> Phrase:
    """A short FM chime arpeggio: C5 E5 G5 B5."""
    notes = [72, 76, 79, 83]
    events = [
        note(i * 0.18, "fm", midi_to_freq(m), 1.2 - i * 0.15, 0.3, pan=-0.3 + 0.2 * i, ratio=3.5, index=2)
        for i, m in enumerate(notes)
    ]
    return Phrase(events, 0.54 + 1.2 + release_of("fm"), "a test chime (C E G B)")


def single_note(synth: str, freq: float, duration: float, volume: float) -> Phrase:
    event = note(0.0, synth, freq, duration, volume, legato=1.0)
    return Phrase([event], duration + release_of(synth), f"one {synth} note at {freq:.1f} Hz for {duration:g} s")


def melody(
    rng: random.Random,
    scale: str,
    root: int,
    tempo: float,
    length: int,
    synth: str,
    volume: float,
) -> Phrase:
    """A random walk over the scale that favours steps over leaps and resolves to the tonic."""
    beat = 60.0 / tempo
    size = len(SCALES[scale])
    moves, weights = [-2, -1, 1, 2, -3, 3, 0, 4, -4], [3, 5, 5, 3, 1.2, 1.2, 1, 0.4, 0.4]
    durations, duration_weights = [0.25, 0.5, 1.0, 1.5, 2.0], [0.1, 0.45, 0.3, 0.08, 0.07]

    degree, t, events, names = 0, 0.0, [], []
    for i in range(length):
        last = i == length - 1
        if last:
            degree = round(degree / size) * size  # resolve to the nearest tonic
        elif i:
            degree += rng.choices(moves, weights)[0]
            if not -size <= degree <= 2 * size:  # bounce off the edges of a three-octave range
                degree = max(-size, min(2 * size, degree)) - (2 if degree > 0 else -2)
        beats = 2.0 if last else rng.choices(durations, duration_weights)[0]
        midi = scale_note(root, scale, degree)
        events.append(note(t, synth, midi_to_freq(midi), beats * beat, volume, pan=rng.uniform(-0.3, 0.3)))
        names.append(note_name(midi))
        t += beats * beat

    key = f"{note_name(root)[:-1]} {scale.replace('_', ' ')}"
    summary = f"a melody of {length} notes in {key} at {tempo:g} BPM on {synth}"
    return Phrase(events, t + release_of(synth), summary, [" ".join(names)])


_TOKEN_RE = re.compile(r"^(?P<pitch>[A-Ga-g][#b]{0,2}\d?|\.|[rR])(?P<mods>[_+]*)(?::(?P<beats>\d+(?:\.\d+)?))?$")


def parse_sequence(text: str) -> list[tuple[int | None, float]]:
    """Parse 'C4 E4_ G4_ . C5+' into (midi or None for a rest, length in beats).

    `_` halves a note, `+` doubles it, `:1.5` sets an explicit length in beats,
    `.` or `r` is a rest. Notes are separated by spaces, commas or dashes.
    """
    steps: list[tuple[int | None, float]] = []
    for token in split_symbols(text):
        match = _TOKEN_RE.match(token)
        if not match:
            raise ValueError(f"cannot parse {token!r} in sequence; use notes like C4, F#3_, Bb2+, G4:1.5 or . for rest")
        pitch, mods, beats = match.group("pitch"), match.group("mods"), match.group("beats")
        length = float(beats) if beats else 2.0 ** (mods.count("+") - mods.count("_"))
        steps.append((None if pitch in (".", "r", "R") else parse_note(pitch), length))
    if not steps:
        raise ValueError("the sequence is empty")
    return steps


def sequence(steps: list[tuple[int | None, float]], synth: str, tempo: float, repeats: int, volume: float) -> Phrase:
    beat = 60.0 / tempo
    events, t = [], 0.0
    for _ in range(repeats):
        for midi, beats in steps:
            if midi is not None:
                events.append(note(t, synth, midi_to_freq(midi), beats * beat, volume, legato=0.95))
            t += beats * beat
    played = " ".join("." if m is None else note_name(m) for m, _ in steps)
    return Phrase(
        events, t + release_of(synth), f"a {len(steps)}-step sequence x{repeats} at {tempo:g} BPM on {synth}", [played]
    )


LfoTarget = Literal["frequency", "amplitude", "filter", "pan"]
LfoWaveform = Literal["sine", "triangle", "square", "random"]
_LFO_SHAPES = {"sine": 0, "triangle": 1, "square": 2, "random": 3}


def lfo(
    target: str,
    rate: float,
    depth: float,
    waveform: str,
    duration: float,
    freq: float,
    synth: str,
    control_bus: int,
    volume: float,
) -> Phrase:
    """A held note whose `target` control is driven by a server-side LFO on `control_bus`."""
    source = note(0.0, synth, freq, duration, volume, legato=1.0)
    amp = float(source.params["amp"])
    lo, hi, curve, control = {
        "frequency": (freq / 2**depth, freq * 2**depth, 1, "freq"),  # up to +-1 octave
        "amplitude": (amp * (1 - depth), amp, 0, "amp"),
        "filter": (200.0, 200.0 * 40**depth, 1, "cutoff"),  # 200 Hz .. 8 kHz
        "pan": (-depth, depth, 0, "pan"),
    }[target]
    modulator = Event(
        0.0,
        "mcp_lfo",
        {
            "out": control_bus,
            "rate": rate,
            "lo": lo,
            "hi": hi,
            "shape": _LFO_SHAPES[waveform],
            "curve": curve,
            "sustain": duration + release_of(synth),
        },
        kind="lfo",
    )
    source = replace(source, params={**source.params, control: f"c{control_bus}"})
    return Phrase(
        [modulator, source],
        duration + release_of(synth),
        f"a {synth} note at {freq:.1f} Hz with a {rate:g} Hz {waveform} LFO on {target} (depth {depth:g})",
    )


def layered(
    freq: float, layers: int, detune: float, width: float, synth: str, duration: float, volume: float
) -> Phrase:
    """Several detuned copies of one note spread across the stereo field."""
    events = []
    for i in range(layers):
        position = (i / (layers - 1)) * 2 - 1 if layers > 1 else 0.0  # -1 .. 1
        cents = position * detune * 50
        weight = 1.0 - 0.4 * abs(position)  # centre layers loudest
        events.append(
            note(
                0.0,
                synth,
                freq * 2 ** (cents / 1200),
                duration,
                volume * weight / math.sqrt(layers),
                pan=position * 0.8 * width,
                legato=1.0,
            )
        )
    return Phrase(
        events,
        duration + release_of(synth),
        f"{layers} {synth} layers at {freq:.1f} Hz, detuned +-{detune * 50:.0f} cents, for {duration:g} s",
    )


def granular(
    rng: random.Random,
    freq: float,
    density: float,
    grain_size: float,
    pitch_spread: float,
    duration: float,
    volume: float,
) -> Phrase:
    """A cloud of short sine grains. density 0..1 maps to 5..100 grains per second."""
    rate = 5 + 95 * density
    overlap = max(1.0, rate * grain_size)
    amp = 0.6 * volume / math.sqrt(overlap)

    def grains() -> Iterator[Event]:
        t = 0.0
        while t < duration:
            semitones = rng.uniform(-1, 1) * pitch_spread * 12
            yield Event(
                t,
                "mcp_grain",
                {
                    "freq": freq * 2 ** (semitones / 12),
                    "amp": amp * rng.uniform(0.6, 1.0),
                    "pan": rng.uniform(-0.8, 0.8),
                    "sustain": grain_size * rng.uniform(0.8, 1.2),
                },
            )
            t += rng.uniform(0.5, 1.5) / rate

    return Phrase(
        grains(),
        duration + grain_size * 1.2,
        f"a granular cloud around {freq:.1f} Hz, ~{rate:.0f} grains/s of {grain_size * 1000:.0f} ms, "
        f"for {duration:g} s",
    )


ChordStyle = Literal["pad", "staccato", "arpeggio", "power"]
_STYLE_SYNTH = {"pad": "pad", "staccato": "pluck", "arpeggio": "pluck", "power": "saw"}


def chord_progression(
    symbols: list[str],
    style: str,
    tempo: float,
    beats_per_chord: float,
    octave: int,
    synth: str | None,
    repeats: int,
    volume: float,
) -> Phrase:
    beat = 60.0 / tempo
    synth = synth or _STYLE_SYNTH[style]
    chords = [parse_chord(symbol, octave) for symbol in symbols]
    chord_len = beats_per_chord * beat
    events: list[Event] = []

    for index in range(len(chords) * repeats):
        start = index * chord_len
        notes = chords[index % len(chords)]
        if style == "power":
            notes = [notes[0], notes[0] + 7, notes[0] + 12]
        level = volume / math.sqrt(len(notes))
        spread = [((i / (len(notes) - 1)) - 0.5) if len(notes) > 1 else 0.0 for i in range(len(notes))]

        if style in ("pad", "power"):
            events += [
                note(start, synth, midi_to_freq(m), chord_len, level, pan=p, legato=1.0)
                for m, p in zip(notes, spread, strict=True)
            ]
        elif style == "staccato":
            for b in range(max(1, int(beats_per_chord))):
                events += [
                    note(start + b * beat, synth, midi_to_freq(m), beat * 0.3, level, pan=p, legato=1.0)
                    for m, p in zip(notes, spread, strict=True)
                ]
        else:  # arpeggio: 8th notes up through the chord and its octave
            tones = [*notes, notes[0] + 12]
            for step in range(max(1, int(beats_per_chord * 2))):
                position = step % len(tones)
                events.append(
                    note(
                        start + step * beat / 2,
                        synth,
                        midi_to_freq(tones[position]),
                        beat / 2,
                        volume * 0.8,
                        pan=position / (len(tones) - 1) - 0.5,
                    )
                )

    events.sort(key=lambda e: e.time)
    total = len(chords) * repeats * chord_len
    voiced = [" ".join(note_name(m) for m in chord) for chord in chords]
    return Phrase(
        events,
        total + release_of(synth),
        f"{'-'.join(symbols)} as {style} on {synth} at {tempo:g} BPM" + (f", x{repeats}" if repeats > 1 else ""),
        [f"{s}: {v}" for s, v in zip(symbols, voiced, strict=True)],
    )


DrumKind = Literal["four_on_floor", "breakbeat", "shuffle", "half_time", "two_step", "random"]


def drum_hit(time: float, lane: str, velocity: float, volume: float, rng: random.Random) -> Event:
    synth, params = pt.LANE_VOICES[lane]
    amp = params["amp"] * velocity * volume * 2 * rng.uniform(0.9, 1.05)
    return Event(time, synth, {**params, "amp": amp, "pan": rng.uniform(-0.1, 0.1) if lane != "kick" else 0.0})


def drums(pattern: pt.DrumPattern, bars: int, tempo: float, volume: float, rng: random.Random, name: str) -> Phrase:
    step_len = 60.0 / tempo / 4
    total_steps = bars * 16
    events = [
        drum_hit(pt.step_time(step, step_len, pattern.swing), lane, velocity, volume, rng)
        for step in range(total_steps)
        for lane, velocity in pattern.hits(step)
    ]
    lanes = [f"{lane}: {steps}" for lane, steps in pattern.lanes.items()]
    swing = f", swing {pattern.swing:g}" if pattern.swing else ""
    return Phrase(events, total_steps * step_len + 0.5, f"{bars} bar(s) of {name} drums at {tempo:g} BPM{swing}", lanes)


# ---- soundscapes -----------------------------------------------------------

Mood = Literal["calm", "dark", "bright", "mysterious", "chaotic"]
PitchRange = Literal["low", "medium", "high", "full"]

_PITCH_RANGES = {"low": (40.0, 200.0), "medium": (100.0, 800.0), "high": (400.0, 3200.0), "full": (40.0, 3200.0)}


@dataclass(frozen=True)
class _Mood:
    base: tuple[float, float]
    ratios: tuple[float, ...]
    synths: tuple[str, ...]
    event_length: tuple[float, float]
    effects: Effects


MOODS: dict[str, _Mood] = {
    "calm": _Mood((110, 196), (1, 1.5, 2, 3, 4), ("pad", "sine", "fm"), (4, 10), Effects(reverb=0.7, delay=0.2)),
    "dark": _Mood((55, 98), (1, 1.2, 1.5, 2, 2.4), ("pad", "saw", "noise"), (4, 12), Effects(reverb=0.8, filter=0.45)),
    "bright": _Mood(
        (220, 392), (1, 1.25, 1.5, 2, 3, 4), ("pluck", "fm", "sine"), (1.5, 5), Effects(reverb=0.5, delay=0.35)
    ),
    "mysterious": _Mood(
        (82, 165), (1, 1.414, 1.7, 2.3, 3.3), ("fm", "pad", "sine"), (4, 12), Effects(reverb=0.85, delay=0.25)
    ),
    "chaotic": _Mood(
        (100, 400),
        (1, 1.3, 2.1, 2.7, 3.4, 5.1),
        ("fm", "noise", "square", "pluck"),
        (0.3, 3),
        Effects(reverb=0.4, delay=0.4, distortion=0.3),
    ),
}


def _fold(freq: float, lo: float, hi: float) -> float:
    """Move a frequency by octaves until it lies in [lo, hi], keeping its pitch class."""
    while freq < lo:
        freq *= 2
    while freq > hi:
        freq /= 2
    return max(freq, lo)


def ambient(
    rng: random.Random, duration: float, density: float, pitch_range: str, mood: str, volume: float
) -> tuple[Phrase, Effects]:
    """A drone plus overlapping swells; returns the phrase and the mood's default effects."""
    preset = MOODS[mood]
    lo, hi = _PITCH_RANGES[pitch_range]
    base = rng.uniform(*preset.base)
    drone_synth = "sine" if mood == "bright" else "pad"
    drone_freq = _fold(base, lo, hi)

    events = [
        note(
            0.0,
            drone_synth,
            drone_freq,
            duration,
            volume * 0.35,
            legato=1.0,
            attack=min(4.0, duration * 0.2),
            release=min(4.0, duration * 0.2),
        )
    ]
    if mood == "calm":
        events.append(
            note(
                0.0,
                "sine",
                _fold(base * 1.5, lo, hi),
                duration,
                volume * 0.18,
                legato=1.0,
                attack=min(6.0, duration * 0.3),
                release=min(4.0, duration * 0.2),
            )
        )

    count = max(2, round(duration / 10 * (1 + density * 7)))
    for start in sorted(rng.uniform(0, duration * 0.85) for _ in range(count)):
        synth = rng.choice(preset.synths)
        length = min(rng.uniform(*preset.event_length), duration - start)
        freq = _fold(base * rng.choice(preset.ratios) * rng.choice((0.5, 1, 1, 2)), lo, hi)
        swell = length * 0.35
        events.append(
            note(
                start,
                synth,
                freq,
                length,
                volume * 0.3 / math.sqrt(1 + density * 2),
                pan=rng.uniform(-0.8, 0.8),
                legato=1.0,
                attack=swell if synth != "pluck" else 0.001,
                release=swell,
            )
        )

    return (
        Phrase(
            events,
            duration + 4.0,
            f"a {mood} ambient soundscape ({pitch_range} range, {count} events) "
            f"over a {drone_freq:.1f} Hz drone for {duration:g} s",
        ),
        preset.effects,
    )


RhythmStyle = Literal["minimal", "techno", "glitch", "jazz", "ambient"]


@dataclass(frozen=True)
class _RhythmStyle:
    lanes: dict[str, str] | None  # None = start from a random pattern
    fill: float  # chance that a written hit is played
    variation: float  # chance per bar that the pattern mutates
    accents: float  # chance per step of a random blip
    swing: float


RHYTHM_STYLES: dict[str, _RhythmStyle] = {
    "minimal": _RhythmStyle(
        {"kick": "X...x...X...x...", "snare": "........x.......", "hat": "..o...o...o...o."}, 0.9, 0.15, 0.04, 0.05
    ),
    "techno": _RhythmStyle(
        {
            "kick": "X...X...X...X...",
            "snare": "....x.......x...",
            "hat": "o.x.o.x.o.x.o.x.",
            "open_hat": "..o...o...o...o.",
        },
        0.95,
        0.25,
        0.08,
        0.0,
    ),
    "glitch": _RhythmStyle(None, 0.8, 0.6, 0.35, 0.1),
    "jazz": _RhythmStyle(
        {"kick": "x.....o...x.....", "snare": "..o...o.x..o..o.", "hat": "x..x.xx..x.xx..."}, 0.85, 0.35, 0.05, 0.33
    ),
    "ambient": _RhythmStyle(
        {"kick": "x...............", "snare": "........o.......", "hat": "..o...o...o...o."}, 0.6, 0.15, 0.1, 0.1
    ),
}


def generative_rhythm(
    rng: random.Random, style: str, duration: float, tempo: float, intensity: float, volume: float
) -> Phrase:
    """Drums that mutate as they play; every 8 bars the groove snaps back to its starting point."""
    preset = RHYTHM_STYLES[style]
    scale = 0.7 + 0.6 * intensity
    fill = min(1.0, preset.fill * scale)
    variation, accents = min(1.0, preset.variation * scale), min(1.0, preset.accents * scale)
    base = pt.DrumPattern(dict(preset.lanes), preset.swing) if preset.lanes else pt.random_pattern(rng)
    if style == "glitch":
        base.lanes["perc"] = "x..x.x...x..x..."
    step_len = 60.0 / tempo / 4
    total_steps = max(16, int(duration / step_len))

    def events() -> Iterator[Event]:
        current = base.copy()
        for step in range(total_steps):
            if step % 16 == 0 and step:
                bar = step // 16
                current = (
                    base.copy()
                    if bar % 8 == 0
                    else (pt.mutate(current, rng, 0.08 + 0.2 * intensity) if rng.random() < variation else current)
                )
            t = pt.step_time(step, step_len, current.swing)
            for lane, velocity in current.hits(step):
                if rng.random() < fill:
                    yield drum_hit(t, lane, velocity, volume, rng)
            if rng.random() < accents * 0.25:
                yield Event(
                    t,
                    "mcp_blip",
                    {
                        "freq": rng.choice((800, 1600, 2400, 3200)),
                        "amp": 0.12 * volume * 2,
                        "pan": rng.uniform(-0.7, 0.7),
                        "decay": rng.choice((0.03, 0.08, 0.15)),
                    },
                )

    return Phrase(
        events(),
        total_steps * step_len + 0.5,
        f"an evolving {style} rhythm at {tempo:g} BPM for {total_steps * step_len:.1f} s (intensity {intensity:g})",
        [f"{lane}: {steps}" for lane, steps in base.lanes.items()],
    )
