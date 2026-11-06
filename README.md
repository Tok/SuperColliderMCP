[![CI](https://github.com/Tok/SuperColliderMCP/actions/workflows/ci.yml/badge.svg)](https://github.com/Tok/SuperColliderMCP/actions/workflows/ci.yml)
[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/70ac07b9-ec05-4fec-9456-5c4331cdf994)

# SuperCollider MCP 🎛️

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets AI assistants make sound with
[SuperCollider](https://supercollider.github.io/). Ask for "a dark ambient drone with slow swells" or
"a breakbeat at 170 under a Cm7-Fm7 arpeggio" and it plays on your SuperCollider server.

- **Real synths and drums.** It ships its own SynthDefs (sine, saw, square, noise, FM, pad, Karplus-Strong
  pluck, kick, snare, hats, grains) plus an effect chain (distortion, low-pass, delay, reverb) and a safety
  limiter. Nothing depends on sclang's `default` synth or on sc3-plugins.
- **Sample-accurate timing.** Phrases are streamed to scsynth as timestamped OSC bundles, so every tool
  returns immediately. Calls can overlap, so you can layer drums, chords and melody.
- **Music-aware tools.** Melodies follow 14 scales, chords understand symbols like `Am7`, `Bbmaj9` and `G/B`,
  drum patterns are readable step strings the assistant can write itself, and generative tools take a
  `seed` so a result you like can be replayed exactly.
- **A panic button.** `stop_all` silences everything this server started.

## Requirements

- [SuperCollider](https://supercollider.github.io/downloads) 3.10 or newer (tested with 3.13). Only the
  audio server, `scsynth`, has to be running.
- [uv](https://docs.astral.sh/uv/), or any Python 3.10+ with pip.

## Quick start

**1. Install and boot SuperCollider.** Install it from the
[downloads page](https://supercollider.github.io/downloads) (or `brew install --cask supercollider` on
macOS, `sudo apt install supercollider` on Debian/Ubuntu), then boot the server:

- in the SuperCollider IDE: *Server → Boot Server* (or run `s.boot;`)
- or without the IDE: `scsynth -u 57110`

**2. Add the MCP server to your assistant.**

Claude Code:

```bash
claude mcp add supercollider -- uvx --from git+https://github.com/Tok/SuperColliderMCP@v0.2.0 supercollider-mcp
```

Claude Desktop, Cursor, Cline, Roo Code and other clients that use an `mcpServers` config:

```json
{
  "mcpServers": {
    "supercollider": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Tok/SuperColliderMCP@v0.2.0", "supercollider-mcp"]
    }
  }
}
```

This installs the v0.2.0 release straight from GitHub; `uvx` caches it, so later starts are quick. A PyPI
release (plain `uvx supercollider-mcp`) is on the way. To follow the latest unreleased code instead, drop the
`@v0.2.0`.

**3. Ask for something.** Start with "play a test sound" to check the connection, then try the prompts
below.

### Configuration

| Setting | Flag | Environment | Default |
| --- | --- | --- | --- |
| scsynth host | `--host` | `SC_HOST` | `127.0.0.1` |
| scsynth UDP port | `--port` | `SC_PORT` | `57110` |
| log level (stderr) | `--log-level` | | `WARNING` |

Flags go after the command name, for example
`"args": ["--from", "git+https://github.com/Tok/SuperColliderMCP@v0.2.0", "supercollider-mcp", "--port", "57111"]`.

## Tools

| Tool | What it does |
| --- | --- |
| `server_status` | Connection check: scsynth version, CPU, running playbacks, recent server errors |
| `stop_all` | Silence everything this server started and cancel scheduled notes |
| `play_example_osc` | A short test chime |
| `play_synth` | One note on `sine`, `saw`, `square`, `noise`, `fm`, `pad` or `pluck` |
| `create_layered_synth` | A thick unison: several detuned copies of one note spread in stereo |
| `create_lfo_modulation` | A held note with a server-side LFO on pitch, volume, filter or pan |
| `create_granular_texture` | A cloud of 5–100 tiny grains per second, scattered in pitch and space |
| `play_melody` | A generated melody in one of 14 scales that resolves to the tonic |
| `create_sequence` | A melody you spell out: `"C4 E4_ G4_ . C5+"` |
| `create_chord_progression` | Chord symbols as pads, staccato stabs, 8th-note arpeggios or power chords |
| `create_drum_pattern` | `four_on_floor`, `breakbeat`, `shuffle`, `half_time`, `two_step`, `random`, or your own |
| `create_generative_rhythm` | Drums that keep mutating: `minimal`, `techno`, `glitch`, `jazz`, `ambient` |
| `create_ambient_soundscape` | A drone with overlapping swells in a `calm`, `dark`, `bright`, `mysterious` or `chaotic` mood |

Most tools also take `volume` (0–1) and an optional `effects` object:

```json
{"reverb": 0.6, "delay": 0.3, "delay_time": 0.25, "distortion": 0.0, "filter": 0.2}
```

All amounts are 0–1, and 0 means off. `filter` darkens the sound with a low-pass filter. `delay_time` is in
seconds and defaults to three quarters of a beat.

**Notes** are names like `C4` (middle C), `F#3` or `Bb2`, or frequencies like `"440"` or `"440hz"`.

**Sequences** separate notes with spaces or dashes. `_` halves a note, `+` doubles it, `:1.5` sets its
length in beats, and `.` is a rest.

**Drum patterns** use one character per 16th note: `X` accent, `x` hit, `o` ghost note, `.` rest. Lanes
(`kick`, `snare`, `hat`, `open_hat`, `perc`) can have different lengths and loop independently:

```json
{"custom": {"kick": "X..x..X...x.....", "snare": "....X.......X..o", "hat": "x.x.x.x.x.x.x.x."}, "tempo": 92, "swing": 0.2}
```

### Things to try

- "Play a dorian melody in D on the pluck synth with some delay, then the same one an octave lower."
- "Give me two bars of breakbeat at 170 BPM, then layer an Am7-Dm7-G7-Cmaj7 arpeggio on top."
- "A mysterious ambient soundscape, 60 seconds, low register."
- "Sweep a saw's filter with a slow triangle LFO while a granular cloud shimmers around A5."
- "Write me a half-time drum pattern with ghost notes on the snare."

## How it works

```
assistant ──MCP (stdio)──▶ supercollider-mcp ──OSC/UDP──▶ scsynth ──▶ speakers
```

On first use the server checks that scsynth answers, uploads its SynthDefs (`/d_recv`) and creates its own
node group with a voice group, an effects group and a limiter. Node IDs sit far above the ranges sclang
uses, so your own SuperCollider work is not affected. If scsynth restarts, the setup runs again on the next
call.

Each tool call turns into a *phrase*: a time-ordered stream of synth events (`supercollidermcp/compose.py`,
pure Python). A background task sends each event about half a second ahead as an OSC bundle with an NTP
timetag, and scsynth starts it at exactly that time. Every synth frees itself when its envelope ends. When
a call asks for effects, its voices go to a private bus that one `mcp_fx` synth reads.

## Upgrading from 0.1

- Point your MCP config at the `uvx` command shown above. Old configs that run
  `mcp run path/to/server.py` still work through a small compatibility `server.py`.
- Sounds now come from real SynthDefs, so you no longer need sclang's `default` synth.
- Tools return right away instead of blocking until the sound ends.
- Some parameters changed meaning. `create_drum_pattern` takes `bars` (16 steps each) instead of `beats`.
  `effects` is an object instead of a JSON string. `detune` is now ±50 cents at 1.0 instead of up to an
  octave. The `sc-osc` command-line tool is gone.

See [CHANGELOG.md](CHANGELOG.md) for everything else.

## Troubleshooting

- **"No reply from the SuperCollider server…"**: scsynth is not running, or it listens on a different
  port. Boot it, or set `SC_PORT`.
- **Calls succeed but you hear nothing**: check that scsynth's outputs are connected to your sound card
  and that `server_status` shows synths while something plays.
- **Linux with PipeWire** (the default on current Ubuntu and Fedora): scsynth talks to JACK, so install
  PipeWire's JACK layer (`sudo apt install pipewire-jack`) and start SuperCollider through it:
  `pw-jack scide`, or `pw-jack scsynth -u 57110` without the IDE. Otherwise scsynth tries to start its
  own `jackd`, which conflicts with PipeWire.
- **`FAILURE IN SERVER /g_queryTree Group 2147480000 not found` in the post window** on first connect is
  expected: it is how the server notices that scsynth still needs to be set up.
- **Remote scsynth**: timetags use wall-clock time, so keep both machines' clocks in sync (NTP).

## Development

```bash
git clone https://github.com/Tok/SuperColliderMCP.git
cd SuperColliderMCP
uv sync
uv run pytest          # unit and protocol tests run anywhere
uv run ruff check . && uv run ruff format --check .
```

Some tests need SuperCollider:

- `tests/test_synthdefs_nrt.py` renders every SynthDef with `scsynth -N` (no audio device needed) and
  checks the audio. It runs automatically when `scsynth` is on `PATH`, or set `SCSYNTH=/path/to/scsynth`.
- `tests/test_live_server.py` runs every tool against a live server. Start a silent one with
  `scsynth -u 57199 -i 0 -o 0`, then run `SC_TEST_PORT=57199 uv run pytest`.

The SynthDefs are written in SuperCollider itself, in `supercollidermcp/synthdefs/synthdefs.scd`. After
editing that file, rebuild the compiled `.scsyndef` files with `python scripts/build_synthdefs.py`
(needs `sclang`; it runs headless).

```
supercollidermcp/
├── server.py      MCP tools: validation and wiring
├── compose.py     musical logic: requests → timed events (pure, unit-tested)
├── theory.py      notes, scales, chords
├── patterns.py    drum patterns as step strings
├── engine.py      server setup, buses, streaming playback, stop_all
├── osc.py         async OSC client that also reads scsynth's replies
└── synthdefs/     synthdefs.scd (source) + compiled .scsyndef files
```

Contributions are welcome. New sounds usually mean a SynthDef in `synthdefs.scd` plus a composer function
in `compose.py`.

## External Security Assessment

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/tok-supercollidermcp-badge.png)](https://mseep.ai/app/tok-supercollidermcp)

## License

MIT. See [LICENSE](LICENSE).
