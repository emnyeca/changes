# Track 8 Hardware Validation Fixtures (Phase 4G)

## Purpose

This phase generates concrete fixture artifacts for Digitone II Track 8 hardware validation.

## Scope Boundary

This phase is fixture generation only.

It does not perform:

- MIDI send
- hardware operation
- normal export integration
- bundle planner integration
- UI integration

## Generated Files

- examples/generated/track8_hardware_validation/track8_cmaj7_changes.events.yaml
- examples/generated/track8_hardware_validation/track8_cmaj7_changes.syx
- examples/generated/track8_hardware_validation/track8_cmaj7_changes_manifest.md

## How to Regenerate

From local changes repository:

python -m pip install -e .
python -m pip install -e ..\\digitone-syx-toolkit
python -c "from changes.digitone.track8_fixture_generation import write_track8_cmaj7_hardware_validation_fixture; write_track8_cmaj7_hardware_validation_fixture('examples/generated/track8_hardware_validation', overwrite=True)"

Alternative with py launcher:

py -m pip install -e .
py -m pip install -e ..\\digitone-syx-toolkit
py -c "from changes.digitone.track8_fixture_generation import write_track8_cmaj7_hardware_validation_fixture; write_track8_cmaj7_hardware_validation_fixture('examples/generated/track8_hardware_validation', overwrite=True)"

## Hardware Validation Procedure

1. Open Elektron Transfer.
2. Send the .syx file to Digitone II.
3. Load or inspect the generated pattern.
4. Check Track 8 step 1.
5. Confirm six same-step notes: C4, E4, G4, B4, D5, A5.
6. Confirm velocities: 70, 70, 70, 50, 70, 50.
7. Confirm length behavior if visible.
8. Play the pattern and confirm it sounds like a Cmaj7 voicing.

## Expected Caveats

- This validates a single Cmaj7 same-step chord fixture.
- It does not validate all chord qualities.
- It does not validate complete song export.
- It does not validate bundle planner integration.
- It does not validate hardware transfer success automatically.
- It does not validate final UI workflow.

## Next Phase

Recommended next step:

- Phase 4H: hardware validation result logging and follow-up fixes

Alternative after hardware confirmation:

- Phase 5A: explicit CLI command for Track 8 chord SysEx export
