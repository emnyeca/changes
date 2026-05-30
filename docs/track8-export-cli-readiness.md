# Track 8 Export CLI Readiness

## Summary

The Track 8 export CLI is now usable as a practical developer/user-facing export command for SongModel YAML v1 input.

Current command:

```bash
changes export digitone-track8 \
  --input examples/song_models/demo_cmaj7.changes.yaml \
  --output-dir out/digitone-track8 \
  --events-yaml-only
```

For SysEx generation:

```bash
changes export digitone-track8 \
  --input examples/song_models/demo_cmaj7.changes.yaml \
  --output-dir out/digitone-track8 \
  --overwrite
```

## Supported input modes

### SongModel YAML v1
Primary input mode:

--input PATH

The input file must use SongModel YAML v1.

### Built-in demo
Development/demo mode:

--demo cmaj7

This remains useful for smoke tests and examples.

## Output artifacts
The command writes:

- {basename}.events.yaml
- {basename}.syx when SysEx generation is enabled
- {basename}_manifest.md

Default basename:

changes_track8_export

## Name behavior
If --name is provided, it is used as the exported pattern name.

If --name is omitted, the CLI uses the input song title.

## Toolkit dependency

- --events-yaml-only does not require digitone-syx-toolkit.
- SysEx generation requires digitone-syx-toolkit.
- toolkit integration remains lazy.
- dependency direction remains changes -> digitone-syx-toolkit.

## Safety boundaries
This CLI does not:

- send MIDI
- operate hardware
- discover MIDI ports
- load arbitrary project/editor state
- support non-SongModel YAML project formats
- guarantee all chord qualities/keys/durations beyond tested paths

## Transport boundary

Phase 6A introduces a dry-run MIDI SysEx transport boundary for future send support.

Real MIDI send is still not implemented.

The Track 8 CLI remains artifact export only.

Phase 6B adds a separate dry-run `changes send digitone-syx` command for validating existing `.syx` files.

Export still does not send implicitly.

Phase 6D adds an optional backend prototype for future send work, but export CLI remains artifact-only and hardware validation is not yet performed.

## User-facing readiness decision
Status:

Ready as an explicit artifact export command for SongModel YAML v1 input.
Not yet ready as a complete end-user application workflow.

Reason:

Ready:

- SongModel YAML v1 input exists
- export artifacts are deterministic
- product-like Track 8 fixture passed hardware validation
- toolkit integration CI covers SysEx path
- MIDI send is not implicit

Not yet complete:

- no GUI
- no broad project/editor serialization
- no MIDI send flow
- limited but expanded coverage: single Cmaj7 and one-measure II-V-I examples
- no full user documentation/tutorial yet

## Recommended next phase
Recommend one of:

Phase 5G: Multi-chord SongModel YAML export coverage

or:

Phase 6A: MIDI send transport design

Recommendation:

Prefer Phase 5G before MIDI send.

Reason:

Before sending directly to hardware, the export path should be validated with more than a single Cmaj7 fixture.

## Documentation cleanup

Current docs now describe implemented CLI behavior:

- docs/track8-export-api.md
- docs/song-model-yaml-v1.md

Future CLI architecture cleanup may move early dispatch logic to full argparse subparsers, but this phase intentionally keeps the current small dispatch shape.
