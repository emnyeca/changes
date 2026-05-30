# Digitone SysEx Send Dry-run CLI

## Purpose

This document describes the Phase 6B dry-run-only send command.

Phase 6E keeps this dry-run path valid while adding a separate guarded real-send mode.

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

Phase 6E adds guarded real-send and port listing in the same CLI command family, but this dry-run mode remains available and safe by default.

The first manual real-send validation passed for the II-V-I fixture while keeping dry-run as the recommended first step.

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

For guarded real-send behavior, see docs/digitone-syx-real-send-guarded-cli.md.

For the practical end-to-end workflow, see docs/real-send-workflow.md.
