# Rendered Arrangement Model

This document introduces `RenderedArrangement`, a structured intermediate representation for the Changes engine. Unlike the existing `RenderedTimeline`, which is a flat list of note events, a rendered arrangement is organised per harmony occurrence and groups the outputs of different rendering engines into layers.

## Motivation

The Changes engine now has three independent rendering engines: Cloud (context‑aware moving voices), Chord (symbol‑faithful six‑note chords) and Bass (root/slash bass). Flattening their outputs prematurely loses the relationship between notes that belong to the same chord trigger or harmony occurrence. In particular, the Track 8 export workflow needs to know that six notes belong to one chord event.

## Structure

A rendered arrangement consists of a collection of `RenderedHarmonyOccurrence` objects. Each harmony occurrence carries:

- The identifier of the source harmony from the song model.
- The chord symbol and timing (onset and duration) as `Fraction` values in quarter notes.
- Optional `RenderedCloudLayer`, `RenderedChordLayer` and `RenderedBassLayer` objects.
- Optional diagnostic strings.

Each layer groups notes from the corresponding engine:

- **RenderedCloudLayer**: up to six moving voices from the Cloud engine, including lane identifiers (`cloud_voice_1`, etc.) and per‑note diagnostics.
- **RenderedChordLayer**: the six notes produced by the chord engine, along with their pitch classes, stacked and realised MIDI values, velocity profile and length mode. These values come from `ChordRealizationResult` and are preserved for later Track 8 rendering.
- **RenderedBassLayer**: a single bass note, its pitch class and optional diagnostics.

All note objects are instances of `RenderedLayerNote` and carry only stable attributes: `note_midi`, optional `velocity`, optional `lane_id`, optional `degree_label` and optional diagnostics. Fractions are used for temporal values to preserve exact durations.

## Comparison with `RenderedTimeline`

`RenderedTimeline` is still used to flatten musical data into per‑note events for exporting to MIDI, the Digitone or other synthesizers. It does not encode group or engine information; it simply assigns each note a voice and role. By contrast, `RenderedArrangement` preserves higher‑level structure:

- Notes belonging to the same chord trigger stay together in the chord layer.
- Cloud and chord outputs are kept separate, avoiding confusion over the meaning of `role="chord"` in the existing timeline.
- Future exporters and renderers can decide how to handle each layer appropriately without guessing.

The arrangement model is not a MIDI or Digitone file. It is an intermediate representation that can be converted to a `RenderedTimeline` or directly to a hardware-specific format in later phases.

## Future phases

Phase 3B will implement an arrangement renderer that builds a `RenderedArrangement` from a `SongModel` and the outputs of the Cloud, Chord and Bass engines. Phase 3C will provide functions to flatten a rendered arrangement into a `RenderedTimeline` or other event-specific representations. Phase 4 will handle the Track 8/Digitone export, using the grouping information preserved in the chord layer. The existing renderer and export modules remain unchanged in Phase 3A.
