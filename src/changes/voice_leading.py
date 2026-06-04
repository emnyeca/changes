"""Voice-leading logic to connect consecutive chord voicings smoothly."""

from __future__ import annotations

import hashlib
import math
from bisect import bisect_left
from collections import Counter
from itertools import permutations
from typing import List, Sequence


def _deterministic_bit(*parts: object) -> int:
    """Return 0 or 1 from a stable SHA-256 hash of the given parts."""
    key = "|".join(str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(key).digest()[0] & 1


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


def _assign_minimum_motion_target(
    previous_notes: Sequence[int],
    target_notes: Sequence[int],
    *,
    tie_break_seed: int | None = None,
    chord_index: int = 0,
) -> list[int]:
    """Assign target pitch classes to current lanes with unrestricted minimum-motion search."""
    previous = [int(n) for n in previous_notes]
    target_pcs = [int(n) % 12 for n in sorted(int(n) for n in target_notes)]

    best_notes: list[int] | None = None
    best_cost: tuple[int, int, tuple[int, ...]] | None = None

    for perm in _unique_permutations(target_pcs):
        notes: list[int] = []
        distances: list[int] = []
        for voice_index, (prev_note, pc) in enumerate(zip(previous, perm)):
            near_octave = prev_note // 12
            # Keep ordinary voice leading local; bounded repair stage handles register overflow.
            candidates = [pc + 12 * (near_octave + d) for d in (-1, 0, 1)]
            if tie_break_seed is None:
                picked = min(candidates, key=lambda n: (abs(n - prev_note), n))
            else:
                min_dist = min(abs(n - prev_note) for n in candidates)
                tied = [n for n in candidates if abs(n - prev_note) == min_dist]
                if len(tied) == 1:
                    picked = tied[0]
                else:
                    bit = _deterministic_bit(tie_break_seed, "cloud_tiebreak", chord_index, voice_index, pc)
                    picked = max(tied) if bit else min(tied)
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


def _slide_on_pitch_order(
    vector: Sequence[int],
    donor_lane: int,
    missing_note: int,
) -> tuple[int, ...]:
    indexed = [(lane, int(note)) for lane, note in enumerate(vector)]
    ordered = sorted(indexed, key=lambda item: (item[1], item[0]))

    ordered_lanes = [lane for lane, _note in ordered]
    ordered_notes = [note for _lane, note in ordered]

    donor_pos = ordered_lanes.index(int(donor_lane))
    insert_pos = bisect_left(ordered_notes, int(missing_note))

    transformed = list(ordered_notes)
    transformed.pop(donor_pos)
    if donor_pos < insert_pos:
        insert_pos -= 1
    transformed.insert(insert_pos, int(missing_note))

    lane_to_note = {lane: note for lane, note in enumerate(int(n) for n in vector)}
    for pos, lane in enumerate(ordered_lanes):
        lane_to_note[lane] = transformed[pos]
    return tuple(lane_to_note[lane] for lane in range(len(vector)))


def _pc_target_at_or_below(pc: int, max_val: int) -> int:
    """Largest int with (result % 12 == pc) and result <= max_val."""
    return max_val - (max_val - pc) % 12


def _pc_target_at_or_above(pc: int, min_val: int) -> int:
    """Smallest int with (result % 12 == pc) and result >= min_val."""
    return min_val + (pc - min_val) % 12


def _donor_for_down_target(notes: list[int], missing: int) -> int | None:
    """Lane index of a note with same PC as missing that is > missing (can slide down to it)."""
    pc = missing % 12
    candidates = [i for i, n in enumerate(notes) if n % 12 == pc and n > missing]
    return min(candidates, key=lambda i: notes[i]) if candidates else None


def _donor_for_up_target(notes: list[int], missing: int) -> int | None:
    """Lane index of a note with same PC as missing that is < missing (can slide up to it)."""
    pc = missing % 12
    candidates = [i for i, n in enumerate(notes) if n % 12 == pc and n < missing]
    return max(candidates, key=lambda i: notes[i]) if candidates else None


def fit_cloud_center_spread_voice_vector(
    target_notes: Sequence[int],
    reference_notes: Sequence[int],
    *,
    center_midi: int,
    spread_min: int,
    spread_max: int,
    average_tolerance: int,
    tie_break_seed: int | None = None,
    chord_index: int = 0,
) -> list[int]:
    """Repair cloud voicing via a center/average/spread re-validation loop.

    reference_notes is accepted for API symmetry with fit_bounded_voice_vector but is unused.

    State machine:
      ① avg_validate → OK → spread_validate; NG → avg_repair
      ② spread_validate → OK → check; NG → spread_repair
      ③ check: both OK → return; else → avg_validate
      ④ avg_repair: compute exact PC-matching target; after OK → spread_validate
      ⑤ spread_repair: compute PC-matching target from middle/extreme analysis; after OK → avg_validate
    """
    notes = [int(n) for n in target_notes]
    n = len(notes)

    averageOK = False
    spreadOK = False
    state = "avg_validate"
    _MAX_ITER = 24  # internal safety limit; not a user parameter

    for _ in range(_MAX_ITER):

        # ① Average validation ─────────────────────────────────────────────────
        if state == "avg_validate":
            avg = sum(notes) / n
            if abs(avg - center_midi) <= average_tolerance:
                averageOK = True
                state = "spread_validate"
            else:
                state = "avg_repair"

        # ② Spread validation ──────────────────────────────────────────────────
        elif state == "spread_validate":
            spread = max(notes) - min(notes)
            if spread_min <= spread <= spread_max:
                spreadOK = True
                state = "check"
            else:
                state = "spread_repair"

        # ③ Flag check ─────────────────────────────────────────────────────────
        elif state == "check":
            if averageOK and spreadOK:
                return notes
            state = "avg_validate"

        # ④ Average repair ─────────────────────────────────────────────────────
        elif state == "avg_repair":
            prev = list(notes)
            avg = sum(notes) / n
            delta = avg - center_midi

            if delta > average_tolerance:
                high = max(notes)
                high_lane = notes.index(high)
                S = sum(notes) - high
                # Compute the largest PC-matching note that brings avg within tolerance.
                target_max = math.floor(n * (center_midi + average_tolerance) - S)
                missing = _pc_target_at_or_below(high % 12, target_max)
                if missing >= high:
                    missing -= 12
                if missing not in notes:
                    notes = list(_slide_on_pitch_order(notes, donor_lane=high_lane, missing_note=missing))
            elif delta < -average_tolerance:
                low = min(notes)
                low_lane = notes.index(low)
                S = sum(notes) - low
                # Compute the smallest PC-matching note that brings avg within tolerance.
                target_min = math.ceil(n * (center_midi - average_tolerance) - S)
                missing = _pc_target_at_or_above(low % 12, target_min)
                if missing <= low:
                    missing += 12
                if missing not in notes:
                    notes = list(_slide_on_pitch_order(notes, donor_lane=low_lane, missing_note=missing))

            if notes == prev:
                return notes  # no progress; bail

            if abs(sum(notes) / n - center_midi) <= average_tolerance:
                averageOK = True
                spreadOK = False
                state = "spread_validate"
            else:
                state = "avg_repair"

        # ⑤ Spread repair ──────────────────────────────────────────────────────
        elif state == "spread_repair":
            prev = list(notes)
            spread = max(notes) - min(notes)

            if spread < spread_min:
                sorted_n = sorted(notes)
                mid_lo = sorted_n[n // 2 - 1]
                mid_hi = sorted_n[n // 2]
                dist_lo = abs(mid_lo - center_midi)
                dist_hi = abs(mid_hi - center_midi)

                if dist_lo < dist_hi:
                    direction = "down"
                elif dist_hi < dist_lo:
                    direction = "up"
                else:
                    bit = _deterministic_bit(
                        tie_break_seed if tie_break_seed is not None else 0,
                        "spread_closed_tiebreak", chord_index, mid_lo, mid_hi,
                    )
                    direction = "up" if bit else "down"

                if direction == "down":
                    # Place a PC-matching note at max - spread_min, expanding downward.
                    for target in range(max(notes) - spread_min, max(notes) - spread_min - 12, -1):
                        lane = _donor_for_down_target(notes, target)
                        if lane is not None and target not in notes:
                            notes = list(_slide_on_pitch_order(notes, donor_lane=lane, missing_note=target))
                            break
                else:
                    # Place a PC-matching note at min + spread_min, expanding upward.
                    for target in range(min(notes) + spread_min, min(notes) + spread_min + 12):
                        lane = _donor_for_up_target(notes, target)
                        if lane is not None and target not in notes:
                            notes = list(_slide_on_pitch_order(notes, donor_lane=lane, missing_note=target))
                            break

            elif spread > spread_max:
                high = max(notes)
                low = min(notes)
                dist_hi = abs(high - center_midi)
                dist_lo = abs(low - center_midi)

                if dist_hi > dist_lo:
                    compress_high = True
                elif dist_lo > dist_hi:
                    compress_high = False
                else:
                    compress_high = bool(_deterministic_bit(
                        tie_break_seed if tie_break_seed is not None else 0,
                        "spread_open_tiebreak", chord_index, high, low,
                    ))

                if compress_high:
                    # Move high note to the PC-matching position at min + spread_max.
                    target = _pc_target_at_or_below(high % 12, min(notes) + spread_max)
                    if target >= high:
                        target -= 12
                    if target not in notes:
                        notes = list(_slide_on_pitch_order(notes, donor_lane=notes.index(high), missing_note=target))
                else:
                    # Move low note to the PC-matching position at max - spread_max.
                    target = _pc_target_at_or_above(low % 12, max(notes) - spread_max)
                    if target <= low:
                        target += 12
                    if target not in notes:
                        notes = list(_slide_on_pitch_order(notes, donor_lane=notes.index(low), missing_note=target))

            if notes == prev:
                return notes  # no progress; bail

            if spread_min <= max(notes) - min(notes) <= spread_max:
                spreadOK = True
                averageOK = False
                state = "avg_validate"
            else:
                state = "spread_repair"

    return notes


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
            candidate = _slide_on_pitch_order(
                absorbed,
                donor_lane=donor_idx,
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
    tie_break_seed: int | None = None,
    chord_index: int = 0,
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

    if tie_break_seed is None:
        best_candidate = min(
            finals,
            key=lambda candidate: (
                sum(abs(int(candidate[idx]) - reference[idx]) for idx in range(len(reference))),
                max(abs(int(candidate[idx]) - reference[idx]) for idx in range(len(reference))),
                max(int(n) for n in candidate),
                tuple(int(n) for n in candidate),
            ),
        )
    else:
        def _bounded_key(candidate: tuple[int, ...]) -> tuple[int, int, int]:
            sum_dist = sum(abs(int(candidate[idx]) - reference[idx]) for idx in range(len(reference)))
            max_dist = max(abs(int(candidate[idx]) - reference[idx]) for idx in range(len(reference)))
            det = _deterministic_bit(tie_break_seed, "cloud_bounded_tiebreak", chord_index, candidate)
            return (sum_dist, max_dist, det)
        best_candidate = min(finals, key=_bounded_key)
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
    tie_break_seed: int | None = None,
    center_midi: int | None = None,
    spread_min: int | None = None,
    spread_max: int | None = None,
    average_tolerance: int | None = None,
) -> List[List[int]]:
    """Apply sequential minimum-motion voice leading with optional repair.

    Two repair modes (mutually exclusive):
      center/spread mode: all of center_midi, spread_min, spread_max, average_tolerance provided.
      bounded range mode: both min_midi and max_midi provided.

    tie_break_seed: if None, uses the existing downward-biased tie-break (backwards-compatible).
    """
    if not voicings:
        return []

    _center_mode = all(p is not None for p in (center_midi, spread_min, spread_max, average_tolerance))
    _range_mode = min_midi is not None and max_midi is not None

    if any(p is not None for p in (center_midi, spread_min, spread_max, average_tolerance)) and not _center_mode:
        raise ValueError("center_midi, spread_min, spread_max, and average_tolerance must all be provided together")
    if (min_midi is None) != (max_midi is None):
        raise ValueError("Both min_midi and max_midi are required for bounded voice leading")
    if _center_mode and _range_mode:
        raise ValueError("Cannot combine center/spread mode with min/max range mode")

    if not _center_mode and not _range_mode:
        return _generate_unbounded_voice_leading(voicings)

    first_target = [int(n) for n in voicings[0]]

    if _center_mode:
        led: List[List[int]] = [
            fit_cloud_center_spread_voice_vector(
                first_target, first_target,
                center_midi=center_midi,
                spread_min=spread_min,
                spread_max=spread_max,
                average_tolerance=average_tolerance,
                tie_break_seed=tie_break_seed,
                chord_index=1,
            )
        ]
        for chord_index, target in enumerate(voicings[1:], start=2):
            target_notes = [int(n) for n in target]
            pre_fit = _assign_minimum_motion_target(
                led[-1], target_notes,
                tie_break_seed=tie_break_seed,
                chord_index=chord_index,
            )
            led.append(fit_cloud_center_spread_voice_vector(
                pre_fit, pre_fit,
                center_midi=center_midi,
                spread_min=spread_min,
                spread_max=spread_max,
                average_tolerance=average_tolerance,
                tie_break_seed=tie_break_seed,
                chord_index=chord_index,
            ))
        return led

    # bounded range mode
    led = [
        fit_bounded_voice_vector(
            first_target, first_target,
            min_midi=min_midi,
            max_midi=max_midi,
            context="chord_index=1",
            tie_break_seed=tie_break_seed,
            chord_index=1,
        )
    ]
    for chord_index, target in enumerate(voicings[1:], start=2):
        target_notes = [int(n) for n in target]
        previous_bounded = led[-1]

        # Stage 1: ordinary minimum-motion assignment from previous audible bounded state.
        pre_fit = _assign_minimum_motion_target(
            previous_bounded, target_notes,
            tie_break_seed=tie_break_seed,
            chord_index=chord_index,
        )

        # Stage 2: bounded register repair by boundary-slide operations.
        fitted = fit_bounded_voice_vector(
            pre_fit, pre_fit,
            min_midi=min_midi,
            max_midi=max_midi,
            context=f"chord_index={chord_index}",
            tie_break_seed=tie_break_seed,
            chord_index=chord_index,
        )
        led.append(fitted)

    return led
