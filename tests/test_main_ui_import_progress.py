from types import SimpleNamespace

import pytest

pytest.importorskip("streamlit")

from changes import main_ui


def test_extract_zip_optional_progress_supports_legacy_signature() -> None:
    events: list[tuple[str, int, int, str]] = []

    def legacy_extract_zip(raw: bytes) -> dict[str, bytes]:
        assert raw == b"zip"
        return {"song.musicxml": b"xml"}

    result = main_ui._extract_zip_with_optional_progress(
        legacy_extract_zip,
        b"zip",
        lambda stage, current, total, message: events.append((stage, current, total, message)),
    )

    assert result == {"song.musicxml": b"xml"}
    assert events[0][0] == "zip_open"
    assert events[-1][0] == "zip_complete"


def test_import_files_optional_progress_supports_legacy_signature() -> None:
    events: list[tuple[str, int, int, str]] = []

    def legacy_import_files(files: dict[str, bytes], default_tempo: int = 120):
        assert files == {"song.musicxml": b"xml"}
        assert default_tempo == 120
        return SimpleNamespace(songs=[object()], failed=[])

    result = main_ui._import_files_with_optional_progress(
        legacy_import_files,
        {"song.musicxml": b"xml"},
        lambda stage, current, total, message: events.append((stage, current, total, message)),
    )

    assert len(result.songs) == 1
    assert events[0][0] == "songmodel_build"
    assert events[-1][0] == "complete"
