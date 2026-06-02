"""Tests for key_signature helpers and SongModel working_key_mode integration."""

from __future__ import annotations

import pytest

from changes.key_signature import format_working_key, parse_working_key_display
from changes.models.song_model import SongModel, song_model_from_dict, song_model_to_dict


# ── format_working_key ────────────────────────────────────────────────────────

class TestFormatWorkingKey:
    def test_major(self):
        assert format_working_key("C", "major") == "C"

    def test_minor(self):
        assert format_working_key("E", "minor") == "Em"

    def test_unknown_mode(self):
        assert format_working_key("F", None) == "F?"

    def test_no_key(self):
        assert format_working_key(None, None) == "-"

    def test_no_key_with_mode(self):
        assert format_working_key(None, "major") == "-"

    def test_invalid_mode_treated_as_unknown(self):
        assert format_working_key("C", "dorian") == "C?"

    def test_sharp_minor(self):
        assert format_working_key("F#", "minor") == "F#m"

    def test_flat_major(self):
        assert format_working_key("Bb", "major") == "Bb"


# ── parse_working_key_display ─────────────────────────────────────────────────

class TestParseWorkingKeyDisplay:
    # Empty / unknown inputs
    def test_empty(self):
        assert parse_working_key_display("") == (None, None)

    def test_dash(self):
        assert parse_working_key_display("-") == (None, None)

    def test_question_mark(self):
        assert parse_working_key_display("?") == (None, None)

    # Major
    def test_plain_c(self):
        assert parse_working_key_display("C") == ("C", "major")

    def test_cmaj(self):
        assert parse_working_key_display("Cmaj") == ("C", "major")

    def test_cmajor(self):
        assert parse_working_key_display("Cmajor") == ("C", "major")

    def test_cm_uppercase(self):
        assert parse_working_key_display("CM") == ("C", "major")

    # Minor
    def test_em(self):
        assert parse_working_key_display("Em") == ("E", "minor")

    def test_eminor(self):
        assert parse_working_key_display("Eminor") == ("E", "minor")

    def test_e_dash(self):
        assert parse_working_key_display("E-") == ("E", "minor")

    def test_fsharp_minor(self):
        assert parse_working_key_display("F#m") == ("F#", "minor")

    def test_bb_major(self):
        assert parse_working_key_display("Bb") == ("Bb", "major")

    def test_db_minor(self):
        assert parse_working_key_display("Dbm") == ("Db", "minor")

    # Unknown mode
    def test_c_question(self):
        assert parse_working_key_display("C?") == ("C", None)

    def test_fsharp_question(self):
        assert parse_working_key_display("F#?") == ("F#", None)

    # Case insensitivity for tonic
    def test_lowercase_tonic(self):
        assert parse_working_key_display("c") == ("C", "major")

    def test_lowercase_eb(self):
        assert parse_working_key_display("ebm") == ("Eb", "minor")

    # Invalid inputs
    def test_invalid_returns_none(self):
        assert parse_working_key_display("xyz") == (None, None)

    def test_invalid_suffix(self):
        assert parse_working_key_display("Cxyz") == (None, None)

    # Whitespace stripping
    def test_strip_whitespace(self):
        assert parse_working_key_display("  Em  ") == ("E", "minor")


# ── Round-trip ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("key,mode,display", [
    ("C", "major", "C"),
    ("E", "minor", "Em"),
    ("F#", "minor", "F#m"),
    ("Bb", "major", "Bb"),
    ("Ab", "minor", "Abm"),
    ("C", None, "C?"),
])
def test_round_trip(key, mode, display):
    assert format_working_key(key, mode) == display
    parsed_key, parsed_mode = parse_working_key_display(display)
    assert parsed_key == key
    assert parsed_mode == mode


# ── SongModel serialization ───────────────────────────────────────────────────

def _make_song(working_key, working_key_mode):
    return SongModel(
        title="Test",
        working_key=working_key,
        working_key_mode=working_key_mode,
        performance_tempo=120,
        measures=(),
    )


def test_song_model_serializes_minor_mode():
    song = _make_song("E", "minor")
    d = song_model_to_dict(song)
    assert d["working_key"] == "E"
    assert d["working_key_mode"] == "minor"


def test_song_model_serializes_major_mode():
    song = _make_song("C", "major")
    d = song_model_to_dict(song)
    assert d["working_key_mode"] == "major"


def test_song_model_serializes_none_mode():
    song = _make_song("C", None)
    d = song_model_to_dict(song)
    assert d["working_key_mode"] is None


def test_song_model_deserializes_minor_mode():
    d = {"title": "T", "working_key": "E", "working_key_mode": "minor",
         "performance_tempo": "120", "measures": []}
    song = song_model_from_dict(d)
    assert song.working_key == "E"
    assert song.working_key_mode == "minor"


def test_song_model_deserializes_missing_mode_as_none():
    """Old JSON without working_key_mode defaults to None."""
    d = {"title": "T", "working_key": "C", "performance_tempo": "120", "measures": []}
    song = song_model_from_dict(d)
    assert song.working_key_mode is None


def test_song_model_serialization_round_trip():
    song = _make_song("F#", "minor")
    restored = song_model_from_dict(song_model_to_dict(song))
    assert restored.working_key == "F#"
    assert restored.working_key_mode == "minor"
