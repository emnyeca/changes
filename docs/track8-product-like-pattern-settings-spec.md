# Track 8 Product-like Pattern Settings Specification

## Purpose

This document converts the Phase 4H open questions into product-like Digitone pattern settings decisions.

It does not implement these settings.

## Scope

This specification covers the target behavior for product-like Track 8 chord export.

It does not validate hardware behavior.

It does not modify SysEx generation.

It does not modify bundle planner behavior.

## Context: what Phase 4G revealed

The Phase 4G fixture was Track-8-only. When loaded to Digitone II, Track 1-7 showed
the base empty template defaults rather than the intended product default output spec.
This is expected for a Track-8-only fixture: Changes only emits events for active tracks,
and the template supplies all other defaults.

This means the caveat about Track 1-7 LEN / VEL defaults "not matching intended spec"
is a product-readiness gap, not a bug in the Track 8 chord-trigger logic.

## Decisions

### Decision 1: LENGTH / SPEED / CHANGE / RESET modes

Product-like export should use PER TRACK mode for:

- LENGTH
- SPEED
- CHANGE
- RESET

This is already the stated target in `docs/design/digitone-native-syx-backend.md`:

- pattern.mode = per-track
- Track 1..8 LENGTH = Changes-computed total_steps
- Track 1..8 SPEED = Changes-computed speed
- pattern-shared CHANGE = OFF
- pattern-shared RESET = INF

The Phase 4G fixture used pattern-wide mode because it was a Track-8-only scoped fixture.
Product-like export will use per-track mode per the existing design.

Rationale:

Track 8 chord export needs independent length/speed from Tracks 1-7.
Global/shared modes would cause Track 8 chord behavior to affect unrelated tracks.

### Decision 2: Track 1-7 VEL default

Track 1-7 trigger-level VEL uses `inherit` at the trigger record level and falls back to
the track_default_velocity table already defined in `src/changes/models/digitone_target_profile.py`:

- Track 1: 70
- Track 2: 70
- Track 3: 70
- Track 4: 50
- Track 5: 70
- Track 6: 50
- Track 7: 100

This value is already present in `default_digitone_target_profile()`. No guessing is needed.

Rationale:

Track 1-7 VEL is already part of the default output profile. It was not applied in the
Phase 4G fixture because the fixture contained no Track 1-7 events.

### Decision 3: Track 1-7 LEN default

Track 1-7 trigger-level LEN is not a fixed per-track default value.
It is computed per event using `length_strategy = hold_until_next_event`.
Each trigger gets an explicit length_code derived from its duration_quarters.

There is no single "Track 1-7 default LEN" to define.

If an exported pattern contains no Track 1-7 events, Track 1-7 LEN state in the loaded
pattern comes from the base empty template, not from Changes.

SPEC-OPEN: The base empty template LEN state for Track 1-7 (when no events are emitted)
is not currently inspected. Phase 4J must confirm whether the template default LEN
state is acceptable for product-like patterns where Track 1-7 events are absent.

Rationale:

LEN is an event-level property for Cloud/Bass voices. Changes computes it from
hold_until_next_event. A fixed per-track fallback does not apply to the Cloud engine model.

### Decision 4: Track 8 defaults

Track 8 has a separate policy from Tracks 1-7:

- note velocities come from ChordRealizationResult.velocities (e.g. 70 70 70 50 70 50 for Cmaj7)
- explicit note lengths come from event duration_quarters -> length_code
- micro timing defaults to 0
- note order is preserved from realized chord note order
- same-step chord trigger records are permitted up to the toolkit/device limit (16 notes)

Track 8 does not use Track 1-7 default VEL/LEN for chord notes.

Rationale:

Track 8 chord notes carry musically intentional per-note velocity and length from the
chord realization model. They must not be overwritten by Track 1-7 defaults.

### Decision 5: Ownership of product-like defaults

Changes:
  chooses the product export profile and template policy
  emits musical event rows
  preserves chord note order, velocity, length mode, duration, and timing
  supplies track_default_velocity table to the events YAML exporter

digitone-syx-toolkit:
  applies template/default pattern data
  converts toolkit-loadable events YAML to SysEx
  owns low-level Digitone encoding details
  accepts track_defaults.velocity in events YAML

template file:
  stores product-like Digitone pattern state
  should contain PER TRACK modes and baseline track defaults
  is loaded by toolkit builder as the starting state

Rationale:

PER TRACK modes and default track behavior are Digitone pattern state, not pure musical
rendering data. They belong to the template/toolkit layer, with Changes supplying the
policy choice.

### Decision 6: Default template policy

Use:

bundled product-like default template + optional user-supplied template

Product behavior should not require the user to supply a template for basic export.

However, advanced users should be able to provide a template later.

SPEC-OPEN: The current base empty template bundled in digitone-syx-toolkit sets
PATTERN-wide mode. Phase 4J must determine whether a separate PER TRACK template is
needed, and if so, whether it should be bundled in toolkit, in Changes, or generated
dynamically.

Rationale:

Bundled template gives reproducible default output. Optional user template keeps the
workflow extensible. Requiring a template from the user makes the first usable export
too difficult.

### Decision 7: Relationship with bundle planner

Product-like pattern settings should be treated as export profile / template concerns,
not as bundle planner musical allocation concerns.

Bundle planner:
  decides musical allocation
  decides pattern/section/track placement

Product-like export profile/template:
  decides Digitone pattern initialization
  decides PER TRACK modes
  decides baseline LEN/VEL defaults
  decides device-specific starting state

Rationale:

Bundle planner should not become responsible for device initialization policy.

## Product-like target settings table

| Setting | Target | Owner | Status |
|---|---|---|---|
| LENGTH mode | PER TRACK | template/toolkit | decided |
| SPEED mode | PER TRACK | template/toolkit | decided |
| CHANGE mode | PER TRACK (OFF) | template/toolkit | decided |
| RESET mode | PER TRACK (INF) | template/toolkit | decided |
| Track 1-7 VEL | {1:70,2:70,3:70,4:50,5:70,6:50,7:100} | Changes track_default_velocity | decided |
| Track 1-7 LEN | event-level via hold_until_next_event | Changes events | decided |
| Track 1-7 LEN (template default) | base empty template state when no events | template | SPEC-OPEN |
| Track 8 LEN | chord event length_code | Changes events + toolkit | decided |
| Track 8 VEL | ChordRealizationResult.velocities | Changes chord realization | decided |
| Track 8 micro timing | 0 by default | Changes event model | decided |
| Track 8 note order | preserve realized order | Changes event model | decided |
| Template policy | bundled default + optional user template | Changes/toolkit boundary | SPEC-OPEN (PER TRACK template source) |
| Bundle planner relation | separate from device initialization | architecture | decided |

## Requirements for Phase 4J

Phase 4J must inspect digitone-syx-toolkit and determine whether the product-like
settings are currently expressible through events YAML, template pattern file, builder
defaults, or direct builder API.

Phase 4J must specifically answer:

1. Can LENGTH / SPEED / CHANGE / RESET PER TRACK modes be expressed in events YAML today?
2. If yes, where?
3. If no, should support be added to toolkit, a template file, or Changes?
4. Can Track 1-7 VEL defaults be expressed via track_defaults.velocity in events YAML today?
5. If yes, does it propagate correctly to the built SysEx?
6. What LEN state does the base empty template set for Track 1-7 when no events are emitted?
7. Is there already a PER TRACK template in toolkit?
8. Does build_syx_from_events(..., template_file=None) use the base empty template?
9. If so, what PER TRACK / LEN / VEL state does it contain?
10. Should Changes pass an explicit PER TRACK template file for product-like export?

## Non-goals

This phase does not:

- implement PER TRACK modes
- edit toolkit behavior
- generate new SysEx
- generate new fixture files
- modify existing fixtures
- validate hardware
- does not implement any of the settings defined in this document
- does not validate hardware behavior for PER TRACK mode
- does not modify bundle planner
- does not modify UI
