# Track 8 Toolkit Payload Adapter (Phase 4B)

## Summary

This phase converts Changes-side Track8ChordEvent objects into a toolkit-facing plain dictionary payload.

It still does not write SysEx.
It still does not import or call digitone-syx-toolkit.

## Conversion Path

SongModel -> RenderedArrangement -> Track8ChordEvent -> toolkit-facing payload

The payload is intentionally plain Python data (dict/list) so it can later be serialized to YAML or passed into a toolkit integration layer.

## Public API

- track8_chord_events_to_toolkit_payload(events, steps_per_quarter=4)

## Payload Characteristics

- top-level fields: version, type, steps_per_quarter, events
- event-level fields include:
  - id
  - source_harmony_id
  - symbol
  - track_index_0based
  - step_index_0based
  - onset_quarters (string)
  - duration_quarters (string)
  - notes
  - diagnostics

## Step Conversion

Step conversion uses steps_per_quarter (default 4):

- step_index_0based = onset_quarters * steps_per_quarter

The onset must map exactly to an integer step using Fraction arithmetic.
If not exact, conversion raises ValueError.

## Duration Handling

Duration remains quarter-note string form in this phase.
No conversion to toolkit length bytes is performed here.

## Preserved Note Data

For each note:

- note_midi is preserved as numeric value
- velocity is preserved as numeric value
- micro_timing is preserved as numeric value
- length_mode is preserved symbolically as:
  - explicit_event_length
  - inherit

## Determinism Rules

- note order inside each event is preserved exactly as input
- events are sorted deterministically by:
  - step_index_0based
  - track_index_0based
  - id

Same-step event merge/reject decisions are deferred to a later bundle/trigger-capacity phase.

## Export-Boundary Validation

The adapter validates boundary constraints and raises ValueError when invalid:

- steps_per_quarter is not a positive integer
- onset cannot be mapped to an integer step
- track_index_0based is not 7
- event note count is zero
- event note count exceeds 16
- note velocity is outside 1..127
- note_midi is outside 0..127
- micro_timing is outside -23..23
- length_mode is not explicit_event_length/inherit

## Later Integration

A later phase can translate this payload into actual toolkit YAML/API schema and then to SysEx generation.
