from __future__ import annotations

from changes.harmonic_context import (
    build_local_pitch_collection,
    extract_output_chord_tone_set,
    select_scale_collection,
)


_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _pcs_to_names(pcs: set[int] | frozenset[int] | tuple[int, ...]) -> list[str]:
    return sorted(_NAMES[p] for p in pcs)


def test_local_pitch_collection_skips_repeated_same_chord_blocks():
    progression = ["Cmaj7", "Am7", "Am7", "Dm7", "G7"]
    # Index 2 is repeated Am7; context should still resolve prev=Cmaj7, next=Dm7.
    local = build_local_pitch_collection(progression, 2, circular=True)
    assert _pcs_to_names(local) == ["A", "B", "C", "D", "E", "F", "G"]


def test_local_pitch_collection_circular_lookup_at_edges():
    progression = ["Cmaj7", "Am7", "Dm7", "G7"]

    local_head = build_local_pitch_collection(progression, 0, circular=True)
    local_tail = build_local_pitch_collection(progression, 3, circular=True)

    assert _pcs_to_names(local_head) == ["A", "B", "C", "D", "E", "F", "G"]
    assert _pcs_to_names(local_tail) == ["A", "B", "C", "D", "E", "F", "G"]


def test_local_pitch_collection_single_chord_progression_is_safe():
    progression = ["Bm7"]
    local = build_local_pitch_collection(progression, 0, circular=True)
    assert _pcs_to_names(local) == ["A", "B", "D", "F#"]


def test_selected_collection_for_single_bm7_prefers_dorian_color():
    local = build_local_pitch_collection(["Bm7"], 0, circular=True)
    selected = select_scale_collection("Bm7", local)

    assert 8 in selected.pitch_classes  # G#
    output = extract_output_chord_tone_set("Bm7", selected)
    assert _pcs_to_names(output) == ["A", "B", "C#", "D", "F#", "G#"]


def test_c_major_ii_v_i_output_sets():
    progression = ["Dm7", "G7", "Cmaj7"]
    expected = {
        "Dm7": ["A", "B", "C", "D", "E", "F"],
        "G7": ["A", "B", "D", "E", "F", "G"],
        "Cmaj7": ["A", "B", "C", "D", "E", "G"],
    }

    for idx, symbol in enumerate(progression):
        local = build_local_pitch_collection(progression, idx, circular=True)
        selected = select_scale_collection(symbol, local)
        output = extract_output_chord_tone_set(symbol, selected)
        assert _pcs_to_names(output) == expected[symbol]
