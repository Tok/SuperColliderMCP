import pytest

from supercollidermcp.theory import (
    SCALES,
    midi_to_freq,
    note_name,
    parse_chord,
    parse_note,
    parse_pitch,
    scale_note,
    split_symbols,
)


@pytest.mark.parametrize(
    ("text", "midi"),
    [
        ("C4", 60),
        ("A4", 69),
        ("c4", 60),
        ("C#4", 61),
        ("Db4", 61),
        ("Bb2", 46),
        ("B#3", 60),
        ("Cb4", 59),
        ("C-1", 0),
        ("G9", 127),
        ("C10", None),
        ("E", 64),
        (" F#3 ", 54),
    ],
)
def test_parse_note(text, midi):
    if midi is None:
        with pytest.raises(ValueError):
            parse_note(text)
    else:
        assert parse_note(text) == midi


@pytest.mark.parametrize("bad", ["H4", "", "4C", "C#x", "do"])
def test_parse_note_rejects_garbage_instead_of_defaulting_to_a440(bad):
    with pytest.raises(ValueError, match="not a note name"):
        parse_note(bad)


def test_frequencies():
    assert midi_to_freq(69) == 440.0
    assert midi_to_freq(60) == pytest.approx(261.6256, abs=1e-3)
    assert parse_pitch("A4") == 440.0
    assert parse_pitch("440") == parse_pitch("440hz") == parse_pitch("440 Hz") == parse_pitch(440) == 440.0
    with pytest.raises(ValueError, match="audible"):
        parse_pitch("5")


def test_note_name_round_trip():
    for midi in range(0, 128):
        assert parse_note(note_name(midi)) == midi


def test_scales_wrap_octaves():
    assert scale_note(60, "major", 0) == 60
    assert scale_note(60, "major", 7) == 72
    assert scale_note(60, "major", -1) == 59
    assert scale_note(60, "minor_pentatonic", 5) == 72
    assert all(intervals[0] == 0 and max(intervals) < 12 for intervals in SCALES.values())


@pytest.mark.parametrize(
    ("symbol", "names"),
    [
        ("C", ["C4", "E4", "G4"]),
        ("Am7", ["A3", "C4", "E4", "G4"]),  # A is voiced below C so progressions stay in one register
        ("F#m", ["F#4", "A4", "C#5"]),
        ("Bbmaj7", ["A#3", "D4", "F4", "A4"]),
        ("Ddim", ["D4", "F4", "G#4"]),
        ("Gsus4", ["G3", "C4", "D4"]),
        ("E5", ["E4", "B4"]),
        ("C/E", ["E3", "C4", "E4", "G4"]),
        ("CMaj7", ["C4", "E4", "G4", "B4"]),
    ],
)
def test_parse_chord(symbol, names):
    assert [note_name(n) for n in parse_chord(symbol)] == names


@pytest.mark.parametrize("bad", ["Xyz", "Cfoo", "c", "C/H"])
def test_parse_chord_rejects_unknown(bad):
    with pytest.raises(ValueError):
        parse_chord(bad)


def test_split_symbols():
    assert split_symbols("C-G-Am-F") == ["C", "G", "Am", "F"]
    assert split_symbols(" C  G/B, Am | F ") == ["C", "G/B", "Am", "F"]
