# Native SysEx Pipeline Status (2026-05-26)

## Completed

- Digitone II Pattern SysEx analysis and encoder for:
  - trigger / track / step / pitch / velocity / full length / tempo / speed / total steps / pattern name
- Simple ii-V-I end-to-end hardware validation
- Blue Moon end-to-end hardware validation
- Pattern Name hardware validation completed and passed
- Song-level shared timing plan for split patterns
- Section-first deterministic split planning with 128-step capacity handling
- Prefix-first readable auto naming for multi-pattern exports
- Bundle artifacts export:
  - `digitone_bundle_plan.json`
  - `bundle_manifest.json`
  - ordered per-pattern events YAML and per-pattern SYX
  - concatenated bundle SYX
- Sequential send support in toolkit (ordered file list and concatenated bundle replay)
- Initial BLUE MOON pattern-bundle fixture generated:
  - `examples/generated/pattern_bundle_blue_moon/`

## Confirmed import behavior

- Multiple Pattern SYX messages can be received consecutively.
- They are placed sequentially from the destination start slot selected on the device.
- Destination slot does not need to be encoded by the generator.
- Same destination slot is overwritten on receive.

## Current boundary policy

- `changes` separates `source_title` (song identity) and `pattern_name` (device display name).
- events YAML `name` is always exported from the final per-pattern `pattern_name`.
- `changes` supports explicit per-segment Pattern Name override, records `pattern_name_source` (`auto` or `explicit`), and preserves override intent (no auto prefix injection when explicit name is present).
- toolkit normalizes Pattern Name with ASCII lowercase to uppercase, validates allowed characters across the full normalized string, and truncates over-16-char names to the first 16 characters.
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

- Additional hardware validation for bundle workflow (sequential import order, practical display readability, shared timing behavior across sections)
- iReal Pro HTML importer implementation
- MusicXML importer implementation
