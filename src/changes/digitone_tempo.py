"""Tempo conversion helpers for Digitone Native SysEx backend."""

from __future__ import annotations

from fractions import Fraction


def compute_digitone_device_tempo(performance_tempo: Fraction | float, q_step: Fraction) -> float:
    """Compute Digitone device tempo for SPEED=1/8 playback equivalence."""
    return 2.0 * float(performance_tempo) / float(q_step)


def validate_digitone_device_tempo(device_tempo: float) -> float:
    """Validate Digitone tempo range accepted by current backend scope."""
    if device_tempo < 30.0 or device_tempo > 300.0:
        raise ValueError(f"digitone_device_tempo out of supported range 30.0..300.0: {device_tempo}")
    return device_tempo
