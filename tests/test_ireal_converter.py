"""Tests for the bundled ireal-musicxml subprocess wrapper.

All subprocess interaction is mocked so CI does not need Node or the bundled
converter. The final test runs the real converter and is skipped when the
bundled tool is not staged (scripts/PrepareBundledIRealMusicXML.ps1).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from changes.importers import ireal_converter as ic

REPO_ROOT = Path(__file__).resolve().parent.parent
SINGLE_SAMPLE = REPO_ROOT / "examples" / "iRealb" / "single-Tonal Cycle of 5ths in 12 Keys.html"


def _wrapper_json(*songs: tuple[str, str]) -> bytes:
    return json.dumps(
        {"songs": [{"title": t, "musicxml": x} for t, x in songs]}
    ).encode("utf-8")


def _fake_tools(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        ic, "_resolve_tools",
        lambda: (tmp_path / "node.exe", tmp_path / "wrapper.mjs", tmp_path / "lib.mjs"),
    )


def _fake_run(monkeypatch, *, returncode=0, stdout=b"", stderr=b"", record=None):
    def run(args, **kwargs):
        if record is not None:
            record.append(args)
        return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(ic.subprocess, "run", run)


# ── Tool resolver ─────────────────────────────────────────────────────────────

def test_env_var_override_resolves_tools(monkeypatch, tmp_path):
    node = tmp_path / "node.exe"
    node.write_bytes(b"")
    ireal_dir = tmp_path / "ireal"
    lib = ireal_dir / "build" / "ireal-musicxml.mjs"
    lib.parent.mkdir(parents=True)
    lib.write_text("export {}", encoding="utf-8")

    monkeypatch.setenv(ic.NODE_EXE_ENV, str(node))
    monkeypatch.setenv(ic.IREAL_MUSICXML_DIR_ENV, str(ireal_dir))

    assert ic.find_node_exe() == node
    assert ic.find_ireal_musicxml_lib() == lib


def test_missing_tools_raise_user_readable_error(monkeypatch, tmp_path):
    # Env vars pointing at nonexistent paths fail closed (no silent fallback).
    monkeypatch.setenv(ic.NODE_EXE_ENV, str(tmp_path / "missing-node.exe"))
    monkeypatch.setenv(ic.IREAL_MUSICXML_DIR_ENV, str(tmp_path / "missing-dir"))

    assert ic.find_node_exe() is None
    assert ic.find_ireal_musicxml_lib() is None
    assert not ic.bundled_ireal_available()

    with pytest.raises(ic.IRealToolNotFoundError) as exc_info:
        ic.convert_ireal_playlist_to_musicxml("irealb://whatever")
    assert "iReal converter is not available" in exc_info.value.message


# ── Subprocess wrapper ────────────────────────────────────────────────────────

def test_successful_conversion_returns_songs_and_warnings(monkeypatch, tmp_path):
    _fake_tools(monkeypatch, tmp_path)
    _fake_run(
        monkeypatch,
        stdout=_wrapper_json(("Song A", "<score-partwise/>"), ("Song B", "<score-partwise/>")),
        stderr="[ireal-musicxml] [Song A#3] Unhandled alternate chord\n\n".encode("utf-8"),
    )

    conversion = ic.convert_ireal_playlist_to_musicxml("irealb://input")

    assert [s.source_label for s in conversion.songs] == ["Song A", "Song B"]
    assert conversion.songs[0].musicxml_text == "<score-partwise/>"
    assert conversion.warnings == ("[ireal-musicxml] [Song A#3] Unhandled alternate chord",)


def test_nonzero_exit_is_import_error_with_stderr_details(monkeypatch, tmp_path):
    _fake_tools(monkeypatch, tmp_path)
    _fake_run(monkeypatch, returncode=1, stderr=b"[eub-ireal-wrapper] Input does not look like iReal Pro data")

    with pytest.raises(ic.IRealConversionError) as exc_info:
        ic.convert_ireal_playlist_to_musicxml("not ireal at all")
    assert "Invalid iReal input" in exc_info.value.message
    assert "does not look like iReal Pro data" in exc_info.value.details


def test_timeout_raises_short_message(monkeypatch, tmp_path):
    _fake_tools(monkeypatch, tmp_path)

    def run(args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr(ic.subprocess, "run", run)

    with pytest.raises(ic.IRealConversionError) as exc_info:
        ic.convert_ireal_playlist_to_musicxml("irealb://input", timeout_seconds=5)
    assert "timed out" in exc_info.value.message


def test_empty_stdout_is_no_musicxml_error(monkeypatch, tmp_path):
    _fake_tools(monkeypatch, tmp_path)
    _fake_run(monkeypatch, stdout=b"", stderr=b"")

    with pytest.raises(ic.IRealConversionError) as exc_info:
        ic.convert_ireal_playlist_to_musicxml("irealb://input")
    assert "no MusicXML" in exc_info.value.message


def test_input_temp_file_is_cleaned_up(monkeypatch, tmp_path):
    _fake_tools(monkeypatch, tmp_path)
    recorded: list[list[str]] = []
    _fake_run(monkeypatch, stdout=_wrapper_json(("Song A", "<x/>")), record=recorded)

    ic.convert_ireal_playlist_to_musicxml("irealb://input")

    input_path = Path(recorded[0][recorded[0].index("--input") + 1])
    assert not input_path.exists()
    assert not input_path.parent.exists()


def test_single_song_api_selector_and_playlist_guard(monkeypatch, tmp_path):
    _fake_tools(monkeypatch, tmp_path)
    _fake_run(monkeypatch, stdout=_wrapper_json(("Blues One", "<a/>"), ("Waltz Two", "<b/>")))

    selected = ic.convert_ireal_to_musicxml("irealb://input", song_selector="waltz")
    assert selected.source_label == "Waltz Two"
    assert selected.musicxml_text == "<b/>"

    with pytest.raises(ic.IRealConversionError) as exc_info:
        ic.convert_ireal_to_musicxml("irealb://input")
    assert "no song was selected" in exc_info.value.message


# ── Import pipeline bridge ────────────────────────────────────────────────────

def test_expand_ireal_inputs_replaces_html_with_musicxml(monkeypatch):
    conversion = ic.IRealPlaylistConversion(
        songs=(
            ic.IRealConversionResult("<a/>", (), "Song: A/B"),
            ic.IRealConversionResult("<b/>", (), "Song: A/B"),
        ),
        warnings=("warn line",),
    )
    monkeypatch.setattr(ic, "convert_ireal_playlist_to_musicxml", lambda text, **kw: conversion)

    files, warnings, failed = ic.expand_ireal_inputs(
        {"playlist.html": b"<html/>", "other.musicxml": b"<keep/>"}
    )

    assert files["other.musicxml"] == b"<keep/>"
    # Unsafe filename chars sanitized; duplicate titles deduped.
    assert files["Song_ A_B.musicxml"] == b"<a/>"
    assert files["Song_ A_B (2).musicxml"] == b"<b/>"
    assert warnings == [("playlist.html", "warn line")]
    assert failed == []


def test_expand_ireal_inputs_survives_missing_tool(monkeypatch):
    def raise_not_found(text, **kw):
        raise ic.IRealToolNotFoundError("iReal converter is not available.")

    monkeypatch.setattr(ic, "convert_ireal_playlist_to_musicxml", raise_not_found)

    files, warnings, failed = ic.expand_ireal_inputs({"song.html": b"<html/>"})

    assert files == {}
    assert warnings == []
    assert failed == [("song.html", "iReal converter is not available.")]


# ── Import UI flow (_start_import) ────────────────────────────────────────────

_MINIMAL_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
    <work><work-title>iReal UI Song</work-title></work>
    <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
    <part id="P1">
        <measure number="1">
            <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
            <harmony>
                <root><root-step>C</root-step></root>
                <kind text="7">dominant</kind>
            </harmony>
        </measure>
    </part>
</score-partwise>
"""


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def _patched_main_ui(monkeypatch, tmp_path):
    pytest.importorskip("streamlit")
    from types import SimpleNamespace

    from changes import main_ui

    state = _SessionState({"_settings": SimpleNamespace(library_path=str(tmp_path / "library"))})
    monkeypatch.setattr(main_ui.st, "session_state", state)
    return main_ui, state


def test_start_import_html_with_unavailable_converter_does_not_crash(monkeypatch, tmp_path):
    main_ui, state = _patched_main_ui(monkeypatch, tmp_path)

    def raise_not_found(text, **kw):
        raise ic.IRealToolNotFoundError("iReal converter is not available.")

    monkeypatch.setattr(ic, "convert_ireal_playlist_to_musicxml", raise_not_found)

    main_ui._start_import([{"name": "song.html", "data": b"<html/>"}])

    result = state["_import_result"]
    assert result["ok"] == 0
    assert result["failed"][0][0] == "song.html"
    assert "iReal converter is not available" in result["failed"][0][1]


def test_start_import_html_saves_converted_song_to_library(monkeypatch, tmp_path):
    main_ui, state = _patched_main_ui(monkeypatch, tmp_path)

    conversion = ic.IRealPlaylistConversion(
        songs=(ic.IRealConversionResult(_MINIMAL_MUSICXML, (), "iReal UI Song"),),
        warnings=("[ireal-musicxml] [iReal UI Song] sample warning",),
    )
    monkeypatch.setattr(ic, "convert_ireal_playlist_to_musicxml", lambda text, **kw: conversion)

    main_ui._start_import([{"name": "song.html", "data": b"<html/>"}])

    result = state["_import_result"]
    assert result["ok"] == 1
    assert result["failed"] == []
    saved = list((tmp_path / "library").glob("*"))
    assert len(saved) == 1
    bundle_result = state["_import_bundle_result"]
    assert any("sample warning" in w.message for w in bundle_result.warnings)


# ── Optional: real converter end-to-end ───────────────────────────────────────

@pytest.mark.skipif(not ic.bundled_ireal_available(), reason="bundled ireal-musicxml not available")
def test_real_converter_single_song_imports_to_song_model():
    from changes.importers.import_bundle import import_files

    ireal_html = SINGLE_SAMPLE.read_bytes()
    files, warnings, failed = ic.expand_ireal_inputs({SINGLE_SAMPLE.name: ireal_html})

    assert failed == []
    assert len(files) == 1

    result = import_files(files)
    assert len(result.songs) == 1
    assert result.failed == []
    candidate = result.songs[0]
    assert candidate.song.title == "Tonal Cycle of 5ths in 12 Keys"
    assert len(candidate.song.measures) > 0
