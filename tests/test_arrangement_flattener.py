from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from changes.models.render_profile import default_render_profile
from changes.models.rendered_arrangement import (
    RenderedArrangement,
    RenderedBassLayer,
    RenderedChordLayer,
    RenderedCloudLayer,
    RenderedHarmonyOccurrence,
    RenderedLayerNote,
)
from changes.models.rendered_timeline import RenderedTimeline
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
from changes.rendering.arrangement_renderer import render_arrangement


def _chord_layer(
    notes: tuple[RenderedLayerNote, ...],
    *,
    realized: tuple[int, ...] = (48, 52, 55, 59, 62, 69),
) -> RenderedChordLayer:
    return RenderedChordLayer(
        role="chord",
        source_pitch_classes=(0, 4, 7, 11, 2, 9),
        canonical_stacked_midi_notes=(48, 52, 55, 59, 62, 69),
        realized_midi_notes=realized,
        velocities=(70, 70, 70, 50, 70, 50),
        length_mode="explicit_event_length",
        notes=notes,
    )


def _minimal_song_model() -> SongModel:
    return SongModel(
        title="Flatten Integration",
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


def test_flatten_chord_only_arrangement_to_six_chord_events():
    chord_notes = tuple(
        RenderedLayerNote(note_midi=note, lane_id=f"chord_note_{idx}")
        for idx, note in enumerate((48, 52, 55, 59, 62, 69), start=1)
    )
    arrangement = RenderedArrangement(
        title="Chord Only",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="src-h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                chord=_chord_layer(chord_notes),
            ),
        ),
    )

    timeline = flatten_arrangement_to_timeline(arrangement)

    assert isinstance(timeline, RenderedTimeline)
    assert timeline.title == "Chord Only"
    assert timeline.performance_tempo == Fraction(120, 1)
    assert len(timeline.events) == 6
    assert all(event.role == "chord" for event in timeline.events)
    assert tuple(event.voice_id for event in timeline.events) == (
        "chord_note_1",
        "chord_note_2",
        "chord_note_3",
        "chord_note_4",
        "chord_note_5",
        "chord_note_6",
    )
    assert all(event.source_harmony_id == "src-h1" for event in timeline.events)
    assert all(event.onset_quarters == Fraction(0, 1) for event in timeline.events)
    assert all(event.duration_quarters == Fraction(4, 1) for event in timeline.events)
    assert all(event.retrigger is True for event in timeline.events)
    assert tuple(event.note_midi for event in timeline.events) == (48, 52, 55, 59, 62, 69)


def test_flatten_cloud_chord_bass_arrangement_to_nine_events():
    cloud_layer = RenderedCloudLayer(
        role="cloud",
        notes=(
            RenderedLayerNote(note_midi=72, lane_id="cloud_voice_1"),
            RenderedLayerNote(note_midi=76, lane_id="cloud_voice_2"),
        ),
    )
    chord_layer = _chord_layer(
        tuple(
            RenderedLayerNote(note_midi=note, lane_id=f"chord_note_{idx}")
            for idx, note in enumerate((48, 52, 55, 59, 62, 69), start=1)
        )
    )
    bass_layer = RenderedBassLayer(
        role="bass",
        note=RenderedLayerNote(note_midi=36, lane_id="bass"),
        source_pitch_class=0,
    )
    arrangement = RenderedArrangement(
        title="All Layers",
        performance_tempo=Fraction(100, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h2",
                source_harmony_id="src-h2",
                symbol="Cmaj7",
                onset_quarters=Fraction(2, 1),
                duration_quarters=Fraction(2, 1),
                cloud=cloud_layer,
                chord=chord_layer,
                bass=bass_layer,
            ),
        ),
    )

    timeline = flatten_arrangement_to_timeline(arrangement)

    assert len(timeline.events) == 9
    assert sum(event.role == "cloud" for event in timeline.events) == 2
    assert sum(event.role == "chord" for event in timeline.events) == 6
    assert sum(event.role == "bass" for event in timeline.events) == 1
    assert tuple(event.note_midi for event in timeline.events) == (72, 76, 48, 52, 55, 59, 62, 69, 36)


def test_flatten_sorting_is_deterministic_by_onset_role_voice_and_id():
    arrangement = RenderedArrangement(
        title="Sort",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h2",
                source_harmony_id="h2-src",
                symbol="Cmaj7",
                onset_quarters=Fraction(4, 1),
                duration_quarters=Fraction(1, 1),
                cloud=RenderedCloudLayer(
                    role="cloud",
                    notes=(RenderedLayerNote(note_midi=77, lane_id="cloud_voice_1"),),
                ),
            ),
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="h1-src",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                cloud=RenderedCloudLayer(
                    role="cloud",
                    notes=(RenderedLayerNote(note_midi=74, lane_id="cloud_voice_2"),),
                ),
                chord=_chord_layer(
                    (
                        RenderedLayerNote(note_midi=52, lane_id="chord_note_2"),
                        RenderedLayerNote(note_midi=48, lane_id="chord_note_1"),
                        RenderedLayerNote(note_midi=55, lane_id="chord_note_3"),
                        RenderedLayerNote(note_midi=59, lane_id="chord_note_4"),
                        RenderedLayerNote(note_midi=62, lane_id="chord_note_5"),
                        RenderedLayerNote(note_midi=69, lane_id="chord_note_6"),
                    ),
                    realized=(52, 48, 55, 59, 62, 69),
                ),
                bass=RenderedBassLayer(
                    role="bass",
                    note=RenderedLayerNote(note_midi=36, lane_id="bass"),
                ),
            ),
        ),
    )

    timeline = flatten_arrangement_to_timeline(arrangement)

    assert tuple(event.id for event in timeline.events) == (
        "h1_cloud_1",
        "h1_chord_2",
        "h1_chord_1",
        "h1_chord_3",
        "h1_chord_4",
        "h1_chord_5",
        "h1_chord_6",
        "h1_bass",
        "h2_cloud_1",
    )


def test_flatten_uses_fallback_lane_ids_when_missing():
    chord_layer = _chord_layer(
        tuple(RenderedLayerNote(note_midi=note) for note in (48, 52, 55, 59, 62, 69))
    )
    arrangement = RenderedArrangement(
        title="Fallback",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="",
                source_harmony_id="src-fallback",
                symbol="Cmaj7",
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(4, 1),
                chord=chord_layer,
            ),
        ),
    )

    timeline = flatten_arrangement_to_timeline(arrangement)

    assert tuple(event.id for event in timeline.events) == (
        "occ1_chord_1",
        "occ1_chord_2",
        "occ1_chord_3",
        "occ1_chord_4",
        "occ1_chord_5",
        "occ1_chord_6",
    )
    assert tuple(event.voice_id for event in timeline.events) == (
        "chord_note_1",
        "chord_note_2",
        "chord_note_3",
        "chord_note_4",
        "chord_note_5",
        "chord_note_6",
    )


def test_flatten_render_arrangement_output_for_minimal_cmaj7_song():
    song = _minimal_song_model()
    arrangement = render_arrangement(song)

    timeline = flatten_arrangement_to_timeline(arrangement)

    assert len(timeline.events) == 13
    assert sum(event.role == "cloud" for event in timeline.events) == 6
    assert sum(event.role == "chord" for event in timeline.events) == 6
    assert sum(event.role == "bass" for event in timeline.events) == 1
    assert tuple(event.note_midi for event in timeline.events) == (
        48,
        52,
        55,
        57,
        59,
        62,
        48,
        52,
        55,
        59,
        62,
        69,
        36,
    )
    assert tuple(event.voice_id for event in timeline.events) == (
        "cloud_voice_1",
        "cloud_voice_2",
        "cloud_voice_3",
        "cloud_voice_4",
        "cloud_voice_5",
        "cloud_voice_6",
        "chord_note_1",
        "chord_note_2",
        "chord_note_3",
        "chord_note_4",
        "chord_note_5",
        "chord_note_6",
        "bass",
    )
    assert tuple(event.velocity for event in timeline.events if event.role == "chord") == (
        70,
        70,
        70,
        50,
        70,
        50,
    )


def _two_occurrence_arrangement(note_midi_1: int, note_midi_2: int, *, contiguous: bool = True) -> RenderedArrangement:
    gap = Fraction(0) if contiguous else Fraction(1)
    return RenderedArrangement(
        title="Hold Test",
        performance_tempo=Fraction(120, 1),
        occurrences=(
            RenderedHarmonyOccurrence(
                id="h1",
                source_harmony_id="src-h1",
                symbol="Cmaj7",
                onset_quarters=Fraction(0),
                duration_quarters=Fraction(2),
                cloud=RenderedCloudLayer(
                    role="cloud",
                    notes=(RenderedLayerNote(note_midi=note_midi_1, lane_id="cloud_voice_1"),),
                ),
                bass=RenderedBassLayer(
                    role="bass",
                    note=RenderedLayerNote(note_midi=note_midi_1, lane_id="bass"),
                    source_pitch_class=0,
                ),
                chord=_chord_layer((RenderedLayerNote(note_midi=note_midi_1, lane_id="chord_note_1"),)),
            ),
            RenderedHarmonyOccurrence(
                id="h2",
                source_harmony_id="src-h2",
                symbol="Cmaj7",
                onset_quarters=Fraction(2) + gap,
                duration_quarters=Fraction(2),
                cloud=RenderedCloudLayer(
                    role="cloud",
                    notes=(RenderedLayerNote(note_midi=note_midi_2, lane_id="cloud_voice_1"),),
                ),
                bass=RenderedBassLayer(
                    role="bass",
                    note=RenderedLayerNote(note_midi=note_midi_2, lane_id="bass"),
                    source_pitch_class=0,
                ),
                chord=_chord_layer((RenderedLayerNote(note_midi=note_midi_2, lane_id="chord_note_1"),)),
            ),
        ),
    )


def test_hold_until_change_merges_contiguous_same_pitch_cloud_and_bass():
    arrangement = _two_occurrence_arrangement(60, 60, contiguous=True)
    profile = default_render_profile()  # cloud=hold_until_change, bass=hold_until_change, chord=retrigger

    timeline = flatten_arrangement_to_timeline(arrangement, render_profile=profile)

    cloud_events = [e for e in timeline.events if e.role == "cloud"]
    bass_events = [e for e in timeline.events if e.role == "bass"]
    chord_events = [e for e in timeline.events if e.role == "chord"]

    assert len(cloud_events) == 1, "cloud: same pitch contiguous should merge to 1 event"
    assert cloud_events[0].duration_quarters == Fraction(4)
    assert cloud_events[0].onset_quarters == Fraction(0)
    assert cloud_events[0].retrigger is False, "merged hold event must not be marked as retrigger"

    assert len(bass_events) == 1, "bass: same pitch contiguous should merge to 1 event"
    assert bass_events[0].duration_quarters == Fraction(4)
    assert bass_events[0].retrigger is False

    assert len(chord_events) == 2, "chord: retrigger always produces 2 events"
    assert all(e.retrigger is True for e in chord_events)


def test_hold_until_change_does_not_merge_different_pitches():
    arrangement = _two_occurrence_arrangement(60, 62, contiguous=True)
    profile = default_render_profile()

    timeline = flatten_arrangement_to_timeline(arrangement, render_profile=profile)

    cloud_events = [e for e in timeline.events if e.role == "cloud"]
    bass_events = [e for e in timeline.events if e.role == "bass"]

    assert len(cloud_events) == 2, "cloud: different pitches should not merge"
    assert all(e.retrigger is True for e in cloud_events), "non-merged events trigger fresh"
    assert len(bass_events) == 2, "bass: different pitches should not merge"
    assert all(e.retrigger is True for e in bass_events)


def test_hold_until_change_does_not_merge_non_contiguous_same_pitch():
    arrangement = _two_occurrence_arrangement(60, 60, contiguous=False)
    profile = default_render_profile()

    timeline = flatten_arrangement_to_timeline(arrangement, render_profile=profile)

    cloud_events = [e for e in timeline.events if e.role == "cloud"]
    bass_events = [e for e in timeline.events if e.role == "bass"]

    assert len(cloud_events) == 2, "cloud: gap between events means no merge"
    assert all(e.retrigger is True for e in cloud_events)
    assert len(bass_events) == 2, "bass: gap between events means no merge"


def test_retrigger_policy_never_merges_same_pitch():
    arrangement = _two_occurrence_arrangement(60, 60, contiguous=True)
    profile = replace(
        default_render_profile(),
        cloud_trigger_policy="retrigger",
        bass_trigger_policy="retrigger",
    )

    timeline = flatten_arrangement_to_timeline(arrangement, render_profile=profile)

    cloud_events = [e for e in timeline.events if e.role == "cloud"]
    bass_events = [e for e in timeline.events if e.role == "bass"]

    assert len(cloud_events) == 2, "retrigger: same pitch contiguous must NOT merge"
    assert all(e.retrigger is True for e in cloud_events)
    assert len(bass_events) == 2, "retrigger: same pitch contiguous must NOT merge"
    assert all(e.retrigger is True for e in bass_events)
