# Cloud/Bass/Chord Documentation Rebalance TODO (2026-05-31)

## 目的

Track 8 文書の情報密度偏重を是正し、EUB Changes の本来の主機能である
Cloud / Bass / Chord を同等比重で扱う文書体系に再編する。

この文書は実施スケジュール用 TODO であり、実装変更は含まない。

## 情報密度評価（現状スナップショット）

### Track 8 文書群（整理前）

- 文書数: 15
- 合計行数: 2266
- 特徴: フェーズ別の分割文書が多く、同一論点（payload/loader/schema/sysex/fixture）が分散

### Cloud / Bass / Chord 文書群（現行）

- 主正本: `harmony-engine-spec.md`
- 補助: `voicing-and-duration-rules.md`
- パイプライン補助: `rendered-arrangement-pipeline.md`
- 特徴: 仕様は存在するが、Track 8 系ほどの粒度で分割されていない

### ギャップ評価

- Chord（特に Track 8）に関する運用・検証メモが過密
- Cloud/Bass のユーザー理解導線が相対的に弱い
- 「実装フェーズ記録」と「現行正本」の境界が曖昧になりやすい

## 直近実施済み（この回）

- Track 8 phase 文書の一部を `track8-internal-implementation-notes.md` に統合
- 分散した重複文書を削減

## 直近実施済み（追加整理）

- Track 8 履歴系文書をさらに統合し、`track8-export-api.md` / `track8-chord-event-model.md` / `track8-product-like-pattern-settings-spec.md` / `track8-internal-implementation-notes.md` の4本へ集約
- design/readiness/follow-up/capability-check/template-fixture の分散文書を削除し、リンク先を更新

## 現在地情報の置き場（運用ルール反映）

- 仕様本文から current scope / 実装済み未実装の記述を削減
- Digitone 実装状況は `status/native-syx-pipeline-status-20260526.md` を参照
- RC/validation 状態は `validation-status.md` / `validation-matrix.md` で管理

## TODO schedule

### TODO-1: Product architecture への導線強化（短期）

- `index.md` / `current-state.md` から Cloud/Bass/Chord の同等導線を追加
- Track 8 を「追加レイヤー + RC stabilized subset」として明示維持

### TODO-2: Harmony正本の章構造強化（短期）

- `harmony-engine-spec.md` を Cloud / Bass / Chord 章で再編
- Cloud/Bass の entrypoint と検証対象を明示

### TODO-3: Digitone文書の責務分離再確認（中期）

- `digitone-internal-spec.md` で「musical allocation」と「device initialization」を明示分離
- bundle planner と export profile の責務境界を再整理

### TODO-4: Track 8 文書群の最終アーカイブ方針（中期）

- テスト契約で固定されている文書は維持
- それ以外は統合済み正本へ寄せ、履歴価値が低いものは archive または削除

### TODO-5: Cloud/Bass 検証文書の増強（中期）

- Track 8 相当の検証粒度で Cloud/Bass の検証観点を明文化
- ただし実装状態を過大主張しない

### TODO-6: 比重監査チェック（継続）

- 新規文書追加時に「Cloud/Bass/Chord のどこに属するか」を必須記載
- Track 8 専用文書追加時は、Cloud/Bass 側導線への影響を同時確認

## 完了条件（将来）

- Cloud/Bass/Chord を同等に辿れる文書導線が index から成立
- Track 8 が「主要3機能の1つ」であることを誤解しない構成
- 正本・補助・履歴の区分が明確