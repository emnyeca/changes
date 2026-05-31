# ワークフロー RC 状態

## 状態

Release-candidate workflow: active development / v0.1 candidate

これは polished public release ではありません。

この文書は現在安定化している Chord subset（Digitone Track 8）を扱います。
プロダクト全体方針を定義する文書ではありません。
プロダクトアーキテクチャは Cloud > Bass > Chord を維持します。

## 現在の RC-stabilized workflow

```text
SongModel YAML
  -> Chord export (Digitone Track 8)
  -> SysEx check
  -> manifest-aware validation
  -> dry-run send
  -> guarded real-send
```

この stable path は検証済み subset であり、プロダクト全体の最終ワークフローではありません。

## 現在の検証済み fixture

- Input: `examples/song_models/demo_ii_v_i.changes.yaml`
- Output: `out/digitone-track8/changes_track8_export.syx`
- Manifest: `out/digitone-track8/changes_track8_export_manifest.md`
- Device: Digitone II
- Firmware: 1.10D
- Result: Dm7 -> G7 -> Cmaj7 の Chord import/send workflow（Digitone Track 8）で passed

## RC 受け入れチェックリスト

- [x] Chord export CLI が存在
- [x] SongModel YAML v1 入力が存在
- [x] SysEx file envelope check が存在
- [x] Manifest-aware check が存在
- [x] Dry-run send が存在
- [x] Guarded real-send が存在
- [x] Real-send は明示確認が必須
- [x] II-V-I fixture の first hardware validation が passed
- [x] mido は optional を維持
- [x] Export は送信しない
- [x] Check は送信しない
- [x] より広い SongModel software fixture coverage がある
- [ ] 複数 hardware/device 検証
- [ ] Chord parameter mapping の全面検証
- [ ] Public-facing installer/app packaging
- [ ] GUI workflow

現在の追加ソフトウェア fixture:

- software E2E export/check/dry-run: `demo_multibar_turnaround`
- export/manifest regression coverage: `demo_multisection_form`

hardware validation は現時点で最初の II-V-I fixture に限定されています。

fixture ごとの正確なカバレッジは `docs/validation-matrix.md` と `docs/fixture-inventory.md` を参照してください。

## Release-candidate の意味

現在 workflow が controlled development と manual validation で利用可能であることを示します。

一般 consumer 利用準備が完了したことを意味しません。
