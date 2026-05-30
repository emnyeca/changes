"""Render SongModel into a structured RenderedArrangement.

Phase 3B only: this module creates the arrangement-level intermediate model
without changing existing RenderedTimeline rendering or export behavior.
"""

from __future__ import annotations

from fractions import Fraction

from changes.chord_engine import construct_chord_pitch_classes
from changes.chord_parser import parse_chord_core
from changes.chord_realization import ChordRegisterPolicy, realize_chord_register
from changes.harmonic_context import resolve_scale_collection_with_retry_details
from changes.models.render_profile import RenderProfile, default_render_profile
from changes.models.rendered_arrangement import (
    RenderedArrangement,
    RenderedChordLayer,
    RenderedHarmonyOccurrence,
    RenderedLayerNote,
)
from changes.models.song_model import HarmonyEvent, SongModel


def _collect_harmony_events(song: SongModel) -> list[tuple[HarmonyEvent, Fraction, Fraction]]:
    events: list[tuple[HarmonyEvent, Fraction, Fraction]] = []
    for measure in song.measures:
        for harmony in measure.harmony:
            onset = measure.absolute_start_quarters + harmony.offset_quarters
            events.append((harmony, onset, harmony.duration_quarters))
    return events


def render_arrangement(song: SongModel, profile: RenderProfile | None = None) -> RenderedArrangement:
    active_profile = profile if profile is not None else default_render_profile()

    harmony_events = _collect_harmony_events(song)
    progression = [h.symbol for h, _onset, _duration in harmony_events]

    rendered_occurrences: list[RenderedHarmonyOccurrence] = []

    for index, (harmony, onset, duration) in enumerate(harmony_events):
        core = parse_chord_core(harmony.symbol)
        resolved = resolve_scale_collection_with_retry_details(progression, index)
        selected_pitch_classes = tuple(sorted(resolved.selected_collection.pitch_classes))

        construction = construct_chord_pitch_classes(core, selected_pitch_classes)
        realization = realize_chord_register(
            construction,
            register_policy=ChordRegisterPolicy(
                min_midi=active_profile.chord_min_midi,
                max_midi=active_profile.chord_max_midi,
            ),
        )

        chord_notes = tuple(
            RenderedLayerNote(
                note_midi=note_midi,
                velocity=velocity,
                lane_id=f"chord_note_{slot_index}",
            )
            for slot_index, (note_midi, velocity) in enumerate(
                zip(realization.realized_midi_notes, realization.velocities),
                start=1,
            )
        )

        chord_layer = RenderedChordLayer(
            role="chord",
            source_pitch_classes=realization.source_pitch_classes,
            canonical_stacked_midi_notes=realization.canonical_stacked_midi_notes,
            realized_midi_notes=realization.realized_midi_notes,
            velocities=realization.velocities,
            length_mode=realization.length_mode,
            notes=chord_notes,
            diagnostics=construction.diagnostics + realization.diagnostics,
        )

        rendered_occurrences.append(
            RenderedHarmonyOccurrence(
                id=harmony.id,
                source_harmony_id=harmony.id,
                symbol=harmony.symbol,
                onset_quarters=onset,
                duration_quarters=duration,
                chord=chord_layer,
            )
        )

    return RenderedArrangement(
        title=song.title or "Untitled",
        performance_tempo=song.performance_tempo,
        occurrences=tuple(rendered_occurrences),
    )
