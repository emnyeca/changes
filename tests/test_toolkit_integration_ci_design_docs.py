from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/toolkit-integration-ci-design.md")


def test_ci_design_document_exists():
    assert DOC_PATH.exists(), f"Missing document: {DOC_PATH}"


def test_document_includes_current_toolkit_dependent_tests():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "test_track8_toolkit_loader_validation.py" in text
    assert "test_track8_sysex_export.py" in text
    assert "test_track8_fixture_generation.py" in text
    assert "test_track8_product_like_fixture_generation.py" in text


def test_document_includes_options_a_to_e():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Option A" in text
    assert "Option B" in text
    assert "Option C" in text
    assert "Option D" in text
    assert "Option E" in text


def test_document_includes_proposed_ci_job_concepts():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "toolkit-integration" in text
    assert "actions/checkout@v4" in text
    assert "actions/setup-python@v5" in text
    assert "digitone-syx-toolkit" in text
    assert "workflow_dispatch" in text


def test_document_includes_failure_ref_and_local_workflow_policies():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Branch/ref policy" in text
    assert "Failure policy" in text
    assert "Local developer workflow" in text
    assert "toolkit_ref" in text
    assert "advisory" in text


def test_document_states_non_goals():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "does not" in text
    assert "modify GitHub Actions" in text
    assert "modify runtime code" in text
    assert "modify toolkit" in text
    assert "change test behavior" in text
