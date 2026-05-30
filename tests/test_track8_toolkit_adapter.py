from __future__ import annotations

from fractions import Fraction

import pytest

from changes.digitone.track8_chord_events import extract_track8_chord_events
from changes.digitone.track8_toolkit_adapter import changes_track8_payload_to_toolkit_events
from changes.digitone.track8_toolkit_payload import track8_chord_events_to_toolkit_payload
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_renderer import render_arrangement


def _minimal_song_model() -> SongModel:
    return SongModel(
        title="Schema Align",
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


def _build_valid_payload() -> dict:
    arrangement = render_arrangement(_minimal_song_model())
    events = extract_track8_chord_events(arrangement)
    return track8_chord_events_to_toolkit_payload(events)


def test_cmaj7_changes_payload_maps_to_toolkit_events_with_preserved_order():
    payload = _build_valid_payload()

    toolkit_events = changes_track8_payload_to_toolkit_events(payload)

    assert len(toolkit_events) == 6
    assert all(event["track"] == 8 for event in toolkit_events)
    assert all(event["step"] == 1 for event in toolkit_events)
    assert tuple(event["note"] for event in toolkit_events) == ("C4", "E4", "G4", "B4", "D5", "A5")
    assert tuple(event["velocity"] for event in toolkit_events) == (70, 70, 70, 50, 70, 50)
    assert all(event["time"] == 0 for event in toolkit_events)


def test_grouped_event_expands_to_same_step_flat_note_events():
    payload = _build_valid_payload()

    toolkit_events = changes_track8_payload_to_toolkit_events(payload)

    assert len(toolkit_events) == 6
    assert {event["step"] for event in toolkit_events} == {1}
    assert {event["track"] for event in toolkit_events} == {8}


def test_rejects_invalid_payload_type_or_version():
    payload = _build_valid_payload()

    payload_bad_type = dict(payload)
    payload_bad_type["type"] = "wrong"
    with pytest.raises(ValueError, match="payload type"):
        changes_track8_payload_to_toolkit_events(payload_bad_type)

    payload_bad_version = dict(payload)
    payload_bad_version["version"] = 2
    with pytest.raises(ValueError, match="payload version"):
        changes_track8_payload_to_toolkit_events(payload_bad_version)


def test_rejects_invalid_note_count():
    payload = _build_valid_payload()

    payload_zero = dict(payload)
    payload_zero["events"] = [dict(payload["events"][0])]
    payload_zero["events"][0]["notes"] = []
    with pytest.raises(ValueError, match="at least one note"):
        changes_track8_payload_to_toolkit_events(payload_zero)

    payload_too_many = dict(payload)
    payload_too_many["events"] = [dict(payload["events"][0])]
    payload_too_many["events"][0]["notes"] = payload["events"][0]["notes"] * 3
    with pytest.raises(ValueError, match="max notes"):
        changes_track8_payload_to_toolkit_events(payload_too_many)


@pytest.mark.parametrize(
    "patch",
    [
        ("note_midi", 128, "note_midi"),
        ("velocity", 0, "velocity"),
        ("velocity", 128, "velocity"),
        ("micro_timing", 24, "micro_timing"),
        ("micro_timing", -24, "micro_timing"),
    ],
)
def test_rejects_invalid_note_velocity_time(patch: tuple[str, int, str]):
    field, value, expected = patch
    payload = _build_valid_payload()
    mutated = dict(payload)
    mutated["events"] = [dict(payload["events"][0])]
    note0 = dict(payload["events"][0]["notes"][0])
    note0[field] = value
    notes = list(payload["events"][0]["notes"])
    notes[0] = note0
    mutated["events"][0]["notes"] = notes

    with pytest.raises(ValueError, match=expected):
        changes_track8_payload_to_toolkit_events(mutated)


def test_metadata_policy_includes_source_fields():
    payload = _build_valid_payload()

    toolkit_events = changes_track8_payload_to_toolkit_events(payload)

    metadata = toolkit_events[0]["metadata"]
    assert metadata["changes_event_id"] == "h1_track8_chord"
    assert metadata["source_harmony_id"] == "h1"
    assert metadata["symbol"] == "Cmaj7"


def test_explicit_length_mode_is_marked_as_deferred_with_duration_context():
    payload = _build_valid_payload()

    toolkit_events = changes_track8_payload_to_toolkit_events(payload)

    assert all(event.get("length_mode") == "explicit_event_length" for event in toolkit_events)
    assert all(event.get("duration_quarters") == "4" for event in toolkit_events)
    assert all("length" not in event for event in toolkit_events)


def test_inherit_length_mode_maps_to_toolkit_length_inherit():
    payload = _build_valid_payload()
    payload_inherit = dict(payload)
    payload_inherit["events"] = [dict(payload["events"][0])]
    notes = []
    for note in payload["events"][0]["notes"]:
        patched = dict(note)
        patched["length_mode"] = "inherit"
        notes.append(patched)
    payload_inherit["events"][0]["notes"] = notes

    toolkit_events = changes_track8_payload_to_toolkit_events(payload_inherit)

    assert all(event["length"] == "inherit" for event in toolkit_events)


def test_deterministic_event_order_by_step_then_track_then_source_id():
    payload = _build_valid_payload()
    base_event = payload["events"][0]

    event_b = dict(base_event)
    event_b["id"] = "b"
    event_b["step_index_0based"] = 4

    event_a = dict(base_event)
    event_a["id"] = "a"
    event_a["step_index_0based"] = 0

    payload_rev = {
        "version": 1,
        "type": "digitone_track8_chord_payload",
        "steps_per_quarter": 4,
        "events": [event_b, event_a],
    }

    toolkit_events = changes_track8_payload_to_toolkit_events(payload_rev)

    grouped_ids = [event["metadata"]["changes_event_id"] for event in toolkit_events]
    assert grouped_ids[:6] == ["a"] * 6
    assert grouped_ids[6:] == ["b"] * 6
