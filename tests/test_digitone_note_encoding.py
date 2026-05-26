from __future__ import annotations

from changes.digitone.note_encoding import midi_to_digitone_display_note_name


def test_digitone_note_display_mapping_examples():
    assert midi_to_digitone_display_note_name(36) == "C3"
    assert midi_to_digitone_display_note_name(48) == "C4"
    assert midi_to_digitone_display_note_name(60) == "C5"
    assert midi_to_digitone_display_note_name(61) == "C#5"
