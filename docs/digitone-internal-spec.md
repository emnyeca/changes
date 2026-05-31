# Digitone Internal Specification

## 位置づけ

この文書は Changes における Digitone 関連内部仕様の統合正本です。

Export / Transport / Backend の責務境界と current scope を定義します。

## Architecture boundary

期待フロー:

```text
SongModel YAML
  -> Track 8 export
  -> .syx bytes
  -> transport layer
  -> MIDI backend
  -> Digitone II
```

責務分離:

- Export layer: artifact 生成（send しない）
- Transport layer: SysEx validation / send policy / dry-run / guard
- Backend layer: port list / byte send / backend adapter

## Native SysEx policy

- Digitone 出力の primary backend は Native SysEx
- dependency direction は one-way: `changes -> digitone-syx-toolkit`
- Generic MIDI backend は検証・比較用途として維持
- legacy realtime high-speed recording は通常フローにしない

base policy:

- `pattern.mode = per-track`
- Track 1..8 LENGTH/SPEED は Changes 計算値
- Track 9..16 は fixed LENGTH/SPEED
- pattern-shared CHANGE=`OFF`, RESET=`INF`

## Safety boundary

- Export does not send.
- Check does not send.
- Real-send is never implicit.
- MIDI port auto-selection is not allowed.

real-send 要件:

- `--real-send`
- `--yes-i-understand-this-writes-to-hardware`
- `--port`
- `--syx`

## CLI modes

`changes send digitone-syx` mode:

- `--list-ports`
- `--dry-run`
- `--real-send`

推奨順序:

1. export
2. check (`changes check digitone-syx`)
3. list ports
4. dry-run
5. guarded real-send

詳細コマンドは `docs/digitone-syx-cli-modes.md` を参照。

## Backend policy

候補:

- `mido` + `python-rtmidi`（第一候補）
- direct `python-rtmidi`（代替）

方針:

- normal install / normal test で mandatory にしない
- optional dependency は lazy import 背後に置く
- backend error は transport/domain error へ変換

実験時 install:

```bash
pip install .[midi]
```

version check:

```powershell
python -c "import importlib.metadata as md; print('mido', md.version('mido'))"
python -c "import importlib.metadata as md; print('python-rtmidi', md.version('python-rtmidi'))"
```

実装状況は status 文書で管理する。

- `docs/status/native-syx-pipeline-status-20260526.md`

## Tempo and pattern notes

用語:

- `performance_tempo`
- `digitone_device_tempo`

formula:

- `digitone_device_tempo = 2 * performance_tempo / q_step`

validation scope:

- `30.0 <= digitone_device_tempo <= 300.0`

## 関連文書

- `docs/digitone-syx-cli-modes.md`
- `docs/real-send-workflow.md`
- `docs/generated-artifacts-policy.md`
- `docs/manifest-aware-validation.md`
- `docs/status/native-syx-pipeline-status-20260526.md`（時点スナップショット）