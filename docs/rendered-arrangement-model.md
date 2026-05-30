# Rendered Arrangement Model

この文書では、Changes engine の構造化中間表現 `RenderedArrangement` を説明します。既存の `RenderedTimeline` は flat な note event 列ですが、RenderedArrangement は harmony occurrence 単位で整理され、複数 rendering engine の出力を layer ごとに保持します。

## Motivation

Changes engine には Cloud（context-aware moving voices）、Chord（symbol-faithful six-note chord）、Bass（root/slash bass）の 3 つの独立 rendering engine があります。これらの出力を早い段階で flat 化すると、同じ chord trigger / harmony occurrence に属する note の関係が失われます。特に Track 8 export workflow では、6 note が 1 chord event に属することを保持する必要があります。

## Structure

rendered arrangement は `RenderedHarmonyOccurrence` の集合で構成されます。各 harmony occurrence は次を持ちます。

- The identifier of the source harmony from the song model.
- The chord symbol and timing (onset and duration) as `Fraction` values in quarter notes.
- Optional `RenderedCloudLayer`, `RenderedChordLayer` and `RenderedBassLayer` objects.
- Optional diagnostic strings.

各 layer では対応する engine の note を group 化します。

- **RenderedCloudLayer**: Cloud engine の最大 6 moving voices。lane identifier（`cloud_voice_1` など）と per-note diagnostics を含みます。
- **RenderedChordLayer**: chord engine が生成した 6 note。pitch class、stacked/realized MIDI value、velocity profile、length mode を保持します。これらは `ChordRealizationResult` 由来で、後続の Track 8 rendering に維持されます。
- **RenderedBassLayer**: 単一 bass note、その pitch class、optional diagnostics。

すべての note object は `RenderedLayerNote` で表され、`note_midi`、optional `velocity`、optional `lane_id`、optional `degree_label`、optional diagnostics という stable attribute のみを持ちます。時間値は正確な duration 保持のため Fraction を使用します。

## Comparison with `RenderedTimeline`

`RenderedTimeline` は MIDI / Digitone / その他 synthesizer への export のために、音楽データを per-note event へ flat 化する用途で引き続き使います。group 情報や engine 情報は持たず、各 note に voice と role を割り当てるだけです。対して `RenderedArrangement` は上位構造を保持します。

- Notes belonging to the same chord trigger stay together in the chord layer.
- Cloud and chord outputs are kept separate, avoiding confusion over the meaning of `role="chord"` in the existing timeline.
- Future exporters and renderers can decide how to handle each layer appropriately without guessing.

arrangement model は MIDI file や Digitone file そのものではありません。後続フェーズで `RenderedTimeline` または hardware-specific format に変換するための intermediate representation です。

## Future phases

Phase 3B では `SongModel` と Cloud/Chord/Bass engine 出力から `RenderedArrangement` を構築する arrangement renderer を実装します。Phase 3C では rendered arrangement を `RenderedTimeline` や event-specific representation に変換する関数を提供します。Phase 4 では chord layer に保持された grouping 情報を利用して Track 8 / Digitone export を扱います。Phase 3A では既存 renderer / export module は変更しません。
