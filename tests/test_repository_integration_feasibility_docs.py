from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/repository-integration-feasibility.md")


def test_feasibility_document_exists():
    assert DOC_PATH.exists(), f"Missing document: {DOC_PATH}"


def test_document_includes_options_a_to_e():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Option A" in text
    assert "Option B" in text
    assert "Option C" in text
    assert "Option D" in text
    assert "Option E" in text


def test_document_includes_key_concepts():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "changes -> digitone-syx-toolkit" in text
    assert "monorepo" in text
    assert "separate Python packages" in text
    assert "pinned dependency" in text
    assert "vendor" in text
    assert "submodule" in text
    assert "CI" in text
    assert "rollback" in text
    assert "SPEC-OPEN" in text


def test_document_includes_recommendation():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Short term" in text
    assert "Medium term" in text
    assert "Do not perform monorepo migration before Phase 5A" in text
    assert "Preserve import boundary" in text
    assert "digitone_syx_toolkit" in text


def test_document_states_non_goals():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "does not" in text
    assert "move repositories" in text
    assert "change imports" in text
    assert "vendor toolkit code" in text
    assert "modify runtime code" in text
