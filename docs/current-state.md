# 現在状態と計画

この文書は、次を一体で扱う正本です。

- 判断材料としての現在状態
- 今後の計画方針

## プロダクト目標と方針

EUB Changes は、楽曲データから Cloud / Bass / Chord の各レイヤーを生成し、用途に応じて単独または組み合わせて使える machine-live workflow を目指します。

- Track 1-6: Harmony Cloud
- Track 7: Bass
- Track 8: Chord

楽曲データの入力源は、iReal Pro / MusicXML 由来のファイルと、GUI Editor からの直接入力の2種類を想定します。

現在は Cloud / Bass / Chord の統合 product workflow を RC 安定化 subset として扱います。

## 現在エビデンスのスナップショット (2026-05-31)

### ハードウェアエビデンス

- Digitone II guarded real-send は次 fixture で検証済み: `examples/song_models/demo_ii_v_i.changes.yaml`
- 観測進行: Dm7 (step1), G7 (step5), Cmaj7 (step9)
- Pattern location: A01
- 結果: passed

詳細: hardware validation notes under `docs/hardware-validation/`

### ソフトウェアエビデンス

テストでカバー済み:

- Product export CLI
- SysEx file validation
- dry-run send
- fake backend を使った guarded real-send safety checks
- CLI help / dispatch
- MusicXML import と bundle diagnostics
- iReal MusicXML ZIP import で groove/style default tempo を考慮した tempo 推定
- MIDI only metadata update で converter default 120 を考慮した既存tempo維持判定
- Harmony Engine の dominant-blues fallback による MusicXML slash-bass blues 文脈（例: `A7/C`）解決
- dominant_blues 選択時に prev/current と current/next の比較でより高優先度スケールを優先する近傍省略条件を追加
- Product render path の Chord layer でも dominant-blues 抽出（1,3,5,6,b7,#9）を適用
- chord / bass register bounds を含む timeline rendering
- `RenderedArrangement` から Cloud Track 1-6 / Bass Track 7 / Chord Track 8 を同時 compile する regression
- `changes export digitone-product` による Track 1-8 product artifact export
- layer 別 trigger policy（`hold_until_change` / `retrigger`）の flatten 適用
- `EditorState` からの SongModel 変換（chord 入力・% 解決・空小節補填・section 進行）

ソフトウェア E2E fixture:

- `examples/song_models/demo_ii_v_i.changes.yaml`
- `examples/song_models/demo_multibar_turnaround.changes.yaml`

export/manifest fixture:

- `examples/song_models/demo_multisection_form.changes.yaml`
- `examples/song_models/demo_cmaj7.changes.yaml`（smoke-level）

### 現在ギャップ要約

- 広い song form カバレッジのハードウェア検証は未完了
- duration / LEN mapping の全面検証は未完了
- Chord parameter mapping の全面検証は未完了
- 複数 Digitone II firmware 版の検証は未完了
- 複数 OS 環境の検証は未完了
- 大規模 song export の検証は未完了
- consumer 向け導入フローの検証は未完了
- Cloud / Bass / Chord をそろえた実機検証は継続中
- Editor GUI シェル（画面実装）は未着手

## 現在状態にもとづく計画

### Horizon A: Product workflow 安定化（近接）

- safety guardrail を維持したまま fixture 多様性を拡張
- mapping と form-coverage の明確な検証ギャップを解消
- real-send 経路を guarded かつ再現可能に維持

完了シグナル:

- 複数系統の hardware-validated fixture が成立
- guarded send safety checks に回帰がない

### Horizon B: Cloud/Bass/Chord 統合提供・Editor 拡張（中期）

- Chord 偏重を減らすため Cloud/Bass/Chord 統合経路の検証カバレッジを増加
- Cloud/Bass/Chord の導線バランスを改善
- Track 1-8 product export を実機 validation へ進める
- Editor GUI シェル実装（Generate/Send 画面との統合）

完了シグナル:

- validation matrix が Chord 中心を超える実用カバレッジを示す
- docs 読み順で Cloud/Bass/Chord のレイヤー関係が過不足なく理解できる
- Editor 画面で chord 進行を入力し Digitone へ送れる基本フローが動作する

### Horizon C: production 耐性拡張（後期）

- 追加 firmware 版と OS 環境で検証
- より大きい song form と export 規模を検証
- consumer 向け導入前に運用信頼性を向上

完了シグナル:

- 環境横断で再現可能な validation 結果
- 大規模 song export の運用許容範囲が文書化済み

## 参照マップ

- プロダクト階層と意図: `product-architecture.md`
- 検証範囲: `validation-matrix.md`

status と schedule 情報は、仕様本文ではなく status/schedule 文書または本サマリーで管理します。
