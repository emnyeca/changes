# プロダクトアーキテクチャ

## プロダクト方向性

EUB Changes は、iReal Pro または MusicXML 由来の楽曲データを Digitone II の machine-live performance material に変換することを目指します。

```text
iReal Pro
  -> MusicXML export
  -> internal song/harmony model
  -> machine-live-friendly note layers
  -> Digitone II tracks
```

プロダクト方針順序:

- Cloud > Bass > Chord
- Track 1-6 > Track 7 > Track 8

## レイヤーモデル

| Digitone II Track | Layer | Role | Product priority | Current status |
| --- | --- | --- | --- | --- |
| Track 1-6 | Harmony Cloud | 主演奏レイヤーとしての six-voice playable harmony cloud | Primary | architecture target / partial implementation |
| Track 7 | Bass | root movement / slash-bass の grounding layer | Secondary | architecture target / partial implementation |
| Track 8 | Chord | chord reference / helper layer | Additional | current RC-stabilized workflow |

## この順序の意味

Track 1-6 Harmony Cloud は主要な音楽出力です。演奏時の和声テクスチャを担う playable な machine-live 素材として扱います。

Track 7 Bass は grounding を担います。低域で和声を支え、Cloud を置き換えるのではなく補強します。

Chord（Digitone Track 8）は和声参照・補助制御に有効ですが、プロダクトの主出力そのものではありません。

## 内部パイプライン観

リポジトリには、より広いアーキテクチャの要素がすでに存在します。

- internal song/harmony model への MusicXML import
- harmonic-context 解決と six-note harmony 抽出
- bounded voicing と bass rendering
- より広い track 指向 export に向けた Digitone bundle compilation パス

ただし、現在安定化している hardware-facing workflow はより限定的です。

- SongModel YAML
- Chord export（Digitone Track 8）
- SysEx check
- manifest-aware validation
- dry-run send
- guarded real-send

この RC パスは重要な検証済み subset ですが、上位プロダクトアーキテクチャ配下の位置づけであり、プロダクト全体定義ではありません。

## ドキュメントマップ

- `current-state.md` は、目標方向と実装・検証 subset を分けて扱います。
- `e2e-user-workflow.md` は、現在の Chord RC ワークフロー（Digitone Track 8）のみを扱います。
- `validation-matrix.md` は、現在 RC subset の検証深度を追跡します。