# Workflow Release Candidate Status

## Status

Release-candidate workflow: active development / v0.1 candidate.

This is not a polished public release.

## Current stable workflow

```text
SongModel YAML
  -> Track 8 export
  -> SysEx check
  -> manifest-aware validation
  -> dry-run send
  -> guarded real-send
```

## Current validated fixture

- Input: `examples/song_models/demo_ii_v_i.changes.yaml`
- Output: `out/digitone-track8/changes_track8_export.syx`
- Manifest: `out/digitone-track8/changes_track8_export_manifest.md`
- Device: Digitone II
- Firmware: 1.10D
- Result: passed for Dm7 -> G7 -> Cmaj7 Track 8 import/send workflow

## RC acceptance checklist

- [x] Track 8 export CLI exists.
- [x] SongModel YAML v1 input exists.
- [x] SysEx file envelope check exists.
- [x] Manifest-aware check exists.
- [x] Dry-run send exists.
- [x] Guarded real-send exists.
- [x] Real-send requires explicit confirmation.
- [x] First hardware validation passed for II-V-I fixture.
- [x] mido remains optional.
- [x] Export does not send.
- [x] Check does not send.
- [x] Broader SongModel software fixture coverage.
- [ ] Multiple hardware/device validation.
- [ ] Full Track 8 parameter mapping validation.
- [ ] Public-facing installer/app packaging.
- [ ] GUI workflow.

Additional software fixtures currently include:

- software E2E export/check/dry-run: `demo_multibar_turnaround`
- export/manifest regression coverage: `demo_multisection_form`

Hardware validation remains limited to the first II-V-I fixture.

See `docs/validation-matrix.md` and `docs/fixture-inventory.md` for exact fixture coverage.

## Release-candidate meaning

This means the current workflow is usable for controlled development and manual validation.

It does not mean the project is ready for general consumer use.
