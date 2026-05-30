# Track 8 Toolkit Template Capability Check

## Purpose
This document checks whether the current digitone-syx-toolkit can express the product-like pattern settings required by Changes Track 8 export.

It does not implement any settings.

## Scope
This phase inspects toolkit capabilities for:

- PER TRACK modes
- Track default velocity
- Track default length / template state
- default template behavior
- explicit template override behavior
- builder API surface

It does not generate new fixture artifacts.

It does not modify toolkit.

It does not modify Changes runtime code.

## Toolkit files inspected

Found and inspected:

- src/digitone_syx_toolkit/events_yaml.py
- src/digitone_syx_toolkit/events_to_syx.py
- src/digitone_syx_toolkit/digitone2/builder.py
- src/digitone_syx_toolkit/digitone2/template.py
- src/digitone_syx_toolkit/digitone2/constants.py
- tests/test_events_yaml.py
- tests/test_events_to_syx.py
- tests/test_digitone2_pattern_settings.py
- examples/generated/track8_chord_trigger_validation/track8_cmaj7_root.events.yaml
- docs/hardware-validation/track8-chord-trigger-validation-2026-05.md
- README.md

Requested paths not found:

- not found: src/digitone_syx_toolkit/digitone2/pattern.py
- not found: src/digitone_syx_toolkit/digitone2/track.py

Additional static evidence checked:

- src/digitone_syx_toolkit/resources/digitone2/BASE_EMPTY.syx
- captures/BASE/*.syx

## Capability matrix

| Capability | Supported today | Mechanism | Evidence | Required follow-up |
|---|---|---|---|---|
| events YAML: PER TRACK LENGTH mode | yes | pattern.mode=per-track + track_scale[1..16].length | events_yaml parser + test_digitone2_pattern_settings | none |
| events YAML: PER TRACK SPEED mode | yes | pattern.mode=per-track + track_scale[1..16].speed | events_yaml parser + test_digitone2_pattern_settings | none |
| events YAML: PER TRACK CHANGE mode | partial | accepts pattern.change only as OFF in per-track mode | events_yaml rejects non-OFF + builder guard | decide if non-OFF needed |
| events YAML: PER TRACK RESET mode | partial | accepts pattern.reset only as INF in per-track mode | events_yaml rejects non-INF + builder guard | decide if non-INF needed |
| events YAML: track_defaults.velocity | yes | track_defaults.velocity map (tracks 1..8) | parser + builder write + tests in test_events_to_syx | none |
| events YAML: track_defaults.length | no | no parser field / no writer | events_yaml only consumes velocity; no track default length map | add schema/API only if required |
| template file: PER TRACK modes | yes (via explicit template) | build_syx_from_events(..., template_file=...) seeds from .syx template | events_to_syx -> builder template_override | validate target template contents |
| template file: Track 1-7 LEN defaults | unknown/available via template bytes | inherited from template when no events write them | builder writes no track default LEN table | map offsets if deterministic control needed |
| template file: Track 1-7 VEL defaults | yes | defaults from template; optionally overridden by track_defaults.velocity | builder _set_track_default_velocity + tests | none |
| builder default template | yes, but not product-like target | load_base_empty_template() -> BASE_EMPTY.syx | template.py + builder.py + static byte read | assess replacement vs explicit template |
| builder explicit template override | yes | template_file argument -> template_override path | events_to_syx + cli --template + tests | add product-like template asset |
| direct builder API for product-like defaults | partial | build_digitone2_syx(EventAssignment, template_override=...) | builder API supports per-track track_scale and velocity map, fixed change/reset | decide extension boundary |

## Findings

### Finding 1: events YAML support
Current events YAML supports:

- pattern.mode = per-track and pattern.mode = pattern-wide
- track-level LENGTH in per-track mode via track_scale[track].length (tracks 1..16 required)
- track-level SPEED in per-track mode via track_scale[track].speed
- track_defaults.velocity map for tracks 1..8

Current events YAML does not support:

- arbitrary per-track CHANGE values
- arbitrary per-track RESET values
- track_defaults.length

For per-track mode, parser behavior is constrained:

- pattern.change must be OFF
- pattern.reset must be INF

So CHANGE and RESET are not represented as per-track value tables today. They are constrained pattern fields tied to per-track mode.

### Finding 2: template support
A template .syx file can carry pattern state, including values not described by events rows, because builder starts from template bytes and applies updates.

This means template can carry:

- PER TRACK mode state
- Track 1-7 LEN default state
- Track 1-7 VEL default state
- Track 8 baseline state

But exact semantic meaning of every byte is not fully proven in code for all LEN defaults. Static code proves template seeding exists; full behavioral confirmation of each field still depends on binary mapping/hardware verification.

### Finding 3: builder default behavior
Yes. build_syx_from_events(..., template_file=None) uses default/base template:

- events_to_syx.build_syx_from_events passes template_file into builder as template_override
- builder.build_digitone2_syx uses load_base_empty_template() when template_override is None
- template loader reads resource file: resources/digitone2/BASE_EMPTY.syx

Observed default template state from static byte inspection:

- PATTERN_MODE_OFFSET(101511) = 0 -> pattern-wide
- PATTERN_SPEED_OFFSET(101512) = 2 (speed code for 1)
- TRACK1_DEFAULT_VEL_OFFSET(1333) = 100
- TRACK1_DEFAULT_LENGTH_OFFSET(1334) = 14

So current built-in default appears pattern-wide, not PER TRACK.

### Finding 4: explicit template override
Yes. build_syx_from_events(..., template_file=...) accepts explicit template path and forwards it to builder as template_override.

Expected format/path:

- file path to a Digitone II .syx template blob

CLI also exposes this via --template.

This looks safe for Changes to pass a product-like template later, because this path already exists and is covered by multiple tests using captures/BASE/*.syx.

### Finding 5: Track 1-7 VEL defaults
Yes. Changes can communicate the existing track_default_velocity table today via:

- track_defaults.velocity in events YAML

Toolkit behavior is proven to apply these values to output SysEx, not just parse them:

- tests/test_events_to_syx.py verifies bytes at TRACK_DEFAULT_VELOCITY_OFFSETS are updated
- partial map behavior is tested (unspecified tracks keep template values)

### Finding 6: Track 1-7 LEN state when no events exist
Today this is controlled by template state.

Reason:

- builder has no track default LEN writer equivalent to track default VEL writer
- parser has no track_defaults.length support
- only one explicit length default offset constant (TRACK1_DEFAULT_LENGTH_OFFSET) is present in constants

What is statically visible:

- BASE_EMPTY track 1 default LEN raw byte at offset 1334 is 14 (0x0E)

What remains unknown:

- complete mapped offsets and semantic defaults for Track 1-7 LEN in toolkit code surface
- whether current BASE_EMPTY LEN defaults match intended product-like defaults for all tracks

### Finding 7: CHANGE / RESET ambiguity
Current toolkit model indicates CHANGE and RESET are pattern-shared fields with per-track-mode constraints, not per-track value tables.

Evidence:

- constants define PATTERN_CHANGE_* and PATTERN_RESET_* as single offsets/masks
- per-track builder path writes pattern change OFF and pattern reset INF to these single fields
- parser enforces change=OFF and reset=INF in per-track mode

Conclusion:

- representation today: pattern-shared settings constrained by mode
- not represented today: independent per-track CHANGE/RESET tables

## Recommended implementation path

Option D: hybrid

template file for pattern state
events YAML for musical events and track_defaults.velocity
Changes chooses template policy
toolkit applies template and encodes SysEx

Why:

- template is already the authoritative carrier for baseline device pattern state
- events YAML already cleanly carries musical events and velocity defaults
- built-in default template is pattern-wide, so product-like PER TRACK should be introduced as an explicit template policy rather than forcing bundle planner or Track8 event model changes

## Recommendation for Changes

Recommendation:

Changes should not try to encode PER TRACK modes directly in Track8ChordEvent or Track 8 toolkit row adapters.

Changes should select a product-like template policy and pass an explicit template file to toolkit for product export.

Track 8 chord event rows should remain focused on musical note events, per-note velocity, per-note length_code, and timing.

Track 1-7 VEL defaults should continue to flow through track_defaults.velocity.

Track 1-7 LEN default state (when no events are present) should be handled via template selection, not event schema expansion in Changes.

## Recommended next phase

Phase 4K: Product-like template fixture design

Phase 4K should:

- define product-like PER TRACK template requirements
- identify source of truth for template defaults
- add template fixture provenance and verification plan
- confirm LEN default expectations for Track 1-7 when events are absent

## Phase 4J answers to the 10 required questions

1. Can LENGTH / SPEED / CHANGE / RESET PER TRACK modes be expressed in events YAML today?
   - LENGTH/SPEED: yes, via track_scale in per-track mode.
   - CHANGE/RESET: only constrained values OFF/INF; no free per-track value tables.
2. Can they be expressed through a template pattern file today?
   - Yes, template bytes can carry these states; exact semantics require template/hardware verification.
3. Can they be expressed through builder defaults today?
   - Default builder template is BASE_EMPTY and appears pattern-wide; not product-like PER TRACK by default.
4. Can they be expressed through direct builder API today?
   - Partially: per-track scale and track default velocity supported; change/reset fixed to OFF/INF in per-track mode.
5. Can Track 1-7 VEL defaults be expressed via track_defaults.velocity in events YAML today?
   - Yes.
6. If yes, does it propagate correctly to built SysEx?
   - Yes, tested in toolkit tests (byte-level assertions at TRACK_DEFAULT_VELOCITY_OFFSETS).
7. What LEN state does the base empty template set for Track 1-7 when no events are emitted?
   - Controlled by template. Track 1 default LEN raw byte is 0x0E at known offset; full Track 1-7 mapped LEN defaults remain partially unknown in exposed code.
8. Is there already a PER TRACK template in toolkit?
   - Not as a bundled resource template; only BASE_EMPTY.syx is bundled under resources.
9. Does build_syx_from_events(..., template_file=None) use the base empty template?
   - Yes.
10. Should Changes pass an explicit PER TRACK template file for product-like export?
   - Yes, recommended.

## Non-goals

This phase does not:

- implement product-like settings
- does not implement runtime behavior changes
- does not modify toolkit
- does not modify Changes runtime code
- generate new .syx fixtures
- modify existing fixtures
