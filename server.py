"""
SuperCollider OSC MCP Server for Claude integration.

This script implements an MCP server that allows Claude Desktop to communicate
with SuperCollider using OSC.
"""

import random
import time
from mcp.server.fastmcp import FastMCP
from supercollidermcp.osc import SuperColliderClient
from supercollidermcp.melody import generate_melody, play_melody, play_scale
from supercollidermcp.rhythm import play_drum_pattern

# Initialize the MCP server
mcp = FastMCP("Super-Collider-OSC-MCP")

@mcp.tool()
async def play_example_osc():
    """
    Play a simple example sound using SuperCollider OSC.
    
    This demonstrates basic OSC communication by playing a sine wave
    with random frequency modulation.
    """
    # Create the client
    client = SuperColliderClient()

    # Create a simple sine wave synth
    client.create_synth("default", 1000, 0, 0, freq=440, amp=0.5)
    time.sleep(1)

    # Change the frequency a few times
    for x in range(10):
        freq = 300 + random.random() * 700
        # /n_set sets parameters on an existing synth
        client.set_node_params(1000, freq=freq)
        time.sleep(0.5)

    # Free the synth when done
    client.free_node(1000)

    return "Successfully sent OSC messages using standard SuperCollider commands"

@mcp.tool()
async def play_melody(scale="major", tempo=120):
    """
    Play a procedurally generated melody using SuperCollider.

    Args:
        scale: The scale to use ("major", "minor", "pentatonic", "blues")
        tempo: Beats per minute (60-240)
    """
    # Validate inputs
    if scale not in ["major", "minor", "pentatonic", "blues"]:
        scale = "major"

    tempo = max(60, min(240, int(tempo)))  # Clamp between 60-240 BPM

    # Create the client
    client = SuperColliderClient()
    
    # Generate a melody
    melody = generate_melody(scale=scale, note_count=16)
    
    # Play the melody
    play_melody(melody, tempo=tempo, client=client)
    
    # Play the scale to finish
    play_scale(scale=scale, tempo=tempo, direction="both", client=client)

    return f"Successfully played a {scale} scale melody at {tempo} BPM"

@mcp.tool()
async def create_drum_pattern(pattern_type="four_on_floor", beats=16, tempo=120):
    """
    Play a drum pattern using SuperCollider.

    Args:
        pattern_type: Type of drum pattern ("four_on_floor", "breakbeat", "shuffle", "random")
        beats: Number of beats in the pattern (4-32)
        tempo: Beats per minute (60-240)
    """
    # Validate inputs
    if pattern_type not in ["four_on_floor", "breakbeat", "shuffle", "random"]:
        pattern_type = "four_on_floor"

    beats = max(4, min(32, int(beats)))  # Clamp between 4-32 beats
    tempo = max(60, min(240, int(tempo)))  # Clamp between 60-240 BPM

    # Play the drum pattern
    play_drum_pattern(pattern_type=pattern_type, beats=beats, tempo=tempo)

    return f"Successfully played a {pattern_type} drum pattern with {beats} beats at {tempo} BPM"

if __name__ == "__main__":
    print("SuperCollider OSC MCP Server")
    print("----------------------------")
    print("This script is intended to be run with the MCP server.")
    print("To test it locally, you can use:")
    print("  python -m mcp.run server.py")
