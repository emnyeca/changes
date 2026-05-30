# Track 8 Product-like Cmaj7 Hardware Validation - 2026-05

## Summary

The product-like Track 8 Cmaj7 fixture was tested on Digitone II.

Result: PASS for the scoped product-like Track 8 Cmaj7 fixture.

## Fixture files

- examples/generated/track8_product_like_validation/track8_product_like_cmaj7.events.yaml
- examples/generated/track8_product_like_validation/track8_product_like_cmaj7.syx
- examples/generated/track8_product_like_validation/track8_product_like_cmaj7_manifest.md

## Validated product-like pattern settings

The following settings matched expectations on hardware:

- Transfer/import: OK
- Pattern mode: PER TRACK
- CHANGE: OFF
- RESET: INF
- Track 1-8 LENGTH: 16
- Track 1-8 SPEED: 1/8
- Track 9-16 LENGTH: 16
- Track 9-16 SPEED: 1
- Track 1-7 default velocities: OK

## Validated Track 8 chord content

Track 8 Step 1 matched the expected same-step six-note Cmaj7 chord trigger:

- Track: 8
- Step: 1
- Same-step note records: OK
- Notes: C4 E4 G4 B4 D5 A5
- Velocities: 70 70 70 50 70 50
- Micro timing: 0
- Playback result: Cmaj7 voicing sounded as expected

## Length behavior

The fixture encoded Track 8 note lengths as:

- length_code: 0x4E

On hardware, the length display showed:

- 16

This is considered PASS for this fixture.

Reason:

- the intended musical duration is 16 sixteenth-note units
- Phase 4D maps this duration to Digitone explicit length code 0x4E
- the hardware display of 16 is consistent with the intended musical duration

This validation does not claim that the hardware UI displays the internal hex code 0x4E.

## Scope of this validation

This validation covers:

- product-like per-track pattern settings in this fixture
- Track 1-7 default velocities
- Track 8 Cmaj7 same-step chord trigger
- Track 8 note identity
- Track 8 event velocities
- Track 8 length display consistency
- playback confirmation

It does not validate:

- complete song export
- bundle planner integration
- normal CLI export workflow
- UI workflow
- all chord qualities
- all keys
- all durations
- Track 1-7 musical event behavior
- hardware transfer automation
- user-supplied template workflows

## Decision

The product-like Track 8 Cmaj7 fixture is validated enough to proceed toward explicit export workflow design.

## Follow-up

Recommended next phase:

- Phase 5A: explicit CLI or export command design for Track 8 chord SysEx export

Before broad productization, future validation should still cover:

- multiple chord qualities
- multiple keys
- multiple durations
- non-step-1 events
- multi-measure progression export
- Track 1-7 musical events if they become part of the export path
