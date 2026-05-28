"""Voice-leading logic to connect consecutive chord voicings smoothly."""

from __future__ import annotations

from collections import Counter
from itertools import permutations
from itertools import product
from typing import List, Sequence


class RegisterFitError(ValueError):
    """Raised when a chord pitch-class multiset cannot be realized in the requested range."""


def _closest_pitch_class_tone(target_note: int, previous_note: int) -> int:
    """Find octave-shifted target note with smallest movement to previous note."""
    candidates = [target_note + 12 * k for k in range(-3, 4)]
    return min(candidates, key=lambda n: (abs(n - previous_note), n))


def _pitch_class_multiset(notes: Sequence[int]) -> tuple[int, ...]:
    return tuple(int(n) % 12 for n in notes)


def _range_candidates_for_pitch_class(pc: int, min_midi: int, max_midi: int) -> tuple[int, ...]:
    return tuple(note for note in range(min_midi, max_midi + 1) if note % 12 == pc)


def _unique_permutations(values: Sequence[int]) -> list[tuple[int, ...]]:
    # Voice count is fixed at six, so set(permutations()) is acceptable and deterministic after sorting.
    return sorted(set(permutations(tuple(values))))


def fit_bounded_voice_vector(
    target_notes: Sequence[int],
    reference_notes: Sequence[int],
    *,
    min_midi: int,
    max_midi: int,
    context: str | None = None,
) -> List[int]:
    """Fit target pitch classes into a bounded MIDI range with minimum lane-wise motion."""
    if min_midi > max_midi:
        raise ValueError(f"Invalid range: min_midi={min_midi} > max_midi={max_midi}")

    target_pcs = _pitch_class_multiset(target_notes)
    reference = [int(n) for n in reference_notes]
    if len(target_pcs) != len(reference):
        raise ValueError(
            f"voice count mismatch: target={len(target_pcs)} reference={len(reference)}"
        )

    best_candidate: tuple[int, ...] | None = None
    best_cost: tuple[int, int, int, tuple[int, ...]] | None = None

    for lane_pcs in _unique_permutations(target_pcs):
        lane_candidates: list[tuple[int, ...]] = []
        infeasible = False
        for pc in lane_pcs:
            notes = _range_candidates_for_pitch_class(pc, min_midi, max_midi)
            if not notes:
                infeasible = True
                break
            lane_candidates.append(notes)
        if infeasible:
            continue

        for candidate in product(*lane_candidates):
            if len(set(candidate)) != len(candidate):
                continue

            distances = [abs(candidate[idx] - reference[idx]) for idx in range(len(reference))]
            cost = (
                tuple(distances),
                sum(distances),
                max(distances, default=0),
                max(candidate),
                tuple(int(n) for n in candidate),
            )
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_candidate = tuple(int(n) for n in candidate)

    if best_candidate is None:
        context_text = f" context={context}" if context else ""
        raise RegisterFitError(
            "No in-range realization for pitch-class multiset"
            f"{context_text} target_multiset={dict(Counter(target_pcs))}"
            f" range={min_midi}..{max_midi}"
        )

    return [int(n) for n in best_candidate]


def _generate_unbounded_voice_leading(voicings: Sequence[Sequence[int]]) -> List[List[int]]:
    """Legacy unrestricted minimum-motion voice leading."""
    led: List[List[int]] = [sorted(int(n) for n in voicings[0])]

    for target in voicings[1:]:
        target_sorted = sorted(int(n) for n in target)
        previous = led[-1]

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


def generate_voice_leading(
    voicings: Sequence[Sequence[int]],
    *,
    min_midi: int | None = None,
    max_midi: int | None = None,
) -> List[List[int]]:
    """Apply sequential minimum-motion voice leading with optional bounded register fitting."""
    if not voicings:
        return []

    if min_midi is None and max_midi is None:
        return _generate_unbounded_voice_leading(voicings)
    if min_midi is None or max_midi is None:
        raise ValueError("Both min_midi and max_midi are required for bounded voice leading")

    first_target = [int(n) for n in voicings[0]]
    led: List[List[int]] = [
        fit_bounded_voice_vector(
            first_target,
            first_target,
            min_midi=min_midi,
            max_midi=max_midi,
            context="chord_index=1",
        )
    ]

    for chord_index, target in enumerate(voicings[1:], start=2):
        target_notes = [int(n) for n in target]
        previous_bounded = led[-1]
        fitted = fit_bounded_voice_vector(
            target_notes,
            previous_bounded,
            min_midi=min_midi,
            max_midi=max_midi,
            context=f"chord_index={chord_index}",
        )
        led.append(fitted)

    return led
