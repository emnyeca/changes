from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from changes.digitone.track8_demo_songs import build_demo_cmaj7_song
from changes.digitone.track8_export_api import build_track8_export_yaml_payload_from_song
from changes.models.song_model_yaml import (
    dump_song_model_yaml,
    format_fraction_value,
    load_song_model_yaml,
    parse_fraction_value,
    song_model_from_dict,
    song_model_to_dict,
)


def _minimal_payload() -> dict:
    return {
        "version": 1,
        "type": "changes.song",
        "title": "Demo Cmaj7",
        "working_key": "C",
        "performance_tempo": 120,
        "measures": [
            {
                "number": 1,
                "section_id": "A",
                "meter": "4/4",
                "absolute_start_quarters": 0,
                "harmony": [
                    {
                        "id": "h1",
                        "symbol": "Cmaj7",
                        "offset_quarters": 0,
                        "duration_quarters": 4,
                    }
                ],
            }
        ],
    }


def test_load_minimal_cmaj7_yaml_dict():
    song = song_model_from_dict(_minimal_payload())

    assert song.title == "Demo Cmaj7"
    assert song.working_key == "C"
    assert song.performance_tempo == Fraction(120, 1)
    assert len(song.measures) == 1

    measure = song.measures[0]
    assert measure.meter_numerator == 4
    assert measure.meter_denominator == 4
    assert len(measure.harmony) == 1

    harmony = measure.harmony[0]
    assert harmony.symbol == "Cmaj7"
    assert harmony.offset_quarters == Fraction(0, 1)
    assert harmony.duration_quarters == Fraction(4, 1)
    assert harmony.measure_number == 1


def test_dump_minimal_cmaj7_song_model_to_dict():
    song = build_demo_cmaj7_song()

    payload = song_model_to_dict(song)

    assert payload["version"] == 1
    assert payload["type"] == "changes.song"
    assert payload["measures"][0]["meter"] == "4/4"
    assert payload["measures"][0]["absolute_start_quarters"] == 0
    assert payload["performance_tempo"] == 120
    assert payload["measures"][0]["harmony"][0]["symbol"] == "Cmaj7"

    def _walk(v):
        if isinstance(v, dict):
            for vv in v.values():
                yield from _walk(vv)
        elif isinstance(v, list):
            for vv in v:
                yield from _walk(vv)
        else:
            yield v

    assert all(not isinstance(v, float) for v in _walk(payload))


def test_yaml_roundtrip(tmp_path: Path):
    song = build_demo_cmaj7_song()

    yaml_text = dump_song_model_yaml(song)
    path = tmp_path / "demo.changes.yaml"
    path.write_text(yaml_text, encoding="utf-8")

    loaded = load_song_model_yaml(path)

    assert loaded.title == song.title
    assert loaded.working_key == song.working_key
    assert loaded.performance_tempo == song.performance_tempo
    assert len(loaded.measures) == len(song.measures)
    assert loaded.measures[0].number == song.measures[0].number
    assert loaded.measures[0].meter_numerator == song.measures[0].meter_numerator
    assert loaded.measures[0].meter_denominator == song.measures[0].meter_denominator
    assert loaded.measures[0].harmony[0].symbol == song.measures[0].harmony[0].symbol
    assert loaded.measures[0].harmony[0].offset_quarters == song.measures[0].harmony[0].offset_quarters
    assert loaded.measures[0].harmony[0].duration_quarters == song.measures[0].harmony[0].duration_quarters


def test_example_file_loads():
    path = Path("examples/song_models/demo_cmaj7.changes.yaml")
    song = load_song_model_yaml(path)

    assert song.title == "Demo Cmaj7"
    assert song.working_key == "C"
    assert song.measures[0].harmony[0].symbol == "Cmaj7"


def test_loaded_song_model_feeds_track8_export_api():
    path = Path("examples/song_models/demo_cmaj7.changes.yaml")
    song = load_song_model_yaml(path)

    payload = build_track8_export_yaml_payload_from_song(song)

    assert payload["device"] == "digitone2"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["events"]
    assert [event["note"] for event in payload["events"]] == ["C4", "E4", "G4", "B4", "D5", "A5"]


def test_invalid_version_or_type_errors():
    payload = _minimal_payload()
    payload["version"] = 2
    with pytest.raises(ValueError, match="unsupported song model version"):
        song_model_from_dict(payload)

    payload2 = _minimal_payload()
    payload2["type"] = "something.else"
    with pytest.raises(ValueError, match="unsupported song model type"):
        song_model_from_dict(payload2)


@pytest.mark.parametrize(
    "mutator, match",
    [
        (lambda p: p.pop("measures"), "missing required fields"),
        (lambda p: p.pop("working_key"), "missing required fields"),
        (lambda p: p["measures"][0].pop("meter"), "missing required fields"),
        (lambda p: p["measures"][0]["harmony"][0].pop("symbol"), "missing required fields"),
    ],
)
def test_missing_required_fields_error(mutator, match: str):
    payload = _minimal_payload()
    mutator(payload)
    with pytest.raises(ValueError, match=match):
        song_model_from_dict(payload)


def test_fraction_parser():
    assert parse_fraction_value(0) == Fraction(0, 1)
    assert parse_fraction_value(4) == Fraction(4, 1)
    assert parse_fraction_value("1/2") == Fraction(1, 2)
    assert parse_fraction_value("3/2") == Fraction(3, 2)

    with pytest.raises(ValueError):
        parse_fraction_value(1.5)
    with pytest.raises(ValueError):
        parse_fraction_value("")
    with pytest.raises(ValueError):
        parse_fraction_value("foo")
    with pytest.raises(ValueError):
        parse_fraction_value("1/0")

    assert format_fraction_value(Fraction(4, 1)) == 4
    assert format_fraction_value(Fraction(3, 2)) == "3/2"


def test_no_floats_in_dumped_yaml():
    song = build_demo_cmaj7_song()
    yaml_text = dump_song_model_yaml(song)

    assert "0.0" not in yaml_text
    assert "4.0" not in yaml_text
    assert "120.0" not in yaml_text
