from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/track8-export-cli-readiness.md")


def test_readiness_doc_contains_required_statements():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Ready as an explicit artifact export command" in text
    assert "Not yet ready as a complete end-user application workflow" in text
    assert "does not" in text
    assert "send MIDI" in text
    assert "SongModel YAML v1" in text
    assert "--input" in text
    assert "--demo cmaj7" in text
    assert "RC-ready for the controlled II-V-I workflow" in text
    assert "Prioritize validation breadth and documentation clarity" in text
