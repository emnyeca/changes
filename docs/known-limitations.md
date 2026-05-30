# Known Limitations

## Scope

The current release-candidate workflow is focused on Digitone II Track 8 export and guarded SysEx sending.

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
