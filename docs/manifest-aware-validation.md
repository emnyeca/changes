# Manifest-aware SysEx Validation

## Purpose

`changes check digitone-syx` can validate a `.syx` file envelope and optionally compare it with a generated Track 8 manifest.

This helps catch:

- wrong `.syx` file
- stale `.syx` file
- mismatched export artifacts
- incorrect source title/count assumptions

## Basic envelope check

```powershell
changes check digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx
```

## Manifest-aware check

```powershell
changes check digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --manifest out/digitone-track8/changes_track8_export_manifest.md `
  --expect-source-title "Demo II V I" `
  --expect-chord-events 3 `
  --expect-note-rows 18
```

## What is validated

- SysEx starts with `0xF0`
- SysEx ends with `0xF7`
- byte size matches manifest if manifest includes SysEx size
- source title matches expected value if available
- Track 8 chord event count matches expected value if available
- Track 8 note row count matches expected value if available

## What is not validated

- full Digitone payload semantics
- target pattern slot
- device identity
- actual hardware import
- all note/parameter mappings

## Safety

Check does not send MIDI.

Check does not require `mido`.

Real-send remains a separate explicit command.
