"""
Melody generation module for SuperCollider.

This module provides functions for generating and playing melodies through SuperCollider.
"""

import random
import time
from .osc import SuperColliderClient

# Define scale patterns (semitones from root)
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11, 12],
    "minor": [0, 2, 3, 5, 7, 8, 10, 12],
    "pentatonic": [0, 2, 4, 7, 9, 12],
    "blues": [0, 3, 5, 6, 7, 10, 12]
}

def generate_melody(scale="major", note_count=16, base_freq=440):
    """
    Generate a melody based on a scale.
    
    Args:
        scale (str): The scale to use ("major", "minor", "pentatonic", "blues").
        note_count (int): Number of notes in the melody.
        base_freq (float): Base frequency for calculations.
        
    Returns:
        list: A list of (frequency, duration) tuples.
    """
    # Validate scale
    if scale not in SCALES:
        scale = "major"
    
    # Generate a random root note and octave
    root_note = random.randint(0, 11)
    octave = random.randint(0, 2)
    
    # Create a melody pattern
    melody = []
    for _ in range(note_count):
        # Select a note from the scale
        scale_degree = random.randint(0, len(SCALES[scale])-1)
        note = root_note + SCALES[scale][scale_degree] + (octave * 12)
        
        # Convert to frequency (equal temperament)
        freq = base_freq * (2 ** ((note - 9) / 12))
        
        # Duration (whole, half, quarter notes)
        duration_options = [0.25, 0.5, 1.0]
        duration_weights = [0.5, 0.3, 0.2]  # More likely to use shorter notes
        duration = random.choices(duration_options, duration_weights)[0]
        
        melody.append((freq, duration))
    
    return melody

def play_melody(melody, tempo=120, client=None):
    """
    Play a melody through SuperCollider.
    
    Args:
        melody (list): A list of (frequency, duration) tuples.
        tempo (int): Beats per minute.
        client (SuperColliderClient): Client to use (creates one if None).
        
    Returns:
        bool: True if successful.
    """
    # Create client if needed
    if client is None:
        client = SuperColliderClient()
    
    # Calculate beat duration
    beat_duration = 60 / tempo
    
    # Play the melody
    for i, (freq, duration) in enumerate(melody):
        # Create a new synth for each note
        synth_id = 2000 + i
        
        # Play note
        client.create_synth("default", synth_id, 0, 0, freq=freq, amp=0.3)
        
        # Wait for the note duration
        time.sleep(duration * beat_duration)
        
        # Free the synth
        client.free_node(synth_id)
    
    return True

def play_scale(scale="major", tempo=120, direction="both", client=None):
    """
    Play a scale up and optionally down.
    
    Args:
        scale (str): The scale to use ("major", "minor", "pentatonic", "blues").
        tempo (int): Beats per minute.
        direction (str): "up", "down", or "both".
        client (SuperColliderClient): Client to use (creates one if None).
        
    Returns:
        bool: True if successful.
    """
    # Validate scale
    if scale not in SCALES:
        scale = "major"
    
    # Create client if needed
    if client is None:
        client = SuperColliderClient()
    
    # Calculate beat duration
    beat_duration = 60 / tempo
    
    # Base frequency (A4 = 440Hz)
    base_freq = 440
    
    # Get the scale intervals
    intervals = SCALES[scale]
    
    # Play up
    if direction in ["up", "both"]:
        for i, semitones in enumerate(intervals):
            # Calculate frequency
            freq = base_freq * (2 ** (semitones / 12))
            
            # Play the note
            node_id = 1000 + i
            client.create_synth("default", node_id, 0, 0, freq=freq, amp=0.3)
            
            # Wait for the note duration
            time.sleep(beat_duration * 0.9)  # Slightly shorter for legato effect
            
            # Free the node
            client.free_node(node_id)
    
    # Play down (excluding the first and last notes which would be duplicated)
    if direction in ["down", "both"] and len(intervals) > 2:
        for i, semitones in enumerate(reversed(intervals[1:-1])):
            # Calculate frequency
            freq = base_freq * (2 ** (semitones / 12))
            
            # Play the note
            node_id = 2000 + i
            client.create_synth("default", node_id, 0, 0, freq=freq, amp=0.3)
            
            # Wait for the note duration
            time.sleep(beat_duration * 0.9)
            
            # Free the node
            client.free_node(node_id)
    
    return True
