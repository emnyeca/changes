from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Track8ManifestInfo:
    path: Path
    source_title: str | None = None
    track8_chord_event_count: int | None = None
    track8_note_row_count: int | None = None
    sysex_size: int | None = None


@dataclass(frozen=True)
class ManifestValidationResult:
    syx_byte_count: int
    manifest_sysex_size: int | None
    source_title: str | None
    track8_chord_event_count: int | None
    track8_note_row_count: int | None
    warnings: tuple[str, ...] = ()


def _strip_bullet_prefix(line: str) -> str:
    return line.lstrip().lstrip("- ").strip()


def _parse_int_value(line: str, label: str) -> int:
    value_region = line.split(":", 1)[1] if ":" in line else line
    match = re.search(r"(-?\d+)", value_region)
    if match is None:
        raise ValueError(f"Manifest field '{label}' is malformed: {line}")
    return int(match.group(1))


def parse_track8_manifest(path: str | Path) -> Track8ManifestInfo:
    src = Path(path)
    text = src.read_text(encoding="utf-8")

    source_title: str | None = None
    chord_count: int | None = None
    note_row_count: int | None = None
    sysex_size: int | None = None

    for raw_line in text.splitlines():
        line = _strip_bullet_prefix(raw_line)
        if not line:
            continue

        lower = line.lower()

        if lower.startswith("source title:"):
            source_title = line.split(":", 1)[1].strip() or None
            continue

        if lower.startswith("source name:"):
            # Current manifest wording uses "Source name".
            source_title = line.split(":", 1)[1].strip() or None
            continue

        if "track 8 chord event count" in lower:
            chord_count = _parse_int_value(line, "Track 8 chord event count")
            continue

        if "track 8 note row count" in lower:
            note_row_count = _parse_int_value(line, "Track 8 note row count")
            continue

        if "sysex size" in lower:
            sysex_size = _parse_int_value(line, "SysEx size")
            continue

    return Track8ManifestInfo(
        path=src,
        source_title=source_title,
        track8_chord_event_count=chord_count,
        track8_note_row_count=note_row_count,
        sysex_size=sysex_size,
    )


def validate_sysex_against_manifest(
    *,
    syx_byte_count: int,
    manifest: Track8ManifestInfo,
    expected_source_title: str | None = None,
    expected_chord_event_count: int | None = None,
    expected_note_row_count: int | None = None,
) -> ManifestValidationResult:
    warnings: list[str] = []

    if manifest.sysex_size is not None and manifest.sysex_size != syx_byte_count:
        raise ValueError(
            f"manifest sysex size mismatch: expected {manifest.sysex_size}, got {syx_byte_count}"
        )

    if expected_source_title is not None:
        if manifest.source_title is None:
            warnings.append("manifest did not include source title")
        elif manifest.source_title != expected_source_title:
            raise ValueError(
                f"source title mismatch: expected {expected_source_title!r}, found {manifest.source_title!r}"
            )

    if expected_chord_event_count is not None:
        if manifest.track8_chord_event_count is None:
            warnings.append("manifest did not include Track 8 chord event count")
        elif manifest.track8_chord_event_count != expected_chord_event_count:
            raise ValueError(
                "Track 8 chord event count mismatch: "
                f"expected {expected_chord_event_count}, found {manifest.track8_chord_event_count}"
            )

    if expected_note_row_count is not None:
        if manifest.track8_note_row_count is None:
            warnings.append("manifest did not include Track 8 note row count")
        elif manifest.track8_note_row_count != expected_note_row_count:
            raise ValueError(
                "Track 8 note row count mismatch: "
                f"expected {expected_note_row_count}, found {manifest.track8_note_row_count}"
            )

    return ManifestValidationResult(
        syx_byte_count=syx_byte_count,
        manifest_sysex_size=manifest.sysex_size,
        source_title=manifest.source_title,
        track8_chord_event_count=manifest.track8_chord_event_count,
        track8_note_row_count=manifest.track8_note_row_count,
        warnings=tuple(warnings),
    )
