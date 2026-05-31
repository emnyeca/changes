# 現在状態と計画

この文書は、次を一体で扱う正本です。

- 判断材料としての現在状態
- 今後の計画方針

## プロダクト目標と方針

EUB Changes は、iReal Pro または MusicXML 由来の楽曲データから Cloud / Bass / Chord の各レイヤーを生成し、用途に応じて単独または組み合わせて使える machine-live workflow を目指します。

- Track 1-6: Harmony Cloud
- Track 7: Bass
- Track 8: Chord

現在は Track 8 が RC 安定化 subset ですが、これは長期的なプロダクト方針を変更するものではありません。

## 現在エビデンスのスナップショット (2026-05-31)

### ハードウェアエビデンス

- Digitone II guarded real-send は次 fixture で検証済み: `examples/song_models/demo_ii_v_i.changes.yaml`
- 観測進行: Dm7 (step1), G7 (step5), Cmaj7 (step9)
- Pattern location: A01
- 結果: passed

詳細: `docs/hardware-validation/digitone-syx-real-send-first-validation.md`

### ソフトウェアエビデンス

テストでカバー済み:

- Chord export CLI
- SysEx file validation
- manifest-aware validation
- dry-run send
- fake backend を使った guarded real-send safety checks
- CLI help / dispatch
- MusicXML import と bundle diagnostics
- chord / bass register bounds を含む timeline rendering
- `RenderedArrangement` から Cloud Track 1-6 / Bass Track 7 / Chord Track 8 を同時 compile する regression
- `changes export digitone-product` による Track 1-8 product artifact export

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
- Cloud / Bass / Chord をそろえた実機検証は Chord RC workflow 相当の粒度には未到達

## 現在状態にもとづく計画

### Horizon A: Chord RC パス安定化（近接）

- safety guardrail を維持したまま fixture 多様性を拡張
- mapping と form-coverage の明確な検証ギャップを解消
- real-send 経路を guarded かつ再現可能に維持

完了シグナル:

- 複数系統の hardware-validated fixture が成立
- guarded send safety checks に回帰がない

### Horizon B: Cloud/Bass/Chord 統合提供へ再バランス（中期）

- Chord 偏重を減らすため Cloud/Bass/Chord 統合経路の検証カバレッジを増加
- Cloud/Bass/Chord の導線バランスを改善
- Track 1-8 product export を実機 validation へ進める

完了シグナル:

- validation matrix が Chord 中心を超える実用カバレッジを示す
- docs 読み順で Cloud/Bass/Chord のレイヤー関係が過不足なく理解できる

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
