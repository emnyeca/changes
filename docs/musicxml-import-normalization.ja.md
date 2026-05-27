# MusicXML Import Normalization (iReal Pro / ireal-musicxml)

## 目的

Changes の MusicXML import は、出力元依存の表記差分を吸収して、和声コアに渡す構造化イベントを安定化する。

対象入力:
- iReal Pro direct export (observed: MusicXML 3.1, software: iReal Pro 2026.5)
- @infojunkie/ireal-musicxml output (observed: MusicXML 4.0, software: @infojunkie/ireal-musicxml 2.1.1)

注意:
- producer 文字列は受理条件ではない。
- producer/version は診断用途メタデータとして保持する。

## 正規化方針

### 主ルール

和声同定は `kind value + degree operations + bass` を主とする。

- `kind@text` は原則 identity に使わない
- ただし互換ヒントとして次のみ使用:
  - `alt`
  - iReal Pro direct-export の `suspended-fourth` + `text=7sus4`

## 既知 producer 差分と吸収ルール

- `major-seventh` text 差分 (`maj7` vs `M7`) は `maj7` へ統一
- `m7b5`:
  - direct: `minor-seventh + alter5=-1`
  - converted: `half-diminished`
  - 正規化: `m7b5`
- `7b9` / `7#9`: text 有無に関係なく degree で正規化
- `7#5`:
  - direct: `dominant + alter5=+1`
  - converted: `augmented-seventh`
  - 正規化: `7#5`
- `7#11`, `7b13`: degree によって正規化
- `maj7#5`: `major-seventh + alter5=+1` として構造保持
- `7#5b9`: `alter5=+1` + `add9=-1` を保持
- `mMaj7`:
  - direct: `minor + add7=+1`
  - converted: `major-minor`
  - 正規化: `mMaj7`
- `7sus4`:
  - direct: `suspended-fourth + add7`
  - converted: `dominant + add4 + subtract3`
  - 正規化: `7sus4`
- `dim`/`dim7`: `diminished` / `diminished-seventh` を区別して保持
- `alt`:
  - text に `alt` を含む場合は canonical `alt` に固定
  - raw degree は診断用に保持するが、constituent 決定は canonical `alt` を優先

## root / bass 正規化

- root と bass は pitch class に正規化
- enharmonic 同値は同一 pc として扱う (`C# == Db`)
- slash bass は signature root と分離保持
- slash bass は後段 harmony engine で Local Pitch Collection に加算

## timing 方針 (Phase 1)

- measure ごとに harmony を document order で保持
- `source_position_quarters` は保持する
  - `harmony/offset` があればそれを優先
  - なければ measure 内 cursor (note/forward/backup) から計算
- ただし duration 生成には使用しない
  - 現行は measure 内 harmony-event 数で等分割

このため、source 間で厳密 onset が異なっても、順序と件数が一致すれば同一 progression として扱う。

## form marker 方針

- repeat/ending/segno/coda/tocoda/words は raw marker として保持
- backward repeat に `times` が無い場合は `normalized_times=2` を補完
- style/groove words は和声進行生成には使わない
- repeat/ending/DS/DC/Coda 展開は本タスクでは未実装
- bar は written order のまま import

## 既知の deferred

- repeat/ending/segno/coda 展開
- MusicXML offset ベースの可変 duration import
- iReal HTML / irealb:// の decode
- runtime での ireal-musicxml 依存

## 実装モジュール

- `src/changes/importers/musicxml.py`
- 主 API:
  - `load_musicxml_song(path)`
  - `import_musicxml_text(xml_text)`
  - `imported_song_to_song_model(imported, tempo=...)`
  - `load_musicxml_song_model(path, tempo=...)`
