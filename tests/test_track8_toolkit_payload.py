from __future__ import annotations

from fractions import Fraction

import pytest

from changes.digitone.track8_chord_events import (
    TRACK8_INDEX_0BASED,
    Track8ChordEvent,
    Track8ChordNote,
    extract_track8_chord_events,
)
from changes.digitone.track8_toolkit_payload import track8_chord_events_to_toolkit_payload
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_renderer import render_arrangement


def _minimal_song_model() -> SongModel:
    return SongModel(
        title="Payload",
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


def _mk_notes(
    midi: tuple[int, ...] = (48, 52, 55, 59, 62, 69),
    velocity: tuple[int, ...] = (70, 70, 70, 50, 70, 50),
    *,
    length_mode: str = "explicit_event_length",
    micro_timing: int = 0,
) -> tuple[Track8ChordNote, ...]:
    return tuple(
        Track8ChordNote(
            note_midi=midi_note,
            velocity=vel,
            length_mode=length_mode,
            micro_timing=micro_timing,
        )
        for midi_note, vel in zip(midi, velocity)
    )


def _mk_event(
    *,
    event_id: str = "h1_track8_chord",
    source_harmony_id: str = "h1",
    symbol: str = "Cmaj7",
    onset: Fraction = Fraction(0, 1),
    duration: Fraction = Fraction(4, 1),
    track: int = TRACK8_INDEX_0BASED,
    notes: tuple[Track8ChordNote, ...] | None = None,
    diagnostics: tuple[str, ...] = (),
) -> Track8ChordEvent:
    return Track8ChordEvent(
        id=event_id,
        source_harmony_id=source_harmony_id,
        symbol=symbol,
        onset_quarters=onset,
        duration_quarters=duration,
        track_index_0based=track,
        notes=_mk_notes() if notes is None else notes,
        diagnostics=diagnostics,
    )


def test_converts_one_cmaj7_event_from_render_path():
    arrangement = render_arrangement(_minimal_song_model())
    events = extract_track8_chord_events(arrangement)

    payload = track8_chord_events_to_toolkit_payload(events)

    assert payload["version"] == 1
    assert payload["type"] == "digitone_track8_chord_payload"
    assert payload["steps_per_quarter"] == 4
    assert len(payload["events"]) == 1

    event = payload["events"][0]
    assert event["track_index_0based"] == 7
    assert event["step_index_0based"] == 0
    assert event["source_harmony_id"] == "h1"
    assert event["symbol"] == "Cmaj7"
    assert tuple(note["note_midi"] for note in event["notes"]) == (48, 52, 55, 59, 62, 69)
    assert tuple(note["velocity"] for note in event["notes"]) == (70, 70, 70, 50, 70, 50)
    assert all(note["micro_timing"] == 0 for note in event["notes"])
    assert all(note["length_mode"] == "explicit_event_length" for note in event["notes"])


def test_step_conversion_with_fractional_onset():
    events = (_mk_event(onset=Fraction(1, 2)),)

    payload = track8_chord_events_to_toolkit_payload(events, steps_per_quarter=4)

    assert payload["events"][0]["step_index_0based"] == 2


def test_rejects_non_integer_step_position():
    events = (_mk_event(onset=Fraction(1, 3)),)

    with pytest.raises(ValueError, match="integer step"):
        track8_chord_events_to_toolkit_payload(events, steps_per_quarter=4)


@pytest.mark.parametrize("steps_per_quarter", [0, -1])
def test_rejects_invalid_steps_per_quarter(steps_per_quarter: int):
    events = (_mk_event(),)

    with pytest.raises(ValueError, match="steps_per_quarter"):
        track8_chord_events_to_toolkit_payload(events, steps_per_quarter=steps_per_quarter)


def test_sorts_events_deterministically():
    events = (
        _mk_event(event_id="b", onset=Fraction(4, 1)),
        _mk_event(event_id="a", onset=Fraction(0, 1)),
        _mk_event(event_id="c", onset=Fraction(0, 1)),
    )

    payload = track8_chord_events_to_toolkit_payload(events)

    assert tuple(event["id"] for event in payload["events"]) == ("a", "c", "b")


def test_preserves_note_order_inside_event():
    notes = _mk_notes(midi=(60, 48, 67, 52, 69, 55))
    events = (_mk_event(notes=notes),)

    payload = track8_chord_events_to_toolkit_payload(events)

    assert tuple(note["note_midi"] for note in payload["events"][0]["notes"]) == (60, 48, 67, 52, 69, 55)


def test_rejects_invalid_length_mode():
    notes = _mk_notes(length_mode="bad-mode")
    events = (_mk_event(notes=notes),)

    with pytest.raises(ValueError, match="length_mode"):
        track8_chord_events_to_toolkit_payload(events)


@pytest.mark.parametrize("micro_timing", [24, -24])
def test_rejects_invalid_micro_timing(micro_timing: int):
    notes = _mk_notes(micro_timing=micro_timing)
    events = (_mk_event(notes=notes),)

    with pytest.raises(ValueError, match="micro timing"):
        track8_chord_events_to_toolkit_payload(events)


@pytest.mark.parametrize(
    ("midi", "velocity"),
    [
        ((128, 52, 55, 59, 62, 69), (70, 70, 70, 50, 70, 50)),
        ((48, 52, 55, 59, 62, 69), (0, 70, 70, 50, 70, 50)),
        ((48, 52, 55, 59, 62, 69), (128, 70, 70, 50, 70, 50)),
    ],
)
def test_rejects_invalid_note_or_velocity(
    midi: tuple[int, ...],
    velocity: tuple[int, ...],
):
    notes = _mk_notes(midi=midi, velocity=velocity)
    events = (_mk_event(notes=notes),)

    with pytest.raises(ValueError):
        track8_chord_events_to_toolkit_payload(events)


def test_preserves_event_diagnostics_as_list():
    events = (_mk_event(diagnostics=("d1", "d2")),)

    payload = track8_chord_events_to_toolkit_payload(events)

    assert payload["events"][0]["diagnostics"] == ["d1", "d2"]
