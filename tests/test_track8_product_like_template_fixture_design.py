"""Contract tests for Phase 4K product-like template fixture design document."""

from __future__ import annotations

from pathlib import Path

DOC_FILE = (
    Path(__file__).parent.parent
    / "docs"
    / "track8-product-like-template-fixture-design.md"
)


def test_design_document_exists_and_includes_fixture_goals() -> None:
    """Design document exists and covers core product-like fixture goals."""
    assert DOC_FILE.exists(), f"Design document not found: {DOC_FILE}"
    text = DOC_FILE.read_text(encoding="utf-8")

    required_keywords = [
        "Product-like fixture goals",
        "Track 8 same-step Cmaj7",
        "PER TRACK",
        "track_scale",
        "track_defaults.velocity",
        "CHANGE",
        "RESET",
    ]
    for keyword in required_keywords:
        assert keyword in text, (
            f"Design document missing required fixture-goal keyword: {keyword!r}"
        )


def test_design_document_includes_ownership_split() -> None:
    """Design document contains all ownership boundary sections."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_sections = [
        "Template should own",
        "Events YAML should own",
        "Changes should own",
    ]
    for section in required_sections:
        assert section in text, (
            f"Design document missing ownership section: {section!r}"
        )


def test_design_document_includes_generated_file_plan() -> None:
    """Design document defines expected output directory and artifact names."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_artifacts = [
        "examples/generated/track8_product_like_validation/",
        "track8_product_like_cmaj7.events.yaml",
        "track8_product_like_cmaj7.syx",
        "track8_product_like_cmaj7_manifest.md",
    ]
    for artifact in required_artifacts:
        assert artifact in text, (
            f"Design document missing generated-file plan entry: {artifact!r}"
        )


def test_design_document_includes_spec_open_items() -> None:
    """Design document must preserve unresolved issues as SPEC-OPEN."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_spec_open_items = [
        "SPEC-OPEN",
        "1..16",
        "track_scale.length",
        "product-like template file",
    ]
    for item in required_spec_open_items:
        assert item in text, (
            f"Design document missing SPEC-OPEN item: {item!r}"
        )


def test_design_document_states_no_implementation() -> None:
    """Design document explicitly says this phase is design-only."""
    text = DOC_FILE.read_text(encoding="utf-8")

    required_phrases = [
        "does not implement",
        "does not generate product-like SysEx",
        "does not modify Changes runtime code",
        "does not modify toolkit",
    ]
    for phrase in required_phrases:
        assert phrase in text, (
            f"Design document missing non-goal phrase: {phrase!r}"
        )
