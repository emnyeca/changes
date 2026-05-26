# Native SysEx Pipeline Status (2026-05-26)

## Completed

- Digitone II Pattern SysEx analysis and encoder for:
  - trigger / track / step / pitch / velocity / full length / tempo / speed / total steps / pattern name
- Simple ii-V-I end-to-end hardware validation
- Blue Moon end-to-end hardware validation
- Pattern Name hardware validation workflow and artifacts prepared

## Confirmed import behavior

- Multiple Pattern SYX messages can be received consecutively.
- They are placed sequentially from the destination start slot selected on the device.
- Destination slot does not need to be encoded by the generator.
- Same destination slot is overwritten on receive.

## Current boundary policy

- `changes` exports `DigitoneCompilePlan.title` to toolkit events YAML `name` as-is.
- toolkit validates/normalizes/encodes Pattern Name and rejects over-16-char names without silent truncation.
- Generic MIDI export path is unaffected by Digitone Pattern Name restrictions.

## Pattern Name validation artifacts

- `examples/generated/pattern_name_validation/intro.digitone.events.yaml`
- `examples/generated/pattern_name_validation/intro.syx`
- `examples/generated/pattern_name_validation/theme_a.digitone.events.yaml`
- `examples/generated/pattern_name_validation/theme_a.syx`
- `examples/generated/pattern_name_validation/blue_moon_a.digitone.events.yaml`
- `examples/generated/pattern_name_validation/blue_moon_a.syx`
- `examples/generated/pattern_name_validation/angstrom.digitone.events.yaml`
- `examples/generated/pattern_name_validation/angstrom.syx`

Execution note:

- This session generated artifacts and checklist documents for hardware validation; runbook execution results should be appended in `docs/hardware-validation/pattern-name-native-sysex-send-2026-05-26.md`.

## Next major target

- Digitone Pattern Bundle and section splitting
- Batch replay / sequential send support
- Whole-song shared timing plan across split patterns
- Per-pattern readable naming policy
- Then iReal Pro HTML / MusicXML importer implementation
