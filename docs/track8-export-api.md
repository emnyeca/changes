# Track 8 Export API

## 1. Purpose
This document describes the minimal explicit Python API for Track 8 artifact export.

The API takes an in-memory SongModel and writes deterministic export artifacts.

## 2. Why Python API before CLI
Track 8 export is implemented as a Python API before a user-facing CLI because:

- SongModel/project file format is still SPEC-OPEN.
- CLI namespace exists, but Track 8 command shape is not stable yet.
- Python API enables deterministic test-first validation of export behavior.

## 3. API
Public API in src/changes/digitone/track8_export_api.py:

- Track8ExportPaths
- build_track8_export_yaml_payload_from_song(...)
- build_track8_export_manifest(...)
- export_track8_artifacts_from_song(...)

Constants:

- DEFAULT_TRACK8_EXPORT_BASENAME = "changes_track8_export"
- DEFAULT_TRACK8_EXPORT_PROFILE = "product-like"

## 4. Output files
For basename "my_song":

- my_song.events.yaml
- my_song.syx
- my_song_manifest.md

If include_sysex=False:

- my_song.events.yaml
- my_song_manifest.md

No .syx is generated.

## 5. Toolkit dependency
Dependency behavior:

- .events.yaml only export does not require toolkit.
- .syx export requires digitone-syx-toolkit.
- toolkit dependency is used lazily only during SysEx generation.
- dependency direction remains changes -> digitone-syx-toolkit.

## 6. Safety
This API intentionally does not:

- send MIDI
- operate hardware
- expose CLI command behavior
- implement arbitrary input file loading

## 7. Local example
Use an in-memory SongModel (see tests/test_track8_export_api.py for concrete SongModel construction):

```python
from changes.digitone.track8_export_api import export_track8_artifacts_from_song

paths = export_track8_artifacts_from_song(
    song,
    "out/digitone-track8",
    basename="my_song",
    name="My Song",
    include_sysex=True,
    overwrite=False,
)
```

## 8. Next phase
Recommended next phase:

Phase R2B: implement toolkit integration CI job

Rationale:

- Phase 5B adds a concrete export API with optional toolkit path.
- CI should make toolkit-dependent behavior visible before broadening CLI surface.
- After R2B, Phase 5C can add a minimal developer CLI wrapper around this API.
