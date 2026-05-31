# End-to-end Digitone Track 8 SysEx ワークフロー

## 目的

この文書は、現在安定化している Chord RC ワークフロー（Digitone Track 8）を示します。
EUB Changes 全体の完成形ワークフローを示すものではありません。

上位のプロダクト方針は `docs/product-architecture.md` と `docs/current-state.md` を参照してください。

実運用フロー:

SongModel YAML -> Chord export (Digitone Track 8) -> manifest-aware SysEx check -> dry-run -> guarded real-send

## 安全境界

Export は送信しません。

Check は送信しません。

Dry-run は送信しません。

Guarded real-send は明示確認が必須です。

`mido` と `python-rtmidi` は `changes send digitone-syx --list-ports` と guarded real-send にのみ必要です。

## ワークフロー

1. Export Chord artifacts（Digitone Track 8, `changes export digitone-track8`）
2. Check `.syx` envelope and optional manifest (`changes check digitone-syx`)
3. List ports (`changes send digitone-syx --list-ports`)
4. Dry-run (`changes send digitone-syx --dry-run`)
5. Guarded real-send (`changes send digitone-syx --real-send --yes-i-understand-this-writes-to-hardware`)

厳密なコマンドオプションは `docs/cli.md` を参照してください。

## 検証済み fixture

現在の検証済み fixture:

- `examples/song_models/demo_ii_v_i.changes.yaml`
- Dm7 at step1
- G7 at step5
- Cmaj7 at step9
- Digitone II firmware 1.10D で検証済み

## 追加ソフトウェア fixture

ソフトウェア検証・回帰用の SongModel fixture:

- `examples/song_models/demo_multibar_turnaround.changes.yaml`
- `examples/song_models/demo_multisection_form.changes.yaml`

II-V-I fixture は既知のハードウェア検証済みパスとして使用します。

`demo_multibar_turnaround` はソフトウェア E2E export/check/dry-run 検証に使用します。

`demo_multisection_form` は export/manifest 回帰に使用します。

fixture ごとの正確な検証範囲は `docs/validation-matrix.md` を参照してください。

## 要件

export/check/dry-run に必要:

- 通常の開発インストール
- `.syx` 生成時は digitone-syx-toolkit

これらの手順に `mido` は不要です。

port 一覧 / real-send に必要:

```powershell
python -m pip install -e ".[midi]"
```

これにより optional MIDI backend がない環境でも check と dry-run を維持できます。

## バージョン確認

MIDI backend のトラブルシュート時は `docs/real-send-workflow.md` の version-check コマンドを使います。

## 中止条件

次の場合は real-send 前に中止します:

- SysEx check が失敗した
- Digitone II port が見えない
- port 名が曖昧
- `.syx` が想定ファイルでない
- 重要な Digitone データをバックアップしていない

manifest-aware check の詳細と警告挙動は `docs/manifest-aware-validation.md` を参照してください。

現在の RC 範囲と検証済み fixture 状態は `docs/release-candidate-status.md` と `docs/current-state.md` を参照してください。
