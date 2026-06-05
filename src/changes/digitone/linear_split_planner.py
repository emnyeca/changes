"""Linear-mode section-boundary split planner for Digitone exports."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from changes.digitone.pattern_name_policy import fit_prefixed_auto_pattern_name
from changes.digitone.planner import (
    TimingPlan,
    choose_shared_timing_plan,
    compile_timeline_events_with_timing,
)
from changes.models.digitone_bundle_plan import (
    DigitonePatternBundlePlan,
    DigitonePatternSegment,
    DigitoneSongTimingPlan,
)
from changes.models.digitone_target_profile import DigitoneTargetProfile, speed_fraction_to_label
from changes.models.rendered_timeline import RenderedTimeline
from changes.models.song_model import SongModel

MAX_LINEAR_PATTERN_STEPS = 128


@dataclass(frozen=True)
class _LinearChunk:
    global_step_start: int
    global_step_end: int

    @property
    def total_steps(self) -> int:
        return self.global_step_end - self.global_step_start + 1


def _song_end_quarters(song: SongModel, fallback: Fraction) -> Fraction:
    end = max(
        (
            measure.absolute_start_quarters + harmony.offset_quarters + harmony.duration_quarters
            for measure in song.measures
            for harmony in measure.harmony
        ),
        default=Fraction(0, 1),
    )
    return end if end > 0 else fallback


def section_boundaries_in_quarters(song: SongModel, song_end: Fraction | None = None) -> list[Fraction]:
    """Return song, section-start, and song-end boundaries in quarter notes."""
    fallback_end = song_end if song_end is not None else Fraction(0, 1)
    end = _song_end_quarters(song, fallback_end)
    boundaries: list[Fraction] = [Fraction(0, 1)]

    current_section_id: str | None = None
    seen_any_measure = False
    for measure in sorted(song.measures, key=lambda m: (m.absolute_start_quarters, m.number)):
        section_id = measure.section_id
        if not seen_any_measure:
            current_section_id = section_id
            seen_any_measure = True
            continue
        if section_id != current_section_id:
            boundaries.append(measure.absolute_start_quarters)
            current_section_id = section_id

    boundaries.append(end)
    return sorted(set(boundaries))


def _has_named_section_structure(song: SongModel) -> bool:
    return any((measure.section_id or "").strip() for measure in song.measures)


def _boundary_steps(boundaries: list[Fraction], timing: TimingPlan) -> list[int]:
    out: list[int] = []
    for boundary in boundaries:
        ratio = boundary / timing.q_step
        if ratio.denominator != 1:
            raise ValueError(f"Section boundary is not aligned to shared timing grid: {boundary}")
        out.append(int(ratio))
    return sorted(set(out))


def _linear_chunks_from_section_boundaries(
    song: SongModel,
    timing: TimingPlan,
) -> list[_LinearChunk]:
    total_steps = timing.total_steps
    if total_steps <= MAX_LINEAR_PATTERN_STEPS:
        return [_LinearChunk(global_step_start=1, global_step_end=total_steps)]

    if not _has_named_section_structure(song):
        raise ValueError("Linear Auto Split requires section boundaries for songs longer than 128 steps.")

    boundaries = section_boundaries_in_quarters(song, Fraction(total_steps, 1) * timing.q_step)
    steps = _boundary_steps(boundaries, timing)
    steps = sorted({step for step in steps if 0 <= step <= total_steps} | {0, total_steps})

    internal_boundaries = [step for step in steps if 0 < step < total_steps]
    if not internal_boundaries:
        raise ValueError("Section is too long for Linear Auto Split: section length exceeds 128 steps.")

    for start, end in zip(steps, steps[1:], strict=False):
        if end - start > MAX_LINEAR_PATTERN_STEPS:
            raise ValueError("Section is too long for Linear Auto Split: section length exceeds 128 steps.")

    chunks: list[_LinearChunk] = []
    chunk_start = 0
    while chunk_start < total_steps:
        candidates = [
            boundary
            for boundary in steps
            if chunk_start < boundary <= chunk_start + MAX_LINEAR_PATTERN_STEPS
        ]
        if not candidates:
            raise ValueError("No valid section boundary split found within 128 steps.")
        chunk_end = max(candidates)
        if chunk_end <= chunk_start:
            raise ValueError("No valid section boundary split found within 128 steps.")
        chunks.append(_LinearChunk(global_step_start=chunk_start + 1, global_step_end=chunk_end))
        chunk_start = chunk_end

    return chunks


def _linear_pattern_name(index: int, source_title: str, multi: bool) -> tuple[str, tuple[str, ...]]:
    prefix = f"{index:02d} " if multi else ""
    name, warning = fit_prefixed_auto_pattern_name(prefix, source_title)
    return name, ((warning,) if warning is not None else tuple())


def compile_timeline_to_digitone_linear_split_plan(
    song: SongModel,
    timeline: RenderedTimeline,
    target: DigitoneTargetProfile,
) -> DigitonePatternBundlePlan:
    timing = choose_shared_timing_plan(timeline, target)
    chunks = _linear_chunks_from_section_boundaries(song, timing)
    multi = len(chunks) > 1

    patterns: list[DigitonePatternSegment] = []
    for i, chunk in enumerate(chunks, start=1):
        if not (2 <= chunk.total_steps <= MAX_LINEAR_PATTERN_STEPS):
            raise ValueError(
                f"Invalid Linear Auto Split pattern length: {chunk.total_steps} steps "
                "(expected 2..128)."
            )

        pattern_name, warnings = _linear_pattern_name(i, song.title, multi)
        events = compile_timeline_events_with_timing(
            timeline,
            target,
            timing,
            step_start=chunk.global_step_start,
            step_end=chunk.global_step_end,
            include_boundary_carryover=True,
        )

        patterns.append(
            DigitonePatternSegment(
                source_title=song.title,
                pattern_name=pattern_name,
                pattern_name_source="auto",
                section_id=None,
                section_label=None,
                section_token=None,
                section_occurrence_index=None,
                section_global_order_index=None,
                segment_index=i,
                section_split_index=1,
                section_split_count=1,
                global_step_start=chunk.global_step_start,
                global_step_end=chunk.global_step_end,
                total_steps=chunk.total_steps,
                events=events,
                warnings=warnings,
            )
        )

    timing_plan = DigitoneSongTimingPlan(
        performance_tempo=timeline.performance_tempo,
        speed=speed_fraction_to_label(timing.speed_ratio),
        speed_ratio=timing.speed_ratio,
        q_step=timing.q_step,
        device_tempo=timing.device_tempo,
    )

    return DigitonePatternBundlePlan(
        source_title=song.title,
        timing=timing_plan,
        patterns=tuple(patterns),
        warnings=tuple(),
    )
