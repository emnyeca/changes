"""Chord progression and chord symbol parser for Changes."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Sequence
import yaml

from .note import pitch_class_to_semitone

@dataclass(frozen=True)
class ChordSymbolCore:
    symbol: str
    root: str
    root_pc: int
    quality: str
    normalized_quality: str
    base_quality: str
    seventh_type: str | None
    extensions: frozenset[str]
    added_degrees: frozenset[str]
    altered_degrees: frozenset[str]
    omitted_degrees: frozenset[str]
    slash_bass: str | None
    slash_bass_pc: int | None
    special_semantic_tag: str | None


_QUALITY_PATTERNS = (
    "7b9sus4",
    "7#9b5",
    "mMaj7",
    "7#11",
    "7b13",
    "7#9",
    "7b9",
    "7#5",
    "7b5",
    "9sus4",
    "7sus4",
    "m7b5",
    "dim7",
    "maj7",
    "m9",
    "m7",
    "m6",
    "aug7",
    "alt",
    "m",
    "9",
    "7",
    "6",
    "",
)
_CHORD_RE = re.compile(
    r"^(?P<root>[A-G](?:#|b)?)(?P<quality>" + "|".join(_QUALITY_PATTERNS) + r")$"
)


_QUALITY_MODEL: dict[str, dict] = {
    "": {
        "base_quality": "major",
        "seventh_type": None,
        "extensions": frozenset(),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "m": {
        "base_quality": "minor",
        "seventh_type": None,
        "extensions": frozenset(),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "6": {
        "base_quality": "major",
        "seventh_type": None,
        "extensions": frozenset({"6"}),
        "added_degrees": frozenset({"6"}),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "m6": {
        "base_quality": "minor",
        "seventh_type": None,
        "extensions": frozenset({"6"}),
        "added_degrees": frozenset({"6"}),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "maj7": {
        "base_quality": "major",
        "seventh_type": "maj7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "m7": {
        "base_quality": "minor",
        "seventh_type": "b7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "mMaj7": {
        "base_quality": "minor",
        "seventh_type": "maj7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "m9": {
        "base_quality": "minor",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9"}),
        "added_degrees": frozenset({"9"}),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "m7b5": {
        "base_quality": "minor",
        "seventh_type": "b7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"b5"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": "half_diminished",
    },
    "dim7": {
        "base_quality": "diminished",
        "seventh_type": "dim7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"b5"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": "diminished",
    },
    "7": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "9": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9"}),
        "added_degrees": frozenset({"9"}),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7b9": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"b9"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7#9": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"#9"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7b5": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"b5"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7#5": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"#5"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7#11": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "11"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"#11"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7b13": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "13"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"b13"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7#9b5": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"#9", "b5"}),
        "omitted_degrees": frozenset(),
        "special_semantic_tag": None,
    },
    "7sus4": {
        "base_quality": "suspended",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "11"}),
        "added_degrees": frozenset({"4"}),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset({"3"}),
        "special_semantic_tag": "sus",
    },
    "9sus4": {
        "base_quality": "suspended",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9", "11"}),
        "added_degrees": frozenset({"4", "9"}),
        "altered_degrees": frozenset(),
        "omitted_degrees": frozenset({"3"}),
        "special_semantic_tag": "sus",
    },
    "7b9sus4": {
        "base_quality": "suspended",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9", "11"}),
        "added_degrees": frozenset({"4"}),
        "altered_degrees": frozenset({"b9"}),
        "omitted_degrees": frozenset({"3"}),
        "special_semantic_tag": "sus",
    },
    "alt": {
        "base_quality": "dominant",
        "seventh_type": "b7",
        "extensions": frozenset({"7", "9", "13"}),
        "added_degrees": frozenset(),
        "altered_degrees": frozenset({"b9", "#5", "b13"}),
        "omitted_degrees": frozenset({"5"}),
        "special_semantic_tag": "alt",
    },
}


def normalize_chord_quality(quality: str) -> str:
    q = str(quality)
    if q == "aug7":
        return "7#5"
    return q


def _parse_root_and_quality(text: str) -> tuple[str, str]:
    m = _CHORD_RE.match(text)
    if not m:
        raise ValueError(f"Unsupported chord symbol: {text}")
    return m.group("root"), m.group("quality")


def parse_chord_core(chord: str) -> ChordSymbolCore:
    text = str(chord).strip()
    left, slash = text, None
    if "/" in text:
        left, slash = text.split("/", 1)
        slash = slash.strip() or None

    root, quality = _parse_root_and_quality(left.strip())
    normalized_quality = normalize_chord_quality(quality)
    model = _QUALITY_MODEL.get(normalized_quality)
    if model is None:
        raise ValueError(f"Unsupported chord quality: {quality}")

    slash_bass = None
    slash_bass_pc = None
    if slash is not None:
        if len(slash) >= 2 and slash[1] in ("#", "b"):
            slash_bass = slash[:2]
        else:
            slash_bass = slash[:1]
        slash_bass_pc = pitch_class_to_semitone(slash_bass)

    return ChordSymbolCore(
        symbol=text,
        root=root,
        root_pc=pitch_class_to_semitone(root),
        quality=quality,
        normalized_quality=normalized_quality,
        base_quality=model["base_quality"],
        seventh_type=model["seventh_type"],
        extensions=model["extensions"],
        added_degrees=model["added_degrees"],
        altered_degrees=model["altered_degrees"],
        omitted_degrees=model["omitted_degrees"],
        slash_bass=slash_bass,
        slash_bass_pc=slash_bass_pc,
        special_semantic_tag=model["special_semantic_tag"],
    )


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
    """Parse canonical chord symbols used by legacy callers.

    This adapter keeps the historical dictionary API.
    """
    core = parse_chord_core(chord)
    return {
        "symbol": core.symbol,
        "root": core.root,
        "quality": core.quality,
        "normalized_quality": core.normalized_quality,
    }


def flatten_progression(progression: Sequence[Sequence[str]]) -> List[str]:
    """Flatten bars/groups into a single sequence of chord symbols."""
    return [chord for bar in progression for chord in bar]
