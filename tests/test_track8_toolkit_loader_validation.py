from __future__ import annotations

from fractions import Fraction

import pytest

from changes.digitone.track8_chord_events import extract_track8_chord_events
from changes.digitone.track8_toolkit_adapter import changes_track8_payload_to_toolkit_events
from changes.digitone.track8_toolkit_payload import track8_chord_events_to_toolkit_payload
from changes.digitone.track8_toolkit_validation import (
    is_digitone_syx_toolkit_available,
    validate_track8_events_yaml_with_toolkit_loader,
)
from changes.digitone.track8_yaml_export import (
    build_track8_events_yaml_payload,
    dump_track8_events_yaml,
    finalize_track8_toolkit_event_lengths,
)
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_renderer import render_arrangement


def _minimal_song_model() -> SongModel:
    return SongModel(
        title="Toolkit Loader Validation",
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


def test_full_cmaj7_yaml_payload_is_toolkit_loadable_when_available():
    pytest.importorskip("digitone_syx_toolkit.events_yaml")

    yaml_text = _build_cmaj7_yaml_text()
    assignment = validate_track8_events_yaml_with_toolkit_loader(yaml_text)

    assert assignment.version == 1
    assert assignment.device == "digitone2"
    assert assignment.pattern.mode == "pattern-wide"
    assert assignment.pattern.tempo == 120.0
    assert assignment.pattern.speed == "1/8"
    assert assignment.pattern.total_steps == 16
    assert len(assignment.events) == 6

    assert tuple(event.step for event in assignment.events) == (1, 1, 1, 1, 1, 1)
    assert tuple(event.track for event in assignment.events) == (8, 8, 8, 8, 8, 8)
    assert tuple(event.note for event in assignment.events) == ("C4", "E4", "G4", "B4", "D5", "A5")
    assert tuple(event.velocity for event in assignment.events) == (70, 70, 70, 50, 70, 50)
    assert tuple(event.length_code for event in assignment.events) == (0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E)
    assert tuple(event.time for event in assignment.events) == (0, 0, 0, 0, 0, 0)


def test_generated_yaml_text_contains_toolkit_required_top_level_keys():
    yaml_text = _build_cmaj7_yaml_text()

    assert "version: 1" in yaml_text
    assert "device: digitone2" in yaml_text
    assert "pattern:" in yaml_text
    assert "events:" in yaml_text
    assert "track: 8" in yaml_text
    assert "length_code:" in yaml_text
    assert "0x4E" in yaml_text


def test_validation_helper_raises_clear_error_when_toolkit_missing(monkeypatch: pytest.MonkeyPatch):
    from changes.digitone import track8_toolkit_validation as validation_module

    def _raise_module_not_found(_: str):
        raise ModuleNotFoundError("simulated missing toolkit")

    monkeypatch.setattr(validation_module.importlib, "import_module", _raise_module_not_found)

    assert is_digitone_syx_toolkit_available() is False

    with pytest.raises(RuntimeError, match="digitone-syx-toolkit is not installed or not importable"):
        validate_track8_events_yaml_with_toolkit_loader("version: 1\ndevice: digitone2\n")


def test_toolkit_validation_rejects_malformed_yaml_when_available():
    pytest.importorskip("digitone_syx_toolkit.events_yaml")

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
        validate_track8_events_yaml_with_toolkit_loader(malformed_yaml)
