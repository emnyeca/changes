from __future__ import annotations

from pathlib import Path

DOC_PATH = Path("docs/hardware-validation/track8-product-like-cmaj7-2026-05.md")


def test_product_like_hardware_validation_log_exists_and_records_pass():
    assert DOC_PATH.exists(), f"Missing hardware validation log: {DOC_PATH}"
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Result: PASS" in text
    assert "product-like Track 8 Cmaj7" in text
    assert "PER TRACK" in text
    assert "CHANGE: OFF" in text
    assert "RESET: INF" in text

    assert (
        "Track 1-8 LENGTH: 16" in text
        or "Track 1\u20138 LENGTH: 16" in text
    )
    assert (
        "Track 1-8 SPEED: 1/8" in text
        or "Track 1\u20138 SPEED: 1/8" in text
    )
    assert (
        "Track 9-16 LENGTH: 16" in text
        or "Track 9\u201316 LENGTH: 16" in text
    )
    assert (
        "Track 9-16 SPEED: 1" in text
        or "Track 9\u201316 SPEED: 1" in text
    )
    assert (
        "Track 1-7 default velocities" in text
        or "Track 1\u20137 default velocities" in text
    )


def test_log_records_track8_chord_contract():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Track: 8" in text
    assert "Step: 1" in text
    assert "C4 E4 G4 B4 D5 A5" in text
    assert "70 70 70 50 70 50" in text
    assert "Cmaj7 voicing sounded as expected" in text


def test_log_records_length_interpretation_correctly():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "length_code: 0x4E" in text
    assert "16" in text
    assert "sixteenth-note units" in text
    assert "does not claim that the hardware UI displays the internal hex code" in text


def test_log_states_scope_limitations():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "does not validate" in text
    assert "complete song export" in text
    assert "bundle planner" in text
    assert "UI workflow" in text
    assert "all chord qualities" in text
    assert "all keys" in text
    assert "all durations" in text
