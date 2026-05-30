# Rendered Arrangement Flattening (Phase 3C)

## Why This Adapter Exists

rendering pipeline には現在、structured かつ layer-aware な intermediate model があります。

SongModel -> RenderedArrangement

既存 exporter の多くは flat event model に依存しています。

RenderedTimeline

Phase 3C では、この 2 つの model を安全に共存させるため explicit adapter を追加します。

RenderedArrangement -> RenderedTimeline

## Model Roles

- RenderedArrangement: harmony occurrence と layer（cloud/chord/bass）で group 化された structured representation
- RenderedTimeline: 既存 export path 互換のための flat note event sequence

## Scope of This Phase

このフェーズで追加するのは structural flatten adapter のみです。

- changes.rendering.arrangement_flattener.flatten_arrangement_to_timeline

既存 timeline renderer は置き換えません。
MIDI export、Digitone export、bundle planning、UI behavior は変更しません。

## Flatten Semantics

各 RenderedHarmonyOccurrence について次を適用します。

- Cloud notes map to role=cloud events.
- Chord notes map to role=chord events.
- Bass note maps to one role=bass event.

生成される各 event は次を保持します。

- source_harmony_id
- onset_quarters
- duration_quarters
- note_midi

Events are emitted with retrigger=True.

deterministic sorting は次の順序で適用します。

1. onset_quarters
2. role order (cloud, chord, bass, unknown)
3. voice_id
4. id

## Current Limitation

RenderedTimeline は現時点で RenderedArrangement の per-note / per-layer payload 全体を保持しません。例:

- velocity
- length_mode
- diagnostics
- grouping metadata

これらの metadata は RenderedArrangement 側に保持され、後続フェーズで利用する前提です。

## Forward Compatibility

- 将来の Track 8 export は chord grouping と per-note policy data が保持される RenderedArrangement の直接利用を優先すべきです。
- Generic MIDI export は flattening 経由で RenderedTimeline を継続利用するか、後続フェーズで richer model へ移行できます。
