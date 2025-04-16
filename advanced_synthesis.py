"""
Advanced synthesis tools for SuperCollider OSC MCP.

This module provides tools for more complex sound synthesis techniques
and audio manipulations using SuperCollider via OSC.
"""

import random
import time
import json
import math
from mcp.server.fastmcp import FastMCP
from pythonosc import udp_client

# Use the global SC client and helpers
from server import sc_client, get_node_id, note_to_freq

# Register tools with the MCP server
mcp = FastMCP("Super-Collider-OSC-MCP")

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
