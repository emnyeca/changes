from __future__ import annotations

import sys

import pytest

from changes import cli


def test_send_help_includes_safety_flags(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["changes", "send", "digitone-syx", "--help"])

    with pytest.raises(SystemExit):
        cli.main()

    out = capsys.readouterr().out
    assert "--dry-run" in out
    assert "--real-send" in out
    assert "--list-ports" in out
    assert "--yes-i-understand-this-writes-to-hardware" in out
