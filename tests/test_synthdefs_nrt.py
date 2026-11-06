"""Render every SynthDef with scsynth in non-realtime mode and inspect the audio.

No audio device is needed, so this runs in CI as long as scsynth is installed.
Skipped when scsynth is not found (set SCSYNTH=/path/to/scsynth to point at one,
and SC_PLUGINS=/path/to/plugins if the UGen plugins are not in the default place).
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import pytest
from pythonosc.osc_message_builder import OscMessageBuilder

from supercollidermcp.synthdefs import SYNTHDEF_DIR

SCSYNTH = os.environ.get("SCSYNTH") or shutil.which("scsynth")
pytestmark = pytest.mark.skipif(not SCSYNTH, reason="scsynth not installed")

SR = 48000


def msg(address: str, *args) -> bytes:
    builder = OscMessageBuilder(address)
    for arg in args:
        builder.add_arg(arg)
    return builder.build().dgram


def render(tmp_path: Path, timeline: list[tuple[float, list[bytes]]], length: float) -> list[tuple[float, float]]:
    """Render a score and return the stereo frames as floats in [-1, 1]."""
    load = [msg("/d_recv", p.read_bytes()) for p in sorted(SYNTHDEF_DIR.glob("*.scsyndef"))]
    entries = [(0.0, load), *[(t + 0.01, m) for t, m in timeline], (length, [msg("/c_set", 0, 0)])]

    score = b""
    for t, messages in entries:
        bundle = b"#bundle\x00" + struct.pack(">Q", int(t * 2**32))
        for m in messages:
            bundle += struct.pack(">i", len(m)) + m
        score += struct.pack(">i", len(bundle)) + bundle

    score_path, wav_path = tmp_path / "score.osc", tmp_path / "out.wav"
    score_path.write_bytes(score)
    cmd = [SCSYNTH, "-N", str(score_path), "_", str(wav_path), str(SR), "WAV", "int16", "-o", "2"]
    if plugins := os.environ.get("SC_PLUGINS"):
        cmd += ["-U", plugins]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAILURE" not in result.stdout, result.stdout

    with wave.open(str(wav_path)) as w:
        raw = w.readframes(w.getnframes())
    ints = struct.unpack(f"<{len(raw) // 2}h", raw)
    return [(ints[i] / 32768, ints[i + 1] / 32768) for i in range(0, len(ints), 2)]


def peak(frames, start: float = 0.0, end: float | None = None) -> float:
    a, b = int(start * SR), int(end * SR) if end is not None else len(frames)
    return max((max(abs(left), abs(right)) for left, right in frames[a:b]), default=0.0)


def rms(frames, start: float, end: float) -> float:
    window = frames[int(start * SR) : int(end * SR)]
    return math.sqrt(sum(left * left + right * right for left, right in window) / (2 * len(window)))


@pytest.mark.parametrize("name", ["sine", "saw", "square", "noise", "fm", "pad", "pluck"])
def test_pitched_sources_sound_and_end(tmp_path, name):
    frames = render(
        tmp_path,
        [
            (
                0.0,
                [
                    msg(
                        "/s_new",
                        f"mcp_{name}",
                        -1,
                        0,
                        0,
                        "freq",
                        220.0,
                        "amp",
                        0.3,
                        "attack",
                        0.01,
                        "sustain",
                        0.5,
                        "release",
                        0.2,
                    )
                ],
            )
        ],
        length=1.5,
    )
    assert 0.02 < peak(frames, 0.0, 0.8) < 0.99
    assert peak(frames, 0.9) < 1e-3, "envelope did not close"


@pytest.mark.parametrize("name", ["kick", "snare", "hat", "blip"])
def test_percussion_sounds_and_decays(tmp_path, name):
    frames = render(tmp_path, [(0.0, [msg("/s_new", f"mcp_{name}", -1, 0, 0)])], length=1.5)
    assert 0.02 < peak(frames, 0.0, 0.5) < 0.99
    assert peak(frames, 1.0) < 1e-3


def test_grain(tmp_path):
    frames = render(tmp_path, [(0.0, [msg("/s_new", "mcp_grain", -1, 0, 0, "sustain", 0.05, "amp", 0.3)])], 0.5)
    assert 0.02 < peak(frames, 0.0, 0.1) < 0.99
    assert peak(frames, 0.12) < 1e-3


def test_private_bus_is_silent_without_fx(tmp_path):
    frames = render(tmp_path, [(0.0, [msg("/s_new", "mcp_sine", -1, 0, 0, "out", 512, "sustain", 0.5)])], 1.0)
    assert peak(frames) < 1e-4


def test_fx_routes_private_bus_and_adds_reverb_tail(tmp_path):
    source = msg("/s_new", "mcp_sine", -1, 0, 0, "out", 512, "amp", 0.3, "sustain", 0.3, "release", 0.01)
    fx = msg("/s_new", "mcp_fx", -1, 1, 0, "in", 512, "out", 0, "sustain", 2.5, "reverb", 0.8, "room", 0.9)
    frames = render(tmp_path, [(0.0, [source, fx])], length=3.0)
    assert peak(frames, 0.0, 0.3) > 0.02
    assert rms(frames, 0.5, 1.0) > 1e-3, "no reverb tail after the source ended"
    assert peak(frames, 2.7) < 1e-4, "fx synth did not end"


def test_lfo_drives_mapped_control(tmp_path):
    lfo = msg("/s_new", "mcp_lfo", -1, 0, 0, "out", 8192, "rate", 2.0, "lo", 0.0, "hi", 0.4, "shape", 2, "sustain", 2.0)
    sine = msg("/s_new", "mcp_sine", -1, 1, 0, "amp", "c8192", "sustain", 2.0)
    frames = render(tmp_path, [(0.0, [lfo, sine])], length=2.5)
    # square LFO at 2 Hz: high for the first 0.25 s of each 0.5 s cycle, then silent
    assert rms(frames, 0.55, 0.7) > 0.05
    assert rms(frames, 0.8, 0.95) < 0.01


def test_limiter_keeps_peaks_below_ceiling(tmp_path):
    loud = [
        msg("/s_new", "mcp_saw", -1, 0, 0, "freq", 110.0 * (i + 1), "amp", 1.0, "sustain", 0.5, "cutoff", 18000)
        for i in range(8)
    ]
    limiter = msg("/s_new", "mcp_limiter", -1, 1, 0)
    frames = render(tmp_path, [(0.0, [*loud, limiter])], length=1.0)
    assert 0.5 < peak(frames) <= 0.96
