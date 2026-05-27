"""Bundle-oriented split planning and auto pattern naming for Digitone exports."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

from changes.digitone.pattern_name_policy import (
    ascii_upper_only,
    fit_prefixed_auto_pattern_name,
    normalize_validate_and_truncate_pattern_name,
)
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

MAX_PATTERN_STEPS = 128
MAX_PATTERN_NAME_CHARS = 16

DEFAULT_SECTION_TOKENS = {
    "intro": "INT",
    "theme": "THM",
    "head": "HD",
    "verse": "VRS",
    "a": "A",
    "b": "B",
    "c": "C",
    "bridge": "BRG",
    "solo": "SOL",
    "interlude": "ITL",
    "ending": "END",
    "outro": "OUT",
}

@dataclass(frozen=True)
class SectionOccurrence:
    section_id: str | None
    section_label: str | None
    occurrence_index_for_label: int
    global_order_index: int
    start_quarters: Fraction
    end_quarters: Fraction


@dataclass(frozen=True)
class _RawSegment:
    section_id: str | None
    section_label: str | None
    section_occurrence_index: int
    section_global_order_index: int
    section_split_index: int
    section_split_count: int
    global_step_start: int
    global_step_end: int


def _resolve_section_token(section_label: str | None) -> str | None:
    if section_label is None:
        return None
    norm = ascii_upper_only(section_label.strip())
    if not norm:
        return None
    mapped = DEFAULT_SECTION_TOKENS.get(norm.lower())
    if mapped is not None:
        return mapped
    return norm[:3]


def _decode_section_identity(raw_section_id: str | None) -> tuple[str | None, str | None]:
    if raw_section_id is None:
        return None, None
    text = str(raw_section_id)
    marker = "__OCC"
    if marker in text:
        label, _, _suffix = text.partition(marker)
        label = label or text
        return text, label
    return text, text


def _harmony_section_occurrences(song: SongModel) -> tuple[list[SectionOccurrence], bool]:
    timeline_items: list[tuple[str | None, str | None, Fraction, Fraction]] = []
    for measure in song.measures:
        section_id, section_label = _decode_section_identity(measure.section_id)
        for h in measure.harmony:
            onset = measure.absolute_start_quarters + h.offset_quarters
            end = onset + h.duration_quarters
            timeline_items.append((section_id, section_label, onset, end))

    if not timeline_items:
        return [], False

    occurrences: list[SectionOccurrence] = []
    per_label_count: dict[str | None, int] = {}

    current_id, current_label, current_start, current_end = timeline_items[0]
    for section_id, section_label, onset, end in timeline_items[1:]:
        if section_id == current_id:
            if end > current_end:
                current_end = end
            continue

        per_label_count[current_label] = per_label_count.get(current_label, 0) + 1
        occurrences.append(
            SectionOccurrence(
                section_id=current_id,
                section_label=current_label,
                occurrence_index_for_label=per_label_count[current_label],
                global_order_index=len(occurrences) + 1,
                start_quarters=current_start,
                end_quarters=current_end,
            )
        )
        current_id, current_label, current_start, current_end = section_id, section_label, onset, end

    per_label_count[current_label] = per_label_count.get(current_label, 0) + 1
    occurrences.append(
        SectionOccurrence(
            section_id=current_id,
            section_label=current_label,
            occurrence_index_for_label=per_label_count[current_label],
            global_order_index=len(occurrences) + 1,
            start_quarters=current_start,
            end_quarters=current_end,
        )
    )

    has_named_sections = any((occ.section_label is not None and occ.section_label.strip()) for occ in occurrences)
    return occurrences, has_named_sections


def _fraction_to_global_step_start(value: Fraction, q_step: Fraction) -> int:
    ratio = value / q_step
    if ratio.denominator != 1:
        raise ValueError(f"Section boundary is not aligned to shared timing grid: {value}")
    return int(ratio) + 1


def _fraction_to_global_step_end(value: Fraction, q_step: Fraction) -> int:
    ratio = value / q_step
    if ratio.denominator != 1:
        raise ValueError(f"Section boundary is not aligned to shared timing grid: {value}")
    return int(ratio)


def _split_occurrences_into_segments(
    occurrences: list[SectionOccurrence],
    timing: TimingPlan,
) -> list[_RawSegment]:
    segments: list[_RawSegment] = []
    for occ in occurrences:
        start_step = _fraction_to_global_step_start(occ.start_quarters, timing.q_step)
        end_step = _fraction_to_global_step_end(occ.end_quarters, timing.q_step)
        if end_step < start_step:
            continue

        span = end_step - start_step + 1
        split_count = (span + MAX_PATTERN_STEPS - 1) // MAX_PATTERN_STEPS
        for split_idx in range(split_count):
            g0 = start_step + split_idx * MAX_PATTERN_STEPS
            g1 = min(end_step, g0 + MAX_PATTERN_STEPS - 1)
            segments.append(
                _RawSegment(
                    section_id=occ.section_id,
                    section_label=occ.section_label,
                    section_occurrence_index=occ.occurrence_index_for_label,
                    section_global_order_index=occ.global_order_index,
                    section_split_index=split_idx + 1,
                    section_split_count=split_count,
                    global_step_start=g0,
                    global_step_end=g1,
                )
            )
    return segments


def _segment_span(seg: _RawSegment) -> int:
    return seg.global_step_end - seg.global_step_start + 1


def _resolve_short_segments(segments: list[_RawSegment]) -> tuple[list[_RawSegment], list[str]]:
    resolved = list(segments)
    warnings: list[str] = []

    while True:
        short_index = next((i for i, seg in enumerate(resolved) if _segment_span(seg) < 2), None)
        if short_index is None:
            break
        if len(resolved) == 1:
            raise ValueError("Cannot resolve short bundle segment: total_steps < 2")

        seg = resolved[short_index]
        merged = False

        if short_index + 1 < len(resolved):
            nxt = resolved[short_index + 1]
            if seg.global_step_end + 1 == nxt.global_step_start and _segment_span(nxt) > 2:
                resolved[short_index] = replace(seg, global_step_end=seg.global_step_end + 1)
                resolved[short_index + 1] = replace(nxt, global_step_start=nxt.global_step_start + 1)
                warnings.append(
                    "short section boundary-adjusted by borrowing 1 step from next segment: "
                    f'section="{seg.section_label}" occurrence={seg.section_occurrence_index}'
                )
                continue

        if short_index > 0:
            prev = resolved[short_index - 1]
            if prev.global_step_end + 1 == seg.global_step_start and _segment_span(prev) > 2:
                resolved[short_index - 1] = replace(prev, global_step_end=prev.global_step_end - 1)
                resolved[short_index] = replace(seg, global_step_start=seg.global_step_start - 1)
                warnings.append(
                    "short section boundary-adjusted by borrowing 1 step from previous segment: "
                    f'section="{seg.section_label}" occurrence={seg.section_occurrence_index}'
                )
                continue

        if short_index + 1 < len(resolved):
            nxt = resolved[short_index + 1]
            if seg.global_step_end + 1 == nxt.global_step_start:
                if _segment_span(seg) + _segment_span(nxt) > MAX_PATTERN_STEPS:
                    raise ValueError(
                        "Cannot resolve short bundle segment without exceeding 128 steps: "
                        f"segment_index={short_index + 1}"
                    )
                resolved[short_index + 1] = replace(nxt, global_step_start=seg.global_step_start)
                warnings.append(
                    "short section merged due to Digitone minimum pattern length: "
                    f'section="{seg.section_label}" occurrence={seg.section_occurrence_index}'
                )
                del resolved[short_index]
                merged = True

        if merged:
            continue

        if short_index > 0:
            prev = resolved[short_index - 1]
            if prev.global_step_end + 1 == seg.global_step_start:
                if _segment_span(prev) + _segment_span(seg) > MAX_PATTERN_STEPS:
                    raise ValueError(
                        "Cannot resolve short bundle segment without exceeding 128 steps: "
                        f"segment_index={short_index + 1}"
                    )
                resolved[short_index - 1] = replace(prev, global_step_end=seg.global_step_end)
                warnings.append(
                    "short section merged due to Digitone minimum pattern length: "
                    f'section="{seg.section_label}" occurrence={seg.section_occurrence_index}'
                )
                del resolved[short_index]
                continue

        raise ValueError(
            "Cannot resolve short bundle segment deterministically: "
            f"segment_index={short_index + 1} total_steps={_segment_span(seg)}"
        )

    return resolved, warnings


def _build_auto_prefix(
    *,
    segment_index: int,
    seg: _RawSegment,
    has_named_sections: bool,
    label_occurrence_totals: dict[str, int],
) -> str:
    if not has_named_sections:
        return f"P{segment_index} "

    section_token = _resolve_section_token(seg.section_label)
    if not section_token:
        return f"P{segment_index} "

    label_key = ascii_upper_only((seg.section_label or "").strip())
    repeated = bool(label_key and label_occurrence_totals.get(label_key, 0) > 1)
    occurrence_suffix = str(seg.section_occurrence_index) if repeated else ""

    if seg.section_split_count > 1 and repeated:
        token = f"{section_token}{occurrence_suffix}S{seg.section_split_index}"
    elif seg.section_split_count > 1:
        token = f"{section_token}{seg.section_split_index}"
    else:
        token = f"{section_token}{occurrence_suffix}"

    return f"{token} "


def compile_timeline_to_digitone_bundle_plan(
    song: SongModel,
    timeline: RenderedTimeline,
    target: DigitoneTargetProfile,
    explicit_pattern_name_overrides: dict[int, str] | None = None,
) -> DigitonePatternBundlePlan:
    timing = choose_shared_timing_plan(timeline, target)

    occurrences, has_named_sections = _harmony_section_occurrences(song)
    if not occurrences:
        occurrences = [
            SectionOccurrence(
                section_id=None,
                section_label=None,
                occurrence_index_for_label=1,
                global_order_index=1,
                start_quarters=Fraction(0, 1),
                end_quarters=timing.total_steps * timing.q_step,
            )
        ]
        has_named_sections = False

    raw_segments = _split_occurrences_into_segments(occurrences, timing)
    if not raw_segments:
        raise ValueError("Bundle planning produced no segments")

    raw_segments, short_merge_warnings = _resolve_short_segments(raw_segments)

    song_title = song.title
    multi = len(raw_segments) > 1

    patterns: list[DigitonePatternSegment] = []
    bundle_warnings: list[str] = list(short_merge_warnings)

    overrides = explicit_pattern_name_overrides or {}
    label_occurrence_totals: dict[str, int] = {}
    for occ in occurrences:
        key = ascii_upper_only((occ.section_label or "").strip())
        if key:
            label_occurrence_totals[key] = label_occurrence_totals.get(key, 0) + 1

    for i, seg in enumerate(raw_segments, start=1):
        total_steps = _segment_span(seg)
        if not (2 <= total_steps <= 128):
            raise ValueError(
                f"Invalid pattern total_steps={total_steps} at segment_index={i}. "
                "Bundle planning must resolve each segment to 2..128 before encoding."
            )

        events = compile_timeline_events_with_timing(
            timeline,
            target,
            timing,
            step_start=seg.global_step_start,
            step_end=seg.global_step_end,
            include_boundary_carryover=True,
        )

        section_token = _resolve_section_token(seg.section_label)
        warnings: list[str] = []

        explicit_name = overrides.get(i)
        if explicit_name is not None:
            pattern_name, truncate_warning = normalize_validate_and_truncate_pattern_name(
                explicit_name,
                context=f"explicit Pattern Name override for segment {i}",
            )
            pattern_name_source = "explicit"
            if truncate_warning is not None:
                warnings.append(truncate_warning)
        else:
            prefix = "" if not multi else _build_auto_prefix(
                segment_index=i,
                seg=seg,
                has_named_sections=has_named_sections,
                label_occurrence_totals=label_occurrence_totals,
            )

            pattern_name, truncate_warning = fit_prefixed_auto_pattern_name(prefix, song_title)
            pattern_name_source = "auto"
            if truncate_warning is not None:
                warnings.append(truncate_warning)

        patterns.append(
            DigitonePatternSegment(
                source_title=song.title,
                pattern_name=pattern_name,
                pattern_name_source=pattern_name_source,
                section_id=seg.section_id,
                section_label=seg.section_label,
                section_token=section_token,
                section_occurrence_index=seg.section_occurrence_index,
                section_global_order_index=seg.section_global_order_index,
                segment_index=i,
                section_split_index=seg.section_split_index,
                section_split_count=seg.section_split_count,
                global_step_start=seg.global_step_start,
                global_step_end=seg.global_step_end,
                total_steps=total_steps,
                events=events,
                warnings=tuple(warnings),
            )
        )

    seen_names: set[str] = set()
    for p in patterns:
        if p.pattern_name in seen_names:
            bundle_warnings.append(f'Duplicate pattern_name detected in bundle: "{p.pattern_name}"')
        seen_names.add(p.pattern_name)

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
        warnings=tuple(bundle_warnings),
    )
