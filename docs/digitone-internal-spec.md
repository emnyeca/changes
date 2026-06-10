# Digitone 内部仕様

## 位置づけ

この文書は Changes における Digitone 関連内部仕様の統合正本です。

Export / Transport / Backend の責務境界と現在スコープを定義します。

## アーキテクチャ境界

期待フロー:

```text
SongModel YAML
  -> Product export (Digitone Tracks 1-8)
  -> .syx bytes
  -> transport layer
  -> MIDI backend
  -> Digitone II
```

責務分離:

- Export layer: artifact 生成（send しない）
- Transport layer: SysEx validation / send policy / dry-run / guard
- Backend layer: port list / byte send / backend adapter

## Native SysEx ポリシー

- Digitone 出力の primary backend は Native SysEx
- dependency direction は one-way: `changes -> digitone-syx-toolkit`
- Generic MIDI backend は検証・比較用途として維持
- legacy realtime high-speed recording は通常フローにしない

base policy:

- `pattern.mode = per-track`
- Track 1..8 LENGTH/SPEED は Changes 計算値
- Track 9..16 は fixed LENGTH/SPEED
- pattern-shared CHANGE=`OFF`, RESET=`INF`

## 安全境界

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

詳細コマンドは `docs/cli.md` を参照。

## Backend ポリシー

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

## Pattern import / naming policy

- 複数の Pattern SysEx message は連続受信できる。
- device 側で選んだ destination start slot から順に配置される。
- generator 側で destination slot を encode しない。
- 同じ destination slot へ受信した場合は上書きされる。
- `source_title` は song identity、`pattern_name` は device display name として分離する。
- events YAML の `name` は最終的な per-pattern `pattern_name` から export する。
- explicit per-segment Pattern Name override は `pattern_name_source` で記録し、auto prefix を注入しない。
- toolkit は Pattern Name を Digitone 側の allowed character / 16文字制約に合わせて normalize / validate / truncate する。
- Generic MIDI export path は Digitone Pattern Name restriction の影響を受けない。

## Tempo と pattern メモ

用語:

- `performance_tempo`
- `digitone_device_tempo`

formula:

- `digitone_device_tempo = 2 * performance_tempo / q_step`

validation scope:

- `30.0 <= digitone_device_tempo <= 300.0`

## 関連文書

- `docs/cli.md`
- `docs/real-send-workflow.md`
