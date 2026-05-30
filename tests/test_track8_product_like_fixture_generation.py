from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from changes.digitone.track8_product_like_fixture_generation import (
    PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY,
    PRODUCT_LIKE_TRACK_SCALE_LENGTH,
    PRODUCT_LIKE_TRACK_SCALE_SPEED_ACTIVE,
    PRODUCT_LIKE_TRACK_SCALE_SPEED_INACTIVE,
    build_track8_product_like_cmaj7_manifest,
    build_track8_product_like_cmaj7_yaml_payload,
    write_track8_product_like_cmaj7_fixture,
)
from changes.digitone.track8_toolkit_validation import validate_track8_events_yaml_with_toolkit_loader
from changes.digitone.track8_yaml_export import dump_track8_events_yaml


def test_product_like_yaml_payload_has_expected_pattern_contract():
    payload = build_track8_product_like_cmaj7_yaml_payload()

    assert payload["version"] == 1
    assert payload["device"] == "digitone2"
    assert payload["name"] == "T8 Product Like Cmaj7"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["pattern"]["tempo"] == 120.0
    assert payload["pattern"]["change"] == "OFF"
    assert payload["pattern"]["reset"] == "INF"

    track_scale = payload["track_scale"]
    assert set(track_scale.keys()) == set(range(1, 17))

    for track in range(1, 9):
        assert track_scale[track]["length"] == PRODUCT_LIKE_TRACK_SCALE_LENGTH
        assert track_scale[track]["speed"] == PRODUCT_LIKE_TRACK_SCALE_SPEED_ACTIVE

    for track in range(9, 17):
        assert track_scale[track]["length"] == PRODUCT_LIKE_TRACK_SCALE_LENGTH
        assert track_scale[track]["speed"] == PRODUCT_LIKE_TRACK_SCALE_SPEED_INACTIVE

    assert payload["track_defaults"]["velocity"] == PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY


def test_product_like_yaml_payload_has_expected_track8_chord_contract():
    payload = build_track8_product_like_cmaj7_yaml_payload()
    events = payload["events"]

    assert len(events) == 6
    assert all(event["track"] == 8 for event in events)
    assert all(event["step"] == 1 for event in events)
    assert [event["note"] for event in events] == ["C4", "E4", "G4", "B4", "D5", "A5"]
    assert [event["velocity"] for event in events] == [70, 70, 70, 50, 70, 50]
    assert all(event["length_code"] == "0x4E" for event in events)
    assert all(event["time"] == 0 for event in events)
    assert all("metadata" not in event for event in events)
    assert all(event["track"] not in {1, 2, 3, 4, 5, 6, 7} for event in events)


def test_product_like_yaml_loads_through_toolkit_when_available():
    pytest.importorskip("digitone_syx_toolkit.events_yaml")

    payload = build_track8_product_like_cmaj7_yaml_payload()
    yaml_text = dump_track8_events_yaml(payload)
    assignment = validate_track8_events_yaml_with_toolkit_loader(yaml_text)

    assert assignment.pattern.mode == "per-track"
    assert assignment.pattern.change == "OFF"
    assert assignment.pattern.reset == "INF"
    assert len(assignment.events) == 6
    assert all(event.track == 8 for event in assignment.events)

    if hasattr(assignment, "track_scale"):
        assert set(assignment.track_scale.keys()) == set(range(1, 17))
        for track in range(1, 9):
            assert assignment.track_scale[track].length == PRODUCT_LIKE_TRACK_SCALE_LENGTH
            assert assignment.track_scale[track].speed == PRODUCT_LIKE_TRACK_SCALE_SPEED_ACTIVE
        for track in range(9, 17):
            assert assignment.track_scale[track].length == PRODUCT_LIKE_TRACK_SCALE_LENGTH
            assert assignment.track_scale[track].speed == PRODUCT_LIKE_TRACK_SCALE_SPEED_INACTIVE

    if hasattr(assignment, "track_default_velocity"):
        assert assignment.track_default_velocity == PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY


def test_product_like_yaml_generates_sysex_through_toolkit_when_available():
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    from changes.digitone.track8_sysex_export import generate_track8_sysex_bytes_with_toolkit

    payload = build_track8_product_like_cmaj7_yaml_payload()
    yaml_text = dump_track8_events_yaml(payload)
    syx_bytes = generate_track8_sysex_bytes_with_toolkit(yaml_text)

    assert isinstance(syx_bytes, bytes)
    assert len(syx_bytes) > 0
    assert syx_bytes[0] == 0xF0
    assert syx_bytes[-1] == 0xF7


def test_fixture_writer_writes_expected_files_with_monkeypatched_sysex(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    from changes.digitone import track8_product_like_fixture_generation as fixture_module

    fake_syx = bytes([0xF0, 0x7D, 0x00, 0xF7])
    monkeypatch.setattr(fixture_module, "generate_track8_sysex_bytes_with_toolkit", lambda _yaml: fake_syx)

    paths = write_track8_product_like_cmaj7_fixture(tmp_path)

    assert paths.events_yaml_path.exists()
    assert paths.syx_path.exists()
    assert paths.manifest_path.exists()

    payload = yaml.safe_load(paths.events_yaml_path.read_text(encoding="utf-8"))
    assert payload["pattern"]["mode"] == "per-track"
    assert set(payload["track_scale"].keys()) == set(range(1, 17))
    assert payload["track_defaults"]["velocity"] == PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY

    assert paths.syx_path.read_bytes() == fake_syx

    manifest_text = paths.manifest_path.read_text(encoding="utf-8")
    assert "PER TRACK" in manifest_text
    assert "CHANGE: OFF" in manifest_text
    assert "RESET: INF" in manifest_text
    assert "C4 E4 G4 B4 D5 A5" in manifest_text


def test_fixture_writer_refuses_overwrite_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    from changes.digitone import track8_product_like_fixture_generation as fixture_module

    fake_syx = bytes([0xF0, 0x7D, 0x00, 0xF7])
    monkeypatch.setattr(fixture_module, "generate_track8_sysex_bytes_with_toolkit", lambda _yaml: fake_syx)

    write_track8_product_like_cmaj7_fixture(tmp_path)

    with pytest.raises(FileExistsError):
        write_track8_product_like_cmaj7_fixture(tmp_path, overwrite=False)


def test_committed_fixture_files_exist_and_match_contract():
    fixture_dir = Path("examples/generated/track8_product_like_validation")
    events_yaml_path = fixture_dir / "track8_product_like_cmaj7.events.yaml"
    syx_path = fixture_dir / "track8_product_like_cmaj7.syx"
    manifest_path = fixture_dir / "track8_product_like_cmaj7_manifest.md"

    assert events_yaml_path.exists()
    assert syx_path.exists()
    assert manifest_path.exists()

    payload = yaml.safe_load(events_yaml_path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["device"] == "digitone2"
    assert payload["name"] == "T8 Product Like Cmaj7"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["pattern"]["tempo"] == 120.0
    assert payload["pattern"]["change"] == "OFF"
    assert payload["pattern"]["reset"] == "INF"
    assert set(payload["track_scale"].keys()) == set(range(1, 17))
    assert payload["track_defaults"]["velocity"] == PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY

    events = payload["events"]
    assert len(events) == 6
    assert all(event["track"] == 8 for event in events)
    assert all(event["step"] == 1 for event in events)
    assert [event["note"] for event in events] == ["C4", "E4", "G4", "B4", "D5", "A5"]
    assert [event["velocity"] for event in events] == [70, 70, 70, 50, 70, 50]
    assert all(event["length_code"] == "0x4E" for event in events)
    assert all(event["time"] == 0 for event in events)

    syx = syx_path.read_bytes()
    assert len(syx) > 0
    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7

    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert "Elektron Transfer" in manifest_text
    assert "PER TRACK" in manifest_text
    assert "CHANGE: OFF" in manifest_text
    assert "RESET: INF" in manifest_text
    assert "C4 E4 G4 B4 D5 A5" in manifest_text


def test_generated_fixture_is_deterministic_with_monkeypatched_sysex(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    from changes.digitone import track8_product_like_fixture_generation as fixture_module

    fake_syx = bytes([0xF0, 0x7D, 0x00, 0xF7])
    monkeypatch.setattr(fixture_module, "generate_track8_sysex_bytes_with_toolkit", lambda _yaml: fake_syx)

    dir1 = tmp_path / "gen1"
    dir2 = tmp_path / "gen2"
    paths1 = write_track8_product_like_cmaj7_fixture(dir1)
    paths2 = write_track8_product_like_cmaj7_fixture(dir2)

    assert paths1.events_yaml_path.read_text(encoding="utf-8") == paths2.events_yaml_path.read_text(encoding="utf-8")
    assert paths1.manifest_path.read_text(encoding="utf-8") == paths2.manifest_path.read_text(encoding="utf-8")
    assert paths1.syx_path.read_bytes() == paths2.syx_path.read_bytes()


def test_manifest_builder_contains_expected_sections():
    text = build_track8_product_like_cmaj7_manifest(
        events_yaml_filename="track8_product_like_cmaj7.events.yaml",
        syx_filename="track8_product_like_cmaj7.syx",
        syx_size_bytes=999,
    )

    assert "# Track 8 Product-like Cmaj7 Fixture" in text
    assert "Expected product-like pattern settings" in text
    assert "Track default velocities" in text
    assert "Track 8 chord content" in text
    assert "No MIDI" in text or "does not send MIDI" in text
