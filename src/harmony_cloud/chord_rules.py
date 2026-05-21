"""Chord expansion and interpretation rules for Harmony Cloud."""

from __future__ import annotations

from typing import List, Dict, Any

from .chord_parser import parse_chord_symbol

_EXPANSION_MAP = {
    "m7": "m6/9",
    "7": "9/13",
    "maj7": "6/9",
}

_INTERVALS = {
    "m6/9": [0, 3, 7, 9, 14, 17],
    "9/13": [0, 4, 7, 10, 14, 21],
    "6/9": [0, 4, 7, 9, 14, 16],
}

_TENSIONS = {
    "m6/9": ["9", "11"],
    "9/13": ["9", "13"],
    "6/9": ["6", "9"],
}


def get_chord_tensions(chord: str) -> List[str]:
    """Return selected tensions after applying Harmony Cloud expansion rules."""
    expanded = expand_chord_symbol(chord)
    parsed = parse_chord_symbol_for_expanded(expanded)
    return _TENSIONS[parsed["expanded_quality"]]


def expand_chord_symbol(chord: str) -> str:
    """Expand base chord symbols for ii-V-I cloud voicings.

    Dm7 -> Dm6/9, G7 -> G9/13, Cmaj7 -> C6/9
    """
    parsed = parse_chord_symbol(chord)
    target = _EXPANSION_MAP[parsed["quality"]]
    return f"{parsed['root']}{target}"


def parse_chord_symbol_for_expanded(chord: str) -> Dict[str, str]:
    """Parse expanded symbol into root + expanded quality."""
    for quality in ("m6/9", "9/13", "6/9"):
        if chord.endswith(quality):
            root = chord[: -len(quality)]
            if not root:
                break
            return {"root": root, "expanded_quality": quality}
    raise ValueError(f"Unsupported expanded chord symbol: {chord}")


def interpret_chord(chord: str) -> Dict[str, Any]:
    """Parse and expand a chord symbol into voicing-ready data."""
    parsed = parse_chord_symbol(chord)
    expanded_symbol = expand_chord_symbol(chord)
    expanded = parse_chord_symbol_for_expanded(expanded_symbol)
    expanded_quality = expanded["expanded_quality"]
    return {
        "input_symbol": chord,
        "root": parsed["root"],
        "quality": parsed["quality"],
        "expanded_symbol": expanded_symbol,
        "expanded_quality": expanded_quality,
        "intervals": list(_INTERVALS[expanded_quality]),
        "tensions": list(_TENSIONS[expanded_quality]),
    }
