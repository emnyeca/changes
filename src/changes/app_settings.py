"""Application settings model and persistence for EUB Changes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

LIBRARY_PATH = Path.home() / "EUBChanges" / "library"
SETTINGS_PATH = LIBRARY_PATH / ".eub_changes_settings.json"


@dataclass
class AppSettings:
    library_path: str = field(default_factory=lambda: str(LIBRARY_PATH))

    # Cloud
    cloud_trigger_policy: str = "hold_until_change"  # hold_until_change | retrigger
    cloud_center_midi: int = 60   # C4
    cloud_track_base: int = 1     # voices map to track_base .. track_base+5

    # Bass
    bass_trigger_policy: str = "hold_until_change"
    bass_center_midi: int = 36    # C2
    bass_track: int = 7
    bass_switch_enabled: bool = False
    bass_switch_every: int = 4

    # Chord
    chord_trigger_policy: str = "retrigger"
    chord_center_midi: int = 60   # C4
    chord_track: int = 8

    # Safety
    confirm_before_hardware_write: bool = True

    # MIDI destination
    destination: str = "Internal"


def load_settings() -> AppSettings:
    if SETTINGS_PATH.exists():
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            defaults = asdict(AppSettings())
            merged = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
            return AppSettings(**merged)
        except Exception:
            pass
    return AppSettings()


def save_settings(settings: AppSettings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
