# Cloud Role Migration Plan (Phase 3D)

## Problem Statement

There is a semantic naming conflict between the legacy timeline renderer and the target architecture.

Current target architecture:

- Cloud: context-aware moving six-voice texture
- Bass: root/slash-bass low note
- Chord: symbol-faithful vertical six-note chord

## 1. Current Legacy Behavior

The existing legacy renderer `render_timeline()` emits the context-aware six-voice layer as:

- `role="chord"`
- `voice_id="chord_voice_1" ... "chord_voice_6"`

This is legacy naming. Semantically, these notes correspond to the old Cloud-like behavior, not the new Chord Engine output.

## 2. Target Behavior

Future timeline semantics should be:

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

Immediate renaming in `render_timeline()` is risky because existing behavior may be implicitly depended on by:

- tests and serialized fixtures
- exporters and downstream adapters
- MIDI and Digitone-related planning logic
- role/voice-id based mapping code

A direct rename without compatibility staging can silently change outputs.

## 4. Recommended Staged Migration

Recommended sequence:

- Phase 3D: document and test current contracts
- Phase 3E: add optional profile flag or new renderer entrypoint for cloud role naming
- Phase 3F: update exporters to understand both legacy and new names
- Phase 3G: switch default naming after compatibility is confirmed
- Phase 3H: remove/deprecate legacy `chord_voice_*` naming if appropriate

## 5. Export Implications

- Generic MIDI export may tolerate role-name changes if it only consumes note events.
- Digitone export and bundle planning are more likely to depend on role/voice mappings.
- Track 8 Chord export should not rely on legacy timeline `role="chord"` events.
- Track 8 Chord export should consume `RenderedArrangement.chord` directly because it preserves grouping, per-note velocity, length mode, and diagnostics.

## 6. Contract Table

| Layer | Current legacy timeline | Target timeline | Source of truth |
| --- | --- | --- | --- |
| Cloud | `role=chord`, `chord_voice_N` | `role=cloud`, `cloud_voice_N` | existing voice-leading renderer / future `arrangement.cloud` |
| Chord | not present in legacy timeline | `role=chord`, `chord_note_N` | `RenderedArrangement.chord` |
| Bass | `role=bass`, `bass` | `role=bass`, `bass` | existing bass / future `arrangement.bass` |
