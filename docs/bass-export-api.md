# Bass Export API（TBD）

## 1. 目的

この文書は、Bass export artifact の API 仕様正本候補です。

現在状態: `TBD`（安定した公開 Bass export API は未整備）

## 2. 想定 API 形状 (TBD)

Bass export を現在の Chord export と同等パターンで設計する場合、想定公開シンボルは次の通りです。

- `BassExportPaths` (`TBD`)
- `build_bass_export_yaml_payload_from_song(...)` (`TBD`)
- `build_bass_export_manifest(...)` (`TBD`)
- `export_bass_artifacts_from_song(...)` (`TBD`)

想定定数 (`TBD`):

- `DEFAULT_BASS_EXPORT_BASENAME`
- `DEFAULT_BASS_EXPORT_PROFILE`

## 3. 出力ファイル (TBD)

想定 artifact ファミリ:

- `*.events.yaml`
- `*.syx` (if enabled)
- `*_manifest.md`

最終的な命名・分割ポリシーは `TBD` です。

## 4. 依存ポリシー (TBD)

想定ルール:

- YAML-only export は toolkit 固有依存なしで実行できること
- SysEx 生成は export backend/toolkit を明示的に要求すること
- 依存方向は `changes` から backend toolkit への one-way を維持すること

Bass export の具体 backend 依存は `TBD` です。

## 5. 安全境界（契約目標）

Bass export API は次を行ってはなりません。

- MIDI 送信
- ハードウェア操作
- device port 自動選択
- transport 層の確認規則の隠蔽

export は artifact 生成専用のまま維持し、send policy は CLI/transport 境界で扱います。

## 6. 入力契約 (TBD)

想定入力ベースライン:

- SongModel YAML v1（`docs/concept.md` Model Contracts）

Bass 固有の追加契約項目は `TBD` です。

## 7. 検証ターゲット (TBD)

Bass export API 導入時は、最低でも次を検証対象にします。

- 同一入力からの deterministic artifact 生成
- slash bass / root fallback 処理の整合性
- manifest 整合性チェック
- send/hardware 境界との分離

具体 fixture と test matrix 登録は `TBD` です。

## 8. スコープ注記

この文書は API 境界の目標定義のみを扱います。

実装準備完了を主張するものではありません。