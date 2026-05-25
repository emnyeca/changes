# EUB Changes

![EUB Changes logo](docs/assets/1x/eub_changes_logo.png)

This repository contains a **machine‑jazz harmony engine** for generating six‑voice jazz chord clouds and recording them to Digitone II via MIDI.  The goal is to build a toolkit that lets performers call a jazz standard or progression and have a dense, voice‑led six‑note harmonic texture recorded onto the Digitone in a few seconds, ready for live layering and muting.

The core concept is to:

- Parse jazz chord progressions (for example from an iRealPro export).  
- Expand each chord into a six‑note voicing such as a 6/9, 9, 13, sus or altered variant with added tensions.  
- Allocate each note to one Digitone track and voice‑lead between chords with minimal melodic motion.  
- Output MIDI (over USB or DIN) so the Digitone II can record the generated voices at very high tempo for real‑time capture.  
- Use track muting and level controls during performance to reveal or hide layers and evolve the harmonic cloud.

This project prioritizes deterministic behavior, readable music‑theory logic, and performance‑safe MIDI output. It is intended to be used in Emnyeca/EMN Records machine‑jazz sessions and Embient events, but the code may be adapted for other live harmony generation setups.

Contributions and issue reports are welcome once the basic architecture is in place.

## Minimal Streamlit UI (drag & drop)

You can run a simple GUI for non-terminal workflows:

1. Install UI dependencies:

	- `pip install -e .[ui]`

2. Launch app:

	- `python -m streamlit run src/changes/ui_streamlit.py`

The UI supports:

- Drag & drop YAML progression
- Tempo / meter input
- Hold Trigger ON/OFF switch (same-pitch retrigger policy)
- Per-track MIDI channel assignment (Track1-6 + Bass, each `send off` or 1-16)
- Independent Bass track (C1-B1), with root/fifth auto-switch after configurable repeats
- MIDI file generation
- Realtime send to selected MIDI output port

For realtime send, also install:

- `pip install -e .[realtime]`
