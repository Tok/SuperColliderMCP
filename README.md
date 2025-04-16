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

#### Basic Tools
1. **Play Example OSC** - Plays a simple example sound with frequency modulation
2. **Play Melody** - Creates a procedurally generated melody using a specified scale and tempo
3. **Create Drum Pattern** - Plays a drum pattern with customizable pattern type, beats, and tempo
4. **Play Synth** - Plays a single note with different synthesizer types and effects
5. **Create Sequence** - Creates a musical sequence from a string pattern notation

#### Advanced Tools
6. **Create Ambient Soundscape** - Generates evolving ambient textures with customizable mood
7. **Create Generative Rhythm** - Creates evolving rhythmic patterns in different styles
8. **Create LFO Modulation** - Applies modulation to synthesizer parameters
9. **Create Layered Synth** - Creates rich sounds with multiple oscillator layers
10. **Create Granular Texture** - Creates textures using granular synthesis techniques
11. **Create Chord Progression** - Plays chord progressions with different voicing styles

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

- `server.py` - Main MCP server with basic sound generation tools
- `soundscape_tools.py` - Tools for creating ambient soundscapes and generative rhythms
- `advanced_synthesis.py` - Advanced synthesis tools with LFOs, layered synths, and granular synthesis
- `supercollidermcp/` - Package directory with utility modules

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
