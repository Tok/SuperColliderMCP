# SuperCollider OSC MCP 🎛️

A Model Context Protocol (MCP) server for SuperCollider using Open Sound Control (OSC).

## Description

This project provides a Python interface for communicating with [SuperCollider](https://supercollider.github.io/) via OSC messages, integrated with AI development environments using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). It allows for programmatic control of audio synthesis and processing in SuperCollider from various AI coding assistants.

## Features

- Send OSC messages to SuperCollider
- Play procedurally generated melodies with different scales
- Create rhythmic drum patterns
- Advanced sound design with synthesizers, effects, and modulation
- Ambient soundscape generation
- Granular synthesis and layered instruments
- Chord progression generation with different voicing styles
- Flexible integration with multiple AI development- and assistance environments

## Architecture

```mermaid
graph TD
    classDef aiAssistant fill:#00bfff,color:#ffffff,stroke:#000000;
    classDef mcpServer fill:#6bd968,color:#000000,stroke:#000000;
    classDef audioServer fill:#8ae180,color:#000000,stroke:#000000;
    classDef pythonClient fill:#a5e9a3,color:#000000,stroke:#000000;
    classDef protocolLayer fill:#c0c0c0,color:#000000,stroke:#000000,stroke-dasharray:5;

    A[AI Assistant] -->|Method Call| B[MCP Server]
    B -->|OSC| C[SuperCollider Audio Server]
    B <-->|Control| D[Python OSC Client]

    subgraph protocolContainer["Protocol Layer"]
        style protocolContainer fill:#f0f0f0,stroke:#888,stroke-width:2px
        direction TB
        E[🔍 Method Registry]
        F[✅ Parameter Validation]
        G[📦 Response Handling]
    end

    A -->|Invokes| E
    E -->|Validates| F
    F -->|Formats| G
    G -->|Routes| B

    class A aiAssistant;
    class B mcpServer;
    class C audioServer;
    class D pythonClient;
    class E,F,G protocolLayer;
```

## Installation

### Prerequisites

- Python 3.12 or higher
- [SuperCollider 3.13.1](https://supercollider.github.io/) 
  - Ensure server is running on port 57110
- [UV](https://github.com/astral-sh/uv) - Fast Python package manager

### Installing UV (Python Package Manager)

```bash
# Install UV on macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install UV on Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Project Installation

```bash
# Clone the repository
git clone https://github.com/tok/supercollidermcp.git
cd supercollidermcp

# Install with UV
uv pip install -e .
```

## Usage

### AI Development Environment Integration

#### Claude Desktop
Configure in Claude Desktop settings:

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

#### Roo Code / Cline
Add to `mcp.json`:

```json
{
  "mcpServers": {
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
  }
}
```

## AI Assistant Tool Adaptation

### Workspace Integration for Dynamic Tool Creation

To enable advanced functionality, it is recommended to add `server.py` to the AI assistant's workspace. This allows the AI to:

- Dynamically understand the project's structure
- Analyze and modify the existing sound generation tools
- Create new OSC-based tools on demand
- Adapt the Python code to extend functionality

#### Integration Steps

1. Add the entire project directory to the AI assistant's workspace
2. Ensure `server.py` is visible and accessible to the AI
3. Provide context about the MCP and OSC communication protocols
4. Allow the AI to inspect and modify the project files

##### Recommended Workspace Structure
```
supercollidermcp/
│
├── server.py              # Main MCP server with all sound generation tools including advanced synthesis, soundscape and generative rhythm tools
├── supercollidermcp/
│   ├── osc.py             # SuperCollider OSC client
│   ├── melody.py          # Melody generation utilities
│   ├── rhythm.py          # Rhythm pattern utilities
│   └── ...
└── README.md
```

**Note:** The ability to modify tools dynamically depends on the specific capabilities of the AI assistant and its integration with the Model Context Protocol.

### Local Testing and Development

The project has been tested with Claude Desktop and locally using Roo Code with:
- [Ollama](https://ollama.ai/) - Local AI model server
- [DeepCoder](https://ollama.com/library/deepcoder) (open-source model)

### Available Commands

Once configured, the assistant can use a variety of tools:

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

## Security Assessment
[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/tok-supercollidermcp-badge.png)](https://mseep.ai/app/tok-supercollidermcp)

## Development

The project uses FastMCP for handling Claude's requests and the python-osc library for communicating with SuperCollider. For more information about the Model Context Protocol, visit [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/).

## Contributing

Contributions are welcome! Please submit Pull Requests with:
- New sound generation tools
- Improved integration methods
- Bug fixes and optimizations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Additional Resources

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [SuperCollider Official Website](https://supercollider.github.io/)
