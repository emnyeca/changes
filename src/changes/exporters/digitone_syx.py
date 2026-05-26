"""Compile plan to SYX bytes via optional digitone_syx_toolkit dependency."""

from __future__ import annotations

from changes.exporters.digitone_events import digitone_compile_plan_to_events_yaml_payload
from changes.models.digitone_compile_plan import DigitoneCompilePlan


class DigitoneToolkitMissingError(RuntimeError):
    pass


def compile_plan_to_syx_bytes(plan: DigitoneCompilePlan) -> bytes:
    try:
        from digitone_syx_toolkit import build_syx_from_events
    except Exception as exc:  # pragma: no cover
        raise DigitoneToolkitMissingError(
            "digitone_syx_toolkit is not installed. Install with: pip install -e ../digitone-syx-toolkit"
        ) from exc

    payload = digitone_compile_plan_to_events_yaml_payload(plan)
    return build_syx_from_events(payload)
