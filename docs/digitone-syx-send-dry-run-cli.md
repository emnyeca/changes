# Digitone SysEx Send Dry-run CLI

## Purpose

This document describes the Phase 6B dry-run-only send command.

## Command

```bash
changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II" \
  --dry-run
```

## Current behavior

The command:

- reads a `.syx` file
- validates the SysEx envelope
- validates the requested port name against a dry-run fake transport
- prints a dry-run result

The command does not:

- open MIDI ports
- discover MIDI ports
- send hardware
- require mido
- require python-rtmidi
- modify export behavior

Phase 6D adds an optional `MidoMidiBackend` prototype in the transport module, but this command still uses dry-run-only behavior and does not switch to real send.

## Why --dry-run is required

Phase 6B intentionally prevents accidental hardware writes.

Real send will be added only after backend selection, fake-backend tests, and manual hardware validation checklist are reviewed.

## Backend selection

Future real backend recommendation:

Prefer `mido` with `python-rtmidi` backend first, unless Windows install or SysEx behavior proves unreliable.

Phase 6B does not add these dependencies.

Phase 6D keeps these dependencies optional and behind lazy import.

For backend experiments only:

```bash
pip install .[midi]
```

## Relationship to Track 8 export

Export and send remain separate.

Typical future workflow:

```bash
changes export digitone-track8 \
  --input examples/song_models/demo_ii_v_i.changes.yaml \
  --output-dir out/digitone-track8 \
  --overwrite

changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II" \
  --dry-run
```

## Not implemented

- real MIDI send
- port discovery
- device identity check
- transfer progress
- retry
- hardware validation
- real-send CLI mode
