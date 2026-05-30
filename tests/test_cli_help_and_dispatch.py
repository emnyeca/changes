from __future__ import annotations

import sys
from pathlib import Path

import pytest

from changes import cli


DOC_ENTRYPOINTS = [
    Path("docs/index.md"),
    Path("docs/cli.md"),
    Path("docs/generated-artifacts-policy.md"),
    Path("docs/manifest-aware-validation.md"),
]


def test_top_level_help_mentions_modern_commands(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "--help"])

    cli.main()

    out = capsys.readouterr().out
    assert "Modern commands:" in out
    assert "export" in out
    assert "check" in out
    assert "send" in out
    assert "digitone-track8" in out
    assert "digitone-syx" in out
    assert "Legacy commands:" in out


def test_export_help_mentions_track8_artifacts(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "export", "digitone-track8", "--help"])

    with pytest.raises(SystemExit):
        cli.main()

    out = capsys.readouterr().out
    assert "Digitone II Track 8 artifacts" in out
    assert "SongModel YAML v1" in out
    assert "--input" in out
    assert "--events-yaml-only" in out
    assert "--overwrite" in out
    assert "--send" not in out


def test_export_group_help_mentions_digitone_track8(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "export", "--help"])

    cli.main()

    out = capsys.readouterr().out
    assert "Available export commands:" in out
    assert "digitone-track8" in out


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


def test_modern_export_dispatch_routes_to_track8_helper(monkeypatch: pytest.MonkeyPatch):
    called: dict[str, list[str]] = {}

    monkeypatch.setattr(cli, "_run_track8_export_cli", lambda argv: called.setdefault("argv", argv))
    monkeypatch.setattr(sys, "argv", ["changes", "export", "digitone-track8", "--demo", "cmaj7"])

    cli.main()

    assert called["argv"] == ["--demo", "cmaj7"]


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


def test_docs_entrypoints_exist():
    for path in DOC_ENTRYPOINTS:
        assert path.exists(), f"Expected documentation entrypoint to exist: {path}"
