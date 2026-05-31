"""Rendered timeline dataclasses and serialization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


def _fraction_to_text(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def _fraction_from_text(v: str | int | float) -> Fraction:
    return Fraction(str(v))


@dataclass(frozen=True)
class RenderedNoteEvent:
    id: str
    voice_id: str
    role: str
    note_midi: int
    onset_quarters: Fraction
    duration_quarters: Fraction
    source_harmony_id: str
    retrigger: bool
    velocity: int | str | None = None


@dataclass(frozen=True)
class RenderedTimeline:
    title: str
    performance_tempo: Fraction
    events: tuple[RenderedNoteEvent, ...]


def rendered_timeline_to_dict(timeline: RenderedTimeline) -> dict:
    return {
        "title": timeline.title,
        "performance_tempo": _fraction_to_text(timeline.performance_tempo),
        "events": [
            {
                "id": e.id,
                "voice_id": e.voice_id,
                "role": e.role,
                "note_midi": e.note_midi,
                "onset_quarters": _fraction_to_text(e.onset_quarters),
                "duration_quarters": _fraction_to_text(e.duration_quarters),
                "source_harmony_id": e.source_harmony_id,
                "retrigger": e.retrigger,
                "velocity": e.velocity,
            }
            for e in timeline.events
        ],
    }


def rendered_timeline_from_dict(data: dict) -> RenderedTimeline:
    events = tuple(
        RenderedNoteEvent(
            id=str(e["id"]),
            voice_id=str(e["voice_id"]),
            role=str(e["role"]),
            note_midi=int(e["note_midi"]),
            onset_quarters=_fraction_from_text(e["onset_quarters"]),
            duration_quarters=_fraction_from_text(e["duration_quarters"]),
            source_harmony_id=str(e["source_harmony_id"]),
            retrigger=bool(e["retrigger"]),
            velocity=e.get("velocity"),
        )
        for e in data.get("events", [])
    )
    return RenderedTimeline(
        title=str(data.get("title") or "Untitled"),
        performance_tempo=_fraction_from_text(data.get("performance_tempo", "120")),
        events=events,
    )
