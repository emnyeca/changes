# Track 8 Export Artifacts

## Summary

- Source name: Demo II V I
- Profile: product-like

## Output files

- events_yaml: changes_track8_export.events.yaml
- manifest: changes_track8_export_manifest.md
- syx: changes_track8_export.syx

## Product-like pattern settings

- Pattern mode: per-track
- Tempo: 120.0
- CHANGE: OFF
- RESET: INF
- Tracks 1-8 LENGTH: 16
- Tracks 1-8 SPEED: 1/8
- Tracks 9-16 LENGTH: 16
- Tracks 9-16 SPEED: 1
- Track default velocities:
  - Track 1: 70
  - Track 2: 70
  - Track 3: 70
  - Track 4: 50
  - Track 5: 70
  - Track 6: 50
  - Track 7: 100

## Track 8 export counts

- Track 8 chord event count: 3
- Track 8 note row count: 18

## SysEx status

- SysEx generated: yes
- SysEx size bytes: 114118

## Toolkit dependency note

- .events.yaml export does not require digitone-syx-toolkit.
- .syx export requires digitone-syx-toolkit and uses lazy import through Changes integration helpers.
- Dependency direction remains changes -> digitone-syx-toolkit.

## Safety

- This API does not send MIDI.
- This API does not operate hardware.
- This API does not provide CLI commands.

## Caveats

- SongModel/project file loading is not implemented here.
- This export path targets Track 8 product-like artifacts only.
- Verify generated artifacts before any external transfer.
