# Validation Matrix

## Purpose

This matrix tracks what is currently validated for each SongModel fixture in the v0.1 release-candidate workflow.

The validation matrix currently emphasizes Track 8 because Track 8 is the stabilized RC subset.
It is not the full product priority order.

Validation levels:

- hardware-validated: manually observed on Digitone II hardware
- software E2E validated: automated export -> check --manifest -> dry-run coverage
- export/manifest validated: automated export and manifest/count validation without full check/dry-run flow
- not validated: no dedicated validation at this level yet

## Product priority vs validation status

| Layer | Tracks | Product priority | Current validation status |
| --- | --- | --- | --- |
| Harmony Cloud | 1-6 | primary | architecture target / partial implementation; not yet RC-stabilized |
| Bass | 7 | secondary | architecture target / partial implementation; not yet RC-stabilized |
| Chord | 8 | additional | RC-stabilized subset |

## Fixture Matrix

| Fixture | Purpose | Export | SysEx generation | check --manifest | dry-run | real-send hardware | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `examples/song_models/demo_cmaj7.changes.yaml` | Quick smoke path | yes | optional | not primary path | not primary path | no | Basic single-chord smoke fixture |
| `examples/song_models/demo_ii_v_i.changes.yaml` | Known hardware baseline | yes | yes | yes | yes | yes | Observed Track 8 steps: Dm7 step1, G7 step5, Cmaj7 step9 |
| `examples/song_models/demo_multibar_turnaround.changes.yaml` | Multi-bar regression | yes | yes | yes | yes | no | Software E2E validated |
| `examples/song_models/demo_multisection_form.changes.yaml` | Multi-section regression | yes | not covered as stable E2E path | export/manifest regression only | export/manifest regression only | no | Covered by export + manifest count regression tests |

## Current Summary

- Product priority remains Cloud > Bass > Chord even though the current matrix is Track 8-focused.
- Hardware-validated: `demo_ii_v_i`
- Software E2E validated: `demo_ii_v_i`, `demo_multibar_turnaround`
- Export/manifest validated: `demo_multisection_form` (and smoke export coverage for `demo_cmaj7`)
- Not validated: broad hardware/device matrix and full payload-semantic validation