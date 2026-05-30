from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest
import yaml

from changes import cli
from changes.digitone.track8_export_api import (
    build_track8_export_yaml_payload_from_song,
    export_track8_artifacts_from_song,
)
from changes.models.song_model_yaml import load_song_model_yaml


EXAMPLE_PATH = Path("examples/song_models/demo_ii_v_i.changes.yaml")
MULTIBAR_PATH = Path("examples/song_models/demo_multibar_turnaround.changes.yaml")
MULTISECTION_PATH = Path("examples/song_models/demo_multisection_form.changes.yaml")


def test_multichord_example_file_loads():
    song = load_song_model_yaml(EXAMPLE_PATH)

    assert song.title == "Demo II V I"
    assert song.working_key == "C"
    assert len(song.measures) == 1

    measure = song.measures[0]
    assert len(measure.harmony) == 3
    assert [h.symbol for h in measure.harmony] == ["Dm7", "G7", "Cmaj7"]
    assert [h.offset_quarters for h in measure.harmony] == [Fraction(0, 1), Fraction(1, 1), Fraction(2, 1)]
    assert [h.duration_quarters for h in measure.harmony] == [Fraction(1, 1), Fraction(1, 1), Fraction(2, 1)]


def test_multichord_example_feeds_track8_export_api():
    song = load_song_model_yaml(EXAMPLE_PATH)

    payload = build_track8_export_yaml_payload_from_song(song)

    assert payload["device"] == "digitone2"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["events"]
    assert all(event["track"] == 8 for event in payload["events"])
    assert len(payload["events"]) > 6

    steps = [int(event["step"]) for event in payload["events"]]
    assert len(set(steps)) >= 3
    assert steps == sorted(steps)


def test_generated_event_groups_preserve_chord_offsets():
    song = load_song_model_yaml(EXAMPLE_PATH)
    payload = build_track8_export_yaml_payload_from_song(song)

    steps = [int(event["step"]) for event in payload["events"]]
    assert min(steps) == 1
    assert max(steps) > min(steps)
    assert len(set(steps)) > 1


def test_generated_lengths_vary_by_duration():
    song = load_song_model_yaml(EXAMPLE_PATH)
    payload = build_track8_export_yaml_payload_from_song(song)

    length_codes = {str(event["length_code"]) for event in payload["events"] if "length_code" in event}
    assert len(length_codes) >= 2


def test_cli_input_events_yaml_only_multichord_succeeds_without_toolkit(tmp_path: Path, monkeypatch, capsys):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            str(EXAMPLE_PATH),
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )

    cli.main()

    events_yaml = output_dir / "changes_track8_export.events.yaml"
    manifest = output_dir / "changes_track8_export_manifest.md"
    syx = output_dir / "changes_track8_export.syx"

    assert events_yaml.exists()
    assert manifest.exists()
    assert not syx.exists()

    payload = yaml.safe_load(events_yaml.read_text(encoding="utf-8"))
    assert payload["name"] == "Demo II V I"
    assert payload["device"] == "digitone2"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["events"]
    assert all(event["track"] == 8 for event in payload["events"])
    assert len(payload["events"]) > 6
    steps = [int(event["step"]) for event in payload["events"]]
    assert len(set(steps)) > 1

    out = capsys.readouterr().out
    assert str(events_yaml) in out
    assert str(manifest) in out


def test_optional_real_toolkit_multichord_sysex_export(tmp_path: Path):
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    song = load_song_model_yaml(EXAMPLE_PATH)
    paths = export_track8_artifacts_from_song(song, tmp_path, include_sysex=True, overwrite=True)

    assert paths.syx_path is not None
    assert paths.syx_path.exists()
    data = paths.syx_path.read_bytes()
    assert len(data) > 0
    assert data[0] == 0xF0
    assert data[-1] == 0xF7


def test_manifest_includes_multichord_counts(tmp_path: Path):
    song = load_song_model_yaml(EXAMPLE_PATH)
    paths = export_track8_artifacts_from_song(song, tmp_path, include_sysex=False, overwrite=True)

    text = paths.manifest_path.read_text(encoding="utf-8")
    assert "Track 8 chord event count" in text
    assert "Track 8 note row count" in text

    # Parse count values from deterministic manifest lines.
    lines = [line.strip() for line in text.splitlines()]
    chord_line = next(line for line in lines if line.startswith("- Track 8 chord event count:"))
    row_line = next(line for line in lines if line.startswith("- Track 8 note row count:"))

    chord_count = int(chord_line.split(":", 1)[1].strip())
    row_count = int(row_line.split(":", 1)[1].strip())

    assert chord_count == 3
    assert row_count > 6


@pytest.mark.parametrize(
    ("fixture_path", "expected_title", "expected_chord_events", "expected_note_rows"),
    [
        (MULTIBAR_PATH, "Demo Multibar Turnaround", 4, 24),
        (MULTISECTION_PATH, "Demo Multisection Form", 8, 48),
    ],
)
def test_broader_songmodel_fixtures_export_and_manifest_counts(
    fixture_path: Path,
    expected_title: str,
    expected_chord_events: int,
    expected_note_rows: int,
    tmp_path: Path,
):
    song = load_song_model_yaml(fixture_path)

    assert song.title == expected_title

    paths = export_track8_artifacts_from_song(
        song,
        tmp_path,
        name=song.title,
        include_sysex=False,
        overwrite=True,
    )

    payload = yaml.safe_load(paths.events_yaml_path.read_text(encoding="utf-8"))
    assert payload["name"] == expected_title
    assert len(payload["events"]) == expected_note_rows

    text = paths.manifest_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    chord_line = next(line for line in lines if line.startswith("- Track 8 chord event count:"))
    row_line = next(line for line in lines if line.startswith("- Track 8 note row count:"))

    chord_count = int(chord_line.split(":", 1)[1].strip())
    row_count = int(row_line.split(":", 1)[1].strip())

    assert chord_count == expected_chord_events
    assert row_count == expected_note_rows
