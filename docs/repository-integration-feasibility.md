# Repository Integration Feasibility

## Purpose

This document defines the current repository strategy for `changes` and `digitone-syx-toolkit`.

## Current decision

- Keep repositories separate.
- Keep dependency direction one-way: `changes -> digitone-syx-toolkit`.
- Keep toolkit integration explicit and lazy in `changes` runtime paths.
- Do not duplicate low-level Digitone encoding logic in musical model layers.

## Required toolkit capabilities

- events YAML loading/validation
- SysEx build from events YAML
- Digitone template seed handling
- per-track scale handling
- track default velocity propagation

## Responsibility boundary

Remain in `changes`:

- musical allocation and rendering
- export orchestration and artifact policy
- send/check command safety policy

Remain in `digitone-syx-toolkit`:

- byte-level SysEx encoding
- checksum/packing details
- template byte handling
- hardware-specific low-level builder behavior

## CI policy while repositories remain separate

- normal tests run without mandatory toolkit install
- toolkit-dependent integration tests run in dedicated CI job
- local development can run integration tests with editable install of both repos

## Migration criteria (only if needed)

Consider stronger integration topology only when most of the following are true:

- integration tests must run on every PR as required checks
- schema changes frequently span both repos
- product packaging requires tighter repository coupling
- current two-repo overhead exceeds migration cost

## Rollback posture

If repository topology changes later, maintain rollback by preserving package import boundary and keeping public toolkit APIs stable during migration.

## Scope boundary

This document defines current strategy only. It does not change runtime behavior.
