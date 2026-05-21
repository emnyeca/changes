"""Midi writer for Harmony Cloud.

This module provides functions for converting a sequence of chords or six-note voicings
into a MIDI file or for streaming to hardware. It uses mido to build a multi-track
MIDI file where each voice is on its own track.

Functions:
    write_midi(voicings: Sequence[Sequence[int]], filename: str, tempo: int = 120) -> None
        Create a MIDI file from a list of six-note voicings.

"""

from typing import Sequence
import mido


def write_midi(voicings: Sequence[Sequence[int]], filename: str, tempo: int = 120) -> None:
    """
    Write a sequence of six-note voicings to a MIDI file.

    Each inner sequence is treated as a chord; the notes are written on separate tracks
    so that they can be routed to individual voices on a synthesizer.

    Args:
        voicings: A sequence of sequences, where each inner sequence contains up to six MIDI note numbers.
        filename: Path of the output MIDI file.
        tempo: Tempo in BPM for the generated file.

    """
    mid = mido.MidiFile()
    # Create six tracks
    tracks = [mido.MidiTrack() for _ in range(6)]
    for track in tracks:
        mid.tracks.append(track)
    # Set tempo at start of track 0
    tempo_message = mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo))
    tracks[0].append(tempo_message)
    # Write each voicing
    for chord in voicings:
        # Note on messages for each voice (assuming up to six voices)
        for i, note in enumerate(chord):
            track = tracks[i]
            track.append(mido.Message('note_on', note=note, velocity=100, time=0))
        # Note off messages one beat later (using ticks_per_beat)
        duration_ticks = int(mid.ticks_per_beat)
        for i, note in enumerate(chord):
            track = tracks[i]
            track.append(mido.Message('note_off', note=note, velocity=0, time=duration_ticks))
    mid.save(filename)
