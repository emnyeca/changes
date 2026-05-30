# Fixture Inventory

## Purpose

This inventory captures intended use and current validation scope for SongModel fixtures used by the Digitone II Track 8 RC workflow.

## Fixtures

### Demo Cmaj7

- title: Demo Cmaj7
- file: `examples/song_models/demo_cmaj7.changes.yaml`
- musical shape: single 4/4 measure, one Cmaj7 harmony event
- chord events: 1
- expected Track 8 note rows: 6
- intended validation purpose: quick smoke test for export path and CLI basics
- hardware validation status: not hardware-validated

### Demo II V I

- title: Demo II V I
- file: `examples/song_models/demo_ii_v_i.changes.yaml`
- musical shape: one 4/4 measure with Dm7 -> G7 -> Cmaj7
- chord events: 3
- expected Track 8 note rows: 18
- intended validation purpose: known baseline for export/check/dry-run and guarded real-send workflow
- hardware validation status: hardware-validated on Digitone II (Dm7 step1, G7 step5, Cmaj7 step9)

### Demo Multibar Turnaround

- title: Demo Multibar Turnaround
- file: `examples/song_models/demo_multibar_turnaround.changes.yaml`
- musical shape: two 2/4 measures with four harmony events across bars
- chord events: 4
- expected Track 8 note rows: 24
- intended validation purpose: multi-bar regression for software export/check/dry-run workflow
- hardware validation status: not hardware-validated

### Demo Multisection Form

- title: Demo Multisection Form
- file: `examples/song_models/demo_multisection_form.changes.yaml`
- musical shape: eight 4/4 measures, A section then B section
- chord events: 8
- expected Track 8 note rows: 48
- intended validation purpose: multi-section SongModel export/manifest regression
- hardware validation status: not hardware-validated

## Fixture Selection Guide

- quick smoke test: `demo_cmaj7`
- known hardware-validated path: `demo_ii_v_i`
- multi-bar regression: `demo_multibar_turnaround`
- multi-section regression: `demo_multisection_form`