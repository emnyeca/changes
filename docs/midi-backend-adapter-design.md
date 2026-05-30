# MIDI Backend Adapter Design

## Purpose

This document defines the backend abstraction for future real MIDI SysEx sending.

Phase 6E adds guarded real-send CLI integration but keeps explicit confirmation and optional dependencies.

The first manual validation passed for the guarded II-V-I real-send workflow on Digitone II.

## Layers

### Export layer

Produces `.syx` bytes.

Does not send MIDI.

### Transport layer

Validates SysEx bytes and application-level send policy.

Owns dry-run behavior and send safety.

### Backend layer

Lists ports and sends bytes to a MIDI implementation.

Phase 6D provides fake backend and optional mido backend prototype.

## Interfaces

- `MidiBackend`
- `FakeMidiBackend`
- `MidoMidiBackend`
- `BackendSysexTransport`
- `DryRunSysexTransport`
- `GuardedSysexSender`

## Real backend candidates

### mido + python-rtmidi

Pros:

- practical high-level API
- common Python MIDI abstraction
- suitable candidate for port listing and SysEx sending

Cons:

- native/backend dependency
- platform-specific installation behavior
- Windows port naming may need real testing
- SysEx behavior must be verified with Digitone II

### direct python-rtmidi

Pros:

- closer to backend
- fewer abstraction layers

Cons:

- more backend-specific code
- less ergonomic
- harder to swap later

## Recommendation

Prefer `mido` with `python-rtmidi` backend first, unless Windows installation or SysEx sending proves unreliable.

Do not make either dependency mandatory for normal install or normal tests.

Use `importlib.metadata` for version checks:

```powershell
python -c "import importlib.metadata as md; print('mido', md.version('mido'))"
python -c "import importlib.metadata as md; print('python-rtmidi', md.version('python-rtmidi'))"
```

## Optional dependency policy

Phase 6D keeps `mido` optional behind lazy import in `MidoMidiBackend`.

Recommended install path for MIDI backend experiments:

```bash
pip install .[midi]
```

## Safety policy

Real sending must remain disabled at application/CLI level until:

- backend dependency choice is explicitly accepted
- fake backend tests exist
- real backend tests are isolated
- CLI requires explicit confirmation flow
- manual hardware validation checklist exists
- user confirms testing on real Digitone II

Phase 6E guarded send requires explicit confirmation flag and does not run implicitly from export.

For user-facing CLI usage, see docs/cli.md and docs/real-send-workflow.md.

## Future real backend shape

A future phase may keep this backend class and expose a reviewed application-level real-send switch:

```python
class MidoMidiBackend:
    ...
```

Expected responsibilities:

- import `mido` lazily
- list output ports
- open selected output port
- send SysEx bytes
- close port safely
- convert backend errors to `MidiTransportError`

## Non-goals

Phase 6E does not:

- make `mido` mandatory
- make `python-rtmidi` mandatory
- remove `--dry-run`
- add export `--send`
- discover ports automatically in user CLI
- perform hardware validation automatically
