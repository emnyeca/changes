"""Flatten RenderedArrangement into export-compatible RenderedTimeline.

This adapter preserves timing, source identity, lane assignment, and per-note
velocity where the layer supplies it.
"""

from __future__ import annotations

from changes.models.rendered_arrangement import RenderedArrangement
from changes.models.rendered_timeline import RenderedNoteEvent, RenderedTimeline

DEFAULT_LAYERS = ("cloud", "bass", "chord")
_ALLOWED_LAYERS = frozenset(DEFAULT_LAYERS)

_ROLE_ORDER = {
    "cloud": 0,
    "chord": 1,
    "bass": 2,
}


def _sort_key(event: RenderedNoteEvent) -> tuple[object, int, str, str]:
    return (
        event.onset_quarters,
        _ROLE_ORDER.get(event.role, 99),
        event.voice_id,
        event.id,
    )


def normalize_layers(layers: str | list[str] | tuple[str, ...] | set[str] | None) -> tuple[str, ...]:
    if layers is None:
        return DEFAULT_LAYERS

    raw_layers = layers.split(",") if isinstance(layers, str) else list(layers)
    normalized = tuple(layer.strip().lower() for layer in raw_layers if layer.strip())
    if not normalized:
        raise ValueError("layers must contain at least one of: cloud, bass, chord")

    unknown = sorted(set(normalized) - _ALLOWED_LAYERS)
    if unknown:
        raise ValueError(f"Unsupported layer selection: {', '.join(unknown)}")

    return tuple(layer for layer in DEFAULT_LAYERS if layer in normalized)


def flatten_arrangement_to_timeline(
    arrangement: RenderedArrangement,
    *,
    layers: str | list[str] | tuple[str, ...] | set[str] | None = None,
) -> RenderedTimeline:
    selected_layers = set(normalize_layers(layers))
    events: list[RenderedNoteEvent] = []

    for occurrence_index, occurrence in enumerate(arrangement.occurrences, start=1):
        occurrence_key = occurrence.id if occurrence.id else f"occ{occurrence_index}"

        if "cloud" in selected_layers and occurrence.cloud is not None:
            for note_index, note in enumerate(occurrence.cloud.notes, start=1):
                events.append(
                    RenderedNoteEvent(
                        id=f"{occurrence_key}_cloud_{note_index}",
                        voice_id=note.lane_id or f"cloud_voice_{note_index}",
                        role="cloud",
                        note_midi=note.note_midi,
                        onset_quarters=occurrence.onset_quarters,
                        duration_quarters=occurrence.duration_quarters,
                        source_harmony_id=occurrence.source_harmony_id,
                        retrigger=True,
                        velocity=note.velocity,
                    )
                )

        if "chord" in selected_layers and occurrence.chord is not None:
            for note_index, note in enumerate(occurrence.chord.notes, start=1):
                events.append(
                    RenderedNoteEvent(
                        id=f"{occurrence_key}_chord_{note_index}",
                        voice_id=note.lane_id or f"chord_note_{note_index}",
                        role="chord",
                        note_midi=note.note_midi,
                        onset_quarters=occurrence.onset_quarters,
                        duration_quarters=occurrence.duration_quarters,
                        source_harmony_id=occurrence.source_harmony_id,
                        retrigger=True,
                        velocity=note.velocity,
                    )
                )

        if "bass" in selected_layers and occurrence.bass is not None:
            events.append(
                RenderedNoteEvent(
                    id=f"{occurrence_key}_bass",
                    voice_id=occurrence.bass.note.lane_id or "bass",
                    role="bass",
                    note_midi=occurrence.bass.note.note_midi,
                    onset_quarters=occurrence.onset_quarters,
                    duration_quarters=occurrence.duration_quarters,
                    source_harmony_id=occurrence.source_harmony_id,
                    retrigger=True,
                    velocity=occurrence.bass.note.velocity,
                )
            )

    return RenderedTimeline(
        title=arrangement.title,
        performance_tempo=arrangement.performance_tempo,
        events=tuple(sorted(events, key=_sort_key)),
    )
