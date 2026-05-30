# Track 8 Toolkit SysEx Generation (Phase 4F)

## Purpose

This phase adds an explicit software-only function that generates SysEx bytes
through digitone-syx-toolkit from toolkit-loadable events YAML text.

## Scope Boundary

This phase does not include:

- hardware send
- MIDI port access
- bundle planner integration
- UI integration
- automatic export in existing workflows
- hard runtime dependency on digitone-syx-toolkit

## Toolkit API Inspection Summary

Inspected toolkit files:

- digitone-syx-toolkit/src/digitone_syx_toolkit/events_yaml.py
- digitone-syx-toolkit/src/digitone_syx_toolkit/events_to_syx.py
- digitone-syx-toolkit/src/digitone_syx_toolkit/cli.py
- digitone-syx-toolkit/tests/test_events_to_syx.py
- digitone-syx-toolkit/tests/test_events_yaml.py
- digitone-syx-toolkit/README.md

Chosen integration path:

- load YAML path via toolkit loader path inside build flow
- call digitone_syx_toolkit.events_to_syx.build_syx_from_events(
    events_yaml=..., output_file=..., template_file=None
  )
- read generated temporary .syx file bytes and return bytes

Observed behavior:

- toolkit build API is file-path based, not direct bytes return
- build function returns BuildResult and writes output file
- no hardware send is required for this software generation path
- generation can be done entirely locally from events YAML

## Input and Output

Input:

- toolkit-loadable events YAML text

Output:

- bytes containing generated SysEx data

## Lazy Toolkit Import

Toolkit import is performed only inside:

- generate_track8_sysex_bytes_with_toolkit(yaml_text)

If toolkit is unavailable, the function raises a clear RuntimeError.

## Local Setup

From D:\emnye\Documents\GitHub\changes:

python -m pip install -e .
python -m pip install -e ..\digitone-syx-toolkit
python -m pytest tests/test_track8_sysex_export.py -q

Alternative with py launcher:

py -m pip install -e .
py -m pip install -e ..\digitone-syx-toolkit
py -m pytest tests/test_track8_sysex_export.py -q

## Expected Cmaj7 Contract

For the full Changes Track 8 Cmaj7 path, generated SysEx is validated as:

- non-empty bytes
- first byte is 0xF0
- last byte is 0xF7

This phase does not claim hardware import/send success.

## CI Policy

Toolkit-dependent tests are optional and skipped when toolkit is not installed.
No GitHub Actions workflow change is included in this phase.

## Next Phase

Safer next step:

- Phase 4G: write SysEx fixture artifacts for hardware validation

Alternative:

- Phase 4G: add explicit CLI command for Track 8 chord SysEx file export
