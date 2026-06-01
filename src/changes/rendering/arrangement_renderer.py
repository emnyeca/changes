"""Render SongModel into a structured RenderedArrangement."""

from __future__ import annotations

from fractions import Fraction

from changes.chord_engine import construct_chord_pitch_classes
from changes.chord_parser import parse_chord_core
from changes.chord_realization import ChordRegisterPolicy, realize_chord_register
from changes.harmonic_context import resolve_scale_collection_with_retry_details
from changes.models.render_profile import RenderProfile, default_render_profile
from changes.models.rendered_arrangement import (
    RenderedArrangement,
    RenderedBassLayer,
    RenderedChordLayer,
    RenderedCloudLayer,
    RenderedHarmonyOccurrence,
    RenderedLayerNote,
)
from changes.models.song_model import HarmonyEvent, SongModel
from changes.voice_leading import generate_voice_leading
from changes.voicing import progression_to_voicings
from changes.no_chord import is_no_chord_symbol


def _collect_harmony_events(song: SongModel) -> list[tuple[HarmonyEvent, Fraction, Fraction]]:
    events: list[tuple[HarmonyEvent, Fraction, Fraction]] = []
    for measure in song.measures:
        for harmony in measure.harmony:
            onset = measure.absolute_start_quarters + harmony.offset_quarters
            events.append((harmony, onset, harmony.duration_quarters))
    return events


def _note_for_pitch_class_in_window(pc: int, min_midi: int, max_midi: int) -> int:
    candidates = [note for note in range(min_midi, max_midi + 1) if note % 12 == int(pc)]
    if not candidates:
        raise ValueError(
            f"No pitch-class realization in requested window: pc={pc} range={min_midi}..{max_midi}"
        )
    return min(candidates)


def _to_bars(song: SongModel) -> list[list[str]]:
    return [[h.symbol for h in m.harmony] for m in song.measures]


def render_arrangement(song: SongModel, profile: RenderProfile | None = None) -> RenderedArrangement:
    active_profile = profile if profile is not None else default_render_profile()

    harmony_events = _collect_harmony_events(song)
    playable_events = [
        (harmony, onset, duration)
        for harmony, onset, duration in harmony_events
        if not is_no_chord_symbol(harmony.symbol)
    ]
    progression = [h.symbol for h, _onset, _duration in playable_events]

    if not progression:
        return RenderedArrangement(
            title=song.title or "Untitled",
            performance_tempo=song.performance_tempo,
            occurrences=tuple(),
        )

    raw_cloud_voicings = progression_to_voicings([progression])
    cloud_voicings = generate_voice_leading(
        raw_cloud_voicings,
        min_midi=active_profile.cloud_min_midi,
        max_midi=active_profile.cloud_max_midi,
    )

    if len(cloud_voicings) != len(playable_events):
        raise ValueError("voicing count does not match harmony events")

    rendered_occurrences: list[RenderedHarmonyOccurrence] = []

    for index, ((harmony, onset, duration), cloud_notes_source) in enumerate(
        zip(playable_events, cloud_voicings)
    ):
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

        cloud_notes = tuple(
            RenderedLayerNote(
                note_midi=int(note_midi),
                lane_id=f"cloud_voice_{slot_index}",
            )
            for slot_index, note_midi in enumerate(
                cloud_notes_source[: active_profile.voices],
                start=1,
            )
        )
        cloud_layer = RenderedCloudLayer(role="cloud", notes=cloud_notes)

        bass_layer = None
        if active_profile.bass_enabled:
            bass_source_pc = core.slash_bass_pc if core.slash_bass_pc is not None else core.root_pc
            bass_layer = RenderedBassLayer(
                role="bass",
                note=RenderedLayerNote(
                    note_midi=_note_for_pitch_class_in_window(
                        bass_source_pc,
                        active_profile.bass_min_midi,
                        active_profile.bass_max_midi,
                    ),
                    lane_id="bass",
                ),
                source_pitch_class=bass_source_pc,
            )

        rendered_occurrences.append(
            RenderedHarmonyOccurrence(
                id=harmony.id,
                source_harmony_id=harmony.id,
                symbol=harmony.symbol,
                onset_quarters=onset,
                duration_quarters=duration,
                cloud=cloud_layer,
                chord=chord_layer,
                bass=bass_layer,
            )
        )

    return RenderedArrangement(
        title=song.title or "Untitled",
        performance_tempo=song.performance_tempo,
        occurrences=tuple(rendered_occurrences),
    )
