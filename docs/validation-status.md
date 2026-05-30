# Validation Status

The current validation emphasis is Track 8-heavy because Track 8 is the stabilized RC subset.

That emphasis does not change the intended product priority order:

- Cloud > Bass > Chord
- Track 1-6 > Track 7 > Track 8

## Hardware validation

Validated:

- Digitone II guarded real-send
- Fixture: `examples/song_models/demo_ii_v_i.changes.yaml`
- Observed progression:
  - Dm7 at step1
  - G7 at step5
  - Cmaj7 at step9
- Pattern location: A01
- Result: passed

Details:

`docs/hardware-validation/digitone-syx-real-send-first-validation.md`

## Software validation

Covered by tests:

- Track 8 export CLI
- SysEx file validation
- manifest-aware validation
- dry-run send
- guarded real-send safety checks using fake backend
- CLI help / dispatch
- MusicXML import and bundle diagnostics
- broader timeline rendering with chord and bass register bounds

Software E2E validated fixtures:

- `examples/song_models/demo_ii_v_i.changes.yaml`
- `examples/song_models/demo_multibar_turnaround.changes.yaml`

Export/manifest validated fixtures:

- `examples/song_models/demo_multisection_form.changes.yaml`
- `examples/song_models/demo_cmaj7.changes.yaml` (smoke-level fixture)

Additional software fixtures now cover broader SongModel shapes, including multi-bar and multi-section examples. Hardware validation is still limited to the II-V-I fixture.

These software checks show that broader Cloud/Bass/Chord-oriented building blocks exist in the codebase, but they do not yet make Track 1-6 or Track 7 an RC-stabilized product workflow.

See `docs/validation-matrix.md` and `docs/fixture-inventory.md` for fixture-level details.

## Not yet validated

- broad song form coverage
- all duration / LEN mappings
- all Track 8 parameter mappings
- multiple Digitone II firmware versions
- multiple OS environments
- large song exports
- consumer-style installation flow
