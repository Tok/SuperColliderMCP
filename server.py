"""
SuperCollider OSC MCP Server for Claude integration.

This script implements a Model Context Protocol (MCP) server that allows Claude Desktop to communicate
with SuperCollider using Open Sound Control (OSC), providing fine-grained control over sound synthesis.
"""

import random
import time
import json
import math
from mcp.server.fastmcp import FastMCP
from pythonosc import udp_client

# Initialize the MCP server
mcp = FastMCP("Super-Collider-OSC-MCP")

# Default SuperCollider connection
DEFAULT_SC_IP = "127.0.0.1"
DEFAULT_SC_PORT = 57110

# Create a global client that can be reused
sc_client = udp_client.SimpleUDPClient(DEFAULT_SC_IP, DEFAULT_SC_PORT)

# Helper function to manage node IDs
def get_node_id():
    """Generate a semi-random node ID to avoid conflicts."""
    return int(time.time() * 100) % 10000 + 1000

# Note name to frequency conversion helpers
NOTE_TO_SEMITONE = {
    "C": -9, "C#": -8, "Db": -8, "D": -7, "D#": -6, "Eb": -6,
    "E": -5, "F": -4, "F#": -3, "Gb": -3, "G": -2, "G#": -1, "Ab": -1,
    "A": 0, "A#": 1, "Bb": 1, "B": 2
}

def note_to_freq(note):
    """Convert a note name (e.g., 'C4', 'A#3') to frequency in Hz."""
    if isinstance(note, (int, float)):
        return float(note)
        
    if not isinstance(note, str) or len(note) < 2:
        return 440.0  # Default to A4
        
    note_name = note[:-1]
    try:
        octave = int(note[-1])
        if note_name in NOTE_TO_SEMITONE:
            # Calculate semitones from A4
            semitones = NOTE_TO_SEMITONE[note_name] + (octave - 4) * 12
            # Convert to frequency (A4 = 440Hz)
            return 440.0 * (2 ** (semitones / 12))
    except (ValueError, IndexError):
        pass
        
    return 440.0  # Default to A4 if parsing fails

@mcp.tool()
async def play_example_osc():
    """
    Play a simple example sound using SuperCollider OSC.
    
    This demonstrates basic OSC communication by playing a sine wave
    with random frequency modulation.
    """
    # Create a simple sine wave synth
    node_id = get_node_id()
    sc_client.send_message("/s_new", ["default", node_id, 0, 0, "freq", 440, "amp", 0.5])
    time.sleep(1)

    # Change the frequency a few times
    for x in range(10):
        freq = 300 + random.random() * 700
        # /n_set sets parameters on an existing synth
        sc_client.send_message("/n_set", [node_id, "freq", freq])
        time.sleep(0.5)

    # Free the synth when done
    sc_client.send_message("/n_free", [node_id])

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
    synth_id = get_node_id()
    for i, (freq, duration) in enumerate(melody):
        # Create a new synth for each note
        current_id = synth_id + i
        sc_client.send_message("/s_new", ["default", current_id, 0, 0, "freq", freq, "amp", 0.3])
        time.sleep(duration)
        sc_client.send_message("/n_free", [current_id])
    
    # Play the scale to finish
    for i, semitones in enumerate(scales[scale]):
        # Calculate frequency
        freq = base_freq * (2 ** (semitones / 12))
        
        # Play the note
        current_id = synth_id + note_count + i
        sc_client.send_message("/s_new", ["default", current_id, 0, 0, "freq", freq, "amp", 0.3])
        
        # Wait for the note duration
        time.sleep(note_duration * 0.9)  # Slightly shorter for legato effect
        
        # Free the node
        sc_client.send_message("/n_free", [current_id])

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

    # Base node ID
    base_id = get_node_id()

    # Play the drum pattern
    for beat in range(beats):
        beat_idx = beat % 16  # Loop the pattern if beats > 16

        # Play each drum sound if it's a hit
        if pattern["kick"][beat_idx]:
            # Kick drum (low frequency sine with quick decay)
            sc_client.send_message("/s_new", ["default", base_id + beat, 0, 0, "freq", 60, "amp", 0.5])

        if pattern["snare"][beat_idx]:
            # Snare (mid frequency with noise)
            sc_client.send_message("/s_new", ["default", base_id + 1000 + beat, 0, 0, "freq", 300, "amp", 0.3])

        if pattern["hihat"][beat_idx]:
            # Hi-hat (high frequency)
            sc_client.send_message("/s_new", ["default", base_id + 2000 + beat, 0, 0, "freq", 1200, "amp", 0.2])

        # Wait for the next beat
        time.sleep(beat_duration)

        # Free all synths from this beat
        if pattern["kick"][beat_idx]:
            sc_client.send_message("/n_free", [base_id + beat])
        if pattern["snare"][beat_idx]:
            sc_client.send_message("/n_free", [base_id + 1000 + beat])
        if pattern["hihat"][beat_idx]:
            sc_client.send_message("/n_free", [base_id + 2000 + beat])

    return f"Successfully played a {pattern_type} drum pattern with {beats} beats at {tempo} BPM"

@mcp.tool()
async def play_synth(synth_type="sine", note="A4", duration=2.0, volume=0.5, effects=None):
    """
    Play a synthesizer with various waveforms and optional effects.
    
    Args:
        synth_type: Type of synthesizer ("sine", "saw", "square", "noise", "fm", "pad")
        note: Musical note (e.g., "C4", "G#3", "F5") or frequency in Hz
        duration: Duration in seconds
        volume: Volume level (0.0-1.0)
        effects: Optional effects as JSON string: {"reverb": 0-1, "delay": 0-1, "distortion": 0-1, "filter": 0-1}
    """
    # Convert note to frequency
    frequency = note_to_freq(note)
    
    # Validate parameters
    volume = max(0.0, min(1.0, float(volume)))
    duration = max(0.1, min(30.0, float(duration)))
    
    # Create a node ID
    node_id = get_node_id()
    
    # Default parameters
    params = ["freq", frequency, "amp", volume]
    
    # Parse effects
    if effects:
        try:
            effect_dict = json.loads(effects) if isinstance(effects, str) else effects
            if isinstance(effect_dict, dict):
                for effect in ["reverb", "delay", "distortion", "filter"]:
                    if effect in effect_dict:
                        value = max(0, min(1, float(effect_dict[effect])))
                        params.extend([effect, value])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    
    # Create the synth based on type
    synth_name = "default"  # Default sine wave
    if synth_type == "saw":
        # In reality, you'd use a specific SynthDef for each type
        # For this demo, we'll use the default with slightly modified parameters
        params.extend(["harmonics", 10])  # More harmonics for saw-like sound
    elif synth_type == "square":
        params.extend(["harmonics", 20])  # Even more harmonics for square-like
    elif synth_type == "noise":
        params[0:2] = ["freq", random.uniform(100, 1000)]  # Random frequency for noise
    elif synth_type == "fm":
        # For FM synthesis, we might use a ratio between carrier and modulator
        params.extend(["mod_ratio", 2.0, "mod_depth", 0.5])
    elif synth_type == "pad":
        # For pad, we'd use longer attack/release
        params.extend(["attack", 0.5, "release", 1.0])
    
    # Send OSC message to create the synth
    sc_client.send_message("/s_new", [synth_name, node_id, 0, 0] + params)
    
    # Wait for the specified duration
    time.sleep(duration)
    
    # Free the synth
    sc_client.send_message("/n_free", [node_id])
    
    return f"Played {synth_type} synth at {frequency:.1f}Hz for {duration} seconds"

@mcp.tool()
async def create_sequence(pattern, synth="sine", tempo=120, repeats=1):
    """
    Create a musical sequence from a pattern string.
    
    Args:
        pattern: Pattern string (e.g., "C4-E4-G4-C5" or "C_-E_-G_-C+" for note length variation)
                 Use "-" to separate notes, "_" for shorter notes, "+" for longer notes, "." for rests
        synth: Synthesizer type ("sine", "saw", "square", "fm", "pad")
        tempo: Beats per minute (60-240)
        repeats: Number of times to repeat the pattern (1-8)
    """
    # Validate inputs
    tempo = max(60, min(240, int(tempo)))
    repeats = max(1, min(8, int(repeats)))
    
    # Calculate beat duration in seconds
    beat_duration = 60 / tempo
    
    # Parse the pattern
    notes = pattern.split("-") if "-" in pattern else [c for c in pattern]
    
    # Process each note
    structured_notes = []
    for note_str in notes:
        # Check for rest
        if note_str == "." or not note_str:
            structured_notes.append({"type": "rest", "duration": beat_duration})
            continue
        
        # Check for duration modifiers
        duration_mod = 1.0
        note_name = note_str
        
        if "_" in note_str:  # Shorter notes
            count = note_str.count("_")
            duration_mod = 1.0 / (count + 1)
            note_name = note_str.replace("_", "")
        elif "+" in note_str:  # Longer notes
            count = note_str.count("+")
            duration_mod = 1.0 + (count * 0.5)  # Each + adds 50% more duration
            note_name = note_str.replace("+", "")
        
        # Convert note to frequency
        frequency = note_to_freq(note_name)
        if frequency > 0:
            structured_notes.append({
                "type": "note",
                "frequency": frequency,
                "duration": beat_duration * duration_mod
            })
        else:
            structured_notes.append({"type": "rest", "duration": beat_duration})
    
    # Base node ID
    base_id = get_node_id()
    
    # Play the sequence
    for repeat in range(repeats):
        for i, note_data in enumerate(structured_notes):
            if note_data["type"] == "note":
                # Create the synth
                node_id = base_id + (repeat * 100) + i
                
                # Send message to create the synth
                synth_name = "default"  # Default for sine
                sc_client.send_message("/s_new", [synth_name, node_id, 0, 0, 
                                             "freq", note_data["frequency"], 
                                             "amp", 0.3])
                
                # Wait for the note duration
                time.sleep(note_data["duration"] * 0.95)  # Slightly shorter for legato
                
                # Free the synth
                sc_client.send_message("/n_free", [node_id])
            else:
                # Rest - just wait
                time.sleep(note_data["duration"])
    
    return f"Played sequence with {len(notes)} notes at {tempo} BPM, repeated {repeats} times"

if __name__ == "__main__":
    print("SuperCollider OSC MCP Server running")
    print("------------------------------------")
    print("This server provides the following tools:")
    print("1. play_example_osc - Play a simple example sound")
    print("2. play_melody - Play a procedurally generated melody")
    print("3. create_drum_pattern - Play a drum pattern")
    print("4. play_synth - Play a synthesizer with various waveforms")
    print("5. create_sequence - Create a musical sequence from a pattern string")
    print("\nTo test locally, run: python -m mcp.run server.py")
