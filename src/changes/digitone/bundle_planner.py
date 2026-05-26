"""Bundle-oriented split planning and auto pattern naming for Digitone exports."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

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

ALLOWED_PATTERN_NAME_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "\u00c5\u00c4\u00d6\u00dc\u00df\u00c6\u00d8\u00c7\u00d1"
    "0123456789~!@#$%^&()_+-= "
)


@dataclass(frozen=True)
class _RawSegment:
    section_id: str | None
    section_label: str | None
    section_split_index: int
    section_split_count: int
    global_step_start: int
    global_step_end: int


def _ascii_upper_only(text: str) -> str:
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if 0x61 <= code <= 0x7A:
            out.append(chr(code - 0x20))
        else:
            out.append(ch)
    return "".join(out)


def _resolve_section_token(section_label: str | None) -> str | None:
    if section_label is None:
        return None
    norm = _ascii_upper_only(section_label.strip())
    if not norm:
        return None
    mapped = DEFAULT_SECTION_TOKENS.get(norm.lower())
    if mapped is not None:
        return mapped
    return norm[:3]


def _fit_pattern_name(prefix: str, title: str) -> tuple[str, str | None]:
    if not prefix:
        if len(title) <= MAX_PATTERN_NAME_CHARS:
            return title, None
        fitted = title[:MAX_PATTERN_NAME_CHARS]
        return fitted, f'Pattern name truncated to 16 characters: "{title}" -> "{fitted}"'

    if len(prefix) >= MAX_PATTERN_NAME_CHARS:
        fitted = prefix[:MAX_PATTERN_NAME_CHARS]
        return fitted, f'Pattern name truncated to 16 characters: "{prefix}{title}" -> "{fitted}"'

    room = MAX_PATTERN_NAME_CHARS - len(prefix)
    if len(title) <= room:
        return prefix + title, None

    fitted = prefix + title[:room]
    return fitted, f'Pattern name truncated to 16 characters: "{prefix}{title}" -> "{fitted}"'


def _normalize_validate_and_truncate_explicit_pattern_name(name: str) -> tuple[str, str | None]:
    if not isinstance(name, str):
        raise ValueError("Explicit pattern name must be a string")

    normalized = _ascii_upper_only(name)
    for ch in normalized:
        if ch not in ALLOWED_PATTERN_NAME_CHARS:
            raise ValueError(f"Unsupported pattern name character: {ch!r} in {normalized!r}")

    if len(normalized) <= MAX_PATTERN_NAME_CHARS:
        return normalized, None

    fitted = normalized[:MAX_PATTERN_NAME_CHARS]
    return fitted, f'Pattern name truncated to 16 characters: "{normalized}" -> "{fitted}"'


def _harmony_section_ranges(song: SongModel) -> tuple[list[tuple[str | None, str | None, Fraction, Fraction]], bool]:
    ranges: dict[str | None, tuple[Fraction, Fraction]] = {}
    order: list[str | None] = []

    for measure in song.measures:
        section_id = measure.section_id
        if section_id not in order:
            order.append(section_id)

        for h in measure.harmony:
            onset = measure.absolute_start_quarters + h.offset_quarters
            end = onset + h.duration_quarters
            if section_id not in ranges:
                ranges[section_id] = (onset, end)
            else:
                cur_start, cur_end = ranges[section_id]
                ranges[section_id] = (min(cur_start, onset), max(cur_end, end))

    has_named_sections = any((sid is not None and str(sid).strip()) for sid in order)
    out: list[tuple[str | None, str | None, Fraction, Fraction]] = []
    for sid in order:
        if sid not in ranges:
            continue
        s, e = ranges[sid]
        label = None if sid is None else str(sid)
        out.append((sid, label, s, e))
    return out, has_named_sections


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


def _split_ranges_into_segments(
    section_ranges: list[tuple[str | None, str | None, Fraction, Fraction]],
    timing: TimingPlan,
) -> list[_RawSegment]:
    segments: list[_RawSegment] = []
    for section_id, section_label, start_q, end_q in section_ranges:
        start_step = _fraction_to_global_step_start(start_q, timing.q_step)
        end_step = _fraction_to_global_step_end(end_q, timing.q_step)
        if end_step < start_step:
            continue

        span = end_step - start_step + 1
        split_count = (span + MAX_PATTERN_STEPS - 1) // MAX_PATTERN_STEPS
        for split_idx in range(split_count):
            g0 = start_step + split_idx * MAX_PATTERN_STEPS
            g1 = min(end_step, g0 + MAX_PATTERN_STEPS - 1)
            segments.append(
                _RawSegment(
                    section_id=section_id,
                    section_label=section_label,
                    section_split_index=split_idx + 1,
                    section_split_count=split_count,
                    global_step_start=g0,
                    global_step_end=g1,
                )
            )
    return segments


def compile_timeline_to_digitone_bundle_plan(
    song: SongModel,
    timeline: RenderedTimeline,
    target: DigitoneTargetProfile,
    explicit_pattern_name_overrides: dict[int, str] | None = None,
) -> DigitonePatternBundlePlan:
    timing = choose_shared_timing_plan(timeline, target)

    section_ranges, has_named_sections = _harmony_section_ranges(song)
    if not section_ranges:
        section_ranges = [(None, None, Fraction(0, 1), timing.total_steps * timing.q_step)]
        has_named_sections = False

    raw_segments = _split_ranges_into_segments(section_ranges, timing)
    if not raw_segments:
        raise ValueError("Bundle planning produced no segments")

    song_title = _ascii_upper_only(song.title)
    multi = len(raw_segments) > 1

    patterns: list[DigitonePatternSegment] = []
    bundle_warnings: list[str] = []

    overrides = explicit_pattern_name_overrides or {}

    for i, seg in enumerate(raw_segments, start=1):
        events = compile_timeline_events_with_timing(
            timeline,
            target,
            timing,
            step_start=seg.global_step_start,
            step_end=seg.global_step_end,
        )
        total_steps = seg.global_step_end - seg.global_step_start + 1

        section_token = _resolve_section_token(seg.section_label)
        warnings: list[str] = []

        explicit_name = overrides.get(i)
        if explicit_name is not None:
            pattern_name, truncate_warning = _normalize_validate_and_truncate_explicit_pattern_name(explicit_name)
            pattern_name_source = "explicit"
            if truncate_warning is not None:
                warnings.append(truncate_warning)
        else:
            if not multi:
                prefix = ""
            elif has_named_sections and section_token:
                suffix = str(seg.section_split_index) if seg.section_split_count > 1 else ""
                prefix = f"{section_token}{suffix} "
            else:
                prefix = f"P{i} "

            pattern_name, truncate_warning = _fit_pattern_name(prefix, song_title)
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
                segment_index=i,
                section_split_index=seg.section_split_index,
                section_split_count=seg.section_split_count,
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
