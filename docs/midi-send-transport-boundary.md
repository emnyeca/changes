# MIDI Send Transport Boundary

## Purpose

This document defines the safe boundary for future MIDI SysEx sending.

Phase 6A does not send MIDI or operate hardware.

## Current status

Implemented:

- SysEx byte validation
- MIDI output port data model
- dry-run transport protocol
- dry-run transport implementation
- no-hardware-send tests

Not implemented:

- real MIDI backend
- MIDI port discovery
- hardware send
- CLI send command
- export `--send`
- retry logic
- device identity confirmation
- transfer progress feedback

## Dependency boundary

The transport layer consumes already-generated SysEx bytes.

It must not:

- generate SysEx
- import digitone-syx-toolkit
- import SongModel
- import Track 8 export API
- know about Track 8
- know about product-like profile

Expected future flow:

```text
SongModel YAML
  -> Track 8 export
  -> .syx bytes
  -> transport layer
  -> MIDI backend
  -> Digitone II
```

## Safety policy

Sending must remain explicit.

Do not send from export by default.

Preferred future CLI shape:

```bash
changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II"
```

Avoid implicit send during:

```bash
changes export ...
```

unless a future explicit `--send` design is separately reviewed.

## Dry-run transport

Phase 6A provides `DryRunSysexTransport`.

It validates:

- SysEx byte envelope
- selected output port

It returns a result but does not send hardware.

If `dry_run=False`, it raises `HardwareSendNotImplementedError`.

## Future real transport

A future phase may add a real transport implementation using a MIDI backend.

Candidate backends:

- mido
- python-rtmidi

Backend choice is not made in Phase 6A.

Future implementation must include:

- explicit dependency decision
- port listing
- send confirmation
- no-send dry-run mode
- tests with fake backend
- manual hardware validation checklist

## Relationship to Track 8 export

Track 8 export remains artifact-only.

The current Track 8 CLI does not send MIDI.

Transport support will consume `.syx` files or bytes after export.

## Recommended next phase

Recommend:

Phase 6B: MIDI backend selection and fake-backend send command design

or, if preferred:

Phase 5H: broader export coverage before real transport

Recommendation:

Proceed to Phase 6B only if current export coverage is sufficient.
Otherwise add one more export coverage phase first.
