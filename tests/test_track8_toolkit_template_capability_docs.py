"""Contract tests for the Track 8 toolkit/template capability-check document."""

from __future__ import annotations

from pathlib import Path

DOC_FILE = (
    Path(__file__).parent.parent
    / "docs"
    / "track8-toolkit-template-capability-check.md"
)


def test_capability_document_exists() -> None:
    """Capability-check document must exist."""
    assert DOC_FILE.exists(), f"Capability document not found: {DOC_FILE}"


def test_document_includes_required_capability_topics() -> None:
    """Document must contain key capability terms and API hooks."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_keywords = [
        "PER TRACK",
        "LENGTH",
        "SPEED",
        "CHANGE",
        "RESET",
        "track_defaults.velocity",
        "template_file",
        "build_syx_from_events",
        "Track 1-7",
        "Track 8",
        "Recommendation",
    ]
    for keyword in required_keywords:
        assert keyword in text, (
            f"Capability document missing required keyword: {keyword!r}"
        )


def test_document_includes_explicit_findings() -> None:
    """Document must include explicit Finding 1..7 sections."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_findings = [
        "Finding 1",
        "Finding 2",
        "Finding 3",
        "Finding 4",
        "Finding 5",
        "Finding 6",
        "Finding 7",
    ]
    for finding in required_findings:
        assert finding in text, (
            f"Capability document missing finding heading: {finding!r}"
        )


def test_document_states_no_implementation_in_this_phase() -> None:
    """Document must clearly state inspection-only non-goals."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_phrases = [
        "does not implement",
        "does not modify toolkit",
        "does not modify Changes runtime code",
    ]
    for phrase in required_phrases:
        assert phrase in text, (
            f"Capability document missing non-goal phrase: {phrase!r}"
        )


def test_document_references_key_toolkit_files() -> None:
    """Document should reference core inspected toolkit files."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_files = [
        "events_yaml.py",
        "events_to_syx.py",
        "builder.py",
    ]
    for file_name in required_files:
        assert file_name in text, (
            f"Capability document missing toolkit file reference: {file_name!r}"
        )
