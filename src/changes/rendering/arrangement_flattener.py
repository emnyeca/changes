"""Flatten RenderedArrangement into export-compatible RenderedTimeline.

This adapter preserves timing and source identity but intentionally drops
layer-specific metadata that RenderedTimeline does not model yet.
"""

from __future__ import annotations

from changes.models.rendered_arrangement import RenderedArrangement
from changes.models.rendered_timeline import RenderedNoteEvent, RenderedTimeline

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


def flatten_arrangement_to_timeline(arrangement: RenderedArrangement) -> RenderedTimeline:
    events: list[RenderedNoteEvent] = []

    for occurrence_index, occurrence in enumerate(arrangement.occurrences, start=1):
        occurrence_key = occurrence.id if occurrence.id else f"occ{occurrence_index}"

        if occurrence.cloud is not None:
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
                    )
                )

        if occurrence.chord is not None:
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
                    )
                )

        if occurrence.bass is not None:
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
                )
            )

    return RenderedTimeline(
        title=arrangement.title,
        performance_tempo=arrangement.performance_tempo,
        events=tuple(sorted(events, key=_sort_key)),
    )
