# Digitone SysEx Real-send ワークフロー

## 現在状態

Guarded real-send は Digitone II で手動検証済みです。

全体の export -> check -> dry-run -> real-send フローは `docs/e2e-user-workflow.md` を参照してください。
コマンド仕様は `docs/cli.md` が正本です。

検証済み fixture:

- `examples/song_models/demo_ii_v_i.changes.yaml`
- Pattern location: `A01`
- Track 8 progression:
- Dm7 at step1
- G7 at step5
- Cmaj7 at step9

## 安全境界

Export は送信しません。

Real-send には次が必要です:

- 明示的な `.syx`
- 明示的な `--port`
- `--real-send`
- `--yes-i-understand-this-writes-to-hardware`

## 標準ワークフロー

### 1. MIDI extras をインストール

```powershell
python -m pip install -e ".[midi]"
```

### 2. version を確認

```powershell
python --version
python -c "import importlib.metadata as md; print('mido', md.version('mido'))"
python -c "import importlib.metadata as md; print('python-rtmidi', md.version('python-rtmidi'))"
```

### 3. guarded sequence を実行

1. export
2. check
3. list ports
4. dry-run
5. 明示確認付き real-send

厳密なコマンド定義は `docs/cli.md` を参照してください。

## 既知の検証環境

初回検証時:

```text
Date: 2026-05-30
OS: Windows PowerShell
Python: 3.14.5
mido: 1.3.3
python-rtmidi: 1.5.8
Digitone II firmware: 1.10D
Port selected: Elektron Digitone II 2
```

## 非ゴール

このワークフローが保証しないもの:

- export からの送信
- port 自動選択
- 確認フローの省略
- 将来すべての fixture 保証
- すべての LEN mapping の検証

## 関連文書

- `docs/index.md`
- `docs/cli.md`
- `docs/e2e-user-workflow.md`
- `docs/manifest-aware-validation.md`
- `docs/generated-artifacts-policy.md`
- `docs/current-state.md`
- `docs/current-state.md`
