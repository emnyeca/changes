# Digitone Native SysEx Backend (Design Memo)

## Intent

- Digitone output in EUB Changes should use Native SysEx as the primary backend.
- Legacy high-speed realtime MIDI recording workflow is not part of normal product flow.
- Generic MIDI backend remains supported for DAW/soft synth/other hardware verification.

## Confirmed Direction

- Native SysEx uses digitone-syx-toolkit as a dependency.
- Dependency direction is one-way:
  - EUB Changes -> digitone-syx-toolkit
- Base Pattern speed policy for Native SysEx: `speed: "1/8"`.

## Tempo Terms

- `performance_tempo`:
  - Musical tempo recognized by performer / external environment.
- `digitone_device_tempo`:
  - Tempo configured on Digitone II so SPEED=`1/8` pattern reproduces intended timing.

Confirmed formula:

- `digitone_device_tempo = 2 * performance_tempo / q_step`

Where `q_step` is the quarter-note duration represented by one Digitone step.

Validation in current scope:

- `30.0 <= digitone_device_tempo <= 300.0`

## Current Implementation Scope

- Song Model -> Rendered Timeline -> Digitone Compile Plan pipeline is implemented.
- Compact progression importer is implemented.
- Render Profile / Digitone Target Profile defaults are implemented.
- Compile plan to toolkit-compatible `.events.yaml` exporter is implemented.
- Optional `.syx` generation via toolkit wrapper is implemented.
- Streamlit and CLI expose pipeline artifact export.
- Generic MIDI file export and Generic realtime MIDI send remain available.

## Open Questions (Not Implemented Here)

- Multi-pattern partition strategy (section-level split vs single-pattern packing).
- Approximation policy when exact length code mapping fails.
- Profile customization UX (current implementation uses defaults).
- Meter changes in one song and cross-pattern continuity behavior.
