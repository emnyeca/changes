# Rendered Arrangement Integration (Phase 3B)

## Summary

Phase 3B adds arrangement rendering from SongModel into RenderedArrangement.
RenderedArrangement is now the structured intermediate model for layer-aware outputs.

In this phase:
- Chord Engine is connected to RenderedArrangement.
- Existing RenderedTimeline behavior is unchanged.
- Existing export paths remain unchanged.

## What Is Implemented

A new renderer entrypoint is available:
- changes.rendering.arrangement_renderer.render_arrangement

The function:
- Accepts SongModel and optional RenderProfile.
- Produces one RenderedHarmonyOccurrence per source harmony occurrence.
- Preserves source_harmony_id, symbol, onset_quarters, and duration_quarters.
- Builds the Chord layer using:
  - construct_chord_pitch_classes
  - realize_chord_register
- Emits six chord notes with lane IDs chord_note_1..chord_note_6.
- Preserves Chord layer realization payload:
  - source_pitch_classes
  - canonical_stacked_midi_notes
  - realized_midi_notes
  - velocities
  - length_mode
  - diagnostics

## Scope Boundaries

Not implemented in Phase 3B:
- Editor integration
- Digitone Track 8 export integration
- MIDI export changes
- Replacement of existing timeline renderer behavior
- Flattening RenderedArrangement into RenderedTimeline

Cloud and Bass population are intentionally deferred in this phase.

## Notes for Next Phases

- Phase 3C can add explicit flattening from RenderedArrangement to RenderedTimeline.
- Exporters can then consume either flattened events or layer-aware arrangement data as needed.
