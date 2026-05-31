# Native SysEx Pipeline Status (2026-05-26)

## Completed

- Digitone II Pattern SysEx analysis and encoder for:
  - trigger / track / step / pitch / velocity / full length / tempo / speed / total steps / pattern name
- `changes` -> `digitone-syx-toolkit` integration 全体で per-track scale mode output を実装:
  - emitted events YAML now defaults to `pattern.mode = per-track`
  - Track 1..8 `track_scale.length` mirrors computed segment `total_steps`
  - Track 1..8 `track_scale.speed` mirrors computed plan/segment `speed`
  - Track 9..16 `track_scale.length` is fixed to `16`
  - Track 9..16 `track_scale.speed` is fixed to `1`
  - pattern-shared CHANGE is fixed to `OFF`
  - pattern-shared RESET is fixed to `INF`
- simple ii-V-I end-to-end hardware validation
- Blue Moon end-to-end hardware validation
- Pattern Name hardware validation 完了（pass）
- split pattern 向け song-level shared timing plan
- 128-step capacity を考慮した section-first deterministic split planning
- multi-pattern export 向け prefix-first readable auto naming
- Bundle artifact export:
  - `digitone_bundle_plan.json`
  - `bundle_manifest.json`
  - ordered per-pattern events YAML and per-pattern SYX
  - concatenated bundle SYX
- toolkit 側で sequential send support（ordered file list と concatenated bundle replay）
- 初期 BLUE MOON pattern-bundle fixture を生成:
  - `examples/generated/pattern_bundle_blue_moon/`
- context-aware voicing migration 完了:
  - fixed per-chord expansion removed from main render path
  - Local Pitch Collection + Selected Scale Collection + slot extraction (`1,3,5,6/13,7,9`)
  - corrected C-major context output for `Am7` (`F`, not `F#`)
- bundle robustness hardening 完了:
  - section occurrence-aware split planning (`A`, `B`, `A` handled as independent occurrences)
  - boundary carryover reconstruction for section/capacity splits (held notes retriggered at pattern step 1)
  - deterministic short-section merge policy for Digitone minimum length (`2..128` enforced)
  - shared Pattern Name policy for single and bundle outputs (auto/explicit consistent validation)
  - `digitone-bundle` CLI backend integrated with artifact and optional SYX output
  - manifest enriched with `pattern_count`, occurrence/global-order metadata, and path aliases
- bundle transport / display / timing hardware validation 完了:
  - Section bundle smoke test: pass
  - Held note boundary test: pass
  - Overflow/sequential import test: pass
  - Repeated section naming test: pass
  - verification mode: direct visual/aural confirmation on hardware (no screenshot/capture evidence recorded)
- harmonic context engine extension 完了:
  - canonical qualities added:
    - `major`, `m`, `6`, `m6`, `dim`, `maj7`, `maj9`, `maj7#5`, `m7`, `mMaj7`, `m9`, `m7b5`, `dim7`
    - `7`, `9`, `13`, `13b9`, `7b9`, `7#9`, `7b5`, `7#5`, `7#5b9`, `7b5b9`, `7#11`, `7b13`, `7#9b5`
    - `7sus4`, `9sus4`, `7b9sus4`, `alt`, slash bass
  - structured internal chord model introduced (base quality / 7th / extensions / altered / added / omitted / slash / semantic tag)
  - prioritized collection families added: diatonic/dorian, harmonic minor, melodic minor/lydian dominant, whole-tone, diminished
  - deterministic tie-break by signature-root circular distance + stable ordering
  - normalized harmonic identity used for repeated-chord context decisions
  - chromatic fallback removed; context-reduction retry policy implemented (`current+prev+next` -> `current+prev` -> `current`)
  - sus heptatonic extraction rule added: `1-4-5-13-b7-9`
- MusicXML importer normalization 完了:
  - accepts both iReal Pro direct-export MusicXML and `@infojunkie/ireal-musicxml` output
  - source-independent harmony normalization (`kind + degree + bass`) with compatibility overrides for `alt` and direct-export `7sus4` / `9sus4` / `7b9sus4`
  - normalized import-layer structured event model implemented with raw degree/form-marker diagnostics retained
  - phase-1 timing policy implemented: keep source positions as metadata, generate durations by equal subdivision per measure event count
  - relative `harmony/offset` handling fixed (`cursor + offset/divisions`)
  - unknown MusicXML harmony kind no longer degrades silently to dominant 7; explicit unsupported-kind error raised
  - form-marker policy implemented: preserve raw markers, default backward repeat without `times` to normalized `2`, no unfolding yet
  - paired compatibility tests strengthened for local 20-pair corpus (`examples/musicXML/iRealPro` vs `examples/musicXML/ireal-musicxml`):
    - structured semantic signature comparison
    - importer -> harmony-core end-to-end resolution/output equivalence comparison
- MusicXML to Digitone vertical-slice CLI path 完了:
  - new command style: `changes digitone-bundle --musicxml <file.musicxml> --output <artifact-dir> [--write-syx]`
  - pipeline path: MusicXML import -> SongModel -> timeline render -> Digitone bundle plan -> artifacts
  - emits `musicxml_harmony_resolution.json` for per-occurrence harmonic decision diagnostics
  - unresolved harmonic contexts fail conversion explicitly with measure/event/symbol/local-pitch-collection details
- Digitone II listening validation（`500 Miles High`）後、symmetric collection eligibility restriction を追加:
  - plain major/minor qualities cannot select whole-tone/diminished as current output collection
  - explicit altered/diminished qualities remain eligible for whole-tone/diminished selection
  - prevents accidental recoloring such as plain `Gm7` resolving to diminished from surrounding context alone
- Digitone II listening validation 後、dominant altered-tension の hard/color split を追加:
  - contextual selection now distinguishes hard structural constituents vs color hints
  - dominant altered tensions (`b9`, `#9`, `#11`, `b13`) are treated as soft color hints in Attempt 1/2
  - Attempt 3 (`current_only`) restores current chord color hints into constraint set
  - preserves `alt` as a hard semantic directive (`1, b9, 3, b13/#5`)
  - preserves structural altered-fifth tones (`b5`, `#5`) as hard constraints
  - fixes minor ii-V case (`Bm7b5 | E7#9 | Am7`) to prefer `A_harmonic_minor` for `E7#9`
- regression validation 完了:
  - `changes`: `168 passed`
  - `digitone-syx-toolkit`: `97 passed`
- register policy rollout 完了（render-layer）:
  - chord voices now bounded to Digitone display `C4-A5` (MIDI `48..69`)
  - bass now bounded to Digitone display `G2-F#3` (MIDI `31..42`)
  - bass source now follows slash bass when present (`Dm7/G` -> `G` bass, `C/E` -> `E` bass)
  - bounded voice sliding integrated into sequential voice leading state (next chord references previously bounded audible output)
  - no changes to harmonic collection selection policy, diagnostics semantics, Track Default Velocity policy, trigger inherit encoding, or SYX structure

## Confirmed import behavior

- 複数の Pattern SYX message は連続受信できる。
- device 側で選んだ destination start slot から順に配置される。
- generator 側で destination slot を encode する必要はない。
- 同じ destination slot へ受信した場合は上書きされる。

## Current boundary policy

- `changes` は `source_title`（song identity）と `pattern_name`（device display name）を分離する。
- events YAML の `name` は最終的な per-pattern `pattern_name` から常に export する。
- `changes` は explicit な per-segment Pattern Name override をサポートし、`pattern_name_source`（`auto` or `explicit`）を記録し、override 意図を保持する（explicit name がある場合は auto prefix を注入しない）。
- toolkit は Pattern Name を ASCII lowercase から uppercase へ normalize し、正規化後の全文字列で allowed character を検証し、16 文字超過時は先頭 16 文字に truncate する。
- Generic MIDI export path は Digitone Pattern Name restriction の影響を受けない。

## Pattern Name validation artifacts

- `examples/generated/pattern_name_validation/intro.digitone.events.yaml`
- `examples/generated/pattern_name_validation/intro.syx`
- `examples/generated/pattern_name_validation/theme_a.digitone.events.yaml`
- `examples/generated/pattern_name_validation/theme_a.syx`
- `examples/generated/pattern_name_validation/blue_moon_a.digitone.events.yaml`
- `examples/generated/pattern_name_validation/blue_moon_a.syx`
- `examples/generated/pattern_name_validation/angstrom.digitone.events.yaml`
- `examples/generated/pattern_name_validation/angstrom.syx`

execution note:

- この session では hardware validation 用 artifact と checklist 文書を生成済み。runbook 実行結果は `docs/hardware-validation/pattern-name-native-sysex-send-2026-05-26.md` へ追記する。

## Bundle transport validation artifacts (generated)

- `examples/generated/hardware_validation_bundle_precheck/section_bundle_smoke/`
  - pattern names: `INT BLUE MOON`, `A BLUE MOON`, `SOL BLUE MOON`, `OUT BLUE MOON`
  - packet check: 4 individual `.syx` packets and 4 packets in `.bundle.syx`
- `examples/generated/hardware_validation_bundle_precheck/held_note_boundary/`
  - pattern names: `INT BLUE MOON`, `A BLUE MOON`
  - packet check: 2 individual `.syx` packets and 2 packets in `.bundle.syx`
- `examples/generated/hardware_validation_bundle_precheck/overflow_split/`
  - pattern names: `SOL1 BLUE MOON`, `SOL2 BLUE MOON`
  - packet check: 2 individual `.syx` packets and 2 packets in `.bundle.syx`
- `examples/generated/hardware_validation_bundle_precheck/repeated_section_naming/`
  - pattern names: `A1 BLUE MOON`, `B BLUE MOON`, `A2 BLUE MOON`
  - packet check: 3 individual `.syx` packets and 3 packets in `.bundle.syx`
- Manual checklist document:
  - `docs/hardware-validation/digitone-bundle-pre-hardware-validation-2026-05-26.md`

## Per-track scale validation artifacts (generated)

- `examples/generated/musicxml_hardware_validation/500_miles_high_direct/`
  - per-pattern events YAML now emits `pattern.mode = per-track`
  - bundle SYX regenerated: `500_MILES_HIGH.bundle.syx`
- `examples/generated/musicxml_hardware_validation/500_miles_high_converted/`
  - per-pattern events YAML now emits `pattern.mode = per-track`
  - bundle SYX regenerated: `500_MILES_HIGH.bundle.syx`
- `examples/generated/hardware_validation_harmony/minor_ii_v_e7sharp9/`
  - per-pattern events YAML now emits `pattern.mode = per-track`
  - bundle SYX regenerated: `MINOR_II_V_E7_9.bundle.syx`
- Manual checklist document:
  - `docs/hardware-validation/per-track-scale-output-2026-05-29.md`

## Intentionally Unimplemented Scope (Current)

- iReal Pro HTML / `irealb://` の direct decoding。
- iReal Pro alias grammar expansion は deferred のまま（symbol sample 収集後に data-driven 実装）。
- `allow_sus_add3` は deferred のまま。

## Next major target

- iReal Pro HTML importer 実装
- dedicated validation を伴う MusicXML repeat/ending/DS/DC/Coda unfolding

## Register Policy and Bounded Voice Sliding (current default)

Bass:

- source: slash bass if present, otherwise chord signature root
- register: Digitone display `G2-F#3` / MIDI `31..42`

Chord voices:

- target register: Digitone display `C4-A5` / MIDI `48..69`
- realized by bounded minimum-motion voice sliding over six moving lanes
- final lane output is not pitch-sorted by force; voice crossing is permitted
- explicit `RegisterFitError` is raised when no in-range distinct realization exists for requested multiset/range

Velocity-layer interpretation:

- Track Default Velocity is interpreted as moving voice-layer balance, not fixed degree-role balance
- voice leading and bounded sliding may reassign degree content per track over time by design
