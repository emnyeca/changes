# Roadmap

この roadmap は Changes の開発ステージ計画を示します。日付は目安であり、testing と feedback に応じて変更される可能性があります。

## Phase 1: Core Engine (Q2 2026)
- common format（YAML、iRealPro export）から progression を読む chord parser を構築する。
- chord を tension 付き six-note texture に展開する voicing rule を実装する。
- voicing 間の motion を最小化する voice-leading module を実装する。
- MIDI file 生成または Digitone II への realtime MIDI 送信を行う command-line interface を提供する。

## Phase 2: Performance Integration (Q3 2026)
- record-to-Digitone II workflow を自動化する high-tempo recording utility を追加する。
- 曲選択と voicing export のための quick-selection script または minimal GUI を開発する。
- blues、rhythm changes、ballad など song form 別の preset template を用意する。
- performance setup 別の track assignment profile を用意する。

## Phase 3: Extended Features (Q4 2026)
- user-configurable な voicing preference と tension set を導入する。
- multi-port MIDI により追加の synthesizer / sampler をサポートする。
- dynamic filter sweep や LFO などの effects automation を generated sequence に統合する。
- curated voicing 付きの example progression library を追加する。

## Phase 4: Polishing and Community (2027)
- video demonstration を含む documentation / tutorial を改善する。
- DAW や plugin format との integration を提供する。
- 演奏者の feedback を取り込み、feature request を反映する。
- 拡張 improvisation に向けた live-coding / generative variation を検討する。

各ステージで community からの contribution を歓迎します。toolkit を試しながら issue や pull request を送ってください。

## Documentation Balance TODO

Cloud / Bass / Chord と Track 8 の文書比重調整タスクは次を参照してください。

- `docs/status/cloud-bass-chord-doc-rebalance-todo-20260531.md`
