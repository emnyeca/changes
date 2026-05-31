# フィクスチャ一覧

## 目的

この一覧は、Chord RC ワークフロー（Digitone II Track 8）で使用する SongModel fixture の用途と現在の検証範囲を整理したものです。

記載対象は現在安定化している subset のみです。プロダクト全体の方針順序（Cloud > Bass > Chord）を定義する文書ではありません。

## フィクスチャ詳細

### Demo Cmaj7

- title: Demo Cmaj7
- file: `examples/song_models/demo_cmaj7.changes.yaml`
- musical shape: 4/4 1小節、Cmaj7 harmony event 1件
- chord events: 1
- expected Track 8 note rows: 6
- intended validation purpose: export 経路と CLI 基本動作の quick smoke test
- hardware validation status: hardware 検証なし

### Demo II V I

- title: Demo II V I
- file: `examples/song_models/demo_ii_v_i.changes.yaml`
- musical shape: 4/4 1小節に Dm7 -> G7 -> Cmaj7
- chord events: 3
- expected Track 8 note rows: 18
- intended validation purpose: export/check/dry-run/guarded real-send ワークフローの既知ベースライン
- hardware validation status: Digitone II で hardware 検証済み（Dm7 step1, G7 step5, Cmaj7 step9）

### Demo Multibar Turnaround

- title: Demo Multibar Turnaround
- file: `examples/song_models/demo_multibar_turnaround.changes.yaml`
- musical shape: 2/4 2小節に4つの harmony event
- chord events: 4
- expected Track 8 note rows: 24
- intended validation purpose: ソフトウェア export/check/dry-run の multi-bar 回帰
- hardware validation status: hardware 検証なし

### Demo Multisection Form

- title: Demo Multisection Form
- file: `examples/song_models/demo_multisection_form.changes.yaml`
- musical shape: 4/4 8小節、A section -> B section
- chord events: 8
- expected Track 8 note rows: 48
- intended validation purpose: multi-section SongModel の export/manifest 回帰
- hardware validation status: hardware 検証なし

## フィクスチャ選択ガイド

- quick smoke test: `demo_cmaj7`
- 既知の hardware 検証済みパス: `demo_ii_v_i`
- multi-bar 回帰: `demo_multibar_turnaround`
- multi-section 回帰: `demo_multisection_form`