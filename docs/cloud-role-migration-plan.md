# Cloud Role Migration Plan (Phase 3D)

## Problem Statement

legacy timeline renderer と target architecture の間に、semantic naming conflict があります。

Current target architecture:

- Cloud: context-aware moving six-voice texture
- Bass: root/slash-bass low note
- Chord: symbol-faithful vertical six-note chord

## 1. Current Legacy Behavior

現行の legacy renderer `render_timeline()` は、context-aware six-voice layer を次の naming で出力します。

- `role="chord"`
- `voice_id="chord_voice_1" ... "chord_voice_6"`

これは legacy naming です。semantic 的には、新しい Chord Engine output ではなく、旧来の Cloud-like behavior に相当します。

## 2. Target Behavior

将来的な timeline semantics は次を想定します。

- Cloud:
  - `role="cloud"`
  - `voice_id="cloud_voice_1" ... "cloud_voice_6"`
- Chord:
  - `role="chord"`
  - `voice_id="chord_note_1" ... "chord_note_6"`
- Bass:
  - `role="bass"`
  - `voice_id="bass"`

## 3. Why Immediate Migration Is Risky

`render_timeline()` で即時リネームすると、既存挙動への暗黙依存を壊すリスクがあります。主な依存先は以下です。

- tests and serialized fixtures
- exporters and downstream adapters
- MIDI and Digitone-related planning logic
- role/voice-id based mapping code

compatibility staging なしの直接リネームは、気づきにくい output change を引き起こす可能性があります。

## 4. Recommended Staged Migration

推奨シーケンスは次のとおりです。

- Phase 3D: document and test current contracts
- Phase 3E: add optional profile flag or new renderer entrypoint for cloud role naming
- Phase 3F: update exporters to understand both legacy and new names
- Phase 3G: switch default naming after compatibility is confirmed
- Phase 3H: remove/deprecate legacy `chord_voice_*` naming if appropriate

## 5. Export Implications

- Generic MIDI export は note event のみを消費している場合、role-name change に耐えられる可能性があります。
- Digitone export と bundle planning は role/voice mapping への依存が高い可能性があります。
- Track 8 Chord export は legacy timeline の `role="chord"` event に依存すべきではありません。
- Track 8 Chord export は grouping、per-note velocity、length mode、diagnostics を保持する `RenderedArrangement.chord` を直接消費すべきです。

## 6. Contract Table

| Layer | Current legacy timeline | Target timeline | Source of truth |
| --- | --- | --- | --- |
| Cloud | `role=chord`, `chord_voice_N` | `role=cloud`, `cloud_voice_N` | existing voice-leading renderer / future `arrangement.cloud` |
| Chord | not present in legacy timeline | `role=chord`, `chord_note_N` | `RenderedArrangement.chord` |
| Bass | `role=bass`, `bass` | `role=bass`, `bass` | existing bass / future `arrangement.bass` |
