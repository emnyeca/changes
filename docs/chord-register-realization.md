# Chord Register Realization (Phase 2)

この文書は Changes における independent Chord engine の Phase 2 を説明します。

## Separation from Cloud

Chord は vertical chord layer であり、Cloud moving voices とは別物です。

- Cloud: context-aware moving six-voice texture with continuity across events.
- Chord (Phase 2): independent per-occurrence vertical realization from pitch classes.

本フェーズでは Cloud voice-lane continuity や previous-chord minimum-motion repair は利用しません。

## Register

Chord register は MIDI `48..69` に固定します。

- `48` = Digitone display `C4`
- `69` = Digitone display `A5`

realized された Chord note はすべてこの範囲内でなければなりません。

## Realization algorithm

realization algorithm は deterministic です。

1. stack
2. octave-fold
3. ascending-sort

### 1) Stack

chord stacking の順序は `ChordConstructionResult.final_pitch_classes` の順序を使用します。

- First note: lowest matching MIDI at or above register minimum.
- Following notes: lowest matching MIDI strictly above the previous stacked note.

### 2) Octave-fold

register maximum を超える stacked note は、範囲に入るまで 12 を減算します。

- Pitch class is preserved.
- No chromatic substitution.

### 3) Ascending-sort

fold 後の note を MIDI 昇順でソートし、6 つの distinct note を返します。

6 つの distinct かつ in-range な note を生成できない場合、realization は明示的な error を返します。

## Root-position preservation and inversion behavior

canonical stack がすでに範囲内ならそのまま保持します。
範囲外の場合は octave folding の結果として inversion が発生し得ますが、これは register bounds に基づく deterministic な結果です。

## Velocity policy (modeled)

Phase 2 では low-to-high の per-note profile を model 化します。

- `70, 70, 70, 50, 70, 50`

velocity は最終的な MIDI 昇順ソート後に割り当てます。

これは Cloud の lane identity でも track assignment でもありません。

## Length policy (modeled)

Phase 2 で model 化するのは Chord の length mode のみです。

- `explicit_event_length`
- `inherit`

本フェーズでは duration-to-event conversion は行いません。

## Deferred integration

以下は deferred のままです。

- Renderer integration
- Track 8 output mapping
- MIDI export integration
- Digitone export integration
- bundle planning / trigger capacity integration
