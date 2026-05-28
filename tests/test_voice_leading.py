import pytest

from changes.harmonic_context import (
    build_local_pitch_collection,
    extract_output_chord_tone_set,
    select_scale_collection,
)
from changes.voicing import progression_to_voicings
from changes.voice_leading import RegisterFitError, fit_bounded_voice_vector, generate_voice_leading


def _movement(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def _pc_set(notes):
    return {n % 12 for n in notes}


def test_ii_v_i_voice_leading_preserves_context_selected_pitch_class_sets():
    progression = [["Dm7", "G7", "Cmaj7"]]
    raw = progression_to_voicings(progression, base_octave=3)
    led = generate_voice_leading(raw)

    assert len(led) == 3
    assert all(len(chord) == 6 for chord in led)

    flat = [c for bar in progression for c in bar]
    expected_pc_sets = []
    for idx, symbol in enumerate(flat):
        local = build_local_pitch_collection(flat, idx, circular=True)
        selected = select_scale_collection(symbol, local)
        expected_pc_sets.append(set(extract_output_chord_tone_set(symbol, selected)))

    for idx, chord in enumerate(led):
        assert _pc_set(chord) == expected_pc_sets[idx]
        assert len(_pc_set(chord)) == 6

    # ii->V and V->I should both be controlled movement.
    assert _movement(led[0], led[1]) <= 18
    assert _movement(led[1], led[2]) <= 18


def test_blue_moon_head_voice_leading_keeps_am7_with_f_not_f_sharp():
    progression = [["Cmaj7", "Am7", "Dm7", "G7"]]
    raw = progression_to_voicings(progression, base_octave=3)
    led = generate_voice_leading(raw)

    am7_pc = _pc_set(led[1])
    assert 5 in am7_pc  # F
    assert 6 not in am7_pc  # F#


def test_bounded_voice_sliding_exact_example_1_preserves_lane_order():
    target = [47, 52, 55, 57, 50, 60]  # B3 E4 G4 A4 D4 C5
    fitted = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)
    assert fitted == [48, 52, 55, 57, 50, 59]  # C4 E4 G4 A4 D4 B4


def test_bounded_voice_sliding_exact_example_2_preserves_lane_order():
    target = [52, 55, 60, 62, 69, 71]  # E4 G4 C5 D5 A5 B5
    fitted = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)
    assert fitted == [52, 55, 60, 62, 69, 59]  # E4 G4 C5 D5 A5 B4


def test_bounded_voice_sliding_in_range_identity():
    target = [48, 52, 55, 57, 59, 62]  # C4 E4 G4 A4 B4 D5
    fitted = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)
    assert fitted == target


def test_bounded_voice_sliding_multiple_out_of_range_notes_is_deterministic_and_preserves_multiset():
    target = [35, 74, 55, 80, 69, 40]
    reference = [48, 52, 55, 57, 59, 62]
    out1 = fit_bounded_voice_vector(target, reference, min_midi=48, max_midi=69)
    out2 = fit_bounded_voice_vector(target, reference, min_midi=48, max_midi=69)

    assert out1 == out2
    assert all(48 <= n <= 69 for n in out1)
    assert len(set(out1)) == 6
    assert sorted(n % 12 for n in out1) == sorted(n % 12 for n in target)


def test_bounded_voice_sliding_impossible_realization_raises_register_fit_error():
    target = [48, 60, 72, 84, 96, 108]
    reference = [48, 50, 52, 53, 55, 57]
    with pytest.raises(RegisterFitError, match="No in-range realization"):
        fit_bounded_voice_vector(target, reference, min_midi=48, max_midi=52, context="unit_test")


def test_generate_voice_leading_uses_previous_bounded_output_as_next_reference_state():
    voicings = [
        [47, 52, 55, 57, 50, 60],
        [44, 49, 52, 54, 57, 59],
    ]

    bounded = generate_voice_leading(voicings, min_midi=48, max_midi=69)
    assert bounded[0] == [48, 52, 55, 57, 50, 59]
    assert all(48 <= note <= 69 for note in bounded[1])

    # Regression guard: if a future refactor applies fitting only as a final postprocess,
    # this sequence should diverge from bounded sequential generation.
    postprocess_like = [
        fit_bounded_voice_vector(voicings[0], voicings[0], min_midi=48, max_midi=69),
        fit_bounded_voice_vector(voicings[1], voicings[1], min_midi=48, max_midi=69),
    ]
    assert bounded != postprocess_like
