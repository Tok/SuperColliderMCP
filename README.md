# SuperCollider OSC MCP

A Model Context Protocol (MCP) server for SuperCollider using Open Sound Control (OSC).

## Description

This project provides a Python interface for communicating with [SuperCollider](https://supercollider.github.io/) via OSC messages, integrated with Claude Desktop via the Model Context Protocol (MCP). It allows for programmatic control of audio synthesis and processing in SuperCollider from Claude.

## Features

- Send OSC messages to SuperCollider
- Play procedurally generated melodies with different scales
- Create rhythmic drum patterns
- Advanced sound design with synthesizers, effects, and modulation
- Ambient soundscape generation
- Granular synthesis and layered instruments
- Chord progression generation with different voicing styles
- Seamless integration with Claude Desktop

## Installation

### Prerequisites

- Python 3.12 or higher
- [SuperCollider](https://supercollider.github.io/) (with server running on port 57110)
- UV (Python package manager)

### Installing

```bash
# Clone the repository
git clone https://github.com/tok/supercollidermcp.git
cd supercollidermcp

# Install with UV
uv pip install -e .
```

## Usage

### Claude Desktop Integration

This package is designed to work with Claude Desktop using the following configuration:

```json
"Super-Collider-OSC-MCP": {
  "command": "uv",
  "args": [
    "run",
    "--with",
    "mcp[cli],python-osc",
    "mcp",
    "run",
    "path/to/server.py"
  ]
}
```

Add this configuration to your Claude Desktop settings to enable SuperCollider integration, replacing `path/to/server.py` with the actual path to the server.py file on your system.

### Available Commands

Once configured, Claude can use a variety of tools:

#### Basic Sound Generation
1. **play_example_osc** - Play a simple example sound with frequency modulation
2. **play_melody** - Create a procedurally generated melody using a specified scale and tempo
3. **create_drum_pattern** - Play drum patterns in various styles (four_on_floor, breakbeat, shuffle, random)
4. **play_synth** - Play a single note with different synthesizer types (sine, saw, square, noise, fm, pad) and effects
5. **create_sequence** - Create a musical sequence from a pattern string with note length variations

#### Advanced Synthesis
6. **create_lfo_modulation** - Apply modulation to synthesizer parameters (frequency, amplitude, filter, pan)
7. **create_layered_synth** - Create rich sounds with multiple detuned oscillator layers and stereo spread
8. **create_granular_texture** - Create textures using granular synthesis with controllable density and pitch variation
9. **create_chord_progression** - Play chord progressions with different voicing styles (pad, staccato, arpeggio, power)

#### Soundscape Generation
10. **create_ambient_soundscape** - Generate evolving ambient textures with different moods (calm, dark, bright, mysterious, chaotic)
11. **create_generative_rhythm** - Create evolving rhythmic patterns in different styles (minimal, techno, glitch, jazz, ambient)

### Example Usage in Claude

Here are some examples of how to use these tools in Claude:

```
// Basic melody
play_melody(scale="pentatonic", tempo=110)

// Layered synth with effects
create_layered_synth(base_note="F3", num_layers=4, detune=0.2, effects={"reverb": 0.6, "delay": 0.3}, duration=4.0)

// Ambient soundscape
create_ambient_soundscape(duration=20, density=0.6, pitch_range="medium", mood="mysterious")

// Chord progression
create_chord_progression(progression="Cmaj7-Am7-Dm7-G7", style="arpeggio", tempo=100, duration_per_chord=2.0)
```

### Testing Locally

You can test the functionality directly by running:

```bash
python -m mcp.run server.py
```

You can also use the command-line interface:

```bash
# Play a note
sc-osc note --freq 440 --amp 0.5 --duration 2.0

# Play a scale
sc-osc scale --scale minor --tempo 100 --direction both

# Generate and play a melody
sc-osc melody --scale blues --tempo 120 --notes 16

# Play a drum pattern
sc-osc drums --pattern breakbeat --beats 32 --tempo 140
```

## About SuperCollider

[SuperCollider](https://supercollider.github.io/) is a platform for audio synthesis and algorithmic composition, used by musicians, artists, and researchers working with sound. It consists of:

- A real-time audio server with hundreds of unit generators for synthesis and signal processing
- A cross-platform interpreted programming language (sclang)
- A flexible scheduling system for precise timing of musical events

This project communicates with SuperCollider's audio server using OSC messages to control synthesizers and create sound patterns.

## Development

The project uses FastMCP for handling Claude's requests and the python-osc library for communicating with SuperCollider. For more information about the Model Context Protocol, visit [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/).

## Project Structure

- `server.py` - Main MCP server with all sound generation tools
- `supercollidermcp/` - Package directory with utility modules:
  - `osc.py` - SuperCollider OSC client
  - `melody.py` - Melody generation utilities
  - `rhythm.py` - Rhythm pattern utilities
  - `advanced_synthesis.py` - Advanced synthesis tools
  - `soundscape_tools.py` - Soundscape and generative rhythm tools

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
