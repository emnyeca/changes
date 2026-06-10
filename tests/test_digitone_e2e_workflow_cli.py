from __future__ import annotations

import sys
from pathlib import Path

import pytest

from changes import cli


def _run_cli(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["changes", *args])
    cli.main()


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
    assert "SysEx" in out
    assert "--port" not in out
    assert "--real-send" not in out


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
