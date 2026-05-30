# Track 8 Product-like Cmaj7 Fixture

## Files

- track8_product_like_cmaj7.events.yaml
- track8_product_like_cmaj7.syx

## Purpose

This fixture validates product-like per-track pattern settings together with the Track 8 Cmaj7 same-step chord trigger.

## Expected product-like pattern settings

- Pattern mode: per-track
- Tempo: 120.0
- CHANGE: OFF
- RESET: INF
- Tracks 1-8 LENGTH: 16
- Tracks 1-8 SPEED: 1/8
- Tracks 9-16 LENGTH: 16
- Tracks 9-16 SPEED: 1
- Track default velocities:
  - Track 1: 70
  - Track 2: 70
  - Track 3: 70
  - Track 4: 50
  - Track 5: 70
  - Track 6: 50
  - Track 7: 100

## Expected Track 8 chord content

- Track: 8
- Step: 1
- Notes: C4 E4 G4 B4 D5 A5
- Velocities: 70 70 70 50 70 50
- Length code: 0x4E
- Micro timing: 0
- SysEx size bytes: 114118

## Static validation notes

- events.yaml must parse with toolkit per-track schema.
- track_scale must include tracks 1..16.
- track_defaults.velocity must be written for tracks 1..7.
- Events should include Track 8 rows only for this fixture.

## Hardware validation steps

1. Open Elektron Transfer.
2. Send track8_product_like_cmaj7.syx to Digitone II.
3. Load the generated pattern.
4. Confirm pattern mode is PER TRACK.
5. Confirm LENGTH and SPEED settings if visible.
6. Confirm CHANGE is OFF and RESET is INF.
7. Confirm Track 1-7 default velocities if visible.
8. Inspect Track 8 step 1.
9. Confirm the six same-step notes are present.
10. Play the pattern and confirm it sounds like a Cmaj7 voicing.

## Caveats

- This fixture does not validate complete song export.
- This fixture does not validate bundle planner integration.
- This fixture does not validate UI workflow.
- This fixture does not emit Track 1-7 musical trigger events.
- Track 1-7 LEN baseline behavior should be confirmed on hardware.

## Notes

Changes does not send MIDI or operate hardware during fixture generation.
