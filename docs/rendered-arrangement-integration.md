# Rendered Arrangement Integration (Phase 3B)

## Summary

Phase 3B では SongModel から RenderedArrangement への arrangement rendering を追加します。
RenderedArrangement は layer-aware output のための structured intermediate model です。

このフェーズでは次を実施します。
- Chord Engine を RenderedArrangement に接続する。
- 既存 RenderedTimeline の behavior は変更しない。
- 既存 export path は変更しない。

## What Is Implemented

新しい renderer entrypoint:
- changes.rendering.arrangement_renderer.render_arrangement

この関数は次を行います。
- SongModel と optional RenderProfile を受け取る。
- source harmony occurrence ごとに 1 つの RenderedHarmonyOccurrence を生成する。
- source_harmony_id、symbol、onset_quarters、duration_quarters を保持する。
- Chord layer を次で構築する。
  - construct_chord_pitch_classes
  - realize_chord_register
- lane ID `chord_note_1..chord_note_6` で 6 chord note を出力する。
- Chord layer realization payload を保持する。
  - source_pitch_classes
  - canonical_stacked_midi_notes
  - realized_midi_notes
  - velocities
  - length_mode
  - diagnostics

## Scope Boundaries

Phase 3B では未実装:
- Editor integration
- Digitone Track 8 export integration
- MIDI export changes
- Replacement of existing timeline renderer behavior
- Flattening RenderedArrangement into RenderedTimeline

Cloud と Bass の population は意図的に deferred とします。

## Notes for Next Phases

- Phase 3C で RenderedArrangement から RenderedTimeline への explicit flattening を追加できます。
- その後 exporter は必要に応じて flattened event または layer-aware arrangement data を消費できます。
