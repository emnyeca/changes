# Track 8 Product-like Pattern Settings 仕様

## 目的

この文書は、Chord export（Digitone Track 8）における product-like Digitone pattern settings の判断を定義します。

この文書自体はこれらの settings を実装しません。

## scope

この仕様は、product-like Chord export（Digitone Track 8）の target behavior を対象にします。

hardware behavior は検証しません。

SysEx generation は変更しません。

bundle planner behavior は変更しません。

## context

Track-8-only fixture では、Track 1-7 が intended product default output spec ではなく base empty template default に依存することが分かっています。
これは Track-8-only fixture としては想定内です。Changes は active track の event のみを emit し、それ以外の default は template が供給します。

これは Digitone Track 8 の Chord trigger bug ではなく、product-readiness gap として扱います。

## decisions

### decision 1: LENGTH / SPEED / CHANGE / RESET modes

Product-like export は次に PER TRACK mode を使います。

- LENGTH
- SPEED
- CHANGE
- RESET

これは `docs/digitone-internal-spec.md` の既存 target です。

- pattern.mode = per-track
- Track 1..8 LENGTH = Changes-computed total_steps
- Track 1..8 SPEED = Changes-computed speed
- pattern-shared CHANGE = OFF
- pattern-shared RESET = INF

Product-like export は既存設計に従って per-track mode を使います。

理由:

Digitone Track 8 の Chord export は、Track 1-7 から独立した length / speed を必要とします。
global / shared mode では、Track 8 の Chord behavior が無関係な track に影響します。

### decision 2: Track 1-7 VEL default

Track 1-7 trigger-level VEL は trigger record level では `inherit` を使い、`src/changes/models/digitone_target_profile.py` にある track_default_velocity table に fallback します。

- Track 1: 70
- Track 2: 70
- Track 3: 70
- Track 4: 50
- Track 5: 70
- Track 6: 50
- Track 7: 100

この値は `default_digitone_target_profile()` に定義済みです。推測は不要です。

理由:

Track 1-7 VEL は default output profile の一部であり、Track 1-7 event が存在する場合に適用されます。

### decision 3: Track 1-7 LEN default

Track 1-7 trigger-level LEN は固定の per-track default value ではありません。
`length_strategy = hold_until_next_event` により event ごとに計算されます。
各 trigger は duration_quarters から導出した explicit length_code を持ちます。

定義すべき単一の "Track 1-7 default LEN" はありません。

exported pattern に Track 1-7 event が含まれない場合、loaded pattern の Track 1-7 LEN state は Changes ではなく base empty template 由来です。

OPEN: event が emit されない場合の Track 1-7 に対する base empty template LEN state は未確認であり、検証が必要です。

理由:

LEN は Cloud / Bass voice の event-level property です。Changes は hold_until_next_event から LEN を計算します。固定 per-track fallback は Cloud engine model には適用されません。

### decision 4: Track 8 defaults

Track 8 は Track 1-7 とは別 policy を持ちます。

- note velocity は ChordRealizationResult.velocities 由来（例: Cmaj7 は 70 70 70 50 70 50）
- explicit note length は event duration_quarters -> length_code 由来
- micro timing default は 0
- note order は realized chord note order を保持
- same-step chord trigger record は toolkit / device limit（16 notes）まで許可

Track 8 は Chord note に Track 1-7 default VEL / LEN を使いません。

理由:

Track 8 の Chord note は chord realization model 由来の musically intentional な per-note velocity / length を持ちます。Track 1-7 default で上書きしてはいけません。

### decision 5: product-like default の ownership

Changes:
  product export profile と template policy を選ぶ
  musical event row を emit する
  chord note order、velocity、length mode、duration、timing を保持する
  events YAML exporter に track_default_velocity table を供給する

digitone-syx-toolkit:
  template / default pattern data を適用する
  toolkit-loadable events YAML を SysEx に変換する
  low-level Digitone encoding details を所有する
  events YAML の track_defaults.velocity を受け取る

template file:
  product-like Digitone pattern state を保持する
  PER TRACK mode と baseline track default を含むべきである
  toolkit builder の starting state として読み込まれる

理由:

PER TRACK mode と default track behavior は Digitone pattern state であり、純粋な musical rendering data ではありません。これは template / toolkit layer の責務であり、Changes は policy choice を供給します。

### decision 6: default template policy

使用するもの:

bundled product-like default template + optional user-supplied template

basic export で user に template 供給を要求しません。

ただし advanced user は template を指定できるべきです。

OPEN: digitone-syx-toolkit bundled の current base empty template は PATTERN-wide mode を設定します。別の PER TRACK template source は未決定です。

理由:

bundled template は reproducible default output を与えます。optional user template は workflow の拡張性を保ちます。user に template を要求すると、最初に使える export までの難度が上がりすぎます。

### decision 7: bundle planner との関係

Product-like pattern settings は export profile / template concern として扱い、bundle planner の musical allocation concern とは分離します。

Bundle planner:
  musical allocation を決める
  pattern / section / track placement を決める

Product-like export profile/template:
  Digitone pattern initialization を決める
  PER TRACK mode を決める
  baseline LEN / VEL default を決める
  device-specific starting state を決める

理由:

bundle planner は device initialization policy の責務を持つべきではありません。

## product-like target settings table

| Setting | Target | Owner | Status |
|---|---|---|---|
| LENGTH mode | PER TRACK | template/toolkit | decided |
| SPEED mode | PER TRACK | template/toolkit | decided |
| CHANGE mode | PER TRACK (OFF) | template/toolkit | decided |
| RESET mode | PER TRACK (INF) | template/toolkit | decided |
| Track 1-7 VEL | {1:70,2:70,3:70,4:50,5:70,6:50,7:100} | Changes track_default_velocity | decided |
| Track 1-7 LEN | event-level via hold_until_next_event | Changes events | decided |
| Track 1-7 LEN (template default) | base empty template state when no events | template | OPEN |
| Track 8 LEN | chord event length_code | Changes events + toolkit | decided |
| Track 8 VEL | ChordRealizationResult.velocities | Changes chord realization | decided |
| Track 8 micro timing | 0 by default | Changes event model | decided |
| Track 8 note order | preserve realized order | Changes event model | decided |
| Template policy | bundled default + optional user template | Changes/toolkit boundary | OPEN (PER TRACK template source) |
| Bundle planner relation | separate from device initialization | architecture | decided |

## open verification items

この仕様を完了するには、次の項目を検証する必要があります。

1. LENGTH / SPEED / CHANGE / RESET の PER TRACK mode を events YAML で表現できるか。
2. できる場合、どこで表現するか。
3. できない場合、toolkit、template file、Changes のどこに support を追加するか。
4. Track 1-7 VEL default を events YAML の track_defaults.velocity で表現できるか。
5. できる場合、built SysEx へ正しく伝播するか。
6. event が emit されない場合、base empty template は Track 1-7 にどの LEN state を設定するか。
7. toolkit に PER TRACK template が既にあるか。
8. build_syx_from_events(..., template_file=None) は base empty template を使うか。
9. 使う場合、どの PER TRACK / LEN / VEL state を含むか。
10. Changes は explicit PER TRACK template file を渡すべきか。

## scope boundary

この仕様は次を行いません。

- PER TRACK mode の実装
- toolkit behavior の編集
- new SysEx の生成
- new fixture file の生成
- existing fixture の変更
- hardware validation
- bundle planner の変更
- UI の変更
