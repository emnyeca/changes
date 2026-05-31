# Digitone SysEx CLI Modes

## 位置づけ

この文書は `changes send digitone-syx` の mode（`--list-ports` / `--dry-run` / `--real-send`）を開発者向けに一元化して説明する正本です。

従来の mode 別文書は履歴・導線として残し、仕様の重複記述はこの文書に集約します。

## コマンドモード

### 1. Port list mode

```bash
changes send digitone-syx --list-ports
```

- MIDI output port の列挙のみを行う
- hardware write はしない
- optional MIDI dependency（`mido`, `python-rtmidi`）が必要

### 2. Dry-run mode

```bash
changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II" \
  --dry-run
```

- `.syx` file を読み込む
- SysEx envelope を検証する
- 指定 port 名を dry-run transport 上で検証する
- hardware write はしない
- optional MIDI dependency なしでも実行可能

### 3. Guarded real-send mode

```bash
changes send digitone-syx \
  --syx out/digitone-track8/changes_track8_export.syx \
  --port "Digitone II" \
  --real-send \
  --yes-i-understand-this-writes-to-hardware
```

- 実機への SysEx 送信を実行する
- `--yes-i-understand-this-writes-to-hardware` が必須
- optional MIDI dependency（`mido`, `python-rtmidi`）が必要

## Safety boundary

- Export does not send.
- Check does not send.
- Real-send is never implicit.
- Real-send requires explicit confirmation.
- MIDI port auto-selection is not allowed.

## 推奨実行順序

1. `.syx` を export
2. `changes check digitone-syx` で envelope / manifest を検証
3. `--list-ports` で port 名を確認
4. `--dry-run` を実行
5. backup 済みを確認後に `--real-send` を実行

## 依存関係

optional MIDI dependency:

```bash
pip install .[midi]
```

version check:

```powershell
python -c "import importlib.metadata as md; print('mido', md.version('mido'))"
python -c "import importlib.metadata as md; print('python-rtmidi', md.version('python-rtmidi'))"
```

## 関連文書

- `docs/cli.md`（ユーザー向け CLI 参照）
- `docs/e2e-user-workflow.md`（RC stabilized Track 8 workflow）
- `docs/real-send-workflow.md`（実行手順）
- `docs/manifest-aware-validation.md`（check の詳細）
- `docs/generated-artifacts-policy.md`（artifact 取り扱い）
- `docs/hardware-validation/digitone-syx-real-send-first-validation.md`（実機検証記録）