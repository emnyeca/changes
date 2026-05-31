# Toolkit Integration CI Design

## Purpose

This document defines the current CI policy for toolkit-dependent tests in `changes`.

## Current CI policy

- Core pytest suite runs without requiring toolkit installation.
- Toolkit-dependent tests run in a dedicated integration job.
- Integration job checks out both repositories and installs both packages editable.

## Toolkit-dependent test scope

Current high-value integration checks:

- loader validation of generated events YAML
- SysEx byte generation path
- fixture generation paths that require toolkit behavior

## Job behavior

- run on pull requests
- allow manual dispatch when specific toolkit refs must be checked
- keep normal core test job separate for speed and clarity

## Failure policy

- integration job can start as advisory
- promote to required check when affected export paths become standard product path

## Ref policy

- default toolkit ref may follow main for drift detection
- stabilization/release paths may use pinned ref for reproducibility

## Local workflow

From `changes` repository:

```powershell
python -m pip install -e .
python -m pip install -e ..\digitone-syx-toolkit
python -m pytest tests/test_track8_toolkit_loader_validation.py tests/test_track8_sysex_export.py tests/test_track8_fixture_generation.py tests/test_track8_product_like_fixture_generation.py -q
```

## Scope boundary

This document describes policy and job shape. It does not itself modify workflows or runtime code.
