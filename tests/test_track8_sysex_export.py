from __future__ import annotations

from fractions import Fraction

import pytest

from changes.digitone.track8_chord_events import extract_track8_chord_events
from changes.digitone.track8_sysex_export import (
    generate_track8_sysex_bytes_with_toolkit,
    is_digitone_syx_toolkit_sysex_export_available,
)
from changes.digitone.track8_toolkit_adapter import changes_track8_payload_to_toolkit_events
from changes.digitone.track8_toolkit_payload import track8_chord_events_to_toolkit_payload
from changes.digitone.track8_yaml_export import (
    build_track8_events_yaml_payload,
    dump_track8_events_yaml,
    finalize_track8_toolkit_event_lengths,
)
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_renderer import render_arrangement


def _minimal_song_model() -> SongModel:
    return SongModel(
        title="Track8 Syx",
        working_key="C",
        performance_tempo=Fraction(120, 1),
        measures=(
            Measure(
                number=1,
                section_id="A",
                meter_numerator=4,
                meter_denominator=4,
                absolute_start_quarters=Fraction(0, 1),
                harmony=(
                    HarmonyEvent(
                        id="h1",
                        symbol="Cmaj7",
                        measure_number=1,
                        offset_quarters=Fraction(0, 1),
                        duration_quarters=Fraction(4, 1),
                    ),
                ),
            ),
        ),
    )


def _build_cmaj7_yaml_text() -> str:
    song = _minimal_song_model()
    arrangement = render_arrangement(song)
    events = extract_track8_chord_events(arrangement)
    changes_payload = track8_chord_events_to_toolkit_payload(events)
    toolkit_rows = changes_track8_payload_to_toolkit_events(changes_payload)
    final_rows = finalize_track8_toolkit_event_lengths(toolkit_rows)
    yaml_payload = build_track8_events_yaml_payload(
        final_rows,
        name="T8 Cmaj7 Changes",
        tempo=120.0,
    )
    return dump_track8_events_yaml(yaml_payload)


def test_missing_toolkit_raises_clear_error(monkeypatch: pytest.MonkeyPatch):
    from changes.digitone import track8_sysex_export as export_module

    def _raise_module_not_found(_: str):
        raise ModuleNotFoundError("simulated missing toolkit")

    monkeypatch.setattr(export_module.importlib, "import_module", _raise_module_not_found)

    assert is_digitone_syx_toolkit_sysex_export_available() is False

    with pytest.raises(RuntimeError, match="digitone-syx-toolkit is not installed or not importable"):
        generate_track8_sysex_bytes_with_toolkit("version: 1\n")


def test_cmaj7_full_yaml_can_generate_sysex_bytes_when_toolkit_available():
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    yaml_text = _build_cmaj7_yaml_text()
    sysex_bytes = generate_track8_sysex_bytes_with_toolkit(yaml_text)

    assert isinstance(sysex_bytes, bytes)
    assert len(sysex_bytes) > 0
    assert sysex_bytes[0] == 0xF0
    assert 0xF7 in sysex_bytes
    assert sysex_bytes[-1] == 0xF7


def test_sysex_generation_is_deterministic_when_toolkit_available():
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    yaml_text = _build_cmaj7_yaml_text()
    sysex_bytes_1 = generate_track8_sysex_bytes_with_toolkit(yaml_text)
    sysex_bytes_2 = generate_track8_sysex_bytes_with_toolkit(yaml_text)

    assert sysex_bytes_1 == sysex_bytes_2


def test_invalid_yaml_fails_through_toolkit_when_available():
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    malformed_yaml = "\n".join(
        [
            "version: 1",
            "device: digitone2",
            "events:",
            "  - step: 1",
            "    track: 8",
            "    note: C4",
            "    velocity: 70",
            "    length_code: '0x4E'",
            "    time: 0",
        ]
    )

    with pytest.raises(Exception):
        generate_track8_sysex_bytes_with_toolkit(malformed_yaml)
