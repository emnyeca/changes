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
- Context-aware voicing migration completed:
  - fixed per-chord expansion removed from main render path
  - Local Pitch Collection + Selected Scale Collection + slot extraction (`1,3,5,6/13,7,9`)
  - corrected C-major context output for `Am7` (`F`, not `F#`)
- Bundle robustness hardening completed:
  - section occurrence-aware split planning (`A`, `B`, `A` handled as independent occurrences)
  - boundary carryover reconstruction for section/capacity splits (held notes retriggered at pattern step 1)
  - deterministic short-section merge policy for Digitone minimum length (`2..128` enforced)
  - shared Pattern Name policy for single and bundle outputs (auto/explicit consistent validation)
  - `digitone-bundle` CLI backend integrated with artifact and optional SYX output
  - manifest enriched with `pattern_count`, occurrence/global-order metadata, and path aliases
- Bundle transport/display/timing hardware validation completed:
  - Section bundle smoke test: pass
  - Held note boundary test: pass
  - Overflow/sequential import test: pass
  - Repeated section naming test: pass
  - verification mode: direct visual/aural confirmation on hardware (no screenshot/capture evidence recorded)
- Harmonic context engine extension completed:
  - canonical qualities added:
    - `major`, `m`, `6`, `m6`, `maj7`, `m7`, `mMaj7`, `m9`, `m7b5`, `dim7`
    - `7`, `9`, `7b9`, `7#9`, `7b5`, `7#5`, `7#11`, `7b13`, `7#9b5`
    - `7sus4`, `9sus4`, `7b9sus4`, `alt`, slash bass
  - structured internal chord model introduced (base quality / 7th / extensions / altered / added / omitted / slash / semantic tag)
  - prioritized collection families added: diatonic/dorian, harmonic minor, melodic minor/lydian dominant, whole-tone, diminished
  - deterministic tie-break by signature-root circular distance + stable ordering
  - normalized harmonic identity used for repeated-chord context decisions
  - chromatic fallback removed; context-reduction retry policy implemented (`current+prev+next` -> `current+prev` -> `current`)
  - sus heptatonic extraction rule added: `1-4-5-13-b7-9`
- Regression validation completed:
  - `changes`: `97 passed, 2 skipped`
  - `digitone-syx-toolkit`: `81 passed`

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

## Bundle transport validation artifacts (generated)

- `examples/generated/hardware_validation_bundle_precheck/section_bundle_smoke/`
  - pattern names: `INT BLUE MOON`, `A BLUE MOON`, `SOL BLUE MOON`, `OUT BLUE MOON`
  - packet check: 4 individual `.syx` packets and 4 packets in `.bundle.syx`
- `examples/generated/hardware_validation_bundle_precheck/held_note_boundary/`
  - pattern names: `INT BLUE MOON`, `A BLUE MOON`
  - packet check: 2 individual `.syx` packets and 2 packets in `.bundle.syx`
- `examples/generated/hardware_validation_bundle_precheck/overflow_split/`
  - pattern names: `SOL1 BLUE MOON`, `SOL2 BLUE MOON`
  - packet check: 2 individual `.syx` packets and 2 packets in `.bundle.syx`
- `examples/generated/hardware_validation_bundle_precheck/repeated_section_naming/`
  - pattern names: `A1 BLUE MOON`, `B BLUE MOON`, `A2 BLUE MOON`
  - packet check: 3 individual `.syx` packets and 3 packets in `.bundle.syx`
- Manual checklist document:
  - `docs/hardware-validation/digitone-bundle-pre-hardware-validation-2026-05-26.md`

## Intentionally Unimplemented Scope (Current)

- MusicXML importer implementation itself (policy is finalized, implementation deferred to importer task).
- iReal Pro HTML / `irealb://` direct decoding.
- iReal Pro alias grammar expansion remains deferred (data-driven implementation after symbol-sample collection).
- `allow_sus_add3` remains deferred.

## Next major target

- iReal Pro HTML importer implementation
- MusicXML importer implementation
