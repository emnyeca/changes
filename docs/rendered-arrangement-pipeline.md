# Rendered Arrangement Pipeline

## 位置づけ

この文書は `RenderedArrangement` 系の設計・統合・flattening 方針を一元化した開発者向け正本です。

## 目的

`RenderedTimeline` だけでは保持しづらい layer 構造を、`RenderedArrangement` で保持し、必要に応じて flat event へ変換可能にする。

主な狙い:

- Cloud / Chord / Bass の責務を分離して保持
- chord grouping（1 occurrence 内の 6 note）を lossless に扱う
- Track 8 export 等で必要な per-note policy / diagnostics を保持

## モデル

`RenderedArrangement` は `RenderedHarmonyOccurrence` の集合で構成される。

各 occurrence は次を保持する:

- source_harmony_id
- chord symbol
- onset_quarters / duration_quarters（Fraction）
- optional layer: `cloud` / `chord` / `bass`
- optional diagnostics

layer ごとの要点:

- `RenderedCloudLayer`
  - moving voice（`cloud_voice_n`）
- `RenderedChordLayer`
  - source pitch class
  - canonical stack / realized MIDI
  - velocity profile / length mode
- `RenderedBassLayer`
  - single bass note と source pitch class

## 統合

entrypoint:

- `changes.rendering.arrangement_renderer.render_arrangement`

実装境界:

- SongModel から occurrence 単位で arrangement を生成
- Chord layer を優先接続
- 既存 `RenderedTimeline` の挙動は置換しない
- exporter や UI の既存パスはこの段階で変更しない

## Flattening

adapter:

- `changes.rendering.arrangement_flattener.flatten_arrangement_to_timeline`

変換ルール:

- cloud -> `role=cloud`
- chord -> `role=chord`
- bass -> `role=bass`

保持する情報:

- source_harmony_id
- onset_quarters
- duration_quarters
- note_midi

注意:

- `RenderedTimeline` は layer payload 全体（velocity, length_mode, diagnostics, grouping）を保持しない
- richer metadata が必要な downstream は `RenderedArrangement` を直接参照する

## Naming migration（Cloud/Chord role）

legacy timeline では context-aware six-voice が `role="chord"` として扱われる領域がある。

移行方針:

- 即時 rename は避ける
- compatibility staging を前提に進める
- 既存テスト / fixture / exporter 依存を壊さない

この方針により、単純 rename ではなく段階的移行（dual handling -> default switch -> deprecate）を採用する。

## 関連

- `docs/voicing-and-duration-rules.md`
- `docs/track8-chord-event-model.md`
- `docs/track8-export-api.md`
- `docs/validation-status.md`