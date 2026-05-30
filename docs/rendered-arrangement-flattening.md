# Rendered Arrangement Flattening (Phase 3C)

## Why This Adapter Exists

The rendering pipeline now has a structured, layer-aware intermediate model:

SongModel -> RenderedArrangement

Most existing exporters currently depend on the flat event model:

RenderedTimeline

Phase 3C adds an explicit adapter so these two models can coexist safely:

RenderedArrangement -> RenderedTimeline

## Model Roles

- RenderedArrangement: structured representation grouped by harmony occurrence and layer (cloud/chord/bass).
- RenderedTimeline: flat sequence of note events for compatibility with existing export paths.

## Scope of This Phase

This phase adds only a structural flatten adapter:

- changes.rendering.arrangement_flattener.flatten_arrangement_to_timeline

It does not replace the existing timeline renderer.
It does not change MIDI export, Digitone export, bundle planning, or UI behavior.

## Flatten Semantics

For each RenderedHarmonyOccurrence:

- Cloud notes map to role=cloud events.
- Chord notes map to role=chord events.
- Bass note maps to one role=bass event.

Each generated event preserves:

- source_harmony_id
- onset_quarters
- duration_quarters
- note_midi

Events are emitted with retrigger=True.

Deterministic sorting is applied by:

1. onset_quarters
2. role order (cloud, chord, bass, unknown)
3. voice_id
4. id

## Current Limitation

RenderedTimeline does not currently carry the full per-note and per-layer payload from RenderedArrangement, including:

- velocity
- length_mode
- diagnostics
- grouping metadata

That metadata remains available in RenderedArrangement and is intentionally preserved there for later phases.

## Forward Compatibility

- Future Track 8 export should prefer consuming RenderedArrangement directly because chord grouping and per-note policy data are preserved there.
- Generic MIDI export can continue to consume RenderedTimeline via flattening, or move to richer models in later phases.
