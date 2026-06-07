"""Digitone Native SysEx backend wrapper for toolkit interop."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable


def _load_toolkit_builder() -> Callable[..., Any]:
    try:
        mod = importlib.import_module("digitone_syx_toolkit.events_to_syx")
    except ModuleNotFoundError as exc:
        import logging
        logging.getLogger(__name__).debug(
            "digitone_syx_toolkit import failed. "
            "For local development, install digitone-syx-toolkit in the build environment."
        )
        raise ModuleNotFoundError(
            "Digitone SysEx Toolkit could not be loaded.\n"
            "This desktop app may be incomplete or corrupted.\n"
            "Please reinstall EUB Changes or download the latest release."
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
