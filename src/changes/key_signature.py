"""Key signature display and parse helpers."""

from __future__ import annotations

import re

_CANONICAL_TONICS = frozenset({
    "C", "Db", "D", "Eb", "E", "F", "F#", "Gb", "G", "Ab", "A", "Bb", "B",
    "C#", "D#", "G#", "A#",
})

_TONIC_RE = re.compile(r"^([A-Ga-g][#b]?)(.*)", re.DOTALL)


def _split_tonic_suffix(text: str) -> tuple[str, str] | None:
    m = _TONIC_RE.match(text)
    if not m:
        return None
    raw = m.group(1)
    normalized = raw[0].upper() + raw[1:].lower() if len(raw) > 1 else raw[0].upper()
    if normalized not in _CANONICAL_TONICS:
        return None
    return normalized, m.group(2)


def format_working_key(working_key: str | None, working_key_mode: str | None) -> str:
    """Format (working_key, working_key_mode) for display.

    ("C", "major") -> "C"
    ("E", "minor") -> "Em"
    ("F", None)    -> "F?"
    (None, _)      -> "-"
    Invalid mode   -> "X?" (treated as unknown)
    """
    if working_key is None:
        return "-"
    if working_key_mode == "major":
        return working_key
    if working_key_mode == "minor":
        return f"{working_key}m"
    return f"{working_key}?"


def parse_working_key_display(text: str) -> tuple[str | None, str | None]:
    """Parse a key display string into (working_key, working_key_mode).

    "C"       -> ("C", "major")
    "Cmaj"    -> ("C", "major")
    "Cmajor"  -> ("C", "major")
    "CM"      -> ("C", "major")
    "Em"      -> ("E", "minor")
    "Eminor"  -> ("E", "minor")
    "E-"      -> ("E", "minor")
    "C?"      -> ("C", None)
    "?"       -> (None, None)
    ""        -> (None, None)
    "-"       -> (None, None)
    """
    t = text.strip()
    if not t or t in ("-", "?"):
        return None, None

    result = _split_tonic_suffix(t)
    if result is None:
        return None, None

    tonic, suffix = result

    if not suffix:
        return tonic, "major"

    if suffix == "?":
        return tonic, None

    # Single-char suffixes are case-sensitive: "m" = minor, "M" = major
    if suffix == "m" or suffix == "-":
        return tonic, "minor"

    if suffix == "M":
        return tonic, "major"

    sl = suffix.lower()
    if sl in ("min", "minor"):
        return tonic, "minor"
    if sl in ("maj", "major"):
        return tonic, "major"

    return None, None
