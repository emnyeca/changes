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


def _minimal_a7_over_c_song() -> SongModel:
    return SongModel(
        title="DominantBlues",
        working_key="A",
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
                        symbol="A7/C",
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

    assert occ.cloud is not None
    assert tuple(note.note_midi for note in occ.cloud.notes) == (48, 52, 55, 57, 59, 62)
    assert tuple(note.lane_id for note in occ.cloud.notes) == (
        "cloud_voice_1",
        "cloud_voice_2",
        "cloud_voice_3",
        "cloud_voice_4",
        "cloud_voice_5",
        "cloud_voice_6",
    )

    assert occ.bass is not None
    assert occ.bass.note.note_midi == 36
    assert occ.bass.note.lane_id == "bass"
    assert occ.bass.source_pitch_class == 0

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


def test_render_arrangement_chord_layer_uses_dominant_blues_extraction_for_a7_over_c():
    arrangement = render_arrangement(_minimal_a7_over_c_song())

    occ = arrangement.occurrences[0]
    assert occ.chord is not None
    chord = occ.chord

    # Dominant blues extraction is 1,3,5,6,b7,#9 -> A,C#,E,F#,G,C.
    assert chord.source_pitch_classes == (9, 1, 4, 6, 7, 0)
    realized_pitch_classes = {note % 12 for note in chord.realized_midi_notes}
    assert realized_pitch_classes == {9, 1, 4, 6, 7, 0}
    assert 0 in realized_pitch_classes  # #9 (C)
    assert 11 not in realized_pitch_classes  # 9 (B)


# ── pipeline regression: variable-note chord symbols ──────────────────────────

def _minimal_song_with_symbol(title: str, symbol: str, key: str = "C") -> SongModel:
    return SongModel(
        title=title,
        working_key=key,
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
                        symbol=symbol,
                        measure_number=1,
                        offset_quarters=Fraction(0, 1),
                        duration_quarters=Fraction(4, 1),
                    ),
                ),
            ),
        ),
    )


def test_render_arrangement_bm_slash_a_does_not_raise():
    # Regression: Bm/A triggered ChordRealizationError when selected collection
    # (modes of G major) provided only 5 notes instead of 6.
    song = _minimal_song_with_symbol("ComeTogether", "Bm/A", key="G")

    arrangement = render_arrangement(song)

    assert len(arrangement.occurrences) == 1
    occ = arrangement.occurrences[0]
    assert occ.chord is not None


def test_render_arrangement_bm_slash_a_chord_layer_mandatory_pitch_classes_present():
    song = _minimal_song_with_symbol("ComeTogether", "Bm/A", key="G")

    arrangement = render_arrangement(song)

    occ = arrangement.occurrences[0]
    realized_pcs = {n % 12 for n in occ.chord.realized_midi_notes}
    assert 11 in realized_pcs  # B
    assert 2 in realized_pcs   # D
    assert 6 in realized_pcs   # F#


def test_render_arrangement_bm_slash_a_chord_velocities_match_note_count():
    song = _minimal_song_with_symbol("ComeTogether", "Bm/A", key="G")

    arrangement = render_arrangement(song)

    occ = arrangement.occurrences[0]
    chord = occ.chord
    assert len(chord.velocities) == len(chord.realized_midi_notes)


def test_render_arrangement_c5_does_not_raise():
    song = _minimal_song_with_symbol("PowerChord", "C5", key="C")

    arrangement = render_arrangement(song)

    assert len(arrangement.occurrences) == 1
    occ = arrangement.occurrences[0]
    assert occ.chord is not None
    assert len(occ.chord.realized_midi_notes) >= 2


def test_render_arrangement_chord_layer_note_and_velocity_counts_always_match():
    for key, symbol in [("G", "Bm/A"), ("C", "Cmaj7"), ("C", "C5"), ("A", "Em7")]:
        song = _minimal_song_with_symbol(symbol, symbol, key=key)
        arrangement = render_arrangement(song)
        occ = arrangement.occurrences[0]
        chord = occ.chord
        assert chord is not None
        assert len(chord.notes) == len(chord.realized_midi_notes)
        assert len(chord.velocities) == len(chord.realized_midi_notes)
