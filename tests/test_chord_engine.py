from __future__ import annotations

import pytest

from changes.chord_engine import CHORD_MANDATORY_INTERVALS, ChordConstructionError, construct_chord_pitch_classes
from changes.chord_parser import parse_chord_core


def _selected_collection(*pitch_classes: int) -> tuple[int, ...]:
    return tuple(pitch_classes)


def test_parse_chord_core_normalizes_plain_sus4_to_dominant_sus4():
    core = parse_chord_core("Csus4")

    assert core.quality == "sus4"
    assert core.normalized_quality == "7sus4"


def test_construct_chord_cmaj7_uses_symbol_tones_plus_collection_tensions():
    core = parse_chord_core("Cmaj7")
    selected = _selected_collection(0, 2, 4, 5, 7, 9, 11)

    result = construct_chord_pitch_classes(core, selected)

    assert result.mandatory_intervals == (0, 4, 7, 11)
    assert result.mandatory_pitch_classes == (0, 4, 7, 11)
    assert result.automatic_tension_intervals == (2, 9)
    assert result.automatic_tension_pitch_classes == (2, 9)
    assert result.final_pitch_classes == (0, 4, 7, 11, 2, 9)


def test_construct_chord_c7b9_preserves_explicit_b9():
    core = parse_chord_core("C7b9")
    selected = _selected_collection(0, 1, 4, 5, 7, 8, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert 1 in result.mandatory_intervals
    assert 1 in result.mandatory_pitch_classes
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6
    assert 8 in result.automatic_tension_pitch_classes


def test_construct_chord_c7b9_matches_requested_construction_order():
    core = parse_chord_core("C7b9")
    selected = _selected_collection(0, 1, 4, 5, 7, 8, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert result.mandatory_pitch_classes == (0, 4, 7, 10, 1)
    assert result.automatic_tension_pitch_classes == (8,)
    assert result.final_pitch_classes == (0, 4, 7, 10, 1, 8)


def test_construct_chord_c7b9_does_not_auto_add_sharp9_when_available():
    core = parse_chord_core("C7b9")
    selected = _selected_collection(0, 1, 3, 4, 7, 8, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert 1 in result.mandatory_pitch_classes
    assert 3 not in result.final_pitch_classes
    assert result.automatic_tension_pitch_classes == (8,)
    assert result.final_pitch_classes == (0, 4, 7, 10, 1, 8)


def test_construct_chord_c7b9_does_not_auto_add_natural9_when_written_b9():
    core = parse_chord_core("C7b9")
    selected = _selected_collection(0, 1, 2, 4, 7, 9, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert 1 in result.final_pitch_classes
    assert 2 not in result.final_pitch_classes
    assert 9 in result.automatic_tension_pitch_classes


def test_construct_chord_csus4_adds_d_and_a_above_shell():
    core = parse_chord_core("Csus4")
    selected = _selected_collection(0, 2, 5, 7, 9, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert core.normalized_quality == "7sus4"
    assert result.mandatory_intervals == (0, 5, 7, 10)
    assert result.mandatory_pitch_classes == (0, 5, 7, 10)
    assert result.automatic_tension_pitch_classes == (2, 9)
    assert result.final_pitch_classes == (0, 5, 7, 10, 2, 9)


def test_construct_chord_csus4_matches_requested_construction_order():
    core = parse_chord_core("Csus4")
    selected = _selected_collection(0, 2, 5, 7, 9, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert core.normalized_quality == "7sus4"
    assert result.mandatory_pitch_classes == (0, 5, 7, 10)
    assert result.automatic_tension_pitch_classes == (2, 9)
    assert result.final_pitch_classes == (0, 5, 7, 10, 2, 9)


def test_construct_chord_e7sharp9_in_minor_context_preserves_explicit_sharp9():
    core = parse_chord_core("E7#9")
    selected = _selected_collection(0, 2, 4, 5, 6, 7, 8, 9, 11)

    result = construct_chord_pitch_classes(core, selected)

    assert result.mandatory_intervals == (0, 4, 7, 10, 3)
    assert result.mandatory_pitch_classes == (4, 8, 11, 2, 7)
    assert result.automatic_tension_pitch_classes == (0,)
    assert result.final_pitch_classes == (4, 8, 11, 2, 7, 0)


def test_construct_chord_e7sharp9_matches_requested_construction_order():
    core = parse_chord_core("E7#9")
    selected = _selected_collection(0, 2, 4, 5, 6, 7, 8, 9, 11)

    result = construct_chord_pitch_classes(core, selected)

    assert result.mandatory_pitch_classes == (4, 8, 11, 2, 7)
    assert result.automatic_tension_pitch_classes == (0,)
    assert result.final_pitch_classes == (4, 8, 11, 2, 7, 0)


def test_construct_chord_c7sharp9_does_not_auto_add_other_ninth_variants():
    core = parse_chord_core("C7#9")
    selected = _selected_collection(0, 1, 2, 3, 4, 7, 8, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert 3 in result.mandatory_pitch_classes
    assert 1 not in result.automatic_tension_pitch_classes
    assert 2 not in result.automatic_tension_pitch_classes
    assert 8 in result.automatic_tension_pitch_classes


def test_construct_chord_gm7b5_uses_natural13_when_locrian_natural2_needs_six_notes():
    core = parse_chord_core("Gm7b5")
    selected = _selected_collection(1, 2, 4, 5, 7, 9, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert set(result.mandatory_pitch_classes) == {7, 10, 1, 5}
    assert result.automatic_tension_intervals == (2, 9)
    assert result.automatic_tension_pitch_classes == (9, 4)
    assert set(result.final_pitch_classes) == {7, 10, 1, 5, 9, 4}
    assert len(result.final_pitch_classes) == 6


def test_construct_chord_alt_allows_compound_alterations():
    core = parse_chord_core("Calt")
    selected = _selected_collection(0, 1, 2, 3, 4, 6, 7, 8, 10)

    result = construct_chord_pitch_classes(core, selected)

    assert result.automatic_excluded_intervals == ()
    assert set(result.automatic_tension_pitch_classes) >= {1, 3, 8}
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6


@pytest.mark.parametrize(
    ("symbol", "expected_pitch_class"),
    [
        ("C7b9", 1),
        ("C7#9", 3),
        ("C7#11", 6),
        ("C7b13", 8),
    ],
)
def test_construct_chord_preserves_explicit_altered_tones(symbol: str, expected_pitch_class: int):
    core = parse_chord_core(symbol)
    selected = tuple(range(12))

    result = construct_chord_pitch_classes(core, selected)

    assert expected_pitch_class in result.mandatory_pitch_classes
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6


@pytest.mark.parametrize("normalized_quality", sorted(CHORD_MANDATORY_INTERVALS))
def test_construct_chord_supported_quality_smoke(normalized_quality: str):
    if normalized_quality == "alt":
        symbol = "Calt"
    else:
        symbol = f"C{normalized_quality}"
    core = parse_chord_core(symbol)
    selected = tuple(range(12))

    result = construct_chord_pitch_classes(core, selected)

    assert core.normalized_quality == normalized_quality
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6
    assert all(pc in result.final_pitch_classes for pc in result.mandatory_pitch_classes)


def test_construct_chord_raises_when_selected_collection_cannot_fill_six_notes():
    core = parse_chord_core("Cmaj7")
    selected = _selected_collection(0, 4, 7, 11)

    with pytest.raises(ChordConstructionError, match="does not provide enough distinct automatic tensions"):
        construct_chord_pitch_classes(core, selected)


def test_construct_chord_raises_for_unknown_normalized_quality():
    core = parse_chord_core("Cmaj7")
    forged = core.__class__(
        symbol=core.symbol,
        root=core.root,
        root_pc=core.root_pc,
        quality=core.quality,
        normalized_quality="not-a-quality",
        base_quality=core.base_quality,
        seventh_type=core.seventh_type,
        extensions=core.extensions,
        added_degrees=core.added_degrees,
        altered_degrees=core.altered_degrees,
        omitted_degrees=core.omitted_degrees,
        slash_bass=core.slash_bass,
        slash_bass_pc=core.slash_bass_pc,
        special_semantic_tag=core.special_semantic_tag,
    )

    with pytest.raises(ChordConstructionError, match="Unsupported normalized chord quality"):
        construct_chord_pitch_classes(forged, tuple(range(12)))
