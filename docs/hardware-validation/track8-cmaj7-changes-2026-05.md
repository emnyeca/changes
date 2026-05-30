# Track 8 Cmaj7 Changes Hardware Validation - 2026-05

## Summary

The Track 8 Cmaj7 hardware-validation fixture was tested on Digitone II.

Result: PASS for the scoped Track 8 chord-trigger validation.

## Fixture files

- examples/generated/track8_hardware_validation/track8_cmaj7_changes.events.yaml
- examples/generated/track8_hardware_validation/track8_cmaj7_changes.syx
- examples/generated/track8_hardware_validation/track8_cmaj7_changes_manifest.md

## Validated contract

The following behavior matched the fixture manifest:

- Track: 8
- Step: 1
- Same-step chord trigger: yes
- Notes: C4 E4 G4 B4 D5 A5
- Velocities: 70 70 70 50 70 50
- Length code: 0x4E
- Micro timing: 0
- Musical result: Cmaj7 voicing was triggered as expected

## Scope of this validation

This validation only covers the isolated Track 8 chord-trigger fixture.

It does not validate:

- complete song export
- bundle planner integration
- normal CLI export workflow
- UI workflow
- Track 1-7 defaults
- product-like pattern settings
- all chord qualities
- all keys
- all durations
- hardware transfer automation

## Known caveats observed

During hardware inspection, the following broader pattern-setting caveats were observed:

- LENGTH was not in PER TRACK mode.
- SPEED was not in PER TRACK mode.
- CHANGE was not in PER TRACK mode.
- RESET was not in PER TRACK mode.
- Track 1-7 LEN / VEL defaults did not match the intended default output spec.

These are acceptable for the Phase 4G fixture because the fixture's purpose was to validate Track 8 same-step chord-trigger behavior only.

They must be addressed before product-like export is considered complete.

## Decision

Track 8 chord-trigger generation is validated enough to proceed to product-like pattern settings work.

## Follow-up

Proceed with a separate phase for:

- PER TRACK mode for LENGTH / SPEED / CHANGE / RESET
- Track 1-7 default LEN / VEL policy
- template/default pattern behavior
- fixture generation that reflects product-like export assumptions
