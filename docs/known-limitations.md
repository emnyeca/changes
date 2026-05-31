# 既知の制約

## Scope

現在の release-candidate workflow は、Digitone II Track 8 向け Chord export と guarded SysEx sending に集中しています。

これは stabilized subset であり、full product architecture ではありません。

## 既知の制約

### hardware validation の範囲は狭い

Digitone II で manual validation 済みなのは II-V-I fixture のみです。

### SongModel coverage は限定的

software fixture には multi-bar / multi-section example を含めています。

hardware validation は引き続き II-V-I fixture に限定されています。

現在の workflow は、すべての SongModel input を support することを意味しません。

fixture ごとの正確な scope は `docs/validation-matrix.md` を参照してください。

### Manifest validation は metadata-level

`changes check digitone-syx --manifest` は envelope と metadata consistency を検証します。

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

`out/digitone-track8/` 配下の file は reproducibility のため一時的に保持しています。

現時点では permanent release asset ではありません。

### consumer installer ではない

現在は developer / technical CLI workflow です。

consumer-facing app や installer は現在の RC scope 外です。
