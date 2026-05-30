from __future__ import annotations

import pytest

from changes.chord_engine import construct_chord_pitch_classes
from changes.chord_parser import parse_chord_core
from changes.chord_realization import (
    ChordPerformancePolicy,
    ChordRealizationError,
    ChordRegisterPolicy,
    realize_chord_register,
)


def _build_construction(symbol: str, selected_collection_pitch_classes: tuple[int, ...]):
    core = parse_chord_core(symbol)
    return construct_chord_pitch_classes(core, selected_collection_pitch_classes)


def test_cmaj7_realizes_to_expected_midi_notes():
    construction = _build_construction("Cmaj7", (0, 2, 4, 5, 7, 9, 11))

    result = realize_chord_register(construction)

    assert result.realized_midi_notes == (48, 52, 55, 59, 62, 69)


def test_c7b9_realizes_to_expected_midi_notes():
    construction = _build_construction("C7b9", (0, 1, 4, 5, 7, 8, 10))

    result = realize_chord_register(construction)

    assert result.realized_midi_notes == (48, 52, 55, 58, 61, 68)


def test_e7sharp9_folds_octave_and_realizes_to_expected_midi_notes():
    construction = _build_construction("E7#9", (0, 2, 4, 5, 6, 7, 8, 9, 11))

    result = realize_chord_register(construction)

    assert result.canonical_stacked_midi_notes == (52, 56, 59, 62, 67, 72)
    assert result.realized_midi_notes == (52, 56, 59, 60, 62, 67)


def test_bmaj7_high_root_case_folds_deterministically():
    construction = _build_construction("Bmaj7", (1, 3, 6, 8, 10, 11))

    result = realize_chord_register(construction)

    assert result.canonical_stacked_midi_notes == (59, 63, 66, 70, 73, 80)
    assert result.realized_midi_notes == (58, 59, 61, 63, 66, 68)


@pytest.mark.parametrize(
    ("symbol", "selected"),
    [
        ("Cmaj7", (0, 2, 4, 5, 7, 9, 11)),
        ("C7b9", (0, 1, 4, 5, 7, 8, 10)),
        ("E7#9", (0, 2, 4, 5, 6, 7, 8, 9, 11)),
        ("Bmaj7", (1, 3, 6, 8, 10, 11)),
    ],
)
def test_results_are_six_distinct_notes_within_default_register(symbol: str, selected: tuple[int, ...]):
    construction = _build_construction(symbol, selected)

    result = realize_chord_register(construction)

    assert len(result.realized_midi_notes) == 6
    assert len(set(result.realized_midi_notes)) == 6
    assert all(48 <= note <= 69 for note in result.realized_midi_notes)


def test_default_velocities_are_assigned_low_to_high_order():
    construction = _build_construction("E7#9", (0, 2, 4, 5, 6, 7, 8, 9, 11))

    result = realize_chord_register(construction)

    assert result.realized_midi_notes == (52, 56, 59, 60, 62, 67)
    assert result.velocities == (70, 70, 70, 50, 70, 50)


def test_length_mode_inherit_is_retained_without_duration_resolution():
    construction = _build_construction("Cmaj7", (0, 2, 4, 5, 7, 9, 11))
    policy = ChordPerformancePolicy(length_mode="inherit")

    result = realize_chord_register(construction, performance_policy=policy)

    assert result.length_mode == "inherit"


def test_invalid_pitch_class_count_raises_error():
    construction = _build_construction("Cmaj7", (0, 2, 4, 5, 7, 9, 11))
    broken = construction.__class__(
        source_symbol=construction.source_symbol,
        root_pc=construction.root_pc,
        normalized_quality=construction.normalized_quality,
        selected_collection_pitch_classes=construction.selected_collection_pitch_classes,
        mandatory_intervals=construction.mandatory_intervals,
        mandatory_pitch_classes=construction.mandatory_pitch_classes,
        automatic_excluded_intervals=construction.automatic_excluded_intervals,
        automatic_tension_intervals=construction.automatic_tension_intervals,
        automatic_tension_pitch_classes=construction.automatic_tension_pitch_classes,
        final_pitch_classes=(0, 4, 7, 11, 2),
        diagnostics=construction.diagnostics,
    )

    with pytest.raises(ChordRealizationError, match="exactly six pitch classes"):
        realize_chord_register(broken)


def test_duplicate_pitch_classes_raise_error():
    construction = _build_construction("Cmaj7", (0, 2, 4, 5, 7, 9, 11))
    broken = construction.__class__(
        source_symbol=construction.source_symbol,
        root_pc=construction.root_pc,
        normalized_quality=construction.normalized_quality,
        selected_collection_pitch_classes=construction.selected_collection_pitch_classes,
        mandatory_intervals=construction.mandatory_intervals,
        mandatory_pitch_classes=construction.mandatory_pitch_classes,
        automatic_excluded_intervals=construction.automatic_excluded_intervals,
        automatic_tension_intervals=construction.automatic_tension_intervals,
        automatic_tension_pitch_classes=construction.automatic_tension_pitch_classes,
        final_pitch_classes=(0, 4, 7, 11, 2, 2),
        diagnostics=construction.diagnostics,
    )

    with pytest.raises(ChordRealizationError, match="six distinct pitch classes"):
        realize_chord_register(broken)


def test_invalid_velocity_profile_raises_error():
    construction = _build_construction("Cmaj7", (0, 2, 4, 5, 7, 9, 11))
    bad_policy = ChordPerformancePolicy(velocity_low_to_high=(70, 70, 70, 50, 70))

    with pytest.raises(ChordRealizationError, match="exactly six values"):
        realize_chord_register(construction, performance_policy=bad_policy)


def test_too_narrow_custom_register_raises_error():
    construction = _build_construction("Cmaj7", (0, 2, 4, 5, 7, 9, 11))
    narrow = ChordRegisterPolicy(min_midi=60, max_midi=64)

    with pytest.raises(ChordRealizationError, match="below register"):
        realize_chord_register(construction, register_policy=narrow)
