import pytest

from changes.harmonic_context import (
    build_local_pitch_collection,
    extract_output_chord_tone_set,
    select_scale_collection,
)
from changes.voicing import progression_to_voicings
from changes.voice_leading import (
    RegisterFitError,
    _assign_minimum_motion_target,
    fit_bounded_voice_vector,
    generate_voice_leading,
)


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
    assert fitted == [52, 55, 59, 60, 62, 69]  # E4 G4 B4 C5 D5 A5
    assert fitted != [52, 55, 60, 62, 69, 59]  # reject pure octave-fold lane relocation


def test_bounded_voice_sliding_uses_pitch_order_when_voice_lanes_are_crossed():
    target = [60, 52, 69, 55, 62, 71]  # lanes: C5 E4 A5 G4 D5 B5

    fitted = fit_bounded_voice_vector(
        target,
        target,
        min_midi=48,
        max_midi=69,
    )

    assert fitted == [59, 52, 62, 55, 60, 69]
    assert fitted != [60, 52, 69, 55, 59, 62]


def test_bounded_voice_sliding_in_range_identity():
    target = [48, 52, 55, 57, 59, 62]  # C4 E4 G4 A4 B4 D5
    fitted = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)
    assert fitted == target


def test_bounded_voice_sliding_multiple_out_of_range_notes_is_deterministic_and_preserves_multiset():
    target = [35, 74, 55, 80, 69, 40]
    out1 = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)
    out2 = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)

    assert out1 == out2
    assert all(48 <= n <= 69 for n in out1)
    assert len(set(out1)) == 6
    assert sorted(n % 12 for n in out1) == sorted(n % 12 for n in target)


def test_bounded_voice_sliding_impossible_realization_raises_register_fit_error():
    target = [48, 60, 72, 84, 96, 108]
    reference = [48, 50, 52, 53, 55, 57]
    with pytest.raises(RegisterFitError, match="No in-range realization"):
        fit_bounded_voice_vector(target, reference, min_midi=48, max_midi=52, context="unit_test")


def test_bounded_voice_sliding_simultaneous_lower_and_upper_overflow():
    target = [46, 52, 60, 62, 69, 71]
    fitted = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)

    assert all(48 <= n <= 69 for n in fitted)
    assert len(set(fitted)) == 6
    assert sorted(n % 12 for n in fitted) == sorted(n % 12 for n in target)


def test_bounded_voice_sliding_deterministic_tie_break_matches_spec_cost_order():
    target = [52, 55, 60, 62, 69, 71]
    fitted = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)

    # Candidate with same total movement and max movement but higher max note must lose.
    alt = [52, 55, 59, 60, 69, 62]
    assert fitted != alt


def test_bounded_voice_sliding_keeps_unaffected_lanes_without_global_reassignment():
    target = [52, 55, 60, 62, 69, 71]
    fitted = fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)

    # First two in-range lanes must remain untouched in this boundary repair case.
    assert fitted[0] == 52
    assert fitted[1] == 55


def test_duplicate_multiset_collision_repair_is_deferred_current_contract():
    # Current production contract emits six distinct pitch classes.
    # Duplicate multiset collision redistribution is intentionally deferred.
    target = [60, 60, 64, 67, 69, 71]
    with pytest.raises(RegisterFitError, match="No in-range realization"):
        fit_bounded_voice_vector(target, target, min_midi=48, max_midi=69)


def test_generate_voice_leading_uses_previous_bounded_output_as_next_reference_state():
    voicings = [
        [47, 52, 55, 57, 50, 60],
        [44, 52, 55, 58, 62, 71],
    ]

    bounded = generate_voice_leading(voicings, min_midi=48, max_midi=69)
    assert bounded[0] == [48, 52, 55, 57, 50, 59]
    pre_fit = _assign_minimum_motion_target(bounded[0], voicings[1])
    expected_from_pipeline = fit_bounded_voice_vector(pre_fit, pre_fit, min_midi=48, max_midi=69)
    assert bounded[1] == expected_from_pipeline

    # Regression guard: postprocess-only fitting on the raw target would yield a different result.
    postprocess_like = [
        fit_bounded_voice_vector(voicings[0], voicings[0], min_midi=48, max_midi=69),
        fit_bounded_voice_vector(voicings[1], voicings[1], min_midi=48, max_midi=69),
    ]
    assert bounded != postprocess_like
