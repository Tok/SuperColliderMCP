# SuperCollider OSC MCP

A Model Context Protocol (MCP) server for SuperCollider using Open Sound Control (OSC).

## Description

This project provides a Python interface for communicating with [SuperCollider](https://supercollider.github.io/) via OSC messages, integrated with Claude Desktop via the Model Context Protocol (MCP). It allows for programmatic control of audio synthesis and processing in SuperCollider from Claude.

## Features

- Send OSC messages to SuperCollider
- Play procedurally generated melodies with different scales
- Create rhythmic drum patterns
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

Once configured, Claude can use the following commands:

1. **Play Example OSC** - Plays a simple example sound with frequency modulation
2. **Play Melody** - Creates a procedurally generated melody using a specified scale and tempo
3. **Create Drum Pattern** - Plays a drum pattern with customizable pattern type, beats, and tempo

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
