# Digitone II Bundle Pre-Hardware Validation Checklist (2026-05-26)

## Scope

This checklist validates transport, display, ordering, and timing safety for bundle workflow before harmonic-quality listening review.

Execution result update (2026-05-27):

- All 4 validations passed on hardware by direct visual/aural confirmation.
- No screenshots or slot-capture evidence were recorded in this run.

## Generated Bundles

- section bundle smoke test:
  - input: `examples/generated/hardware_validation_bundle_precheck/section_bundle_smoke.progression.yaml`
  - artifacts: `examples/generated/hardware_validation_bundle_precheck/section_bundle_smoke/`
- held note boundary test:
  - input: `examples/generated/hardware_validation_bundle_precheck/held_note_boundary.progression.yaml`
  - artifacts: `examples/generated/hardware_validation_bundle_precheck/held_note_boundary/`
- overflow split test:
  - input: `examples/generated/hardware_validation_bundle_precheck/overflow_split.progression.yaml`
  - artifacts: `examples/generated/hardware_validation_bundle_precheck/overflow_split/`
- repeated section naming test:
  - input: `examples/generated/hardware_validation_bundle_precheck/repeated_section_naming.progression.yaml`
  - artifacts: `examples/generated/hardware_validation_bundle_precheck/repeated_section_naming/`

## Device Setup

- Select destination pattern start slot on Digitone II.
- Use the same destination start slot per test unless intentionally verifying overwrite behavior.
- Keep project tempo lock and pattern scale settings visible on device screen while importing.

## Validation 1: Section Bundle Smoke Test

Target names:

- INT BLUE MOON
- A BLUE MOON
- SOL BLUE MOON
- OUT BLUE MOON

Checks:

- 4 patterns are imported sequentially from the selected destination slot.
- On-device display makes current section position identifiable.
- Pattern Name text matches manifest order exactly.
- Per-pattern tempo/speed/total_steps match manifest values.

Result:

- [X] pass
- [ ] fail
- notes:
  - Visual confirmation on device display and slot order.
  - No screenshot/capture evidence recorded.

## Validation 2: Held Note Boundary Test

Checks:

- Playing a later pattern standalone still produces required opening tones from step 1.
- At pattern boundary, chord voices are not partially missing.
- Bass onset is present and not dropped.
- No unnatural re-trigger burst and no unintended silence gap.

Result:

- [X] pass
- [ ] fail
- notes:
  - Visual/aural confirmation for boundary onset and no missing chord/bass at pattern switch.
  - No screenshot/capture evidence recorded.

## Validation 3: Overflow / Sequential Import Test

Target names include split identifiers:

- SOL1 BLUE MOON
- SOL2 BLUE MOON

Checks:

- Split patterns are placed in strict order.
- Shared timing (tempo/speed/q_step intent) is preserved across splits.
- No audible cut at previous-tail / next-head boundary.
- Display name allows immediate split position recognition.

Result:

- [X] pass
- [ ] fail
- notes:
  - Visual confirmation for sequential placement and SOL1/SOL2 split readability.
  - No screenshot/capture evidence recorded.

## Validation 4: Repeated Section Naming Test

Target names:

- A1 BLUE MOON
- B BLUE MOON
- A2 BLUE MOON

Checks:

- Repeated A occurrences are imported as distinct patterns.
- Device display clearly differentiates A1 vs A2.
- Musical order and slot order match manifest order.

Result:

- [X] pass
- [ ] fail
- notes:
  - Visual confirmation for A1/B/A2 order and display differentiation.
  - No screenshot/capture evidence recorded.

## Evidence to Record

- Capture the imported slot range and screenshot Pattern Name display per validation.
- Save observed mismatch details against `bundle_manifest.json` entries.
- If failure occurs, include:
  - failing fixture path
  - failing segment index and pattern name
  - observed vs expected timing/display behavior
