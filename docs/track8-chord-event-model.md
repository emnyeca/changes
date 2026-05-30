# Track 8 Chord Event Model (Phase 4A)

## Purpose

This phase introduces a Changes-side event model for Digitone Track 8 chord triggers.

The conversion path is:

RenderedArrangement.chord -> Track8ChordEvent

This phase does not write SysEx and does not call digitone-syx-toolkit.

## Why Use RenderedArrangement.chord Directly

Track 8 export must consume `RenderedArrangement.occurrences[*].chord` directly.

Using legacy `RenderedTimeline role="chord"` is unsafe because that legacy role may still represent the old Cloud-like moving six-voice layer.

`RenderedArrangement.chord` preserves data that Track 8 needs:

- grouped chord trigger notes at one onset
- per-note velocity values
- length mode policy
- diagnostics
- source harmony identity
- onset and duration

## Scope of This Phase

Implemented in this phase:

- Changes-side dataclasses for Track 8 chord notes/events
- Extraction from `RenderedArrangement` chord occurrences
- Validation for v1 constraints

Not implemented in this phase:

- SysEx byte encoding
- digitone-syx-toolkit calls
- bundle planning integration
- MIDI export changes
- UI changes

## Core Model

- `Track8ChordNote`
- `Track8ChordEvent`
- `extract_track8_chord_events(arrangement, track_index_0based=7)`

Constants:

- `TRACK8_INDEX_0BASED = 7`
- `TRACK8_MAX_NOTES_PER_STEP = 16`
- Changes Chord v1 note count per onset: exactly 6

Although Digitone Track 8 supports up to 16 same-step notes, Changes Chord v1 currently uses six notes per chord onset.

## Data Preservation Rules

For each occurrence with a chord layer:

- one `Track8ChordEvent` is created
- note order follows `occurrence.chord.notes` and is not re-sorted
- velocities are copied from `occurrence.chord.velocities`
- length mode is preserved as string (`explicit_event_length` or `inherit`)
- all note `micro_timing` values are set to `0`

Diagnostics are carried as:

- `event.diagnostics = occurrence.diagnostics + occurrence.chord.diagnostics`

## Validation Rules

Extraction raises `ValueError` when:

- target track is not Track 8 (`track_index_0based != 7`)
- chord note count is not exactly 6
- chord note count exceeds 16
- velocity count does not match note count
- velocity is outside `1..127`
- note MIDI is outside `0..127`

## Next Phase

A later phase will map this model into toolkit-facing payloads (YAML/API) and then to SysEx.
