"""
Chord progression parser for Harmony Cloud.

This module reads a YAML file defining a chord progression and returns the
progression as a list of lists of chord symbols.
"""

from typing import List, Sequence
import yaml


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
