"""Voice-leading logic to connect consecutive chord voicings smoothly."""

from __future__ import annotations

from itertools import permutations
from typing import List, Sequence


def _closest_pitch_class_tone(target_note: int, previous_note: int) -> int:
    """Find octave-shifted target note with smallest movement to previous note."""
    candidates = [target_note + 12 * k for k in range(-3, 4)]
    return min(candidates, key=lambda n: (abs(n - previous_note), n))


def generate_voice_leading(voicings: Sequence[Sequence[int]]) -> List[List[int]]:
    """Apply global minimal-movement voice leading to MIDI voicings."""
    if not voicings:
        return []

    led: List[List[int]] = [sorted(int(n) for n in voicings[0])]

    for target in voicings[1:]:
        target_sorted = sorted(int(n) for n in target)
        previous = led[-1]

        # Assign target chord tones to voices by minimizing total movement.
        target_pcs = [n % 12 for n in target_sorted]
        best_notes: List[int] | None = None
        best_cost: int | None = None

        for perm in permutations(target_pcs):
            notes = []
            cost = 0
            for prev_note, pc in zip(previous, perm):
                near_octave = prev_note // 12
                candidates = [pc + 12 * (near_octave + d) for d in (-1, 0, 1)]
                picked = min(candidates, key=lambda n: (abs(n - prev_note), n))
                notes.append(picked)
                cost += abs(picked - prev_note)

            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_notes = notes

        led.append(best_notes if best_notes is not None else target_sorted)

    return led
