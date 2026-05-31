# コンセプト

## 目的

EUB Changes は、楽曲データを Digitone II で machine-live performance に使いやすい NOTE 情報へ変換するための和声変換・生成ツールです。

楽曲データの入力源は次の2種類を想定します。

- **ファイル入力:** iReal Pro / MusicXML 由来のファイル
- **直接入力:** GUI Editor からのコード進行入力

どちらの入力も `SongModel` に変換された後、共通のレンダリングパイプラインを通ります。

## Core Layers

EUB Changes は、楽曲データから machine-live performance に使うための複数のレイヤーを生成します。

- **Cloud:** 文脈に応じた moving six-voice texture
- **Bass:** root movement や slash bass を扱う低音レイヤー
- **Chord:** chord symbol に忠実な vertical six-note layer

これらのレイヤーは、用途に応じて単独でも組み合わせても使えることを前提にしています。

EUB Changes で扱う主要レイヤーと、Digitone II 上の想定対応は次の通りです。

- Track 1-6: Cloud
- Track 7: Bass
- Track 8: Chord

## Design Goals

- **Performance-First:** 楽曲データを、Digitone II で machine-live performance に使いやすい形へ素早く変換します。
- **Layer-Aware:** Cloud / Bass / Chord の各レイヤーを、Digitone II 上で扱いやすい形に整えます。
- **Deterministic:** 同じ input から常に同じ harmony material と出力 artifact を生成し、演奏準備・検証・再現をしやすくします。
- **Musically Informed:** voice-leading、tension selection、bass handling は jazz harmony の概念に基づきます。
- **Safe and Inspectable:** 中間生成物と export / check / dry-run / real-send の境界により、人間が確認できる安全なワークフローを保ちます。

## Core Model Contracts

この章は、パイプラインを理解するうえで必要なモデル契約を扱います。
詳細な schema や実装仕様は、必要になった時点で別文書へ分割します。

### EditorState

目的:

- GUI Editor の入力状態を保持する軽量モデル
- SongModel には UI 状態を保持する責務がないため、Editor 専用のモデルとして分離する

cells フィールドに次のトークンを flat なリストとして格納します。

- chord symbol 文字列（例: `Cmaj7`, `G7`）
- `%` — 直前の有効 chord の繰り返し
- `|` — measure boundary（小節線）
- `||` — section boundary（同時に measure boundary でもある）

変換パス:

```text
EditorState
  -> cells の % を直前 chord へ解決
  -> | / || で measure buffer に分割
  -> || ごとに section label を A -> B -> C... と進める
  -> 空 measure buffer は直前 chord で補填（leading 空 buffer はスキップ）
  -> 各 measure 内の chord cell に均等 duration を割り当て
  -> 連続する同一 chord を merge して HarmonyEvent を生成
  -> SongModel を構築
```

非自明な仕様:

- `%` は「直前の有効 chord cell と同じコード」。直前 chord が存在しない場合は `ValueError`。
- 空 measure（`| |` のような連続 barline）は直前 chord で補填する。
- 末尾の trailing `|` は余分な measure を作らない。
- `%` は小節単位の繰り返しではなく、chord cell 単位の繰り返しである。

entrypoint:

- `changes.editor.editor_to_song.editor_to_song_model`

### SongModel YAML v1

目的:

- Chord export CLI（Digitone Track 8）へ渡す現行の安定入力フォーマット

現在カバーする項目:

- title
- working_key
- performance_tempo
- measures
- meter
- harmony events

現在カバーしない項目:

- arrangement metadata beyond current SongModel
- multi-device export settings
- EditorState（GUI 入力状態は EditorState が保持し、SongModel は保持しない）
- Digitone-specific export profile settings
- MIDI send settings
- audio settings
- arbitrary future project state

フォーマット:

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

必須 top-level fields:

- version
- type
- title
- working_key
- performance_tempo
- measures

必須 measure fields:

- number
- section_id
- meter
- absolute_start_quarters
- harmony

必須 harmony fields:

- id
- symbol
- offset_quarters
- duration_quarters

`HarmonyEvent.measure_number` は parent `measure.number` から推論されます。

Fraction policy:

- quarter-based values と tempo は integer または rational string を使う
- float は入力と dump の両方で使わない

互換契約:

- version: 1
- type: changes.song

### RenderProfile

目的:

- レンダリング時の音楽的パラメータを保持する設定モデル

trigger policy フィールド（layer ごとに独立して設定可能）:

| フィールド | デフォルト | 意味 |
| --- | --- | --- |
| `cloud_trigger_policy` | `hold_until_change` | 同一 voice で同一 pitch が連続・隣接する場合は merge |
| `bass_trigger_policy` | `hold_until_change` | 同上 |
| `chord_trigger_policy` | `retrigger` | occurrence ごとに必ず新規 trigger を出す |

値は `"hold_until_change"` と `"retrigger"` の2種類です。

trigger policy の適用タイミング:

- `render_arrangement()` は layer 素材を生成するだけで trigger 処理を行わない
- trigger policy は `flatten_arrangement_to_timeline()` において `RenderedArrangement` から `RenderedTimeline` へ変換するときに適用する
- `RenderedArrangement` は rich な layer 構造の正本であり、`RenderedTimeline` は export 用に平坦化されたイベント列である

`hold_until_change` のマージ条件:

- 同一 voice_id かつ同一 note_midi かつ時間的に連続（前イベントの終端 == 次イベントの開始）の場合、1つの長いイベントに merge する
- merge されたイベントの `retrigger` フィールドは `False`（hold であることを示す）
- pitch が変わる場合や時間的に連続しない場合は merge しない

デフォルト生成:

- `changes.models.render_profile.default_render_profile`

### RenderedArrangement Contract

`RenderedArrangement` は `RenderedHarmonyOccurrence` の集合です。

各 occurrence の基準情報:

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

entrypoint:

- `changes.rendering.arrangement_renderer.render_arrangement`

flatten adapter:

- `changes.rendering.arrangement_flattener.flatten_arrangement_to_timeline`
- `render_profile` パラメータで trigger policy を受け取り、layer ごとに適用する
- `hold_until_change` layer: 隣接同一 pitch を merge、merge 結果は `retrigger=False`
- `retrigger` layer: occurrence ごとに独立したイベントを生成、`retrigger=True`

flatten 時の role mapping:

- cloud -> `role=cloud`
- chord -> `role=chord`
- bass -> `role=bass`

注意:

- `RenderedTimeline` は flat event と optional velocity を保持するが、layer payload 全体（length_mode, diagnostics, grouping など）は保持しない
- richer metadata が必要な downstream は `RenderedArrangement` を直接参照する

### DigitoneTargetProfile

目的:

- 生成された素材を Digitone に配置するための設定モデル

routing 構造（layer 別 voice → track マッピング）:

```python
routing = {
    "cloud": LayerRouting(voices={
        "cloud_voice_1": VoiceRouting(track=1),
        ...
    }),
    "bass": LayerRouting(voices={
        "bass": VoiceRouting(track=7),
    }),
    "chord": LayerRouting(voices={
        "chord_note_1": VoiceRouting(track=8),
        ...
    }),
}
```

`voice_to_track` プロパティは後方互換のために `routing` から自動生成されます。

役割分担の基本方針:

- `RenderProfile` — 「どんな音楽素材を生成するか」（range、voice-leading、trigger policy）
- `DigitoneTargetProfile` — 「生成された素材を Digitone にどう配置するか」（track routing、velocity、device constraints）

### Track8ChordEvent Contract

変換パス:

- `RenderedArrangement.chord -> Track8ChordEvent`

このモデルは SysEx を書かず、`digitone-syx-toolkit` も呼びません。

理由:

- Chord export（Digitone Track 8）は `RenderedArrangement.occurrences[*].chord` を直接消費する必要がある
- legacy `RenderedTimeline role="chord"` は旧 Cloud 系を表す場合があり安全ではない

Core model:

- `Track8ChordNote`
- `Track8ChordEvent`
- `extract_track8_chord_events(arrangement, track_index_0based=7)`

Constants:

- `TRACK8_INDEX_0BASED = 7`
- `TRACK8_MAX_NOTES_PER_STEP = 16`
- Changes Chord v1 note count per onset: exactly 6

Data preservation rules:

- chord occurrence ごとに `Track8ChordEvent` を1つ生成
- note order は `occurrence.chord.notes` を保持し再ソートしない
- velocity は `occurrence.chord.velocities` を保持
- length mode は `explicit_event_length` / `inherit` を保持
- note `micro_timing` は全て `0`
- diagnostics は `occurrence.diagnostics + occurrence.chord.diagnostics`

Validation rules（`ValueError`）:

- target track が Track 8 でない（`track_index_0based != 7`）
- chord note count が6でない
- chord note count が16を超える
- velocity count と note count が一致しない
- velocity が `1..127` の範囲外
- note MIDI が `0..127` の範囲外

## Core Concepts and Terms

### EUB Changes

EUBシリーズ向けの和声変換・生成ツール。

楽曲データをもとに、Digitone II で machine-live performance に使う NOTE 情報、出力 artifact、検証フローを扱う。

### Editor / EditorState

EUB Changes の GUI 入力インターフェース。

ユーザーがコード進行を直接入力して `SongModel` に変換できる画面。iReal Pro や MusicXML を介さない直接入力経路を提供する。

`EditorState` は Editor の GUI 入力状態を保持する軽量モデルで、chord symbol・`%`・`|`・`||` のトークンを flat なリストとして保持し、cursor 位置と undo 履歴を管理する。詳細は Core Model Contracts の EditorState 節を参照。

### Cloud

Changes の主要レイヤー。

文脈に応じた moving six-voice texture を指します。Digitone II では主に Track 1-6 に対応します。

Cloud は、EUB Changes における主要な演奏レイヤーです。

### Harmony Cloud

Cloud の正式または説明的な呼称。

単なる効果音的な cloud ではなく、和声文脈に基づく six-voice harmony texture であることを明示したい場合に使います。

### Bass

Changes の低音レイヤー。

slash bass がある場合はそれを優先し、ない場合は chord root を基準にします。Digitone II では主に Track 7 に対応します。

Bass は low register を担う grounding layer です。

### Chord

Changes の和音レイヤー。

symbol-faithful な vertical six-note layer を指します。Cloud のような moving texture ではなく、chord symbol に対して垂直的に構成された和音情報を扱います。

### Track 1-6

Digitone II 上で Cloud を配置する主トラック群。

six-voice harmony texture の各声部に対応する想定の performance layer です。

### Track 7

Digitone II 上で Bass を配置する想定のトラック。

root movement や slash bass を扱う grounding layer です。

### Track 8

Digitone II 上で Chord を配置するトラック。

現在の RC-stabilized subset では、主に Chord export / check / dry-run / guarded real-send（Digitone Track 8）の検証が進んでいます。

### Chord workflow（Digitone Track 8）

Chord layer を Digitone II の Track 8 へ出力する現在の安定化済み subset。

EUB Changes の現在の RC workflow では、この Chord workflow（Digitone Track 8）に関する export / check / dry-run / guarded real-send が先行して整備されています。

### RC / Release Candidate

Release Candidate の略。

EUB Changes では、正式リリースではないが、一定の実用・検証フローとして候補扱いできる段階を指します。

現在の文脈で RC と言う場合、多くは Chord の export / check / dry-run / guarded real-send workflow（Digitone Track 8）を指します。これは EUB Changes 全体が完成間近であるという意味ではありません。

### RC-stabilized subset

EUB Changes 全体のうち、現在比較的安定して検証されている一部分。現在は主に Chord workflow（Digitone Track 8）を指します。

RC-stabilized subset は、レイヤー構成とは別軸で扱います。安定化済みであることは、その機能が主機能であることを意味しません。

### SongModel

Changes の入力・内部変換の基準となる楽曲モデル。

楽曲タイトル、key、tempo、measure、harmony などを保持します。SongModel YAML v1 はファイル入力フォーマット。

### RenderedArrangement

Cloud / Chord / Bass の layer 構造を保持する中間表現。

RenderedTimeline よりも rich な metadata を保持し、layer ごとの情報、grouping、diagnostics などを扱うための基準となります。

### RenderedTimeline

flat event 向けの中間表現。

RenderedArrangement と異なり、layer payload 全体、grouping、diagnostics などの rich metadata は保持しません。Track 8 Chord の compile に必要な optional velocity は保持します。trigger policy が適用済みの状態を表します。

### SysEx

MIDI System Exclusive メッセージ。EUB Changes では、Digitone II へ pattern data を転送するために使います。

### dry-run

実機へ書き込まず、送信内容や条件だけを検証する実行モード。

### real-send

実機へ実際に SysEx を送信する実行モード。

### guarded real-send

明示フラグと確認を要求する安全境界付き real-send。

### 中間生成物 / intermediate artifact

Changes の処理途中で生成されるデータ群。

最終成果物である .syx などに至るまでの内部表現や中間 artifact を指します。中間生成物は検証やデバッグに有用ですが、原則として仕様の正本ではありません。
