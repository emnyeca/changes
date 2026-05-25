"""Utilities for converting note names and MIDI note numbers."""

from __future__ import annotations

import re

_NOTE_TO_SEMITONE = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}

_SEMITONE_TO_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_NOTE_RE = re.compile(r"^([A-G](?:#|b)?)(-?\d+)$")


def pitch_class_to_semitone(note: str) -> int:
    """Convert pitch class name (e.g., C, F#, Bb) to semitone 0..11."""
    if note not in _NOTE_TO_SEMITONE:
        raise ValueError(f"Unsupported note name: {note}")
    return _NOTE_TO_SEMITONE[note]


def semitone_to_pitch_class(semitone: int) -> str:
    """Convert semitone number to canonical sharp pitch class name."""
    return _SEMITONE_TO_SHARP[semitone % 12]


def note_name_to_midi(note_name: str) -> int:
    """Convert note name like C4, F#3, Bb2 to MIDI note number."""
    m = _NOTE_RE.match(note_name)
    if not m:
        raise ValueError(f"Invalid note name: {note_name}")
    pitch, octave_str = m.groups()
    octave = int(octave_str)
    midi = (octave + 1) * 12 + pitch_class_to_semitone(pitch)
    if midi < 0 or midi > 127:
        raise ValueError(f"MIDI note out of range: {midi}")
    return midi


def midi_to_note_name(midi_note: int) -> str:
    """Convert MIDI note number 0..127 to note name (sharp notation)."""
    if midi_note < 0 or midi_note > 127:
        raise ValueError(f"MIDI note out of range: {midi_note}")
    octave = (midi_note // 12) - 1
    semitone = midi_note % 12
    return f"{semitone_to_pitch_class(semitone)}{octave}"


def root_to_midi(root: str, octave: int = 3) -> int:
    """Convert pitch class root to MIDI at the given octave."""
    return note_name_to_midi(f"{root}{octave}")
