from __future__ import annotations

from fractions import Fraction
from dataclasses import replace

import pytest

from changes.digitone.planner import (
    choose_shared_timing_plan,
    choose_timing_plan,
    compile_timeline_to_digitone_plan,
    compute_digitone_device_tempo_for_speed_one_eighth,
)
from changes.exporters.digitone_events import digitone_compile_plan_to_events_yaml_payload
from changes.importers.compact_progression import compact_progression_to_song_model
from changes.models.digitone_target_profile import DigitoneTargetProfile, default_digitone_target_profile
from changes.models.render_profile import default_render_profile
from changes.models.rendered_timeline import RenderedNoteEvent, RenderedTimeline
from changes.pipeline_digitone import compile_digitone_pipeline
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


def test_rendered_timeline_emits_six_chord_voices_plus_bass_per_event_without_hold_merge():
    payload = {
        "name": "Blue Moon Head",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7", "Am7", "Dm7", "G7"]]}],
    }
    song = compact_progression_to_song_model(payload)
    rp = replace(default_render_profile(), hold_repeated_same_pitch="retrigger")
    timeline = render_timeline(song, rp)

    assert len(timeline.events) == 4 * 7

    chord_voices = {e.voice_id for e in timeline.events if e.role == "chord"}
    assert chord_voices == {
        "chord_voice_1",
        "chord_voice_2",
        "chord_voice_3",
        "chord_voice_4",
        "chord_voice_5",
        "chord_voice_6",
    }
    assert any(e.role == "bass" and e.voice_id == "bass" for e in timeline.events)


def test_rendered_timeline_am7_contains_f_not_f_sharp_in_c_major_context():
    payload = {
        "name": "Blue Moon Head",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7", "Am7", "Dm7", "G7"]]}],
    }
    song = compact_progression_to_song_model(payload)
    timeline = render_timeline(song, default_render_profile())

    am7_events = [e for e in timeline.events if e.source_harmony_id == "m1_h2" and e.role == "chord"]
    pcs = {e.note_midi % 12 for e in am7_events}

    assert 5 in pcs  # F
    assert 6 not in pcs  # F#


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


def test_compile_plan_splits_long_durations_into_exact_length_code_chunks():
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

    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())
    assert len(plan.events) >= 2


def test_choose_shared_timing_plan_allows_total_steps_over_128_for_song_level_planning():
    timeline = RenderedTimeline(
        title="long-song",
        performance_tempo=Fraction(120, 1),
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
            RenderedNoteEvent(
                id="e2",
                voice_id="chord_voice_1",
                role="chord",
                note_midi=60,
                onset_quarters=Fraction(300, 1),
                duration_quarters=Fraction(1, 1),
                source_harmony_id="h2",
                retrigger=True,
            ),
        ),
    )

    target = default_digitone_target_profile()

    shared = choose_shared_timing_plan(timeline, target)
    assert shared.total_steps > 128
    assert Fraction(30, 1) <= shared.device_tempo <= Fraction(300, 1)

    with pytest.raises(ValueError, match="128-step capacity"):
        choose_timing_plan(timeline, target)


def test_compile_plan_and_events_export_smoke():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    song = compact_progression_to_song_model(payload)
    timeline = render_timeline(song, default_render_profile())
    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())

    assert plan.total_steps <= 128
    assert plan.source_title == timeline.title
    assert plan.pattern_name == "TEST"
    assert plan.pattern_name_source == "auto"
    assert len(plan.events) > 0

    out = digitone_compile_plan_to_events_yaml_payload(plan)
    assert out["version"] == 1
    assert out["device"] == "digitone2"
    assert out["pattern"]["speed"] == plan.speed
    assert out["events"]
    assert out["events"][0]["length_code"].startswith("0x")


def test_default_target_profile_contains_track_default_velocity_map():
    profile = default_digitone_target_profile()
    assert profile.track_default_velocity == {1: 50, 2: 70, 3: 70, 4: 70, 5: 70, 6: 70, 7: 100}


def test_compile_digitone_pipeline_exports_track_defaults_and_keeps_event_velocity_inherit():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    _song, _timeline, _plan, events_payload = compile_digitone_pipeline(payload)

    assert events_payload["track_defaults"]["velocity"] == {1: 50, 2: 70, 3: 70, 4: 70, 5: 70, 6: 70, 7: 100}
    assert events_payload["events"]
    assert all(event["velocity"] == "inherit" for event in events_payload["events"])


def test_single_pattern_plan_pattern_name_is_final_device_name():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    payload["name"] = "Blue Moon A"
    song = compact_progression_to_song_model(payload)
    timeline = render_timeline(song, default_render_profile())
    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())

    out = digitone_compile_plan_to_events_yaml_payload(plan)
    assert out["name"] == plan.pattern_name
    assert out["name"] == "BLUE MOON A"


def test_single_pattern_long_title_is_truncated_in_plan_with_warning():
    timeline = RenderedTimeline(
        title="BLUE MOON SOLO LONG",
        performance_tempo=Fraction(120, 1),
        events=(
            RenderedNoteEvent(
                id="e1",
                voice_id="chord_voice_1",
                role="chord",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(2, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
            RenderedNoteEvent(
                id="e2",
                voice_id="chord_voice_2",
                role="chord",
                note_midi=64,
                onset_quarters=Fraction(2, 1),
                duration_quarters=Fraction(2, 1),
                source_harmony_id="h2",
                retrigger=True,
            ),
        ),
    )

    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())
    assert plan.pattern_name == "BLUE MOON SOLO L"
    assert any("truncated to 16" in w for w in plan.warnings)


def test_single_pattern_unsupported_auto_name_character_fails_before_build():
    timeline = RenderedTimeline(
        title="BLUE MOON 😺",
        performance_tempo=Fraction(120, 1),
        events=(
            RenderedNoteEvent(
                id="e1",
                voice_id="chord_voice_1",
                role="chord",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(2, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
            RenderedNoteEvent(
                id="e2",
                voice_id="chord_voice_2",
                role="chord",
                note_midi=64,
                onset_quarters=Fraction(2, 1),
                duration_quarters=Fraction(2, 1),
                source_harmony_id="h2",
                retrigger=True,
            ),
        ),
    )

    with pytest.raises(ValueError, match="Unsupported character in auto Pattern Name source title"):
        compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())


def test_compile_digitone_pipeline_keeps_six_voice_tracks_and_bass_without_collisions():
    payload = {
        "name": "Blue Moon Head",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7", "Am7", "Dm7", "G7"]]}],
    }

    song, timeline, plan, events_payload = compile_digitone_pipeline(payload)
    assert song.title == "Blue Moon Head"

    # Am7 must contain F and not F# in rendered harmony source.
    am7_events = [e for e in timeline.events if e.source_harmony_id == "m1_h2" and e.role == "chord"]
    am7_pcs = {e.note_midi % 12 for e in am7_events}
    assert 5 in am7_pcs
    assert 6 not in am7_pcs

    events = events_payload["events"]
    pairs = {(ev["track"], ev["step"]) for ev in events}
    assert len(pairs) == len(events)

    tracks = {int(ev["track"]) for ev in events}
    # chord voices 1..6 and bass track 7 are all used by default profile/mapping.
    assert {1, 2, 3, 4, 5, 6}.issubset(tracks)
    assert 7 in tracks
