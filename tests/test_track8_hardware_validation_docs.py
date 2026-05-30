from __future__ import annotations

from pathlib import Path


def test_hardware_validation_log_exists_and_records_pass() -> None:
    path = Path("docs/hardware-validation/track8-cmaj7-changes-2026-05.md")
    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "Result: PASS" in text
    assert "Track: 8" in text
    assert "Step: 1" in text
    assert "C4 E4 G4 B4 D5 A5" in text
    assert "70 70 70 50 70 50" in text
    assert "0x4E" in text
    assert "LENGTH was not in PER TRACK mode" in text
    assert "SPEED was not in PER TRACK mode" in text
    assert "CHANGE was not in PER TRACK mode" in text
    assert "RESET was not in PER TRACK mode" in text
    assert "Track 1-7 LEN / VEL" in text


def test_followup_document_exists_and_defines_staged_plan() -> None:
    path = Path("docs/track8-product-like-pattern-settings-followup.md")
    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "PER TRACK" in text
    assert "Track 1-7" in text
    assert "Phase 4I" in text
    assert "Phase 4J" in text
    assert "Phase 4K" in text
    assert "Phase 4L" in text
    assert "template" in text
    assert "bundle planner" in text
