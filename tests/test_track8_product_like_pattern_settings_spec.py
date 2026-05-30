"""Contract tests for the Track 8 product-like pattern settings specification document."""

from __future__ import annotations

from pathlib import Path

SPEC_FILE = (
    Path(__file__).parent.parent
    / "docs"
    / "track8-product-like-pattern-settings-spec.md"
)


def test_spec_file_exists_and_answers_core_decisions() -> None:
    """Spec document exists and contains all required decision keywords."""
    assert SPEC_FILE.exists(), f"Spec file not found: {SPEC_FILE}"
    text = SPEC_FILE.read_text(encoding="utf-8")

    required_keywords = [
        "PER TRACK",
        "LENGTH",
        "SPEED",
        "CHANGE",
        "RESET",
        "Track 1",
        "Track 8",
        "bundled product-like default template",
        "optional user-supplied template",
        "Bundle planner",
        "SPEC-OPEN",
        "Phase 4J",
    ]
    for keyword in required_keywords:
        assert keyword in text, (
            f"Spec file missing required keyword: {keyword!r}"
        )


def test_spec_does_not_claim_implementation() -> None:
    """Spec document explicitly lists non-goals including no implementation."""
    text = SPEC_FILE.read_text(encoding="utf-8")

    required_phrases = [
        "does not implement",
        "does not validate hardware",
        "does not modify bundle planner",
    ]
    for phrase in required_phrases:
        assert phrase in text, (
            f"Spec file missing non-goal phrase: {phrase!r}"
        )


def test_spec_defines_ownership_boundary() -> None:
    """Spec document contains all three ownership labels."""
    text = SPEC_FILE.read_text(encoding="utf-8")

    required_owners = [
        "Changes:",
        "digitone-syx-toolkit:",
        "template file:",
    ]
    for owner in required_owners:
        assert owner in text, (
            f"Spec file missing ownership boundary label: {owner!r}"
        )
