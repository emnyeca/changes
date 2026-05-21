"""Elektron recorder module for Harmony Cloud.

This module handles sending MIDI note sequences to Elektron hardware (e.g. Digitone II)
at high tempos for real-time recording. It uses mido to open an output port and plays
each chord one after another with a single beat duration.

Functions:
    record_to_elektron(voicings: Sequence[Sequence[int]], port_name: str, tempo: int = 120) -> None
        Send voicings to a specified MIDI output port at a given tempo.
"""

from typing import Sequence
import mido
import time


def record_to_elektron(voicings: Sequence[Sequence[int]], port_name: str, tempo: int = 120) -> None:
    """
    Send a list of six-note voicings to an Elektron instrument via MIDI.

    Args:
        voicings: Sequence of chords/voicings, each a sequence of MIDI note numbers.
        port_name: Name of the mido output port to send messages to.
        tempo: Tempo in BPM at which to play the voicings.

    This function opens the specified port and plays each chord in succession,
    with each chord lasting one beat. It assumes the Elektron device is already
    in record mode and listening to the port.

    """
    # Calculate delay per beat in seconds
    delay = 60.0 / tempo
    with mido.open_output(port_name) as outport:
        for chord in voicings:
            # Note on events
            messages_on = [mido.Message('note_on', note=note, velocity=100) for note in chord]
            for msg in messages_on:
                outport.send(msg)
            # Hold for one beat
            time.sleep(delay)
            # Note off events
            messages_off = [mido.Message('note_off', note=note, velocity=0) for note in chord]
            for msg in messages_off:
                outport.send(msg)
