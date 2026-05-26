"""Render SongModel into a device-agnostic RenderedTimeline."""

from __future__ import annotations

from fractions import Fraction

from changes.models.render_profile import RenderProfile
from changes.models.rendered_timeline import RenderedNoteEvent, RenderedTimeline
from changes.models.song_model import SongModel
from changes.note import pitch_class_to_semitone
from changes.voicing import progression_to_voicings
from changes.voice_leading import generate_voice_leading


def _root_from_symbol(symbol: str) -> str:
    head = symbol.split("/", 1)[0].strip()
    if len(head) >= 2 and head[1] in ("#", "b"):
        return head[:2]
    return head[:1]


def _root_bass_note(symbol: str) -> int:
    root = _root_from_symbol(symbol)
    return 36 + pitch_class_to_semitone(root)


def _to_bars(song: SongModel) -> list[list[str]]:
    return [[h.symbol for h in m.harmony] for m in song.measures]


def render_timeline(song: SongModel, profile: RenderProfile) -> RenderedTimeline:
    bars = _to_bars(song)
    raw_voicings = progression_to_voicings(bars)
    voiced = generate_voice_leading(raw_voicings)

    harmony_events = []
    for measure in song.measures:
        for h in measure.harmony:
            onset = measure.absolute_start_quarters + h.offset_quarters
            harmony_events.append((h, onset, h.duration_quarters))

    if len(voiced) != len(harmony_events):
        raise ValueError("voicing count does not match harmony events")

    rendered: list[RenderedNoteEvent] = []
    for idx, ((h, onset, duration), chord_notes) in enumerate(zip(harmony_events, voiced), start=1):
        for v_idx, note in enumerate(chord_notes[: profile.voices], start=1):
            rendered.append(
                RenderedNoteEvent(
                    id=f"ev{idx}_v{v_idx}",
                    voice_id=f"chord_voice_{v_idx}",
                    role="chord",
                    note_midi=int(note),
                    onset_quarters=onset,
                    duration_quarters=duration,
                    source_harmony_id=h.id,
                    retrigger=True,
                )
            )

        if profile.bass_enabled:
            rendered.append(
                RenderedNoteEvent(
                    id=f"ev{idx}_bass",
                    voice_id="bass",
                    role="bass",
                    note_midi=_root_bass_note(h.symbol),
                    onset_quarters=onset,
                    duration_quarters=duration,
                    source_harmony_id=h.id,
                    retrigger=True,
                )
            )

    if profile.hold_repeated_same_pitch == "hold_until_change":
        return _merge_holds(song.title, song.performance_tempo, rendered)

    return RenderedTimeline(
        title=song.title,
        performance_tempo=song.performance_tempo,
        events=tuple(sorted(rendered, key=lambda e: (e.onset_quarters, e.voice_id, e.id))),
    )


def _merge_holds(title: str, tempo: Fraction, events: list[RenderedNoteEvent]) -> RenderedTimeline:
    ordered = sorted(events, key=lambda e: (e.voice_id, e.onset_quarters, e.id))
    merged: list[RenderedNoteEvent] = []

    for event in ordered:
        if merged and merged[-1].voice_id == event.voice_id and merged[-1].note_midi == event.note_midi:
            prev = merged[-1]
            prev_end = prev.onset_quarters + prev.duration_quarters
            if prev_end == event.onset_quarters:
                merged[-1] = RenderedNoteEvent(
                    id=prev.id,
                    voice_id=prev.voice_id,
                    role=prev.role,
                    note_midi=prev.note_midi,
                    onset_quarters=prev.onset_quarters,
                    duration_quarters=prev.duration_quarters + event.duration_quarters,
                    source_harmony_id=prev.source_harmony_id,
                    retrigger=prev.retrigger,
                )
                continue
        merged.append(event)

    final_events = tuple(sorted(merged, key=lambda e: (e.onset_quarters, e.voice_id, e.id)))
    return RenderedTimeline(title=title, performance_tempo=tempo, events=final_events)
