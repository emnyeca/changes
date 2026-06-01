"""Tests for save_song keep_both / overwrite modes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from changes.library import SONG_SUFFIX, save_song
from changes.models.song_model import SongModel, song_model_from_dict


def _song(title: str) -> SongModel:
    return SongModel(title=title, working_key="C", performance_tempo=120, measures=[])


def _read_title(path: Path) -> str:
    return song_model_from_dict(json.loads(path.read_text(encoding="utf-8"))).title


# ── keep_both ────────────────────────────────────────────────────────────────

def test_keep_both_saves_to_fresh_path(tmp_path: Path) -> None:
    song = _song("Blue Moon")
    p = save_song(tmp_path, song, mode="keep_both")
    assert p.exists()
    assert _read_title(p) == "Blue Moon"


def test_keep_both_never_overwrites_existing(tmp_path: Path) -> None:
    song = _song("Blue Moon")
    p1 = save_song(tmp_path, song, mode="keep_both")
    p2 = save_song(tmp_path, song, mode="keep_both")
    assert p1 != p2
    assert p1.exists()
    assert p2.exists()


def test_keep_both_deduplicates_with_numeric_suffix(tmp_path: Path) -> None:
    song = _song("Blue Moon")
    paths = [save_song(tmp_path, song, mode="keep_both") for _ in range(3)]
    names = {p.name for p in paths}
    assert f"Blue Moon{SONG_SUFFIX}" in names
    assert f"Blue Moon (2){SONG_SUFFIX}" in names
    assert f"Blue Moon (3){SONG_SUFFIX}" in names


# ── overwrite ────────────────────────────────────────────────────────────────

def test_overwrite_rewrites_existing_title(tmp_path: Path) -> None:
    original = _song("Blue Moon")
    p_orig = save_song(tmp_path, original, mode="keep_both")

    updated = SongModel(title="Blue Moon", working_key="F", performance_tempo=100, measures=[])
    p_back = save_song(tmp_path, updated, mode="overwrite")

    assert p_back == p_orig
    saved = song_model_from_dict(json.loads(p_orig.read_text(encoding="utf-8")))
    assert saved.working_key == "F"
    # Only one file exists
    assert len(list(tmp_path.glob(f"*{SONG_SUFFIX}"))) == 1


def test_overwrite_creates_new_when_no_match(tmp_path: Path) -> None:
    song = _song("Brand New Song")
    p = save_song(tmp_path, song, mode="overwrite")
    assert p.exists()
    assert _read_title(p) == "Brand New Song"


def test_overwrite_does_not_touch_other_songs(tmp_path: Path) -> None:
    save_song(tmp_path, _song("Song A"), mode="keep_both")
    save_song(tmp_path, _song("Song B"), mode="keep_both")
    updated_a = SongModel(title="Song A", working_key="G", performance_tempo=80, measures=[])
    save_song(tmp_path, updated_a, mode="overwrite")

    files = list(tmp_path.glob(f"*{SONG_SUFFIX}"))
    assert len(files) == 2


def test_overwrite_finds_non_canonical_filename(tmp_path: Path) -> None:
    # First keep_both creates "Song A.song.json"
    # Second keep_both creates "Song A (2).song.json" for same title
    song = _song("Song A")
    p1 = save_song(tmp_path, song, mode="keep_both")
    p2 = save_song(tmp_path, song, mode="keep_both")

    # overwrite should hit the first file it finds (p1 alphabetically)
    updated = SongModel(title="Song A", working_key="Bb", performance_tempo=90, measures=[])
    p_out = save_song(tmp_path, updated, mode="overwrite")
    assert p_out in (p1, p2)
    assert song_model_from_dict(json.loads(p_out.read_text(encoding="utf-8"))).working_key == "Bb"
