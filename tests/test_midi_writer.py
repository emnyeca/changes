import mido

from harmony_cloud.midi_writer import write_midi, write_midi_with_events


def test_write_midi(tmp_path):
    # Create a dummy voicing with six notes
    voicings = [[60, 64, 67, 71, 74, 77]]
    midi_file = tmp_path / "test_output.mid"
    write_midi(voicings, midi_file.as_posix(), tempo=120)
    assert midi_file.exists()


def test_write_midi_with_events_merges_held_notes(tmp_path):
    voicings = [
        [60, 64],
        [60, 65],
        [62, 65],
    ]
    events = [
        {"duration_steps": 1},
        {"duration_steps": 2},
        {"duration_steps": 1},
    ]

    midi_file = tmp_path / "test_output_held.mid"
    write_midi_with_events(voicings, events, midi_file.as_posix(), tempo=120)

    assert midi_file.exists()

    mid = mido.MidiFile(midi_file.as_posix())
    track0_notes_on = [msg.note for msg in mid.tracks[0] if msg.type == "note_on" and msg.velocity > 0]
    track1_notes_on = [msg.note for msg in mid.tracks[1] if msg.type == "note_on" and msg.velocity > 0]

    assert track0_notes_on == [60, 62]
    assert track1_notes_on == [64, 65]


def test_write_midi_with_events_allows_retrigger_and_channel_map(tmp_path):
    voicings = [
        [60, 64],
        [60, 64],
    ]
    events = [
        {"duration_steps": 1},
        {"duration_steps": 1},
    ]

    midi_file = tmp_path / "test_output_retrigger.mid"
    write_midi_with_events(
        voicings,
        events,
        midi_file.as_posix(),
        tempo=120,
        hold_same_pitch=False,
        channel_map=[3, 3, 3, 3, 3, 3],
    )

    mid = mido.MidiFile(midi_file.as_posix())
    track0 = [msg for msg in mid.tracks[0] if msg.type in ("note_on", "note_off")]

    note_on_events = [msg for msg in track0 if msg.type == "note_on" and msg.velocity > 0]
    assert len(note_on_events) == 2
    assert all(msg.channel == 2 for msg in note_on_events)
