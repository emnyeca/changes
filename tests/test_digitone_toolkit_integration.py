from __future__ import annotations

import importlib
import sys
from fractions import Fraction
from pathlib import Path

import pytest
import yaml

from changes.digitone.planner import _find_exact_length_code_for_units, compile_timeline_to_digitone_plan
from changes.exporters.digitone_events import digitone_compile_plan_to_events_yaml_payload
from changes.models.digitone_target_profile import DigitoneTargetProfile, default_digitone_target_profile
from changes.models.rendered_timeline import RenderedNoteEvent, RenderedTimeline
from changes.pipeline_digitone import compile_digitone_pipeline, save_digitone_pipeline_artifacts


def _ensure_toolkit_or_skip():
    try:
        importlib.import_module("digitone_syx_toolkit.events_yaml")
        return
    except Exception:
        pass

    root = Path(__file__).resolve().parents[2]
    local_src = root / "digitone-syx-toolkit" / "src"
    if local_src.exists() and str(local_src) not in sys.path:
        sys.path.insert(0, str(local_src))

    try:
        importlib.import_module("digitone_syx_toolkit.events_yaml")
    except Exception:
        pytest.skip("digitone-syx-toolkit is required for integration tests")


def _simple_ii_v_i_payload() -> dict:
    return {
        "name": "Simple ii-V-I",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 120,
        "sections": [
            {
                "name": "A",
                "progression": [["Dm7", "G7", "Cmaj7", "Cmaj7"]],
            }
        ],
    }


def test_events_yaml_matches_toolkit_schema_and_validates(tmp_path: Path):
    _ensure_toolkit_or_skip()
    from digitone_syx_toolkit.events_yaml import load_event_assignment_yaml

    song, timeline, plan, payload = compile_digitone_pipeline(_simple_ii_v_i_payload())
    out = save_digitone_pipeline_artifacts(tmp_path, song, timeline, plan, payload, write_syx=False)

    assignment = load_event_assignment_yaml(out["events_yaml"])

    assert assignment.version == 1
    assert assignment.device == "digitone2"
    assert assignment.pattern.tempo == float(plan.device_tempo)
    assert assignment.pattern.mode == "per-track"
    assert assignment.pattern.change == "OFF"
    assert assignment.pattern.reset == "INF"
    assert len(assignment.track_scale) == 16
    assert assignment.track_scale[1].length == plan.total_steps
    assert assignment.track_scale[8].speed == plan.speed
    assert assignment.track_scale[16].length == 16
    assert assignment.track_scale[16].speed == "1"
    assert assignment.name == "SIMPLE II-V-I"
    assert len(assignment.events) == len(plan.events)

    plan_codes = {
        (e.track, e.step, e.note): int(e.length_code)
        for e in plan.events
    }
    for ev in assignment.events:
        key = (ev.track, ev.step, ev.note)
        assert key in plan_codes
        assert ev.length_code == plan_codes[key]


def test_digitone_note_round_trip_c5_to_midi_60(tmp_path: Path):
    _ensure_toolkit_or_skip()
    from digitone_syx_toolkit.events_yaml import load_event_assignment_yaml

    timeline = RenderedTimeline(
        title="note-roundtrip",
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
        ),
    )
    target = DigitoneTargetProfile(
        name="note-rt",
        device="digitone2",
        voice_to_track={"chord_voice_1": 1},
        default_velocity="inherit",
        length_strategy="hold_until_next_event",
        allow_inf=False,
        approximation="error",
        preferred_speed=Fraction(1, 8),
        fallback_speeds=(Fraction(1, 4), Fraction(1, 2), Fraction(1, 1), Fraction(2, 1)),
    )

    plan = compile_timeline_to_digitone_plan(timeline, target)
    assert len(plan.events) == 1
    assert plan.events[0].note == "C5"

    payload = digitone_compile_plan_to_events_yaml_payload(plan)
    path = tmp_path / "events.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")

    assignment = load_event_assignment_yaml(path)
    assert assignment.pattern.mode == "per-track"
    assert assignment.events[0].note_midi == 60


def test_length_lookup_uses_toolkit_exact_mapping():
    _ensure_toolkit_or_skip()

    assert _find_exact_length_code_for_units(Fraction(1, 1)) == 0x0E
    assert _find_exact_length_code_for_units(Fraction(2, 1)) == 0x1E
    assert _find_exact_length_code_for_units(Fraction(4, 1)) == 0x2E
    assert _find_exact_length_code_for_units(Fraction(8, 1)) == 0x3E
    assert _find_exact_length_code_for_units(Fraction(128, 1)) == 0x7E


def test_total_steps_minimum_two_and_toolkit_validation(tmp_path: Path):
    _ensure_toolkit_or_skip()
    from digitone_syx_toolkit.events_yaml import load_event_assignment_yaml

    payload = {
        "name": "OneChord",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Cmaj7"]]}],
    }

    song, timeline, plan, events_payload = compile_digitone_pipeline(payload)
    assert 2 <= plan.total_steps <= 128

    out = save_digitone_pipeline_artifacts(tmp_path, song, timeline, plan, events_payload, write_syx=False)
    assignment = load_event_assignment_yaml(out["events_yaml"])
    assert all(2 <= scale.length <= 128 for scale in assignment.track_scale.values())


def test_e2e_simple_ii_v_i_to_syx_and_round_trip(tmp_path: Path):
    _ensure_toolkit_or_skip()
    from digitone_syx_toolkit.digitone2.length_codes import find_exact_length_code_for_sixteenth_units
    from digitone_syx_toolkit.events_yaml import load_event_assignment_yaml

    song, timeline, plan, events_payload = compile_digitone_pipeline(_simple_ii_v_i_payload())
    out = save_digitone_pipeline_artifacts(tmp_path, song, timeline, plan, events_payload, write_syx=True)

    assert Fraction(30, 1) <= plan.device_tempo <= Fraction(300, 1)
    assert 2 <= plan.total_steps <= 128

    assignment = load_event_assignment_yaml(out["events_yaml"])
    assert len(assignment.events) == len(plan.events)
    assert assignment.pattern.mode == "per-track"
    assert assignment.track_scale[8].length == plan.total_steps
    assert assignment.track_scale[16].length == 16

    midi_by_pair = {(e.track, e.step): e.note_midi for e in assignment.events}
    for event in plan.events:
        assert (event.track, event.step) in midi_by_pair

    timeline_by_id = {e.id: e for e in timeline.events}
    for event in plan.events:
        src = timeline_by_id[event.source_event_id]
        units = src.duration_quarters / (plan.speed_ratio * plan.q_step)
        expected = find_exact_length_code_for_sixteenth_units(units)
        assert expected == int(event.length_code)

    assert out["syx"].exists()
    assert out["syx"].stat().st_size > 0


def test_toolkit_truncates_over_16_char_pattern_name_from_pipeline(tmp_path: Path):
    _ensure_toolkit_or_skip()
    from digitone_syx_toolkit.events_yaml import load_event_assignment_yaml

    payload = {
        "name": "BLUE MOON SOLO FORM",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {
                "name": "A",
                "progression": [["Cmaj7", "Dm7", "G7", "Cmaj7"]],
            }
        ],
    }

    song, timeline, plan, events_payload = compile_digitone_pipeline(payload)
    out = save_digitone_pipeline_artifacts(tmp_path, song, timeline, plan, events_payload, write_syx=False)

    assignment = load_event_assignment_yaml(out["events_yaml"])
    assert assignment.name == "BLUE MOON SOLO F"
