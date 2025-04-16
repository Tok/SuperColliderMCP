"""
Soundscape generation tools for SuperCollider OSC MCP.

This module provides tools for creating ambient soundscapes and generative rhythms
using SuperCollider via OSC.
"""

import random
import time
import json
import math
from mcp.server.fastmcp import FastMCP
from pythonosc import udp_client

# Use the global SC client
from server import sc_client, get_node_id

# Register tools with the MCP server
mcp = FastMCP("Super-Collider-OSC-MCP")

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
