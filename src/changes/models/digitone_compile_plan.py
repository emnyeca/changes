"""Digitone compile plan dataclasses and serializers."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


def _fraction_to_text(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


@dataclass(frozen=True)
class CompiledDigitoneEvent:
    source_event_id: str
    track: int
    step: int
    note: str
    velocity: int | str
    length_code: int


@dataclass(frozen=True)
class DigitoneCompilePlan:
    source_title: str
    pattern_name: str
    pattern_name_source: str
    performance_tempo: Fraction
    speed: str
    speed_ratio: Fraction
    q_step: Fraction
    device_tempo: Fraction
    total_steps: int
    events: tuple[CompiledDigitoneEvent, ...]
    warnings: tuple[str, ...]

    @property
    def title(self) -> str:
        """Backward-compatible alias for legacy callers."""
        return self.source_title


def digitone_compile_plan_to_dict(plan: DigitoneCompilePlan) -> dict:
    return {
        "source_title": plan.source_title,
        "pattern_name": plan.pattern_name,
        "pattern_name_source": plan.pattern_name_source,
        # Keep legacy key for compatibility with older fixtures/tools.
        "title": plan.title,
        "performance_tempo": _fraction_to_text(plan.performance_tempo),
        "speed": plan.speed,
        "speed_ratio": _fraction_to_text(plan.speed_ratio),
        "q_step": _fraction_to_text(plan.q_step),
        "device_tempo": _fraction_to_text(plan.device_tempo),
        "total_steps": plan.total_steps,
        "warnings": list(plan.warnings),
        "events": [
            {
                "source_event_id": e.source_event_id,
                "track": e.track,
                "step": e.step,
                "note": e.note,
                "velocity": e.velocity,
                "length_code": f"0x{e.length_code:02X}",
            }
            for e in plan.events
        ],
    }
