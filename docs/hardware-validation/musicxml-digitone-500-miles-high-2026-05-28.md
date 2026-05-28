# MusicXML to Digitone II Hardware Validation Note (500 Miles High, 2026-05-28)

## Finding

Digitone II listening validation found that plain `Gm7` in the opening phrase could be recolored to diminished under contextual retry.

- progression excerpt: `Em7 | Em7 | Gm7 | Gm7 | A#maj7 ...`
- previous behavior at first `Gm7` (measure 3):
  - retry_level: `current+previous`
  - selected_collection_family: `diminished`
  - selected_collection_name: `G_half_whole_diminished`
  - output_chord_tone_set: `G A# C# E F G#`

## Fix Applied

Symmetric collection eligibility restriction was added in harmonic selection:

- whole-tone / diminished can be selected only when current chord explicitly has altered/diminished semantics
- plain major/minor qualities may still contribute to Local Pitch Collection, but cannot select symmetric collection as current output

## Post-fix Regeneration Check

Regenerated artifacts for both MusicXML source variants (`iRealPro` and `ireal-musicxml`) are semantically identical.

Expected/verified target for first `Gm7` in measure 3:

- retry_level: `current_only`
- selected_collection_family: `diatonic_dorian`
- selected_collection_name: `G_dorian_diatonic`
- output_chord_tone_set: `G A# D E F A`

## Listening Validation Status

- artifact regeneration: complete
- by-ear resend on Digitone II: pending
- do not mark as passed until the regenerated bundle SYX is resent and `Gm7` color is confirmed by ear
