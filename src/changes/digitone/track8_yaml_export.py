"""Track 8 toolkit-loadable events YAML utilities for Changes Phase 4D.

This module intentionally does not import or call digitone-syx-toolkit.
"""

from __future__ import annotations

from typing import Any

import yaml

from changes.digitone.track8_length_encoding import encode_digitone_length_from_duration_quarters

_TRACK8_INDEX_1BASED = 8
_ALLOWED_PATTERN_SPEEDS = {"2", "3/2", "1", "3/4", "1/2", "1/4", "1/8"}


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


def _normalize_length_code(value: Any, field: str) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer or string")
    if isinstance(value, int):
        code = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{field} must not be empty")
        try:
            code = int(text, 16) if text.lower().startswith("0x") else int(text, 10)
        except ValueError as exc:
            raise ValueError(f"{field} is not a valid length code: {value!r}") from exc
    else:
        raise ValueError(f"{field} must be an integer or string")

    if code < 0x00 or code > 0x7F:
        raise ValueError(f"{field} out of range 0x00..0x7F: {code}")
    return f"0x{code:02X}"


def finalize_track8_toolkit_event_lengths(
    rows: list[dict],
    *,
    explicit_length_field: str = "length_code",
) -> list[dict]:
    """Finalize deferred explicit lengths into toolkit-compatible length fields."""
    if explicit_length_field != "length_code":
        raise ValueError("explicit_length_field must be 'length_code'")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list of mappings")

    out: list[dict[str, Any]] = []
    for idx, raw in enumerate(rows, start=1):
        row = dict(_require_mapping(raw, f"rows[{idx}]"))

        if "length" in row and "length_code" in row:
            raise ValueError(f"rows[{idx}] must not include both length and length_code")

        if row.get("length_mode") == "explicit_event_length":
            duration_quarters = row.get("duration_quarters")
            if duration_quarters is None:
                raise ValueError(f"rows[{idx}].duration_quarters is required for explicit_event_length")
            row["length_code"] = encode_digitone_length_from_duration_quarters(str(duration_quarters))
            row.pop("length_mode", None)
            row.pop("duration_quarters", None)
        elif "length_mode" in row or "duration_quarters" in row:
            raise ValueError(
                f"rows[{idx}] has unresolved deferred length fields: "
                f"length_mode={row.get('length_mode')!r} duration_quarters={row.get('duration_quarters')!r}"
            )

        if "length" in row:
            if str(row["length"]).strip().lower() != "inherit":
                raise ValueError(f"rows[{idx}].length must be inherit when provided")
            row["length"] = "inherit"

        if "length_code" in row:
            row["length_code"] = _normalize_length_code(row["length_code"], f"rows[{idx}].length_code")

        if "length" not in row and "length_code" not in row:
            raise ValueError(f"rows[{idx}] must include length or length_code")

        out.append(row)

    return out


def build_track8_events_yaml_payload(
    finalized_rows: list[dict],
    *,
    name: str | None = None,
    tempo: float = 120.0,
    pattern_speed: str = "1/8",
    total_steps: int | None = None,
    include_metadata: bool = False,
) -> dict:
    """Build toolkit-loadable events YAML payload mapping for Track 8 rows."""
    if not isinstance(finalized_rows, list):
        raise ValueError("finalized_rows must be a list of mappings")

    if pattern_speed not in _ALLOWED_PATTERN_SPEEDS:
        raise ValueError(f"pattern_speed must be one of {sorted(_ALLOWED_PATTERN_SPEEDS)}: {pattern_speed}")

    if tempo < 30.0 or tempo > 300.0:
        raise ValueError(f"tempo must be in 30.0..300.0: {tempo}")

    payload_events: list[dict[str, Any]] = []
    for idx, raw in enumerate(finalized_rows, start=1):
        row = _require_mapping(raw, f"finalized_rows[{idx}]")

        if "length_mode" in row or "duration_quarters" in row:
            raise ValueError(
                f"finalized_rows[{idx}] has unresolved deferred length fields and must be finalized first"
            )

        step = _as_int(row.get("step"), f"finalized_rows[{idx}].step")
        track = _as_int(row.get("track"), f"finalized_rows[{idx}].track")
        velocity_raw = row.get("velocity")
        time = _as_int(row.get("time", 0), f"finalized_rows[{idx}].time")

        if step < 1:
            raise ValueError(f"finalized_rows[{idx}].step must be >= 1: {step}")
        if track != _TRACK8_INDEX_1BASED:
            raise ValueError(f"finalized_rows[{idx}].track must be 8 for the Chord layer: {track}")
        if time < -23 or time > 23:
            raise ValueError(f"finalized_rows[{idx}].time must be in -23..23: {time}")

        note = str(row.get("note", "")).strip()
        if not note:
            raise ValueError(f"finalized_rows[{idx}].note is required")

        if isinstance(velocity_raw, str) and velocity_raw.strip().lower() == "inherit":
            velocity: int | str = "inherit"
        else:
            velocity = _as_int(velocity_raw, f"finalized_rows[{idx}].velocity")
            if velocity < 1 or velocity > 127:
                raise ValueError(f"finalized_rows[{idx}].velocity must be 1..127 or inherit")

        has_length = "length" in row
        has_length_code = "length_code" in row
        if has_length and has_length_code:
            raise ValueError(f"finalized_rows[{idx}] must not include both length and length_code")
        if not has_length and not has_length_code:
            raise ValueError(f"finalized_rows[{idx}] must include length or length_code")

        out_row: dict[str, Any] = {
            "step": step,
            "track": track,
            "note": note,
            "velocity": velocity,
            "time": time,
        }

        if has_length:
            if str(row["length"]).strip().lower() != "inherit":
                raise ValueError(f"finalized_rows[{idx}].length must be inherit")
            out_row["length"] = "inherit"
        else:
            out_row["length_code"] = _normalize_length_code(
                row["length_code"], f"finalized_rows[{idx}].length_code"
            )

        if include_metadata and "metadata" in row:
            out_row["metadata"] = row["metadata"]

        payload_events.append(out_row)

    if total_steps is None:
        max_step = max((event["step"] for event in payload_events), default=1)
        total_steps = max(16, max_step)

    if total_steps < 2 or total_steps > 128:
        raise ValueError(f"total_steps must be in 2..128: {total_steps}")

    payload: dict[str, Any] = {
        "version": 1,
        "device": "digitone2",
        "pattern": {
            "mode": "pattern-wide",
            "tempo": float(tempo),
            "speed": pattern_speed,
            "total_steps": int(total_steps),
        },
        "events": payload_events,
    }

    if name is not None:
        payload["name"] = str(name)

    return payload


def dump_track8_events_yaml(payload: dict) -> str:
    """Serialize payload mapping into YAML text for toolkit-facing artifacts."""
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
