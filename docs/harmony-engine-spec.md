# Harmony Engine 仕様

## 位置づけ

この文書は Changes の和声形成（harmony formation）に関する内部仕様の正本です。

## scope

本仕様は次を対象にします。

- Chord Symbol から Local Pitch Collection を導出する規則
- Selected Scale Collection の選択規則
- Output Chord Tone Set の抽出規則
- Chord register realization と bounded voice sliding
- slash bass の扱い
- MusicXML import normalization と timing 方針

## layer separation

Changes の概念レイヤー:

- Cloud: context-aware moving six-voice texture
- Chord: symbol-faithful vertical six-note layer
- Bass: slash-bass-or-root low-note layer

本仕様は主に Chord / Bass の生成規則を定義し、Cloud との責務境界を明確にします。

## core principles

- Chord Symbol は Local Pitch Collection 構築の入力。
- Chord Symbol の tension/alteration はそのまま mandatory 出力ではなく、選択 collection 規則に従う。
- Output Chord Tone Set は Selected Scale Collection から deterministic に抽出。
- unresolved context は silent fallback せず explicit error とする。

## Chord construction rules

1. chord symbol に明示された mandatory tone を保持する
2. Selected Scale Collection に含まれる tone のみ追加する
3. 6 distinct pitch class に到達した時点で確定する

補足:

- `b9` / `#9` / `#11` / `b13` は symbol-faithful Chord で conflicting variant の自動追加を抑制
- `alt` は compound altered color を表す semantic directive として例外扱い
- plain `sus4` は dominant-suspended convention で扱う（`Csus4` -> `C7sus4`）

## Collection selection

優先 family:

1. Diatonic / Dorian
2. Harmonic minor
3. Melodic minor / Lydian dominant
4. Whole-tone
5. Diminished

retry policy:

1. `current + previous distinct + next distinct`
2. `current + previous distinct`
3. `current only`

current-only でも解決不能な場合は `UnsupportedHarmonicContextError` を送出する。

### symmetric eligibility

- Whole-tone / Diminished は current chord が altered/symmetric 性を示す場合に限定
- plain major/minor quality は accidental recoloring を防ぐため symmetric selection を許可しない

### hard constituents / color hints

- hard constituents: chord structure を定義する tone（root, 3rd/b3, 5th/altered5, 7th, sus4, slash bass 等）
- color hints: dominant の `b9` / `#9` / `#11` / `b13`
- Attempt 1/2 では color hint を containment 制約に使わず、Attempt 3 current-only で復帰

## register / realization

### Chord

- register: MIDI `48..72`（Digitone display `C4..C6`）
- algorithm: stack -> octave-fold -> ascending-sort
- 6 distinct in-range note を生成できない場合は explicit error

### Bass

- source: slash bass があれば優先、なければ chord signature root
- register: MIDI `36..47`（Digitone display `C3..B3`）

### Cloud

- register: MIDI `48..72`（Digitone display `C4..C6`）
- Cloud range は Chord range と別フィールドで管理する

### bounded voice sliding

- six-lane voice-leading 後の vector に boundary repair を適用
- voice crossing を許可
- final lane assignment を pitch sort で強制しない
- pitch-class multiset と six-lane continuity を保持

## MusicXML normalization

対象 source:

- iReal Pro direct export MusicXML
- `@infojunkie/ireal-musicxml` converted MusicXML

主要方針:

- identity は `kind value + degree operations + bass` を主に使用
- `kind@text` は原則 identity 非採用（`alt` と direct-export sus 互換ヒントを除く）
- unsupported `kind` は暗黙 `7` fallback せず `UnsupportedMusicXMLHarmonyError`
- root/bass は pitch class 正規化し enharmonic 同値を同一扱い

timing policy:

- `source_position_quarters` は保持
- duration 生成は measure 内 harmony-event 数で等分割
- repeat/ending/DS/DC/Coda unfolding は deferred

## deferred

- iReal HTML / `irealb://` direct decode
- importer 側の variable duration import
- `allow_sus_add3`
- alias grammar の全面展開（data-driven 前提）

## 実装参照

- `src/changes/harmonic_context.py`
- `src/changes/voicing.py`
- `src/changes/voice_leading.py`
- `src/changes/importers/musicxml.py`
- `src/changes/rendering/arrangement_renderer.py`
- `src/changes/rendering/arrangement_flattener.py`

## 補助資料

- `docs/voicing-and-duration-rules.md`（詳細ルール・検証背景）
- `docs/concept.md`（Core Model Contracts）
- `docs/current-state.md`
