# Changes Voicing / Duration ルール

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

- `major`（triad）: 1, 3, 5
- `maj7`: 1, 3, 5, 7
- `m7`: 1, b3, 5, b7
- `7`: 1, 3, 5, b7
- `m`: 1, b3, 5
- `6`: 1, 3, 5, 6
- `m6`: 1, b3, 5, 6
- `mMaj7`: 1, b3, 5, 7
- `m9`: 1, b3, 5, b7, 9
- `m7b5`: 1, b3, b5, b7
- `dim7`: 1, b3, b5, 6
- `9`: 1, 3, 5, b7, 9
- `7b9`: 1, 3, 5, b7, b9
- `7#9`: 1, 3, 5, b7, #9
- `7b5`: 1, 3, b5, b7
- `7b13`: 1, 3, 5, b7, b13
- `7#11`: 1, 3, 5, b7, #11
- `7#9b5`: 1, 3, b5, b7, #9
- `7sus4`: 1, 4, 5, b7
- `9sus4`: 1, 4, 5, b7, 9
- `7b9sus4`: 1, 4, 5, b7, b9
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
- bass render の音源は次の優先順です。
  - slash bass がある場合: slash bass pitch class
  - slash bass がない場合: chord signature root pitch class

## 4A. Register Policy and Bounded Voice Sliding

### Bass

Bass pitch source:

- use slash bass if present
- otherwise use chord signature root

Bass register:

- Digitone display G2-F#3
- MIDI 31-42

### Chord voices

Chord target register:

- Digitone display C4-A5
- MIDI 48-69

After harmony collection extraction, chord voices are realized by bounded minimum-motion voice sliding.

Bounded voice sliding is a boundary-repair stage on an already voice-led six-lane vector.
It is not an arbitrary bounded permutation search over all pitch-class lane assignments.

Bounded Voice Sliding determines the sliding chain from audible pitch order,
not voice-lane index order.

The returned voicing remains indexed by moving voice lanes; it is not
pitch-sorted. This distinction is required because ordinary voice leading may
produce voice crossing.

Pipeline:

- ordinary minimum-motion voice leading against previous audible bounded chord
- pre-fit six-lane vector (can be out of range)
- boundary slide repair (duplicate/missing-tone resolution)
- bounded audible output for this chord and next-step reference

Requirements:

- preserve the Output Chord Tone Set pitch-class multiset
- preserve six moving voice lanes
- fit every final chord note inside the configured range
- minimize movement by voice-lane index
- permit voice crossing
- do not sort final track/lane assignment by pitch
- raise an explicit error if no valid in-range realization exists

Concrete examples:

- `B3 E4 G4 A4 D4 C5 -> C4 E4 G4 A4 D4 B4`
- `E4 G4 C5 D5 A5 B5 -> E4 G4 B4 C5 D5 A5`

Crossed-lane example:

- Lane vector: `C5 E4 A5 G4 D5 B5`
- Audible pitch order: `E4 G4 C5 D5 A5 B5`
- After pitch-order sliding: `E4 G4 B4 C5 D5 A5`
- Returned lane vector: `B4 E4 D5 G4 C5 A5`

### Velocity-layer interpretation

Track Default Velocity represents voice-layer balance, not fixed chord-degree balance.

Because voice leading and bounded register sliding may reassign chord degrees between moving voice lanes, quieter tracks may sound different chord degrees over time. This behavior is currently intentional and will be evaluated by hardware listening validation.

### Current scope note (duplicate multiset)

Bounded Voice Sliding currently supports the present Changes output contract:
six distinct pitch classes per chord output.

Full collision-repair support for intentionally duplicated pitch-class
multisets is deferred until an output extraction rule produces such data.

## 5. Normalized harmonic identity

distinct chord 判定は raw string ではなく正規化IDで行います。

- identity: `(root_pc, normalized_quality, normalized_modifiers, slash_bass_pc)`
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

sus quality（`7sus4`, `9sus4`, `7b9sus4`）で heptatonic collection が選ばれた場合は、sus専用抽出を使います。

- `1 - 4 - 5 - 13 - b7 - 9`

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
- `allow_sus_add3`
- importer 実装（MusicXML importer本体は別タスク）

注記:

- parser alias 展開は data-driven に後続対応する。実サンプル収集前に推測で拡張しない。
- 本変更ではテストに必要な canonical symbol のみ実装対象。
- 外部フォーマット方針: 最初の外部インポート形式は MusicXML とし、iReal Pro HTML / `irealb://` 直接デコードは deferred。

## 13. Symmetric Collection Eligibility

Whole-tone および Diminished collection は、current chord が symmetric / altered 性を明示している場合にのみ Selected Scale Collection として採用できます。

- 前後の plain chord は Local Pitch Collection の構築には通常通り参加します。
- ただし current chord が plain major / minor quality の場合、文脈が偶然 whole-tone / diminished collection に包含されても、当該 symmetric collection を出力用 collection として採用しません。

目的:

- plain `m7` / `maj7` が偶発的に altered / diminished cloud 化することを防ぐ
- explicit altered / diminished chord の特殊色彩は維持する

適用メモ:

- 本タスクでは whole-tone / diminished で同一の eligibility セットを使います。
- plain dominant / plain sus（`7`, `9`, `13`, `7sus4`, `9sus4`）は現時点では symmetric 選択を許可しません。

検出事例（500 Miles High 抜粋）:

- 進行: `Em7 | Gm7`
- 制限前: `Gm7` が `G_half_whole_diminished` を選ぶ場合があり、出力は `G A# C# E F G#`
- 制限後: plain `Gm7` は diminished を選べないため retry は `current_only` まで進み、`G_dorian_diatonic` を選択
- 制限後出力: `G A# D E F A`

## 14. Hard Constituents and Color Hints

コード記号に含まれる音情報は、contextual collection selection において以下の二種類に分ける。

Hard constituents:

- chord の構造を定義する音
- root, 3rd/b3, 5th または altered 5th, 7th, sus4, diminished / half-diminished structure, slash bass
- Attempt 1 / Attempt 2 / Attempt 3 のすべてで collection containment を制約する

Color hints:

- ordinary dominant に明示された altered tension: `b9`, `#9`, `#11`, `b13`
- chord symbol および診断情報として保持する
- Attempt 1 / Attempt 2 では containment 制約に使わない
- Attempt 3 current_only では current chord の表記色を保つため制約へ戻す

Exception:

- `alt` は semantic directive として、従来の canonical hard constituent `1, b9, 3, b13/#5` を維持する

具体例:

- `Bm7b5 | E7#9 | Am7`
- 変更前: `#9 = G` が Attempt 2 の制約集合を塞ぎ、`A_harmonic_minor` への解決を阻害する場合がある
- 変更前の代表挙動: `E_half_whole_diminished` -> `E G A# C# D F`
- 変更後: Attempt 2 は `E7#9` の `#9` を hard 制約に含めない
- 変更後の解決: `A_harmonic_minor` -> `E G# B C D F`

補足:

- 対称collection制限（plain `m7` / `maj7` などは whole-tone / diminished を current 出力として選べない）とは独立に有効。
- plain chord の accidental symmetric recoloring を防ぎつつ、altered dominant の機能解決を優先できる。

## 12. Structured chord model（内部表現）

和声コアは固定quality文字列の列挙に依存せず、以下の概念を分離した構造化モデルで扱う。

- harmonic signature root
- base quality
- seventh type
- extensions
- added degrees
- altered degrees
- omitted degrees
- slash bass
- semantic special tag（例: `alt`, `sus`）

この内部表現は将来の MusicXML `kind` / `degree` / `bass` からのマッピング先として使用する。

## 11. 修正済み仕様メモ（以前の誤記修正）

- `Dm7b5` の誤った出力例を削除し、collection 抽出規則に統一。
- whole-tone の説明を修正（通常 heptatonic の `1,3,5,13,7,9` ではなく専用抽出）。
- `G7b13` と `Gaug7` の constituent 差異を明示。
- 「diminished が MVP に常時含まれる」という旧表現を、優先順位付き条件適用へ改訂。
- chromatic 出力 fallback 表現を削除し、context-reduction retry に置換。
