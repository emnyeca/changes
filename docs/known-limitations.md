# 既知の制約

## Scope

The current release-candidate workflow is focused on Chord export to Digitone II Track 8 and guarded SysEx sending.

The Chord workflow on Digitone Track 8 is currently the stabilized RC path, but the intended product architecture prioritizes Track 1-6 Harmony Cloud and Track 7 Bass before this Chord subset.

The current Track 8 emphasis in docs and validation should be read as subset status for Chord workflow, not as the product priority order.

## Known limitations

### Hardware validation is narrow

Only the II-V-I fixture has been manually validated on Digitone II.

### SongModel coverage is limited

Broader software fixtures now include multi-bar and multi-section examples.

Hardware validation is still limited to the II-V-I fixture.

The current workflow still does not imply that all SongModel inputs are supported.

See `docs/validation-matrix.md` for exact fixture-by-fixture scope.

### Manifest validation is metadata-level

`changes check digitone-syx --manifest` validates envelope and metadata consistency.

It does not validate full Digitone payload semantics.

### Real-send is intentionally guarded

Real-send requires:

- explicit `.syx`
- explicit `--port`
- `--real-send`
- `--yes-i-understand-this-writes-to-hardware`

This is intentional and should not be weakened.

### MIDI backend is optional

`mido` and `python-rtmidi` are required only for port listing and real-send.

### Generated artifacts are temporary development assets

Files under `out/digitone-track8/` are retained temporarily for reproducibility.

They are not permanent release assets yet.

### Not a consumer installer

This is still a developer/technical CLI workflow.

A consumer-facing app or installer is out of scope for the current RC.
