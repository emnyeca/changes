# E2E user workflow

This document describes the supported non-hardware and guarded hardware workflow.

## Main path

```text
compact progression or MusicXML
  -> product export (Cloud/Bass/Chord, Tracks 1-8)
  -> SysEx file check
  -> dry-run
  -> guarded real-send
```

## Product export

```powershell
changes export digitone-product `
  --input examples/ii_v_i_intro_a.progression.yaml `
  --output-dir out/digitone-product `
  --layers cloud,bass,chord `
  --write-syx
```

The product export path writes artifacts only. It does not send MIDI.

## SysEx check

```powershell
changes check digitone-syx --syx out/digitone-product/digitone_product.syx
```

The check command validates the SysEx file envelope and does not touch MIDI hardware.

## Dry-run send

```powershell
changes send digitone-syx `
  --syx out/digitone-product/digitone_product.syx `
  --port "Elektron Digitone II 2" `
  --dry-run
```

Dry-run validates the selected port name and SysEx bytes without writing hardware.

## Guarded real-send

```powershell
changes send digitone-syx `
  --syx out/digitone-product/digitone_product.syx `
  --port "Elektron Digitone II 2" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

Real-send writes to hardware and therefore requires explicit confirmation.

`mido` and `python-rtmidi` are only required for port listing and real-send:

```powershell
python -m pip install -e ".[midi]"
```
