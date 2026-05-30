# Track 8 Explicit Export Command Design

## Purpose
This document designs an explicit user-facing export command for Track 8 chord SysEx output.

It does not implement the command.

## Scope
The command is intended to export product-like Digitone II Track 8 chord output from Changes-generated musical data.

Initial export target:

.events.yaml
.syx
manifest.md

Future export/send target:

send .syx bytes to Digitone II through an explicit transport layer

This future send flow must preserve dependency direction:

changes -> digitone-syx-toolkit
changes -> MIDI transport backend

digitone-syx-toolkit must not import Changes.

## Command design status
Changes currently has an existing CLI convention via the `changes` script and `changes.cli:main`.

Current implemented CLI modes are generic MIDI and Digitone compile/bundle flows.

There is no stable explicit Track 8 command namespace implemented yet.

Therefore this document is a proposed design, not an implemented interface.

## Proposed command
Primary proposal:

changes export digitone-track8 \
  --input song.yaml \
  --output-dir out/digitone-track8 \
  --profile product-like \
  --name "My Song"

Alternative launch shape when invoking as module:

python -m changes export digitone-track8 \
  --input song.yaml \
  --output-dir out/digitone-track8 \
  --profile product-like

Neither form is claimed to exist yet.

## Proposed command responsibilities
The command should:

1. Load a Changes song/project input.
2. Render arrangement.
3. Extract Track 8 chord events.
4. Convert to toolkit-compatible rows.
5. Finalize lengths.
6. Build product-like events YAML.
7. Dump .events.yaml.
8. Generate .syx through digitone-syx-toolkit.
9. Write a deterministic manifest.
10. Never send MIDI unless an explicit future send flag/subcommand is used.

## Proposed output files
For a song named my_song, output should be:

out/digitone-track8/
  my_song.track8.events.yaml
  my_song.track8.syx
  my_song.track8_manifest.md

Fallback deterministic names when no song name is provided:

changes_track8_export.events.yaml
changes_track8_export.syx
changes_track8_export_manifest.md

## Input assumptions
Expected input model is intentionally open in this phase.

SPEC-OPEN: exact input file format for SongModel/project import.

Possible future inputs:

- .changes.yaml
- .json
- internal project file
- editor state
- direct in-memory SongModel
- fixture helper for tests

This phase does not implement input loading.

## Export profile
Initial supported profile:

product-like

Product-like profile should use:

- pattern mode: per-track
- CHANGE: OFF
- RESET: INF
- Track 1-8 LENGTH: 16
- Track 1-8 SPEED: 1/8
- Track 9-16 LENGTH: 16
- Track 9-16 SPEED: 1
- Track 1-7 default velocities:
  - Track 1: 70
  - Track 2: 70
  - Track 3: 70
  - Track 4: 50
  - Track 5: 70
  - Track 6: 50
  - Track 7: 100
- Track 8 chord event velocities from ChordRealizationResult
- Track 8 note lengths from duration_quarters -> length_code
- Track 8 micro timing default 0

This profile is validated by the product-like Cmaj7 fixture but not yet by broad song export.

## Artifact manifest design
The command should write a manifest containing:

- source input path
- export profile
- output file names
- pattern settings
- number of Track 8 chord events
- number of generated note rows
- toolkit dependency status
- whether SysEx generation succeeded
- caveats
- no-send warning

Do not include current timestamp unless determinism policy is explicitly changed.

## Toolkit dependency behavior
The command should use lazy toolkit integration.

Expected behavior:

- If only .events.yaml output is requested, toolkit may not be required.
- If .syx output is requested, digitone-syx-toolkit is required.
- If toolkit is missing, fail with a clear message: digitone-syx-toolkit is required for SysEx generation.
- Include install/development setup guidance.
- Do not import toolkit at module import time.
- Do not make toolkit import happen in unrelated Changes code paths.

## Dependency direction
Changes may call digitone-syx-toolkit.

digitone-syx-toolkit must not import Changes.

If direct send-to-Digitone is added later, keep this shape:

changes -> digitone-syx-toolkit
changes -> MIDI transport backend

Do not introduce:

digitone-syx-toolkit -> changes

## Future send-to-hardware extension
Future extension must be explicit, never implicit.

Possible future command:

changes send digitone-track8 \
  --syx out/digitone-track8/my_song.track8.syx \
  --port "Digitone II"

Alternative:

changes export digitone-track8 \
  --input song.yaml \
  --output-dir out/digitone-track8 \
  --profile product-like \
  --send \
  --port "Digitone II"

Recommendation: prefer separate send subcommand first.

Rationale:

- safer for hardware
- easier to inspect file before transmission
- avoids accidental hardware writes
- keeps export and transport testable separately

## Transport layer design
If send support is added later, introduce a thin Changes-side transport layer.

Suggested future module:

src/changes/digitone/transport.py

Responsibilities:

- list MIDI ports
- validate selected port
- send SysEx bytes
- report send result
- never generate SysEx itself
- never know SongModel

Do not implement this in Phase 5A.

## Error handling design
Define errors for:

- missing input file
- invalid SongModel/project file
- unsupported chord/event content
- no Track 8 chord events generated
- unsupported duration/length code
- invalid output directory
- output files already exist unless overwrite requested
- missing toolkit for .syx generation
- toolkit parse/build failure
- future MIDI port missing
- future send failure

## Overwrite policy
Default should be safe:

overwrite = false

If output files already exist, command should fail unless:

--overwrite

is provided.

## Output mode policy
Consider staged output modes:

--events-yaml-only
--syx
--all

Recommended default for product command:

--all

If toolkit is unavailable, allow .events.yaml only mode.

## Testing strategy for implementation phase
Future implementation tests should cover:

- product-like export from in-memory minimal SongModel
- output file naming
- overwrite protection
- .events.yaml contract
- .syx generation when toolkit installed
- missing toolkit error
- deterministic manifest
- no MIDI send during export
- future send command separated from export

## CLI implementation boundary
Phase 5B should implement the narrowest possible slice.

Suggested Phase 5B:

Implement explicit file artifact export from an in-memory or fixture SongModel helper.
Do not implement arbitrary input file loading yet if SongModel serialization is unstable.
Do not implement hardware send yet.

Reason:

SongModel/project file format remains SPEC-OPEN.

A safe first implementation can expose a Python API or developer command before final CLI UX.

## SPEC-OPEN items

- exact user-facing CLI framework/entry point for new export subcommands
- exact SongModel/project input file format
- whether first implementation should be CLI or Python API
- whether .events.yaml only mode should be exposed
- whether output file names should be slugified from song title
- whether product-like profile constants should be centralized
- whether toolkit should become pinned dependency before implementation
- whether CI should install toolkit for integration tests before implementation
- future MIDI backend choice for send command
- cross-platform device/port discovery behavior

## Non-goals
This phase does not:

- implement CLI
- implement export API
- implement input file loading
- implement MIDI send
- modify toolkit
- modify runtime code
- modify pyproject
- generate new fixtures
- modify GitHub Actions
- perform monorepo migration

## Recommended next phase
Recommend:

Phase 5B: minimal explicit Track 8 export API for artifact generation

Scope for Phase 5B:

- Python API first
- input is in-memory SongModel
- output is .events.yaml, .syx, manifest
- no arbitrary input file loading
- no MIDI send
- no new CLI entry point unless current CLI convention is clarified further

Alternative:

Phase R2: CI integration design for toolkit-dependent tests

Priority rationale:

- Phase 5B is preferred first to lock product export behavior and artifacts.
- Phase R2 should follow immediately to strengthen integration confidence in CI.

## Acceptance criteria
This design is acceptable if:

1. Proposed command shape is defined.
2. Output artifacts are defined.
3. Product-like profile behavior is defined.
4. Toolkit dependency behavior is defined.
5. Dependency direction is explicit.
6. Future send-to-hardware extension is separated.
7. Transport layer boundary is defined.
8. Error handling policy is defined.
9. SPEC-OPEN items are listed.
10. Recommended next phase is stated.
11. No runtime code is changed.
