# Track 8 Product-like Pattern Settings Follow-up

## Problem

The Phase 4G hardware fixture validated Track 8 same-step chord-trigger behavior, but it did not validate product-like Digitone pattern settings.

The first hardware validation revealed that several broader settings still need explicit handling.

## Observed gaps

### PER TRACK mode

The following were not yet set to PER TRACK mode:

- LENGTH
- SPEED
- CHANGE
- RESET

### Track 1-7 defaults

Track 1-7 LEN / VEL defaults did not match the intended default output spec.

## Why this was acceptable in Phase 4G

Phase 4G intentionally validated only:

- Track 8
- Step 1
- six same-step chord notes
- note identity
- velocity
- length_code
- micro timing

It was not intended to validate product-like pattern initialization.

## Target product-like behavior

Define target behavior before implementing.

Open questions:

1. Should LENGTH / SPEED / CHANGE / RESET always be PER TRACK?
2. What should the default LEN be for Tracks 1-7?
3. What should the default VEL be for Tracks 1-7?
4. Should Track 8 receive separate defaults from Tracks 1-7?
5. Should product-like defaults live in Changes, digitone-syx-toolkit, or a template file?
6. Should Changes generate a default template pattern or require a user-supplied template?
7. How should these defaults interact with future bundle planner output?

## Proposed staged plan

### Phase 4I: Product-like settings specification

Document exact target values for:

- LENGTH mode
- SPEED mode
- CHANGE mode
- RESET mode
- Track 1-7 LEN
- Track 1-7 VEL
- Track 8 LEN
- Track 8 VEL
- pattern speed
- pattern total steps

No code changes yet.

### Phase 4J: Toolkit/template capability check

Inspect digitone-syx-toolkit to determine whether these settings are currently expressible via:

- events YAML
- template pattern file
- builder defaults
- direct builder API

### Phase 4K: Product-like fixture generation

Generate a second fixture:

examples/generated/track8_product_like_validation/

This fixture should validate:

- Track 8 Cmaj7 chord trigger
- PER TRACK modes
- Track 1-7 defaults
- Track 8 defaults
- product-like pattern settings

### Phase 4L: Hardware validation for product-like fixture

Run real hardware validation and log results.

## Non-goals for this follow-up note

This document does not implement the settings.

It only records the gap and the next staged plan.
