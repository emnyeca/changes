# Concept

## Purpose

The Changes project aims to generate six-voice chord clouds for jazz standards and progressions, focusing on live machine-jazz performance. It provides a real-time tool that transforms simple chord progressions into rich harmonic textures recorded into the Digitone II and manipulated in live settings.

## Approach

- **Chord Parsing:** Read a chord sequence (for example from an iRealPro export) and interpret it in terms of scale degrees and functions.
- **Voicing Expansion:** Expand each chord into a six-note voicing that includes tensions (9, 11, 13) and sixths. Use voicing rules to choose appropriate chord qualities such as 6/9, 9/13 or sus4.
- **Voice Leading:** Allocate each note to a separate track and ensure minimal motion between adjacent chords. High-priority tones like the third and seventh resolve as expected, while tensions may be held across changes.
- **Performance Layer:** Use track muting and level control to abstract the dense voicing into simple shells, ambient pads or broken chords. This abstraction lets the performer reveal or conceal harmonic layers during improvisation.
- **Recording Workflow:** Export or stream MIDI to the Digitone II at a very high tempo to record the entire progression in a few seconds, then restore normal tempo for performance.

## Design Goals

- **Deterministic:** The generator produces consistent voicings given the same input.
- **Musically Informed:** Voice-leading rules and tension choices are rooted in jazz harmony concepts.
- **Modular:** Components such as chord parsing, voicing rules, and MIDI output are modular for future extension.
- **Performance-Focused:** Designed for live Embient sessions, so speed and reliability are prioritized over offline rendering.
