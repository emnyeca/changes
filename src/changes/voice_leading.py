"""Voice-leading logic to connect consecutive chord voicings smoothly."""

from __future__ import annotations

from collections import Counter
from itertools import permutations
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


def _assign_minimum_motion_target(previous_notes: Sequence[int], target_notes: Sequence[int]) -> list[int]:
    """Assign target pitch classes to current lanes with unrestricted minimum-motion search."""
    previous = [int(n) for n in previous_notes]
    target_pcs = [int(n) % 12 for n in sorted(int(n) for n in target_notes)]

    best_notes: list[int] | None = None
    best_cost: tuple[int, int, tuple[int, ...]] | None = None

    for perm in _unique_permutations(target_pcs):
        notes: list[int] = []
        distances: list[int] = []
        for prev_note, pc in zip(previous, perm):
            near_octave = prev_note // 12
            # Keep ordinary voice leading local; bounded repair stage handles register overflow.
            candidates = [pc + 12 * (near_octave + d) for d in (-1, 0, 1)]
            picked = min(candidates, key=lambda n: (abs(n - prev_note), n))
            notes.append(int(picked))
            distances.append(abs(int(picked) - prev_note))

        cost = (
            sum(distances),
            max(distances, default=0),
            tuple(int(n) for n in notes),
        )
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_notes = notes

    if best_notes is None:
        return [int(n) for n in target_notes]
    return best_notes


def _slide_remove_donor_insert_missing(
    vector: Sequence[int],
    donor_index: int,
    insert_index: int,
    missing_note: int,
) -> tuple[int, ...]:
    out = list(int(n) for n in vector)
    if insert_index <= donor_index:
        for idx in range(donor_index, insert_index, -1):
            out[idx] = out[idx - 1]
        out[insert_index] = int(missing_note)
    else:
        for idx in range(donor_index, insert_index):
            out[idx] = out[idx + 1]
        out[insert_index] = int(missing_note)
    return tuple(out)


def _repair_single_overflow_states(
    current: Sequence[int],
    overflow_index: int,
    *,
    min_midi: int,
    max_midi: int,
    original_multiset: Counter,
) -> list[tuple[int, ...]]:
    original_note = int(current[overflow_index])
    if min_midi <= original_note <= max_midi:
        return []

    boundary_note = min_midi if original_note < min_midi else max_midi
    boundary_pc = boundary_note % 12
    missing_pc = original_note % 12

    absorbed = [int(n) for n in current]
    absorbed[overflow_index] = boundary_note

    donors = [
        idx
        for idx, note in enumerate(absorbed)
        if min_midi <= note <= max_midi and note % 12 == boundary_pc
    ]
    if not donors:
        return []

    missing_notes = _range_candidates_for_pitch_class(missing_pc, min_midi, max_midi)
    if not missing_notes:
        return []

    states: set[tuple[int, ...]] = set()
    for donor_idx in donors:
        for missing_note in missing_notes:
            for insert_idx in range(len(absorbed)):
                candidate = _slide_remove_donor_insert_missing(
                    absorbed,
                    donor_index=donor_idx,
                    insert_index=insert_idx,
                    missing_note=int(missing_note),
                )
                if Counter(_pitch_class_multiset(candidate)) != original_multiset:
                    continue
                states.add(candidate)
    return sorted(states)


def fit_bounded_voice_vector(
    target_notes: Sequence[int],
    reference_notes: Sequence[int],
    *,
    min_midi: int,
    max_midi: int,
    context: str | None = None,
) -> List[int]:
    """Repair out-of-range lanes by boundary-slide operations on an already lane-assigned vector."""
    if min_midi > max_midi:
        raise ValueError(f"Invalid range: min_midi={min_midi} > max_midi={max_midi}")

    start_vector = tuple(int(n) for n in target_notes)
    target_pcs = _pitch_class_multiset(start_vector)
    reference = [int(n) for n in reference_notes]
    if len(start_vector) != len(reference):
        raise ValueError(
            f"voice count mismatch: target={len(start_vector)} reference={len(reference)}"
        )

    target_multiset = Counter(target_pcs)

    pending = [start_vector]
    seen: set[tuple[int, ...]] = {start_vector}
    finals: list[tuple[int, ...]] = []

    while pending:
        current = pending.pop()
        in_range = all(min_midi <= int(n) <= max_midi for n in current)
        if in_range:
            if Counter(_pitch_class_multiset(current)) == target_multiset and len(set(current)) == len(current):
                finals.append(current)
            continue

        for overflow_index, note in enumerate(current):
            if min_midi <= int(note) <= max_midi:
                continue
            next_states = _repair_single_overflow_states(
                current,
                overflow_index,
                min_midi=min_midi,
                max_midi=max_midi,
                original_multiset=target_multiset,
            )
            for nxt in next_states:
                if nxt not in seen:
                    seen.add(nxt)
                    pending.append(nxt)

    if not finals:
        context_text = f" context={context}" if context else ""
        raise RegisterFitError(
            "No in-range realization for pitch-class multiset"
            f"{context_text} target_multiset={dict(target_multiset)}"
            f" range={min_midi}..{max_midi}"
        )

    best_candidate = min(
        finals,
        key=lambda candidate: (
            sum(abs(int(candidate[idx]) - reference[idx]) for idx in range(len(reference))),
            max(abs(int(candidate[idx]) - reference[idx]) for idx in range(len(reference))),
            max(int(n) for n in candidate),
            tuple(int(n) for n in candidate),
        ),
    )
    return [int(n) for n in best_candidate]


def _generate_unbounded_voice_leading(voicings: Sequence[Sequence[int]]) -> List[List[int]]:
    """Legacy unrestricted minimum-motion voice leading."""
    led: List[List[int]] = [sorted(int(n) for n in voicings[0])]

    for target in voicings[1:]:
        target_sorted = sorted(int(n) for n in target)
        previous = led[-1]
        led.append(_assign_minimum_motion_target(previous, target_sorted))

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

        # Stage 1: ordinary minimum-motion assignment from previous audible bounded state.
        pre_fit = _assign_minimum_motion_target(previous_bounded, target_notes)

        # Stage 2: bounded register repair by boundary-slide operations.
        fitted = fit_bounded_voice_vector(
            pre_fit,
            pre_fit,
            min_midi=min_midi,
            max_midi=max_midi,
            context=f"chord_index={chord_index}",
        )
        led.append(fitted)

    return led
