# Track 8 Product-like Pattern Settings Specification

## Purpose

This document defines product-like Digitone pattern settings decisions for Track 8 export.

It does not implement these settings.

## Scope

This specification covers the target behavior for product-like Track 8 chord export.

It does not validate hardware behavior.

It does not modify SysEx generation.

It does not modify bundle planner behavior.

## Context

The Track-8-only fixture showed that Track 1-7
the base empty template defaults rather than the intended product default output spec.
This is expected for a Track-8-only fixture: Changes only emits events for active tracks,
and the template supplies all other defaults.

This is treated as a product-readiness gap, not a Track 8 chord-trigger bug.

## Decisions

### Decision 1: LENGTH / SPEED / CHANGE / RESET modes

Product-like export should use PER TRACK mode for:

- LENGTH
- SPEED
- CHANGE
- RESET

This is already the stated target in `docs/digitone-internal-spec.md`:

- pattern.mode = per-track
- Track 1..8 LENGTH = Changes-computed total_steps
- Track 1..8 SPEED = Changes-computed speed
- pattern-shared CHANGE = OFF
- pattern-shared RESET = INF

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

Track 1-7 VEL is already part of the default output profile and applies when Track 1-7 events exist.

### Decision 3: Track 1-7 LEN default

Track 1-7 trigger-level LEN is not a fixed per-track default value.
It is computed per event using `length_strategy = hold_until_next_event`.
Each trigger gets an explicit length_code derived from its duration_quarters.

There is no single "Track 1-7 default LEN" to define.

If an exported pattern contains no Track 1-7 events, Track 1-7 LEN state in the loaded
pattern comes from the base empty template, not from Changes.

OPEN: The base empty template LEN state for Track 1-7 (when no events are emitted)
is not currently inspected and must be verified.

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

OPEN: The current base empty template bundled in digitone-syx-toolkit sets
PATTERN-wide mode. A separate PER TRACK template source is still undecided.

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
| Track 1-7 LEN (template default) | base empty template state when no events | template | OPEN |
| Track 8 LEN | chord event length_code | Changes events + toolkit | decided |
| Track 8 VEL | ChordRealizationResult.velocities | Changes chord realization | decided |
| Track 8 micro timing | 0 by default | Changes event model | decided |
| Track 8 note order | preserve realized order | Changes event model | decided |
| Template policy | bundled default + optional user template | Changes/toolkit boundary | OPEN (PER TRACK template source) |
| Bundle planner relation | separate from device initialization | architecture | decided |

## Open verification items

The following items must be verified to complete this specification:

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

## Scope boundary

This specification does not:

- implement PER TRACK modes
- edit toolkit behavior
- generate new SysEx
- generate new fixture files
- modify existing fixtures
- validate hardware
- modify bundle planner
- modify UI
