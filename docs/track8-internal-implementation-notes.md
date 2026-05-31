# Track 8 Internal Implementation Notes

## 位置づけ

この文書は、Track 8 実装フェーズで分散していた内部メモを統合した開発者向け資料です。

対象となる旧文書:

- `track8-toolkit-payload-adapter.md`
- `track8-toolkit-schema-alignment.md`
- `track8-length-encoding-yaml-export.md`
- `track8-toolkit-loader-validation.md`
- `track8-toolkit-sysex-generation.md`
- `track8-hardware-validation-fixtures.md`
- `track8-product-like-cmaj7-fixture.md`
- `track8-explicit-export-command-design.md`
- `track8-export-cli-readiness.md`
- `track8-toolkit-template-capability-check.md`
- `track8-product-like-pattern-settings-followup.md`
- `track8-product-like-template-fixture-design.md`

## 変換パイプライン（内部）

主な内部変換は次の順序で成立する。

```text
SongModel
  -> RenderedArrangement
  -> Track8ChordEvent
  -> toolkit-facing payload
  -> toolkit-style flat rows
  -> finalized length rows
  -> toolkit-loadable events YAML
  -> toolkit SysEx generation
```

## Payload / row 変換の要点

- Track 8 は 0-based index 7（toolkit 側 row では `track=8`）
- step は toolkit 側で 1-based
- note order は preserve（same-step chord trigger の代表音挙動を壊さない）
- velocity は `1..127` を厳密検証
- micro timing は `-23..23` を厳密検証
- `length_mode` は `inherit` / `explicit_event_length` を扱う

## Length encoding policy

explicit length は quarter duration から exact な Digitone `length_code` に変換する。

- 近似は行わない
- exact mapping 不可時は `ValueError`

既知例:

- `1/2` -> `0x1E`
- `1` -> `0x2E`
- `2` -> `0x3E`
- `4` -> `0x4E`

`inherit` は `length: inherit` を維持し、`length_code` は付与しない。

## toolkit loader validation

toolkit import は lazy import で実施し、ローカルに toolkit が無い場合は明示エラーとする。

検証対象（Cmaj7 baseline）:

- 6 event
- step=1（全 event）
- track=8（全 event）
- notes: `C4 E4 G4 B4 D5 A5`
- velocities: `70 70 70 50 70 50`
- `length_code=0x4E`
- `time=0`

## toolkit SysEx generation policy

- software-only 生成（hardware send は行わない）
- `build_syx_from_events(..., output_file=...)` を利用
- builder API は file-path ベースのため temporary file 経由で bytes 取得
- output contract: 非空、先頭 `0xF0`、末尾 `0xF7`

## Fixture generation summary

### hardware validation fixture

- `examples/generated/track8_hardware_validation/track8_cmaj7_changes.events.yaml`
- `examples/generated/track8_hardware_validation/track8_cmaj7_changes.syx`
- `examples/generated/track8_hardware_validation/track8_cmaj7_changes_manifest.md`

### product-like Cmaj7 fixture

- `examples/generated/track8_product_like_validation/track8_product_like_cmaj7.events.yaml`
- `examples/generated/track8_product_like_validation/track8_product_like_cmaj7.syx`
- `examples/generated/track8_product_like_validation/track8_product_like_cmaj7_manifest.md`

## Scope boundary

この内部メモは次を行わない。

- hardware send
- UI integration
- bundle planner の設計変更
- Cloud/Bass の主機能化（別タスク）

## Export command status (current)

- `changes export digitone-track8` は artifact export command
- export path は `.events.yaml` / `.syx` / `manifest` 生成を担当
- export は MIDI send を行わない（send は別 CLI 境界）
- SongModel YAML v1 入力は対応済み

## Product-like pattern settings (current)

- product-like policy は `docs/track8-product-like-pattern-settings-spec.md` を正本とする
- PER TRACK と Track 1-7 default velocity の扱いは spec 準拠
- template capability の詳細調査ログは本統合メモに吸収済み

## 関連する正本

- `docs/product-architecture.md`
- `docs/current-state.md`
- `docs/track8-chord-event-model.md`
- `docs/track8-export-api.md`
- `docs/track8-product-like-pattern-settings-spec.md`
- `docs/digitone-internal-spec.md`