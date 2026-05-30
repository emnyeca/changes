"""Optional Track 8 YAML validation via digitone-syx-toolkit loader.

This module intentionally keeps toolkit integration optional and lazy.
It does not import toolkit modules at import-time.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable


def _load_toolkit_loader() -> Callable[[str | Path], Any]:
    try:
        module = importlib.import_module("digitone_syx_toolkit.events_yaml")
    except Exception as exc:
        raise RuntimeError(
            "digitone-syx-toolkit is not installed or not importable. "
            "Install it in editable mode for local integration validation."
        ) from exc

    loader = getattr(module, "load_event_assignment_yaml", None)
    if loader is None or not callable(loader):
        raise RuntimeError(
            "digitone-syx-toolkit loader function is unavailable: "
            "digitone_syx_toolkit.events_yaml.load_event_assignment_yaml"
        )
    return loader


def is_digitone_syx_toolkit_available() -> bool:
    """Return True when toolkit YAML loader is importable."""
    try:
        _load_toolkit_loader()
    except RuntimeError:
        return False
    return True


def validate_track8_events_yaml_with_toolkit_loader(
    yaml_text: str,
) -> object:
    """Validate YAML text by parsing it through toolkit's real loader."""
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        raise ValueError("yaml_text must be a non-empty string")

    loader = _load_toolkit_loader()

    with TemporaryDirectory(prefix="changes_track8_yaml_") as temp_dir:
        yaml_path = Path(temp_dir) / "track8_validation.events.yaml"
        yaml_path.write_text(yaml_text, encoding="utf-8")
        assignment = loader(yaml_path)

    return assignment
