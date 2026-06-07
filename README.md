# EUB Changes (EUB-SW01)

![EUB Changes logo](docs/assets/1x/eub_changes_logo.png)

EUB Changes is a machine-live harmony conversion toolkit.

Its intended user experience is to turn iReal Pro / MusicXML song data into Digitone II performance material quickly.

The repository name is `changes`, but the software name is intentionally branded as **EUB Changes**.

EUB Changes generates multiple performance layers for Digitone II:

- Cloud: moving six-voice texture
- Bass: low-register grounding layer
- Chord: symbol-faithful vertical layer

These layers can be used independently or together depending on the performance workflow.

![EUB Changes UI1](docs/assets/1x/EUB-Changes_Screenshot1.png)
![EUB Changes UI2](docs/assets/1x/EUB-Changes_Screenshot2.png)

## UI

Start the initial release Streamlit UI:

```powershell
python -m pip install -e ".[ui]"
python -m streamlit run src/changes/main_ui.py
```

If `streamlit` is not recognized in PowerShell, use:

```powershell
d:/emnye/Documents/GitHub/changes/.venv/Scripts/python.exe -m streamlit run src/changes/main_ui.py
```

## Product architecture

EUB Changes targets a Digitone II machine-live workflow:

| Digitone II Track | Layer | Role | Current status |
| --- | --- | --- | --- |
| Track 1-6 | Harmony Cloud | six-voice playable harmony texture | architecture target / partial implementation |
| Track 7 | Bass | root movement / slash-bass grounding layer | architecture target / partial implementation |
| Track 8 | Chord | symbol-faithful vertical layer | current RC-stabilized workflow |

The intended end-to-end flow is:

```text
iReal Pro
	-> MusicXML export
	-> EUB Changes conversion
	-> machine-live-friendly note data
	-> Digitone II
```

The current Chord workflow (Digitone Track 8) remains important, but it is a stabilized subset rather than the full product architecture.

See `docs/product-architecture.md` for the target layer model and `docs/current-state.md` for the distinction between product direction, current implementation, and current validation.

## Current RC-stabilized subset

The current practical workflow focuses on Chord SysEx export to Digitone II Track 8 and guarded sending.

This is the currently stabilized subset, not the full product architecture:

```text
SongModel YAML
	-> Chord export (Digitone Track 8)
	-> SysEx check
	-> manifest-aware validation
	-> dry-run send
	-> guarded real-send
```

## Quick start: Chord workflow on Digitone II Track 8

### 1. Export Chord artifacts (Digitone Track 8)

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

The II-V-I fixture has been manually validated on Digitone II for the Chord RC workflow (Track 8).

Additional SongModel fixtures are available under `examples/song_models/` for software validation.
The hardware-validated fixture remains `examples/song_models/demo_ii_v_i.changes.yaml`.

Validation scope references:

- `docs/validation-matrix.md`
- `docs/current-state.md`

See:

- docs/hardware-validation/digitone-syx-real-send-first-validation.md
- docs/product-architecture.md
- docs/current-state.md

## Known limitations

See docs/known-limitations.md.

## Documentation index

See docs/index.md for product architecture, current state, workflow docs, and safety references.

## License

EUB Changes is released under the MIT License.
See [LICENSE](./LICENSE) for details.
