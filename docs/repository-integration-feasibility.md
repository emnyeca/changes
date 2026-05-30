# Repository Integration Feasibility

## Purpose
This document evaluates whether changes and digitone-syx-toolkit should remain separate repositories, become a monorepo, or be integrated through another dependency strategy.

It does not implement any repository migration.

## Current dependency map
Current dependency direction is:

changes -> digitone-syx-toolkit

In current code, this is explicit but optional for integration paths (lazy imports and skip-capable tests).

Practical dependency points today:

- toolkit-compatible events YAML shape
- toolkit YAML loader validation
- toolkit SysEx generation
- Digitone II length code semantics
- template and default pattern behavior
- per-track pattern settings
- track default velocity propagation
- hardware-validation fixture generation

## Capabilities required by Changes product export

| Capability | Classification | Notes |
|---|---|---|
| load_event_assignment_yaml | Required now | Used for real schema validation from Changes integration path |
| build_syx_from_events | Required now | Used for product-like fixture and Track 8 SysEx generation |
| Digitone II length code table and exact mapping | Required now | Changes currently mirrors mapping logic for deterministic Track 8 length encoding |
| events YAML schema (pattern-wide/per-track, chord constraints) | Required now | Product-like fixture depends on per-track schema and constraints |
| per-track track_scale support | Required now | Required to express product-like mode and length/speed |
| track_defaults.velocity support | Required now | Required for Track 1..7 default velocity profile |
| template override support | Required soon | Needed if BASE_EMPTY no longer sufficient for product defaults |
| BASE_EMPTY.syx or future product-like template | Required now | Current builder default seed source |
| SysEx builder with checksum and packing behavior | Required now | Required for hardware-accepted .syx output |
| toolkit GUI / capture / replay features | Optional | Useful tooling, not required for Changes export path |
| broader reverse-engineering utilities | Research/validation only | Important for evolution, not mandatory in day-to-day Changes musical logic |

## Capabilities that should remain generic toolkit responsibilities
The following should remain in digitone-syx-toolkit, not absorbed into Changes musical model:

- binary SysEx encoding
- Digitone II byte offsets
- checksum recalculation
- 7-bit packing and unpacking
- template byte handling
- length code canonical table
- event YAML parsing and validation
- hardware-specific pattern builder
- future Digitone-specific reverse engineering

Why:

- These are hardware-encoding concerns, not musical model concerns.
- Keeping them isolated reduces accidental coupling between composition logic and byte-level transport details.
- Toolkit remains reusable as a standalone debug/analysis package.

## Pain points of current two-repo structure

- repeated schema inspection and cross-repo context switching
- optional integration tests skipped when toolkit is unavailable
- local editable install friction for full validation
- version drift risk between two active repos
- duplicated length mapping logic in Changes
- fixture regeneration depends on synchronized local setups
- product packaging will need explicit cross-repo dependency policy
- CI coverage for integration behavior is weaker by default
- cross-repo PR coordination slows iteration

## Benefits of keeping separate repositories

- clean responsibility boundary
- toolkit remains reusable outside Changes
- low-level Digitone work stays isolated
- reverse-engineering experiments do not pollute Changes core musical model
- smaller conceptual surface for composition/rendering work
- easier rollback if toolkit changes regress hardware behavior

## Options

### Option A: Keep separate repositories with optional integration
Description:

- continue current structure
- toolkit remains optional
- integration tests skip if toolkit not installed

Pros:

- minimal change
- clean separation
- low migration risk

Cons:

- weak CI integration
- product export remains awkward
- version drift risk

### Option B: Keep separate repositories but make toolkit a pinned dependency
Description:

- publish or pin digitone-syx-toolkit
- Changes depends on a version or git ref
- CI installs toolkit

Pros:

- better CI coverage
- no repo migration
- clear package boundary

Cons:

- packaging and release/version management overhead
- still cross-repo development friction

### Option C: Monorepo with separate Python packages
Description:

- one repository contains both packages
- import boundaries remain separate Python packages
- possible layouts:

src/changes/
src/digitone_syx_toolkit/

or

packages/changes/
packages/digitone-syx-toolkit/

Pros:

- one CI surface
- integration tests always run
- schema and fixture changes can land in one PR
- package boundary preserved
- easier future app packaging/distribution

Cons:

- migration work and process risk
- larger repository and governance overhead
- risk of concern mixing if boundaries are not enforced

### Option D: Vendor selected toolkit features into Changes
Description:

- copy selected toolkit features into changes
- keep toolkit separately for experiments

Pros:

- product runtime appears self-contained

Cons:

- duplicated low-level Digitone logic
- high drift risk
- unclear source of truth
- weaker long-term maintainability

### Option E: Git submodule/subtree
Description:

- keep toolkit as a nested dependency

Pros:

- preserves toolkit history
- coordinated checkout possible

Cons:

- submodule friction for contributors
- subtree sync maintenance overhead
- packaging/CI complexity still remains

## Recommendation

Short term:

- Do not perform monorepo migration before Phase 5A.
- Keep runtime integration explicit and lazy in Changes.
- Plan CI integration for toolkit-dependent tests in a later CI phase (checkout/install toolkit in integration jobs).

Medium term:

- Prefer monorepo with separate Python packages if Track 8 export becomes a product path.
- Preserve import boundary:
  - import changes
  - import digitone_syx_toolkit

Avoid:

- vendoring low-level toolkit code into changes.digitone
- copying selected low-level functions into Changes as parallel source-of-truth
- merging toolkit low-level implementation into Changes musical model

Rationale:

- Phase 4 chain shows product usefulness now depends on stable toolkit integration.
- Current split is still workable for immediate product UX exploration.
- Forced migration before export UX definition adds risk without reducing near-term uncertainty.

## Suggested near-term plan

- Phase R2: CI integration design for toolkit-dependent tests
- Phase 5A: explicit export command design
- Phase R3: package boundary and monorepo migration design

Preferred ordering:

- Phase R2 first if stronger automated confidence is needed before broad product work.
- Phase 5A first if product UX decisions should drive repository strategy.

Current preference:

- Phase 5A first, then Phase R2 immediately after first CLI/export shape is fixed.

## Decision criteria for actual monorepo migration

- Track 8 export becomes a standard product feature
- toolkit-dependent tests should run on every PR
- app packaging requires bundled toolkit behavior
- schema changes frequently span both repos
- user-facing CLI/export depends continuously on toolkit
- optional integration overhead exceeds migration cost

## CI strategy if repositories remain separate

- normal tests run without toolkit dependency
- integration tests remain optional/skippable locally
- dedicated PR or scheduled workflow installs toolkit for integration suite
- alternative: CI job checks out both repositories and installs toolkit editable
- avoid forcing local path dependency for normal users

This phase does not implement CI changes.

## Rollback strategy
If monorepo migration is attempted later:

- preserve original toolkit repo until stabilization
- keep import path digitone_syx_toolkit unchanged
- avoid renaming public APIs during initial migration step
- migrate tests before migrating product runtime flow
- keep fixture bytes unchanged in first migration iteration
- tag pre-migration commits for both repositories
- document explicit rollback steps to previous two-repo workflow

## SPEC-OPEN items

- Should monorepo use src dual-package layout or packages layout?
- Should toolkit remain publishable as standalone package?
- Should Changes app distribution bundle toolkit internally?
- Should history be preserved via subtree/filter-repo or copied as snapshot?
- Should toolkit CI remain independently runnable after migration?
- Should hardware-validation fixtures live in Changes, toolkit, or a shared location?

## Requested file inspection inventory
Requested toolkit files checked:

- pyproject.toml
- src/digitone_syx_toolkit/events_yaml.py
- src/digitone_syx_toolkit/events_to_syx.py
- src/digitone_syx_toolkit/digitone2/builder.py
- src/digitone_syx_toolkit/digitone2/length_codes.py
- src/digitone_syx_toolkit/digitone2/template.py
- src/digitone_syx_toolkit/resources/digitone2/BASE_EMPTY.syx
- tests/test_events_yaml.py
- tests/test_events_to_syx.py
- tests/test_digitone2_pattern_settings.py
- examples/generated/
- docs/hardware-validation/
- README.md

Requested changes files checked:

- pyproject.toml
- src/changes/digitone/
- tests/test_track8_*.py
- examples/generated/
- docs/track8-*.md
- docs/hardware-validation/

Missing requested files:

- none

## Non-goals
This phase does not:

- move repositories
- change package layout
- change imports
- vendor toolkit code
- modify CI
- modify runtime code
- generate new fixtures
- modify toolkit

## Acceptance criteria
The document is acceptable if:

1. It maps current dependencies.
2. It identifies required toolkit capabilities.
3. It identifies generic toolkit responsibilities.
4. It compares options A-E.
5. It gives a short-term and medium-term recommendation.
6. It defines near-term phases.
7. It defines CI strategy options.
8. It defines rollback strategy.
9. It lists SPEC-OPEN items.
10. It makes no runtime changes.
