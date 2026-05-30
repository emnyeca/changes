# Track 8 Cmaj7 Hardware Validation Fixture

## Files

- track8_cmaj7_changes.events.yaml
- track8_cmaj7_changes.syx

## Purpose

This fixture verifies that Changes can generate a Digitone II Track 8 same-step six-note chord trigger through digitone-syx-toolkit.

## Expected musical content

- Pattern name: T8 Cmaj7 Changes
- Tempo: 120.0
- Track: 8
- Step: 1
- Notes: C4 E4 G4 B4 D5 A5
- Velocities: 70 70 70 50 70 50
- Length code: 0x4E
- Micro timing: 0
- SysEx size bytes: 114118

## Hardware validation steps

1. Open Elektron Transfer.
2. Send track8_cmaj7_changes.syx to Digitone II.
3. Load the generated pattern.
4. Inspect Track 8 step 1.
5. Confirm that the six note records are present on the same step.
6. Confirm note order and velocities if the UI exposes them.
7. Play the pattern and confirm a Cmaj7 voicing is triggered.

## Notes

This fixture is for validation only.
It does not prove final export workflow integration.
No MIDI or hardware send is performed by Changes during fixture generation.
