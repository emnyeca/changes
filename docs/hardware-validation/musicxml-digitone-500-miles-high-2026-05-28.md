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

## Additional Finding (Minor ii-V, E7#9)

Listening validation also found an unnatural dominant interpretation in:

- progression excerpt: `Bm7b5 | E7#9 | Am7`
- issue: written `#9` on `E7#9` behaved as a hard context constraint in Attempt 2, which could block `A_harmonic_minor`

Policy update applied:

- split context constraints into hard constituents and color hints
- dominant altered tensions (`b9`, `#9`, `#11`, `b13`) are excluded from Attempt 1/2 containment constraints
- current-only Attempt 3 restores current chord color hints to preserve standalone altered color
- `alt` remains hard semantic directive; `b5/#5` remain hard structural tones

Post-fix expected/verified target for `E7#9` occurrence in measure 8:

- retry_level: `current+previous`
- selected_collection_family: `harmonic_minor`
- selected_collection_name: `A_harmonic_minor`
- output_chord_tone_set: `E G# B C D F`

Additional listening status:

- regenerated SYX has not yet been resent to Digitone II for this specific `E7#9` color change
- keep validation status pending until by-ear confirmation on hardware
