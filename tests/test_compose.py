import random

import pytest

from supercollidermcp import compose as c
from supercollidermcp import patterns as pt


def events(phrase: c.Phrase) -> list[c.Event]:
    return list(phrase.events)


def end_of(event: c.Event) -> float:
    p = event.params
    return event.time + float(p.get("attack", 0)) + float(p.get("sustain", 0)) + float(p.get("release", 0))


def assert_well_formed(phrase: c.Phrase) -> list[c.Event]:
    evs = events(phrase)
    assert evs, "phrase has no events"
    times = [e.time for e in evs]
    assert times == sorted(times), "events must be in time order"
    for e in evs:
        assert e.synth.startswith("mcp_")
        assert all(isinstance(v, (int, float, str)) for v in e.params.values())
        if "amp" in e.params and not isinstance(e.params["amp"], str):
            assert 0 <= e.params["amp"] <= 1.0
        if e.kind == "source" and "sustain" in e.params:
            assert end_of(e) <= phrase.duration + 1e-6, f"{e} outlasts the phrase ({phrase.duration})"
    return evs


def test_note_envelope_fits_length():
    e = c.note(1.0, "pad", 440, length=0.5, volume=0.5)
    assert e.params["attack"] <= 0.5 * 0.9 * 0.4 + 1e-9  # pad's slow attack is shortened for short notes
    assert e.params["attack"] + e.params["sustain"] == pytest.approx(0.45)


def test_single_note():
    evs = assert_well_formed(c.single_note("saw", 220, 2, 0.5))
    assert len(evs) == 1 and evs[0].synth == "mcp_saw" and evs[0].params["freq"] == 220


def test_melody_is_reproducible_and_resolves_to_tonic():
    a = c.melody(random.Random(42), "minor", 62, 120, 16, "pluck", 0.5)
    b = c.melody(random.Random(42), "minor", 62, 120, 16, "pluck", 0.5)
    evs = assert_well_formed(a)
    assert len(evs) == 16
    assert [e.params["freq"] for e in evs] == [e.params["freq"] for e in events(b)]
    assert a.details[0].split()[-1].rstrip("0123456789") == "D"
    assert "D minor" in a.summary


def test_parse_sequence():
    assert c.parse_sequence("C4 E4_ G4+ . r C5:1.5 D4__") == [
        (60, 1.0),
        (64, 0.5),
        (67, 2.0),
        (None, 1.0),
        (None, 1.0),
        (72, 1.5),
        (62, 0.25),
    ]
    assert c.parse_sequence("C4-E4-G4") == [(60, 1.0), (64, 1.0), (67, 1.0)]
    for bad in ["C4E4", "X4", "C4:abc", "   "]:
        with pytest.raises(ValueError):
            c.parse_sequence(bad)


def test_sequence_timing_and_repeats():
    phrase = c.sequence(c.parse_sequence("C4 . E4+"), "sine", 120, 2, 0.5)
    evs = assert_well_formed(phrase)
    assert [e.time for e in evs] == [0.0, 1.0, 2.0, 3.0]  # 0.5 s beats; the rest leaves a gap


def test_lfo_maps_control_to_bus():
    phrase = c.lfo("filter", 2.0, 1.0, "square", 4.0, 220.0, "saw", 8200, 0.5)
    modulator, source = assert_well_formed(phrase)
    assert modulator.kind == "lfo" and modulator.params["out"] == 8200
    assert modulator.params["lo"] == 200 and modulator.params["hi"] == pytest.approx(8000)
    assert source.params["cutoff"] == "c8200"


def test_layered_detune_and_spread():
    evs = assert_well_formed(c.layered(440, 3, 1.0, 1.0, "saw", 2, 0.5))
    freqs = [e.params["freq"] for e in evs]
    assert freqs[1] == 440 and freqs[0] < 440 < freqs[2]
    assert freqs[2] / 440 == pytest.approx(2 ** (50 / 1200))
    assert [e.params["pan"] for e in evs] == [-0.8, 0.0, 0.8]


def test_granular_handles_zero_pitch_spread():
    # v0.1 crashed with ZeroDivisionError here
    phrase = c.granular(random.Random(1), 440, 0.5, 0.05, 0.0, 2.0, 0.5)
    evs = assert_well_formed(phrase)
    assert {e.params["freq"] for e in evs} == {440}
    assert 80 < len(evs) < 130  # ~52 grains/s for 2 s


@pytest.mark.parametrize("style", ["pad", "staccato", "arpeggio", "power"])
def test_chord_progression_styles(style):
    phrase = c.chord_progression(["C", "Am", "F", "G7"], style, 120, 4, 4, None, 2, 0.5)
    evs = assert_well_formed(phrase)
    assert phrase.duration >= 2 * 4 * 2.0  # 2 repeats x 4 chords x 4 beats at 0.5 s
    if style == "pad":
        assert len(evs) == 2 * (3 + 3 + 3 + 4)
    if style == "arpeggio":
        assert len(evs) == 2 * 4 * 8


def test_drums_follow_pattern_and_swing():
    pattern = pt.DrumPattern({"kick": "x...", "hat": "xx"}, swing=0.5)
    evs = assert_well_formed(c.drums(pattern, 1, 120, 0.5, random.Random(0), "test"))
    step = 60 / 120 / 4
    kicks = [e.time for e in evs if e.synth == "mcp_kick"]
    hats = [e.time for e in evs if e.synth == "mcp_hat"]
    assert kicks == pytest.approx([0, 4 * step, 8 * step, 12 * step])
    assert hats[:2] == pytest.approx([0, 1.5 * step])  # off-beat 16th delayed by half a step


@pytest.mark.parametrize("style", list(c.RHYTHM_STYLES))
def test_generative_rhythm_is_lazy_and_reproducible(style):
    a = c.generative_rhythm(random.Random(5), style, 30, 128, 0.8, 0.5)
    b = c.generative_rhythm(random.Random(5), style, 30, 128, 0.8, 0.5)
    evs = assert_well_formed(a)
    assert [(e.time, e.synth) for e in evs] == [(e.time, e.synth) for e in events(b)]
    assert evs[-1].time < 30


@pytest.mark.parametrize("mood", list(c.MOODS))
def test_ambient_moods(mood):
    phrase, effects = c.ambient(random.Random(3), 40, 0.7, "medium", mood, 0.5)
    evs = assert_well_formed(phrase)
    assert len(evs) >= 3
    assert effects.active()
    assert all(100 / 2 <= e.params["freq"] <= 800 for e in evs)


def test_effects_routing():
    plain = c.single_note("sine", 440, 1, 0.5)
    assert c.with_effects(plain, None, 600) is plain
    assert c.with_effects(plain, c.Effects(), 600) is plain

    routed = c.with_effects(c.single_note("sine", 440, 1, 0.5), c.Effects(reverb=0.5, filter=1), 600, beat=0.5)
    fx, voice = events(routed)
    assert fx.kind == "fx" and fx.params["in"] == 600 and fx.params["out"] == 0
    assert fx.params["cutoff"] == pytest.approx(200)
    assert fx.params["delaytime"] == pytest.approx(0.375)
    assert voice.params["out"] == 600
    assert routed.duration == pytest.approx(1 + c.release_of("sine") + 4.0)
    assert "reverb 0.50" in routed.summary


def test_lfo_events_keep_their_control_bus_when_routed():
    phrase = c.lfo("pan", 1, 1, "sine", 2, 220, "saw", 9000, 0.5)
    modulator, voice = events(c.with_effects(phrase, c.Effects(delay=0.5), 700))[1:]
    assert modulator.params["out"] == 9000
    assert voice.params["out"] == 700


def test_patterns_validate():
    with pytest.raises(ValueError, match="lane"):
        pt.DrumPattern({"cowbell": "x..."})
    with pytest.raises(ValueError, match="characters"):
        pt.DrumPattern({"kick": "x-x-"})
    with pytest.raises(ValueError):
        pt.DrumPattern({})
    p = pt.DrumPattern({"kick": "x..", "hat": "x."})
    assert p.steps == 3
    assert p.hits(3) == [("kick", 0.75)]  # lanes loop independently


def test_mutate_keeps_downbeat():
    rng = random.Random(0)
    base = pt.PATTERNS["four_on_floor"]
    for _ in range(50):
        assert pt.mutate(base, rng, 1.0).lanes["kick"][0] == "X"
