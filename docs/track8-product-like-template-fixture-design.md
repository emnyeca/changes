# Track 8 Product-like Template Fixture Design

## Purpose
This document defines the product-like template fixture needed after the isolated Track 8 Cmaj7 hardware validation.

It does not generate the fixture.

## Scope
This design covers:

- product-like template requirements
- events YAML requirements for product-like fixture generation
- expected generated files
- validation strategy
- known unknowns

It does not implement toolkit changes.

It does not generate SysEx.

It does not validate hardware.

## Design baseline
Use the Phase 4J hybrid recommendation:

template file for baseline Digitone pattern state
events YAML for musical events and track_defaults.velocity
Changes chooses template policy
toolkit applies template and encodes SysEx

## Product-like fixture goals
The next product-like fixture should validate more than the Phase 4G isolated Track 8 fixture.

It should validate:

- Track 8 same-step Cmaj7 chord trigger still works
- pattern mode is PER TRACK
- Track 1-8 LENGTH scale values are explicitly set
- Track 1-8 SPEED scale values are explicitly set
- CHANGE is OFF in per-track mode
- RESET is INF in per-track mode
- Track 1-7 default velocities are applied
- Track 8 default and event velocities remain chord-event driven
- template state does not corrupt Track 8 chord events
- no unrelated Track 1-7 events are required merely to set defaults

## Ownership split

### Template should own
The product-like template should own baseline Digitone pattern state:

- baseline pattern state before events are applied
- PER TRACK-compatible starting state if needed
- baseline Track 1-7 LEN state when no events exist
- any static Digitone state not expressible in events YAML
- optional user-provided starting sound and pattern state in the future

### Events YAML should own
Events YAML should own data that toolkit already supports explicitly:

- pattern.mode = per-track
- pattern.change = OFF
- pattern.reset = INF
- track_scale[1..16].length
- track_scale[1..16].speed
- track_defaults.velocity
- Track 8 chord event rows
- tempo
- pattern name
- total steps and track lengths as applicable

### Changes should own
Changes should own policy selection and musical event generation:

- select default product-like template unless user overrides it
- emit musical note events
- emit Track 8 chord event rows
- emit track_defaults.velocity
- preserve ChordRealizationResult velocities
- preserve chord note order
- avoid embedding binary Digitone template details in musical rendering models

## Target fixture files for next phase
The next implementation phase should generate a new fixture directory:

examples/generated/track8_product_like_validation/

Expected files:

- track8_product_like_cmaj7.events.yaml
- track8_product_like_cmaj7.syx
- track8_product_like_cmaj7_manifest.md

If a template file is generated or bundled, expected candidate locations are:

- examples/generated/track8_product_like_validation/track8_product_like_template.syx

or, if it becomes a reusable asset later:

- resources/digitone2/PRODUCT_LIKE_EMPTY.syx

Do not decide the final reusable resource path in this phase unless already obvious.

## Proposed product-like events YAML shape
The product-like fixture YAML should be pattern-wide incompatible and explicitly per-track.

Conceptual shape:

```yaml
version: 1
device: digitone2
name: T8 Product Like Cmaj7
pattern:
  mode: per-track
  tempo: 120.0
  change: OFF
  reset: INF
track_scale:
  1:
    length: 16
    speed: 1/8
  2:
    length: 16
    speed: 1/8
  3:
    length: 16
    speed: 1/8
  4:
    length: 16
    speed: 1/8
  5:
    length: 16
    speed: 1/8
  6:
    length: 16
    speed: 1/8
  7:
    length: 16
    speed: 1/8
  8:
    length: 16
    speed: 1/8
  9:
    length: 16
    speed: 1
  10:
    length: 16
    speed: 1
  11:
    length: 16
    speed: 1
  12:
    length: 16
    speed: 1
  13:
    length: 16
    speed: 1
  14:
    length: 16
    speed: 1
  15:
    length: 16
    speed: 1
  16:
    length: 16
    speed: 1
track_defaults:
  velocity:
    1: 70
    2: 70
    3: 70
    4: 50
    5: 70
    6: 50
    7: 100
events:
  - step: 1
    track: 8
    note: C4
    velocity: 70
    time: 0
    length_code: "0x4E"
  - step: 1
    track: 8
    note: E4
    velocity: 70
    time: 0
    length_code: "0x4E"
  - step: 1
    track: 8
    note: G4
    velocity: 70
    time: 0
    length_code: "0x4E"
  - step: 1
    track: 8
    note: B4
    velocity: 50
    time: 0
    length_code: "0x4E"
  - step: 1
    track: 8
    note: D5
    velocity: 70
    time: 0
    length_code: "0x4E"
  - step: 1
    track: 8
    note: A5
    velocity: 50
    time: 0
    length_code: "0x4E"
```

Important:

- Include track_scale for all tracks required by toolkit.
- Toolkit currently validates track_scale entries for exactly tracks 1..16 in per-track mode.
- Product use is primarily tracks 1..8, but schema still requires 1..16 entries today.
- Do not add fake Track 1-7 events just to set defaults.
- Use track_defaults.velocity instead.

## Candidate target values
Use these provisional product-like fixture values unless contradicted by toolkit schema:

tempo: 120.0
pattern.mode: per-track
pattern.change: OFF
pattern.reset: INF
track_scale[1..8].length: 16
track_scale[1..8].speed: 1/8
track_defaults.velocity:
  1: 70
  2: 70
  3: 70
  4: 50
  5: 70
  6: 50
  7: 100
Track 8 chord notes:
  C4 E4 G4 B4 D5 A5
Track 8 chord velocities:
  70 70 70 50 70 50
Track 8 chord length_code:
  0x4E
Track 8 micro timing:
  0

SPEC-OPEN:

- whether track_scale must include 1..16 rather than 1..8 as a permanent product contract
- whether track_scale.length = 16 is the right product-like target for all tracks
- whether speed = 1/8 is the correct product-like target for all product defaults
- whether Track 1-7 LEN template state needs a dedicated product-like template or can be ignored when no Track 1-7 events exist
- whether a reusable product-like template file belongs in Changes or digitone-syx-toolkit

## Static validation strategy
The next implementation phase should be able to test without hardware:

1. Generated YAML loads through toolkit loader.
2. Generated YAML builds SysEx through toolkit.
3. Generated SysEx is non-empty and wrapped by 0xF0 ... 0xF7.
4. Parsed or byte-level checks confirm pattern mode is per-track.
5. Parsed or byte-level checks confirm pattern change is OFF.
6. Parsed or byte-level checks confirm pattern reset is INF.
7. Parsed or byte-level checks confirm track default velocities are written.
8. Parsed or byte-level checks confirm Track 8 Cmaj7 trigger rows remain present.
9. Parsed event checks confirm no Track 1-7 trigger events are emitted unless musically required.

Do not require hardware for these static tests.

## Hardware validation strategy
Hardware validation should confirm:

- pattern is in PER TRACK mode
- LENGTH and SPEED are per-track and have expected values
- CHANGE is OFF
- RESET is INF
- Track 1-7 VEL defaults match the intended profile if visible
- Track 1-7 LEN baseline state is acceptable when no events exist
- Track 8 step 1 still contains the six-note Cmaj7 chord trigger
- Track 8 note velocities match expected values
- Track 8 length behavior is acceptable
- playback still sounds like Cmaj7

## Template strategy decision for now
Use this interim decision:

Next phase should first try product-like events YAML without adding a new template file.

Reason:

Phase 4J found that events YAML can express per-track mode, track_scale length and speed,
change=OFF and reset=INF, and track_defaults.velocity.

If this produces correct static and hardware behavior, no product template is needed for the first product-like fixture.

If Track 1-7 LEN baseline or other static state remains wrong, then add an explicit product-like template file in a later phase.

This avoids prematurely creating or maintaining binary template assets.

## Required next implementation phase
Recommend:

Phase 4L: Generate product-like Track 8 Cmaj7 fixture using per-track events YAML

Phase 4L should:

- generate examples/generated/track8_product_like_validation/
- build product-like events YAML
- generate SysEx through toolkit
- add static tests for per-track mode, track_defaults.velocity, and Track 8 chord events
- optionally add hardware validation manifest
- not modify bundle planner or UI

## Non-goals
This phase does not:

- implement product-like YAML generation
- generate product-like SysEx
- add template resources
- does not modify toolkit
- does not modify Changes runtime code
- modify bundle planner
- modify UI
- validate hardware
- does not implement runtime behavior changes
- does not generate product-like SysEx in this design phase

