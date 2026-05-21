"""Voicing generation for Harmony Cloud."""

from __future__ import annotations

from typing import List, Sequence

from .chord_parser import flatten_progression
from .chord_rules import interpret_chord
from .note import root_to_midi


def generate_voicing_candidates(chord_symbol: str, base_octave: int = 3) -> List[List[int]]:
    """Generate deterministic six-note candidate voicings for one chord."""
    info = interpret_chord(chord_symbol)
    root = root_to_midi(info["root"], base_octave)
    base = [root + interval for interval in info["intervals"]]

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
    """Convert parsed progression data to six-note voicings."""
    chords = flatten_progression(progression)
    return [generate_voicing(chord, base_octave=base_octave) for chord in chords]
