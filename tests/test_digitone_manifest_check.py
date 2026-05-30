from __future__ import annotations

from pathlib import Path

import pytest

from changes.digitone.manifest_check import (
    Track8ManifestInfo,
    parse_track8_manifest,
    validate_sysex_against_manifest,
)


def test_parse_current_style_manifest(tmp_path: Path):
    path = tmp_path / "manifest.md"
    path.write_text(
        "\n".join(
            [
                "Source title: Demo II V I",
                "Track 8 chord event count: 3",
                "Track 8 note row count: 18",
                "SysEx size: 114118",
            ]
        ),
        encoding="utf-8",
    )

    info = parse_track8_manifest(path)

    assert info.source_title == "Demo II V I"
    assert info.track8_chord_event_count == 3
    assert info.track8_note_row_count == 18
    assert info.sysex_size == 114118


def test_parse_retained_manifest_style_with_source_name_and_size_bytes(tmp_path: Path):
    path = tmp_path / "manifest.md"
    path.write_text(
        "\n".join(
            [
                "- Source name: Demo II V I",
                "- Track 8 chord event count: 3",
                "- Track 8 note row count: 18",
                "- SysEx size bytes: 114118",
            ]
        ),
        encoding="utf-8",
    )

    info = parse_track8_manifest(path)

    assert info.source_title == "Demo II V I"
    assert info.track8_chord_event_count == 3
    assert info.track8_note_row_count == 18
    assert info.sysex_size == 114118


def test_parse_sysex_size_with_bytes_suffix(tmp_path: Path):
    path = tmp_path / "manifest.md"
    path.write_text("SysEx size: 114118 bytes\n", encoding="utf-8")

    info = parse_track8_manifest(path)

    assert info.sysex_size == 114118


def test_parse_tolerates_missing_fields(tmp_path: Path):
    path = tmp_path / "manifest.md"
    path.write_text("Source name: Demo II V I\n", encoding="utf-8")

    info = parse_track8_manifest(path)

    assert info.source_title == "Demo II V I"
    assert info.track8_chord_event_count is None
    assert info.track8_note_row_count is None
    assert info.sysex_size is None


def test_parse_malformed_numeric_field_fails(tmp_path: Path):
    path = tmp_path / "manifest.md"
    path.write_text("Track 8 note row count: eighteen\n", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed"):
        parse_track8_manifest(path)


def test_validate_sysex_byte_count_match_succeeds():
    manifest = Track8ManifestInfo(path=Path("manifest.md"), sysex_size=114118)

    result = validate_sysex_against_manifest(syx_byte_count=114118, manifest=manifest)

    assert result.manifest_sysex_size == 114118
    assert result.warnings == ()


def test_validate_sysex_byte_count_mismatch_fails():
    manifest = Track8ManifestInfo(path=Path("manifest.md"), sysex_size=114118)

    with pytest.raises(ValueError, match="sysex size mismatch"):
        validate_sysex_against_manifest(syx_byte_count=10, manifest=manifest)


def test_validate_expected_source_title_mismatch_fails():
    manifest = Track8ManifestInfo(path=Path("manifest.md"), source_title="Demo II V I")

    with pytest.raises(ValueError, match="source title mismatch"):
        validate_sysex_against_manifest(
            syx_byte_count=1,
            manifest=manifest,
            expected_source_title="Other",
        )


def test_validate_expected_chord_event_count_mismatch_fails():
    manifest = Track8ManifestInfo(path=Path("manifest.md"), track8_chord_event_count=3)

    with pytest.raises(ValueError, match="chord event count mismatch"):
        validate_sysex_against_manifest(
            syx_byte_count=1,
            manifest=manifest,
            expected_chord_event_count=4,
        )


def test_validate_expected_note_row_count_mismatch_fails():
    manifest = Track8ManifestInfo(path=Path("manifest.md"), track8_note_row_count=18)

    with pytest.raises(ValueError, match="note row count mismatch"):
        validate_sysex_against_manifest(
            syx_byte_count=1,
            manifest=manifest,
            expected_note_row_count=24,
        )


def test_validate_missing_expected_source_title_becomes_warning():
    manifest = Track8ManifestInfo(path=Path("manifest.md"))

    result = validate_sysex_against_manifest(
        syx_byte_count=1,
        manifest=manifest,
        expected_source_title="Demo II V I",
    )

    assert "manifest did not include source title" in result.warnings


def test_validate_missing_expected_chord_count_becomes_warning():
    manifest = Track8ManifestInfo(path=Path("manifest.md"), source_title="Demo II V I")

    result = validate_sysex_against_manifest(
        syx_byte_count=1,
        manifest=manifest,
        expected_chord_event_count=3,
    )

    assert "manifest did not include Track 8 chord event count" in result.warnings


def test_validate_missing_expected_count_becomes_warning():
    manifest = Track8ManifestInfo(path=Path("manifest.md"), source_title="Demo II V I")

    result = validate_sysex_against_manifest(
        syx_byte_count=1,
        manifest=manifest,
        expected_note_row_count=18,
    )

    assert "manifest did not include Track 8 note row count" in result.warnings


def test_validate_without_optional_expectations_keeps_warnings_empty():
    manifest = Track8ManifestInfo(
        path=Path("manifest.md"),
        source_title="Demo II V I",
        track8_chord_event_count=3,
        track8_note_row_count=18,
    )

    result = validate_sysex_against_manifest(
        syx_byte_count=114118,
        manifest=manifest,
    )

    assert result.warnings == ()
