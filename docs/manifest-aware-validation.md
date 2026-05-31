# Manifest-aware SysEx 検証

## 目的

`changes check digitone-syx` は `.syx` file envelope を検証し、必要に応じて生成済み Track 8 manifest と照合できます。

これにより、次の取り違えを検出できます。

- 誤った `.syx` file
- 古い `.syx` file
- export artifact の不一致
- source title / count assumption の誤り

## 基本 envelope check

```powershell
changes check digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx
```

## Manifest-aware check

```powershell
changes check digitone-syx `
  --syx out/digitone-track8/changes_track8_export.syx `
  --manifest out/digitone-track8/changes_track8_export_manifest.md `
  --expect-source-title "Demo II V I" `
  --expect-chord-events 3 `
  --expect-note-rows 18
```

## 検証すること

- SysEx が `0xF0` で始まること
- SysEx が `0xF7` で終わること
- manifest に SysEx size がある場合、byte size が一致すること
- source title が取得できる場合、期待値と一致すること
- Track 8 chord event count が取得できる場合、期待値と一致すること
- Track 8 note row count が取得できる場合、期待値と一致すること

## 検証しないこと

- full Digitone payload semantics
- target pattern slot
- device identity
- actual hardware import
- すべての note / parameter mapping

fixture ごとの validation depth（hardware / software E2E / export-manifest）は `docs/validation-matrix.md` を参照してください。

## Safety

Check は MIDI を送信しません。

Check は `mido` を必要としません。

Real-send は別の明示的な command として維持します。
