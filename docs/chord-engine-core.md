# Chord Engine Core

この文書は、Changes における Phase 1 の Chord Engine 実装範囲を示します。

## Engine separation

Changes の音楽レイヤーは概念上、次の 3 層に分かれます。

- Cloud: 既存の context-aware な 6 声ハーモニーレイヤー
- Chord: 新規の chord symbol 忠実な 6 音レイヤー
- Bass: 既存の slash bass / root ベースレイヤー

本フェーズで実装するのは pure Chord construction core のみです。Cloud rendering、Bass behavior、Digitone export、MIDI export、既存の generated artifacts は変更しません。

## Phase 1 scope

Phase 1 は pitch-class construction までを対象にします。

- chord symbol の parse / normalize
- chord symbol で必須となる tone の保持
- 選択された Local Pitch Collection から deterministic に tension を補完
- 後続 renderer integration 用 diagnostics の返却

MIDI octave、register、velocity、length、Track 8 slot、export format detail はこのフェーズでは決定しません。

## Chord construction rule

Chord construction は次の 3 ルールに従います。

1. Keep the tones explicitly written by the chord symbol.
2. Add only tensions that exist in the selected Local Pitch Collection.
3. Stop once six distinct pitch classes are available, or raise a clear error if six cannot be reached.

`b9` や `#9` のような explicit alteration は mandatory chord content として保持します。

symbol-faithful な Chord output では、`b9` / `#9` / `#11` / `b13` が明示されている場合、同じ extension family で衝突する variant の自動追加を抑制します。`alt` quality は複合 altered color を意図するため例外として扱います。

## Integration warning

Chord の automatic tension filling では、scale selection 時の local constraint pitch-class set ではなく、selected ScaleCollection の pitch classes を使用する必要があります。

現行の harmonic context model では次を守ってください。

- use `RetryResolution.selected_collection.pitch_classes`
- do not use `RetryResolution.local_pitch_collection`
- do not use `RetryResolution.final_local_pitch_collection_used_for_selection`

local constraint set は scale を選ぶための集合であり、6-note chord output を完成させるために必要な tension を必ずしも含みません。

## Plain sus4 convention

Changes では jazz-chart context において plain `sus4` を dominant-suspended harmony として扱います。

- `Csus4` normalizes to `C7sus4`
- existing `C7sus4`, `C9sus4`, and `C7b9sus4` forms remain supported

## Later work

後続フェーズでは次を追加可能です。

- register realization
- Track 8 output
- VEL policy
- LEN policy
- renderer integration
- Digitone export integration

この文書は、Track 8 output がすでに Changes に実装済みであるとは主張しません。