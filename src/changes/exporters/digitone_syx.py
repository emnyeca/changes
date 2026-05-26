"""Deprecated path-based wrappers for Digitone SYX generation."""

from __future__ import annotations

from pathlib import Path

from changes.digitone_backend import build_digitone_syx_from_events_yaml


class DigitoneToolkitMissingError(RuntimeError):
    pass


def compile_plan_to_syx_file(*, events_yaml: str | Path, output_syx: str | Path):
    """Deprecated wrapper: use changes.digitone_backend directly in new code."""
    try:
        return build_digitone_syx_from_events_yaml(events_yaml, output_syx)
    except Exception as exc:  # pragma: no cover
        raise DigitoneToolkitMissingError(
            "digitone_syx_toolkit is not installed. Install with: pip install -e ../digitone-syx-toolkit"
        ) from exc
