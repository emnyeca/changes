from __future__ import annotations

from fractions import Fraction

import pytest

from changes.digitone.track8_chord_events import extract_track8_chord_events
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
        title="Yaml Export",
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


def _build_toolkit_rows_from_full_path() -> list[dict]:
    song = _minimal_song_model()
    arrangement = render_arrangement(song)
    events = extract_track8_chord_events(arrangement)
    payload = track8_chord_events_to_toolkit_payload(events)
    return changes_track8_payload_to_toolkit_events(payload)


def test_finalizes_explicit_length_rows_from_full_changes_path():
    toolkit_events = _build_toolkit_rows_from_full_path()

    final_rows = finalize_track8_toolkit_event_lengths(toolkit_events)

    assert len(final_rows) == 6
    assert all(row.get("length_code") == "0x4E" for row in final_rows)
    assert all("length_mode" not in row for row in final_rows)
    assert all("duration_quarters" not in row for row in final_rows)
    assert tuple(row["note"] for row in final_rows) == ("C4", "E4", "G4", "B4", "D5", "A5")
    assert tuple(row["velocity"] for row in final_rows) == (70, 70, 70, 50, 70, 50)
    assert all(row["time"] == 0 for row in final_rows)


def test_preserves_inherit_length_rows():
    rows = [
        {
            "step": 1,
            "track": 8,
            "note": "C4",
            "velocity": 70,
            "length": "inherit",
            "time": 0,
        }
    ]

    final_rows = finalize_track8_toolkit_event_lengths(rows)

    assert final_rows[0]["length"] == "inherit"
    assert "length_code" not in final_rows[0]


def test_builds_toolkit_loadable_payload_without_metadata_by_default():
    rows = finalize_track8_toolkit_event_lengths(_build_toolkit_rows_from_full_path())

    yaml_payload = build_track8_events_yaml_payload(rows)

    assert yaml_payload["version"] == 1
    assert yaml_payload["device"] == "digitone2"
    assert yaml_payload["pattern"]["mode"] == "pattern-wide"
    assert yaml_payload["pattern"]["tempo"] == 120.0
    assert yaml_payload["pattern"]["speed"] == "1/8"
    assert yaml_payload["pattern"]["total_steps"] >= max(row["step"] for row in rows)
    assert "events" in yaml_payload
    assert all("metadata" not in row for row in yaml_payload["events"])


def test_build_can_optionally_include_metadata():
    rows = finalize_track8_toolkit_event_lengths(_build_toolkit_rows_from_full_path())

    yaml_payload = build_track8_events_yaml_payload(rows, include_metadata=True)

    assert all("metadata" in row for row in yaml_payload["events"])


def test_build_rejects_unresolved_deferred_length():
    unresolved_rows = [
        {
            "step": 1,
            "track": 8,
            "note": "C4",
            "velocity": 70,
            "length_mode": "explicit_event_length",
            "duration_quarters": "4",
            "time": 0,
        }
    ]

    with pytest.raises(ValueError, match="must be finalized first"):
        build_track8_events_yaml_payload(unresolved_rows)


def test_finalize_rejects_unsupported_explicit_length_field_option():
    rows = _build_toolkit_rows_from_full_path()

    with pytest.raises(ValueError, match="explicit_length_field"):
        finalize_track8_toolkit_event_lengths(rows, explicit_length_field="length")


def test_build_rejects_row_with_both_length_and_length_code():
    rows = [
        {
            "step": 1,
            "track": 8,
            "note": "C4",
            "velocity": 70,
            "length": "inherit",
            "length_code": "0x1E",
            "time": 0,
        }
    ]

    with pytest.raises(ValueError, match="both length and length_code"):
        build_track8_events_yaml_payload(rows)


def test_dump_yaml_returns_text_with_core_keys():
    rows = finalize_track8_toolkit_event_lengths(_build_toolkit_rows_from_full_path())
    payload = build_track8_events_yaml_payload(rows)

    text = dump_track8_events_yaml(payload)

    assert isinstance(text, str)
    assert "version: 1" in text
    assert "device: digitone2" in text
    assert "events:" in text
