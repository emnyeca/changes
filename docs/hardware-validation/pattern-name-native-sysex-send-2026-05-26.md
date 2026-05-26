# Hardware Validation: Pattern Name (2026-05-26)

## Goal

Validate that generated Pattern SysEx from `changes` + `digitone-syx-toolkit` writes expected Pattern Name on Digitone II hardware.

## Preconditions

1. Digitone II connected and receiving SysEx via configured MIDI path.
2. Generated `.syx` files available for each test name.
3. Same base pattern/template conditions as analysis docs.

## Test Names

1. INTRO
2. THEME A
3. BLUE MOON A
4. ÅNGSTRÖM

## Procedure

1. Generate events YAML and `.syx` from pipeline for target name.
2. Send `.syx` to Digitone II.
3. Open target pattern and read displayed name.
4. Power-cycle once and re-open pattern to confirm persistence.
5. Re-send another name and verify overwrite behavior.

## Generated artifacts

1. `examples/generated/pattern_name_validation/intro.digitone.events.yaml`
2. `examples/generated/pattern_name_validation/intro.syx`
3. `examples/generated/pattern_name_validation/theme_a.digitone.events.yaml`
4. `examples/generated/pattern_name_validation/theme_a.syx`
5. `examples/generated/pattern_name_validation/blue_moon_a.digitone.events.yaml`
6. `examples/generated/pattern_name_validation/blue_moon_a.syx`
7. `examples/generated/pattern_name_validation/angstrom.digitone.events.yaml`
8. `examples/generated/pattern_name_validation/angstrom.syx`

## Send checklist (exact)

1. Open `digitone_syx_toolkit gui`.
2. In `MIDI Capture/Replay`, choose Digitone II output port.
3. Select one generated `.syx` file from the list above.
4. Press `Send to Output Port`.
5. On Digitone II, confirm displayed Pattern Name equals expected name.
6. Repeat for all 4 names.
7. Re-send a different file into same destination slot and confirm overwrite behavior.

## Checklist

- [ ] INTRO displays exactly.
- [ ] THEME A displays exactly.
- [ ] BLUE MOON A displays exactly.
- [ ] ÅNGSTRÖM displays exactly.
- [ ] Name survives power-cycle.
- [ ] Re-send updates only target pattern as intended.
- [ ] No unexpected tempo/speed/step changes after name-only update.

## Notes Template

- Date:
- Device OS:
- MIDI path:
- Result summary:
- Deviations / anomalies:
