from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from changes.digitone.track8_fixture_generation import (
    build_track8_cmaj7_hardware_validation_manifest,
    build_track8_cmaj7_hardware_validation_yaml_payload,
    write_track8_cmaj7_hardware_validation_fixture,
)


def test_canonical_yaml_payload_has_expected_musical_contract():
    payload = build_track8_cmaj7_hardware_validation_yaml_payload()

    assert payload["version"] == 1
    assert payload["device"] == "digitone2"
    assert payload["pattern"]["mode"] == "pattern-wide"
    assert payload["pattern"]["tempo"] == 120.0
    assert payload["pattern"]["speed"] == "1/8"
    assert payload["pattern"]["total_steps"] == 16
    assert len(payload["events"]) == 6
    assert tuple(event["step"] for event in payload["events"]) == (1, 1, 1, 1, 1, 1)
    assert tuple(event["track"] for event in payload["events"]) == (8, 8, 8, 8, 8, 8)
    assert tuple(event["note"] for event in payload["events"]) == ("C4", "E4", "G4", "B4", "D5", "A5")
    assert tuple(event["velocity"] for event in payload["events"]) == (70, 70, 70, 50, 70, 50)
    assert tuple(event["length_code"] for event in payload["events"]) == (
        "0x4E",
        "0x4E",
        "0x4E",
        "0x4E",
        "0x4E",
        "0x4E",
    )
    assert tuple(event["time"] for event in payload["events"]) == (0, 0, 0, 0, 0, 0)
    assert all("metadata" not in event for event in payload["events"])


def test_manifest_text_is_deterministic_and_contains_key_instructions():
    text = build_track8_cmaj7_hardware_validation_manifest(
        events_yaml_filename="track8_cmaj7_changes.events.yaml",
        syx_filename="track8_cmaj7_changes.syx",
        syx_size_bytes=1234,
    )

    assert "# Track 8 Cmaj7 Hardware Validation Fixture" in text
    assert "track8_cmaj7_changes.events.yaml" in text
    assert "track8_cmaj7_changes.syx" in text
    assert "Track: 8" in text
    assert "Step: 1" in text
    assert "C4 E4 G4 B4 D5 A5" in text
    assert "0x4E" in text
    assert "Elektron Transfer" in text
    assert "2026-" not in text


def test_fixture_writer_refuses_overwrite_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from changes.digitone import track8_fixture_generation as fixture_module

    fake_syx = bytes([0xF0, 0x7D, 0x00, 0xF7])
    monkeypatch.setattr(fixture_module, "generate_track8_sysex_bytes_with_toolkit", lambda _yaml: fake_syx)

    write_track8_cmaj7_hardware_validation_fixture(tmp_path)

    with pytest.raises(FileExistsError):
        write_track8_cmaj7_hardware_validation_fixture(tmp_path, overwrite=False)


def test_fixture_writer_writes_expected_files_with_monkeypatched_sysex(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    from changes.digitone import track8_fixture_generation as fixture_module

    fake_syx = bytes([0xF0, 0x7D, 0x00, 0xF7])
    monkeypatch.setattr(fixture_module, "generate_track8_sysex_bytes_with_toolkit", lambda _yaml: fake_syx)

    paths = write_track8_cmaj7_hardware_validation_fixture(tmp_path)

    assert paths.events_yaml_path.exists()
    assert paths.syx_path.exists()
    assert paths.manifest_path.exists()

    yaml_text = paths.events_yaml_path.read_text(encoding="utf-8")
    assert "C4" in yaml_text
    assert "E4" in yaml_text
    assert "length_code" in yaml_text
    assert "0x4E" in yaml_text

    assert paths.syx_path.read_bytes() == fake_syx

    manifest_text = paths.manifest_path.read_text(encoding="utf-8")
    assert str(len(fake_syx)) in manifest_text
    assert paths.events_yaml_path.name in manifest_text
    assert paths.syx_path.name in manifest_text


def test_optional_real_toolkit_fixture_generation(tmp_path: Path):
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    paths = write_track8_cmaj7_hardware_validation_fixture(tmp_path)

    syx = paths.syx_path.read_bytes()
    assert paths.syx_path.exists()
    assert len(syx) > 0
    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7
    assert paths.events_yaml_path.exists()
    assert paths.manifest_path.exists()


def test_committed_fixture_files_exist_and_match_contract():
    fixture_dir = Path("examples/generated/track8_hardware_validation")
    events_yaml_path = fixture_dir / "track8_cmaj7_changes.events.yaml"
    syx_path = fixture_dir / "track8_cmaj7_changes.syx"
    manifest_path = fixture_dir / "track8_cmaj7_changes_manifest.md"

    assert events_yaml_path.exists()
    assert syx_path.exists()
    assert manifest_path.exists()

    payload = yaml.safe_load(events_yaml_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload["version"] == 1
    assert payload["device"] == "digitone2"
    assert payload["pattern"]["mode"] == "pattern-wide"
    assert payload["pattern"]["tempo"] == 120.0
    assert payload["pattern"]["speed"] == "1/8"
    assert payload["pattern"]["total_steps"] == 16
    assert len(payload["events"]) == 6
    assert tuple(event["step"] for event in payload["events"]) == (1, 1, 1, 1, 1, 1)
    assert tuple(event["track"] for event in payload["events"]) == (8, 8, 8, 8, 8, 8)
    assert tuple(event["note"] for event in payload["events"]) == ("C4", "E4", "G4", "B4", "D5", "A5")
    assert tuple(event["velocity"] for event in payload["events"]) == (70, 70, 70, 50, 70, 50)
    assert tuple(event["length_code"] for event in payload["events"]) == (
        "0x4E",
        "0x4E",
        "0x4E",
        "0x4E",
        "0x4E",
        "0x4E",
    )
    assert tuple(event["time"] for event in payload["events"]) == (0, 0, 0, 0, 0, 0)

    syx = syx_path.read_bytes()
    assert len(syx) > 0
    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7

    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert "Elektron Transfer" in manifest_text
    assert "Track: 8" in manifest_text
    assert "Step: 1" in manifest_text
    assert "C4 E4 G4 B4 D5 A5" in manifest_text
    assert "0x4E" in manifest_text
