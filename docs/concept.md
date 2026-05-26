# Concept

## Purpose

The Changes project aims to generate six-voice chord clouds for jazz standards and progressions, focusing on live machine-jazz performance. It provides a composition/performance tool that transforms simple chord progressions into rich harmonic textures for Generic MIDI playback and Digitone II Native SysEx generation.

## Approach

- **Chord Parsing:** Read a chord sequence (for example from an iRealPro export) and interpret it in terms of scale degrees and functions.
- **Voicing Expansion:** Expand each chord into a six-note voicing that includes tensions (9, 11, 13) and sixths. Use voicing rules to choose appropriate chord qualities such as 6/9, 9/13 or sus4.
- **Voice Leading:** Allocate each note to a separate track and ensure minimal motion between adjacent chords. High-priority tones like the third and seventh resolve as expected, while tensions may be held across changes.
- **Performance Layer:** Use track muting and level control to abstract the dense voicing into simple shells, ambient pads or broken chords. This abstraction lets the performer reveal or conceal harmonic layers during improvisation.
- **Backend Split:** Keep Generic MIDI export/realtime send for broad compatibility, and use Native SysEx backend for Digitone II pattern output.

## Design Goals

- **Deterministic:** The generator produces consistent voicings given the same input.
- **Musically Informed:** Voice-leading rules and tension choices are rooted in jazz harmony concepts.
- **Modular:** Components such as chord parsing, voicing rules, and MIDI output are modular for future extension.
- **Performance-Focused:** Designed for live Embient sessions, prioritizing reliability and deterministic output.
