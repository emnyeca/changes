# Digitone SysEx Real-send Workflow

## Current status

Guarded real-send has been manually validated on Digitone II.

Validated fixture:

- `examples/song_models/demo_ii_v_i.changes.yaml`
- Pattern location observed: `A01`
- Track 8 progression confirmed:
- Dm7 at step1
- G7 at step5
- Cmaj7 at step9

## Safety boundary

Export does not send.

Real-send requires:

- explicit `.syx`
- explicit `--port`
- `--real-send`
- `--yes-i-understand-this-writes-to-hardware`

## Standard workflow

### 1. Install MIDI extras

```powershell
python -m pip install -e ".[midi]"
```

### 2. Check versions

```powershell
python --version
python -c "import importlib.metadata as md; print('mido', md.version('mido'))"
python -c "import importlib.metadata as md; print('python-rtmidi', md.version('python-rtmidi'))"
```

### 3. Export `.syx`

```powershell
changes export digitone-track8 `
  --input examples/song_models/demo_ii_v_i.changes.yaml `
  --output-dir out/digitone-track8 `
  --basename changes_track8_export `
  --overwrite
```

### 4. Confirm SysEx envelope

```powershell
python -c "from pathlib import Path; b=Path('out/digitone-track8/changes_track8_export.syx').read_bytes(); print(len(b), hex(b[0]), hex(b[-1]))"
```

### 5. List ports

```powershell
changes send digitone-syx --list-ports
```

### 6. Dry-run

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --dry-run
```

### 7. Guarded real-send

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

## Known validated environment

From first validation:

```text
Date: 2026-05-30
OS: Windows PowerShell
Python: 3.14.5
mido: 1.3.3
python-rtmidi: 1.5.8
Digitone II firmware: 1.10D
Port selected: Elektron Digitone II 2
```

## Non-goals

This workflow does not:

- send from export
- auto-select ports
- bypass confirmation
- guarantee all future fixtures
- validate every possible LEN mapping
