"""Digitone Native SysEx backend wrapper for toolkit interop."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable


def _load_toolkit_builder() -> Callable[..., Any]:
    try:
        mod = importlib.import_module("digitone_syx_toolkit.events_to_syx")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "digitone-syx-toolkit is required for Digitone Native SysEx backend. "
            "Install with: pip install -e ../digitone-syx-toolkit"
        ) from exc

    builder = getattr(mod, "build_syx_from_events", None)
    if builder is None:
        raise RuntimeError("digitone_syx_toolkit.events_to_syx.build_syx_from_events is unavailable")
    return builder


def build_digitone_syx_from_events_yaml(
    events_yaml_path: str | Path,
    output_syx_path: str | Path,
) -> Any:
    """Build Digitone II .syx from toolkit-compatible events YAML."""
    build_syx_from_events = _load_toolkit_builder()
    return build_syx_from_events(
        events_yaml=Path(events_yaml_path),
        output_file=Path(output_syx_path),
    )
