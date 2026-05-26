from __future__ import annotations

from fractions import Fraction

import pytest

from changes.digitone.planner import (
    choose_timing_plan,
    compile_timeline_to_digitone_plan,
    compute_digitone_device_tempo_for_speed_one_eighth,
)
from changes.exporters.digitone_events import digitone_compile_plan_to_events_yaml_payload
from changes.importers.compact_progression import compact_progression_to_song_model
from changes.models.digitone_target_profile import DigitoneTargetProfile, default_digitone_target_profile
from changes.models.render_profile import default_render_profile
from changes.models.rendered_timeline import RenderedNoteEvent, RenderedTimeline
from changes.rendering.timeline_renderer import render_timeline


def _song_payload(prog):
    return {
        "name": "test",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": prog}],
    }


def test_compact_progression_fraction_expansion_4_4_patterns():
    two = compact_progression_to_song_model(_song_payload([["Cmaj7", "Fmaj7"]]))
    assert two.measures[0].harmony[0].duration_quarters == Fraction(2, 1)
    assert two.measures[0].harmony[1].offset_quarters == Fraction(2, 1)

    three = compact_progression_to_song_model(_song_payload([["Cmaj7", "Dm7", "G7"]]))
    assert three.measures[0].harmony[0].duration_quarters == Fraction(4, 3)
    assert three.measures[0].harmony[2].offset_quarters == Fraction(8, 3)

    four = compact_progression_to_song_model(_song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]]))
    assert four.measures[0].harmony[0].duration_quarters == Fraction(1, 1)
    assert four.measures[0].harmony[3].offset_quarters == Fraction(3, 1)


def test_rendered_timeline_hold_merges_contiguous_same_pitch():
    payload = _song_payload([["Cmaj7", "Cmaj7"]])
    song = compact_progression_to_song_model(payload)
    timeline = render_timeline(song, default_render_profile())

    v1 = [e for e in timeline.events if e.voice_id == "chord_voice_1"]
    assert len(v1) == 1
    assert v1[0].duration_quarters == Fraction(4, 1)


def test_timing_plan_falls_back_from_invalid_tempo_bounds():
    target = DigitoneTargetProfile(
        name="fallback-test",
        device="digitone2",
        voice_to_track={"chord_voice_1": 1},
        default_velocity="inherit",
        length_strategy="hold_until_next_event",
        allow_inf=False,
        approximation="error",
        preferred_speed=Fraction(1, 8),
        fallback_speeds=(Fraction(1, 4), Fraction(1, 2)),
    )

    timeline = RenderedTimeline(
        title="x",
        performance_tempo=Fraction(240, 1),
        events=(
            RenderedNoteEvent(
                id="e1",
                voice_id="chord_voice_1",
                role="chord",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(1, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
        ),
    )

    # With speed 1/8 and q_step=1, device tempo would be out of range (480 BPM).
    assert compute_digitone_device_tempo_for_speed_one_eighth(timeline.performance_tempo, Fraction(1, 1)) == Fraction(480, 1)

    plan = choose_timing_plan(timeline, target)
    assert plan.speed_ratio == Fraction(1, 2)
    assert Fraction(30, 1) <= plan.device_tempo <= Fraction(300, 1)


def test_compile_plan_rejects_non_exact_length_code_mapping():
    timeline = RenderedTimeline(
        title="len-error",
        performance_tempo=Fraction(120, 1),
        events=(
            RenderedNoteEvent(
                id="e1",
                voice_id="chord_voice_1",
                role="chord",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(35, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
            RenderedNoteEvent(
                id="e2",
                voice_id="chord_voice_2",
                role="chord",
                note_midi=64,
                onset_quarters=Fraction(35, 1),
                duration_quarters=Fraction(1, 1),
                source_harmony_id="h2",
                retrigger=True,
            ),
        ),
    )

    with pytest.raises(ValueError, match="No exact length code"):
        compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())


def test_compile_plan_and_events_export_smoke():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    song = compact_progression_to_song_model(payload)
    timeline = render_timeline(song, default_render_profile())
    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())

    assert plan.total_steps <= 128
    assert len(plan.events) > 0

    out = digitone_compile_plan_to_events_yaml_payload(plan)
    assert out["version"] == 1
    assert out["device"] == "digitone2"
    assert out["pattern"]["speed"] == plan.speed
    assert out["events"]
    assert out["events"][0]["length_code"].startswith("0x")


def test_events_export_includes_unmodified_plan_title_as_name():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    payload["name"] = "Blue Moon A"
    song = compact_progression_to_song_model(payload)
    timeline = render_timeline(song, default_render_profile())
    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())

    out = digitone_compile_plan_to_events_yaml_payload(plan)
    assert out["name"] == plan.title
    assert out["name"] == "Blue Moon A"
