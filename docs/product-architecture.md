# プロダクトアーキテクチャ

## プロダクト方向性

EUB Changes は、楽曲データを Digitone II の machine-live performance material に変換することを目指します。

楽曲データの入力源は2種類あります。

```text
【ファイル入力】
iReal Pro
  -> MusicXML export
  -> SongModel

【直接入力】
GUI Editor
  -> EditorState
  -> SongModel
```

どちらも SongModel に変換された後、共通パイプラインを通ります。

```text
SongModel
  -> RenderedArrangement (Cloud / Bass / Chord)
  -> RenderedTimeline (trigger policy 適用済み)
  -> Digitone II tracks
```

EUB Changes は、Cloud / Bass / Chord の各レイヤーを生成し、用途に応じて単独または組み合わせて使える machine-live workflow を目指します。

## 画面構成（計画）

将来のアプリ全体は次の3画面構成を想定します。

```text
[ Generate / Send ] [ Editor ] [ その他 ]
```

- **Editor:** コード進行の直接入力と SongModel への変換
- **Generate / Send:** レンダリング・export・Digitone への送信
- **その他:** 設定、ログ、など

現在実装済みの範囲: Editor の入力モデル（EditorState）と SongModel への変換ロジック。GUI シェルは未実装。

## レイヤーモデル

| Digitone II Track | Layer | Role | Current status |
| --- | --- | --- | --- |
| Track 1-6 | Harmony Cloud | six-voice playable harmony texture | generation implemented; product export command added; hardware validation pending |
| Track 7 | Bass | root movement / slash-bass grounding layer | generation implemented; product export command added; hardware validation pending |
| Track 8 | Chord | symbol-faithful vertical layer | generation implemented; current RC-stabilized workflow |

## レイヤーの役割

Track 1-6 Harmony Cloud は主要な音楽出力です。演奏時の和声テクスチャを担う playable な machine-live 素材として扱います。

Track 7 Bass は grounding を担います。低域で和声を支え、Cloud を置き換えるのではなく補強します。

Chord（Digitone Track 8）は chord symbol に忠実な vertical layer として、現在の RC-stabilized workflow を担います。

## 内部パイプライン観

リポジトリには、より広いアーキテクチャの要素がすでに存在します。

- `EditorState` から `SongModel` への変換（Editor 直接入力経路）
- internal song/harmony model への MusicXML import
- harmonic-context 解決と six-note harmony 抽出
- `RenderedArrangement` 上での Cloud / Bass / Chord layer 生成
- layer 別 trigger policy（`RenderProfile`）を flatten 時に適用
- `RenderedArrangement` から Track 1-8 product timeline への flatten / compile path
- `changes export digitone-product` による layer 選択可能な product artifact export
- より広い track 指向 export に向けた Digitone bundle compilation パス

ただし、現在安定化している hardware-facing workflow はより限定的です。

- SongModel YAML
- Product export（Digitone Tracks 1-8）
- SysEx check
- dry-run send
- guarded real-send

この RC パスは重要な検証済み subset ですが、上位プロダクトアーキテクチャ配下の位置づけであり、プロダクト全体定義ではありません。

## ドキュメントマップ

- 主要概念・モデル契約: `concept.md`
- 現在状態と計画: `current-state.md`
- Chord RC ワークフロー手順: `e2e-user-workflow.md`
- 検証マトリクス: `validation-matrix.md`
