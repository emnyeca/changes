"""Convert Track8ChordEvent objects to a toolkit-facing plain payload.

This module intentionally does not import or call digitone-syx-toolkit.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from changes.digitone.track8_chord_events import (
    DIGITONE_NOTE_MAX_MIDI,
    DIGITONE_NOTE_MIN_MIDI,
    MICRO_TIMING_MAX,
    MICRO_TIMING_MIN,
    TRACK8_INDEX_0BASED,
    TRACK8_MAX_NOTES_PER_STEP,
    Track8ChordEvent,
)

_ALLOWED_LENGTH_MODES = {"explicit_event_length", "inherit"}


def _validate_steps_per_quarter(steps_per_quarter: int) -> None:
    if not isinstance(steps_per_quarter, int) or steps_per_quarter <= 0:
        raise ValueError(f"steps_per_quarter must be a positive integer: {steps_per_quarter!r}")


def _onset_to_step_index(onset_quarters: Fraction, steps_per_quarter: int) -> int:
    step_fraction = onset_quarters * steps_per_quarter
    if step_fraction.denominator != 1:
        raise ValueError(
            "event onset cannot be represented as an integer step index: "
            f"onset_quarters={onset_quarters} steps_per_quarter={steps_per_quarter} step_fraction={step_fraction}"
        )
    return int(step_fraction)


def _validate_event(event: Track8ChordEvent) -> None:
    if event.track_index_0based != TRACK8_INDEX_0BASED:
        raise ValueError(
            f"track_index_0based must be {TRACK8_INDEX_0BASED} for Track 8 payload: {event.track_index_0based}"
        )
    note_count = len(event.notes)
    if note_count == 0:
        raise ValueError(f"Track 8 payload event must contain at least one note: event_id={event.id}")
    if note_count > TRACK8_MAX_NOTES_PER_STEP:
        raise ValueError(
            f"Track 8 payload event exceeds max note count {TRACK8_MAX_NOTES_PER_STEP}: event_id={event.id} notes={note_count}"
        )

    for note in event.notes:
        if note.velocity < 1 or note.velocity > 127:
            raise ValueError(f"Track 8 payload note velocity out of range 1..127: {note.velocity}")
        if note.note_midi < DIGITONE_NOTE_MIN_MIDI or note.note_midi > DIGITONE_NOTE_MAX_MIDI:
            raise ValueError(
                "Track 8 payload note MIDI out of range "
                f"{DIGITONE_NOTE_MIN_MIDI}..{DIGITONE_NOTE_MAX_MIDI}: {note.note_midi}"
            )
        if note.micro_timing < MICRO_TIMING_MIN or note.micro_timing > MICRO_TIMING_MAX:
            raise ValueError(
                f"Track 8 payload micro timing out of range {MICRO_TIMING_MIN}..{MICRO_TIMING_MAX}: {note.micro_timing}"
            )
        if note.length_mode not in _ALLOWED_LENGTH_MODES:
            raise ValueError(
                "Track 8 payload note length_mode must be one of "
                f"{sorted(_ALLOWED_LENGTH_MODES)}: {note.length_mode!r}"
            )


def track8_chord_events_to_toolkit_payload(
    events: tuple[Track8ChordEvent, ...],
    *,
    steps_per_quarter: int = 4,
) -> dict[str, Any]:
    _validate_steps_per_quarter(steps_per_quarter)

    payload_events: list[dict[str, Any]] = []
    for event in events:
        _validate_event(event)
        step_index_0based = _onset_to_step_index(event.onset_quarters, steps_per_quarter)
        payload_events.append(
            {
                "id": event.id,
                "source_harmony_id": event.source_harmony_id,
                "symbol": event.symbol,
                "track_index_0based": event.track_index_0based,
                "step_index_0based": step_index_0based,
                "onset_quarters": str(event.onset_quarters),
                "duration_quarters": str(event.duration_quarters),
                "notes": [
                    {
                        "note_midi": note.note_midi,
                        "velocity": note.velocity,
                        "length_mode": note.length_mode,
                        "micro_timing": note.micro_timing,
                    }
                    for note in event.notes
                ],
                "diagnostics": list(event.diagnostics),
            }
        )

    payload_events.sort(
        key=lambda e: (
            e["step_index_0based"],
            e["track_index_0based"],
            e["id"],
        )
    )

    return {
        "version": 1,
        "type": "digitone_track8_chord_payload",
        "steps_per_quarter": steps_per_quarter,
        "events": payload_events,
    }
