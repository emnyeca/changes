# SongModel YAML v1

## Purpose
SongModel YAML v1 is the first stable input format for future Track 8 export CLI input.

## Scope
This format currently covers:

- title
- working key
- performance tempo
- measures
- meter
- harmony events

It does not cover:

- arrangement metadata beyond current SongModel
- multi-device export settings
- UI/editor state
- Digitone-specific export profile settings
- MIDI send settings
- audio settings
- arbitrary future project state

## Format
```yaml
version: 1
type: changes.song
title: Demo Cmaj7
working_key: C
performance_tempo: 120
measures:
  - number: 1
    section_id: A
    meter: 4/4
    absolute_start_quarters: 0
    harmony:
      - id: h1
        symbol: Cmaj7
        offset_quarters: 0
        duration_quarters: 4
```

Required top-level fields:

- version
- type
- title
- working_key
- performance_tempo
- measures

Required measure fields:

- number
- section_id
- meter
- absolute_start_quarters
- harmony

Required harmony fields:

- id
- symbol
- offset_quarters
- duration_quarters

HarmonyEvent.measure_number is inferred from parent measure.number.

## Fraction policy
Quarter-based values and tempo use integers or rational strings.

Examples:

- 0
- 4
- "1/2"
- "3/2"

Values are parsed into fractions.Fraction.

Floats are avoided in both input policy and dumped YAML.

## Relationship to Track 8 export
SongModel YAML v1 can feed build_track8_export_yaml_payload_from_song.

Track 8 developer CLI accepts this format via --input.

Example:

```bash
changes export digitone-track8 --input examples/song_models/demo_cmaj7.changes.yaml --output-dir out/digitone-track8 --events-yaml-only
```

The command still does not send MIDI.

## Multi-chord example

A small II-V-I example is available at:

examples/song_models/demo_ii_v_i.changes.yaml

It demonstrates multiple harmony events inside one measure with different offsets and durations.

## Compatibility policy
Current format contract:

- version: 1
- type: changes.song

Future incompatible changes should increment version.

## Next phase
Recommended next phase:

Phase 5E: Add --input SongModel YAML mode to Track 8 export CLI
