# Harmony Cloud Voicing & Duration Rules

このドキュメントでは、Harmony Cloud が **ジャズコード進行を 6 声のハーモニー「雲」** に変換するための規則を詳細に定義します。これは実装の仕様書であり、コードとスケールの解釈、声部の割り当て、最小音程移動のボイスリーディング、Digitone II への録音タイミングの計算などの指針を示します。日常的なコード伴奏ではなく、マシンライブでリアルタイムにレイヤーを増減できるように設計されています。

## 1. 用語の整理

Harmony Cloud では以下の 4 層を明確に区別します。

| 層 | 説明 |
|---|---|
| **Chord Symbol** | 入力されるコード表記。例: `Dm7`, `G7b13`, `Cmaj7`, `Gaug7` |
| **Local Pitch Collection** | 前後のコードと現在コードの構成音を合わせて得る音集合。コードが 2 つ以上連続する場合、同じコードは 1 回と数える。Slash bass はこの集合に加える。|
| **Selected Scale Collection** | 上記の音集合を完全に含むスケール。局所的なドリアン集合、ハーモニックマイナー集合などから優先順位順に選ぶ。スケール名はルート名を含まなくてもよい。例: D ドリアンの音集合を G mixolydian モードとして扱う。|
| **Output Chord Tone Set** | 実際に鳴らす 6 音。基本は 1, 3, 5, 6/13, 7, 9。モード名に関わらず、Selected Scale Collection から度数を抽出する。13 は 5 と 7 の間に配置する。|

### スケール優先順位

Local Pitch Collection を完全に含むスケール候補を以下の順位で選びます。欠損音や余剰音があってもペナルティ処理は用いません。**完全一致する最高順位のスケール**を採用します。スケール名はあくまで判断に使うだけで、出力音は度数の指定によって決まります。

1. **Diatonic / Dorian collection**  
   ドリアンを筆頭とするダイアトニック 7 音集合。例: C Ionian / D Dorian など。

2. **Harmonic minor collection**  
   ハーモニックマイナー由来の 7 音集合。例: C harmonic minor = C D Eb F G Ab B。

3. **Melodic minor collection & Lydian dominant**  
   メロディックマイナー系列および Lydian dominant など。オルタードテンションや #11, b9 を含むドミナントに使用する。

4. **Whole tone collection**  
   全音音階。構成音が 6 音であるため、1, 3, 5, 6, 7, 9 の全てが得られる。

5. **Half-whole / Whole-half diminished**  
   減七音階から派生する 8 音集合。half-whole は 1 b3 b5 6 b7 b9 など、whole-half は 1 b3 b5 6 7 9 などに分かれる。

6. **Chromatic collection**  
   12 音全て。どうしても当てはまるスケールが無い場合の最後の選択肢。Chromatic が選ばれた場合でも度数は 1, 3, 5, 6, 7, 9 を優先し、基本構成音から補完する。

スケール候補が複数ある場合は上記順位で決めます。

例えば `G7` の前後が `Dm7` と `Cmaj7` なら、local collection は C D E F G A B です。これは **D Dorian** が最優先集合なので、`G7` の Selected Scale Collection は D ドリアン、Output Chord Tone Set は G mixolydian モードと同等の 1, 3, 5, 6, 7, 9 になります。

ルートが異なるモード名を意識する必要はありません。自然 9 と 13 を選び、altered テンションは含みません。

### スケール決定の例外

- **前後のコードが同一**  
  同じコードが続く場合、それらは一つのコードとみなし、さらに一つ先または後の異なるコードを参照します。曲頭や終端では **progression is circular** をデフォルトとして、フォームの最後のコードを遡って参照します。

- **進行が 1 コードだけ**  
  現在コード単体から local collection を作り、最優先スケールを選びます。例えば `Dm7` だけなら D ドリアンを用います。

- **Slash コード**  
  `/` 以降のベース音は local collection に加えますが、出力音のルートには影響しません。`C/E` の場合、Selected Scale は C Ionian になり、出力は Cmaj13(9) となります。

- **Enharmonic spelling**  
  表示上は常にフラット系の 12 音を用います。

```text
C Db D Eb E F Gb G Ab A Bb B
```

入力の D# や E# などはすべてフラット側に変換して解釈します。

## 2. 出力されるコードトーンセット

Harmony Cloud は各コードイベントに対して常に **6 音** を出力します。

基本形は以下です。

```text
1 - 3 - 5 - 13 - 7 - 9
```

13 は 5 と 7 の間に配置します。

| 入力コード例 | Selected Scale | Output Chord Tone Set |
|---|---|---|
| `Cmaj7` | C Ionian | C E G A B D |
| `Dm7` | D Dorian | D F A B C E |
| `G7` | D Dorian = G mixolydian | G B D E F A |
| `G7b13`, `Gaug7` | C harmonic minor | G B D Eb F A |
| `Cm7` | C Dorian | C Eb G A Bb D |
| `Dm7b5` | F Dorian | D F Ab B C E |
| `C7sus4` | C mixolydian → add4 置換 | C F G A Bb D |

### Sus コードの処理

`sus` と付くドミナントは **3rd を 4th へ置き換え**、add3 を許可します。

ギター的に自然な `C7sus4(add3)` をモデルとして、以下の出力になります。

- 4th は 3rd の代わり。
- 3rd を保持する場合は 5th を削除して `1 - 3 - 4 - 6 - b7 - 9` の 6 音にします。

デフォルトは 4th への置換です。将来オプションとして `allow_sus_add3 = true` を実装予定です。

### Diminished / Half-diminished の処理

- `m7b5` は前後の文脈から local collection を作り、最優先スケールを選びます。
- `Dm7b5 | G7b9 | Cm` のようなマイナー II-V-I では C harmonic minor に一致するため、`Dm7b5` でも `G7b9` でも C ハーモニックマイナー系列の度数を用います。
- `dim7` などは減七音階、つまり half-whole / whole-half が選ばれる可能性がありますが、MVP では後回しにし、サポート外を知らせます。

## 3. ボイシングと声部割り当て

### 初期ボイシング

- 出力 6 音は **2 オクターブ以内、C3 から B4** に収まるクローズドボイシングから始めます。
- 最初のコードでは `(1 - 3 - 5 - 13 - 7 - 9)` の度数順で昇順に配置します。
- Range を外れる場合は全体をオクターブ上下にシフトして収めます。

### ボイスリーディング

- 次のコードへ移るとき、各トラックは前回の音から **最小半音移動** を優先します。
- 同じ音が複数トラックに割り当てられた場合は、空いている音へ移動して重複を解消します。
- 基準音、例えば C3 より高い音が空いている場合は **下** へスライドし、低い音が空いている場合は **上** へスライドします。
- 音域を超えた場合は全体をオクターブ単位でシフトして範囲内に収めます。
- 声部交差は許容しますが、重複解消時に滑らかな配置になるよう調整します。
- 各トラックには機能、たとえば root, third などを固定しません。
- ミュートやボリューム操作で骨格を抽象化できるよう、**機能より声部移動を優先**します。

## 4. Duration 規則と Digitone II 録音

### コード進行の表現

YAML 入力ではコード名の配列を 1 小節として扱います。

```yaml
time_signature: "4/4"
progression:
  - [Dm7, G7]    # 4/4 小節内で Dm7→G7
  - [Cmaj7]      # 次の 1 小節
```

配列の長さがその小節に含まれるコード数を表し、**等分割**します。

上記例では Dm7, G7 が各 2 拍ずつ、Cmaj7 が 4 拍になります。

奇数拍子や素数拍子の場合でも同様に割り算します。

- 3/4 で `[Dm7, G7, Cmaj7]` なら、各コードの duration は 1 拍。
- 4/4 で `[Dm7, G7, Cmaj7]` なら、各コードの duration は 4/3 拍、つまり約 1.333 拍。
- 3/4 で `[Dm7, G7]` なら、各コードの duration は 1.5 拍。

1 拍未満でも step 計算で扱えます。

### Digitone II のステップとテンポ計算

Digitone II はステップ単位で録音します。

各ステップを 8 分音符、つまり `Speed = 1/8` とし、**Length** と **Tempo** を調整して小節内のコードを正確に並べます。

- 1 小節に `n` コードある場合、**minimum step count = bar length × n** です。
- 4/4 のバーに 2 コードなら、4 × 2 = 8 ステップ。
- 3/4 のバーに 2 コードなら、3 × 2 = 6 ステップ。
- 1 ステップが 8 分音符なので、Speed 1/8 のままコード数に合わせてテンポを調整します。
- テンポの最小値は 30 BPM とします。
- それ以下に下げる必要がある場合は **Length** を倍にしてテンポを 30 に戻します。

#### 例: 4/4、テンポ 120 BPM、`[Dm7, G7]`

4/4 で `[Dm7, G7]`、テンポ 120 BPM の場合は 2 コードなので 8 ステップ必要です。

4/4 の 8 分分解能は 8 ステップに収まるので、Digitone では以下の設定にします。

```text
Tempo  = 60
Length = 4
Speed  = 1/8
```

テンポは半分に下げますが、録音は高速で行われるため、後に実際のテンポに戻します。

#### 例: 3/4、テンポ 60 BPM、`[Dm7, G7]`

3/4 で `[Dm7, G7]`、テンポ 60 BPM の場合は 6 ステップ必要です。

Digitone が 8 ステップ単位しかサポートしない場合は、以下のような調整をします。

```text
Tempo  = 45
Length = 4
Speed  = 1/8
```

これは最小に近い設定として扱い、後からテンポを戻します。

#### 例: 30 BPM 以下になる場合

30 BPM 以下になる場合は倍長にして対応します。

例えばテンポ 30 で `[Dm7, G7]` なら、以下のようにします。

```text
Tempo  = 30
Length = 8
Speed  = 1/8
```

各コードを 2 ステップ、つまり 16 分音符相当の細かさに割り当てます。

### 録音手順

1. Digitakt II から Digitone II に DIN MIDI clock を送ります。
2. Digitone II はクロックに従います。
3. PC またはスクリプトからは USB MIDI を用いて note 情報のみ送ります。
4. Harmony Cloud で progression を解析し、各コードを最小移動ボイスで展開します。
5. 必要ステップ数と Tempo / Length / Speed 設定を計算します。
6. Digitone II を録音待機にします。
7. 超高速 tempo で全コードを録音します。
8. 録音が完了したら tempo を実際のライブ BPM に戻します。
9. ライブでは各トラックをミュート / アンミュートして骨格を抽象化し、レイヤーを増減させながら演奏します。

## 5. フォールバックと例外

- 未対応のコード表記、例えば `G13b9#11`, `Cadd11` などは、ルートのみから local collection を作り、最も近いスケールを選びます。
- 必要な度数が不足する場合は diatonic / dorian を仮定します。
- スケールに 7 音以上含まれていても、出力は常に 6 音です。
- 欠けている度数は Current Chord Symbol から補います。
- どうしても決まらない場合は **C ドリアン** を用います。
- diminished 系や altered 系を細かく解釈するのは Phase 2 以降の拡張とし、MVP では範囲外を警告します。
- Intro / Ending / Tag などセクション区別は将来の拡張とし、現時点では progression をそのまま処理します。

## 6. 例

### Blue Moon の冒頭、キー C

| 入力 | Local Pitch Collection | Selected Scale | Output Chord Tone Set |
|---|---|---|---|
| `Cmaj7` | C E G B | C Ionian | C E G A B D |
| `Am7` | A C E G。前後に Cmaj7, Dm7 → C D E F G A B | D Dorian → A Aeolian | A C E F# G B |
| `Dm7` | D F A C → C D E F G A B | D Dorian | D F A B C E |
| `G7` | G B D F → 同上 | D Dorian | G B D E F A |

### Chameleon、一発もの Bm7

現在コードだけを使うので local collection は B D F# A です。

B dorian、つまり B C# D E F# G# A が完全一致するので Selected Scale は B dorian です。

Output Chord Tone Set は以下になります。

```text
B D F# G# A C#
```

ここから最小移動によって各コードの発展を実装します。

## 7. 今後の拡張

- **より多様なコード表記**  
  mMaj7、ø7、alt、sus2、add11 などへの対応を段階的に増やす。

- **機能別ペナルティ**  
  声部交差や 3rd / 7th の解決優先を重みづけするアルゴリズムへの発展。

- **Intros / Tags**  
  セクション分けされた進行のサポート。

- **iRealPro インポーター**  
  XML / MIDI を中間 YAML に変換するプラグインを追加。

- **リアルタイムエディタ**  
  CLI と連携し、実行中に音程やスケール選択を変更できるインタラクティブモード。

---

この仕様は Phase 1: Core Engine の実装のために策定されました。今後のフィードバックや実機検証に応じて更新されます。
