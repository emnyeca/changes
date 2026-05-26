"""Command-line interface for Changes generic MIDI export."""

import argparse

from .chord_parser import parse_progression
from .voicing import progression_to_voicings
from .voice_leading import generate_voice_leading
from .midi_writer import write_midi


def main() -> None:
    """Run the Changes CLI."""
    parser = argparse.ArgumentParser(
        description="Generate six-voice chord clouds and export to generic MIDI"
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
        default=120,
        help="BPM for generic MIDI export",
    )
    args = parser.parse_args()

    progression = parse_progression(args.input)
    voicings = progression_to_voicings(progression)
    voices_led = generate_voice_leading(voicings)
    write_midi(voices_led, args.output, tempo=args.tempo)


if __name__ == "__main__":
    main()
