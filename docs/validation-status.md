# Validation Status

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
- broader SongModel fixture coverage:
  - `examples/song_models/demo_multibar_turnaround.changes.yaml`
  - `examples/song_models/demo_multisection_form.changes.yaml`
- broader fixtures validated through export -> check --manifest -> dry-run (software path only)

Additional software fixtures now cover broader SongModel shapes, including multi-bar and multi-section examples. These fixtures are validated through export, manifest-aware check, and dry-run only. They have not yet been manually validated on Digitone II hardware.

## Not yet validated

- broad song form coverage
- all duration / LEN mappings
- all Track 8 parameter mappings
- multiple Digitone II firmware versions
- multiple OS environments
- large song exports
- consumer-style installation flow
