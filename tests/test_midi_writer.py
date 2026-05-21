from harmony_cloud.midi_writer import write_midi


def test_write_midi(tmp_path):
    # Create a dummy voicing with six notes
    voicings = [[60, 64, 67, 71, 74, 77]]
    midi_file = tmp_path / "test_output.mid"
    write_midi(voicings, midi_file.as_posix(), tempo=120)
    assert midi_file.exists()
