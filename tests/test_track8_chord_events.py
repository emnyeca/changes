from __future__ import annotations

from fractions import Fraction

import pytest

from changes.digitone.track8_chord_events import extract_track8_chord_events
from changes.models.rendered_arrangement import (
    RenderedArrangement,
    RenderedChordLayer,
    RenderedCloudLayer,
    RenderedHarmonyOccurrence,
    RenderedLayerNote,
)
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_renderer import render_arrangement


def _minimal_song_model() -> SongModel:
    return SongModel(
        title="Track8",
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


def _chord_layer(
    notes: tuple[RenderedLayerNote, ...],
    velocities: tuple[int, ...],
    *,
    length_mode: str = "explicit_event_length",
    diagnostics: tuple[str, ...] = (),
) -> RenderedChordLayer:
    return RenderedChordLayer(
        role="chord",
        source_pitch_classes=(0, 4, 7, 11, 2, 9),
        canonical_stacked_midi_notes=(48, 52, 55, 59, 62, 69),
        realized_midi_notes=tuple(note.note_midi for note in notes),
        velocities=velocities,
        length_mode=length_mode,
        notes=notes,
        diagnostics=diagnostics,
    )


def test_extract_one_cmaj7_track8_event_from_render_arrangement():
    arrangement = render_arrangement(_minimal_song_model())

    events = extract_track8_chord_events(arrangement)

    assert len(events) == 1
    event = events[0]
    assert event.track_index_0based == 7
    assert event.source_harmony_id == "h1"
    assert event.symbol == "Cmaj7"
    assert event.onset_quarters == Fraction(0, 1)
    assert event.duration_quarters == Fraction(4, 1)
    assert len(event.notes) == 6
    assert tuple(note.note_midi for note in event.notes) == (48, 52, 55, 59, 62, 69)
    assert tuple(note.velocity for note in event.notes) == (70, 70, 70, 50, 70, 50)
    assert all(note.micro_timing == 0 for note in event.notes)
    assert all(note.length_mode == "explicit_event_length" for note in event.notes)


def test_skips_occurrences_without_chord_layer():
    arrangement = RenderedArrangement(
        title="No Chord",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                cloud=RenderedCloudLayer(
                    role="cloud",
                    notes=(RenderedLayerNote(note_midi=60),),
                ),
            ),
        ),
    )

    assert extract_track8_chord_events(arrangement) == ()


def test_multiple_chord_occurrences_preserve_order_and_onsets():
    occurrence1 = RenderedHarmonyOccurrence(
        id="h1",
        source_harmony_id="h1",
        symbol="Cmaj7",
        onset_quarters=Fraction(0, 1),
        duration_quarters=Fraction(4, 1),
        chord=_chord_layer(
            notes=tuple(RenderedLayerNote(note_midi=n) for n in (48, 52, 55, 59, 62, 69)),
            velocities=(70, 70, 70, 50, 70, 50),
        ),
    )
    occurrence2 = RenderedHarmonyOccurrence(
        id="h2",
        source_harmony_id="h2",
        symbol="G7",
        onset_quarters=Fraction(4, 1),
        duration_quarters=Fraction(4, 1),
        chord=_chord_layer(
            notes=tuple(RenderedLayerNote(note_midi=n) for n in (43, 47, 50, 53, 57, 62)),
            velocities=(70, 70, 70, 50, 70, 50),
        ),
    )
    arrangement = RenderedArrangement(
        title="Two",
        performance_tempo=Fraction(120, 1),
        occurrences=(occurrence1, occurrence2),
    )

    events = extract_track8_chord_events(arrangement)

    assert len(events) == 2
    assert events[0].id == "h1_track8_chord"
    assert events[1].id == "h2_track8_chord"
    assert events[0].onset_quarters == Fraction(0, 1)
    assert events[1].onset_quarters == Fraction(4, 1)


def test_empty_occurrence_id_uses_fallback_event_id():
    arrangement = RenderedArrangement(
        title="Fallback",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="",
                source_harmony_id="h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                chord=_chord_layer(
                    notes=tuple(RenderedLayerNote(note_midi=n) for n in (48, 52, 55, 59, 62, 69)),
                    velocities=(70, 70, 70, 50, 70, 50),
                ),
            ),
        ),
    )

    events = extract_track8_chord_events(arrangement)

    assert len(events) == 1
    assert events[0].id == "occ1_track8_chord"


def test_rejects_non_six_note_chord_layer():
    arrangement = RenderedArrangement(
        title="Bad Count",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                chord=_chord_layer(
                    notes=tuple(RenderedLayerNote(note_midi=n) for n in (48, 52, 55, 59, 62)),
                    velocities=(70, 70, 70, 50, 70),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match="exactly 6 notes"):
        extract_track8_chord_events(arrangement)


def test_rejects_velocity_count_mismatch():
    arrangement = RenderedArrangement(
        title="Bad Vel Count",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                chord=_chord_layer(
                    notes=tuple(RenderedLayerNote(note_midi=n) for n in (48, 52, 55, 59, 62, 69)),
                    velocities=(70, 70, 70, 50, 70),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match="velocity count"):
        extract_track8_chord_events(arrangement)


def test_rejects_invalid_velocity_range():
    arrangement = RenderedArrangement(
        title="Bad Vel",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                chord=_chord_layer(
                    notes=tuple(RenderedLayerNote(note_midi=n) for n in (48, 52, 55, 59, 62, 69)),
                    velocities=(70, 70, 0, 50, 70, 50),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match="velocity out of range"):
        extract_track8_chord_events(arrangement)


def test_rejects_non_track8_target_for_now():
    arrangement = render_arrangement(_minimal_song_model())

    with pytest.raises(ValueError, match="track_index_0based=7"):
        extract_track8_chord_events(arrangement, track_index_0based=6)


def test_preserves_occurrence_and_chord_diagnostics():
    arrangement = RenderedArrangement(
        title="Diag",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                chord=_chord_layer(
                    notes=tuple(RenderedLayerNote(note_midi=n) for n in (48, 52, 55, 59, 62, 69)),
                    velocities=(70, 70, 70, 50, 70, 50),
                    diagnostics=("chord-d1", "chord-d2"),
                ),
                diagnostics=("occ-d1",),
            ),
        ),
    )

    events = extract_track8_chord_events(arrangement)

    assert len(events) == 1
    assert events[0].diagnostics == ("occ-d1", "chord-d1", "chord-d2")
