"""
Rhythm generation module for SuperCollider.

This module provides functions for generating and playing rhythmic patterns through SuperCollider.
"""

import random
import time
from .osc import SuperColliderClient

# Predefined drum patterns (1 = hit, 0 = rest)
PATTERNS = {
    "four_on_floor": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    },
    "breakbeat": {
        "kick":  [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1],
        "hihat": [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0],
    },
    "shuffle": {
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    }
}

def generate_random_pattern(length=16):
    """
    Generate a random drum pattern.
    
    Args:
        length (int): Length of the pattern.
        
    Returns:
        dict: A dictionary with kick, snare, and hihat patterns.
    """
    pattern = {
        "kick": [random.choice([0, 1, 0]) for _ in range(length)],  # Less kicks
        "snare": [random.choice([0, 0, 1]) for _ in range(length)], # Even less snares
        "hihat": [random.choice([0, 1, 1, 1]) for _ in range(length)] # More hi-hats
    }
    
    # Ensure at least some beats
    if sum(pattern["kick"]) == 0:
        pattern["kick"][0] = 1  # Always hit on first beat
    if sum(pattern["snare"]) == 0:
        pattern["snare"][4] = 1  # Classic snare on beat 2
    if sum(pattern["hihat"]) < 2:
        pattern["hihat"] = [1 if i % 2 == 0 else 0 for i in range(length)]  # Basic hi-hat pattern
    
    return pattern

def play_drum_pattern(pattern_type="four_on_floor", beats=16, tempo=120, client=None):
    """
    Play a drum pattern through SuperCollider.
    
    Args:
        pattern_type (str): Type of pattern ("four_on_floor", "breakbeat", "shuffle", "random").
        beats (int): Number of beats to play.
        tempo (int): Beats per minute.
        client (SuperColliderClient): Client to use (creates one if None).
        
    Returns:
        bool: True if successful.
    """
    # Validate inputs
    beats = max(4, min(32, int(beats)))  # Clamp between 4-32 beats
    tempo = max(60, min(240, int(tempo)))  # Clamp between 60-240 BPM
    
    # Create client if needed
    if client is None:
        client = SuperColliderClient()
    
    # Select or generate pattern
    if pattern_type == "random":
        pattern = generate_random_pattern()
    else:
        # Use predefined pattern or default to four_on_floor
        pattern = PATTERNS.get(pattern_type, PATTERNS["four_on_floor"])
    
    # Calculate beat duration
    beat_duration = 60 / tempo
    
    # Play the drum pattern
    pattern_length = len(pattern["kick"])  # Assume all have same length
    
    for beat in range(beats):
        beat_idx = beat % pattern_length  # Loop the pattern
        
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
    
    return True
