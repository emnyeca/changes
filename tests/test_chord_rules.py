from changes.harmonic_context import (
    build_local_pitch_collection,
    chord_tone_pitch_classes,
    extract_output_chord_tone_set,
    select_scale_collection,
)


def _pcs_to_names(pcs: set[int] | frozenset[int] | tuple[int, ...]) -> list[str]:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return sorted(names[p] for p in pcs)


def test_chord_tone_pitch_classes_core_qualities():
    assert _pcs_to_names(chord_tone_pitch_classes("Cmaj7")) == ["B", "C", "E", "G"]
    assert _pcs_to_names(chord_tone_pitch_classes("Am7")) == ["A", "C", "E", "G"]
    assert _pcs_to_names(chord_tone_pitch_classes("Dm7")) == ["A", "C", "D", "F"]
    assert _pcs_to_names(chord_tone_pitch_classes("G7")) == ["B", "D", "F", "G"]


def test_local_pitch_collection_for_am7_in_blue_moon_head():
    progression = [["Cmaj7", "Am7", "Dm7", "G7"]]
    local = build_local_pitch_collection(progression, 1, circular=True)
    assert _pcs_to_names(local) == ["A", "B", "C", "D", "E", "F", "G"]


def test_selected_collection_am7_in_c_major_contains_f_not_f_sharp():
    progression = [["Cmaj7", "Am7", "Dm7", "G7"]]
    local = build_local_pitch_collection(progression, 1, circular=True)
    selected = select_scale_collection("Am7", local)

    assert 5 in selected.pitch_classes  # F
    assert 6 not in selected.pitch_classes  # F#


def test_output_chord_tone_set_blue_moon_head_expected_pitch_classes():
    progression = ["Cmaj7", "Am7", "Dm7", "G7"]
    expected = {
        "Cmaj7": ["A", "B", "C", "D", "E", "G"],
        "Am7": ["A", "B", "C", "E", "F", "G"],
        "Dm7": ["A", "B", "C", "D", "E", "F"],
        "G7": ["A", "B", "D", "E", "F", "G"],
    }

    for idx, symbol in enumerate(progression):
        local = build_local_pitch_collection(progression, idx, circular=True)
        selected = select_scale_collection(symbol, local)
        output = extract_output_chord_tone_set(symbol, selected)
        assert _pcs_to_names(output) == expected[symbol]


def test_regression_guard_dm7_in_c_major_context_is_not_legacy_m69_set():
    progression = ["Dm7", "G7", "Cmaj7"]
    local = build_local_pitch_collection(progression, 0, circular=True)
    selected = select_scale_collection("Dm7", local)
    output = extract_output_chord_tone_set("Dm7", selected)

    assert _pcs_to_names(output) == ["A", "B", "C", "D", "E", "F"]
    assert _pcs_to_names(output) != ["A", "B", "D", "E", "F", "G"]
