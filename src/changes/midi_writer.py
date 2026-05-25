"""Midi writer for Changes.

This module provides functions for converting a sequence of chords or six-note voicings
into a MIDI file or for streaming to hardware. It uses mido to build a multi-track
MIDI file where each voice is on its own track.

Functions:
    write_midi(voicings: Sequence[Sequence[int]], filename: str, tempo: int = 120) -> None
        Create a MIDI file from a list of six-note voicings.

"""

from typing import Dict, List, Sequence
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


def write_midi_with_events(
    voicings: Sequence[Sequence[int]],
    events: Sequence[Dict[str, int | str]],
    filename: str,
    tempo: int = 120,
    hold_same_pitch: bool = True,
    channel_map: Sequence[int | None] | None = None,
    per_voice_hold: Sequence[bool] | None = None,
) -> None:
    """Write MIDI from scheduled events while preserving held notes per voice.

    Consecutive same-pitch notes on the same voice are merged into one long note,
    and note_on is emitted only when that voice pitch changes.
    """
    mid = mido.MidiFile()
    tracks = [mido.MidiTrack() for _ in range(6)]
    for track in tracks:
        mid.tracks.append(track)

    tracks[0].append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo)))

    count = min(len(voicings), len(events))
    ticks_per_step = int(mid.ticks_per_beat)
    channels = list(channel_map) if channel_map is not None else [1, 2, 3, 4, 5, 6]
    if len(channels) < 6:
        channels.extend([1] * (6 - len(channels)))

    max_voices = max((len(v) for v in voicings[:count]), default=0)
    if len(channels) < max_voices:
        channels.extend([1] * (max_voices - len(channels)))

    hold_per_voice = list(per_voice_hold) if per_voice_hold is not None else []
    if len(hold_per_voice) < max_voices:
        hold_per_voice.extend([hold_same_pitch] * (max_voices - len(hold_per_voice)))

    def _voice_channel(voice_idx: int) -> int | None:
        if voice_idx >= len(channels):
            return 0
        ch = channels[voice_idx]
        if ch is None:
            return None
        return max(1, min(16, int(ch))) - 1

    for voice_idx in range(max_voices):
        channel = _voice_channel(voice_idx)
        if channel is None:
            continue

        absolute_tick = 0
        active_note: int | None = None
        voice_events: List[tuple[int, mido.Message]] = []
        voice_hold = bool(hold_per_voice[voice_idx])

        for idx in range(count):
            chord = voicings[idx]
            note = int(chord[voice_idx]) if voice_idx < len(chord) else None
            duration_steps = int(events[idx].get("duration_steps", 1))

            if voice_hold:
                if note != active_note:
                    if active_note is not None:
                        voice_events.append(
                            (
                                absolute_tick,
                                mido.Message(
                                    "note_off",
                                    note=active_note,
                                    velocity=0,
                                    channel=channel,
                                    time=0,
                                ),
                            )
                        )
                    if note is not None:
                        voice_events.append(
                            (
                                absolute_tick,
                                mido.Message(
                                    "note_on",
                                    note=note,
                                    velocity=100,
                                    channel=channel,
                                    time=0,
                                ),
                            )
                        )
                    active_note = note

                absolute_tick += duration_steps * ticks_per_step
            else:
                if note is not None:
                    voice_events.append(
                        (
                            absolute_tick,
                            mido.Message(
                                "note_on",
                                note=note,
                                velocity=100,
                                channel=channel,
                                time=0,
                            ),
                        )
                    )
                    voice_events.append(
                        (
                            absolute_tick + duration_steps * ticks_per_step,
                            mido.Message(
                                "note_off",
                                note=note,
                                velocity=0,
                                channel=channel,
                                time=0,
                            ),
                        )
                    )

                absolute_tick += duration_steps * ticks_per_step

        if voice_hold and active_note is not None:
            voice_events.append(
                (
                    absolute_tick,
                    mido.Message("note_off", note=active_note, velocity=0, channel=channel, time=0),
                )
            )

        last_tick = 0
        for tick, message in voice_events:
            message.time = tick - last_tick
            tracks[voice_idx].append(message)
            last_tick = tick

    mid.save(filename)
