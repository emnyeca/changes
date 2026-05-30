# Generated Artifacts Policy

Generated validation artifacts under `out/digitone-track8/` are currently kept for review and reproducibility during active development.

This is intentional for now.

They may be removed or relocated later when the workflow stabilizes.

Current retained artifacts:

- `changes_track8_export.events.yaml`
- `changes_track8_export.syx`
- `changes_track8_export_manifest.md`

Recommended validation command for retained `.syx` artifacts:

- `changes check digitone-syx --syx out/digitone-track8/changes_track8_export.syx`

These artifacts are not the source of truth.

Source of truth:

- SongModel YAML input
- export code
- validation logs

Do not treat generated artifacts as permanent release assets yet.
