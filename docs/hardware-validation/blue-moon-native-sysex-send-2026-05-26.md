# Hardware Validation Log: Blue Moon Native SysEx Send

- Date: 2026-05-26
- Device: Elektron Digitone II

## Input

- Source progression: examples/blue_moon.progression.yaml
- Tempo: 124 BPM
- Time Signature: 4/4

## Compile Output

- Digitone Device Tempo: 248.0
- Speed: 1/8
- Total Steps: 16
- Event Count: 53
- Tracks Used: 1-7

## Generated Artifacts

- examples/generated/blue_moon/song_model.json
- examples/generated/blue_moon/rendered_timeline.json
- examples/generated/blue_moon/digitone_compile_plan.json
- examples/generated/blue_moon/digitone.events.yaml
- examples/generated/blue_moon/digitone_pattern.syx

## Toolkit Validation

- validate_events/load_event_assignment_yaml: passed
- Parsed summary:
  - version: 1
  - device: digitone2
  - pattern.tempo: 248.0
  - pattern.speed: 1/8
  - pattern.total_steps: 16

## Replay Send Execution

- Command: digitone_syx_toolkit replay --out-port 3 --file ../changes/examples/generated/blue_moon/digitone_pattern.syx
- Result: sent=1 message, replay finished without error

## Hardware Verification

- [x] Pattern import is visible on device
- [x] Chord-cloud transitions match intended harmony movement
- [x] Bass movement and octave mapping are musically correct
- [x] Timing aligns with external tempo context
- [x] No audible blocking issue from finite length codes

## Status

Blue Moon native SysEx pipeline hardware validation succeeded.
