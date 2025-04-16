"""
SuperCollider OSC MCP Server for Claude integration.

This script implements an MCP server that allows Claude Desktop to communicate
with SuperCollider using OSC.
"""

import random
import time
from mcp.server.fastmcp import FastMCP
from supercollidermcp.osc import SuperColliderClient

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
    
    # Define scale patterns (semitones from root)
    scales = {
        "major": [0, 2, 4, 5, 7, 9, 11, 12],
        "minor": [0, 2, 3, 5, 7, 8, 10, 12],
        "pentatonic": [0, 2, 4, 7, 9, 12],
        "blues": [0, 3, 5, 6, 7, 10, 12]
    }

    # Base frequency (A4 = 440Hz)
    base_freq = 440

    # Generate a melody
    note_count = 16
    root_note = random.randint(0, 11)  # Random root note
    octave = random.randint(0, 2)      # Random octave (0, 1, or 2)

    # Time between notes in seconds
    note_duration = 60 / tempo

    # Create a melody pattern
    melody = []
    for i in range(note_count):
        # Select a note from the scale
        scale_degree = random.randint(0, len(scales[scale])-1)
        note = root_note + scales[scale][scale_degree] + (octave * 12)

        # Convert to frequency (equal temperament)
        freq = base_freq * (2 ** ((note - 9) / 12))

        # Duration (whole, half, quarter notes)
        duration_options = [0.25, 0.5, 1.0]
        duration_weights = [0.5, 0.3, 0.2]  # More likely to use shorter notes
        duration = random.choices(duration_options, duration_weights)[0] * note_duration

        melody.append((freq, duration))

    # Play the melody
    synth_id = 2000
    for i, (freq, duration) in enumerate(melody):
        # Create a new synth for each note
        client.create_synth("default", synth_id + i, 0, 0, freq=freq, amp=0.3)
        time.sleep(duration)
        client.free_node(synth_id + i)
    
    # Play the scale to finish
    for i, semitones in enumerate(scales[scale]):
        # Calculate frequency
        freq = base_freq * (2 ** (semitones / 12))
        
        # Play the note
        node_id = 3000 + i
        client.create_synth("default", node_id, 0, 0, freq=freq, amp=0.3)
        
        # Wait for the note duration
        time.sleep(note_duration * 0.9)  # Slightly shorter for legato effect
        
        # Free the node
        client.free_node(node_id)

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

    # Create the client
    client = SuperColliderClient()
    
    # Define predefined patterns (1 = hit, 0 = rest)
    patterns = {
        "four_on_floor": {
            "kick":     [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
            "snare":    [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
            "hihat":    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        },
        "breakbeat": {
            "kick":     [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
            "snare":    [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1],
            "hihat":    [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0],
        },
        "shuffle": {
            "kick":     [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
            "snare":    [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
            "hihat":    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        }
    }

    # For random pattern, generate one
    if pattern_type == "random":
        patterns["random"] = {
            "kick": [random.choice([0, 1]) for _ in range(16)],
            "snare": [random.choice([0, 1]) for _ in range(16)],
            "hihat": [random.choice([0, 1]) for _ in range(16)]
        }
        # Ensure at least some beats
        if sum(patterns["random"]["kick"]) == 0:
            patterns["random"]["kick"][0] = 1
        if sum(patterns["random"]["snare"]) == 0:
            patterns["random"]["snare"][4] = 1

        pattern_type = "random"

    # Select the pattern
    pattern = patterns[pattern_type]

    # Time between beats in seconds
    beat_duration = 60 / tempo

    # Play the drum pattern
    for beat in range(beats):
        beat_idx = beat % 16  # Loop the pattern if beats > 16

        # Play each drum sound if it's a hit
        if pattern["kick"][beat_idx]:
            # Kick drum (low frequency sine with quick decay)
            client.create_synth("default", 3000 + beat, 0, 0, freq=60, amp=0.5)

        if pattern["snare"][beat_idx]:
            # Snare (mid frequency with noise)
            client.create_synth("default", 4000 + beat, 0, 0, freq=300, amp=0.3)

        if pattern["hihat"][beat_idx]:
            # Hi-hat (high frequency)
            client.create_synth("default", 5000 + beat, 0, 0, freq=1200, amp=0.2)

        # Wait for the next beat
        time.sleep(beat_duration)

        # Free all synths from this beat
        if pattern["kick"][beat_idx]:
            client.free_node(3000 + beat)
        if pattern["snare"][beat_idx]:
            client.free_node(4000 + beat)
        if pattern["hihat"][beat_idx]:
            client.free_node(5000 + beat)

    return f"Successfully played a {pattern_type} drum pattern with {beats} beats at {tempo} BPM"

if __name__ == "__main__":
    print("SuperCollider OSC MCP Server")
    print("----------------------------")
    print("This script is intended to be run with the MCP server.")
    print("To test it locally, you can use:")
    print("  python -m mcp.run server.py")
