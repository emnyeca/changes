"""Legacy realtime Elektron recorder (experimental, not normal product flow)."""

from __future__ import annotations

import time
from typing import Sequence

import mido


def record_to_elektron(voicings: Sequence[Sequence[int]], port_name: str, tempo: int = 120) -> None:
    """Send voicings to Elektron hardware via realtime MIDI playback."""
    delay = 60.0 / tempo
    with mido.open_output(port_name) as outport:
        for chord in voicings:
            for note in chord:
                outport.send(mido.Message("note_on", note=note, velocity=100))
            time.sleep(delay)
            for note in chord:
                outport.send(mido.Message("note_off", note=note, velocity=0))
