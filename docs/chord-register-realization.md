# Chord Register Realization (Phase 2)

This document describes Phase 2 of the independent Chord engine in Changes.

## Separation from Cloud

Chord is a vertical chord layer and is distinct from Cloud moving voices.

- Cloud: context-aware moving six-voice texture with continuity across events.
- Chord (Phase 2): independent per-occurrence vertical realization from pitch classes.

This phase does not use Cloud voice-lane continuity or previous-chord minimum-motion repair.

## Register

Chord register is fixed to MIDI `48..69`.

- `48` = Digitone display `C4`
- `69` = Digitone display `A5`

All realized Chord notes must remain inside this range.

## Realization algorithm

The realization algorithm is deterministic:

1. stack
2. octave-fold
3. ascending-sort

### 1) Stack

Use `ChordConstructionResult.final_pitch_classes` order as the chord stacking order.

- First note: lowest matching MIDI at or above register minimum.
- Following notes: lowest matching MIDI strictly above the previous stacked note.

### 2) Octave-fold

For each stacked note above register maximum, subtract 12 until it fits.

- Pitch class is preserved.
- No chromatic substitution.

### 3) Ascending-sort

Sort folded notes in ascending MIDI order and return six distinct notes.

If six distinct in-range notes cannot be produced, realization raises an explicit error.

## Root-position preservation and inversion behavior

If the canonical stack already fits, it is preserved.
If not, octave folding may create an inversion as a deterministic result of register bounds.

## Velocity policy (modeled)

Phase 2 models a low-to-high per-note profile:

- `70, 70, 70, 50, 70, 50`

Velocities are assigned after final ascending MIDI sort.

This is not Cloud lane identity and is not track assignment.

## Length policy (modeled)

Phase 2 models the Chord length mode only:

- `explicit_event_length`
- `inherit`

No duration-to-event conversion is performed in this phase.

## Deferred integration

The following remain deferred:

- Renderer integration
- Track 8 output mapping
- MIDI export integration
- Digitone export integration
- bundle planning / trigger capacity integration
