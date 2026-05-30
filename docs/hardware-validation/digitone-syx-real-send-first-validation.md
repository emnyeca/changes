# Digitone SysEx Real-send First Hardware Validation

## Status

Performed (manual hardware validation run completed).

This document records the first manual hardware validation of guarded SysEx real-send to Digitone II.

Status in this document reflects user-reported observed hardware behavior.

## Branch

feature/digitone-real-send-hardware-validation-log

## Validation target

Guarded real-send command:

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Digitone II" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

One-line form:

```powershell
changes send digitone-syx --syx out/digitone-track8/changes_track8_export.syx --port "Digitone II" --real-send --yes-i-understand-this-writes-to-hardware
```

## Safety policy

This validation may write pattern/device data to Digitone II.

Before real-send:

- back up important Digitone II data
- confirm selected port is Digitone II
- confirm .syx file is expected
- confirm no live performance depends on the device state
- confirm user explicitly accepts overwrite risk

## Environment

Captured from manual validation run:

```text
Date: 2026-05-30
OS: Windows (PowerShell)
Python: not recorded
changes commit: not recorded
mido version: 1.3.3
python-rtmidi version: 1.5.8
Digitone II firmware: not recorded
Connection: not recorded
Port selected: Elektron Digitone II 2
SYX source: out/digitone-track8/changes_track8_export.syx
```

## Preparation commands

### 1. Install optional MIDI dependencies

```powershell
python -m pip install -e ".[midi]"
```

### 2. Confirm CLI is available

```powershell
changes --help
```

If root help is not meaningful yet, this can fail or show legacy help. That is not a blocker.

### 3. Generate a known-good Track 8 .syx

Use the II-V-I example:

```powershell
changes export digitone-track8 `
  --input examples/song_models/demo_ii_v_i.changes.yaml `
  --output-dir out/digitone-track8 `
  --basename changes_track8_export `
  --overwrite
```

One-line form:

```powershell
changes export digitone-track8 --input examples/song_models/demo_ii_v_i.changes.yaml --output-dir out/digitone-track8 --basename changes_track8_export --overwrite
```

Expected artifacts:

```text
out/digitone-track8/changes_track8_export.events.yaml
out/digitone-track8/changes_track8_export.syx
out/digitone-track8/changes_track8_export_manifest.md
```

### 4. Dry-run send

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Digitone II" `
  --dry-run
```

One-line form:

```powershell
changes send digitone-syx --syx out/digitone-track8/changes_track8_export.syx --port "Digitone II" --dry-run
```

Expected:

```text
Dry-run SysEx send validated:
hardware_send: no
```

### 5. List MIDI output ports

```powershell
changes send digitone-syx --list-ports
```

Expected:

```text
Available MIDI output ports:
  - ...
```

Confirm the exact Digitone II port name.

## Real-send command

Only run after all safety checks pass.

Replace the port name with the exact port from --list-ports.

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Digitone II" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

One-line form:

```powershell
changes send digitone-syx --syx out/digitone-track8/changes_track8_export.syx --port "Digitone II" --real-send --yes-i-understand-this-writes-to-hardware
```

Expected CLI output:

```text
Guarded real SysEx send completed:
hardware_send: yes
warning: hardware was written
```

## Observed results

Recorded from manual hardware validation:

```text
Dry-run result: success, hardware_send: no (bytes: 114118)
Port list result: Microsoft GS Wavetable Synth 0 / AIO Midi 1 / Elektron Digitone II 2
Real-send result: success, hardware_send: yes, warning: hardware was written
Digitone II observed behavior: いい感じ
Pattern location: A01
Track 8 behavior: Dm7 G7 Cmaj7 progression confirmed; trigger positions are step1, step5, step9
Issues: Confirm LEN interpretation (1/4, 1/4, 1,2) is correct.
```

## Pass criteria

Mark as passed only if:

- dry-run succeeds
- correct Digitone II output port is identified
- guarded real-send exits successfully
- Digitone II receives/imports the SysEx as expected
- Track 8 behavior matches expected export result
- no unintended device or pattern corruption is observed

## Fail criteria

Mark as failed if:

- port cannot be identified unambiguously
- real-send command errors
- Digitone II does not receive/import the SysEx
- wrong device receives data
- Track 8 behavior does not match expected output
- any unexpected destructive behavior occurs

## Final result

```text
Status: Performed
Passed/Failed/Not performed: Passed (with follow-up)
Summary: Guarded real-send succeeded on Digitone II. Pattern A01 and Track 8 Dm7 -> G7 -> Cmaj7 progression were confirmed with trigger positions at step1, step5, and step9.
Follow-up: Verify LEN interpretation (1/4, 1/4, 1,2) and record the exact confirmed values.
```
