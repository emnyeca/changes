# Per-Track Scale Output Hardware Validation (2026-05-29)

## Scope

Validate that regenerated Digitone II Native SysEx artifacts from `changes` now import as per-track scale mode rather than pattern-wide mode.

## Regenerated artifacts

- `examples/generated/musicxml_hardware_validation/500_miles_high_direct/500_MILES_HIGH.bundle.syx`
- `examples/generated/musicxml_hardware_validation/500_miles_high_converted/500_MILES_HIGH.bundle.syx`
- `examples/generated/hardware_validation_harmony/minor_ii_v_e7sharp9/MINOR_II_V_E7_9.bundle.syx`

## Expected on-device state

- Imported pattern shows `Per Track` mode.
- Track 1..8 LENGTH match the exported segment `total_steps`.
- Track 1..8 SPEED match the exported segment `speed`.
- Track 9..16 LENGTH are fixed to `16`.
- Track 9..16 SPEED are fixed to `1`.
- CHANGE shows `OFF`.
- RESET shows `INF`.
- Existing trigger timing and note content remain unchanged relative to the pre-per-track export.

## Current exported values

- `500_miles_high_direct`: Tracks 1..8 = LENGTH `22`, SPEED `1/8`; Tracks 9..16 = LENGTH `16`, SPEED `1`
- `500_miles_high_converted`: Tracks 1..8 = LENGTH `22`, SPEED `1/8`; Tracks 9..16 = LENGTH `16`, SPEED `1`
- `minor_ii_v_e7sharp9`: Tracks 1..8 = LENGTH `3`, SPEED `1/8`; Tracks 9..16 = LENGTH `16`, SPEED `1`

## Status

- Artifact regeneration: complete
- Automated validation: complete
- On-device confirmation: pending