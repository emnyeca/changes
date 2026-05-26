# Workflow

This document outlines a practical workflow for using Changes in a live machine-jazz session.

1. **Prepare a Chord Progression**  
   Export or write your progression in a supported format (for example YAML or JSON). For jazz standards, you can export from iRealPro and convert it if needed.

2. **Run the Harmony Generator**  
   Use the command-line tool or script to parse the progression and produce a six-voice voicing sequence. The generator will:
   - Map each chord to a six-note voicing with tensions and sixths.
   - Allocate each note to one of the six Digitone tracks.
   - Optimize voice leading to minimize motion between chords.
   - Output a MIDI file or stream.

3. **Build Digitone Native Pattern (Optional)**  
   For Digitone II output, use the Native SysEx backend path (`digitone-syx-toolkit`) to generate Pattern `.syx` from toolkit-compatible events YAML.
   High-speed realtime MIDI recording is treated as a legacy experiment, not normal workflow.

4. **Live Performance**  
   During the session, use track mutes, level controls, filters, and effects to shape the harmonic cloud:
   - Start with only a few tracks active for a sparse texture.
   - Bring in additional tracks to thicken the harmony during climactic sections.
   - Use Digitone-side arrangement controls to introduce movement.
   - Optionally route tracks into effects like reverb, delay, or glitch processors.

5. **Iteration and Expansion**  
   Experiment with different voicing rules and tension selections to suit various songs. You can adjust the voicing engine's parameters or extend it with new chord qualities to refine the harmonic palette.
