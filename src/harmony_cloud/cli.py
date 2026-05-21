"""
Command-line interface for Harmony Cloud.

This module provides a simple CLI to generate six-voice chord clouds from a YAML
progression file and write them to a MIDI file. This is a minimal example and
can be extended with additional options as the project grows.
"""

import argparse

from .chord_parser import parse_progression
from .voice_leading import generate_voice_leading
from .midi_writer import write_midi


def main() -> None:
    """Run the Harmony Cloud CLI."""
    parser = argparse.ArgumentParser(
        description="Generate six-voice chord clouds and export to MIDI"
    )
    parser.add_argument(
        "input",
        help="Path to a YAML file containing the chord progression",
    )
    parser.add_argument(
        "--output",
        default="output.mid",
        help="Path to write the resulting MIDI file",
    )
    parser.add_argument(
        "--tempo",
        type=int,
        default=600,
        help="BPM to use when recording the MIDI for high-speed capture",
    )
    args = parser.parse_args()

    progression = parse_progression(args.input)
    voices = generate_voice_leading(progression)
    write_midi(voices, args.output, tempo=args.tempo)


if __name__ == "__main__":
    main()
