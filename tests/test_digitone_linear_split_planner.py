from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from changes.digitone.linear_split_planner import (
    compile_timeline_to_digitone_linear_split_plan,
)
from changes.digitone.planner import _explicit_length_code_to_sixteenth_units_fallback
from changes.exporters.digitone_events import digitone_pattern_segment_to_events_yaml_payload
from changes.models.digitone_target_profile import default_digitone_target_profile
from changes.models.rendered_timeline import RenderedNoteEvent, RenderedTimeline
from changes.models.song_model import HarmonyEvent, Measure, SongModel


def _song_with_section_lengths(
    title: str,
    lengths: list[int],
    *,
    named_sections: bool = True,
) -> SongModel:
    measures: list[Measure] = []
    step = 0
    for section_index, length in enumerate(lengths):
        section_id = chr(ord("A") + section_index) if named_sections else None
        for _ in range(length):
            measures.append(
                Measure(
                    number=len(measures) + 1,
                    section_id=section_id,
                    meter_numerator=1,
                    meter_denominator=4,
                    absolute_start_quarters=Fraction(step, 1),
                    harmony=(
                        HarmonyEvent(
                            id=f"h{step}",
                            symbol="Cmaj7",
                            measure_number=len(measures) + 1,
                            offset_quarters=Fraction(0, 1),
                            duration_quarters=Fraction(1, 1),
                        ),
                    ),
                )
            )
            step += 1
    return SongModel(title=title, working_key="C", performance_tempo=120, measures=tuple(measures))


def _grid_timeline(title: str, steps: int) -> RenderedTimeline:
    events = tuple(
        RenderedNoteEvent(
            id=f"e{step}",
            voice_id="cloud_voice_1",
            role="cloud",
            note_midi=60,
            onset_quarters=Fraction(step, 1),
            duration_quarters=Fraction(1, 1),
            source_harmony_id=f"h{step}",
            retrigger=True,
            velocity=80,
        )
        for step in range(steps)
    )
    return RenderedTimeline(title=title, performance_tempo=Fraction(120, 1), events=events)


def _duration_steps(length_code: int, speed_ratio: Fraction) -> int:
    steps = _explicit_length_code_to_sixteenth_units_fallback(length_code) * speed_ratio
    assert steps.denominator == 1
    return int(steps)


def test_linear_split_uses_latest_section_boundary_within_128_steps() -> None:
    song = _song_with_section_lengths("Song", [40, 40, 40, 40])
    plan = compile_timeline_to_digitone_linear_split_plan(
        song,
        _grid_timeline(song.title, 160),
        default_digitone_target_profile(),
    )

    assert [p.total_steps for p in plan.patterns] == [120, 40]
    assert [p.pattern_name for p in plan.patterns] == ["01 SONG", "02 SONG"]


def test_linear_split_keeps_exact_128_step_section_group() -> None:
    song = _song_with_section_lengths("Song", [64, 64, 32])
    plan = compile_timeline_to_digitone_linear_split_plan(
        song,
        _grid_timeline(song.title, 160),
        default_digitone_target_profile(),
    )

    assert [p.total_steps for p in plan.patterns] == [128, 32]


def test_linear_split_groups_multiple_sections_when_they_fit() -> None:
    song = _song_with_section_lengths("Song", [32, 32, 32, 32, 32])
    plan = compile_timeline_to_digitone_linear_split_plan(
        song,
        _grid_timeline(song.title, 160),
        default_digitone_target_profile(),
    )

    assert [p.total_steps for p in plan.patterns] == [128, 32]


def test_linear_split_rejects_long_song_without_section_boundaries() -> None:
    song = _song_with_section_lengths("Song", [160], named_sections=False)

    with pytest.raises(ValueError, match="requires section boundaries"):
        compile_timeline_to_digitone_linear_split_plan(
            song,
            _grid_timeline(song.title, 160),
            default_digitone_target_profile(),
        )


def test_linear_split_rejects_section_longer_than_128_steps() -> None:
    song = _song_with_section_lengths("Song", [160])

    with pytest.raises(ValueError, match="section length exceeds 128 steps"):
        compile_timeline_to_digitone_linear_split_plan(
            song,
            _grid_timeline(song.title, 160),
            default_digitone_target_profile(),
        )


def test_linear_split_divides_event_that_crosses_pattern_boundary() -> None:
    song = _song_with_section_lengths("Song", [120, 40])
    timeline = replace(
        _grid_timeline(song.title, 160),
        events=(
            RenderedNoteEvent(
                id="held",
                voice_id="cloud_voice_1",
                role="cloud",
                note_midi=60,
                onset_quarters=Fraction(118, 1),
                duration_quarters=Fraction(6, 1),
                source_harmony_id="held",
                retrigger=True,
                velocity=80,
            ),
            *_grid_timeline(song.title, 160).events,
        ),
    )

    plan = compile_timeline_to_digitone_linear_split_plan(
        song,
        timeline,
        default_digitone_target_profile(),
    )

    first = [e for e in plan.patterns[0].events if e.source_event_id == "held"]
    second = [e for e in plan.patterns[1].events if e.source_event_id == "held"]
    assert [(e.step, _duration_steps(e.length_code, plan.timing.speed_ratio)) for e in first] == [(119, 2)]
    assert [(e.step, _duration_steps(e.length_code, plan.timing.speed_ratio)) for e in second] == [(1, 4)]


def test_linear_split_pattern_change_and_track_scale_use_chunk_length() -> None:
    song = _song_with_section_lengths("Song", [120, 40])
    plan = compile_timeline_to_digitone_linear_split_plan(
        song,
        _grid_timeline(song.title, 160),
        default_digitone_target_profile(),
    )

    payloads = [
        digitone_pattern_segment_to_events_yaml_payload(pattern, plan.timing)
        for pattern in plan.patterns
    ]

    assert [payload["pattern"]["change"] for payload in payloads] == [960, 320]
    assert [payload["pattern"]["reset"] for payload in payloads] == ["INF", "INF"]
    assert payloads[0]["track_scale"][1] == {"length": 120, "speed": "1/8"}
    assert payloads[0]["track_scale"][9] == {"length": 16, "speed": "1"}


def test_linear_split_pattern_change_off_policy() -> None:
    song = _song_with_section_lengths("Song", [120, 40])
    plan = compile_timeline_to_digitone_linear_split_plan(
        song,
        _grid_timeline(song.title, 160),
        default_digitone_target_profile(),
    )

    payload = digitone_pattern_segment_to_events_yaml_payload(
        plan.patterns[0],
        plan.timing,
        pattern_change_policy="off",
    )

    assert payload["pattern"]["change"] == "OFF"
