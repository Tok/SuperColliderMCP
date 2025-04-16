"""
SuperCollider OSC MCP Server for Claude integration.
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

@mcp.tool()
async def create_lfo_modulation(target_param="frequency", rate=0.5, depth=0.5, waveform="sine", duration=10.0):
    """
    Create an LFO modulation effect on a synthesizer parameter.

    Args:
        target_param: Parameter to modulate ("frequency", "amplitude", "filter", "pan")
        rate: LFO speed in Hz (0.01-10.0)
        depth: Modulation depth (0.0-1.0)
        waveform: LFO waveform ("sine", "triangle", "square", "random")
        duration: Duration in seconds (1.0-60.0)
    """
    # Validate inputs
    rate = max(0.01, min(10.0, float(rate)))
    depth = max(0.0, min(1.0, float(depth)))
    duration = max(1.0, min(60.0, float(duration)))

    # Map target parameter to appropriate value ranges
    param_map = {
        "frequency": {
            "base_value": 440.0,
            "min_value": 440.0 * (1.0 - depth * 0.5),
            "max_value": 440.0 * (1.0 + depth * 0.5),
            "sc_param": "freq"
        },
        "amplitude": {
            "base_value": 0.5,
            "min_value": 0.5 * (1.0 - depth),
            "max_value": 0.5,
            "sc_param": "amp"
        },
        "filter": {
            "base_value": 1000.0,
            "min_value": 100.0,
            "max_value": 100.0 + depth * 3900.0,
            "sc_param": "cutoff"
        },
        "pan": {
            "base_value": 0.0,
            "min_value": -1.0 * depth,
            "max_value": 1.0 * depth,
            "sc_param": "pan"
        }
    }

    # Default to frequency if target not recognized
    target_info = param_map.get(target_param, param_map["frequency"])

    # Create the main synth
    node_id = get_node_id()
    sc_client.send_message("/s_new", ["default", node_id, 0, 0,
                                      target_info["sc_param"], target_info["base_value"],
                                      "amp", 0.3])

    # Start time
    start_time = time.time()
    end_time = start_time + duration

    # Perform the LFO modulation
    try:
        cycle_time = 1.0 / rate  # Time for one complete cycle
        step_time = min(0.05, cycle_time / 20.0)  # Update rate (20 steps per cycle or every 50ms)

        while time.time() < end_time:
            # Calculate elapsed time
            elapsed = time.time() - start_time

            # Calculate LFO value based on waveform
            if waveform == "sine":
                # Sine wave: sin(2π × rate × time) mapped to range [min, max]
                phase = elapsed * rate * 2 * math.pi
                lfo_value = (math.sin(phase) + 1.0) / 2.0  # 0 to 1
            elif waveform == "triangle":
                # Triangle wave
                phase = (elapsed * rate) % 1.0
                if phase < 0.5:
                    lfo_value = phase * 2.0  # 0 to 1
                else:
                    lfo_value = 1.0 - (phase - 0.5) * 2.0  # 1 to 0
            elif waveform == "square":
                # Square wave
                phase = (elapsed * rate) % 1.0
                lfo_value = 1.0 if phase < 0.5 else 0.0
            elif waveform == "random":
                # Random sample and hold
                phase = (elapsed * rate) % 1.0
                # Update random value at start of each cycle
                if phase < step_time:
                    lfo_value = random.random()
                else:
                    # Hold the value for the rest of the cycle
                    pass
            else:
                # Default to sine
                phase = elapsed * rate * 2 * math.pi
                lfo_value = (math.sin(phase) + 1.0) / 2.0

            # Map LFO value to parameter range
            param_value = target_info["min_value"] + lfo_value * (target_info["max_value"] - target_info["min_value"])

            # Update the parameter
            sc_client.send_message("/n_set", [node_id, target_info["sc_param"], param_value])

            # Sleep until next update
            time.sleep(step_time)

    finally:
        # Clean up
        sc_client.send_message("/n_free", [node_id])

    return f"Applied {waveform} LFO modulation on {target_param} at {rate}Hz for {duration} seconds"


@mcp.tool()
async def create_layered_synth(base_note="C3", num_layers=3, detune=0.1, effects=None, duration=5.0):
    """
    Create a rich, layered synthesizer sound with multiple oscillators.

    Args:
        base_note: Root note for the sound (e.g., "C3", "G#4")
        num_layers: Number of oscillator layers (1-5)
        detune: Amount of detuning between layers (0.0-1.0)
        effects: Optional effects as JSON string: {"reverb": 0-1, "delay": 0-1, "distortion": 0-1}
        duration: Duration in seconds (1.0-30.0)
    """
    # Validate inputs
    num_layers = max(1, min(5, int(num_layers)))
    detune = max(0.0, min(1.0, float(detune)))
    duration = max(1.0, min(30.0, float(duration)))

    # Convert base note to frequency
    base_freq = note_to_freq(base_note)

    # Parse effects
    reverb = 0.0
    delay = 0.0
    distortion = 0.0
    if effects:
        try:
            effect_dict = json.loads(effects) if isinstance(effects, str) else effects
            if isinstance(effect_dict, dict):
                reverb = max(0.0, min(1.0, float(effect_dict.get("reverb", 0.0))))
                delay = max(0.0, min(1.0, float(effect_dict.get("delay", 0.0))))
                distortion = max(0.0, min(1.0, float(effect_dict.get("distortion", 0.0))))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Initialize nodes list for cleanup
    nodes = []

    # Base node ID
    base_id = get_node_id()

    # Create the layers
    try:
        for i in range(num_layers):
            # Calculate detune factor for this layer
            # Center detuning around the base frequency
            detune_factor = 1.0
            if num_layers > 1:
                # Spread layers evenly across the detune range
                # Layer 0 gets lowest pitch, last layer gets highest
                detune_spread = 2.0 * detune / (num_layers - 1)
                detune_factor = 1.0 - detune + (i * detune_spread)

            # Calculate frequency for this layer
            layer_freq = base_freq * detune_factor

            # Calculate amplitude for this layer (center layer is loudest)
            layer_amp = 0.3
            if num_layers > 1:
                # Center layer(s) are loudest
                center_distance = abs(i - (num_layers - 1) / 2) / (num_layers - 1)
                layer_amp = 0.3 * (1.0 - center_distance * 0.5)

            # Calculate pan position for stereo spread
            pan = 0.0
            if num_layers > 1:
                # Spread layers across the stereo field
                pan = -0.8 + (i / (num_layers - 1)) * 1.6  # -0.8 to 0.8

            # Create a synth for this layer
            node_id = base_id + i

            # Select a waveform for variety (if more than 1 layer)
            synth_type = "default"  # Sine wave

            # Build parameters
            params = [
                "freq", layer_freq,
                "amp", layer_amp,
                "pan", pan
            ]

            # Add effect parameters if enabled
            if reverb > 0.0:
                params.extend(["reverb", reverb])
            if delay > 0.0:
                params.extend(["delay", delay])
            if distortion > 0.0:
                params.extend(["distortion", distortion])

            # Create the synth
            sc_client.send_message("/s_new", [synth_type, node_id, 0, 0] + params)
            nodes.append(node_id)

        # Wait for the specified duration
        time.sleep(duration)

    finally:
        # Clean up all nodes
        for node_id in nodes:
            sc_client.send_message("/n_free", [node_id])

    effects_str = []
    if reverb > 0.0:
        effects_str.append(f"reverb: {reverb:.2f}")
    if delay > 0.0:
        effects_str.append(f"delay: {delay:.2f}")
    if distortion > 0.0:
        effects_str.append(f"distortion: {distortion:.2f}")

    effects_msg = f" with effects ({', '.join(effects_str)})" if effects_str else ""

    return f"Created a {num_layers}-layer synth at {base_note} ({base_freq:.1f}Hz){effects_msg} for {duration} seconds"

@mcp.tool()
async def create_granular_texture(source_note="A4", density=0.5, grain_size=0.1, pitch_spread=0.5, duration=10.0):
    """
    Create a granular synthesis texture by generating many small sonic grains.

    Args:
        source_note: Base note for the grains (e.g., "C4", "G#3")
        density: Grain density/overlap (0.1-1.0)
        grain_size: Size of individual grains in seconds (0.01-0.5)
        pitch_spread: Pitch variation between grains (0.0-1.0)
        duration: Total duration in seconds (1.0-30.0)
    """
    # Validate inputs
    density = max(0.1, min(1.0, float(density)))
    grain_size = max(0.01, min(0.5, float(grain_size)))
    pitch_spread = max(0.0, min(1.0, float(pitch_spread)))
    duration = max(1.0, min(30.0, float(duration)))

    # Convert source note to frequency
    base_freq = note_to_freq(source_note)

    # Calculate parameters for granular synthesis
    # Higher density = more grains per second
    grains_per_second = density * 20  # Up to 20 grains per second at maximum density

    # Calculate grain parameters
    # At lower densities, make grains slightly longer to maintain some continuity
    actual_grain_size = grain_size * (1.2 - density * 0.2)

    # Calculate time between grain onsets
    grain_interval = 1.0 / grains_per_second

    # Start time
    start_time = time.time()
    end_time = start_time + duration

    # Keep track of active nodes for cleanup
    active_nodes = {}  # Map node_id -> expected end time
    next_node_id = get_node_id()

    try:
        # Main granular synthesis loop
        while time.time() < end_time:
            # Create a grain
            grain_id = next_node_id
            next_node_id += 1

            # Calculate random variation for this grain
            # Pitch variation
            pitch_variation = 1.0 + (random.random() * 2 - 1) * pitch_spread
            grain_freq = base_freq * pitch_variation

            # Amplitude variation (quieter at edges of pitch spread)
            amp_factor = 1.0 - (abs(pitch_variation - 1.0) / pitch_spread) * 0.5
            grain_amp = 0.2 * amp_factor

            # Pan position (stereo spread)
            pan = random.uniform(-0.8, 0.8)

            # Create the grain
            sc_client.send_message("/s_new", ["default", grain_id, 0, 0,
                                              "freq", grain_freq,
                                              "amp", grain_amp,
                                              "pan", pan])

            # Record expected end time for this grain
            grain_end_time = time.time() + actual_grain_size
            active_nodes[grain_id] = grain_end_time

            # Clean up expired grains
            current_time = time.time()
            expired_grains = [nid for nid, end_time in active_nodes.items() if end_time <= current_time]
            for nid in expired_grains:
                sc_client.send_message("/n_free", [nid])
                del active_nodes[nid]

            # Wait until next grain
            time.sleep(grain_interval)

    finally:
        # Clean up all remaining nodes
        for node_id in active_nodes:
            sc_client.send_message("/n_free", [node_id])

    return f"Created granular texture at {source_note} with density {density} for {duration} seconds"

@mcp.tool()
async def create_chord_progression(progression="C-G-Am-F", style="pad", tempo=60, duration_per_chord=4.0):
    """
    Play a chord progression with selectable voicing style.

    Args:
        progression: Chord progression as a string (e.g., "C-G-Am-F")
        style: Voicing style ("pad", "staccato", "arpeggio", "power")
        tempo: Beats per minute (40-180)
        duration_per_chord: Duration per chord in beats (1.0-8.0)
    """
    # Validate inputs
    tempo = max(40, min(180, int(tempo)))
    duration_per_chord = max(1.0, min(8.0, float(duration_per_chord)))

    # Calculate beat duration in seconds
    beat_duration = 60.0 / tempo
    chord_duration = beat_duration * duration_per_chord

    # Parse the chord progression
    chords = progression.split("-")
    if not chords:
        return "No chord progression provided"

    # Map chord names to note intervals (from root)
    chord_types = {
        # Major triad
        "": [0, 4, 7],  # Root, major third, perfect fifth
        "M": [0, 4, 7],
        "maj": [0, 4, 7],

        # Minor triad
        "m": [0, 3, 7],  # Root, minor third, perfect fifth
        "min": [0, 3, 7],

        # Seventh chords
        "7": [0, 4, 7, 10],  # Dominant seventh
        "M7": [0, 4, 7, 11],  # Major seventh
        "maj7": [0, 4, 7, 11],
        "m7": [0, 3, 7, 10],  # Minor seventh
        "min7": [0, 3, 7, 10],
        "dim": [0, 3, 6],  # Diminished
        "dim7": [0, 3, 6, 9],  # Diminished seventh
        "aug": [0, 4, 8],  # Augmented

        # Suspended chords
        "sus2": [0, 2, 7],  # Suspended 2nd
        "sus4": [0, 5, 7],  # Suspended 4th

        # Add chords
        "add9": [0, 4, 7, 14],  # Added 9th
        "add11": [0, 4, 7, 17],  # Added 11th

        # Power chord
        "5": [0, 7],  # Root and fifth
    }

    # Map notes to semitones from C
    note_to_semitone = {
        "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
        "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8,
        "A": 9, "A#": 10, "Bb": 10, "B": 11
    }

    # Play each chord in the progression
    base_id = get_node_id()
    node_counter = 0

    for chord_idx, chord_name in enumerate(chords):
        # Parse the chord name to extract root note and type
        if chord_name:
            # Find the root note
            root_note = ""
            chord_type = ""

            # Check for flat/sharp notes first (they have 2 characters)
            if len(chord_name) >= 2 and chord_name[0:2] in note_to_semitone:
                root_note = chord_name[0:2]
                chord_type = chord_name[2:]
            else:
                root_note = chord_name[0:1]
                chord_type = chord_name[1:]

            # Get the root note's semitone value
            if root_note in note_to_semitone:
                root_semitone = note_to_semitone[root_note]

                # Get the intervals for this chord type
                intervals = chord_types.get(chord_type, chord_types[""])  # Default to major if type not recognized

                # Calculate frequencies for each note in the chord
                frequencies = []
                for interval in intervals:
                    # Calculate semitones from C4
                    semitones = root_semitone + interval - 9  # Adjust to be relative to A4
                    # Convert to frequency (A4 = 440Hz)
                    freq = 440.0 * (2.0 ** (semitones / 12.0))
                    frequencies.append(freq)

                # Play the chord according to the selected style
                active_nodes = []

                if style == "pad":
                    # Pad style - all notes play together with slow attack
                    for i, freq in enumerate(frequencies):
                        node_id = base_id + node_counter
                        node_counter += 1

                        # Quieter for inner voices
                        amp = 0.3 if i == 0 or i == len(frequencies) - 1 else 0.2

                        # Small pan variation for stereo width
                        pan = (i / (len(frequencies) - 1)) * 1.6 - 0.8 if len(frequencies) > 1 else 0.0

                        sc_client.send_message("/s_new", ["default", node_id, 0, 0,
                                                          "freq", freq,
                                                          "amp", amp,
                                                          "pan", pan])
                        active_nodes.append(node_id)

                    # Hold for the chord duration
                    time.sleep(chord_duration)

                    # Release all notes
                    for node_id in active_nodes:
                        sc_client.send_message("/n_free", [node_id])

                elif style == "staccato":
                    # Staccato style - all notes play together but shorter
                    for i, freq in enumerate(frequencies):
                        node_id = base_id + node_counter
                        node_counter += 1

                        # Louder for staccato
                        amp = 0.4 if i == 0 or i == len(frequencies) - 1 else 0.3

                        # Small pan variation
                        pan = (i / (len(frequencies) - 1)) * 1.2 - 0.6 if len(frequencies) > 1 else 0.0

                        sc_client.send_message("/s_new", ["default", node_id, 0, 0,
                                                          "freq", freq,
                                                          "amp", amp,
                                                          "pan", pan])
                        active_nodes.append(node_id)

                    # Hold for a shorter duration (1/4 of full duration)
                    time.sleep(chord_duration * 0.25)

                    # Release all notes
                    for node_id in active_nodes:
                        sc_client.send_message("/n_free", [node_id])

                    # Wait for the rest of the duration
                    time.sleep(chord_duration * 0.75)

                elif style == "arpeggio":
                    # Arpeggio style - notes play in sequence
                    note_duration = chord_duration / len(frequencies)

                    for i, freq in enumerate(frequencies):
                        node_id = base_id + node_counter
                        node_counter += 1

                        sc_client.send_message("/s_new", ["default", node_id, 0, 0,
                                                          "freq", freq,
                                                          "amp", 0.3])

                        # Hold for slightly less than the note duration (for separation)
                        time.sleep(note_duration * 0.9)

                        # Release this note
                        sc_client.send_message("/n_free", [node_id])

                        # Small gap between notes
                        time.sleep(note_duration * 0.1)

                elif style == "power":
                    # Power chord style - just root and fifth, louder
                    power_intervals = [0, 7]  # Root and fifth

                    for i, interval in enumerate(power_intervals):
                        if interval in intervals:
                            idx = intervals.index(interval)
                            freq = frequencies[idx]

                            node_id = base_id + node_counter
                            node_counter += 1

                            # Louder for power chords
                            amp = 0.5 if i == 0 else 0.4

                            sc_client.send_message("/s_new", ["default", node_id, 0, 0,
                                                              "freq", freq,
                                                              "amp", amp])
                            active_nodes.append(node_id)

                    # Hold for the chord duration
                    time.sleep(chord_duration)

                    # Release all notes
                    for node_id in active_nodes:
                        sc_client.send_message("/n_free", [node_id])

                else:
                    # Default to pad style if not recognized
                    # Same as pad implementation
                    for i, freq in enumerate(frequencies):
                        node_id = base_id + node_counter
                        node_counter += 1

                        amp = 0.3 if i == 0 or i == len(frequencies) - 1 else 0.2
                        pan = (i / (len(frequencies) - 1)) * 1.6 - 0.8 if len(frequencies) > 1 else 0.0

                        sc_client.send_message("/s_new", ["default", node_id, 0, 0,
                                                          "freq", freq,
                                                          "amp", amp,
                                                          "pan", pan])
                        active_nodes.append(node_id)

                    # Hold for the chord duration
                    time.sleep(chord_duration)

                    # Release all notes
                    for node_id in active_nodes:
                        sc_client.send_message("/n_free", [node_id])
            else:
                # If chord name not recognized, just pause for the duration
                time.sleep(chord_duration)
        else:
            # Empty chord name, just pause
            time.sleep(chord_duration)

    return f"Played {len(chords)}-chord progression in {style} style at {tempo} BPM"

@mcp.tool()
async def create_ambient_soundscape(duration=30, density=0.5, pitch_range="medium", mood="calm"):
    """
    Create an ambient soundscape with various textures and layers.

    Args:
        duration: Length of the soundscape in seconds (10-120)
        density: Density of sound events (0.0-1.0)
        pitch_range: Overall pitch range ("low", "medium", "high", "full")
        mood: Emotional quality ("calm", "dark", "bright", "mysterious", "chaotic")
    """
    # Validate and process inputs
    duration = max(10, min(120, int(duration)))
    density = max(0.0, min(1.0, float(density)))

    # Map pitch range to frequency ranges
    pitch_ranges = {
        "low": (50, 200),
        "medium": (200, 800),
        "high": (800, 3200),
        "full": (50, 3200)
    }
    freq_range = pitch_ranges.get(pitch_range, pitch_ranges["medium"])

    # Map mood to audio characteristics
    moods = {
        "calm": {
            "base_freq": random.uniform(100, 200),
            "amplitude": 0.3,
            "harmonics": [1.0, 2.0, 3.0],  # Consonant harmonics
            "event_duration": (2.0, 8.0)
        },
        "dark": {
            "base_freq": random.uniform(60, 150),
            "amplitude": 0.4,
            "harmonics": [1.0, 1.5, 2.5, 3.5],  # More dissonant harmonics
            "event_duration": (3.0, 10.0)
        },
        "bright": {
            "base_freq": random.uniform(200, 400),
            "amplitude": 0.25,
            "harmonics": [1.0, 2.0, 4.0, 8.0],  # Higher harmonics
            "event_duration": (1.0, 5.0)
        },
        "mysterious": {
            "base_freq": random.uniform(80, 300),
            "amplitude": 0.35,
            "harmonics": [1.0, 1.7, 2.3, 3.3],  # Unusual harmonic ratios
            "event_duration": (4.0, 12.0)
        },
        "chaotic": {
            "base_freq": random.uniform(100, 500),
            "amplitude": 0.5,
            "harmonics": [1.0, 1.3, 2.1, 2.7, 3.4],  # Complex, less consonant harmonics
            "event_duration": (0.5, 4.0)
        }
    }

    # Default to "calm" if mood not recognized
    mood_params = moods.get(mood, moods["calm"])

    # Calculate number of events based on density
    # Higher density = more overlapping sounds
    num_events = int(duration * density * 0.5)
    num_events = max(3, min(20, num_events))  # Reasonable limits

    # Track active nodes for cleanup
    active_nodes = []

    # Base node ID
    base_id = get_node_id()

    # Create background drone
    bg_id = base_id
    sc_client.send_message("/s_new", ["default", bg_id, 0, 0,
                                      "freq", mood_params["base_freq"],
                                      "amp", mood_params["amplitude"] * 0.5])
    active_nodes.append(bg_id)

    # Start time
    start_time = time.time()
    end_time = start_time + duration

    # Generate sound events
    try:
        for i in range(num_events):
            # Calculate when this event should start
            event_start = random.uniform(0, duration * 0.8)  # Start within first 80% of total duration
            time_to_wait = start_time + event_start - time.time()

            if time_to_wait > 0:
                time.sleep(time_to_wait)

            # Check if we've exceeded our duration
            if time.time() >= end_time:
                break

            # Choose a harmonic ratio from the mood's harmonics
            harmonic = random.choice(mood_params["harmonics"])

            # Calculate frequency for this event
            event_freq = mood_params["base_freq"] * harmonic

            # Ensure frequency is within the desired pitch range
            event_freq = max(freq_range[0], min(freq_range[1], event_freq))

            # Randomize amplitude slightly
            event_amp = mood_params["amplitude"] * random.uniform(0.5, 1.0)

            # Determine duration for this event
            min_dur, max_dur = mood_params["event_duration"]
            event_dur = random.uniform(min_dur, max_dur)

            # Ensure event doesn't exceed total duration
            remaining_time = end_time - time.time()
            event_dur = min(event_dur, remaining_time)

            if event_dur <= 0:
                continue  # Skip if no time left

            # Create the event sound
            event_id = base_id + 100 + i
            sc_client.send_message("/s_new", ["default", event_id, 0, 0,
                                              "freq", event_freq,
                                              "amp", event_amp])
            active_nodes.append(event_id)

            # For longer events, add some modulation
            if event_dur > 3.0 and random.random() < 0.7:
                # Random LFO-like frequency modulation
                for j in range(int(event_dur / 0.5)):  # Every 0.5 seconds
                    if time.time() >= end_time:
                        break

                    # Small random frequency shifts
                    mod_freq = event_freq * random.uniform(0.98, 1.02)
                    sc_client.send_message("/n_set", [event_id, "freq", mod_freq])

                    time.sleep(0.5)
            else:
                # For shorter events, just wait the duration
                time.sleep(event_dur)

            # Free this event's node unless it's a long event that should continue
            if event_dur < 5.0 or random.random() < 0.7:
                sc_client.send_message("/n_free", [event_id])
                active_nodes.remove(event_id)

        # Wait until the full duration has passed
        remaining = end_time - time.time()
        if remaining > 0:
            time.sleep(remaining)

    finally:
        # Clean up all active nodes
        for node in active_nodes:
            sc_client.send_message("/n_free", [node])

    return f"Created a {mood} ambient soundscape lasting {duration} seconds with {num_events} sound events"

@mcp.tool()
async def create_generative_rhythm(style="minimal", duration=20, tempo=120, intensity=0.5):
    """
    Create a generative rhythm that evolves over time.

    Args:
        style: Rhythm style ("minimal", "techno", "glitch", "jazz", "ambient")
        duration: Length of the rhythm in seconds (5-120)
        tempo: Beats per minute (60-240)
        intensity: Overall intensity/complexity (0.0-1.0)
    """
    # Validate inputs
    duration = max(5, min(120, int(duration)))
    tempo = max(60, min(240, int(tempo)))
    intensity = max(0.0, min(1.0, float(intensity)))

    # Calculate beat duration in seconds
    beat_duration = 60 / tempo

    # Map styles to rhythm characteristics
    styles = {
        "minimal": {
            "pulse_rate": 0.8,         # How often pulses occur (0-1)
            "variation_rate": 0.2,     # How often the pattern changes (0-1)
            "complexity": 0.3,         # Rhythmic complexity (0-1)
            "syncopation": 0.2,        # Off-beat emphasis (0-1)
            "swing": 0.1               # Timing swing factor (0-1)
        },
        "techno": {
            "pulse_rate": 0.9,
            "variation_rate": 0.3,
            "complexity": 0.5,
            "syncopation": 0.4,
            "swing": 0.2
        },
        "glitch": {
            "pulse_rate": 0.7,
            "variation_rate": 0.8,
            "complexity": 0.9,
            "syncopation": 0.7,
            "swing": 0.3
        },
        "jazz": {
            "pulse_rate": 0.6,
            "variation_rate": 0.5,
            "complexity": 0.7,
            "syncopation": 0.8,
            "swing": 0.7
        },
        "ambient": {
            "pulse_rate": 0.4,
            "variation_rate": 0.2,
            "complexity": 0.2,
            "syncopation": 0.1,
            "swing": 0.05
        }
    }

    # Default to "minimal" if style not recognized
    style_params = styles.get(style, styles["minimal"])

    # Adjust parameters based on intensity
    for param in style_params:
        # Intensity scales the parameter up or down from its base value
        # Higher intensity = more of everything
        style_params[param] *= (0.7 + intensity * 0.6)  # Scale between 70% and 130%
        style_params[param] = min(1.0, style_params[param])  # Cap at 1.0

    # Calculate number of beats
    num_beats = int(duration / beat_duration)
    num_beats = max(4, min(240, num_beats))  # Reasonable limits

    # Base patterns (16-step)
    # Initialize with some basic patterns based on style
    if style == "minimal":
        kick_pattern = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]  # Four on the floor
        snare_pattern = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]  # Backbeat
        hihat_pattern = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]  # Eighth notes
    elif style == "techno":
        kick_pattern = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
        snare_pattern = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
        hihat_pattern = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # 16th notes
    elif style == "glitch":
        # Random patterns for glitch
        kick_pattern = [random.randint(0, 1) for _ in range(16)]
        snare_pattern = [random.randint(0, 1) for _ in range(16)]
        hihat_pattern = [random.randint(0, 1) for _ in range(16)]
    elif style == "jazz":
        # Jazz-influenced pattern
        kick_pattern = [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0]
        snare_pattern = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
        hihat_pattern = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    else:  # ambient or default
        # Sparse pattern
        kick_pattern = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
        snare_pattern = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        hihat_pattern = [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0]

    # Base node ID
    base_id = get_node_id()

    # Play the generative rhythm
    try:
        for beat in range(num_beats):
            # Every 8 or 16 beats, potentially evolve the pattern based on variation_rate
            if (beat % 16 == 0) and (random.random() < style_params["variation_rate"]):
                # Evolve kick pattern
                for i in range(16):
                    if random.random() < style_params["complexity"] * 0.5:
                        # Flip a bit
                        kick_pattern[i] = 1 - kick_pattern[i]

                # Evolve snare pattern
                for i in range(16):
                    if random.random() < style_params["complexity"] * 0.3:
                        # Flip a bit
                        snare_pattern[i] = 1 - snare_pattern[i]

                # Evolve hihat pattern
                for i in range(16):
                    if random.random() < style_params["complexity"] * 0.7:
                        # Flip a bit
                        hihat_pattern[i] = 1 - hihat_pattern[i]

            # Current position in the 16-step pattern
            step = beat % 16

            # Add swing
            swing_amount = 0
            if step % 2 == 1:  # Only apply swing to off-beats
                swing_amount = beat_duration * style_params["swing"] * 0.5

            # Play drum sounds based on patterns
            # Add randomization based on complexity
            if kick_pattern[step] == 1 and (random.random() < style_params["pulse_rate"]):
                kick_id = base_id + beat
                sc_client.send_message("/s_new", ["default", kick_id, 0, 0, "freq", 60, "amp", 0.5])

            if snare_pattern[step] == 1 and (random.random() < style_params["pulse_rate"]):
                snare_id = base_id + 1000 + beat
                sc_client.send_message("/s_new", ["default", snare_id, 0, 0, "freq", 300, "amp", 0.3])

            if hihat_pattern[step] == 1 and (random.random() < style_params["pulse_rate"]):
                hihat_id = base_id + 2000 + beat
                sc_client.send_message("/s_new", ["default", hihat_id, 0, 0, "freq", 1200, "amp", 0.2])

            # Add occasional random accents based on syncopation
            if random.random() < style_params["syncopation"] * 0.2:
                accent_id = base_id + 3000 + beat
                sc_client.send_message("/s_new", ["default", accent_id, 0, 0,
                                                  "freq", random.choice([800, 1600, 2400]),
                                                  "amp", 0.15])

            # Wait for this beat (including swing)
            time.sleep(beat_duration + swing_amount)

            # Free all sounds from this beat
            potential_ids = [
                base_id + beat,          # Kick
                base_id + 1000 + beat,   # Snare
                base_id + 2000 + beat,   # Hihat
                base_id + 3000 + beat    # Accent
            ]
            for node_id in potential_ids:
                sc_client.send_message("/n_free", [node_id])

    except Exception as e:
        return f"Error in generative rhythm: {str(e)}"

    return f"Created a generative {style} rhythm at {tempo} BPM for {duration} seconds with intensity {intensity}"

if __name__ == "__main__":
    print("SuperCollider OSC MCP Server running")
    print("------------------------------------")
    print("This server provides the following tools:")
    print("\n=== Basic Sound Generation ===")
    print("1. play_example_osc - Play a simple example sound")
    print("2. play_melody - Play a procedurally generated melody")
    print("3. create_drum_pattern - Play a drum pattern")
    print("4. play_synth - Play a synthesizer with various waveforms")
    print("5. create_sequence - Create a musical sequence from a pattern string")

    print("\n=== Advanced Synthesis ===")
    print("6. create_lfo_modulation - Create an LFO modulation effect on a synthesizer parameter")
    print("7. create_layered_synth - Create a rich, layered synthesizer with multiple oscillators")
    print("8. create_granular_texture - Create a granular synthesis texture with small sonic grains")
    print("9. create_chord_progression - Play a chord progression with selectable voicing style")

    print("\n=== Soundscape Generation ===")
    print("10. create_ambient_soundscape - Create an ambient soundscape with textures and layers")
    print("11. create_generative_rhythm - Create a generative rhythm that evolves over time")

    print("\nTo test locally, run: python -m mcp.run server.py")