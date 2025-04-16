"""
Main entry point for the SuperCollider OSC MCP package.

This script provides a CLI for interacting with SuperCollider via OSC.
"""

import argparse
import time
from supercollidermcp.osc import SuperColliderClient
from supercollidermcp.melody import play_scale, generate_melody, play_melody
from supercollidermcp.rhythm import play_drum_pattern

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="SuperCollider OSC MCP")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Note command
    note_parser = subparsers.add_parser("note", help="Play a simple note")
    note_parser.add_argument("--freq", type=float, default=440, help="Frequency in Hz (default: 440)")
    note_parser.add_argument("--amp", type=float, default=0.5, help="Amplitude (default: 0.5)")
    note_parser.add_argument("--duration", type=float, default=1.0, help="Duration in seconds (default: 1.0)")
    
    # Scale command
    scale_parser = subparsers.add_parser("scale", help="Play a scale")
    scale_parser.add_argument("--scale", type=str, default="major", 
                             choices=["major", "minor", "pentatonic", "blues"],
                             help="Scale type (default: major)")
    scale_parser.add_argument("--tempo", type=int, default=120, help="Tempo in BPM (default: 120)")
    scale_parser.add_argument("--direction", type=str, default="both", 
                             choices=["up", "down", "both"],
                             help="Direction to play (default: both)")
    
    # Melody command
    melody_parser = subparsers.add_parser("melody", help="Play a procedurally generated melody")
    melody_parser.add_argument("--scale", type=str, default="major", 
                              choices=["major", "minor", "pentatonic", "blues"],
                              help="Scale type (default: major)")
    melody_parser.add_argument("--tempo", type=int, default=120, help="Tempo in BPM (default: 120)")
    melody_parser.add_argument("--notes", type=int, default=16, help="Number of notes (default: 16)")
    
    # Drums command
    drums_parser = subparsers.add_parser("drums", help="Play a drum pattern")
    drums_parser.add_argument("--pattern", type=str, default="four_on_floor", 
                             choices=["four_on_floor", "breakbeat", "shuffle", "random"],
                             help="Pattern type (default: four_on_floor)")
    drums_parser.add_argument("--beats", type=int, default=16, help="Number of beats (default: 16)")
    drums_parser.add_argument("--tempo", type=int, default=120, help="Tempo in BPM (default: 120)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create client
    client = SuperColliderClient()
    
    # Handle commands
    if args.command == "note":
        node_id = client.play_note(frequency=args.freq, amplitude=args.amp, duration=args.duration)
        print(f"Played note at {args.freq}Hz with amplitude {args.amp} for {args.duration}s (node {node_id})")
    
    elif args.command == "scale":
        play_scale(scale=args.scale, tempo=args.tempo, direction=args.direction, client=client)
        print(f"Played {args.scale} scale {args.direction} at {args.tempo} BPM")
    
    elif args.command == "melody":
        melody = generate_melody(scale=args.scale, note_count=args.notes)
        play_melody(melody=melody, tempo=args.tempo, client=client)
        print(f"Played {args.notes}-note melody in {args.scale} scale at {args.tempo} BPM")
    
    elif args.command == "drums":
        play_drum_pattern(pattern_type=args.pattern, beats=args.beats, tempo=args.tempo, client=client)
        print(f"Played {args.pattern} drum pattern with {args.beats} beats at {args.tempo} BPM")
    
    else:
        parser.print_help()
        print("\nTip: You can also use the Claude Desktop Model Context Protocol (MCP) integration with the following configuration:")
        print('''
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
}''')


if __name__ == "__main__":
    main()
