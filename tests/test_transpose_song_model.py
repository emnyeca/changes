"""Tests for transpose_song_model_preserving_structure in song_filter.py.

Verifies that transposing a SongModel only changes chord symbols and working_key,
while preserving all timing, meter, section_id, and structural information.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.song_filter import transpose_song_model_preserving_structure


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------

def _harmony(id: str, symbol: str, measure_number: int, offset: Fraction, duration: Fraction) -> HarmonyEvent:
    return HarmonyEvent(
        id=id,
        symbol=symbol,
        measure_number=measure_number,
        offset_quarters=offset,
        duration_quarters=duration,
    )


def _measure(
    number: int,
    *harmony: HarmonyEvent,
    section_id: str | None = None,
    meter: tuple[int, int] = (4, 4),
    absolute_start: Fraction = Fraction(0),
) -> Measure:
    return Measure(
        number=number,
        section_id=section_id,
        meter_numerator=meter[0],
        meter_denominator=meter[1],
        absolute_start_quarters=absolute_start,
        harmony=tuple(harmony),
    )


def _identity(symbol: str) -> str:
    return symbol


def _prefix(prefix: str):
    return lambda sym: f"{prefix}_{sym}"


def _simple_transpose(semitones: int):
    """Trivial transpose: appends semitone count for testing purposes."""
    return lambda sym: f"T{semitones}({sym})"


# ---------------------------------------------------------------------------
# Core structure preservation tests
# ---------------------------------------------------------------------------

def test_transpose_preserves_measure_count():
    m1 = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)),
                  section_id="S1", absolute_start=Fraction(0))
    m2 = _measure(2, _harmony("h2", "F7", 2, Fraction(0), Fraction(4)),
                  section_id="S2", absolute_start=Fraction(4))
    song = SongModel(title="Test", working_key="C", performance_tempo=Fraction(120), measures=(m1, m2))

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert len(result.measures) == 2


def test_transpose_preserves_section_ids():
    m1 = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)),
                  section_id="S1", absolute_start=Fraction(0))
    m2 = _measure(2, _harmony("h2", "F7", 2, Fraction(0), Fraction(3)),
                  section_id="S2", absolute_start=Fraction(4))
    m3 = _measure(3, _harmony("h3", "Gm7", 3, Fraction(0), Fraction(4)),
                  section_id="S1", absolute_start=Fraction(7))
    song = SongModel(title="Test", working_key="C", performance_tempo=Fraction(120),
                     measures=(m1, m2, m3))

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert result.measures[0].section_id == "S1"
    assert result.measures[1].section_id == "S2"
    assert result.measures[2].section_id == "S1"


def test_transpose_preserves_measure_numbers():
    measures = tuple(
        _measure(i, _harmony(f"h{i}", "Cmaj7", i, Fraction(0), Fraction(4)),
                 absolute_start=Fraction(4 * (i - 1)))
        for i in range(1, 5)
    )
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=measures)

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert [m.number for m in result.measures] == [1, 2, 3, 4]


def test_transpose_preserves_meter_numerator_denominator():
    m_4_4 = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)),
                     meter=(4, 4), section_id="A")
    m_3_4 = _measure(2, _harmony("h2", "G7", 2, Fraction(0), Fraction(3)),
                     meter=(3, 4), section_id="B", absolute_start=Fraction(4))
    m_7_8 = _measure(3, _harmony("h3", "Dm7", 3, Fraction(0), Fraction(7, 2)),
                     meter=(7, 8), section_id="C", absolute_start=Fraction(7))
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120),
                     measures=(m_4_4, m_3_4, m_7_8))

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert result.measures[0].meter_numerator == 4
    assert result.measures[0].meter_denominator == 4
    assert result.measures[1].meter_numerator == 3
    assert result.measures[1].meter_denominator == 4
    assert result.measures[2].meter_numerator == 7
    assert result.measures[2].meter_denominator == 8


def test_transpose_preserves_absolute_start_quarters():
    starts = [Fraction(0), Fraction(4), Fraction(7), Fraction(11)]
    measures = tuple(
        _measure(i + 1, _harmony(f"h{i+1}", "Cmaj7", i + 1, Fraction(0), Fraction(4)),
                 absolute_start=starts[i])
        for i in range(4)
    )
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=measures)

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    for i, expected_start in enumerate(starts):
        assert result.measures[i].absolute_start_quarters == expected_start


def test_transpose_preserves_harmony_offset_quarters():
    h1 = _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(3, 2))
    h2 = _harmony("h2", "G7", 1, Fraction(3, 2), Fraction(5, 2))
    m = _measure(1, h1, h2, section_id="S1")
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert result.measures[0].harmony[0].offset_quarters == Fraction(0)
    assert result.measures[0].harmony[1].offset_quarters == Fraction(3, 2)


def test_transpose_preserves_harmony_duration_quarters():
    h1 = _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(3, 2))
    h2 = _harmony("h2", "G7", 1, Fraction(3, 2), Fraction(5, 2))
    m = _measure(1, h1, h2, section_id="S1")
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert result.measures[0].harmony[0].duration_quarters == Fraction(3, 2)
    assert result.measures[0].harmony[1].duration_quarters == Fraction(5, 2)


def test_transpose_preserves_harmony_measure_number():
    m1 = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)), section_id="S1")
    m2 = _measure(2, _harmony("h2", "G7", 2, Fraction(0), Fraction(4)), section_id="S2",
                  absolute_start=Fraction(4))
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=(m1, m2))

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert result.measures[0].harmony[0].measure_number == 1
    assert result.measures[1].harmony[0].measure_number == 2


def test_transpose_preserves_performance_tempo():
    m = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)))
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(176), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert result.performance_tempo == Fraction(176)


def test_transpose_preserves_title_and_composer():
    m = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)))
    song = SongModel(title="Chasin' The Trane", working_key="Bb", performance_tempo=Fraction(200),
                     measures=(m,), composer="John Coltrane")

    result = transpose_song_model_preserving_structure(song, _identity, _identity)

    assert result.title == "Chasin' The Trane"
    assert result.composer == "John Coltrane"


# ---------------------------------------------------------------------------
# Test: does NOT use equal subdivision
# ---------------------------------------------------------------------------

def test_transpose_does_not_equalize_durations():
    """Non-uniform offsets/durations must be preserved exactly after transpose."""
    h1 = _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(3, 2))
    h2 = _harmony("h2", "G7", 1, Fraction(3, 2), Fraction(5, 2))
    m = _measure(1, h1, h2)
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _prefix("X"), _identity)

    assert result.measures[0].harmony[0].duration_quarters == Fraction(3, 2)
    assert result.measures[0].harmony[1].duration_quarters == Fraction(5, 2)
    assert result.measures[0].harmony[0].symbol == "X_Cmaj7"
    assert result.measures[0].harmony[1].symbol == "X_G7"


# ---------------------------------------------------------------------------
# Test: chord symbols and working_key are changed
# ---------------------------------------------------------------------------

def test_transpose_changes_chord_symbols():
    m = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)))
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _prefix("T"), _identity)

    assert result.measures[0].harmony[0].symbol == "T_Cmaj7"


def test_transpose_changes_working_key():
    m = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)))
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _identity, lambda k: "D")

    assert result.working_key == "D"


def test_transpose_working_key_none_stays_none():
    m = _measure(1, _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4)))
    song = SongModel(title="T", working_key=None, performance_tempo=Fraction(120), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _identity, lambda k: "D")

    assert result.working_key is None


# ---------------------------------------------------------------------------
# Test: variable meter song total duration unchanged
# ---------------------------------------------------------------------------

def test_transpose_variable_meter_total_duration_unchanged():
    """Transposing must not change total duration for a variable-meter song."""
    h1 = _harmony("h1", "Cmaj7", 1, Fraction(0), Fraction(4))
    h2 = _harmony("h2", "Am7", 2, Fraction(0), Fraction(3))
    h3 = _harmony("h3", "G7", 3, Fraction(0), Fraction(7, 2))
    m1 = _measure(1, h1, meter=(4, 4), absolute_start=Fraction(0))
    m2 = _measure(2, h2, meter=(3, 4), absolute_start=Fraction(4))
    m3 = _measure(3, h3, meter=(7, 8), absolute_start=Fraction(7))
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120),
                     measures=(m1, m2, m3))

    def total_duration(s: SongModel) -> Fraction:
        total = Fraction(0)
        for m in s.measures:
            if m.harmony:
                total += m.harmony[-1].offset_quarters + m.harmony[-1].duration_quarters
        return total

    original_total = total_duration(song)
    result = transpose_song_model_preserving_structure(song, _prefix("T"), lambda k: k)

    assert total_duration(result) == original_total


# ---------------------------------------------------------------------------
# Test: harmony event ids preserved
# ---------------------------------------------------------------------------

def test_transpose_preserves_harmony_event_ids():
    h1 = _harmony("m1_h1", "Cmaj7", 1, Fraction(0), Fraction(2))
    h2 = _harmony("m1_h2", "G7", 1, Fraction(2), Fraction(2))
    m = _measure(1, h1, h2)
    song = SongModel(title="T", working_key="C", performance_tempo=Fraction(120), measures=(m,))

    result = transpose_song_model_preserving_structure(song, _prefix("T"), _identity)

    assert result.measures[0].harmony[0].id == "m1_h1"
    assert result.measures[0].harmony[1].id == "m1_h2"
