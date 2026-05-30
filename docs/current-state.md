# Current State

## Product target

The main product target remains Cloud > Bass > Chord.

EUB Changes is supposed to become a machine-live workflow that turns iReal Pro or MusicXML-derived song data into Digitone II performance layers with this priority:

- Track 1-6 Harmony Cloud as the primary layer
- Track 7 Bass as the secondary layer
- Track 8 Chord as the additional helper layer

## Implemented now

The repository currently includes:

- MusicXML import into an internal song model
- harmonic-context selection for six-note outputs
- six-note voicing generation and bounded voice leading
- bass rendering in a defined low register
- Digitone bundle compilation paths that operate on broader multi-track note material
- modern Track 8 export, check, dry-run, and guarded real-send commands

This means parts of the broader Cloud/Bass/Chord architecture exist in code, but they are not all exposed as RC-stabilized product workflows.

## Validated now

The currently stabilized RC path focuses on Track 8 Chord export/check/send.
This does not mean Track 8 is the main feature.
The main product target remains Cloud > Bass > Chord.

What is currently validated most clearly:

- Track 8 Chord export from SongModel YAML
- SysEx envelope check and manifest-aware validation
- dry-run send
- guarded real-send
- first Digitone II hardware validation for the II-V-I fixture

## Not yet RC-stabilized

The following are not yet RC-stabilized as full product workflows:

- Track 1-6 Harmony Cloud as the primary Digitone II workflow
- Track 7 Bass as the secondary Digitone II workflow
- expanded hardware validation for Cloud/Bass layers
- broad product-level validation for MusicXML-to-live-performance output

## Practical reading order

Use the documents in this order:

1. `product-architecture.md` for the product hierarchy and musical intent.
2. `release-candidate-status.md` and `validation-status.md` for what is stabilized now.
3. `e2e-user-workflow.md` for the current Track 8 RC path.

That keeps the repository aligned to the intended architecture while preserving the current Track 8 safety and validation documentation.