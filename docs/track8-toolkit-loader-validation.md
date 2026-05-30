# Track 8 Toolkit Loader Validation (Phase 4E)

## Purpose

This phase validates that Changes-generated Track 8 events YAML is accepted by
the real digitone-syx-toolkit YAML loader implementation.

## Scope Boundary

This phase includes only YAML-loader validation.

It does not include:

- SysEx generation
- toolkit SysEx encoder calls
- hardware operation
- bundle planning changes
- UI changes
- hard runtime dependency on digitone-syx-toolkit

## Validated Path

SongModel
  -> RenderedArrangement
  -> Track8ChordEvent
  -> Changes Track 8 payload
  -> toolkit rows
  -> finalized length rows
  -> toolkit events YAML
  -> digitone-syx-toolkit load_event_assignment_yaml()

## Validation Helper

Phase 4E adds a helper that lazily imports toolkit only when called:

- validate_track8_events_yaml_with_toolkit_loader(yaml_text)

Behavior:

- attempts to import digitone_syx_toolkit.events_yaml.load_event_assignment_yaml
- writes YAML text to a temporary .events.yaml file
- calls toolkit loader against that file
- returns parsed EventAssignment object

If toolkit import fails, a clear RuntimeError is raised describing local setup.

## Local Setup

From D:\emnye\Documents\GitHub\changes:

python -m pip install -e .
python -m pip install -e ..\digitone-syx-toolkit
python -m pytest tests/test_track8_toolkit_loader_validation.py -q

Alternative using py launcher:

py -m pip install -e .
py -m pip install -e ..\digitone-syx-toolkit
py -m pytest tests/test_track8_toolkit_loader_validation.py -q

## Expected Cmaj7 Contract

The integration test validates this loaded contract:

- 6 events
- step = 1 for all events
- track = 8 for all events
- notes = C4 E4 G4 B4 D5 A5
- velocities = 70 70 70 50 70 50
- length_code = 0x4E for all events
- time = 0 for all events

## CI Policy

Toolkit-dependent tests are optional and skipped automatically when toolkit is
not installed.

No GitHub Actions workflow change is included in this phase.

## Next Phase

Recommended next step:

- Phase 4F: explicit SysEx generation through digitone-syx-toolkit behind a deliberate export function

Alternative first:

- Phase 4F: fixture artifact generation for hardware validation
