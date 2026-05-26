"""Bundle-oriented Digitone planning models."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from changes.models.digitone_compile_plan import CompiledDigitoneEvent


def _fraction_to_text(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


@dataclass(frozen=True)
class DigitoneSongTimingPlan:
    performance_tempo: Fraction
    speed: str
    speed_ratio: Fraction
    q_step: Fraction
    device_tempo: Fraction


@dataclass(frozen=True)
class DigitonePatternSegment:
    source_title: str
    pattern_name: str
    pattern_name_source: str
    section_id: str | None
    section_label: str | None
    section_token: str | None
    section_occurrence_index: int | None
    section_global_order_index: int | None
    segment_index: int
    section_split_index: int
    section_split_count: int
    global_step_start: int
    global_step_end: int
    total_steps: int
    events: tuple[CompiledDigitoneEvent, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class DigitonePatternBundlePlan:
    source_title: str
    timing: DigitoneSongTimingPlan
    patterns: tuple[DigitonePatternSegment, ...]
    warnings: tuple[str, ...]


def digitone_song_timing_plan_to_dict(plan: DigitoneSongTimingPlan) -> dict:
    return {
        "performance_tempo": _fraction_to_text(plan.performance_tempo),
        "speed": plan.speed,
        "speed_ratio": _fraction_to_text(plan.speed_ratio),
        "q_step": _fraction_to_text(plan.q_step),
        "device_tempo": _fraction_to_text(plan.device_tempo),
    }


def digitone_pattern_bundle_plan_to_dict(plan: DigitonePatternBundlePlan) -> dict:
    return {
        "source_title": plan.source_title,
        "timing": digitone_song_timing_plan_to_dict(plan.timing),
        "warnings": list(plan.warnings),
        "patterns": [
            {
                "source_title": p.source_title,
                "pattern_name": p.pattern_name,
                "pattern_name_source": p.pattern_name_source,
                "section_id": p.section_id,
                "section_label": p.section_label,
                "section_token": p.section_token,
                "section_occurrence_index": p.section_occurrence_index,
                "section_global_order_index": p.section_global_order_index,
                "segment_index": p.segment_index,
                "section_split_index": p.section_split_index,
                "section_split_count": p.section_split_count,
                "global_step_start": p.global_step_start,
                "global_step_end": p.global_step_end,
                "total_steps": p.total_steps,
                "warnings": list(p.warnings),
                "events": [
                    {
                        "source_event_id": e.source_event_id,
                        "track": e.track,
                        "step": e.step,
                        "note": e.note,
                        "velocity": e.velocity,
                        "length_code": f"0x{e.length_code:02X}",
                    }
                    for e in p.events
                ],
            }
            for p in plan.patterns
        ],
    }
