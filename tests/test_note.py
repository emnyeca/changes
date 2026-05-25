from changes.note import midi_to_note_name, note_name_to_midi, root_to_midi


def test_note_name_midi_roundtrip():
    assert note_name_to_midi("C4") == 60
    assert note_name_to_midi("F#3") == 54
    assert midi_to_note_name(60) == "C4"


def test_root_to_midi():
    assert root_to_midi("D", 3) == 50
    assert root_to_midi("G", 3) == 55
