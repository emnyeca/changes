"""Tests for editor_to_song_model conversion."""

from __future__ import annotations

from fractions import Fraction

import pytest

from changes.editor import EditorState, editor_to_song_model


# ---------------------------------------------------------------------------
# Helpers


def _state(*cells: str, title: str = "TEST", tempo: int = 120, meter: str = "4/4") -> EditorState:
    return EditorState(title=title, tempo=tempo, meter=meter, cells=list(cells))


# ---------------------------------------------------------------------------
# Metadata


def test_title_default_when_empty():
    s = EditorState(title="", cells=["Cmaj7"])
    song = editor_to_song_model(s)
    assert song.title == "NO TITLE"


def test_title_whitespace_only_becomes_no_title():
    s = EditorState(title="   ", cells=["Cmaj7"])
    song = editor_to_song_model(s)
    assert song.title == "NO TITLE"


def test_title_and_tempo_preserved():
    s = _state("Cmaj7", title="My Song", tempo=140)
    song = editor_to_song_model(s)
    assert song.title == "My Song"
    assert song.performance_tempo == Fraction(140)


# ---------------------------------------------------------------------------
# Single measure


def test_single_chord_fills_whole_measure():
    song = editor_to_song_model(_state("Cmaj7"))
    assert len(song.measures) == 1
    h = song.measures[0].harmony
    assert len(h) == 1
    assert h[0].symbol == "Cmaj7"
    assert h[0].duration_quarters == Fraction(4)
    assert h[0].offset_quarters == Fraction(0)


def test_two_chords_split_evenly_in_4_4():
    song = editor_to_song_model(_state("Cmaj7", "G7"))
    h = song.measures[0].harmony
    assert len(h) == 2
    assert h[0].symbol == "Cmaj7"
    assert h[0].duration_quarters == Fraction(2)
    assert h[1].symbol == "G7"
    assert h[1].duration_quarters == Fraction(2)
    assert h[1].offset_quarters == Fraction(2)


def test_three_chords_split_evenly_in_4_4():
    song = editor_to_song_model(_state("Cmaj7", "Am7", "G7"))
    h = song.measures[0].harmony
    assert len(h) == 3
    assert all(hh.duration_quarters == Fraction(4, 3) for hh in h)


# ---------------------------------------------------------------------------
# % resolution


def test_percent_resolves_to_previous_chord():
    # | Cmaj7 % % G7 | → Cmaj7 3拍, G7 1拍
    song = editor_to_song_model(_state("Cmaj7", "%", "%", "G7"))
    h = song.measures[0].harmony
    assert len(h) == 2
    assert h[0].symbol == "Cmaj7"
    assert h[0].duration_quarters == Fraction(3)
    assert h[1].symbol == "G7"
    assert h[1].duration_quarters == Fraction(1)


def test_percent_only_measure_repeats_last_chord_from_previous_measure():
    song = editor_to_song_model(_state("Cmaj7", "|", "%"))
    assert song.measures[1].harmony[0].symbol == "Cmaj7"
    assert song.measures[1].harmony[0].duration_quarters == Fraction(4)


def test_percent_at_start_raises():
    with pytest.raises(ValueError, match="'%'"):
        editor_to_song_model(_state("%", "G7"))


def test_percent_as_first_cell_before_any_chord_raises():
    s = _state("|", "%")
    with pytest.raises(ValueError, match="'%'"):
        editor_to_song_model(s)


# ---------------------------------------------------------------------------
# Barlines and measures


def test_barlines_create_separate_measures():
    song = editor_to_song_model(_state("Cmaj7", "|", "Am7", "|", "G7"))
    assert len(song.measures) == 3
    assert song.measures[0].harmony[0].symbol == "Cmaj7"
    assert song.measures[1].harmony[0].symbol == "Am7"
    assert song.measures[2].harmony[0].symbol == "G7"


def test_leading_barline_does_not_create_empty_measure():
    song = editor_to_song_model(_state("|", "Cmaj7"))
    assert len(song.measures) == 1


def test_trailing_barline_does_not_create_extra_measure():
    song = editor_to_song_model(_state("Cmaj7", "|"))
    assert len(song.measures) == 1


# ---------------------------------------------------------------------------
# Empty measure = repeat last chord


def test_empty_measure_in_middle_repeats_last_chord():
    # | Cmaj7 | | G7 | → measures: Cmaj7, Cmaj7, G7
    song = editor_to_song_model(_state("Cmaj7", "|", "|", "G7"))
    assert len(song.measures) == 3
    assert song.measures[0].harmony[0].symbol == "Cmaj7"
    assert song.measures[1].harmony[0].symbol == "Cmaj7"
    assert song.measures[2].harmony[0].symbol == "G7"


def test_empty_measure_fills_full_measure_duration():
    song = editor_to_song_model(_state("Cmaj7", "|", "|"))
    assert song.measures[1].harmony[0].duration_quarters == Fraction(4)


# ---------------------------------------------------------------------------
# Section boundaries


def test_double_barline_advances_section():
    song = editor_to_song_model(_state("Cmaj7", "||", "Am7"))
    assert song.measures[0].section_id == "A__OCC1"
    assert song.measures[1].section_id == "B__OCC1"


def test_multiple_section_boundaries():
    song = editor_to_song_model(_state("Cmaj7", "||", "Am7", "||", "G7"))
    assert song.measures[0].section_id == "A__OCC1"
    assert song.measures[1].section_id == "B__OCC1"
    assert song.measures[2].section_id == "C__OCC1"


def test_single_section_no_double_barline():
    song = editor_to_song_model(_state("Cmaj7", "|", "Am7"))
    assert all(m.section_id == "A__OCC1" for m in song.measures)


# ---------------------------------------------------------------------------
# Absolute timing


def test_absolute_start_quarters_accumulate():
    song = editor_to_song_model(_state("Cmaj7", "|", "G7", "|", "Am7"))
    assert song.measures[0].absolute_start_quarters == Fraction(0)
    assert song.measures[1].absolute_start_quarters == Fraction(4)
    assert song.measures[2].absolute_start_quarters == Fraction(8)


def test_measure_numbers_are_sequential():
    song = editor_to_song_model(_state("Cmaj7", "|", "G7", "|", "Am7"))
    assert [m.number for m in song.measures] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Meter


def test_three_four_measure_length_is_3_quarters():
    song = editor_to_song_model(_state("Cmaj7", meter="3/4"))
    assert song.measures[0].harmony[0].duration_quarters == Fraction(3)


def test_three_four_two_chords_split_evenly():
    song = editor_to_song_model(_state("Cmaj7", "G7", meter="3/4"))
    h = song.measures[0].harmony
    assert h[0].duration_quarters == Fraction(3, 2)
    assert h[1].duration_quarters == Fraction(3, 2)


# ---------------------------------------------------------------------------
# Edge cases


def test_no_measures_raises():
    with pytest.raises(ValueError):
        editor_to_song_model(EditorState())


def test_only_barlines_raises():
    with pytest.raises(ValueError):
        editor_to_song_model(_state("|", "|", "|"))


def test_harmony_event_ids_are_unique():
    song = editor_to_song_model(_state("Cmaj7", "Am7", "|", "Dm7", "G7"))
    ids = [h.id for m in song.measures for h in m.harmony]
    assert len(ids) == len(set(ids))
