# Chord Export API

## 1. 目的

この文書は、Chord export artifact の API 仕様正本です。

現在の実装対象は Chord export（Digitone Track 8）です。

公開 API 実装は `src/changes/digitone/track8_export_api.py` にあります。

## 2. API

公開シンボル:

- `Track8ExportPaths`
- `build_track8_export_yaml_payload_from_song(...)`
- `build_track8_export_manifest(...)`
- `export_track8_artifacts_from_song(...)`

定数:

- `DEFAULT_TRACK8_EXPORT_BASENAME = "changes_track8_export"`
- `DEFAULT_TRACK8_EXPORT_PROFILE = "product-like"`

## 3. 出力ファイル

basename が `my_song` の場合:

- `my_song.events.yaml`
- `my_song.syx`
- `my_song_manifest.md`

`include_sysex=False` の場合:

- `my_song.events.yaml`
- `my_song_manifest.md`

このモードでは `.syx` は生成されません。

## 4. toolkit 依存

- `.events.yaml` のみの export は toolkit 不要
- `.syx` export は `digitone-syx-toolkit` が必要
- toolkit 依存は SysEx 生成時に lazy import
- 依存方向は `changes -> digitone-syx-toolkit` を維持

## 5. 安全境界

この API は次を行いません。

- MIDI 送信
- ハードウェア操作
- CLI コマンド挙動の公開
- 任意入力ファイルローダーの実装

この API は artifact 生成専用です。送信ポリシーは CLI/transport 側で扱います。

参照:

- `docs/cli.md`
- `docs/digitone-internal-spec.md`
- `docs/generated-artifacts-policy.md`

## 6. ローカル例

```python
from changes.digitone.track8_export_api import export_track8_artifacts_from_song

paths = export_track8_artifacts_from_song(
    song,
    "out/digitone-track8",
    basename="my_song",
    name="My Song",
    include_sysex=True,
    overwrite=False,
)
```

## 7. 入力契約

Chord export CLI/API（Digitone Track 8）は SongModel YAML v1 入力を受け付けます。

入力形式は `docs/concept.md` の Model Contracts を参照してください。

## 8. カバレッジメモ

Chord export は次の fixture でカバーされています。

- `examples/song_models/demo_cmaj7.changes.yaml`
- `examples/song_models/demo_ii_v_i.changes.yaml`

II-V-I 例は、異なる offset を持つ複数 chord event を検証します。