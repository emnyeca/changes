# EUB Changes

![EUB Changes logo](docs/assets/1x/eub_changes_logo.png)

EUB Changes is a machine-live harmony conversion toolkit.

Its intended user experience is to turn iReal Pro / MusicXML song data into Digitone II performance material quickly.

The repository name is `changes`, but the software name is intentionally branded as **EUB Changes**.

The core musical priority is:

- Cloud > Bass > Chord
- Track 1-6 > Track 7 > Track 8

![EUB Changes UI concept](docs/assets/1x/GUI_Concept.png)

## Product architecture

EUB Changes targets a Digitone II machine-live workflow:

| Digitone II Track | Role | Priority | Status |
| --- | --- | --- | --- |
| Track 1-6 | Harmony Cloud voices 1-6 | Primary | architecture target / partial implementation |
| Track 7 | Bass | Secondary | architecture target / partial implementation |
| Track 8 | Chord reference/helper | Additional | current RC-stabilized workflow |

The intended end-to-end flow is:

```text
iReal Pro
	-> MusicXML export
	-> EUB Changes conversion
	-> machine-live-friendly note data
	-> Digitone II
```

The current Track 8 workflow remains important, but it is a stabilized subset rather than the full product architecture.

See `docs/product-architecture.md` for the target layer model and `docs/current-state.md` for the distinction between product direction, current implementation, and current validation.

## Current RC-stabilized subset

The current practical workflow focuses on Digitone II Track 8 SysEx export and guarded sending.

This is the currently stabilized subset, not the full product priority order:

```text
SongModel YAML
	-> Track 8 export
	-> SysEx check
	-> manifest-aware validation
	-> dry-run send
	-> guarded real-send
```

## Quick start: Digitone II Track 8 chord workflow

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

The II-V-I fixture has been manually validated on Digitone II for the Track 8 RC workflow.

Additional SongModel fixtures are available under `examples/song_models/` for software validation.
The hardware-validated fixture remains `examples/song_models/demo_ii_v_i.changes.yaml`.

Validation scope references:

- `docs/validation-matrix.md`
- `docs/fixture-inventory.md`

See:

- docs/validation-status.md
- docs/hardware-validation/digitone-syx-real-send-first-validation.md
- docs/product-architecture.md
- docs/current-state.md

## Known limitations

See docs/known-limitations.md.

## Documentation index

See docs/index.md for product architecture, current state, release-candidate status, workflow docs, and safety references.
