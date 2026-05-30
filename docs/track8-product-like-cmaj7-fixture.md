# Track 8 Product-like Cmaj7 Fixture

## 1. Purpose
This phase creates a product-like Track 8 Cmaj7 fixture using per-track events YAML.

The fixture is software-generated only and does not send MIDI or operate hardware.

## 2. Generated files

- examples/generated/track8_product_like_validation/track8_product_like_cmaj7.events.yaml
- examples/generated/track8_product_like_validation/track8_product_like_cmaj7.syx
- examples/generated/track8_product_like_validation/track8_product_like_cmaj7_manifest.md

## 3. What is product-like in this fixture
This fixture encodes product-like pattern settings and Track 8 chord content in one artifact set:

- pattern.mode = per-track
- track_scale entries for tracks 1..16
- pattern.change = OFF
- pattern.reset = INF
- track_defaults.velocity for tracks 1..7
- Track 8 same-step Cmaj7 chord events

Expected Track 8 chord contract:

- track: 8
- step: 1
- notes: C4 E4 G4 B4 D5 A5
- velocities: 70 70 70 50 70 50
- length_code: 0x4E
- micro timing: 0

## 4. What remains not validated
This fixture does not validate:

- complete song export behavior
- bundle planner integration
- UI workflow
- hardware transfer automation
- all chord qualities
- all keys
- Track 1-7 musical event behavior
- Track 1-7 LEN baseline behavior until hardware validation confirms it

## 5. How to regenerate
From local changes repo:

```powershell
python -m pip install -e .
python -m pip install -e ..\digitone-syx-toolkit
python -c "from changes.digitone.track8_product_like_fixture_generation import write_track8_product_like_cmaj7_fixture; write_track8_product_like_cmaj7_fixture('examples/generated/track8_product_like_validation', overwrite=True)"
```

## 6. Hardware validation procedure

1. Open Elektron Transfer.
2. Send track8_product_like_cmaj7.syx to Digitone II.
3. Load the generated pattern.
4. Confirm pattern mode is PER TRACK.
5. Confirm LENGTH and SPEED settings if visible.
6. Confirm CHANGE is OFF and RESET is INF.
7. Confirm Track 1-7 default velocities if visible.
8. Inspect Track 8 step 1.
9. Confirm the six same-step notes are present.
10. Play the pattern and confirm it sounds like a Cmaj7 voicing.

## 7. Next phase
Recommended next step:

Phase 4M: Product-like Track 8 Cmaj7 hardware validation log
