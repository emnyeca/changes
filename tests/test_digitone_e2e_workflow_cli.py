from __future__ import annotations

import sys
from pathlib import Path

import pytest

from changes import cli


EXAMPLE_PATH = Path("examples/song_models/demo_ii_v_i.changes.yaml")
MULTIBAR_FIXTURE_PATH = Path("examples/song_models/demo_multibar_turnaround.changes.yaml")


def _run_cli(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["changes", *args])
    cli.main()


def test_export_check_dry_run_e2e_without_hardware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    output_dir = tmp_path / "digitone-track8"
    syx_path = output_dir / "changes_track8_export.syx"
    manifest_path = output_dir / "changes_track8_export_manifest.md"

    _run_cli(
        monkeypatch,
        [
            "export",
            "digitone-track8",
            "--input",
            str(EXAMPLE_PATH),
            "--output-dir",
            str(output_dir),
            "--basename",
            "changes_track8_export",
            "--overwrite",
        ],
    )

    assert (output_dir / "changes_track8_export.events.yaml").exists()
    assert syx_path.exists()
    assert manifest_path.exists()

    sys.modules.pop("mido", None)
    sys.modules.pop("rtmidi", None)
    sys.modules.pop("python-rtmidi", None)

    _run_cli(
        monkeypatch,
        [
            "check",
            "digitone-syx",
            "--syx",
            str(syx_path),
            "--manifest",
            str(manifest_path),
            "--expect-source-title",
            "Demo II V I",
            "--expect-chord-events",
            "3",
            "--expect-note-rows",
            "18",
        ],
    )
    check_out = capsys.readouterr().out
    assert "Digitone SysEx file validated" in check_out
    assert "valid: yes" in check_out
    assert "Manifest validation:" in check_out
    assert "manifest_match: yes" in check_out
    assert "source_title: Demo II V I" in check_out

    _run_cli(
        monkeypatch,
        [
            "send",
            "digitone-syx",
            "--syx",
            str(syx_path),
            "--port",
            "Digitone II",
            "--dry-run",
        ],
    )

    dry_run_out = capsys.readouterr().out
    assert "Dry-run SysEx send validated" in dry_run_out
    assert "hardware_send: no" in dry_run_out
    assert "mido" not in sys.modules
    assert "rtmidi" not in sys.modules


def test_check_rejects_invalid_syx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "invalid.syx"
    path.write_bytes(bytes([0x7D, 0x00, 0xF7]))

    with pytest.raises(SystemExit, match="SysEx check failed"):
        _run_cli(monkeypatch, ["check", "digitone-syx", "--syx", str(path)])


def test_check_help_contains_syx_and_not_send_flags(monkeypatch: pytest.MonkeyPatch, capsys):
    with pytest.raises(SystemExit):
        _run_cli(monkeypatch, ["check", "digitone-syx", "--help"])

    out = capsys.readouterr().out
    assert "--syx" in out
    assert "--manifest" in out
    assert "--expect-source-title" in out
    assert "--expect-chord-events" in out
    assert "--expect-note-rows" in out
    assert "SysEx" in out
    assert "--port" not in out
    assert "--real-send" not in out


def test_check_manifest_size_mismatch_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "valid.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    manifest_path = tmp_path / "manifest.md"
    manifest_path.write_text("SysEx size: 999\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="Manifest validation failed"):
        _run_cli(
            monkeypatch,
            [
                "check",
                "digitone-syx",
                "--syx",
                str(syx_path),
                "--manifest",
                str(manifest_path),
            ],
        )


def test_check_command_remains_mido_free(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "valid.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    sys.modules.pop("mido", None)
    sys.modules.pop("rtmidi", None)
    sys.modules.pop("python-rtmidi", None)

    _run_cli(monkeypatch, ["check", "digitone-syx", "--syx", str(syx_path)])

    assert "mido" not in sys.modules
    assert "rtmidi" not in sys.modules
    assert "python-rtmidi" not in sys.modules


def test_multibar_fixture_export_check_manifest_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    output_dir = tmp_path / "digitone-track8"
    syx_path = output_dir / "multibar.syx"
    manifest_path = output_dir / "multibar_manifest.md"

    _run_cli(
        monkeypatch,
        [
            "export",
            "digitone-track8",
            "--input",
            str(MULTIBAR_FIXTURE_PATH),
            "--output-dir",
            str(output_dir),
            "--basename",
            "multibar",
            "--overwrite",
        ],
    )

    assert syx_path.exists()
    assert manifest_path.exists()

    sys.modules.pop("mido", None)
    sys.modules.pop("rtmidi", None)
    sys.modules.pop("python-rtmidi", None)

    _run_cli(
        monkeypatch,
        [
            "check",
            "digitone-syx",
            "--syx",
            str(syx_path),
            "--manifest",
            str(manifest_path),
            "--expect-source-title",
            "Demo Multibar Turnaround",
            "--expect-chord-events",
            "4",
            "--expect-note-rows",
            "24",
        ],
    )

    check_out = capsys.readouterr().out
    assert "Manifest validation:" in check_out
    assert "manifest_match: yes" in check_out

    _run_cli(
        monkeypatch,
        [
            "send",
            "digitone-syx",
            "--syx",
            str(syx_path),
            "--port",
            "Digitone II",
            "--dry-run",
        ],
    )

    dry_run_out = capsys.readouterr().out
    assert "hardware_send: no" in dry_run_out
    assert "mido" not in sys.modules
