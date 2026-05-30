# Changes CLI Reference

## Modern commands

### Export Digitone Track 8 artifacts

```powershell
changes export digitone-track8 `
  --input examples/song_models/demo_ii_v_i.changes.yaml `
  --output-dir out/digitone-track8 `
  --basename changes_track8_export `
  --overwrite
```

Notes:

- exports Digitone II Track 8 artifacts
- does not send MIDI
- writes `.events.yaml`, `.syx`, and manifest unless `--events-yaml-only`
- `--input` expects SongModel YAML v1
- `--events-yaml-only` skips SysEx generation
- `--overwrite` overwrites existing artifacts

### Send Digitone SysEx

List ports:

```powershell
changes send digitone-syx --list-ports
```

Dry-run:

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --dry-run
```

Guarded real-send:

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

Notes:

- `--list-ports` lists output ports and does not send
- `--dry-run` validates without hardware write
- `--real-send` writes to hardware
- `--yes-i-understand-this-writes-to-hardware` is required for real-send
- `pip install .[midi]` is required for port listing and real-send

### Check Digitone SysEx file

```powershell
changes check digitone-syx --syx out/digitone-track8/changes_track8_export.syx
```

Manifest-aware example:

```powershell
changes check digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --manifest out/digitone-track8/changes_track8_export_manifest.md `
  --expect-source-title "Demo II V I" `
  --expect-chord-events 3 `
  --expect-note-rows 18
```

Notes:

- validates file envelope only
- optionally validates `.syx` byte count and expected values against Track 8 manifest
- manifest-aware flags: `--manifest`, `--expect-source-title`, `--expect-chord-events`, `--expect-note-rows`
- does not require `mido`
- does not send

For broader software fixture coverage, run the same export/check/dry-run flow with:

- `examples/song_models/demo_multibar_turnaround.changes.yaml`
- `examples/song_models/demo_multisection_form.changes.yaml`

## Legacy commands

Generic MIDI export:

```powershell
changes input.yaml --backend generic-midi --output out.mid
```

Digitone compile artifacts:

```powershell
changes input.yaml --backend digitone-compile --artifact-dir out_digitone
```

Digitone bundle artifacts from YAML:

```powershell
changes input.yaml --backend digitone-bundle --artifact-dir out_bundle --write-syx
```

MusicXML to Digitone bundle artifacts:

```powershell
changes digitone-bundle --musicxml input.musicxml --output out --write-syx
```

## Safety

- export never sends
- check never sends
- real-send is explicit
- no auto port selection
- optional MIDI dependencies remain optional
