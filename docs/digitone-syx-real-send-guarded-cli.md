# Digitone SysEx Guarded Real-send CLI

## Purpose

This document describes the guarded real-send path for `.syx` files.

## Commands

Dry run:

```bash
changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II" \
  --dry-run
```

List ports:

```bash
changes send digitone-syx --list-ports
```

Guarded real send:

```bash
changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II" \
  --real-send \
  --yes-i-understand-this-writes-to-hardware
```

## Safety

Real send is never implicit.

Export does not send.

Real send requires explicit confirmation.

## Requirements

Real send requires optional MIDI dependencies:

```bash
pip install .[midi]
```

## Risks

SysEx may write pattern/device data.

Back up important Digitone II data before testing.

## Recommended validation sequence

1. Generate `.syx`.
2. Run dry-run.
3. List ports.
4. Confirm correct port.
5. Confirm device backup.
6. Run guarded real-send.
7. Record hardware validation result.

Use docs/hardware-validation/digitone-syx-real-send-first-validation.md for the first manual validation checklist and status log.
