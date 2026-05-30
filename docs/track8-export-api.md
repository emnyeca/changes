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

## MIDI send boundary

Phase 6A adds a dry-run transport boundary for future SysEx sending.

The Track 8 export API and CLI still do not send MIDI.

See docs/midi-send-transport-boundary.md.

Export continues to write `.syx` artifacts only; dry-run send validation lives in the separate send CLI.

See docs/cli.md for the current user-facing CLI reference.

See docs/generated-artifacts-policy.md for the current retained-artifact policy.

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

## Developer CLI wrapper

Track 8 export currently provides a practical explicit CLI wrapper:

```bash
changes export digitone-track8 --demo cmaj7 --output-dir out/digitone-track8 --events-yaml-only
```

SongModel YAML v1 input is also supported:

```bash
changes export digitone-track8 \
    --input examples/song_models/demo_cmaj7.changes.yaml \
    --output-dir out/digitone-track8 \
    --events-yaml-only
```

--demo and --input are mutually exclusive.

It does not load arbitrary song/project files.

It does not send MIDI.

SysEx generation is enabled by default and requires digitone-syx-toolkit.

Use --events-yaml-only to avoid the toolkit dependency.

## SongModel YAML input

Phase 5E adds SongModel YAML v1 input mode:

```bash
changes export digitone-track8 \
    --input examples/song_models/demo_cmaj7.changes.yaml \
    --output-dir out/digitone-track8 \
    --events-yaml-only
```

--demo and --input are mutually exclusive.

The input file must use SongModel YAML v1.

This command still does not send MIDI or operate hardware.

See docs/song-model-yaml-v1.md for the file format.

See docs/track8-export-cli-readiness.md for current readiness status and boundaries.

See docs/index.md for the documentation entry point.

## Multi-chord coverage

Track 8 export is covered by both:

- examples/song_models/demo_cmaj7.changes.yaml
- examples/song_models/demo_ii_v_i.changes.yaml

The II-V-I example verifies that SongModel YAML input can generate multiple Track 8 chord events across different offsets.
