from __future__ import annotations

import pytest

from changes.harmonic_context import (
    UnsupportedHarmonicContextError,
    build_local_pitch_collection,
    chord_tone_pitch_classes,
    color_hint_pitch_classes,
    contextual_constraint_pitch_classes,
    extract_output_chord_tone_set,
    hard_context_pitch_classes,
    normalized_harmonic_identity,
    resolve_scale_collection_with_retry,
    resolve_scale_collection_with_retry_details,
    select_scale_collection,
)


_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _pcs_to_names(pcs: set[int] | frozenset[int] | tuple[int, ...]) -> list[str]:
    return sorted(_NAMES[p] for p in pcs)


def test_local_pitch_collection_skips_repeated_same_chord_blocks():
    progression = ["Cmaj7", "Am7", "Am7", "Dm7", "G7"]
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
    local, selected = resolve_scale_collection_with_retry(["Bm7"], 0, circular=True)

    assert selected.family == "diatonic_dorian"
    assert 8 in selected.pitch_classes  # G#
    output = extract_output_chord_tone_set("Bm7", selected)
    assert _pcs_to_names(output) == ["A", "B", "C#", "D", "F#", "G#"]
    assert _pcs_to_names(local) == ["A", "B", "D", "F#"]


def test_c_major_ii_v_i_output_sets():
    progression = ["Dm7", "G7", "Cmaj7"]
    expected = {
        "Dm7": ["A", "B", "C", "D", "E", "F"],
        "G7": ["A", "B", "D", "E", "F", "G"],
        "Cmaj7": ["A", "B", "C", "D", "E", "G"],
    }

    for idx, symbol in enumerate(progression):
        _local, selected = resolve_scale_collection_with_retry(progression, idx, circular=True)
        output = extract_output_chord_tone_set(symbol, selected)
        assert _pcs_to_names(output) == expected[symbol]


def test_minor_tonic_m_selects_harmonic_minor_when_context_demands_it():
    progression = ["Dm7b5", "G7b9", "Cm"]
    _local, selected = resolve_scale_collection_with_retry(progression, 2, circular=True)
    assert selected.family == "harmonic_minor"


def test_mmaj7_selects_harmonic_minor_in_minor_context():
    progression = ["Dm7b5", "G7b9", "CmMaj7"]
    _local, selected = resolve_scale_collection_with_retry(progression, 2, circular=True)
    assert selected.family == "harmonic_minor"


def test_m7b5_selects_harmonic_minor_in_minor_ii_v_i_context():
    progression = ["Dm7b5", "G7b9", "Cm"]
    _local, selected = resolve_scale_collection_with_retry(progression, 0, circular=True)
    assert selected.family == "harmonic_minor"


def test_7b9_selects_harmonic_minor_in_minor_ii_v_i_context():
    progression = ["Dm7b5", "G7b9", "Cm"]
    _local, selected = resolve_scale_collection_with_retry(progression, 1, circular=True)
    assert selected.family == "harmonic_minor"


def test_7b13_can_resolve_in_harmonic_minor_context():
    progression = ["Cm", "G7b13", "Cm"]
    _local, selected = resolve_scale_collection_with_retry(progression, 1, circular=True)
    assert selected.family == "harmonic_minor"


def test_galt_standalone_selects_ab_harmonic_minor_and_expected_output():
    local, selected = resolve_scale_collection_with_retry(["Galt"], 0, circular=True)
    assert _pcs_to_names(local) == ["B", "D#", "G", "G#"]
    assert selected.family == "harmonic_minor"
    assert selected.name.startswith("G#_")

    output = extract_output_chord_tone_set("Galt", selected)
    assert _pcs_to_names(output) == ["A#", "C#", "D#", "E", "G", "G#"]


def test_g7b13_and_gaug7_constituents_differ_but_output_may_match():
    pcs_7b13 = chord_tone_pitch_classes("G7b13")
    pcs_aug7 = chord_tone_pitch_classes("Gaug7")
    assert pcs_7b13 != pcs_aug7

    progression_a = ["Cm", "G7b13", "Cm"]
    progression_b = ["Cm", "Gaug7", "Cm"]

    _local_a, selected_a = resolve_scale_collection_with_retry(progression_a, 1, circular=True)
    _local_b, selected_b = resolve_scale_collection_with_retry(progression_b, 1, circular=True)

    out_a = extract_output_chord_tone_set("G7b13", selected_a)
    out_b = extract_output_chord_tone_set("Gaug7", selected_b)
    assert _pcs_to_names(out_a) == _pcs_to_names(out_b)


def test_whole_tone_resolution_and_extraction_rule():
    local = frozenset({7, 9, 11, 1, 3, 5})
    selected = select_scale_collection("G7#5", local)
    assert selected.family == "whole_tone"

    output = extract_output_chord_tone_set("G7#5", selected)
    assert _pcs_to_names(output) == ["A", "B", "C#", "D#", "F", "G"]


def test_diminished_signature_root_restriction_is_enforced():
    local = frozenset({0, 1, 3, 4, 6, 7, 9, 10})
    with pytest.raises(UnsupportedHarmonicContextError):
        select_scale_collection("Ddim7", local)


def test_diminished_half_whole_wins_when_both_diminished_families_are_eligible():
    local = chord_tone_pitch_classes("Cdim7")
    selected = select_scale_collection("Cdim7", local)
    assert selected.family == "harmonic_minor"

    # Force priority stage 5 by using collection that only diminished families can satisfy.
    diminished_only_local = frozenset({0, 1, 3, 4, 6, 7, 9, 10})
    selected2 = select_scale_collection("C7b9", diminished_only_local)
    assert selected2.family == "diminished"
    assert selected2.extraction_rule == "dim_half_whole_1b3b56b7b9"


def test_dim7_may_resolve_to_harmonic_minor_before_diminished_priority():
    selected = select_scale_collection("Cdim7", chord_tone_pitch_classes("Cdim7"))
    assert selected.family == "harmonic_minor"


def test_retry_policy_full_context_resolves_for_diatonic_case():
    progression = ["Dm7", "G7", "Cmaj7"]
    _local, selected = resolve_scale_collection_with_retry(progression, 1, circular=True)
    assert selected.family == "diatonic_dorian"


def test_retry_policy_resolves_after_dropping_next_context():
    progression = ["Cmaj7", "G7", "F#maj7"]
    local, selected = resolve_scale_collection_with_retry(progression, 1, circular=True)
    assert selected.family == "diatonic_dorian"
    assert _pcs_to_names(local) == ["B", "C", "D", "E", "F", "G"]


def test_retry_policy_resolves_only_from_current_chord():
    progression = ["F#maj7", "Cmaj7", "F#maj7"]
    local, selected = resolve_scale_collection_with_retry(progression, 1, circular=True)
    assert selected.family == "diatonic_dorian"
    assert _pcs_to_names(local) == ["B", "C", "E", "G"]


def test_retry_policy_raises_explicit_unsupported_when_current_only_fails():
    with pytest.raises(UnsupportedHarmonicContextError, match="Unsupported harmonic context"):
        resolve_scale_collection_with_retry(["Cmaj7/A#"], 0, circular=True)


def test_normalized_identity_enharmonic_roots_are_equal():
    assert normalized_harmonic_identity("C#maj7") == normalized_harmonic_identity("Dbmaj7")


def test_normalized_identity_slash_bass_changes_identity():
    assert normalized_harmonic_identity("Dm7") != normalized_harmonic_identity("Dm7/G")


def test_repeated_normalized_identical_chords_are_skipped_for_context_lookup():
    progression = ["C#maj7", "Dbmaj7", "C#maj7", "G7"]
    local = build_local_pitch_collection(progression, 1, circular=True)
    assert 5 in local  # F from G7 must be included as the next distinct context.


def test_full_song_context_crosses_section_boundaries_by_default():
    progression = ["Cmaj7", "Am7", "Dm7", "G7"]
    local_head = build_local_pitch_collection(progression, 0, circular=True)
    assert 5 in local_head  # F from tail G7


def test_single_section_behavior_is_circular_within_provided_section_sequence():
    section_only = ["Dm7", "G7", "Cmaj7"]
    local = build_local_pitch_collection(section_only, 0, circular=True)
    assert _pcs_to_names(local) == ["A", "B", "C", "D", "E", "F", "G"]


def test_repeated_section_occurrences_are_position_sensitive_not_template_reused():
    progression = ["Cmaj7", "Am7", "Dm7", "Cmaj7", "F#7"]
    local_1, _selected_1 = resolve_scale_collection_with_retry(progression, 0, circular=True)
    local_2, _selected_2 = resolve_scale_collection_with_retry(progression, 3, circular=True)
    assert local_1 != local_2


def test_plain_gm7_in_500_miles_high_phrase_cannot_select_diminished_and_falls_back_to_current_only():
    progression = ["Em7", "Em7", "Gm7", "Gm7", "A#maj7"]

    resolved = resolve_scale_collection_with_retry_details(progression, 2, circular=True)
    output = extract_output_chord_tone_set("Gm7", resolved.selected_collection)

    assert resolved.retry_level == "current_only"
    assert resolved.selected_collection.family == "diatonic_dorian"
    assert "diminished" not in resolved.selected_collection.name
    assert output == (7, 10, 2, 4, 5, 9)  # G, A#, D, E, F, A


@pytest.mark.parametrize("symbol", ["Cmaj7", "Cm7", "Cm", "Cm9"])
def test_plain_tonal_qualities_do_not_select_symmetric_collections(symbol: str):
    diminished_only_local = frozenset({0, 1, 3, 4, 6, 7, 9, 10})

    try:
        selected = select_scale_collection(symbol, diminished_only_local)
        assert selected.family != "diminished"
        assert selected.family != "whole_tone"
    except UnsupportedHarmonicContextError:
        # Rejecting symmetric candidates may legitimately leave no eligible family.
        pass


def test_dim7_remains_eligible_for_diminished_when_no_higher_priority_family_fits():
    diminished_only_local = frozenset({0, 1, 3, 4, 6, 7, 9, 10})
    selected = select_scale_collection("Cdim7", diminished_only_local)
    assert selected.family == "diminished"


def test_altered_dominant_remains_eligible_for_symmetric_collection():
    diminished_only_local = frozenset({0, 1, 3, 4, 6, 7, 9, 10})
    selected = select_scale_collection("C7b9", diminished_only_local)
    assert selected.family == "diminished"


def test_minor_ii_v_e7sharp9_prefers_harmonic_minor_on_current_plus_previous():
    progression = ["Bm7b5", "E7#9", "Am7"]

    resolved = resolve_scale_collection_with_retry_details(progression, 1, circular=True)
    output = extract_output_chord_tone_set("E7#9", resolved.selected_collection)

    assert resolved.retry_level == "current+previous"
    assert resolved.selected_collection.family == "harmonic_minor"
    assert resolved.selected_collection.name.startswith("A_")
    assert resolved.selected_collection.family != "diminished"
    assert _pcs_to_names(output) == ["B", "C", "D", "E", "F", "G#"]
    assert _pcs_to_names(resolved.color_hint_pitch_classes) == ["G"]
    assert resolved.color_hints_applied_to_constraint_set is False
    assert _pcs_to_names(resolved.final_local_pitch_collection_used_for_selection) == ["A", "B", "D", "E", "F", "G#"]


def test_standalone_e7sharp9_applies_color_hints_on_current_only_attempt():
    resolved = resolve_scale_collection_with_retry_details(["E7#9"], 0, circular=True)
    assert resolved.retry_level == "current_only"
    assert resolved.color_hints_applied_to_constraint_set is True
    assert _pcs_to_names(resolved.color_hint_pitch_classes) == ["G"]
    assert 7 in resolved.final_local_pitch_collection_used_for_selection

    plain = resolve_scale_collection_with_retry_details(["E7"], 0, circular=True)
    out_altered = extract_output_chord_tone_set("E7#9", resolved.selected_collection)
    out_plain = extract_output_chord_tone_set("E7", plain.selected_collection)
    assert (resolved.selected_collection.name, out_altered) != (plain.selected_collection.name, out_plain)


@pytest.mark.parametrize(
    ("symbol", "hint_note"),
    [("E7b9", "F"), ("E7#11", "A#"), ("E7b13", "C")],
)
def test_standalone_dominant_altered_color_hints_are_restored_on_current_only(symbol: str, hint_note: str):
    resolved = resolve_scale_collection_with_retry_details([symbol], 0, circular=True)
    assert resolved.retry_level == "current_only"
    assert resolved.color_hints_applied_to_constraint_set is True
    assert hint_note in _pcs_to_names(resolved.color_hint_pitch_classes)


def test_altered_fifth_remains_hard_for_contextual_selection():
    assert "C" in _pcs_to_names(hard_context_pitch_classes("E7#5"))
    assert "C" not in _pcs_to_names(color_hint_pitch_classes("E7#5"))

    assert "A#" in _pcs_to_names(hard_context_pitch_classes("E7b5"))
    assert "A#" not in _pcs_to_names(color_hint_pitch_classes("E7b5"))

    assert "A#" in _pcs_to_names(hard_context_pitch_classes("E7#9b5"))
    assert "G" in _pcs_to_names(color_hint_pitch_classes("E7#9b5"))


def test_alt_remains_hard_semantic_directive_without_soft_color_split():
    assert _pcs_to_names(hard_context_pitch_classes("Galt")) == ["B", "D#", "G", "G#"]
    assert color_hint_pitch_classes("Galt") == frozenset()


def test_contextual_constraint_function_switches_color_hint_inclusion():
    hard_only = contextual_constraint_pitch_classes("E7#9", include_color_hints=False)
    with_color = contextual_constraint_pitch_classes("E7#9", include_color_hints=True)

    assert _pcs_to_names(hard_only) == ["B", "D", "E", "G#"]
    assert _pcs_to_names(with_color) == ["B", "D", "E", "G", "G#"]
