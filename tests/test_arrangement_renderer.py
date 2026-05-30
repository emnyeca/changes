from __future__ import annotations

from fractions import Fraction

from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.models.rendered_arrangement import (
    rendered_arrangement_from_dict,
    rendered_arrangement_to_dict,
)
from changes.rendering.arrangement_renderer import render_arrangement


def _minimal_cmaj7_song() -> SongModel:
    return SongModel(
        title="Phase3B",
        working_key="C",
        performance_tempo=Fraction(120, 1),
        measures=(
            Measure(
                number=1,
                section_id="A",
                meter_numerator=4,
                meter_denominator=4,
                absolute_start_quarters=Fraction(0, 1),
                harmony=(
                    HarmonyEvent(
                        id="h1",
                        symbol="Cmaj7",
                        measure_number=1,
                        offset_quarters=Fraction(0, 1),
                        duration_quarters=Fraction(4, 1),
                    ),
                ),
            ),
        ),
    )


def test_render_arrangement_single_cmaj7_occurrence_chord_layer_shape():
    song = _minimal_cmaj7_song()

    arrangement = render_arrangement(song)

    assert arrangement.title == "Phase3B"
    assert arrangement.performance_tempo == Fraction(120, 1)
    assert len(arrangement.occurrences) == 1

    occ = arrangement.occurrences[0]
    assert occ.source_harmony_id == "h1"
    assert occ.symbol == "Cmaj7"
    assert occ.onset_quarters == Fraction(0, 1)
    assert occ.duration_quarters == Fraction(4, 1)

    assert occ.chord is not None
    chord = occ.chord
    assert chord.realized_midi_notes == (48, 52, 55, 59, 62, 69)
    assert chord.velocities == (70, 70, 70, 50, 70, 50)
    assert len(chord.notes) == 6
    assert tuple(note.lane_id for note in chord.notes) == (
        "chord_note_1",
        "chord_note_2",
        "chord_note_3",
        "chord_note_4",
        "chord_note_5",
        "chord_note_6",
    )


def test_render_arrangement_roundtrip_via_dict_serialization():
    song = _minimal_cmaj7_song()

    arrangement = render_arrangement(song)
    as_dict = rendered_arrangement_to_dict(arrangement)
    restored = rendered_arrangement_from_dict(as_dict)

    assert restored == arrangement
