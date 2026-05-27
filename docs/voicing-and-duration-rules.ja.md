# Changes Voicing & Duration Rules

この文書は Changes の和声生成仕様（実装仕様）です。目的は 6 声の machine-live 向けハーモニークラウドを、決定的（deterministic）に生成することです。

## 1. 基本原則

- Chord Symbol は Local Pitch Collection を作るための入力です。
- Chord Symbol の tension/alteration は「そのまま出力音に必須採用」しません。
- Selected Scale Collection を先に決め、Output Chord Tone Set は選ばれた collection の抽出規則で決まります。
- 既存の検証済みパス（`maj7` / `m7` / `7` と C-major ii-V-I / Blue Moon / `Bm7` 単独）は互換維持します。

## 2. 用語

- Chord Symbol: 例 `Dm7`, `G7b13`, `Galt`, `C/E`
- Local Pitch Collection: 現在コード + 前後の distinct chord（同一和声IDはスキップ）から作る pitch-class 集合
- Selected Scale Collection: Local Pitch Collection を完全包含する候補集合を優先順位で選んだもの
- Output Chord Tone Set: 実際に鳴らす 6 音

## 3. Chord constituent 定義（canonical）

本フェーズで実装する canonical quality:

- `maj7`: 1, 3, 5, 7
- `m7`: 1, b3, 5, b7
- `7`: 1, 3, 5, b7
- `m`: 1, b3, 5
- `mMaj7`: 1, b3, 5, 7
- `m7b5`: 1, b3, b5, b7
- `dim7`: 1, b3, b5, 6
- `7b9`: 1, 3, 5, b7, b9
- `7b13`: 1, 3, 5, b7, b13
- `aug7` / `7#5`: 1, 3, #5, b7
- `alt`: 特別規則（`Ralt` = `bII mMaj7 / R` 的 constituent）
  - constituent: `R`, `b9`, `3`, `b13/#5`
  - 例 `Galt` -> `G, Ab, B, Eb`

注意:

- `G7b13` と `Gaug7` は constituent set が異なります（前者は `5` を含み、後者は `#5`）。
- ただし、選択 collection が同じなら最終 6 音が一致し得ます。

## 4. Slash bass 規則

- slash bass は Local Pitch Collection に追加します。
- slash bass は chord signature root を置換しません。
- 出力抽出の基準 root は常に左側 chord root です。
- bass track の送信仕様は独立です（和声抽出規則とは分離）。

## 5. Normalized harmonic identity

distinct chord 判定は raw string ではなく正規化IDで行います。

- identity: `(root_pc, normalized_quality, normalized_alterations, slash_bass_pc)`
- enharmonic 同値 root は同一として扱う（例: `C#maj7` == `Dbmaj7`）
- `Dm7` と `Dm7/G` は別ID
- canonical 等価品質（例: `aug7` と `7#5`）は同値扱い

## 6. Scale collection family と優先順位

候補 family（優先順）:

1. Diatonic / Dorian
2. Harmonic minor
3. Melodic minor / Lydian dominant
4. Whole-tone
5. Half-whole / Whole-half diminished

候補は「Local Pitch Collection を完全包含」した場合のみ eligible。

同一優先度で複数候補がある場合:

1. chord signature root と candidate anchor root の円環半音距離が最短のもの
2. 同距離なら安定ソートで決定
3. diminished family で Half-Whole と Whole-Half が同条件なら Half-Whole を優先

## 7. 抽出規則

### 7.1 Heptatonic family

適用:

- Diatonic / Dorian
- Harmonic minor
- Melodic minor / Lydian dominant

抽出:

- `1 - 3 - 5 - 13 - 7 - 9`
- scale index では `1, 3, 5, 6, 7, 2`

### 7.2 Whole-tone

collection:

- `1, 2, 3, #4/#11, #5, b7`

抽出:

- `1 - 3 - #11 - #5 - b7 - 9`

### 7.3 Half-Whole diminished

collection:

- `1, b2, b3, 3, b5, 5, 6, b7`

抽出:

- `1 - b3 - b5 - 6 - b7 - b9`

### 7.4 Whole-Half diminished

collection:

- `1, 2, b3, 4, b5, b6, 6, 7`

抽出:

- `1 - b3 - b5 - 6 - 7 - 9`

diminished eligibility 制約:

- chord signature root == diminished collection root

## 8. Resolution retry policy

Chromatic fallback は使用しません。各コード発生点で次の順に試行します。

1. `current + previous distinct + next distinct`
2. `current + previous distinct`（next を除外）
3. `current only`

current-only でも解決不能なら `Unsupported harmonic context` を明示的に raise します。

## 9. Song/Section/Bundle 文脈規則

- full-song rendering: セクション境界を跨いで文脈計算
- single-section rendering: その section 内で circular
- Intro/Ending も full-song circular 文脈に含む
- bundle/pattern split: 分割前の song-level で和声解決し、split 後に再計算しない
- 同名 section の再登場（A|B|A）は occurrence-aware に評価

## 10. 現フェーズで意図的に deferred

- iReal Pro の網羅 alias 展開（`-7`, `ø7`, `°7`, `+7` など）
- `sus` の品質別抽出（例 `7sus4 -> 1-4-5-13-b7-9`）
- `allow_sus_add3`
- importer 拡張

注記:

- parser alias 展開は data-driven に後続対応する。実サンプル収集前に推測で拡張しない。
- 本変更ではテストに必要な canonical symbol のみ実装対象。

## 11. 修正済み仕様メモ（以前の誤記修正）

- `Dm7b5` の誤った出力例を削除し、collection 抽出規則に統一。
- whole-tone の説明を修正（通常 heptatonic の `1,3,5,13,7,9` ではなく専用抽出）。
- `G7b13` と `Gaug7` の constituent 差異を明示。
- 「diminished が MVP に常時含まれる」という旧表現を、優先順位付き条件適用へ改訂。
- chromatic 出力 fallback 表現を削除し、context-reduction retry に置換。
