"""Digitone compile timing/length planner and event compiler."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from math import gcd

from changes.digitone.pattern_name_policy import finalize_single_pattern_auto_name
from changes.digitone.note_encoding import midi_to_digitone_display_note_name
from changes.models.digitone_compile_plan import CompiledDigitoneEvent, DigitoneCompilePlan
from changes.models.digitone_target_profile import DigitoneTargetProfile, speed_fraction_to_label
from changes.models.rendered_timeline import RenderedTimeline


def compute_digitone_device_tempo(performance_tempo: Fraction, q_step: Fraction, speed_ratio: Fraction) -> Fraction:
    return Fraction(performance_tempo, 1) / (Fraction(4, 1) * speed_ratio * q_step)


def compute_digitone_device_tempo_for_speed_one_eighth(performance_tempo: Fraction, q_step: Fraction) -> Fraction:
    return compute_digitone_device_tempo(performance_tempo, q_step, Fraction(1, 8))


def _gcd_int(values: list[int]) -> int:
    return reduce(gcd, values)


def infer_base_q_step(timeline: RenderedTimeline) -> Fraction:
    boundaries = set([Fraction(0, 1)])
    for e in timeline.events:
        boundaries.add(e.onset_quarters)
        boundaries.add(e.onset_quarters + e.duration_quarters)

    den_lcm = 1
    for b in boundaries:
        den_lcm = den_lcm * b.denominator // gcd(den_lcm, b.denominator)
    nums = [int(b * den_lcm) for b in boundaries]
    g = _gcd_int(nums)
    return Fraction(g, den_lcm)


def _is_integer_multiple(value: Fraction, step: Fraction) -> bool:
    q = value / step
    return q.denominator == 1


@dataclass(frozen=True)
class TimingPlan:
    speed_ratio: Fraction
    q_step: Fraction
    device_tempo: Fraction
    total_steps: int


def _choose_timing_plan(
    timeline: RenderedTimeline,
    target: DigitoneTargetProfile,
    *,
    enforce_pattern_capacity: bool,
) -> TimingPlan:
    preferred = [target.preferred_speed]
    for s in target.fallback_speeds:
        if s not in preferred:
            preferred.append(s)

    base_q = infer_base_q_step(timeline)
    total_duration = max((e.onset_quarters + e.duration_quarters for e in timeline.events), default=Fraction(0, 1))

    for refine in range(1, 2049):
        q_step = base_q / refine

        if any(not _is_integer_multiple(e.onset_quarters, q_step) for e in timeline.events):
            continue
        if any(not _is_integer_multiple(e.onset_quarters + e.duration_quarters, q_step) for e in timeline.events):
            continue
        if not _is_integer_multiple(total_duration, q_step):
            continue

        total_steps = int(total_duration / q_step)
        if total_steps < 2:
            continue
        if enforce_pattern_capacity and total_steps > 128:
            continue

        for speed in preferred:
            device_tempo = compute_digitone_device_tempo(timeline.performance_tempo, q_step, speed)
            if Fraction(30, 1) <= device_tempo <= Fraction(300, 1):
                return TimingPlan(speed_ratio=speed, q_step=q_step, device_tempo=device_tempo, total_steps=total_steps)

    if enforce_pattern_capacity:
        raise ValueError("No valid timing plan: speed/tempo range or 128-step capacity constraints are not satisfiable")
    raise ValueError("No valid shared timing plan: speed/tempo range constraints are not satisfiable")


def choose_shared_timing_plan(timeline: RenderedTimeline, target: DigitoneTargetProfile) -> TimingPlan:
    """Choose song-level shared timing without applying per-pattern 128-step capacity limits."""
    return _choose_timing_plan(timeline, target, enforce_pattern_capacity=False)


def choose_timing_plan(timeline: RenderedTimeline, target: DigitoneTargetProfile) -> TimingPlan:
    """Choose timing for single-pattern export (includes 2..128 pattern capacity constraints)."""
    return _choose_timing_plan(timeline, target, enforce_pattern_capacity=True)


def _midi_to_digitone_note_name(note_midi: int) -> str:
    return midi_to_digitone_display_note_name(note_midi)


def _find_exact_length_code_for_units(units: Fraction) -> int | None:
    try:
        from digitone_syx_toolkit.digitone2.length_codes import (
            find_exact_length_code_for_sixteenth_units,
        )
    except ImportError:
        target = Fraction(units)
        for code in range(0x00, 0x7F):
            if _explicit_length_code_to_sixteenth_units_fallback(code) == target:
                return code
        return None

    return find_exact_length_code_for_sixteenth_units(Fraction(units))


def _explicit_length_code_to_sixteenth_units_fallback(code: int) -> Fraction:
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


def _length_step_candidates_for_speed(speed_ratio: Fraction) -> list[tuple[int, int]]:
    try:
        from digitone_syx_toolkit.digitone2.length_codes import explicit_length_code_to_sixteenth_units
    except ImportError:
        explicit_length_code_to_sixteenth_units = _explicit_length_code_to_sixteenth_units_fallback

    candidates: dict[int, int] = {}
    for code in range(0x00, 0x7F):
        try:
            units = explicit_length_code_to_sixteenth_units(code)
        except ValueError:
            continue
        steps = units * speed_ratio
        if steps.denominator != 1:
            continue
        step_count = int(steps)
        if step_count <= 0:
            continue
        candidates[step_count] = code

    return sorted(((steps, code) for steps, code in candidates.items()), key=lambda x: x[0], reverse=True)


def _split_duration_steps_into_exact_codes(duration_steps: int, speed_ratio: Fraction) -> list[tuple[int, int]]:
    if duration_steps <= 0:
        raise ValueError(f"duration_steps must be > 0, got {duration_steps}")

    candidates = _length_step_candidates_for_speed(speed_ratio)
    if not candidates:
        raise ValueError(f"No exact length candidates for speed_ratio={speed_ratio}")

    remaining = duration_steps
    out: list[tuple[int, int]] = []
    while remaining > 0:
        picked: tuple[int, int] | None = None
        for steps, code in candidates:
            if steps <= remaining:
                picked = (steps, code)
                break

        if picked is None:
            raise ValueError(
                f"No exact length-code decomposition for duration_steps={duration_steps} at speed_ratio={speed_ratio}"
            )

        out.append(picked)
        remaining -= picked[0]

    return out


def compile_timeline_events_with_timing(
    timeline: RenderedTimeline,
    target: DigitoneTargetProfile,
    timing: TimingPlan,
    *,
    step_start: int = 1,
    step_end: int | None = None,
    include_boundary_carryover: bool = False,
) -> tuple[CompiledDigitoneEvent, ...]:
    """Compile timeline events using a preselected timing plan.

    step_start/step_end define a global-step inclusive window. Returned events are
    remapped to local steps where local_step = global_step - step_start + 1.
    """
    if step_start < 1:
        raise ValueError(f"step_start must be >= 1, got {step_start}")
    if step_end is not None and step_end < step_start:
        raise ValueError(f"step_end must be >= step_start, got {step_end} < {step_start}")

    events: list[CompiledDigitoneEvent] = []
    seen_pairs: set[tuple[int, int]] = set()
    polyphonic_tracks = set(target.polyphonic_tracks)

    for event in sorted(timeline.events, key=lambda e: (e.onset_quarters, e.voice_id, e.id)):
        if event.voice_id not in target.voice_to_track:
            continue

        track = target.voice_to_track[event.voice_id]
        global_start_fraction = event.onset_quarters / timing.q_step
        if global_start_fraction.denominator != 1:
            raise ValueError(f"event onset is not on planner step grid: {event.id}")
        global_start_step = int(global_start_fraction) + 1

        global_end_fraction = (event.onset_quarters + event.duration_quarters) / timing.q_step
        if global_end_fraction.denominator != 1:
            raise ValueError(f"event end is not on planner step grid: {event.id}")
        global_end_step = int(global_end_fraction)

        if global_end_step < global_start_step:
            raise ValueError(f"event has invalid step span: {event.id}")

        intersects_window = not (global_end_step < step_start or (step_end is not None and global_start_step > step_end))
        if not intersects_window:
            continue

        if global_start_step < step_start and not include_boundary_carryover:
            continue

        emit_start = max(global_start_step, step_start)
        emit_end = global_end_step if step_end is None else min(global_end_step, step_end)
        if emit_end < emit_start:
            continue

        local_step = emit_start - step_start + 1
        duration_steps = Fraction(emit_end - emit_start + 1, 1)
        chunks = _split_duration_steps_into_exact_codes(int(duration_steps), timing.speed_ratio)

        offset = 0
        for chunk_index, (chunk_steps, code) in enumerate(chunks, start=1):
            chunk_local_step = local_step + offset
            pair = (track, chunk_local_step)
            if pair in seen_pairs and track not in polyphonic_tracks:
                raise ValueError(
                    f"Compile conflict: duplicate track/step detected for track={track}, local_step={chunk_local_step}"
                )
            seen_pairs.add(pair)

            source_event_id = event.id if len(chunks) == 1 else f"{event.id}#chunk{chunk_index}"
            events.append(
                CompiledDigitoneEvent(
                    source_event_id=source_event_id,
                    track=track,
                    step=chunk_local_step,
                    note=_midi_to_digitone_note_name(event.note_midi),
                    velocity=event.velocity if event.velocity is not None else target.default_velocity,
                    length_code=code,
                )
            )
            offset += chunk_steps

    return tuple(events)


def compile_timeline_to_digitone_plan(timeline: RenderedTimeline, target: DigitoneTargetProfile) -> DigitoneCompilePlan:
    timing = choose_timing_plan(timeline, target)
    events = compile_timeline_events_with_timing(timeline, target, timing)
    pattern_name, warnings = finalize_single_pattern_auto_name(timeline.title)

    return DigitoneCompilePlan(
        source_title=timeline.title,
        pattern_name=pattern_name,
        pattern_name_source="auto",
        performance_tempo=timeline.performance_tempo,
        speed=speed_fraction_to_label(timing.speed_ratio),
        speed_ratio=timing.speed_ratio,
        q_step=timing.q_step,
        device_tempo=timing.device_tempo,
        total_steps=timing.total_steps,
        events=tuple(events),
        warnings=warnings,
    )
