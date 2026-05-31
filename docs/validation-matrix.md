# 検証マトリクス

## 目的

このマトリクスは、v0.1 release-candidate workflow における各 SongModel fixture の現在検証範囲を追跡します。

現状は Chord workflow（Digitone Track 8）が RC 安定化 subset のため、検証マトリクスも Track 8 中心です。
これはプロダクト全体の方針順序を示すものではありません。

検証レベル:

- hardware-validated: Digitone II 実機で手動観測済み
- software E2E validated: export -> check --manifest -> dry-run を自動検証
- export/manifest validated: check/dry-run 全経路は含まず、export と manifest/count を自動検証
- not validated: 当該レベルの専用検証なし

## レイヤーと検証状態

| Layer | Tracks | Role | Current validation status |
| --- | --- | --- | --- |
| Harmony Cloud | 1-6 | six-voice playable harmony texture | generation implemented; product export command added; hardware validation pending |
| Bass | 7 | root movement / slash-bass grounding layer | generation implemented; product export command added; hardware validation pending |
| Chord | 8 | symbol-faithful vertical layer | generation implemented; current RC-stabilized subset |

## フィクスチャマトリクス

| フィクスチャ | Purpose | Export | SysEx generation | check --manifest | dry-run | real-send hardware | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `examples/song_models/demo_cmaj7.changes.yaml` | Quick smoke path | yes | optional | 主経路ではない | 主経路ではない | no | 単一 chord の基本 smoke fixture |
| `examples/song_models/demo_ii_v_i.changes.yaml` | Known hardware baseline | yes | yes | yes | yes | yes | 観測 Track 8 steps: Dm7 step1, G7 step5, Cmaj7 step9 |
| `examples/song_models/demo_multibar_turnaround.changes.yaml` | Multi-bar regression | yes | yes | yes | yes | no | software E2E validated |
| `examples/song_models/demo_multisection_form.changes.yaml` | Multi-section regression | yes | 安定 E2E 経路としては未カバー | export/manifest 回帰のみ | export/manifest 回帰のみ | no | export + manifest count 回帰でカバー |

## 現在サマリー

- 現在マトリクスは Track 8 中心ですが、これは現在の RC 安定化 subset を示すものです
- Cloud / Bass / Chord を同一 `RenderedArrangement` から Track 1-8 へ compile / export する software regression は追加済みです
- Hardware-validated: `demo_ii_v_i`
- Software E2E validated: `demo_ii_v_i`, `demo_multibar_turnaround`
- Export/manifest validated: `demo_multisection_form`（および `demo_cmaj7` の smoke export カバレッジ）
- 未検証: 広い hardware/device マトリクスと payload 意味論の全面検証
