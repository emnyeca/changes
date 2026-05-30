# Changes Documentation Index

## Current practical workflows

- Track 8 export: `track8-export-api.md`
- SongModel YAML v1: `song-model-yaml-v1.md`
- End-to-end workflow: `e2e-user-workflow.md`
- Digitone SysEx real-send workflow: `real-send-workflow.md`
- CLI reference: `cli.md`

## Release candidate

- Workflow RC status: `release-candidate-status.md`
- Validation status: `validation-status.md`
- Known limitations: `known-limitations.md`

## Safety and validation

- MIDI send transport boundary: `midi-send-transport-boundary.md`
- MIDI backend adapter design: `midi-backend-adapter-design.md`
- MIDI hardware validation checklist: `midi-hardware-validation-checklist.md`
- First Digitone real-send validation: `hardware-validation/digitone-syx-real-send-first-validation.md`
- Generated artifacts policy: `generated-artifacts-policy.md`
- Manifest-aware validation: `manifest-aware-validation.md`

## Current notes

- Export and send remain separate.
- Guarded real-send remains explicit and requires confirmation.
- Optional MIDI dependencies remain optional and are only needed for port listing, real-send, and generic MIDI writing.
