# Changelog

## 0.2.1

- Listed in the official [MCP Registry](https://registry.modelcontextprotocol.io) as
  `io.github.Tok/supercollider-mcp`; each release now publishes there automatically after PyPI.
- README: install with `uvx supercollider-mcp`, PyPI and MCP Registry badges, MseeP badges removed.

## 0.2.0

A rewrite. Every tool now produces the sound it describes, and none of them block.

### Added

- Bundled SynthDefs: `sine`, `saw`, `square`, `noise`, `fm`, `pad`, `pluck`, `kick`, `snare`, `hat`, `blip`,
  `grain`, plus `mcp_fx` (distortion, low-pass, delay, reverb), `mcp_lfo` and an output limiter. They are
  uploaded to scsynth automatically, and the source is `supercollidermcp/synthdefs/synthdefs.scd`.
- `server_status` tool: connection check, CPU, running playbacks, recent scsynth errors.
- `stop_all` tool: silence everything and cancel scheduled notes.
- `seed` on every generative tool (the seed used is reported), so a result can be replayed exactly.
- Custom drum patterns as step strings (`X x o .`), five lanes, independent lane lengths, swing.
- Scales: harmonic/melodic minor, the church modes, minor pentatonic, whole tone, chromatic.
- Chords: 6, m6, mmaj7, m7b5, 7sus4, 9, maj9, m9, madd9 and slash chords (`G/B`).
- `supercollider-mcp` command (`uvx supercollider-mcp`), configurable with `--host`/`--port` or
  `SC_HOST`/`SC_PORT`.
- Test suite: unit tests, protocol tests against a fake scsynth, offline renders of every SynthDef with
  `scsynth -N`, and an end-to-end test against a live server. CI on Python 3.10–3.13.

### Changed

- Requires the current MCP SDK (`mcp>=2.3`) and Python 3.10+ (was 3.12+).
- Playback is scheduled on scsynth with timestamped OSC bundles, so tools return immediately and
  calls can overlap. Before, each call blocked the server for the whole sound.
- Tool parameters have real types, ranges and enums in their schemas (before, everything was a string),
  and `effects` is an object instead of a JSON string.
- Invalid notes, chords and patterns are reported as errors instead of silently becoming A440.
- `create_drum_pattern` takes `bars` (16 steps each) instead of `beats`, and steps are 16th notes. Before,
  every step lasted a whole beat, so grooves played four times too slow.
- `play_melody` makes stepwise melodies that resolve to the tonic (and takes `root`, `notes`, `synth`). It no
  longer appends an unrelated scale run.
- `create_chord_progression` keeps roots near middle C, and its `staccato` and `arpeggio` styles play on the
  beat and in 8th notes. New `octave`, `synth` and `repeats` parameters.
- `create_layered_synth`: `detune` 1.0 now means ±50 cents (it used to reach a full octave), and there is a
  new `stereo_width` parameter.
- `create_ambient_soundscape` events now actually overlap, and each mood has its own effects.
- `create_generative_rhythm` really evolves (patterns mutate bar by bar and snap back every 8 bars).

### Fixed

- `create_granular_texture` crashed with `pitch_spread=0`.
- `create_sequence` ignored its `synth` parameter and split undelimited input into single characters.
- Every "synth type" and effect was silently ignored, because all sounds used sclang's `default` SynthDef.
- Notes ended with a click (`/n_free` instead of an envelope release).
- Node IDs could collide between overlapping calls.

### Removed

- The `sc-osc` CLI (its entry point never worked).
- The duplicated helper modules (`melody.py`, `rhythm.py`, the old `osc.py`), which `server.py` never used.

## 0.1.1

- Pin `mcp<2`: mcp 2.0 renamed `FastMCP`, so fresh installs crashed on startup.

## 0.1.0

- Initial release.
