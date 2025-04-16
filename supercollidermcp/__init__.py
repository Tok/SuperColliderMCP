"""
SuperCollider OSC MCP - A Model Context Protocol for SuperCollider.

This module provides tools for communicating with SuperCollider 
(https://supercollider.github.io/) via OSC from Claude Desktop 
using the Model Context Protocol (MCP).
"""

# supercollidermcp/__init__.py
from .osc import SuperColliderClient
from .melody import play_scale, generate_melody, play_melody
from .rhythm import play_drum_pattern

__version__ = "0.1.0"

# Import advanced modules
try:
    from .advanced_synthesis import (
        create_lfo_modulation,
        create_layered_synth,
        create_granular_texture,
        create_chord_progression
    )
    from .soundscape_tools import (
        create_ambient_soundscape,
        create_generative_rhythm
    )
except ImportError:
    # Handle the case where these modules aren't available yet
    pass