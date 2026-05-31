# ワークフロー

この文書は、live machine-jazz session で Changes を使うための実践的な workflow を示します。

1. **Prepare a Chord Progression**  
   progression をサポート形式（例: YAML / JSON）で用意します。jazz standard については、iRealPro app-converted data と `ireal-musicxml` converted data の両方の MusicXML を扱えます。

2. **Run the Harmony Generator**  
   command-line tool または script で progression を parse し、six-voice voicing sequence を生成します。generator は次を行います。
   - Map each chord to a six-note voicing with tensions and sixths.
   - Allocate each note to one of the six Digitone tracks.
   - Optimize voice leading to minimize motion between chords.
   - Output a MIDI file or stream.

3. **Build Digitone Native Pattern (Optional)**  
   Digitone II output では Native SysEx backend path（`digitone-syx-toolkit`）を使い、toolkit-compatible events YAML から Pattern `.syx` を生成します。
   high-speed realtime MIDI recording は通常 workflow ではなく legacy experiment 扱いです。

4. **Live Performance**  
   session 中は track mute、level control、filter、effect で harmonic cloud を形作ります。
   - Start with only a few tracks active for a sparse texture.
   - Bring in additional tracks to thicken the harmony during climactic sections.
   - Use Digitone-side arrangement controls to introduce movement.
   - Optionally route tracks into effects like reverb, delay, or glitch processors.

5. **Iteration and Expansion**  
   曲に合わせて voicing rule や tension selection を調整します。voicing engine の parameter を変更したり、新しい chord quality を拡張して harmonic palette を洗練できます。
