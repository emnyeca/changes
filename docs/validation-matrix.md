# Validation Matrix

This matrix tracks the current release-candidate validation scope.

The current validation target is the product workflow: Cloud, Bass, and Chord generated together for Digitone II Tracks 1-8.

## Validation Levels

- hardware-validated: manually observed on Digitone II
- software E2E validated: export -> check -> dry-run is covered by automated tests
- export validated: export artifacts are covered by automated tests
- not validated: dedicated validation is not yet present

## Layer Status

| Layer | Tracks | Role | Current validation status |
| --- | --- | --- | --- |
| Harmony Cloud | 1-6 | six-voice playable harmony texture | generation implemented; product export tests present; broad hardware validation pending |
| Bass | 7 | root movement / slash-bass grounding layer | generation implemented; product export tests present; broad hardware validation pending |
| Chord | 8 | symbol-faithful vertical layer | generation implemented as part of product export |

## Fixture Matrix

| Fixture | Purpose | Product export | SysEx generation | check | dry-run | real-send hardware | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `examples/ii_v_i_intro_a.progression.yaml` | Compact product smoke path | yes | optional | yes | yes | limited | Main CLI product-export fixture |
| `examples/song_models/demo_ii_v_i.changes.yaml` | SongModel regression input | indirect | yes | yes | yes | historical | Kept as model/import regression data |
| `examples/song_models/demo_multibar_turnaround.changes.yaml` | Multi-bar regression | indirect | yes | yes | yes | no | Software regression data |
| `examples/song_models/demo_multisection_form.changes.yaml` | Multi-section regression | indirect | partial | yes | partial | no | Software regression data |

## Summary

- Current validation should be read as product-workflow validation, not a standalone Chord feature.
- Track 8 remains the Chord layer inside the product workflow.
- Broader hardware/device matrix and payload semantic validation remain future work.
