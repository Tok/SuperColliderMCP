"""Pitch, scale and chord helpers: the single source of truth for note names."""

from __future__ import annotations

import re
from typing import Literal, get_args

A4_MIDI = 69
A4_FREQ = 440.0

_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_ACCIDENTAL = {"#": 1, "♯": 1, "b": -1, "♭": -1}
_SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_NOTE_RE = re.compile(r"^([A-Ga-g])([#b♯♭]{0,2})(-?\d+)?$")
_HZ_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:hz)?$", re.IGNORECASE)

MIN_FREQ = 16.0
MAX_FREQ = 20000.0


def midi_to_freq(midi: float) -> float:
    return A4_FREQ * 2 ** ((midi - A4_MIDI) / 12)


def note_name(midi: int) -> str:
    """60 -> 'C4' (sharps are used for black keys)."""
    return f"{_SHARP_NAMES[midi % 12]}{midi // 12 - 1}"


def parse_note(text: str, default_octave: int = 4) -> int:
    """Parse a note name such as 'C4', 'F#3', 'Bb2' or 'e5' into a MIDI note number.

    The octave is optional ('C' means C4 by default). Middle C is C4 = 60.
    """
    match = _NOTE_RE.match(text.strip())
    if not match:
        raise ValueError(f"not a note name: {text!r} (expected something like C4, F#3 or Bb2)")
    letter, accidentals, octave = match.groups()
    pitch_class = _PITCH_CLASS[letter.upper()] + sum(_ACCIDENTAL[a] for a in accidentals)
    midi = (int(octave) if octave is not None else default_octave) * 12 + 12 + pitch_class
    if not 0 <= midi <= 127:
        raise ValueError(f"note out of range: {text!r}")
    return midi


def parse_pitch(value: str | float) -> float:
    """Return a frequency in Hz from a note name ('A4') or a frequency ('440', '440hz', 440.0)."""
    if isinstance(value, (int, float)):
        freq = float(value)
    else:
        text = value.strip()
        hz = _HZ_RE.match(text)
        freq = float(hz.group(1)) if hz else midi_to_freq(parse_note(text))
    if not MIN_FREQ <= freq <= MAX_FREQ:
        raise ValueError(f"frequency {freq:g} Hz is outside the audible range ({MIN_FREQ:g}-{MAX_FREQ:g} Hz)")
    return freq


# ---- scales ----------------------------------------------------------------

ScaleName = Literal[
    "major",
    "minor",
    "harmonic_minor",
    "melodic_minor",
    "dorian",
    "phrygian",
    "lydian",
    "mixolydian",
    "locrian",
    "pentatonic",
    "minor_pentatonic",
    "blues",
    "whole_tone",
    "chromatic",
]

SCALES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "locrian": (0, 1, 3, 5, 6, 8, 10),
    "pentatonic": (0, 2, 4, 7, 9),
    "minor_pentatonic": (0, 3, 5, 7, 10),
    "blues": (0, 3, 5, 6, 7, 10),
    "whole_tone": (0, 2, 4, 6, 8, 10),
    "chromatic": tuple(range(12)),
}
assert set(SCALES) == set(get_args(ScaleName))


def scale_note(root: int, scale: str, degree: int) -> int:
    """MIDI note for a scale degree; degrees wrap into higher or lower octaves."""
    intervals = SCALES[scale]
    octave, index = divmod(degree, len(intervals))
    return root + 12 * octave + intervals[index]


# ---- chords ----------------------------------------------------------------

_MAJOR, _MINOR = (0, 4, 7), (0, 3, 7)
CHORD_QUALITIES: dict[str, tuple[int, ...]] = {
    "": _MAJOR,
    "M": _MAJOR,
    "maj": _MAJOR,
    "m": _MINOR,
    "min": _MINOR,
    "5": (0, 7),
    "6": (0, 4, 7, 9),
    "m6": (0, 3, 7, 9),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "M7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "min7": (0, 3, 7, 10),
    "mmaj7": (0, 3, 7, 11),
    "m7b5": (0, 3, 6, 10),
    "dim": (0, 3, 6),
    "dim7": (0, 3, 6, 9),
    "aug": (0, 4, 8),
    "+": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "sus": (0, 5, 7),
    "7sus4": (0, 5, 7, 10),
    "9": (0, 4, 7, 10, 14),
    "maj9": (0, 4, 7, 11, 14),
    "m9": (0, 3, 7, 10, 14),
    "add9": (0, 4, 7, 14),
    "madd9": (0, 3, 7, 14),
    "add11": (0, 4, 7, 17),
}
_CHORD_RE = re.compile(r"^([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?$")


def parse_chord(symbol: str, octave: int = 4) -> list[int]:
    """Parse a chord symbol ('Am7', 'F#dim', 'C/E', 'Bbmaj9') into MIDI notes.

    Roots are kept within a fifth below to a tritone above C of `octave`, so a
    progression stays in one register instead of jumping up for A and B chords.
    A slash bass is placed below the chord.
    """
    match = _CHORD_RE.match(symbol.strip())
    quality = match.group(2) if match else None
    if quality is not None and quality not in CHORD_QUALITIES:
        # accept case variants such as "Maj7" or "MIN"
        quality = next((q for q in CHORD_QUALITIES if q.lower() == quality.lower() and q != "M"), None)
    if not match or quality is None:
        known = ", ".join(q or "(major)" for q in CHORD_QUALITIES)
        raise ValueError(f"unknown chord {symbol!r}; chord qualities: {known}")
    root = parse_note(match.group(1), default_octave=octave)
    if root % 12 > 6:  # G, G#, A, A#, B: voice below C rather than above
        root -= 12
    notes = [root + interval for interval in CHORD_QUALITIES[quality]]
    if bass := match.group(3):
        bass_class = parse_note(bass, default_octave=0) % 12
        notes.insert(0, root - ((root - bass_class) % 12 or 12))
    return notes


def split_symbols(text: str) -> list[str]:
    """Split a progression or sequence on dashes, commas, bars and whitespace."""
    return [token for token in re.split(r"[\s,|\-]+", text.strip()) if token]
