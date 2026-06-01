"""No Chord symbol helpers."""

from __future__ import annotations

import re


def is_no_chord_symbol(symbol: str | None) -> bool:
    """Return True when a symbol represents a no-chord region.

    Matching is case-insensitive and tolerant to punctuation/spacing.
    """
    if symbol is None:
        return False

    normalized = re.sub(r"[^A-Z]", "", symbol.upper())
    return normalized in {"NC", "NOCHORD"}
