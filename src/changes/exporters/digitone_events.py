"""Export DigitoneCompilePlan as toolkit-compatible events YAML payload."""

from __future__ import annotations

from collections.abc import Iterable

from changes.models.digitone_bundle_plan import DigitonePatternSegment, DigitoneSongTimingPlan
from changes.models.digitone_compile_plan import DigitoneCompilePlan


def _compiled_events_to_yaml_rows(events: Iterable) -> list[dict]:
    rows: list[dict] = []
    for e in sorted(events, key=lambda x: (x.track, x.step, x.source_event_id)):
        rows.append(
            {
                "step": int(e.step),
                "track": int(e.track),
                "note": str(e.note),
                "velocity": e.velocity,
                "length_code": f"0x{int(e.length_code):02X}",
            }
        )
    return rows


def _track_defaults_payload(track_default_velocity: dict[int, int] | None) -> dict | None:
    if not track_default_velocity:
        return None
    ordered = {int(track): int(velocity) for track, velocity in sorted(track_default_velocity.items())}
    return {"velocity": ordered}


def _track_scale_payload(*, length: int, speed: str) -> dict[int, dict[str, int | str]]:
    return {
        track: {"length": int(length), "speed": str(speed)}
        for track in range(1, 17)
    }


def digitone_compile_plan_to_events_yaml_payload(
    plan: DigitoneCompilePlan,
    *,
    track_default_velocity: dict[int, int] | None = None,
) -> dict:
    payload: dict = {
        "version": 1,
        "device": "digitone2",
        "name": plan.pattern_name,
        "pattern": {
            "mode": "per-track",
            "tempo": float(plan.device_tempo),
            "change": "OFF",
            "reset": "INF",
        },
        "track_scale": _track_scale_payload(length=plan.total_steps, speed=plan.speed),
    }
    track_defaults = _track_defaults_payload(track_default_velocity)
    if track_defaults is not None:
        payload["track_defaults"] = track_defaults
    payload["events"] = _compiled_events_to_yaml_rows(plan.events)
    return payload


def digitone_pattern_segment_to_events_yaml_payload(
    segment: DigitonePatternSegment,
    timing: DigitoneSongTimingPlan,
    *,
    track_default_velocity: dict[int, int] | None = None,
) -> dict:
    payload: dict = {
        "version": 1,
        "device": "digitone2",
        "name": segment.pattern_name,
        "pattern": {
            "mode": "per-track",
            "tempo": float(timing.device_tempo),
            "change": "OFF",
            "reset": "INF",
        },
        "track_scale": _track_scale_payload(length=segment.total_steps, speed=timing.speed),
    }
    track_defaults = _track_defaults_payload(track_default_velocity)
    if track_defaults is not None:
        payload["track_defaults"] = track_defaults
    payload["events"] = _compiled_events_to_yaml_rows(segment.events)
    return payload
