from __future__ import annotations

from fractions import Fraction

from changes.models.render_profile import default_render_profile
from changes.models.rendered_arrangement import (
    RenderedArrangement,
    RenderedCloudLayer,
    RenderedHarmonyOccurrence,
    RenderedLayerNote,
)
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
from changes.rendering.arrangement_renderer import render_arrangement
from changes.rendering.timeline_renderer import render_timeline


def _minimal_song_model() -> SongModel:
    return SongModel(
        title="Cloud Role Contract",
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


def test_legacy_timeline_renderer_is_not_migrated_yet():
    song = _minimal_song_model()

    timeline = render_timeline(song, default_render_profile())

    # Contract pin: legacy timeline still labels the old moving six-voice layer
    # as role="chord" with chord_voice_* lane names.
    assert any(event.role == "chord" for event in timeline.events)
    assert any(event.voice_id.startswith("chord_voice_") for event in timeline.events)


def test_render_arrangement_then_flatten_emits_new_chord_note_naming():
    song = _minimal_song_model()

    arrangement = render_arrangement(song)
    timeline = flatten_arrangement_to_timeline(arrangement)

    assert all(event.role == "chord" for event in timeline.events)
    assert tuple(event.voice_id for event in timeline.events) == (
        "chord_note_1",
        "chord_note_2",
        "chord_note_3",
        "chord_note_4",
        "chord_note_5",
        "chord_note_6",
    )


def test_flatten_manual_cloud_layer_emits_cloud_role_and_cloud_voice_ids():
    arrangement = RenderedArrangement(
        title="Cloud Layer",
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
                    notes=(
                        RenderedLayerNote(note_midi=60),
                        RenderedLayerNote(note_midi=62),
                        RenderedLayerNote(note_midi=64),
                        RenderedLayerNote(note_midi=65),
                        RenderedLayerNote(note_midi=67),
                        RenderedLayerNote(note_midi=69),
                    ),
                ),
            ),
        ),
    )

    timeline = flatten_arrangement_to_timeline(arrangement)

    assert all(event.role == "cloud" for event in timeline.events)
    assert tuple(event.voice_id for event in timeline.events) == (
        "cloud_voice_1",
        "cloud_voice_2",
        "cloud_voice_3",
        "cloud_voice_4",
        "cloud_voice_5",
        "cloud_voice_6",
    )
