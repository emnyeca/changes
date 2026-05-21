# Harmony Cloud

This repository contains a **machine‑jazz harmony engine** for generating six‑voice jazz chord clouds and recording them to Digitone II via MIDI.  The goal is to build a toolkit that lets performers call a jazz standard or progression and have a dense, voice‑led six‑note harmonic texture recorded onto the Digitone in a few seconds, ready for live layering and muting.

The core concept is to:

- Parse jazz chord progressions (for example from an iRealPro export).  
- Expand each chord into a six‑note voicing such as a 6/9, 9, 13, sus or altered variant with added tensions.  
- Allocate each note to one Digitone track and voice‑lead between chords with minimal melodic motion.  
- Output MIDI (over USB or DIN) so the Digitone II can record the generated voices at very high tempo for real‑time capture.  
- Use track muting and level controls during performance to reveal or hide layers and evolve the harmonic cloud.

This project prioritizes deterministic behavior, readable music‑theory logic, and performance‑safe MIDI output.  It is intended to be used in Emnyeca/EMN Records’ machine‑jazz sessions and Embient events, but the code may be adapted for other live harmony generation setups.

Contributions and issue reports are welcome once the basic architecture is in place.