# Changes CLI リファレンス

この文書は、現在の CLI コマンド仕様の正本です。

## 現行コマンド

### Digitone Product artifact export（Tracks 1-8）

```powershell
changes export digitone-product `
  --input examples/ii_v_i_intro_a.progression.yaml `
  --output-dir out/digitone-product `
  --layers cloud,bass,chord
```

要点:

- Digitone II Track 1-6 の Cloud、Track 7 の Bass、Track 8 の Chord を同時に生成
- MIDI は送信しない
- `--layers` 省略時は `cloud,bass,chord`
- `--layers cloud,bass`、`--layers chord`、`--layers cloud` のように layer を選択可能
- `--write-syx` 指定時のみ `.syx` も生成

### Digitone Chord artifact export（Track 8）

```powershell
changes export digitone-track8 `
  --input examples/song_models/demo_ii_v_i.changes.yaml `
  --output-dir out/digitone-track8 `
  --basename changes_track8_export `
  --overwrite
```

要点:

- Digitone II Track 8 向けの Chord artifact を生成
- MIDI は送信しない
- `--events-yaml-only` でない場合、`.events.yaml` / `.syx` / manifest を出力
- `--input` は SongModel YAML v1 を要求
- `--events-yaml-only` は SysEx 生成をスキップ
- `--overwrite` は既存 artifact を上書き

API 境界:

- Python API 仕様: `docs/chord-export-api.md`

### Digitone SysEx 送信

port 一覧:

```powershell
changes send digitone-syx --list-ports
```

dry-run:

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --dry-run
```

guarded real-send:

```powershell
changes send digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --port "Elektron Digitone II 2" `
  --real-send `
  --yes-i-understand-this-writes-to-hardware
```

要点:

- `--list-ports` は出力 port を列挙するだけで送信しない
- `--dry-run` はハードウェア書き込みなしで検証する
- `--real-send` はハードウェアへ書き込む
- `--yes-i-understand-this-writes-to-hardware` は real-send で必須
- `pip install .[midi]` は port 一覧と real-send で必要

### Digitone SysEx ファイルチェック

```powershell
changes check digitone-syx --syx out/digitone-track8/changes_track8_export.syx
```

manifest-aware 例:

```powershell
changes check digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --manifest out/digitone-track8/changes_track8_export_manifest.md `
  --expect-source-title "Demo II V I" `
  --expect-chord-events 3 `
  --expect-note-rows 18
```

要点:

- file envelope を検証
- 必要に応じて Track 8 manifest と `.syx` byte count / 期待値を照合
- manifest-aware flags: `--manifest`, `--expect-source-title`, `--expect-chord-events`, `--expect-note-rows`
- `mido` は不要
- 送信しない

より広いソフトウェア fixture カバレッジには、同じ export/check/dry-run フローを次で実行:

- `examples/song_models/demo_multibar_turnaround.changes.yaml`

multi-section 回帰には次を使用:

- `examples/song_models/demo_multisection_form.changes.yaml`

fixture ごとの検証深度は `docs/validation-matrix.md` を参照。

## 安全境界

- export は送信しない
- check は送信しない
- real-send は明示指定のみ
- port 自動選択は行わない
- MIDI optional dependency は optional のまま維持
