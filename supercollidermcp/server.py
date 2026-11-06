"""MCP tools. Each tool validates its input, composes a Phrase and hands it to the Engine."""

from __future__ import annotations

import os
import random
from collections.abc import Callable
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field

from . import __version__
from . import compose as c
from . import patterns as pt
from .engine import Engine, Playback
from .osc import SCClient, SCError
from .theory import ScaleName, parse_note, parse_pitch, split_symbols

INSTRUCTIONS = """\
Make sound with a running SuperCollider server (scsynth) over OSC.

- Every play tool returns immediately; the sound is scheduled on the server and plays in
  the background. Calls overlap, so you can layer drums, chords and a melody by calling
  several tools in a row. The result says how long the sound lasts.
- Call stop_all to silence everything at once. Call server_status to check the connection.
- Notes are names like C4, F#3 or Bb2 (C4 = middle C), or frequencies like "440" / "440hz".
- Generative tools accept a seed; the result reports the seed used, so a result you like
  can be played again exactly.
- Most tools take an optional `effects` object: reverb, delay, distortion, filter (0..1).
"""

PLAY = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)

Volume = Annotated[float, Field(ge=0, le=1, description="Loudness, 0..1")]
Tempo = Annotated[float, Field(ge=30, le=300, description="Beats per minute")]
Seed = Annotated[int | None, Field(description="Random seed for a reproducible result; omit for a new one")]
EffectsArg = Annotated[c.Effects | None, Field(description="Optional effect chain")]


def config_from_env() -> tuple[str, int]:
    return os.environ.get("SC_HOST", "127.0.0.1"), int(os.environ.get("SC_PORT", "57110"))


def _rng(seed: int | None) -> tuple[random.Random, int]:
    seed = random.randrange(2**31) if seed is None else seed
    return random.Random(seed), seed


def create_server(engine: Engine | None = None) -> MCPServer:
    if engine is None:
        engine = Engine(SCClient(*config_from_env()))

    mcp = MCPServer(
        "supercollider",
        title="SuperCollider",
        version=__version__,
        instructions=INSTRUCTIONS,
        website_url="https://github.com/Tok/SuperColliderMCP",
    )

    async def start(
        build: Callable[[], c.Phrase],
        effects: c.Effects | None = None,
        beat: float | None = None,
        seed: int | None = None,
    ) -> str:
        try:
            phrase = build()  # validate the request before touching the server
            await engine.ensure_ready()
        except (ValueError, SCError) as exc:
            raise ToolError(str(exc)) from exc
        phrase = c.with_effects(phrase, effects, engine.audio_bus(), beat)
        return _report(phrase, engine.play(phrase), seed)

    def pitch(value: str) -> float:
        try:
            return parse_pitch(value)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

    # ---- utility -----------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    async def server_status() -> str:
        """Check the connection to SuperCollider and show load, playing sounds and recent errors."""
        client = engine.client
        try:
            status = await engine.ensure_ready()
        except SCError as exc:
            return str(exc)
        version = await client.version()
        lines = [
            f"Connected to scsynth {version or '(unknown version)'} at {client.address}",
            f"Sample rate {status.nominal_sample_rate:g} Hz, CPU {status.avg_cpu:.1f}% (peak {status.peak_cpu:.1f}%)",
            f"{status.synths} synths, {status.groups} groups, {status.synthdefs} SynthDefs loaded",
        ]
        active = engine.active()
        lines.append(f"{len(active)} playback(s) running" + (":" if active else ""))
        lines += [f"  #{p.id} {p.summary} ({p.remaining():.1f} s left)" for p in active]
        if client.recent_errors:
            lines.append("Recent server errors:")
            lines += [f"  {error}" for error in list(client.recent_errors)[-5:]]
        return "\n".join(lines)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True))
    async def stop_all() -> str:
        """Immediately silence every sound started by this server and cancel scheduled playback."""
        stopped = await engine.stop_all()
        return f"Stopped {stopped} playback(s); all voices freed."

    @mcp.tool(annotations=PLAY)
    async def play_example_osc() -> str:
        """Play a short test chime to check that sound comes out."""
        return await start(c.example)

    # ---- single sounds -----------------------------------------------------

    @mcp.tool(annotations=PLAY)
    async def play_synth(
        synth_type: c.SynthType = "sine",
        note: Annotated[str, Field(description="Note name (C4, G#3) or frequency ('440')")] = "A4",
        duration: Annotated[float, Field(ge=0.05, le=30, description="Seconds")] = 2.0,
        volume: Volume = 0.5,
        effects: EffectsArg = None,
    ) -> str:
        """Play one note on a synthesizer: sine, saw, square, noise (band-passed), fm, pad or pluck."""
        freq = pitch(note)
        return await start(lambda: c.single_note(synth_type, freq, duration, volume), effects)

    @mcp.tool(annotations=PLAY)
    async def create_layered_synth(
        base_note: Annotated[str, Field(description="Note name or frequency")] = "C3",
        num_layers: Annotated[int, Field(ge=1, le=8, description="Number of detuned voices")] = 3,
        detune: Annotated[float, Field(ge=0, le=1, description="Detune spread; 1 = +-50 cents")] = 0.3,
        stereo_width: Annotated[float, Field(ge=0, le=1, description="How far layers spread left/right")] = 1.0,
        synth: c.SynthType = "saw",
        duration: Annotated[float, Field(ge=0.5, le=30, description="Seconds")] = 5.0,
        volume: Volume = 0.5,
        effects: EffectsArg = None,
    ) -> str:
        """Play a thick unison sound made of several detuned copies of one note."""
        freq = pitch(base_note)
        return await start(lambda: c.layered(freq, num_layers, detune, stereo_width, synth, duration, volume), effects)

    @mcp.tool(annotations=PLAY)
    async def create_lfo_modulation(
        target_param: c.LfoTarget = "frequency",
        rate: Annotated[float, Field(ge=0.01, le=30, description="LFO speed in Hz")] = 0.5,
        depth: Annotated[float, Field(ge=0, le=1, description="Modulation depth")] = 0.5,
        waveform: c.LfoWaveform = "sine",
        duration: Annotated[float, Field(ge=1, le=60, description="Seconds")] = 10.0,
        note: Annotated[str, Field(description="Note name or frequency")] = "A3",
        synth: c.SynthType = "saw",
        volume: Volume = 0.5,
        effects: EffectsArg = None,
    ) -> str:
        """Hold a note while a low-frequency oscillator sweeps its pitch, volume, filter or stereo position.

        Depth 1 means +-1 octave for frequency, full fade for amplitude, 200 Hz..8 kHz for the
        filter (needs saw, square, pad or pluck), and hard left/right for pan.
        """
        if target_param == "filter" and synth not in c.FILTER_SYNTHS:
            raise ToolError(f"the {synth} synth has no filter; use one of {', '.join(sorted(c.FILTER_SYNTHS))}")
        freq = pitch(note)
        bus = engine.control_bus()
        return await start(
            lambda: c.lfo(target_param, rate, depth, waveform, duration, freq, synth, bus, volume), effects
        )

    @mcp.tool(annotations=PLAY)
    async def create_granular_texture(
        source_note: Annotated[str, Field(description="Centre note or frequency")] = "A4",
        density: Annotated[float, Field(ge=0, le=1, description="0 = 5 grains/s, 1 = 100 grains/s")] = 0.5,
        grain_size: Annotated[float, Field(ge=0.005, le=0.5, description="Grain length in seconds")] = 0.08,
        pitch_spread: Annotated[float, Field(ge=0, le=1, description="Random pitch range; 1 = +-1 octave")] = 0.2,
        duration: Annotated[float, Field(ge=1, le=60, description="Seconds")] = 10.0,
        volume: Volume = 0.5,
        effects: EffectsArg = None,
        seed: Seed = None,
    ) -> str:
        """Play a shimmering cloud of many tiny sine grains scattered in pitch and stereo."""
        freq = pitch(source_note)
        rng, seed = _rng(seed)
        return await start(
            lambda: c.granular(rng, freq, density, grain_size, pitch_spread, duration, volume), effects, seed=seed
        )

    # ---- melody and harmony ------------------------------------------------

    @mcp.tool(annotations=PLAY)
    async def play_melody(
        scale: ScaleName = "major",
        tempo: Tempo = 120,
        root: Annotated[str | None, Field(description="Tonic such as D, F#3 or Bb4; random if omitted")] = None,
        notes: Annotated[int, Field(ge=2, le=128, description="Number of notes")] = 16,
        synth: c.SynthType = "pluck",
        volume: Volume = 0.5,
        effects: EffectsArg = None,
        seed: Seed = None,
    ) -> str:
        """Generate and play a melody that moves mostly stepwise through a scale and ends on the tonic."""
        rng, seed = _rng(seed)
        try:
            tonic = parse_note(root) if root else 60 + rng.randrange(12)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        return await start(lambda: c.melody(rng, scale, tonic, tempo, notes, synth, volume), effects, 60 / tempo, seed)

    @mcp.tool(annotations=PLAY)
    async def create_sequence(
        pattern: Annotated[
            str,
            Field(
                description="Notes separated by spaces or dashes, e.g. 'C4 E4 G4_ G4_ . C5+'. "
                "'_' halves a note, '+' doubles it, ':1.5' sets the length in beats, '.' is a rest"
            ),
        ],
        synth: c.SynthType = "sine",
        tempo: Tempo = 120,
        repeats: Annotated[int, Field(ge=1, le=16)] = 1,
        volume: Volume = 0.5,
        effects: EffectsArg = None,
    ) -> str:
        """Play a melody you write out note by note."""
        return await start(
            lambda: c.sequence(c.parse_sequence(pattern), synth, tempo, repeats, volume), effects, 60 / tempo
        )

    @mcp.tool(annotations=PLAY)
    async def create_chord_progression(
        progression: Annotated[
            str,
            Field(description="Chord symbols separated by dashes or spaces, e.g. 'Cmaj7-Am7-Dm7-G7' or 'C G/B Am F'"),
        ] = "C-G-Am-F",
        style: c.ChordStyle = "pad",
        tempo: Tempo = 90,
        duration_per_chord: Annotated[float, Field(ge=0.5, le=16, description="Length of each chord in beats")] = 4,
        octave: Annotated[int, Field(ge=1, le=7, description="Octave of the chord roots")] = 4,
        synth: Annotated[c.SynthType | None, Field(description="Override the style's default synth")] = None,
        repeats: Annotated[int, Field(ge=1, le=8)] = 1,
        volume: Volume = 0.5,
        effects: EffectsArg = None,
    ) -> str:
        """Play a chord progression as sustained pads, rhythmic stabs (staccato), 8th-note arpeggios or power chords.

        Understands major, m, 5, 6, m6, 7, maj7, m7, mmaj7, m7b5, dim, dim7, aug, sus2, sus4,
        7sus4, 9, maj9, m9, add9, madd9, add11 and slash chords such as C/E.
        """
        symbols = split_symbols(progression)
        if not symbols:
            raise ToolError("the progression is empty")
        return await start(
            lambda: c.chord_progression(symbols, style, tempo, duration_per_chord, octave, synth, repeats, volume),
            effects,
            60 / tempo,
        )

    # ---- rhythm ------------------------------------------------------------

    @mcp.tool(annotations=PLAY)
    async def create_drum_pattern(
        pattern_type: c.DrumKind = "four_on_floor",
        bars: Annotated[int, Field(ge=1, le=64, description="Number of 4/4 bars (16 steps each)")] = 2,
        tempo: Tempo = 120,
        swing: Annotated[
            float | None, Field(ge=0, le=0.5, description="Delay of off-beat 16ths; 0.33 = shuffle")
        ] = None,
        custom: Annotated[
            dict[pt.Lane, str] | None,
            Field(
                description="Your own pattern instead of pattern_type: lanes kick, snare, hat, open_hat, perc, "
                "one character per 16th step: X accent, x hit, o ghost, . rest. "
                "Example: {'kick': 'X...x...X...x...', 'snare': '....X.......X...'}"
            ),
        ] = None,
        volume: Volume = 0.5,
        effects: EffectsArg = None,
        seed: Seed = None,
    ) -> str:
        """Play a drum groove: four_on_floor, breakbeat, shuffle, half_time, two_step, random, or a custom pattern."""
        rng, seed = _rng(seed)
        try:
            if custom:
                pattern, name = pt.DrumPattern(dict(custom)), "custom"
            elif pattern_type == "random":
                pattern, name = pt.random_pattern(rng), "random"
            else:
                pattern, name = pt.PATTERNS[pattern_type].copy(), pattern_type.replace("_", " ")
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        if swing is not None:
            pattern.swing = swing
        return await start(lambda: c.drums(pattern, bars, tempo, volume, rng, name), effects, 60 / tempo, seed)

    @mcp.tool(annotations=PLAY)
    async def create_generative_rhythm(
        style: c.RhythmStyle = "minimal",
        duration: Annotated[float, Field(ge=4, le=300, description="Seconds")] = 20,
        tempo: Tempo = 120,
        intensity: Annotated[float, Field(ge=0, le=1, description="How busy and how changeable")] = 0.5,
        volume: Volume = 0.5,
        effects: EffectsArg = None,
        seed: Seed = None,
    ) -> str:
        """Play drums that keep mutating bar by bar (minimal, techno, glitch, jazz or ambient)."""
        rng, seed = _rng(seed)
        return await start(
            lambda: c.generative_rhythm(rng, style, duration, tempo, intensity, volume), effects, 60 / tempo, seed
        )

    # ---- soundscapes -------------------------------------------------------

    @mcp.tool(annotations=PLAY)
    async def create_ambient_soundscape(
        duration: Annotated[float, Field(ge=5, le=300, description="Seconds")] = 30,
        density: Annotated[float, Field(ge=0, le=1, description="How many sound events overlap")] = 0.5,
        pitch_range: c.PitchRange = "medium",
        mood: c.Mood = "calm",
        volume: Volume = 0.5,
        effects: Annotated[c.Effects | None, Field(description="Override the mood's own reverb/delay")] = None,
        seed: Seed = None,
    ) -> str:
        """Play an evolving ambient piece: a drone with slowly swelling, overlapping tones."""
        rng, seed = _rng(seed)
        phrase, mood_effects = c.ambient(rng, duration, density, pitch_range, mood, volume)
        return await start(lambda: phrase, effects or mood_effects, seed=seed)

    return mcp


def _report(phrase: c.Phrase, playback: Playback, seed: int | None) -> str:
    lines = [f"Playing {phrase.summary} ({phrase.duration:.1f} s, playback #{playback.id})."]
    lines += phrase.details
    if seed is not None:
        lines.append(f"seed={seed}")
    return "\n".join(lines)
