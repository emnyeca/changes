from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from changes import cli


def _demo_song_yaml_path() -> str:
    return "examples/song_models/demo_cmaj7.changes.yaml"


def test_demo_cmaj7_events_yaml_only_export_succeeds_without_toolkit(tmp_path: Path, monkeypatch, capsys):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
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
    assert payload["device"] == "digitone2"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["events"]
    assert all(event["track"] == 8 for event in payload["events"])

    out = capsys.readouterr().out
    assert str(events_yaml) in out
    assert str(manifest) in out


def test_overwrite_protection(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )
    cli.main()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )
    with pytest.raises(SystemExit, match="Chord export failed \(Digitone Track 8\)"):
        cli.main()


def test_overwrite_allowed(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )
    cli.main()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
            "--overwrite",
        ],
    )
    cli.main()

    assert (output_dir / "changes_track8_export.events.yaml").exists()
    assert (output_dir / "changes_track8_export_manifest.md").exists()


def test_unsupported_demo_fails(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "unknown",
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )

    with pytest.raises(SystemExit, match="Unsupported demo"):
        cli.main()


def test_monkeypatched_sysex_generation_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from changes.digitone import track8_export_api as export_api_module

    output_dir = tmp_path / "out"
    fake_syx = bytes([0xF0, 0x7D, 0x00, 0xF7])
    monkeypatch.setattr(export_api_module, "generate_track8_sysex_bytes_with_toolkit", lambda _yaml: fake_syx)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ],
    )

    cli.main()

    syx = output_dir / "changes_track8_export.syx"
    manifest = output_dir / "changes_track8_export_manifest.md"

    assert syx.exists()
    assert syx.read_bytes() == fake_syx
    assert manifest.exists()
    assert "SysEx generated: yes" in manifest.read_text(encoding="utf-8")


def test_optional_real_toolkit_cli_export(tmp_path: Path, monkeypatch):
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ],
    )

    cli.main()

    syx = output_dir / "changes_track8_export.syx"
    assert syx.exists()
    data = syx.read_bytes()
    assert data[0] == 0xF0
    assert data[-1] == 0xF7


def test_input_yaml_events_yaml_only_export_succeeds_without_toolkit(tmp_path: Path, monkeypatch, capsys):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            _demo_song_yaml_path(),
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
    assert payload["device"] == "digitone2"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["events"]
    assert [event["note"] for event in payload["events"]] == ["C4", "E4", "G4", "B4", "D5", "A5"]

    out = capsys.readouterr().out
    assert str(events_yaml) in out
    assert str(manifest) in out


def test_demo_and_input_are_mutually_exclusive(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--input",
            _demo_song_yaml_path(),
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )

    with pytest.raises(SystemExit):
        cli.main()


def test_missing_both_demo_and_input_fails(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )

    with pytest.raises(SystemExit):
        cli.main()


def test_invalid_input_file_fails_clearly(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    bad_input = tmp_path / "invalid.changes.yaml"
    bad_input.write_text("version: 1\ntype: changes.song\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            str(bad_input),
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )

    with pytest.raises(SystemExit, match="Chord export failed \(Digitone Track 8\)"):
        cli.main()


def test_input_yaml_overwrite_behavior(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            _demo_song_yaml_path(),
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )
    cli.main()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            _demo_song_yaml_path(),
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )
    with pytest.raises(SystemExit, match="Chord export failed \(Digitone Track 8\)"):
        cli.main()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            _demo_song_yaml_path(),
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
            "--overwrite",
        ],
    )
    cli.main()

    assert (output_dir / "changes_track8_export.events.yaml").exists()
    assert (output_dir / "changes_track8_export_manifest.md").exists()


def test_optional_real_toolkit_input_export(tmp_path: Path, monkeypatch):
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            _demo_song_yaml_path(),
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ],
    )

    cli.main()

    syx = output_dir / "changes_track8_export.syx"
    assert syx.exists()
    data = syx.read_bytes()
    assert data[0] == 0xF0
    assert data[-1] == 0xF7


def test_input_yaml_default_name_uses_song_title(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            _demo_song_yaml_path(),
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )

    cli.main()

    events_yaml = output_dir / "changes_track8_export.events.yaml"
    payload = yaml.safe_load(events_yaml.read_text(encoding="utf-8"))
    assert payload["name"] == "Demo Cmaj7"


def test_demo_default_name_uses_song_title(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--demo",
            "cmaj7",
            "--output-dir",
            str(output_dir),
            "--events-yaml-only",
        ],
    )

    cli.main()

    events_yaml = output_dir / "changes_track8_export.events.yaml"
    payload = yaml.safe_load(events_yaml.read_text(encoding="utf-8"))
    assert payload["name"] == "Demo Cmaj7"


def test_explicit_name_overrides_song_title(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--input",
            _demo_song_yaml_path(),
            "--output-dir",
            str(output_dir),
            "--name",
            "Custom Pattern Name",
            "--events-yaml-only",
        ],
    )

    cli.main()

    events_yaml = output_dir / "changes_track8_export.events.yaml"
    payload = yaml.safe_load(events_yaml.read_text(encoding="utf-8"))
    assert payload["name"] == "Custom Pattern Name"


def test_help_mentions_songmodel_yaml_v1_and_track8_flags(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "export",
            "digitone-track8",
            "--help",
        ],
    )

    with pytest.raises(SystemExit):
        cli.main()

    out = capsys.readouterr().out
    assert "SongModel YAML v1" in out
    assert "--input" in out
    assert "--demo" in out
    assert "--events-yaml-only" in out
