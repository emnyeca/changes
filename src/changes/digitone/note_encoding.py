"""Digitone backend specific note-name encoding helpers."""

from __future__ import annotations

_DIGITONE_PITCH_CLASSES = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)


def midi_to_digitone_display_note_name(midi_note: int) -> str:
    """Convert MIDI note number to Digitone display note naming.

    Digitone toolkit/event schema treats C5 as MIDI 60.
    """
    if midi_note < 0 or midi_note > 127:
        raise ValueError(f"MIDI note out of range: {midi_note}")
    pitch_class = _DIGITONE_PITCH_CLASSES[midi_note % 12]
    octave = midi_note // 12
    return f"{pitch_class}{octave}"
