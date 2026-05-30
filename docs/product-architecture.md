# Product Architecture

## Product direction

EUB Changes is intended to convert iReal Pro or MusicXML-derived song data into Digitone II machine-live performance material.

```text
iReal Pro
  -> MusicXML export
  -> internal song/harmony model
  -> machine-live-friendly note layers
  -> Digitone II tracks
```

The product priority order is:

- Cloud > Bass > Chord
- Track 1-6 > Track 7 > Track 8

## Layer model

| Digitone II Track | Layer | Role | Product priority | Current status |
| --- | --- | --- | --- | --- |
| Track 1-6 | Harmony Cloud | Six-voice playable harmony cloud for the main performance layer | Primary | architecture target / partial implementation |
| Track 7 | Bass | Root movement or slash-bass grounding layer | Secondary | architecture target / partial implementation |
| Track 8 | Chord | Chord reference or helper layer | Additional | current RC-stabilized workflow |

## Why the order matters

Track 1-6 Harmony Cloud is the main musical output. It is the playable, atmospheric, machine-live material that carries the harmonic texture during performance.

Track 7 Bass provides grounding. It anchors the harmony in the low register and supports the cloud rather than replacing it.

Track 8 Chord is useful for harmonic reference, helper behavior, and additional control, but it is not the main output of the product.

## Internal pipeline view

The repository already contains pieces of this broader architecture:

- MusicXML import into an internal song/harmony model
- harmonic-context resolution and six-note harmony extraction
- bounded voicing and bass rendering
- Digitone bundle compilation paths for broader track-oriented exports

The currently stabilized hardware-facing workflow is still narrower:

- SongModel YAML
- Track 8 Chord export
- SysEx check
- manifest-aware validation
- dry-run send
- guarded real-send

That RC path is an important validated subset, but it should be read underneath the product architecture above, not as the full product definition.

## Documentation map

- `current-state.md` separates intended product direction from implemented and validated subsets.
- `e2e-user-workflow.md` describes the current Track 8 RC workflow only.
- `validation-matrix.md` tracks the validation depth of the current RC subset.