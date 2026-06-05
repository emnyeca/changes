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
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.pipeline_digitone import compile_digitone_pipeline
from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
from changes.rendering.arrangement_renderer import render_arrangement


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
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, default_render_profile()))

    v1 = [e for e in timeline.events if e.voice_id == "cloud_voice_1"]
    assert len(v1) == 1, "hold_until_change merges contiguous same-pitch events into one"
    assert v1[0].duration_quarters == Fraction(4, 1), "merged event spans the full duration"


def test_rendered_timeline_emits_six_chord_voices_plus_bass_per_event_without_hold_merge():
    payload = {
        "name": "Blue Moon Head",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7", "Am7", "Dm7", "G7"]]}],
    }
    song = compact_progression_to_song_model(payload)
    rp = replace(default_render_profile(), cloud_trigger_policy="retrigger", bass_trigger_policy="retrigger")
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, rp), render_profile=rp)

    assert len(timeline.events) == 4 * 13

    cloud_voices = {e.voice_id for e in timeline.events if e.role == "cloud"}
    assert cloud_voices == {
        "cloud_voice_1",
        "cloud_voice_2",
        "cloud_voice_3",
        "cloud_voice_4",
        "cloud_voice_5",
        "cloud_voice_6",
    }
    assert {e.voice_id for e in timeline.events if e.role == "chord"} == {
        "chord_note_1",
        "chord_note_2",
        "chord_note_3",
        "chord_note_4",
        "chord_note_5",
        "chord_note_6",
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
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, default_render_profile()))

    am7_events = [e for e in timeline.events if e.source_harmony_id == "m1_h2" and e.role == "cloud"]
    pcs = {e.note_midi % 12 for e in am7_events}

    assert 5 in pcs  # F
    assert 6 not in pcs  # F#


def test_timing_plan_falls_back_from_invalid_tempo_bounds():
    from changes.models.digitone_target_profile import LayerRouting, VoiceRouting
    target = DigitoneTargetProfile(
        name="fallback-test",
        device="digitone2",
        routing={"cloud": LayerRouting(voices={"cloud_voice_1": VoiceRouting(track=1)})},
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
                voice_id="cloud_voice_1",
                role="cloud",
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
                voice_id="cloud_voice_1",
                role="cloud",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(35, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
            RenderedNoteEvent(
                id="e2",
                voice_id="cloud_voice_2",
                role="cloud",
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
                voice_id="cloud_voice_1",
                role="cloud",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(1, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
            RenderedNoteEvent(
                id="e2",
                voice_id="cloud_voice_1",
                role="cloud",
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
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, default_render_profile()))
    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())

    assert plan.total_steps <= 128
    assert plan.source_title == timeline.title
    assert plan.pattern_name == "TEST"
    assert plan.pattern_name_source == "auto"
    assert len(plan.events) > 0

    out = digitone_compile_plan_to_events_yaml_payload(plan)
    assert out["version"] == 1
    assert out["device"] == "digitone2"
    assert out["pattern"]["mode"] == "per-track"
    assert out["pattern"]["change"] == int(Fraction(plan.total_steps, 1) / plan.speed_ratio)
    assert out["pattern"]["reset"] == "INF"
    assert sorted(out["track_scale"]) == list(range(1, 17))
    assert all(out["track_scale"][track]["length"] == plan.total_steps for track in range(1, 9))
    assert all(out["track_scale"][track]["speed"] == plan.speed for track in range(1, 9))
    assert all(out["track_scale"][track]["length"] == 16 for track in range(9, 17))
    assert all(out["track_scale"][track]["speed"] == "1" for track in range(9, 17))
    assert out["events"]
    assert out["events"][0]["length_code"].startswith("0x")


def test_events_export_can_keep_pattern_change_off_policy():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    song = compact_progression_to_song_model(payload)
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, default_render_profile()))
    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())

    out = digitone_compile_plan_to_events_yaml_payload(plan, pattern_change_policy="off")

    assert out["pattern"]["change"] == "OFF"
    assert out["pattern"]["reset"] == "INF"


def test_events_export_derives_pattern_change_for_different_speed():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    song = compact_progression_to_song_model(payload)
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, default_render_profile()))
    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())
    plan = replace(plan, total_steps=32, speed="1/4", speed_ratio=Fraction(1, 4))

    out = digitone_compile_plan_to_events_yaml_payload(plan)

    assert out["pattern"]["change"] == 128
    assert out["pattern"]["reset"] == "INF"


def test_default_target_profile_routing_and_velocity():
    profile = default_digitone_target_profile()

    assert profile.track_default_velocity == {1: 70, 2: 70, 3: 70, 4: 50, 5: 70, 6: 50, 7: 100}
    assert profile.polyphonic_tracks == (8,)

    v2t = profile.voice_to_track
    assert {v2t[f"cloud_voice_{i}"] for i in range(1, 7)} == {1, 2, 3, 4, 5, 6}
    assert v2t["bass"] == 7
    assert all(v2t[f"chord_note_{i}"] == 8 for i in range(1, 7))


def test_flattened_arrangement_compiles_product_tracks_1_to_8_with_chord_velocity():
    song = compact_progression_to_song_model(_song_payload([["Cmaj7"]]))
    arrangement = render_arrangement(song)
    timeline = flatten_arrangement_to_timeline(arrangement)

    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())

    tracks = {event.track for event in plan.events}
    assert {1, 2, 3, 4, 5, 6, 7, 8}.issubset(tracks)

    track8_events = [event for event in plan.events if event.track == 8]
    assert len(track8_events) == 6
    assert {event.step for event in track8_events} == {1}
    assert tuple(event.velocity for event in track8_events) == (70, 70, 70, 50, 70, 50)

    track1_to_7_events = [event for event in plan.events if event.track in {1, 2, 3, 4, 5, 6, 7}]
    assert track1_to_7_events
    assert all(event.velocity == "inherit" for event in track1_to_7_events)


def test_compile_digitone_pipeline_layer_selection_can_export_chord_only():
    payload = _song_payload([["Cmaj7"]])
    _song, timeline, _plan, events_payload = compile_digitone_pipeline(payload, layers="chord")

    assert {event.role for event in timeline.events} == {"chord"}
    assert {event["track"] for event in events_payload["events"]} == {8}
    assert [event["velocity"] for event in events_payload["events"]] == [70, 70, 70, 50, 70, 50]


def test_compile_digitone_pipeline_exports_track_defaults_and_keeps_event_velocity_inherit():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    _song, _timeline, plan, events_payload = compile_digitone_pipeline(payload)

    assert events_payload["track_defaults"]["velocity"] == {1: 70, 2: 70, 3: 70, 4: 50, 5: 70, 6: 50, 7: 100}
    assert events_payload["pattern"] == {
        "mode": "per-track",
        "tempo": float(plan.device_tempo),
        "change": int(Fraction(plan.total_steps, 1) / plan.speed_ratio),
        "reset": "INF",
    }
    assert len(events_payload["track_scale"]) == 16
    assert events_payload["track_scale"][8] == {"length": plan.total_steps, "speed": plan.speed}
    assert events_payload["track_scale"][16] == {"length": 16, "speed": "1"}
    assert events_payload["events"]
    assert all(event["velocity"] == "inherit" for event in events_payload["events"] if event["track"] in range(1, 8))
    assert [event["velocity"] for event in events_payload["events"] if event["track"] == 8][:6] == [
        70,
        70,
        70,
        50,
        70,
        50,
    ]


def test_single_pattern_plan_pattern_name_is_final_device_name():
    payload = _song_payload([["Cmaj7", "Dm7", "G7", "Cmaj7"]])
    payload["name"] = "Blue Moon A"
    song = compact_progression_to_song_model(payload)
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, default_render_profile()))
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
                voice_id="cloud_voice_1",
                role="cloud",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(2, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
            RenderedNoteEvent(
                id="e2",
                voice_id="cloud_voice_2",
                role="cloud",
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


def test_single_pattern_unsupported_auto_name_character_strips_and_warns():
    timeline = RenderedTimeline(
        title="BLUE MOON 😺",
        performance_tempo=Fraction(120, 1),
        events=(
            RenderedNoteEvent(
                id="e1",
                voice_id="cloud_voice_1",
                role="cloud",
                note_midi=60,
                onset_quarters=Fraction(0, 1),
                duration_quarters=Fraction(2, 1),
                source_harmony_id="h1",
                retrigger=True,
            ),
            RenderedNoteEvent(
                id="e2",
                voice_id="cloud_voice_2",
                role="cloud",
                note_midi=64,
                onset_quarters=Fraction(2, 1),
                duration_quarters=Fraction(2, 1),
                source_harmony_id="h2",
                retrigger=True,
            ),
        ),
    )

    plan = compile_timeline_to_digitone_plan(timeline, default_digitone_target_profile())
    assert plan.pattern_name == "BLUE MOON "
    assert any("stripped" in w for w in plan.warnings)


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
    am7_events = [e for e in timeline.events if e.source_harmony_id == "m1_h2" and e.role == "cloud"]
    am7_pcs = {e.note_midi % 12 for e in am7_events}
    assert 5 in am7_pcs
    assert 6 not in am7_pcs

    events = events_payload["events"]
    non_poly_pairs = [(ev["track"], ev["step"]) for ev in events if ev["track"] != 8]
    assert len(set(non_poly_pairs)) == len(non_poly_pairs)

    tracks = {int(ev["track"]) for ev in events}
    assert {1, 2, 3, 4, 5, 6}.issubset(tracks)
    assert 7 in tracks
    assert 8 in tracks


@pytest.mark.parametrize(
    ("symbol", "expected_bass_midi"),
    [
        ("Cmaj7", 36),
        ("F#7", 42),
        ("Gm7", 43),
        ("Am7", 45),
        ("B7", 47),
        ("Dm7/G", 43),
        ("C/E", 40),
    ],
)
def test_bass_register_policy_and_slash_bass_source(symbol: str, expected_bass_midi: int):
    payload = _song_payload([[symbol]])
    song = compact_progression_to_song_model(payload)
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, default_render_profile()))

    bass_events = [e for e in timeline.events if e.role == "bass"]
    assert len(bass_events) == 1
    assert bass_events[0].note_midi == expected_bass_midi


def test_rendered_timeline_chord_and_bass_events_are_within_profile_register_bounds():
    payload = {
        "name": "Blue Moon Head",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7", "Am7", "Dm7", "G7"]]}],
    }
    song = compact_progression_to_song_model(payload)
    rp = default_render_profile()
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, rp))

    # Cloud uses center/spread repair, not fixed range bounds; skip cloud bounds check.
    for event in timeline.events:
        if event.role == "chord":
            assert rp.chord_min_midi <= event.note_midi <= rp.chord_max_midi
        if event.role == "bass":
            assert rp.bass_min_midi <= event.note_midi <= rp.bass_max_midi


def test_no_chord_event_generates_no_notes_but_keeps_duration_boundary():
    song = SongModel(
        title="NC",
        working_key="C",
        performance_tempo=Fraction(120, 1),
        measures=(
            Measure(
                number=1,
                section_id="A",
                meter_numerator=4,
                meter_denominator=4,
                absolute_start_quarters=Fraction(0, 1),
                harmony=(
                    HarmonyEvent(
                        id="m1_h1",
                        symbol="C7",
                        measure_number=1,
                        offset_quarters=Fraction(0, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                    HarmonyEvent(
                        id="m1_h2",
                        symbol="N.C.",
                        measure_number=1,
                        offset_quarters=Fraction(1, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                    HarmonyEvent(
                        id="m1_h3",
                        symbol="F7",
                        measure_number=1,
                        offset_quarters=Fraction(2, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                    HarmonyEvent(
                        id="m1_h4",
                        symbol="Bb7",
                        measure_number=1,
                        offset_quarters=Fraction(3, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                ),
            ),
        ),
    )

    arrangement = render_arrangement(song)
    assert [occ.source_harmony_id for occ in arrangement.occurrences] == ["m1_h1", "m1_h3", "m1_h4"]

    timeline = flatten_arrangement_to_timeline(arrangement, render_profile=default_render_profile())
    assert all(event.source_harmony_id != "m1_h2" for event in timeline.events)


def test_no_chord_breaks_hold_merge_boundary_for_same_pitch_before_after_gap():
    song = SongModel(
        title="NC Hold",
        working_key="C",
        performance_tempo=Fraction(120, 1),
        measures=(
            Measure(
                number=1,
                section_id="A",
                meter_numerator=4,
                meter_denominator=4,
                absolute_start_quarters=Fraction(0, 1),
                harmony=(
                    HarmonyEvent(
                        id="m1_h1",
                        symbol="C7",
                        measure_number=1,
                        offset_quarters=Fraction(0, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                    HarmonyEvent(
                        id="m1_h2",
                        symbol="N.C.",
                        measure_number=1,
                        offset_quarters=Fraction(1, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                    HarmonyEvent(
                        id="m1_h3",
                        symbol="C7",
                        measure_number=1,
                        offset_quarters=Fraction(2, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                    HarmonyEvent(
                        id="m1_h4",
                        symbol="C7",
                        measure_number=1,
                        offset_quarters=Fraction(3, 1),
                        duration_quarters=Fraction(1, 1),
                    ),
                ),
            ),
        ),
    )

    timeline = flatten_arrangement_to_timeline(render_arrangement(song), render_profile=default_render_profile())
    cloud_events = [e for e in timeline.events if e.role == "cloud" and e.voice_id == "cloud_voice_1"]

    assert len(cloud_events) == 2
    assert cloud_events[0].onset_quarters == Fraction(0, 1)
    assert cloud_events[0].duration_quarters == Fraction(1, 1)
    assert cloud_events[1].onset_quarters == Fraction(2, 1)
    assert cloud_events[1].duration_quarters == Fraction(2, 1)
