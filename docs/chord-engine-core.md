# Chord Engine Core

This document describes the Phase 1 Chord Engine work for Changes.

## Engine separation

Changes now has three conceptual musical layers:

- Cloud: the existing context-aware six-voice harmonic layer.
- Chord: the new conventional chord-symbol-faithful six-note layer.
- Bass: the existing slash-bass-or-root layer.

This phase only implements the pure Chord construction core. It does not change Cloud rendering, Bass behavior, Digitone export, MIDI export, or any generated artifacts.

## Phase 1 scope

Phase 1 stops at pitch-class construction:

- parse and normalize chord symbols
- preserve mandatory chord-symbol tones
- fill remaining voices with deterministic tensions from the selected Local Pitch Collection
- return diagnostics for later renderer integration

It does not choose MIDI octaves, register, velocity, length, Track 8 slots, or export format details.

## Chord construction rule

Chord construction follows three rules:

1. Keep the tones explicitly written by the chord symbol.
2. Add only tensions that exist in the selected Local Pitch Collection.
3. Stop once six distinct pitch classes are available, or raise a clear error if six cannot be reached.

Explicit alterations such as `b9` or `#9` are preserved as mandatory chord content.

For symbol-faithful Chord output, a written `b9`/`#9`/`#11`/`b13` suppresses automatic addition of conflicting variants in the same extension family. The general `alt` quality remains exempt because it intentionally represents compound altered color.

## Integration warning

Chord automatic tension filling must consume the selected ScaleCollection pitch classes, not the local constraint pitch-class set used during scale selection.

In the current harmonic context model:

- use `RetryResolution.selected_collection.pitch_classes`
- do not use `RetryResolution.local_pitch_collection`
- do not use `RetryResolution.final_local_pitch_collection_used_for_selection`

The local constraint set is used to choose a scale. It does not necessarily contain the available tensions needed to complete a six-note chord output.

## Plain sus4 convention

Changes treats plain `sus4` as dominant-suspended harmony in the jazz-chart context.

- `Csus4` normalizes to `C7sus4`
- existing `C7sus4`, `C9sus4`, and `C7b9sus4` forms remain supported

## Later work

Future phases can add:

- register realization
- Track 8 output
- VEL policy
- LEN policy
- renderer integration
- Digitone export integration

This document intentionally does not claim that Track 8 output already exists in Changes.