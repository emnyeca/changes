"""Voicing generation for Changes."""

from __future__ import annotations

from typing import List, Sequence

from .chord_parser import flatten_progression
from .harmonic_context import (
    build_local_pitch_collection,
    chord_tone_pitch_classes,
    extract_output_chord_tone_set,
    select_scale_collection,
)

VOICE_MIN_MIDI = 48  # C3
VOICE_MAX_MIDI = 71  # B4


def _fit_chord_range(notes: list[int]) -> list[int]:
    out = list(notes)
    while out and max(out) > VOICE_MAX_MIDI and min(out) - 12 >= VOICE_MIN_MIDI:
        out = [n - 12 for n in out]

    while out and min(out) < VOICE_MIN_MIDI and max(out) + 12 <= VOICE_MAX_MIDI:
        out = [n + 12 for n in out]

    return out


def _output_pitch_classes_for_event(chords: Sequence[str], index: int) -> tuple[int, int, int, int, int, int]:
    symbol = chords[index]
    local = build_local_pitch_collection(chords, index, circular=True, include_slash_bass=True)
    selected = select_scale_collection(symbol, local)
    return extract_output_chord_tone_set(symbol, selected)


def _output_pitch_classes_to_midi(output_pcs: Sequence[int], *, base_octave: int = 3) -> list[int]:
    notes: list[int] = []
    previous: int | None = None

    for pc in output_pcs:
        if previous is None:
            note = (base_octave + 1) * 12 + int(pc)
        else:
            note = int(pc) + 12 * (previous // 12)
            while note <= previous:
                note += 12
        notes.append(note)
        previous = note

    return _fit_chord_range(notes)


def generate_voicing_candidates(chord_symbol: str, base_octave: int = 3) -> List[List[int]]:
    """Generate deterministic six-note candidate voicings for one supported chord.

    This single-chord helper keeps API compatibility for callers, but the primary
    rendering path is progression_to_voicings(), which uses context-aware harmony.
    """
    # Single-chord path: select collection from current chord tones only.
    local = set(chord_tone_pitch_classes(chord_symbol, include_bass=True))
    selected = select_scale_collection(chord_symbol, local)
    output_pcs = extract_output_chord_tone_set(chord_symbol, selected)
    base = _output_pitch_classes_to_midi(output_pcs, base_octave=base_octave)

    # Three deterministic variants: base, slightly opened top, one octave up.
    opened_top = list(base)
    opened_top[-2] += 12
    opened_top[-1] += 12

    octave_up = [n + 12 for n in base]
    return [base, opened_top, octave_up]


def generate_voicing(chord_symbol: str, base_octave: int = 3) -> List[int]:
    """Return the default six-note voicing candidate for a chord symbol."""
    return generate_voicing_candidates(chord_symbol, base_octave=base_octave)[0]


def progression_to_voicings(
    progression: Sequence[Sequence[str]], base_octave: int = 3
) -> List[List[int]]:
    """Convert progression data to six-note context-aware voicings."""
    chords = flatten_progression(progression)
    voicings: list[list[int]] = []
    for idx in range(len(chords)):
        output_pcs = _output_pitch_classes_for_event(chords, idx)
        voicings.append(_output_pitch_classes_to_midi(output_pcs, base_octave=base_octave))
    return voicings
