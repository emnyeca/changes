"""Digitone compile timing/length planner and event compiler."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from math import gcd

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


def choose_timing_plan(timeline: RenderedTimeline, target: DigitoneTargetProfile) -> TimingPlan:
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
        if total_steps < 2 or total_steps > 128:
            continue

        for speed in preferred:
            device_tempo = compute_digitone_device_tempo(timeline.performance_tempo, q_step, speed)
            if Fraction(30, 1) <= device_tempo <= Fraction(300, 1):
                return TimingPlan(speed_ratio=speed, q_step=q_step, device_tempo=device_tempo, total_steps=total_steps)

    raise ValueError("No valid timing plan: speed/tempo range or 128-step capacity constraints are not satisfiable")


def _midi_to_digitone_note_name(note_midi: int) -> str:
    return midi_to_digitone_display_note_name(note_midi)


def _find_exact_length_code_for_units(units: Fraction) -> int | None:
    try:
        from digitone_syx_toolkit.digitone2.length_codes import (
            find_exact_length_code_for_sixteenth_units,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "digitone-syx-toolkit is required for Digitone compilation. "
            "Install with: pip install -e ../digitone-syx-toolkit"
        ) from exc

    return find_exact_length_code_for_sixteenth_units(Fraction(units))


def compile_timeline_to_digitone_plan(timeline: RenderedTimeline, target: DigitoneTargetProfile) -> DigitoneCompilePlan:
    timing = choose_timing_plan(timeline, target)

    events: list[CompiledDigitoneEvent] = []
    seen_pairs: set[tuple[int, int]] = set()

    for event in sorted(timeline.events, key=lambda e: (e.onset_quarters, e.voice_id, e.id)):
        if event.voice_id not in target.voice_to_track:
            continue

        track = target.voice_to_track[event.voice_id]
        step_fraction = event.onset_quarters / timing.q_step
        if step_fraction.denominator != 1:
            raise ValueError(f"event onset is not on planner step grid: {event.id}")
        step = int(step_fraction) + 1

        pair = (track, step)
        if pair in seen_pairs:
            raise ValueError(f"Compile conflict: duplicate track/step detected for track={track}, step={step}")
        seen_pairs.add(pair)

        length_units = event.duration_quarters / (timing.speed_ratio * timing.q_step)
        code = _find_exact_length_code_for_units(length_units)
        if code is None:
            raise ValueError(
                f"No exact length code for duration units={length_units} (event={event.id}); approximation is disabled"
            )

        events.append(
            CompiledDigitoneEvent(
                source_event_id=event.id,
                track=track,
                step=step,
                note=_midi_to_digitone_note_name(event.note_midi),
                velocity=target.default_velocity,
                length_code=code,
            )
        )

    return DigitoneCompilePlan(
        title=timeline.title,
        performance_tempo=timeline.performance_tempo,
        speed=speed_fraction_to_label(timing.speed_ratio),
        speed_ratio=timing.speed_ratio,
        q_step=timing.q_step,
        device_tempo=timing.device_tempo,
        total_steps=timing.total_steps,
        events=tuple(events),
        warnings=tuple(),
    )
