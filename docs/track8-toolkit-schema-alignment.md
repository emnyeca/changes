# Track 8 Toolkit Schema Alignment (Phase 4C)

## Scope

This phase aligns Changes Track 8 payloads with the current digitone-syx-toolkit event schema.

Included:

- Changes-side adapter from Phase 4B payload to toolkit-style event rows
- schema inspection summary and mapping documentation

Excluded:

- SysEx generation
- importing/calling digitone-syx-toolkit from Changes
- hardware operation
- bundle planning changes
- UI changes

## Toolkit Schema Inspection Summary

Inspected toolkit files:

- `digitone-syx-toolkit/src/digitone_syx_toolkit/events_yaml.py`
- `digitone-syx-toolkit/tests/test_events_yaml.py`
- `digitone-syx-toolkit/tests/test_events_to_syx.py`
- `digitone-syx-toolkit/examples/generated/track8_chord_trigger_validation/track8_cmaj7_root.events.yaml`
- `digitone-syx-toolkit/docs/hardware-validation/track8-chord-trigger-validation-2026-05.md`
- `digitone-syx-toolkit/README.md`

Observed current toolkit event-row schema (flat events list):

- `step` (1-based)
- `track` (1-based; Track 8 == 8)
- `note` (Digitone display note name, e.g. C4)
- `velocity` (`inherit` or explicit 1..127)
- `length` or `length_code`
- `time` (`-23..23`)

Track 8 chord behavior in toolkit is represented as multiple same-step event rows on track 8, with note order preserved.

## Mapping Table

| Changes field | Toolkit field | Notes |
| --- | --- | --- |
| `event.track_index_0based` | `track` | `7 -> 8` |
| `event.step_index_0based` | `step` | `step_index_0based + 1` |
| `notes[].note_midi` | `note` | Converted to Digitone display note name |
| `notes[].velocity` | `velocity` | Preserved numeric `1..127` |
| `notes[].micro_timing` | `time` | Preserved, range `-23..23` |
| `notes[].length_mode == "inherit"` | `length: inherit` | Direct mapping |
| `notes[].length_mode == "explicit_event_length"` | deferred fields | Kept as `length_mode` + `duration_quarters` until Phase 4D |
| `event.id` | `metadata.changes_event_id` | Source trace |
| `event.source_harmony_id` | `metadata.source_harmony_id` | Source trace |
| `event.symbol` | `metadata.symbol` | Source trace |

## Length Handling

Current Changes payload has symbolic length mode and quarter duration, but not finalized toolkit length bytes.

Behavior in this phase:

- `inherit` -> toolkit-compatible `length: inherit`
- `explicit_event_length` -> deferred representation:
  - `length_mode: explicit_event_length`
  - `duration_quarters: <string>`

Exact toolkit length encoding (`length` display token or `length_code`) is deferred to Phase 4D.

## Micro Timing

Toolkit key name is `time` and accepted range is `-23..23`.
This adapter maps Changes `micro_timing` directly to toolkit `time` with boundary validation.

## Note Order

Note order is preserved exactly from Changes grouped chord notes when expanding to flat toolkit-style rows.
This is important because Track 8 representative-note behavior can depend on record order.

## Adapter Output Policy

The adapter returns plain dictionaries matching toolkit event-row semantics as closely as possible, while preserving source metadata in a `metadata` sub-object.

For one Changes grouped chord event, output is multiple flat rows (typically six) with identical step/track and per-note values.

## Scope Boundary

This phase does not:

- write SysEx
- import/call digitone-syx-toolkit
- perform hardware operations
- perform bundle/trigger-capacity merge logic
- modify UI

## Next Phase

Recommended next step:

- Phase 4D: implement explicit length encoding decisions (`length`/`length_code`) and toolkit YAML export/direct toolkit integration.
