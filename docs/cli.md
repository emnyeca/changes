# Changes CLI reference

This document describes developer/maintenance CLI commands that remain available for validation and internal workflows.

The primary user-facing interface of EUB Changes is the Windows desktop app.

## Current Commands

### Digitone Product Artifact Export (Tracks 1-8)

```powershell
changes export digitone-product `
  --input examples/ii_v_i_intro_a.progression.yaml `
  --output-dir out/digitone-product `
  --layers cloud,bass,chord
```

Summary:

- Generates Cloud on Digitone II Tracks 1-6, Bass on Track 7, and Chord on Track 8 as one product export path.
- Export never sends MIDI.
- `--layers` defaults to `cloud,bass,chord`.
- Layer subsets such as `--layers cloud,bass`, `--layers chord`, and `--layers cloud` are available for development and validation.
- `.syx` is generated only when `--write-syx` is specified.

### Digitone SysEx Send

List ports:

```powershell
changes send digitone-syx --list-ports
```

Dry-run:

```powershell
changes send digitone-syx `
  --syx out/digitone-product/digitone_product.syx `
  --port "Elektron Digitone II 2" `
  --dry-run
```

Guarded real-send:

```powershell
changes send digitone-syx `
  --syx out/digitone-product/digitone_product.syx `
  --port "Elektron Digitone II 2" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

Summary:

- `--list-ports` lists output ports only and does not send MIDI.
- `--dry-run` validates SysEx bytes and the selected port name without writing hardware.
- `--real-send` writes to hardware.
- `--yes-i-understand-this-writes-to-hardware` is required for real-send.
- `pip install .[midi]` is required for port listing and real-send.

### Digitone SysEx File Check

```powershell
changes check digitone-syx --syx out/digitone-product/digitone_product.syx
```

Summary:

- Validates the SysEx file envelope.
- Does not send MIDI.
- Does not require `mido`.

## Safety Boundaries

- Export never sends MIDI.
- Check never sends MIDI.
- Real-send requires explicit confirmation.
- MIDI port auto-selection is not allowed.
- MIDI optional dependencies remain optional.
