# MIDI Send Transport Boundary

## Purpose

This document defines the safe boundary for future MIDI SysEx sending.

Phase 6A does not send MIDI or operate hardware.

## Current status

Implemented:

- SysEx byte validation
- MIDI output port data model
- MIDI backend protocol and fake backend abstraction
- optional `MidoMidiBackend` prototype with lazy import
- dry-run transport protocol
- dry-run transport implementation
- guarded real-send sender requiring explicit confirmation
- no-hardware-send tests
- dry-run send CLI for validating .syx bytes against a fake output port
- guarded real-send CLI mode with explicit safety flags
- first manual guarded real-send validation passed for the II-V-I fixture

Not implemented:

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

Phase 6E keeps safe defaults and requires explicit mode selection.

`--real-send` requires:

- `--yes-i-understand-this-writes-to-hardware`
- `--port`
- `--syx`

Preferred future CLI shape:

```bash
changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II" \
  --dry-run
```

Avoid implicit send during:

```bash
changes export ...
```

unless a future explicit `--send` design is separately reviewed.

## Dry-run transport

Phase 6A provides `DryRunSysexTransport`.

Phase 6B adds a dry-run send CLI that reads `.syx` bytes from disk and routes them through the fake transport.

It validates:

- SysEx byte envelope
- selected output port

It returns a result but does not send hardware.

`BackendSysexTransport` remains dry-run-only and still raises `HardwareSendNotImplementedError` for `dry_run=False`.

Real send is routed through a separate guarded sender requiring explicit confirmation.

## Future real transport

A future phase may add a real transport implementation using a MIDI backend.

Candidate backends:

- mido
- python-rtmidi

Phase 6E keeps optional backend prototype support for `mido` under explicit dependency guard.

Backend dependencies remain optional; normal install/test paths do not require them.

`mido` with `python-rtmidi` remains the preferred candidate unless Windows install or SysEx behavior proves unreliable.

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

Generated `.syx` artifacts may be kept temporarily for validation reproducibility.

See docs/midi-hardware-validation-checklist.md for future manual validation flow once a reviewed real-send mode exists.

Use docs/hardware-validation/digitone-syx-real-send-template.md to record manual hardware validation results.

See docs/real-send-workflow.md for the stabilized user-facing real-send workflow.

See docs/cli.md for the consolidated CLI reference and docs/generated-artifacts-policy.md for retained validation artifacts.

See docs/manifest-aware-validation.md for optional pre-send `.syx` to manifest consistency checks.

## Recommended next phase

Recommend:

Phase 6C: real MIDI backend selection after dry-run CLI review

or, if preferred:

Phase 5H: broader export coverage before real transport

Recommendation:

Proceed to Phase 6B only if current export coverage is sufficient.
Otherwise add one more export coverage phase first.
