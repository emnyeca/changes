"""Optional Track 8 SysEx byte generation through digitone-syx-toolkit.

This module is intentionally explicit and isolated:
- toolkit import is lazy (only when function is called)
- no MIDI send/hardware access
- no persistent temp files
"""

from __future__ import annotations

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from changes.digitone.track8_yaml_export import dump_track8_events_yaml


def _load_toolkit_syx_builder() -> Callable[..., Any]:
    try:
        module = importlib.import_module("digitone_syx_toolkit.events_to_syx")
    except Exception as exc:
        raise RuntimeError(
            "digitone-syx-toolkit is not installed or not importable. "
            "Install it in editable mode for local integration validation."
        ) from exc

    builder = getattr(module, "build_syx_from_events", None)
    if builder is None or not callable(builder):
        raise RuntimeError(
            "digitone-syx-toolkit SysEx export API is unavailable: "
            "digitone_syx_toolkit.events_to_syx.build_syx_from_events"
        )
    return builder


def is_digitone_syx_toolkit_sysex_export_available() -> bool:
    """Return True when toolkit SysEx builder API is importable."""
    try:
        _load_toolkit_syx_builder()
    except RuntimeError:
        return False
    return True


def generate_track8_sysex_bytes_with_toolkit(
    yaml_text: str,
) -> bytes:
    """Generate SysEx bytes from toolkit-loadable events YAML text.

    The function is software-only and does not send bytes to MIDI/hardware.
    """
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        raise ValueError("yaml_text must be a non-empty string")

    build_syx_from_events = _load_toolkit_syx_builder()

    with TemporaryDirectory(prefix="changes_track8_syx_") as temp_dir:
        temp_path = Path(temp_dir)
        events_yaml = temp_path / "track8.events.yaml"
        output_syx = temp_path / "track8.syx"

        events_yaml.write_text(yaml_text, encoding="utf-8")

        # Toolkit API writes the output file and returns BuildResult.
        build_syx_from_events(events_yaml=events_yaml, output_file=output_syx)

        if not output_syx.exists():
            raise RuntimeError("digitone-syx-toolkit did not produce output .syx bytes")

        data = output_syx.read_bytes()

    return bytes(data)


def generate_track8_sysex_bytes_from_yaml_payload_with_toolkit(
    yaml_payload: dict,
) -> bytes:
    """Convenience helper for payload dict -> YAML text -> SysEx bytes."""
    yaml_text = dump_track8_events_yaml(yaml_payload)
    return generate_track8_sysex_bytes_with_toolkit(yaml_text)
