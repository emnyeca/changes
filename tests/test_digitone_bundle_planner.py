from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest
import json
import yaml

from changes.digitone.bundle_planner import (
    _RawSegment,
    _resolve_short_segments,
    compile_timeline_to_digitone_bundle_plan,
)
from changes.importers.compact_progression import compact_progression_to_song_model
from changes.models.digitone_target_profile import default_digitone_target_profile
from changes.models.render_profile import default_render_profile
from changes.pipeline_digitone import compile_digitone_bundle_pipeline, save_digitone_bundle_artifacts
from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
from changes.rendering.arrangement_renderer import render_arrangement


def test_bundle_single_pattern_uses_song_title_only():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7"]]}],
    }

    rp = replace(default_render_profile(), hold_repeated_same_pitch="retrigger")
    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, render_profile=rp, layers="bass")

    assert len(bundle.patterns) == 1
    assert bundle.patterns[0].pattern_name == "BLUE MOON"
    assert bundle.patterns[0].pattern_name_source == "auto"


def test_bundle_named_multi_pattern_uses_section_prefix_first_names():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"] for _ in range(16)]},
            {"name": "A", "progression": [["Dm7"] for _ in range(16)]},
            {"name": "Solo", "progression": [["G7"] for _ in range(16)]},
            {"name": "Outro", "progression": [["Cmaj7"] for _ in range(16)]},
        ],
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="cloud,bass")
    names = [p.pattern_name for p in bundle.patterns]

    assert names == ["INT BLUE MOON", "A BLUE MOON", "SOL BLUE MOON", "OUT BLUE MOON"]


def test_bundle_overflow_split_adds_section_part_numbers():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {
                "name": "Solo",
                "progression": [["Cmaj7"] for _ in range(130)],
            }
        ],
    }

    rp = replace(default_render_profile(), hold_repeated_same_pitch="retrigger")
    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, render_profile=rp, layers="bass")
    names = [p.pattern_name for p in bundle.patterns]

    assert len(names) == 2
    assert names[0] == "SOL1 BLUE MOON"
    assert names[1] == "SOL2 BLUE MOON"


def test_bundle_capacity_split_without_named_sections_uses_p_prefix():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {
                "name": "A",
                "progression": [["Cmaj7"] for _ in range(130)],
            }
        ],
    }

    song = compact_progression_to_song_model(payload)
    song_without_sections = replace(
        song,
        measures=tuple(replace(m, section_id=None) for m in song.measures),
    )
    rp = replace(default_render_profile(), hold_repeated_same_pitch="retrigger")
    timeline = flatten_arrangement_to_timeline(render_arrangement(song_without_sections, rp), layers="bass")
    bundle = compile_timeline_to_digitone_bundle_plan(
        song_without_sections,
        timeline,
        default_digitone_target_profile(),
    )

    names = [p.pattern_name for p in bundle.patterns]
    assert len(names) == 2
    assert names[0] == "P1 BLUE MOON"
    assert names[1] == "P2 BLUE MOON"


def test_bundle_long_title_truncation_keeps_prefix_and_length_16():
    payload = {
        "name": "SOFTLY AS IN A MORNING SUNRISE",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Solo", "progression": [["Cmaj7"] for _ in range(16)]},
            {"name": "Outro", "progression": [["Cmaj7"] for _ in range(16)]},
        ],
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="cloud,bass")

    for segment in bundle.patterns:
        assert len(segment.pattern_name) <= 16
    assert bundle.patterns[0].pattern_name.startswith("SOL ")
    assert any("truncated to 16" in w for w in bundle.patterns[0].warnings)


def test_bundle_explicit_override_disables_auto_prefix_and_uses_explicit_source():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"] for _ in range(16)]},
            {"name": "Solo", "progression": [["G7"] for _ in range(16)]},
        ],
        "digitone_pattern_name_overrides": {
            "1": "scene one",
        },
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="bass")

    assert [p.pattern_name for p in bundle.patterns] == ["SCENE ONE", "SOL BLUE MOON"]
    assert [p.pattern_name_source for p in bundle.patterns] == ["explicit", "auto"]


def test_bundle_explicit_override_truncates_and_manifest_records_warning(tmp_path: Path):
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7"]]}],
        "digitone_pattern_name_overrides": ["blue moon solo long"],
    }

    song, timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="bass")
    assert bundle.patterns[0].pattern_name == "BLUE MOON SOLO L"
    assert bundle.patterns[0].pattern_name_source == "explicit"
    assert any("truncated to 16" in w for w in bundle.patterns[0].warnings)

    out = save_digitone_bundle_artifacts(tmp_path, song, timeline, bundle, write_syx=False)
    manifest = json.loads(out["bundle_manifest_json"].read_text(encoding="utf-8"))
    warnings = manifest["patterns"][0]["warnings"]
    assert any("BLUE MOON SOLO LONG" in w and "BLUE MOON SOLO L" in w for w in warnings)


def test_bundle_explicit_override_rejects_unsupported_char_even_after_16th_position():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7"]]}],
        "digitone_pattern_name_overrides": ["BLUE MOON SOLO LO😺"],
    }

    with pytest.raises(ValueError, match="Unsupported character"):
        compile_digitone_bundle_pipeline(payload, layers="bass")


def test_repeated_non_contiguous_section_labels_are_separate_occurrences():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "A", "progression": [["Cmaj7"] for _ in range(16)]},
            {"name": "B", "progression": [["Dm7"] for _ in range(16)]},
            {"name": "A", "progression": [["G7"] for _ in range(16)]},
        ],
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="bass")

    assert [p.section_label for p in bundle.patterns] == ["A", "B", "A"]
    assert [p.section_global_order_index for p in bundle.patterns] == [1, 2, 3]
    assert [p.pattern_name for p in bundle.patterns] == ["A1 BLUE MOON", "B BLUE MOON", "A2 BLUE MOON"]


def test_aaba_form_preserves_order_and_unique_auto_names():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "A", "progression": [["Cmaj7"] for _ in range(16)]},
            {"name": "A", "progression": [["Dm7"] for _ in range(16)]},
            {"name": "B", "progression": [["G7"] for _ in range(16)]},
            {"name": "A", "progression": [["Cmaj7"] for _ in range(16)]},
        ],
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="bass")
    names = [p.pattern_name for p in bundle.patterns]

    assert names == ["A1 BLUE MOON", "A2 BLUE MOON", "B BLUE MOON", "A3 BLUE MOON"]
    assert len(set(names)) == len(names)


def test_repeated_section_occurrence_with_overflow_has_unique_deterministic_names():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "A", "progression": [["Cmaj7"] for _ in range(130)]},
            {"name": "B", "progression": [["Dm7"], ["Dm7"]]},
            {"name": "A", "progression": [["G7"], ["G7"]]},
        ],
    }

    rp = replace(default_render_profile(), hold_repeated_same_pitch="retrigger")
    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, render_profile=rp, layers="bass")
    names = [p.pattern_name for p in bundle.patterns]

    assert names[:2] == ["A1S1 BLUE MOON", "A1S2 BLUE MOON"]
    assert names[-1] == "A2 BLUE MOON"
    assert len(set(names)) == len(names)


def test_boundary_crossing_held_notes_are_retriggered_at_next_pattern_step_one():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "A", "progression": [["Cmaj7"] for _ in range(300)]},
        ],
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="cloud,bass")
    assert len(bundle.patterns) >= 2

    p2_steps = {(e.track, e.step) for e in bundle.patterns[1].events}
    assert (1, 1) in p2_steps
    assert (7, 1) in p2_steps


def test_section_boundary_crossing_held_notes_exist_in_each_standalone_pattern():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"] for _ in range(16)]},
            {"name": "A", "progression": [["Cmaj7"] for _ in range(16)]},
        ],
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload, layers="cloud,bass")
    assert len(bundle.patterns) == 2

    p1_steps = {(e.track, e.step) for e in bundle.patterns[0].events}
    p2_steps = {(e.track, e.step) for e in bundle.patterns[1].events}
    assert (1, 1) in p1_steps
    assert (1, 1) in p2_steps
    assert (7, 1) in p2_steps


def test_every_emitted_bundle_pattern_satisfies_total_steps_2_to_128():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"]]},
            {"name": "A", "progression": [["Dm7"]]},
            {"name": "Solo", "progression": [["G7"]]},
            {"name": "Outro", "progression": [["Cmaj7"]]},
        ],
    }

    _song, _timeline, bundle = compile_digitone_bundle_pipeline(payload)
    assert all(2 <= p.total_steps <= 128 for p in bundle.patterns)


def test_bundle_events_yaml_uses_per_track_mode_and_segment_scale(tmp_path: Path):
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "A", "progression": [["Cmaj7"] for _ in range(40)]},
        ],
    }

    song, timeline, bundle = compile_digitone_bundle_pipeline(payload)
    out = save_digitone_bundle_artifacts(tmp_path, song, timeline, bundle, write_syx=False)
    event_files = sorted(out["patterns_dir"].glob("*.digitone.events.yaml"))
    assert event_files

    for event_file, segment in zip(event_files, bundle.patterns, strict=True):
        payload = yaml.safe_load(event_file.read_text(encoding="utf-8"))
        assert payload["pattern"] == {
            "mode": "per-track",
            "tempo": float(bundle.timing.device_tempo),
            "change": "OFF",
            "reset": "INF",
        }
        assert sorted(payload["track_scale"]) == list(range(1, 17))
        assert all(payload["track_scale"][track]["length"] == segment.total_steps for track in range(1, 9))
        assert all(payload["track_scale"][track]["speed"] == bundle.timing.speed for track in range(1, 9))
        assert all(payload["track_scale"][track]["length"] == 16 for track in range(9, 17))
        assert all(payload["track_scale"][track]["speed"] == "1" for track in range(9, 17))


def test_short_section_resolution_is_deterministic_and_reported():
    payload = {
        "name": "BLUE MOON",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"]]},
            {"name": "A", "progression": [["Dm7"]]},
            {"name": "B", "progression": [["G7"]]},
            {"name": "Outro", "progression": [["Cmaj7"]]},
        ],
    }

    _song, _timeline, bundle1 = compile_digitone_bundle_pipeline(payload)
    _song, _timeline, bundle2 = compile_digitone_bundle_pipeline(payload)

    assert [p.global_step_start for p in bundle1.patterns] == [p.global_step_start for p in bundle2.patterns]
    assert any("short section merged due to Digitone minimum pattern length" in w for w in bundle1.warnings)


def test_short_segment_one_plus_128_borrows_from_next_deterministically():
    segments = [
        _RawSegment(
            section_id="A__OCC1",
            section_label="A",
            section_occurrence_index=1,
            section_global_order_index=1,
            section_split_index=1,
            section_split_count=1,
            global_step_start=1,
            global_step_end=1,
        ),
        _RawSegment(
            section_id="B__OCC1",
            section_label="B",
            section_occurrence_index=1,
            section_global_order_index=2,
            section_split_index=1,
            section_split_count=1,
            global_step_start=2,
            global_step_end=129,
        ),
    ]

    resolved, warnings = _resolve_short_segments(segments)

    assert [(s.global_step_start, s.global_step_end) for s in resolved] == [(1, 2), (3, 129)]
    assert any("boundary-adjusted by borrowing 1 step from next segment" in w for w in warnings)


def test_short_segment_128_plus_1_borrows_from_previous_deterministically():
    segments = [
        _RawSegment(
            section_id="A__OCC1",
            section_label="A",
            section_occurrence_index=1,
            section_global_order_index=1,
            section_split_index=1,
            section_split_count=1,
            global_step_start=1,
            global_step_end=128,
        ),
        _RawSegment(
            section_id="B__OCC1",
            section_label="B",
            section_occurrence_index=1,
            section_global_order_index=2,
            section_split_index=1,
            section_split_count=1,
            global_step_start=129,
            global_step_end=129,
        ),
    ]

    resolved, warnings = _resolve_short_segments(segments)

    assert [(s.global_step_start, s.global_step_end) for s in resolved] == [(1, 127), (128, 129)]
    assert any("boundary-adjusted by borrowing 1 step from previous segment" in w for w in warnings)


def test_short_segment_128_plus_1_plus_128_borrows_from_next_first():
    segments = [
        _RawSegment(
            section_id="A__OCC1",
            section_label="A",
            section_occurrence_index=1,
            section_global_order_index=1,
            section_split_index=1,
            section_split_count=1,
            global_step_start=1,
            global_step_end=128,
        ),
        _RawSegment(
            section_id="B__OCC1",
            section_label="B",
            section_occurrence_index=1,
            section_global_order_index=2,
            section_split_index=1,
            section_split_count=1,
            global_step_start=129,
            global_step_end=129,
        ),
        _RawSegment(
            section_id="C__OCC1",
            section_label="C",
            section_occurrence_index=1,
            section_global_order_index=3,
            section_split_index=1,
            section_split_count=1,
            global_step_start=130,
            global_step_end=257,
        ),
    ]

    resolved, warnings = _resolve_short_segments(segments)

    assert [(s.global_step_start, s.global_step_end) for s in resolved] == [(1, 128), (129, 130), (131, 257)]
    assert any("boundary-adjusted by borrowing 1 step from next segment" in w for w in warnings)
