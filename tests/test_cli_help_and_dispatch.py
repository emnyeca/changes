from __future__ import annotations

import sys

import pytest

from changes import cli


def test_top_level_help_mentions_modern_commands(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "--help"])

    cli.main()

    out = capsys.readouterr().out
    assert "Modern commands:" in out
    assert "export" in out
    assert "check" in out
    assert "send" in out
    assert "digitone-product" in out
    assert "digitone-syx" in out
    assert "Legacy commands:" in out



def test_export_group_help_mentions_digitone_product(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "export", "--help"])

    cli.main()

    out = capsys.readouterr().out
    assert "Available export commands:" in out
    assert "digitone-product" in out


def test_send_group_help_mentions_digitone_syx(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "send", "--help"])

    cli.main()

    out = capsys.readouterr().out
    assert "Available send commands:" in out
    assert "digitone-syx" in out


def test_check_group_help_mentions_digitone_syx(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "check", "--help"])

    cli.main()

    out = capsys.readouterr().out
    assert "Available check commands:" in out
    assert "digitone-syx" in out


def test_modern_export_dispatch_routes_to_product_helper(monkeypatch: pytest.MonkeyPatch):
    called: dict[str, list[str]] = {}

    monkeypatch.setattr(cli, "_run_digitone_product_export_cli", lambda argv: called.setdefault("argv", argv))
    monkeypatch.setattr(sys, "argv", ["changes", "export", "digitone-product", "--input", "demo.yaml"])

    cli.main()

    assert called["argv"] == ["--input", "demo.yaml"]


def test_track8_export_command_is_not_available(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "argv", ["changes", "export", "digitone-track8", "--demo", "cmaj7"])

    with pytest.raises(SystemExit, match="Unknown export command: digitone-track8"):
        cli.main()


def test_modern_send_dispatch_routes_to_sysex_helper(monkeypatch: pytest.MonkeyPatch):
    called: dict[str, list[str]] = {}

    monkeypatch.setattr(cli, "_run_digitone_sysex_send_cli", lambda argv: called.setdefault("argv", argv))
    monkeypatch.setattr(sys, "argv", ["changes", "send", "digitone-syx", "--list-ports"])

    cli.main()

    assert called["argv"] == ["--list-ports"]


def test_modern_check_dispatch_routes_to_sysex_helper(monkeypatch: pytest.MonkeyPatch):
    called: dict[str, list[str]] = {}

    monkeypatch.setattr(cli, "_run_digitone_sysex_check_cli", lambda argv: called.setdefault("argv", argv))
    monkeypatch.setattr(sys, "argv", ["changes", "check", "digitone-syx", "--syx", "demo.syx"])

    cli.main()

    assert called["argv"] == ["--syx", "demo.syx"]
