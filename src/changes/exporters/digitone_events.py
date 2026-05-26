"""Export DigitoneCompilePlan as toolkit-compatible events YAML payload."""

from __future__ import annotations

from changes.models.digitone_compile_plan import DigitoneCompilePlan


def digitone_compile_plan_to_events_yaml_payload(plan: DigitoneCompilePlan) -> dict:
    events = []
    for e in sorted(plan.events, key=lambda x: (x.step, x.track, x.source_event_id)):
        events.append(
            {
                "step": int(e.step),
                "track": int(e.track),
                "note": str(e.note),
                "velocity": e.velocity,
                "length_code": f"0x{int(e.length_code):02X}",
            }
        )

    return {
        "version": "0.1",
        "tempo": float(plan.device_tempo),
        "speed": plan.speed,
        "events": events,
    }
