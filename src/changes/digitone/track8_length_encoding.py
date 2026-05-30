"""Track 8 explicit length encoding helpers for Changes Phase 4D.

This module intentionally does not import digitone-syx-toolkit at runtime.
Length semantics are kept toolkit-compatible using a local copy of the finite
Digitone explicit-length code mapping logic.

Provenance for mapping formulas:
- digitone-syx-toolkit/src/digitone_syx_toolkit/digitone2/length_codes.py
"""

from __future__ import annotations

from fractions import Fraction


def _explicit_length_code_to_sixteenth_units(code: int) -> Fraction:
    if code < 0x00 or code > 0x7F:
        raise ValueError(f"length code out of range: {code} (expected 0x00..0x7F)")
    if code == 0x7F:
        raise ValueError("INF (0x7F) does not map to finite sixteenth units")

    if code <= 0x1E:
        return Fraction(1, 8) + Fraction(code, 16)
    if code <= 0x2E:
        return Fraction(17, 8) + Fraction(code - 0x1F, 8)
    if code <= 0x3E:
        return Fraction(17, 4) + Fraction(code - 0x2F, 4)
    if code <= 0x4E:
        return Fraction(17, 2) + Fraction(code - 0x3F, 2)
    if code <= 0x5E:
        return Fraction(17, 1) + Fraction(code - 0x4F, 1)
    if code <= 0x6E:
        return Fraction(34, 1) + Fraction((code - 0x5F) * 2, 1)
    return Fraction(68, 1) + Fraction((code - 0x6F) * 4, 1)


def _find_exact_length_code_for_sixteenth_units(units: Fraction) -> int | None:
    target = Fraction(units)
    for code in range(0x00, 0x7F):
        if _explicit_length_code_to_sixteenth_units(code) == target:
            return code
    return None


def encode_digitone_length_from_duration_quarters(
    duration_quarters: str,
    *,
    steps_per_quarter: int = 4,
) -> str:
    """Encode quarter-note duration to toolkit-compatible explicit length code.

    Returns uppercase hex strings like 0x1E, 0x2E, 0x3E, 0x4E.
    """
    if not isinstance(steps_per_quarter, int) or steps_per_quarter <= 0:
        raise ValueError(f"steps_per_quarter must be a positive integer: {steps_per_quarter!r}")
    if steps_per_quarter != 4:
        raise ValueError(
            "steps_per_quarter other than 4 is not supported by this encoder: "
            f"{steps_per_quarter}"
        )

    try:
        duration = Fraction(duration_quarters)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"invalid duration_quarters: {duration_quarters!r}") from exc

    if duration <= 0:
        raise ValueError(f"duration_quarters must be > 0: {duration_quarters!r}")

    # One quarter note equals four sixteenth-note units.
    sixteenth_units = duration * 4
    code = _find_exact_length_code_for_sixteenth_units(sixteenth_units)
    if code is None:
        raise ValueError(
            "no exact finite Digitone explicit length code for duration_quarters: "
            f"duration_quarters={duration_quarters!r} sixteenth_units={sixteenth_units}"
        )

    return f"0x{code:02X}"
