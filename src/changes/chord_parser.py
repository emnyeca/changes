"""Chord progression and chord symbol parser for Changes."""

from __future__ import annotations

import re
from typing import Dict, List, Sequence
import yaml

_CHORD_RE = re.compile(r"^(?P<root>[A-G](?:#|b)?)(?P<quality>maj7|m7|7)$")


def parse_progression(path: str) -> Sequence[Sequence[str]]:
    """Parse a YAML progression file into a sequence of chord lists.

    Args:
        path: Path to a YAML file with a top-level key 'progression' containing
            lists of chord symbols.

    Returns:
        A sequence of sequences where each inner sequence represents a bar or
        grouping of chords in the progression.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    progression = data.get("progression")
    if progression is None:
        raise ValueError(f"No 'progression' key found in {path}")
    if not isinstance(progression, list):
        raise TypeError("Expected 'progression' to be a list")

    # Ensure each element is a list of strings
    normalized: List[List[str]] = []
    for element in progression:
        if isinstance(element, list):
            normalized.append([str(chord) for chord in element])
        else:
            normalized.append([str(element)])

    return normalized


def parse_chord_symbol(chord: str) -> Dict[str, str]:
    """Parse chord symbols for the core ii-V-I set: Cmaj7 / Dm7 / G7."""
    m = _CHORD_RE.match(chord.strip())
    if not m:
        raise ValueError(f"Unsupported chord symbol: {chord}")

    root = m.group("root")
    quality = m.group("quality")
    return {
        "symbol": chord.strip(),
        "root": root,
        "quality": quality,
    }


def flatten_progression(progression: Sequence[Sequence[str]]) -> List[str]:
    """Flatten bars/groups into a single sequence of chord symbols."""
    return [chord for bar in progression for chord in bar]
