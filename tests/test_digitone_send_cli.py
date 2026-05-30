from __future__ import annotations

import sys
from pathlib import Path

import pytest

from changes import cli


def _run_send_cli(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["changes", "send", "digitone-syx", *args])
    cli.main()


def test_dry_run_send_succeeds_with_valid_syx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    _run_send_cli(
        monkeypatch,
        ["--syx", str(syx_path), "--port", "Digitone II", "--dry-run"],
    )

    out = capsys.readouterr().out
    assert "Dry-run SysEx send validated" in out
    assert "Digitone II" in out
    assert "bytes: 4" in out
    assert "hardware_send: no" in out


def test_missing_dry_run_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    monkeypatch.setattr(sys, "argv", ["changes", "send", "digitone-syx", "--syx", str(syx_path), "--port", "Digitone II"])

    with pytest.raises(SystemExit, match="choose one of --dry-run, --real-send, or --list-ports"):
        cli.main()


def test_invalid_syx_file_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "invalid.syx"
    syx_path.write_bytes(bytes([0x7D, 0x00, 0xF7]))

    monkeypatch.setattr(
        sys,
        "argv",
        ["changes", "send", "digitone-syx", "--syx", str(syx_path), "--port", "Digitone II", "--dry-run"],
    )

    with pytest.raises(SystemExit, match="SysEx send failed"):
        cli.main()


def test_missing_syx_file_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    syx_path = tmp_path / "missing.syx"
    monkeypatch.setattr(
        sys,
        "argv",
        ["changes", "send", "digitone-syx", "--syx", str(syx_path), "--port", "Digitone II", "--dry-run"],
    )

    with pytest.raises(SystemExit, match="SysEx send failed"):
        cli.main()


def test_argparse_requires_syx_and_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    monkeypatch.setattr(sys, "argv", ["changes", "send", "digitone-syx", "--port", "Digitone II", "--dry-run"])
    with pytest.raises(SystemExit):
        cli.main()

    monkeypatch.setattr(sys, "argv", ["changes", "send", "digitone-syx", "--syx", str(syx_path), "--dry-run"])
    with pytest.raises(SystemExit):
        cli.main()


def test_send_command_does_not_call_export_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    def _boom(*args, **kwargs):
        raise AssertionError("export path should not be called by send command")

    monkeypatch.setattr(cli, "export_track8_artifacts_from_song", _boom)
    _run_send_cli(
        monkeypatch,
        ["--syx", str(syx_path), "--port", "Digitone II", "--dry-run"],
    )


def test_send_command_does_not_require_backend_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    sys.modules.pop("mido", None)
    sys.modules.pop("rtmidi", None)
    sys.modules.pop("python-rtmidi", None)

    _run_send_cli(
        monkeypatch,
        ["--syx", str(syx_path), "--port", "Digitone II", "--dry-run"],
    )

    assert "mido" not in sys.modules
    assert "rtmidi" not in sys.modules
    assert "python-rtmidi" not in sys.modules


def test_dry_run_does_not_call_mido_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    def _boom():
        raise AssertionError("dry-run should not create mido backend")

    monkeypatch.setattr(cli, "_create_mido_backend", _boom)

    _run_send_cli(
        monkeypatch,
        ["--syx", str(syx_path), "--port", "Digitone II", "--dry-run"],
    )
