# Hardware Validation: Simple ii-V-I Native SysEx Pipeline

- Date: 2026-05-26
- Device: Elektron Digitone II

## Input

- Compact Progression: Simple ii-V-I
- Tempo: 120 BPM
- Time Signature: 4/4

## Compiled Pattern

- Digitone Device Tempo: 240.0
- Speed: 1/8
- Total Steps: 4
- Tracks Used: 1-7

## Verified

- generated .syx imported successfully on hardware
- note octave mapping is correct
- chord-cloud transitions are audible as intended
- bass movement D -> G -> C is correct
- timing corresponds to external musical tempo
- finite Length codes play without apparent blocking issue

## Artifacts

- song_model.json
- rendered_timeline.json
- digitone_compile_plan.json
- digitone.events.yaml
- digitone_pattern.syx

Generated artifact directory:

- examples/generated/simple_ii_v_i/

## Status

First end-to-end hardware validation succeeded.
