# Digitone II セットアップ

### MIDI ルーティング

- **クロックソース:** Digitakt II をマスタークロックとして使用します。Digitakt II の DIN MIDI OUT を Digitone II の DIN MIDI IN に接続し、テンポとトランスポート信号を安定して受信できるようにします。
- **ノート入力:** PC または Raspberry Pi を USB MIDI で Digitone II に接続します。Digitone II の MIDI 設定で、clock receive を **MIDI**（DIN）、note receive を **USB** に設定します。これにより、クロックは DIN、ノートは USB で受け取れます。
- **ポート設定:** MIDI port 設定メニューで、Note は **USB**、Clock は **MIDI** を有効にします。Changes が生成するトラックチャンネル（1-6）と一致していることを確認します。

### トラック割り当て

Digitone II には 8 トラックあります。Changes は 6 voice を使うため、各 voice を別トラックに割り当てます。

1. **Track 1 (Voice 1):** 高い tension（例: 9th / 13th）を担当。pad や bell 系の音色が有効。
2. **Track 2 (Voice 2):** 3rd または 7th を担当。厚みのある FM chord 音色が有効。
3. **Track 3 (Voice 3):** 5th または sus4 を担当。金属的・パーカッシブな質感が有効。
4. **Track 4 (Voice 4):** 追加 tension（6th / 9th）を担当。filter sweep で動きを付ける。
5. **Track 5 (Voice 5):** sub または rootless bass を担当。暖かい sine 系パッチが有効。
6. **Track 6 (Voice 6):** 和声補助や cluster を担当。detune した operator や noise を試す。

Track 7 と 8 は空けておくか、drums / leads などに使えます。

### 録音ワークフロー

1. Digitone II 側で Track 1-6 を live recording 用にアームします。
2. 一時的にプロジェクト BPM を高く設定します（例: 600 BPM）。
3. 録音を開始し、Changes generator から USB MIDI で進行全体を送信します。6 voice が数秒で Track 1-6 に録音されます。
4. 進行送信が終わったら録音を停止し、BPM を演奏用テンポ（例: 100-120 BPM）へ戻します。
5. パターンを保存します。本番では track mute、level、filter、FX を使って harmonic cloud の出し入れを行います。

### サウンドデザインのヒント

- 各トラックで FM algorithm や operator mix を変え、音色分離とマスキング回避を行います。
- 軽い detune や chorus でステレオの広がりを作ります。
- 必要なトラックを reverb / delay に送って奥行きを出します。
- conditional trig や probability を使って、chord cloud の再トリガー時に動きを加えます。

### トラブルシュート

- トラックが同期しない場合は、Digitakt II のみがクロックマスターであることと、Digitone II の clock receive 設定を確認します。
- ノートが伸びすぎる場合は、amp envelope を短くするか、Changes generator 側の note length を調整します。
- 一部 voice が欠ける場合は、generator 側チャンネル割り当てと Digitone II 側トラック MIDI チャンネルが一致しているか確認します。
