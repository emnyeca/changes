# Changes Documentation Index

## Product framing

- Product architecture: `product-architecture.md`
- Current state: `current-state.md`

## Current practical workflows

- Track 8 export: `track8-export-api.md`
- SongModel YAML v1: `song-model-yaml-v1.md`
- End-to-end workflow: `e2e-user-workflow.md`
- Digitone SysEx real-send workflow: `real-send-workflow.md`
- CLI reference: `cli.md`

## Release candidate

- Workflow RC status: `release-candidate-status.md`
- Validation status: `validation-status.md`
- Validation matrix: `validation-matrix.md`
- Fixture inventory: `fixture-inventory.md`
- Known limitations: `known-limitations.md`

## Safety and validation

- MIDI send transport boundary: `midi-send-transport-boundary.md`
- MIDI backend adapter design: `midi-backend-adapter-design.md`
- MIDI hardware validation checklist: `midi-hardware-validation-checklist.md`
- First Digitone real-send validation: `hardware-validation/digitone-syx-real-send-first-validation.md`
- Generated artifacts policy: `generated-artifacts-policy.md`
- Manifest-aware validation: `manifest-aware-validation.md`

## Current notes

- Product priority remains Cloud > Bass > Chord.
- The current RC emphasis on Track 8 reflects the stabilized subset, not the full product architecture.
- Export and send remain separate.
- Guarded real-send remains explicit and requires confirmation.
- Optional MIDI dependencies remain optional and are only needed for port listing, real-send, and generic MIDI writing.
