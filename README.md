# SuperCollider OSC MCP

A Messaging Control Protocol (MCP) server for SuperCollider using Open Sound Control (OSC).

## Description

This project provides a Python interface for communicating with SuperCollider via OSC messages, integrated with Claude Desktop via the MCP protocol. It allows for programmatic control of audio synthesis and processing in SuperCollider from Claude.

## Features

- Send OSC messages to SuperCollider
- Play procedurally generated melodies with different scales
- Create rhythmic drum patterns
- Seamless integration with Claude Desktop

## Installation

### Prerequisites

- Python 3.12 or higher
- SuperCollider (with server running on port 57110)
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
    "B:\\PycharmProjects\\SuperColliderMCP\\server.py"
  ]
}
```

Add this configuration to your Claude Desktop settings to enable SuperCollider integration.

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

## Development

The project uses FastMCP for handling Claude's requests and the python-osc library for communicating with SuperCollider.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
