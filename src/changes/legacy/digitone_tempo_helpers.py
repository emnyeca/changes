"""Legacy tempo helpers kept only for historical schedule regression tests."""

from __future__ import annotations

from typing import Dict, List, Tuple


def compute_digitone_tempo_for_same_duration(
    performance_tempo: int | float,
    meter_numerator: int,
    meter_denominator: int,
    steps_per_bar: int,
) -> int:
    if meter_numerator <= 0 or meter_denominator <= 0 or steps_per_bar <= 0:
        raise ValueError("meter and steps_per_bar must be positive")

    quarters_per_bar = (4.0 * float(meter_numerator)) / float(meter_denominator)
    quarters_per_step = quarters_per_bar / float(steps_per_bar)
    device_tempo = float(performance_tempo) / (2.0 * quarters_per_step)
    return int(round(device_tempo))


def apply_digitone_tempo_floor(
    digitone_tempo: int,
    total_length_steps: int,
    events: List[Dict[str, int | str]],
) -> Tuple[int, int, List[Dict[str, int | str]]]:
    tempo = int(digitone_tempo)
    length = int(total_length_steps)
    scaled_events = [dict(e) for e in events]

    while tempo < 30:
        if length % 2 != 0:
            break
        if any((int(e["step"]) - 1) % 2 != 0 or int(e["duration_steps"]) % 2 != 0 for e in scaled_events):
            break

        tempo *= 2
        length //= 2
        for e in scaled_events:
            e["step"] = ((int(e["step"]) - 1) // 2) + 1
            e["duration_steps"] = int(e["duration_steps"]) // 2

    return tempo, length, scaled_events
