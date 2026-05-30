from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/track8-explicit-export-command-design.md")


def test_design_document_exists():
    assert DOC_PATH.exists(), f"Missing document: {DOC_PATH}"


def test_document_includes_proposed_command_and_artifacts():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "changes export digitone-track8" in text
    assert ".events.yaml" in text
    assert ".syx" in text
    assert "manifest.md" in text
    assert "product-like" in text


def test_document_includes_dependency_direction():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "changes -> digitone-syx-toolkit" in text
    assert "changes -> MIDI transport backend" in text
    assert "digitone-syx-toolkit must not import Changes" in text


def test_document_includes_future_send_boundary():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "send" in text
    assert "MIDI" in text
    assert "transport" in text
    assert "separate send subcommand" in text


def test_document_includes_spec_open_and_non_goals():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "SPEC-OPEN" in text
    assert "does not" in text
    assert "implement CLI" in text
    assert "implement MIDI send" in text
    assert "modify toolkit" in text
    assert "perform monorepo migration" in text
