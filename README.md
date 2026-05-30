# EUB Changes

![EUB Changes logo](docs/assets/1x/eub_changes_logo.png)

EUB Changes is an experimental toolkit for converting musical progression data into MIDI and Digitone-oriented artifacts.

The repository name is `changes`, but the software name is intentionally branded as **EUB Changes**.

![EUB Changes UI concept](docs/assets/1x/GUI_Concept.png)

## Current release-candidate workflow

The current practical workflow focuses on Digitone II Track 8 SysEx export and guarded sending:

```text
SongModel YAML
	-> Track 8 export
	-> SysEx check
	-> manifest-aware validation
	-> dry-run send
	-> guarded real-send
```

## Quick start: Digitone II Track 8

### 1. Export Track 8 artifacts

```powershell
changes export digitone-track8 `
	--input examples/song_models/demo_ii_v_i.changes.yaml `
	--output-dir out/digitone-track8 `
	--basename changes_track8_export `
	--overwrite
```

### 2. Check SysEx and manifest

```powershell
changes check digitone-syx `
	--syx out/digitone-track8/changes_track8_export.syx `
	--manifest out/digitone-track8/changes_track8_export_manifest.md `
	--expect-source-title "Demo II V I" `
	--expect-chord-events 3 `
	--expect-note-rows 18
```

### 3. Dry-run send

```powershell
changes send digitone-syx `
	--syx out/digitone-track8/changes_track8_export.syx `
	--port "Elektron Digitone II 2" `
	--dry-run
```

### 4. Guarded real-send

Install MIDI extras first:

```powershell
python -m pip install -e ".[midi]"
```

List ports:

```powershell
changes send digitone-syx --list-ports
```

Send only after backup and explicit confirmation:

```powershell
changes send digitone-syx `
	--syx out/digitone-track8/changes_track8_export.syx `
	--port "Elektron Digitone II 2" `
	--real-send `
	--yes-i-understand-this-writes-to-hardware
```

## Safety

- Export never sends MIDI.
- Check never sends MIDI.
- Dry-run never writes hardware.
- Real-send requires explicit confirmation.
- No MIDI port is auto-selected.
- `mido` and `python-rtmidi` are optional dependencies.

## Validation status

The II-V-I fixture has been manually validated on Digitone II.

See:

- docs/validation-status.md
- docs/hardware-validation/digitone-syx-real-send-first-validation.md

## Known limitations

See docs/known-limitations.md.

## Documentation index

See docs/index.md for release-candidate status, workflow docs, and safety references.
