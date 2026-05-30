"""Schema alignment adapter from Changes Track 8 payload to toolkit-style events.

This module does not import or call digitone-syx-toolkit.
"""

from __future__ import annotations

from typing import Any

from changes.digitone.note_encoding import midi_to_digitone_display_note_name

_PAYLOAD_TYPE = "digitone_track8_chord_payload"
_PAYLOAD_VERSION = 1
_TRACK8_INDEX_0BASED = 7
_TOOLKIT_TRACK8_INDEX_1BASED = 8
_MAX_NOTES_PER_STEP = 16
_ALLOWED_LENGTH_MODES = {"explicit_event_length", "inherit"}


def _as_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer: {value!r}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer: {value!r}") from exc


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    return value


def _validate_payload_header(payload: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    payload_type = payload.get("type")
    if payload_type != _PAYLOAD_TYPE:
        raise ValueError(f"payload type must be {_PAYLOAD_TYPE!r}: {payload_type!r}")

    version = _as_int(payload.get("version"), "payload.version")
    if version != _PAYLOAD_VERSION:
        raise ValueError(f"payload version must be {_PAYLOAD_VERSION}: {version}")

    steps_per_quarter = _as_int(payload.get("steps_per_quarter"), "payload.steps_per_quarter")
    if steps_per_quarter <= 0:
        raise ValueError(f"payload.steps_per_quarter must be > 0: {steps_per_quarter}")

    raw_events = payload.get("events")
    if not isinstance(raw_events, list):
        raise ValueError("payload.events must be a list")

    mapped_events: list[dict[str, Any]] = []
    for idx, raw_event in enumerate(raw_events, start=1):
        mapped_events.append(_require_mapping(raw_event, f"payload.events[{idx}]") )

    return steps_per_quarter, mapped_events


def _validate_note(note: dict[str, Any], event_index: int, note_index: int) -> None:
    note_midi = _as_int(note.get("note_midi"), f"events[{event_index}].notes[{note_index}].note_midi")
    if note_midi < 0 or note_midi > 127:
        raise ValueError(
            f"events[{event_index}].notes[{note_index}].note_midi must be in 0..127: {note_midi}"
        )

    velocity = _as_int(note.get("velocity"), f"events[{event_index}].notes[{note_index}].velocity")
    if velocity < 1 or velocity > 127:
        raise ValueError(
            f"events[{event_index}].notes[{note_index}].velocity must be in 1..127: {velocity}"
        )

    micro_timing = _as_int(note.get("micro_timing", 0), f"events[{event_index}].notes[{note_index}].micro_timing")
    if micro_timing < -23 or micro_timing > 23:
        raise ValueError(
            f"events[{event_index}].notes[{note_index}].micro_timing must be in -23..23: {micro_timing}"
        )

    length_mode = note.get("length_mode")
    if length_mode not in _ALLOWED_LENGTH_MODES:
        raise ValueError(
            f"events[{event_index}].notes[{note_index}].length_mode must be one of {sorted(_ALLOWED_LENGTH_MODES)}: {length_mode!r}"
        )


def changes_track8_payload_to_toolkit_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Map Phase-4B Changes Track 8 payload to toolkit-style flat event rows.

    Output is aligned to toolkit `events` row semantics:
    one row per note with keys `step`, `track`, `note`, `velocity`, and `time`.

    Length handling:
    - `inherit` maps directly to toolkit `length: inherit`.
    - `explicit_event_length` remains deferred in this phase and is emitted as
      `length_mode` + `duration_quarters` metadata for Phase 4D.
    """

    _, source_events = _validate_payload_header(payload)

    sorted_source_events = sorted(
        source_events,
        key=lambda e: (
            _as_int(e.get("step_index_0based"), "events[].step_index_0based"),
            _as_int(e.get("track_index_0based"), "events[].track_index_0based"),
            str(e.get("id", "")),
        ),
    )

    out: list[dict[str, Any]] = []
    for event_index, src in enumerate(sorted_source_events, start=1):
        track_index_0based = _as_int(src.get("track_index_0based"), f"events[{event_index}].track_index_0based")
        if track_index_0based != _TRACK8_INDEX_0BASED:
            raise ValueError(
                f"events[{event_index}].track_index_0based must be {_TRACK8_INDEX_0BASED}: {track_index_0based}"
            )

        step_index_0based = _as_int(src.get("step_index_0based"), f"events[{event_index}].step_index_0based")
        if step_index_0based < 0:
            raise ValueError(f"events[{event_index}].step_index_0based must be >= 0: {step_index_0based}")

        notes_raw = src.get("notes")
        if not isinstance(notes_raw, list):
            raise ValueError(f"events[{event_index}].notes must be a list")
        if len(notes_raw) == 0:
            raise ValueError(f"events[{event_index}] must contain at least one note")
        if len(notes_raw) > _MAX_NOTES_PER_STEP:
            raise ValueError(
                f"events[{event_index}] exceeds Track 8 max notes per step ({_MAX_NOTES_PER_STEP}): {len(notes_raw)}"
            )

        duration_quarters = str(src.get("duration_quarters", ""))
        if not duration_quarters:
            raise ValueError(f"events[{event_index}].duration_quarters is required")

        diagnostics = src.get("diagnostics", [])
        if not isinstance(diagnostics, list):
            raise ValueError(f"events[{event_index}].diagnostics must be a list")

        event_id = str(src.get("id", ""))
        if not event_id:
            raise ValueError(f"events[{event_index}].id is required")

        source_harmony_id = str(src.get("source_harmony_id", ""))
        symbol = str(src.get("symbol", ""))

        for note_index, note_raw in enumerate(notes_raw, start=1):
            note = _require_mapping(note_raw, f"events[{event_index}].notes[{note_index}]")
            _validate_note(note, event_index, note_index)

            note_midi = _as_int(note["note_midi"], f"events[{event_index}].notes[{note_index}].note_midi")
            velocity = _as_int(note["velocity"], f"events[{event_index}].notes[{note_index}].velocity")
            micro_timing = _as_int(note.get("micro_timing", 0), f"events[{event_index}].notes[{note_index}].micro_timing")
            length_mode = str(note["length_mode"])

            toolkit_event: dict[str, Any] = {
                "step": step_index_0based + 1,
                "track": _TOOLKIT_TRACK8_INDEX_1BASED,
                "note": midi_to_digitone_display_note_name(note_midi),
                "velocity": velocity,
                "time": micro_timing,
            }

            if length_mode == "inherit":
                toolkit_event["length"] = "inherit"
            else:
                toolkit_event["length_mode"] = "explicit_event_length"
                toolkit_event["duration_quarters"] = duration_quarters

            toolkit_event["metadata"] = {
                "changes_event_id": event_id,
                "source_harmony_id": source_harmony_id,
                "symbol": symbol,
                "diagnostics": list(diagnostics),
                "source_note_index": note_index,
            }

            out.append(toolkit_event)

    out.sort(
        key=lambda e: (
            _as_int(e["step"], "toolkit_event.step"),
            _as_int(e["track"], "toolkit_event.track"),
            _as_int(e["metadata"]["source_note_index"], "toolkit_event.metadata.source_note_index"),
            str(e["metadata"]["changes_event_id"]),
        )
    )
    return out
