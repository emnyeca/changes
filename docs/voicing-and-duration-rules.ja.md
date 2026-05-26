# Changes Voicing & Duration Rules

このドキュメントでは、Changes が **ジャズコード進行を 6 声のハーモニー「雲」** に変換するための規則を詳細に定義します。これは実装の仕様書であり、コードとスケールの解釈、声部の割り当て、最小音程移動のボイスリーディング、Digitone II への録音タイミングの計算などの指針を示します。日常的なコード伴奏ではなく、マシンライブでリアルタイムにレイヤーを増減できるように設計されています。

## 1. 用語の整理

Changes では以下の 4 層を明確に区別します。

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

Changes は各コードイベントに対して常に **6 音** を出力します。

基本形は以下です。

```text
1 - 3 - 5 - 13 - 7 - 9
```

13 は 5 と 7 の間に配置します。

注意:

- 上記は「出力スロット」の定義であり、臨時記号を固定する規則ではありません。
- 6/13 や 9 の実音は、Selected Scale Collection に依存して変化します。
- したがって m7 を機械的に m6/9 へ固定展開しません。

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

Diminished 系は MVP のスケール候補に含める。
ただし、出力する 6 音は通常の `1, 3, 5, 6, 7, 9` ではなく、diminished collection 専用の度数セットを使う。

- **Half-Whole Diminished collection**
  - 出力度数: `1, b3, b5, 6, b7, b9`

- **Whole-Half Diminished collection**
  - 出力度数: `1, b3, b5, 6, 7, 9`

このため、diminished 系では `3rd` や `5th` を通常の長短・完全音程として扱わず、collection 固有の 6 音セットをそのまま出力する。

## 3. ボイシングと声部割り当て

### 初期ボイシング

- 出力 6 音は **2 オクターブ以内、C3 から B4** に収まるクローズドボイシングから始めます。
- 最初のコードでは `(1 - 3 - 5 - 13 - 7 - 9)` の度数順で昇順に配置します。
- Range を外れる場合は全体を上下にシフトして収めます。

### ボイスリーディング

- 次のコードへ移るとき、各トラックは前回の音から **最小半音移動** を優先します。
- 同じ音が複数トラックに割り当てられた場合は、空いている音へ移動して重複を解消します。
- 基準音、例えば C4 より高い音が空いている場合は **上** へスライドし、低い音が空いている場合は **下** へスライドします。
- 音域を超えた場合は全体をシフトして範囲内に収めます。
- 声部交差は許容しますが、重複解消時に滑らかな配置になるよう調整します。
- 各トラックには機能、たとえば root, third などを固定しません。
- ミュートやボリューム操作で骨格を抽象化できるよう、**機能より声部移動を優先**します。

## 4. Duration 規則と Digitone II 録音

### 基本方針

Changes は、Digitone II へ録音するために、**小節単位で拍子に整合する最小ステップ数(Length)** を計算する。

実装上は、YAML の `sections[].progression`（または後方互換の `progression`）を「小節の配列」として扱い、各小節内のコードイベント数を用いて step grid を決める。

基本方針は以下。

1. 進行は必ず小節単位で扱う（`sections[].progression` または `progression: [[bar1...], [bar2...], ...]`）。
2. `Speed` は原則 `1/8` を固定で用いる。
3. 小節内コードイベント数の混在に対応するため、`steps_per_bar = lcm(各小節のイベント数)` を採用する。
4. 解析に使う tempo/拍子は UI 入力値を使用する（YAML の `tempo`/`time_signature` はファイル選択時の既定値として UI に反映）。
5. 拍子は tempo 換算に使う（同じ実時間を維持するため `tempo_out = tempo_in * (steps_per_bar / eighths_per_bar)`）。
6. 各イベントの音価（step数）は `duration_steps = steps_per_bar / その小節のイベント数`。
7. 全体 Length は `steps_per_bar * 小節数`。
8. 推奨 tempo が Digitone II の下限 30 を下回る場合のみ、tempo と Length と各 event の duration_steps を同倍率で倍化する。

### Step / Duration の計算

入力進行で小節ごとのイベント数が混在する場合、以下のように計算する。

さらに実際のトリガー割り当てでは、**同一トラックで同音程が連続する場合は再トリガーしない**。
この場合、最初の `note_on` だけを送信し、`duration` は次の音程変化まで加算して伸長する。

- 連続して同音程: `note_on` を省略（hold 扱い）
- 音程が変化: 旧音 `note_off` + 新音 `note_on`
- セクション終端: まだ鳴っている音を `note_off`

GUI ではこの挙動を切り替え可能:

- Hold Trigger ON: 同音連続は保持して再トリガーしない
- Hold Trigger OFF: 毎 Step で再トリガーする

Bass トラックは独立設定:

- 7本目の独立トラックとして扱う（6声トラックとは別）
- 音域は C1-B1 固定。はみ出す場合はオクターブ上下して範囲内に収める
- 既定は各コードのルートを送信。分数コードは `/` 右側のベース音を採用
- Bass Hold Trigger は 6声とは独立 ON/OFF（既定: OFF = 毎Step再トリガー）
- Root/Fifth 切替は独立 ON/OFF（既定: OFF）
- 同音連続が x 回続いたら 5度へ切替、さらに 5度が x 回続いたらルートへ戻す
  - x は GUI 数値設定
  - この Root/Fifth 切替は Hold Trigger 設定に関わらず適用
  - 分数コードで切替 ON の場合: 1音目のみ分数ベース音、その後はルート/5度サイクルへ移行

また GUI では 6 トラックそれぞれに MIDI Channel を設定できる。

- 初期値: Track1-6 は Channel 1-6
- Bass の初期値: Channel 9
- 設定値: `送らない` または 1-16
- 同一チャンネル重複割り当ても許可

GUI上では「Chord 6トラック設定」と「Bassトラック設定」を分離して表示する。

出力オクターブの既定値:

- Chord 6トラック: +1 octave
- Bassトラック: +2 octave

GUI から各グループを個別に `-4` から `+4` octave まで調整できる。

リアルタイム送信時は、ノートイベント送信に加えて MIDI Transport を同時送信する。

- 送信開始時: `Start`
- 送信終了時: `Stop`

### 例: Waltz (3/4, Tempo 120)

```yaml
name: "Waltz"
key: "F"
time_signature: "3/4"
tempo: 120
sections:
  - name: "A"
    progression:
      - [Fmaj7]
      - [A7, Dm7]
      - [Gm7, C7, Fmaj7]
```

- 小節内イベント数は `1, 2, 3`
- `steps_per_bar = lcm(1, 2, 3) = 6`
- 各イベント音価:
  - bar1: `6/1 = 6`
  - bar2: `6/2 = 3`
  - bar3: `6/3 = 2`
- 全体 Length: `6 * 3 = 18`

このときの推奨値:

```text
Digitone
tempo:120 Length:18 Speed:1/8
```

イベントログ（step開始位置）:

```text
Step:1  コード:"Fmaj7" [0:F3 duration:9] [1:A3 duration:6] ...
Step:7  コード:"A7"    [2:C#4 duration:3] ...
Step:10 コード:"Dm7"   [1:F3 duration:8] ...
Step:13 コード:"Gm7"   [0:G3 duration:2] ...
Step:15 コード:"C7"    (hold)
Step:17 コード:"Fmaj7" [3:A3 duration:2] ...
```

`(hold)` はその step で新規トリガーがないことを示す。

### 録音手順

1. Digitakt II から Digitone II に DIN MIDI clock を送ります。
2. Digitone II はクロックに従います。
3. PC またはスクリプトからは USB MIDI を用いて note 情報のみ送ります。
4. Changes で progression を解析し、各コードを最小移動ボイスで展開します。
5. 必要ステップ数と Tempo / Length / Speed 設定を計算します。
6. Digitone II を録音待機にします。
7. 超高速 tempo で全コードを録音します。
8. 録音が完了したら tempo を実際のライブ BPM に戻します。
9. ライブでは各トラックをミュート / アンミュートして骨格を抽象化し、レイヤーを増減させながら演奏します。

## 5. フォールバックと例外

- 必要な度数が不足する場合は diatonic / dorian を仮定します。
- スケールに 7 音以上含まれていても、出力は常に 6 音です。
- 欠けている度数は Current Chord Symbol から補います。
- どうしても決まらない場合は **C ドリアン** を用います。
- Intro / Ending / Tag などセクション区別は `sections` で扱える。重複するセクション名は `A`, `A2`, `A3` のように内部正規化する。

## 6. 例

### Blue Moon の冒頭、キー C

| 入力 | Local Pitch Collection | Selected Scale | Output Chord Tone Set |
|---|---|---|---|
| `Cmaj7` | C E G B。前後に G7, Am7 → C D E F G A B | C Ionian | C E G A B D |
| `Am7` | A C E G。前後に Cmaj7, Dm7 → C D E F G A B | C Ionian = D Dorian = A Aeolian | A C E F G B |
| `Dm7` | D F A C。前後に Am7, G7 → C D E F G A B | D Dorian | D F A B C E |
| `G7` | G B D F。前後に Dm7, Cmaj7 → C D E F G A B | G Mixolydian (C Ionian等価集合) | G B D E F A |

### Chameleon、一発もの Bm7

現在コードだけを使うので local collection は B D F# A です。

1コード m7 の既定選択では B dorian（B C# D E F# G# A）を採用します。

Output Chord Tone Set は以下になります。

```text
B D F# G# A C#
```

## 実装済み範囲と未対応範囲

現在の parser と和声生成の実装済み範囲:

- `maj7`, `m7`, `7`

未対応（将来対応）:

- altered
- sus
- diminished
- half-diminished
- slash chord の本格的和声ルール

ここから最小移動によって各コードの発展を実装します。

## 7. 今後の拡張

- **より多様なコード表記**  
  mMaj7、ø7、alt、sus2、add11 などへの対応を段階的に増やす。

- **Intros / Tags**  
  セクション分けされた進行のサポート。

- **iRealPro インポーター**  
  XML / MIDI を中間 YAML に変換するプラグインを追加。

---

この仕様は Phase 1: Core Engine の実装のために策定されました。今後のフィードバックや実機検証に応じて更新されます。
