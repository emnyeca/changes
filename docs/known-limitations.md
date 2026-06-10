# 既知の制約

## Scope

現在の release-candidate workflow は、Cloud / Bass / Chord をまとめた product export と guarded SysEx sending に集中しています。

これは stabilized subset であり、full product architecture ではありません。

## 制約一覧

### hardware validation の範囲は狭い

Digitone II で manual validation 済みなのは II-V-I fixture のみです。

### SongModel coverage は限定的

software fixture には multi-bar / multi-section example を含めています。

hardware validation は引き続き II-V-I fixture に限定されています。

現在の workflow は、すべての SongModel input を support することを意味しません。

fixture ごとの正確な scope は `docs/validation-matrix.md` を参照してください。

### SysEx check は envelope-level

`changes check digitone-syx` は SysEx envelope を検証します。

full Digitone payload semantics は検証しません。

### Real-send は意図的に guarded

Real-send には次が必要です。

- explicit `.syx`
- explicit `--port`
- `--real-send`
- `--yes-i-understand-this-writes-to-hardware`

これは意図的な安全境界であり、弱めてはいけません。

### MIDI backend は optional

`mido` と `python-rtmidi` は port listing と real-send の場合のみ必要です。

### generated artifact は一時的な development asset

Generated validation artifacts under `examples/generated/` are development assets and are not permanent release assets.

現時点では permanent release asset ではありません。

### iReal Pro import は変換ベース

- iReal import は同梱の `ireal-musicxml` で iReal data を MusicXML へ変換してから取り込みます。
- iReal固有の layout / alternate chord / repeat / comment / backing track 情報は、完全には再現されない場合があります。
- converter の warning は、取得できた場合に import warning として表示されます。
- MIDI生成（`musicxml-midi`）は同梱していません。tempo / key / meter は MusicXML 変換結果と style default から決まります。

### 公開プレイリストのインポートはネットワーク必須

- Import セクションのプルダウンから公式 iReal Pro プレイリスト（Jazz 1460 など）を選ぶと、インポート実行時にネットワーク経由で取得します。
- オフライン環境ではエラーが表示されます。iReal Pro の .html ファイルを手動でダウンロードしてファイルアップロードからインポートすることで回避できます。
- Jazz 1460 などの大規模プレイリストは変換に数分かかる場合があります。

### consumer installer ではない

現在は developer / technical CLI workflow です。

consumer-facing app や installer は現在の RC scope 外です。
