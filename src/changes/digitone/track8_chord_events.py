"""Track 8 chord trigger event model extracted from RenderedArrangement.

This module intentionally prepares a Changes-side intermediate event model only.
It does not perform SysEx encoding and does not call digitone-syx-toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from changes.models.rendered_arrangement import RenderedArrangement

Track8LengthMode = Literal["explicit_event_length", "inherit"]

TRACK8_INDEX_0BASED = 7
TRACK8_MAX_NOTES_PER_STEP = 16
DIGITONE_NOTE_MIN_MIDI = 0
DIGITONE_NOTE_MAX_MIDI = 127
MICRO_TIMING_MIN = -23
MICRO_TIMING_MAX = 23
CHANGES_CHORD_V1_NOTES_PER_EVENT = 6


@dataclass(frozen=True)
class Track8ChordNote:
    note_midi: int
    velocity: int
    length_mode: Track8LengthMode
    micro_timing: int = 0


@dataclass(frozen=True)
class Track8ChordEvent:
    id: str
    source_harmony_id: str
    symbol: str
    onset_quarters: Fraction
    duration_quarters: Fraction
    track_index_0based: int
    notes: tuple[Track8ChordNote, ...]
    diagnostics: tuple[str, ...] = ()


def _validate_track_index(track_index_0based: int) -> None:
    if track_index_0based != TRACK8_INDEX_0BASED:
        raise ValueError(
            f"Track 8 chord event extraction currently supports only track_index_0based={TRACK8_INDEX_0BASED}: "
            f"got {track_index_0based}"
        )


def _validate_chord_shape(note_count: int, velocity_count: int) -> None:
    if note_count > TRACK8_MAX_NOTES_PER_STEP:
        raise ValueError(
            f"Track 8 chord note count exceeds max {TRACK8_MAX_NOTES_PER_STEP}: {note_count}"
        )
    if note_count != CHANGES_CHORD_V1_NOTES_PER_EVENT:
        raise ValueError(
            f"Changes Chord v1 requires exactly {CHANGES_CHORD_V1_NOTES_PER_EVENT} notes per chord event: {note_count}"
        )
    if velocity_count != note_count:
        raise ValueError(
            f"Chord velocity count must match chord note count: velocities={velocity_count} notes={note_count}"
        )


def _validate_note_and_velocity(note_midi: int, velocity: int) -> None:
    if note_midi < DIGITONE_NOTE_MIN_MIDI or note_midi > DIGITONE_NOTE_MAX_MIDI:
        raise ValueError(
            f"Track 8 chord note MIDI out of range {DIGITONE_NOTE_MIN_MIDI}..{DIGITONE_NOTE_MAX_MIDI}: {note_midi}"
        )
    if velocity < 1 or velocity > 127:
        raise ValueError(f"Track 8 chord note velocity out of range 1..127: {velocity}")


def _validate_micro_timing(micro_timing: int) -> None:
    if micro_timing < MICRO_TIMING_MIN or micro_timing > MICRO_TIMING_MAX:
        raise ValueError(
            f"Track 8 micro timing out of range {MICRO_TIMING_MIN}..{MICRO_TIMING_MAX}: {micro_timing}"
        )


def extract_track8_chord_events(
    arrangement: RenderedArrangement,
    *,
    track_index_0based: int = TRACK8_INDEX_0BASED,
) -> tuple[Track8ChordEvent, ...]:
    _validate_track_index(track_index_0based)

    out: list[Track8ChordEvent] = []
    for occurrence_index, occurrence in enumerate(arrangement.occurrences, start=1):
        if occurrence.chord is None:
            continue

        chord = occurrence.chord
        _validate_chord_shape(len(chord.notes), len(chord.velocities))

        notes: list[Track8ChordNote] = []
        for note_index, note in enumerate(chord.notes):
            velocity = chord.velocities[note_index]
            _validate_note_and_velocity(note.note_midi, velocity)
            micro_timing = 0
            _validate_micro_timing(micro_timing)
            notes.append(
                Track8ChordNote(
                    note_midi=note.note_midi,
                    velocity=velocity,
                    length_mode=chord.length_mode,
                    micro_timing=micro_timing,
                )
            )

        occurrence_key = occurrence.id if occurrence.id else f"occ{occurrence_index}"
        out.append(
            Track8ChordEvent(
                id=f"{occurrence_key}_track8_chord",
                source_harmony_id=occurrence.source_harmony_id,
                symbol=occurrence.symbol,
                onset_quarters=occurrence.onset_quarters,
                duration_quarters=occurrence.duration_quarters,
                track_index_0based=track_index_0based,
                notes=tuple(notes),
                diagnostics=occurrence.diagnostics + chord.diagnostics,
            )
        )

    return tuple(out)
