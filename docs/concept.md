# Concept

## Purpose

Changes は、jazz standard や progression から 6 声の chord cloud を生成し、live machine-jazz performance で使える形にすることを目的とします。シンプルな chord progression を、Generic MIDI playback と Digitone II Native SysEx generation に適した豊かな harmonic texture に変換する composition/performance tool です。

## Approach

- **Chord Parsing:** chord sequence（例: iRealPro export）を読み取り、scale degree と function の観点で解釈します。
- **Voicing Expansion:** 各 chord を tension（9, 11, 13）や 6th を含む six-note voicing に展開します。6/9、9/13、sus4 などの chord quality は voicing rule で決定します。
- **Voice Leading:** 各 note を個別 track に割り当て、隣接 chord 間の motion を最小化します。3rd / 7th など優先度の高い tone は期待どおりに解決し、tension は変化をまたいで保持される場合があります。
- **Performance Layer:** track mute / level control により dense voicing を shell、ambient pad、broken chord のような表現へ抽象化します。これにより演奏者は improvise 中に harmonic layer を出し入れできます。
- **Backend Split:** 広い互換性のため Generic MIDI export/realtime send を維持しつつ、Digitone II pattern 出力には Native SysEx backend を使用します。

## Design Goals

- **Deterministic:** 同じ input から常に同じ voicing を生成します。
- **Musically Informed:** voice-leading rule と tension 選択は jazz harmony の概念に基づきます。
- **Modular:** chord parsing、voicing rule、MIDI output などをモジュール化し、将来拡張しやすくします。
- **Performance-Focused:** live Embient session を前提に、reliability と deterministic output を優先します。
