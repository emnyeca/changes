# End-to-end Digitone Track 8 SysEx Workflow

## Purpose

This document describes the practical end-to-end workflow:

SongModel YAML -> Track 8 export -> manifest-aware SysEx check -> dry-run -> guarded real-send.

## Safety

Export does not send.

Check does not send.

Dry-run does not send.

Guarded real-send requires explicit confirmation.

`mido` and `python-rtmidi` are only required for `changes send digitone-syx --list-ports` and guarded real-send.

## Workflow

### 1. Export

```powershell
changes export digitone-track8 `
  --input examples/song_models/demo_ii_v_i.changes.yaml `
  --output-dir out/digitone-track8 `
  --basename changes_track8_export `
  --overwrite
```

### 2. Check SysEx file

```powershell
changes check digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --manifest out/digitone-track8/changes_track8_export_manifest.md `
  --expect-source-title "Demo II V I" `
  --expect-chord-events 3 `
  --expect-note-rows 18
```

### 3. List ports

```powershell
changes send digitone-syx --list-ports
```

### 4. Dry-run

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --dry-run
```

### 5. Guarded real-send

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

## Validated fixture

Current validated fixture:

- `examples/song_models/demo_ii_v_i.changes.yaml`
- Dm7 at step1
- G7 at step5
- Cmaj7 at step9
- validated on Digitone II firmware 1.10D

## Additional software fixtures

Additional SongModel fixtures are available for software validation and regression coverage:

- `examples/song_models/demo_multibar_turnaround.changes.yaml`
- `examples/song_models/demo_multisection_form.changes.yaml`

Use the II-V-I fixture for the known hardware-validated path.

Use `demo_multibar_turnaround` for software E2E export/check/dry-run validation.

Use `demo_multisection_form` for export/manifest regression coverage.

See `docs/validation-matrix.md` for exact per-fixture validation scope.

## Requirements

For export/check/dry-run:

- normal development install
- digitone-syx-toolkit if generating `.syx`

These steps do not require `mido`.

For port listing / real-send:

```powershell
python -m pip install -e ".[midi]"
```

This keeps check and dry-run usable in environments without optional MIDI backends.

## Version checks

```powershell
python --version
python -c "import importlib.metadata as md; print('mido', md.version('mido'))"
python -c "import importlib.metadata as md; print('python-rtmidi', md.version('python-rtmidi'))"
```

## Stop conditions

Stop before real-send if:

- SysEx check fails
- Digitone II port is not visible
- port name is ambiguous
- `.syx` is not the expected file
- important Digitone data is not backed up

See docs/manifest-aware-validation.md for manifest-aware check details and warning behavior.

See docs/release-candidate-status.md and docs/validation-status.md for current RC scope and validated fixture status.
