# Track 8 Length Encoding and YAML Export (Phase 4D)

## Scope

This phase finalizes deferred Track 8 length representation from Phase 4C.

Included:

- exact duration-to-length-code conversion for explicit Track 8 note lengths
- deferred-row finalization for toolkit-style Track 8 event rows
- toolkit-loadable events YAML payload mapping builder
- optional YAML text dump helper

Excluded:

- SysEx generation
- runtime import or direct call of digitone-syx-toolkit from Changes
- hardware operation
- bundle planning changes
- UI changes

## Toolkit Schema Inspection

Inspected toolkit files:

- digitone-syx-toolkit/src/digitone_syx_toolkit/events_yaml.py
- digitone-syx-toolkit/src/digitone_syx_toolkit/digitone2/length_codes.py
- digitone-syx-toolkit/examples/generated/track8_chord_trigger_validation/track8_cmaj7_root.events.yaml

Observed requirements:

- toolkit accepts explicit length via length_code
- toolkit accepts inherited length via length: inherit
- toolkit explicit lengths are Digitone-specific codes, not step counts
- top-level events YAML requires pattern mapping
- events use 1-based step and 1-based track

## Explicit Length Policy

The conversion policy is:

duration_quarters -> sixteenth-note units -> exact finite Digitone length_code

Calculation uses exact rational arithmetic:

- duration = Fraction(duration_quarters)
- sixteenth_units = duration * 4

No approximation is used.
If no exact finite code exists, ValueError is raised.

Known exact examples:

- "1/2" -> 2 sixteenth units -> 0x1E
- "1" -> 4 sixteenth units -> 0x2E
- "2" -> 8 sixteenth units -> 0x3E
- "4" -> 16 sixteenth units -> 0x4E

## Inherit Policy

Inherited length rows are preserved as:

- length: inherit

No length_code is added for inherited rows.

## Finalization Policy

Input rows from Phase 4C may contain deferred explicit fields:

- length_mode: explicit_event_length
- duration_quarters: "..."

Finalization replaces those with:

- length_code: "0x.."

and removes deferred fields.

Rows are validated so that a row cannot contain both length and length_code.

## YAML Payload Shape

The builder returns a mapping compatible with toolkit loader expectations:

- version
- device
- name (optional)
- pattern
- events

pattern is always emitted and currently uses pattern-wide mode with:

- mode
- tempo
- speed
- total_steps

total_steps behavior:

- if omitted, total_steps = max(16, max event step)
- allowed range is 2..128

## Metadata Policy

- metadata is stripped by default
- metadata can be retained with include_metadata=True for debugging
- metadata-retaining payload may not be accepted by toolkit loader

## Scope Boundary Confirmation

This phase does not implement:

- SysEx generation
- runtime toolkit integration
- hardware operation
- bundle planner updates
- UI changes

## Next Phase

Recommended follow-up:

- Phase 4E: toolkit validation integration and explicit SysEx generation entrypoint

Alternative if integration timing differs:

- Phase 4E: hardware-validation fixture generation for Track 8 chord length behavior
