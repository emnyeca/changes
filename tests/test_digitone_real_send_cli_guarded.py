from __future__ import annotations

import sys
from pathlib import Path

import pytest

from changes import cli
from changes.digitone.transport import FakeMidiBackend, MidiBackendUnavailableError, MidiPortInfo


def _run_send_cli(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["changes", "send", "digitone-syx", *args])
    cli.main()


def test_list_ports_works_with_monkeypatched_backend(monkeypatch: pytest.MonkeyPatch, capsys):
    backend = FakeMidiBackend([MidiPortInfo(name="Digitone II"), MidiPortInfo(name="Other Port")])
    monkeypatch.setattr(cli, "_create_mido_backend", lambda: backend)

    _run_send_cli(monkeypatch, ["--list-ports"])

    out = capsys.readouterr().out
    assert "Available MIDI output ports" in out
    assert "Digitone II" in out
    assert "Other Port" in out


def test_list_ports_does_not_require_syx_or_port(monkeypatch: pytest.MonkeyPatch):
    backend = FakeMidiBackend([MidiPortInfo(name="Digitone II")])
    monkeypatch.setattr(cli, "_create_mido_backend", lambda: backend)

    _run_send_cli(monkeypatch, ["--list-ports"])


def test_list_ports_missing_backend_shows_install_hint(monkeypatch: pytest.MonkeyPatch):
    def _raise_unavailable():
        raise MidiBackendUnavailableError(
            "Mido MIDI backend is unavailable. Install optional dependencies with 'pip install .[midi]' (mido + python-rtmidi)."
        )

    monkeypatch.setattr(cli, "_create_mido_backend", _raise_unavailable)

    with pytest.raises(SystemExit, match=r"pip install \.\[midi\]"):
        _run_send_cli(monkeypatch, ["--list-ports"])


def test_missing_mode_fails(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit, match="choose exactly one of --dry-run, --real-send, or --list-ports"):
        _run_send_cli(monkeypatch, [])


def test_dry_run_and_real_send_together_fails(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit):
        _run_send_cli(monkeypatch, ["--dry-run", "--real-send"])


def test_dry_run_and_list_ports_together_fails(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit):
        _run_send_cli(monkeypatch, ["--dry-run", "--list-ports"])


def test_real_send_and_list_ports_together_fails(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit):
        _run_send_cli(monkeypatch, ["--real-send", "--list-ports"])


def test_real_send_without_confirmation_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    with pytest.raises(SystemExit, match="yes-i-understand-this-writes-to-hardware"):
        _run_send_cli(
            monkeypatch,
            ["--real-send", "--syx", str(syx_path), "--port", "Digitone II"],
        )


def test_real_send_without_port_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    with pytest.raises(SystemExit, match="--port is required"):
        _run_send_cli(
            monkeypatch,
            [
                "--real-send",
                "--syx",
                str(syx_path),
                "--yes-i-understand-this-writes-to-hardware",
            ],
        )


def test_real_send_without_syx_fails(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit, match="--syx is required"):
        _run_send_cli(
            monkeypatch,
            [
                "--real-send",
                "--port",
                "Digitone II",
                "--yes-i-understand-this-writes-to-hardware",
            ],
        )


def test_guarded_real_send_with_fake_backend_records_send(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    syx_path = tmp_path / "test.syx"
    syx_path.write_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))

    backend = FakeMidiBackend([MidiPortInfo(name="Digitone II")])
    monkeypatch.setattr(cli, "_create_mido_backend", lambda: backend)

    _run_send_cli(
        monkeypatch,
        [
            "--real-send",
            "--syx",
            str(syx_path),
            "--port",
            "Digitone II",
            "--yes-i-understand-this-writes-to-hardware",
        ],
    )

    sent = backend.sent_messages
    assert len(sent) == 1
    assert sent[0].port_name == "Digitone II"
    assert sent[0].byte_count == 4

    out = capsys.readouterr().out
    assert "Guarded real SysEx send completed" in out
    assert "hardware_send: yes" in out
    assert "warning: hardware was written" in out


