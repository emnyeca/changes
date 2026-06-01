"""Tests for importers.import_bundle — ZIP/MusicXML+MIDI pairing, tempo fallback."""

from __future__ import annotations

import io
import json
import zipfile
from fractions import Fraction
from pathlib import Path

import pytest

from changes.importers.import_bundle import (
    DEFAULT_TEMPO,
    MIDI_EXTS,
    MUSICXML_EXTS,
    ImportBundleResult,
    MidiMetadata,
    MidiUpdateCandidate,
    extract_zip,
    find_midi_update_candidates,
    group_files_by_basename,
    import_files,
    import_musicxml_with_midi,
    import_zip,
    parse_midi_metadata,
)
from changes.importers.musicxml import extract_musicxml_tempo
from changes.library import SongEntry, save_song
from changes.models.song_model import SongModel

# ── Fixture paths ──────────────────────────────────────────────────────────────

_FIXTURES = Path(__file__).parent / "fixtures" / "import_bundle"
_WITH_TEMPO_XML = (_FIXTURES / "with_tempo.musicxml").read_bytes()
_NO_TEMPO_XML   = (_FIXTURES / "no_tempo.musicxml").read_bytes()


# ── MIDI byte builder (avoids committing binary fixtures) ──────────────────────

def _make_midi(
    tempo_bpm: float | None = 120.0,
    key_sf: int = 0,
    key_minor: bool = False,
    meter: tuple[int, int] = (4, 4),
) -> bytes:
    """Build a minimal MIDI type-0 file with requested meta events."""
    import mido
    mid = mido.MidiFile(type=0)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    if meter:
        track.append(mido.MetaMessage(
            "time_signature",
            numerator=meter[0],
            denominator=meter[1],
            time=0,
        ))
    if key_sf is not None:
        track.append(mido.MetaMessage(
            "key_signature",
            key=_sf_to_key_str(key_sf, key_minor),
            time=0,
        ))
    if tempo_bpm is not None:
        us = round(60_000_000 / tempo_bpm)
        track.append(mido.MetaMessage("set_tempo", tempo=us, time=0))
    track.append(mido.MetaMessage("end_of_track", time=0))
    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()


def _sf_to_key_str(sf: int, is_minor: bool) -> str:
    sharp_maj = ["C", "G", "D", "A", "E", "B", "F#", "C#"]
    flat_maj  = ["C", "F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"]
    sharp_min = ["A", "E", "B", "F#", "C#", "G#", "D#", "A#"]
    flat_min  = ["A", "D", "G", "C", "F", "Bb", "Eb", "Ab"]
    idx = min(abs(sf), 7)
    if is_minor:
        return (sharp_min[idx] if sf >= 0 else flat_min[idx]) + "m"
    return sharp_maj[idx] if sf >= 0 else flat_maj[idx]


def _make_zip(pairs: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in pairs.items():
            zf.writestr(name, data)
    return buf.getvalue()


# ── extract_musicxml_tempo ────────────────────────────────────────────────────

def test_extract_tempo_from_sound_element() -> None:
    assert extract_musicxml_tempo(_WITH_TEMPO_XML.decode()) == 120.0


def test_extract_tempo_returns_none_when_absent() -> None:
    assert extract_musicxml_tempo(_NO_TEMPO_XML.decode()) is None


# ── parse_midi_metadata ───────────────────────────────────────────────────────

def test_midi_tempo_parsed() -> None:
    mid = _make_midi(tempo_bpm=80.0)
    meta = parse_midi_metadata(mid)
    assert meta.tempo_bpm == pytest.approx(80.0, abs=0.5)


def test_midi_key_parsed() -> None:
    mid = _make_midi(key_sf=2)
    meta = parse_midi_metadata(mid)
    assert meta.key == "D"


def test_midi_key_minor_parsed() -> None:
    mid = _make_midi(key_sf=0, key_minor=True)
    meta = parse_midi_metadata(mid)
    assert meta.key == "Am"


def test_midi_time_signature_parsed() -> None:
    mid = _make_midi(meter=(3, 4))
    meta = parse_midi_metadata(mid)
    assert meta.meter == "3/4"


def test_midi_no_tempo_returns_none() -> None:
    mid = _make_midi(tempo_bpm=None)
    meta = parse_midi_metadata(mid)
    assert meta.tempo_bpm is None


def test_midi_empty_bytes_returns_empty() -> None:
    meta = parse_midi_metadata(b"")
    assert meta.tempo_bpm is None
    assert meta.key is None
    assert meta.meter is None


# ── group_files_by_basename ───────────────────────────────────────────────────

def test_grouping_pairs_musicxml_and_midi() -> None:
    files = {
        "song-a.musicxml": b"xml",
        "song-a.mid": b"mid",
        "song-b.musicxml": b"xml2",
    }
    groups = group_files_by_basename(files)
    assert ".musicxml" in groups["song-a"]
    assert ".mid" in groups["song-a"]
    assert ".musicxml" in groups["song-b"]
    assert ".mid" not in groups["song-b"]


def test_grouping_ignores_mscx() -> None:
    files = {
        "song-a.musicxml": b"xml",
        "song-a.mscx": b"mscx",
    }
    groups = group_files_by_basename(files)
    assert ".mscx" not in groups.get("song-a", {})


def test_grouping_ignores_unknown_extensions() -> None:
    files = {"song-a.pdf": b"pdf", "song-a.musicxml": b"xml"}
    groups = group_files_by_basename(files)
    assert ".pdf" not in groups.get("song-a", {})


def test_grouping_midi_only_group_exists() -> None:
    files = {"song-a.mid": b"mid"}
    groups = group_files_by_basename(files)
    assert ".mid" in groups["song-a"]
    assert ".musicxml" not in groups["song-a"]


# ── extract_zip ───────────────────────────────────────────────────────────────

def test_extract_zip_strips_directory_prefix() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("subdir/song-a.musicxml", b"xml")
        zf.writestr("song-b.mid", b"mid")
    files = extract_zip(buf.getvalue())
    assert "song-a.musicxml" in files
    assert "song-b.mid" in files
    assert "subdir/song-a.musicxml" not in files


# ── Tempo fallback priority ───────────────────────────────────────────────────

def test_musicxml_tempo_wins_over_midi() -> None:
    # MusicXML has 120, MIDI has 80 → should use 120
    mid = _make_midi(tempo_bpm=80.0)
    c = import_musicxml_with_midi("t", _WITH_TEMPO_XML, mid, default_tempo=60)
    assert float(c.song.performance_tempo) == pytest.approx(120.0, abs=0.5)
    assert c.tempo_source == "musicxml"


def test_midi_tempo_fallback_when_xml_has_none() -> None:
    mid = _make_midi(tempo_bpm=95.0)
    c = import_musicxml_with_midi("t", _NO_TEMPO_XML, mid, default_tempo=60)
    assert float(c.song.performance_tempo) == pytest.approx(95.0, abs=0.5)
    assert c.tempo_source == "midi"


def test_default_tempo_when_both_absent() -> None:
    mid = _make_midi(tempo_bpm=None)
    c = import_musicxml_with_midi("t", _NO_TEMPO_XML, mid, default_tempo=77)
    assert float(c.song.performance_tempo) == pytest.approx(77.0, abs=0.5)
    assert c.tempo_source == "default"


def test_default_tempo_when_no_midi_at_all() -> None:
    c = import_musicxml_with_midi("t", _NO_TEMPO_XML, None, default_tempo=55)
    assert float(c.song.performance_tempo) == pytest.approx(55.0, abs=0.5)
    assert c.tempo_source == "default"


# ── Mismatch warnings ─────────────────────────────────────────────────────────

def test_key_mismatch_warning() -> None:
    # XML key = C (fifths=0), MIDI key = G (1 sharp)
    mid = _make_midi(key_sf=1)  # G major
    c = import_musicxml_with_midi("t", _WITH_TEMPO_XML, mid)
    # MusicXML key is C (fifths=0), MIDI key is G → mismatch
    assert any("key mismatch" in w for w in c.warnings)


def test_no_key_mismatch_when_same() -> None:
    mid = _make_midi(key_sf=0)  # C major matches XML (fifths=0)
    c = import_musicxml_with_midi("t", _WITH_TEMPO_XML, mid)
    assert not any("key mismatch" in w for w in c.warnings)


def test_meter_mismatch_warning() -> None:
    # XML meter = 4/4, MIDI meter = 3/4
    mid = _make_midi(meter=(3, 4))
    c = import_musicxml_with_midi("t", _WITH_TEMPO_XML, mid)
    assert any("meter mismatch" in w for w in c.warnings)


# ── import_files (batch) ──────────────────────────────────────────────────────

def test_import_files_processes_paired_group() -> None:
    mid = _make_midi(tempo_bpm=90.0)
    files = {
        "blues-a.musicxml": _NO_TEMPO_XML,
        "blues-a.mid": mid,
    }
    result = import_files(files, default_tempo=120)
    assert len(result.songs) == 1
    assert result.songs[0].tempo_source == "midi"
    assert result.tempo_source_counts["midi"] == 1


def test_import_files_skips_midi_only_group() -> None:
    mid = _make_midi(tempo_bpm=90.0)
    files = {"midi-only.mid": mid}
    result = import_files(files)
    assert len(result.songs) == 0


def test_import_files_musicxml_without_midi() -> None:
    files = {"alone.musicxml": _WITH_TEMPO_XML}
    result = import_files(files)
    assert len(result.songs) == 1
    assert result.tempo_source_counts["musicxml"] == 1


def test_import_files_collects_failed() -> None:
    files = {"broken.musicxml": b"not xml at all"}
    result = import_files(files)
    assert len(result.failed) == 1
    assert result.failed[0][0] == "broken"


# ── import_zip ────────────────────────────────────────────────────────────────

def test_import_zip_pairs_xml_and_mid() -> None:
    mid = _make_midi(tempo_bpm=100.0)
    zb = _make_zip({
        "blue-moon.musicxml": _NO_TEMPO_XML,
        "blue-moon.mid": mid,
        "blue-moon.mscx": b"mscx_ignored",
    })
    result = import_zip(zb)
    assert len(result.songs) == 1
    assert result.songs[0].tempo_source == "midi"


def test_import_zip_invalid_bytes() -> None:
    result = import_zip(b"not a zip")
    assert len(result.failed) == 1


def test_import_zip_tempo_source_counts() -> None:
    mid_with = _make_midi(tempo_bpm=110.0)
    mid_none = _make_midi(tempo_bpm=None)
    zb = _make_zip({
        "a.musicxml": _WITH_TEMPO_XML,   # tempo from xml
        "b.musicxml": _NO_TEMPO_XML,     # no tempo, no midi → default
        "c.musicxml": _NO_TEMPO_XML,     # no tempo, has midi → midi
        "c.mid": mid_with,
        "d.musicxml": _NO_TEMPO_XML,     # has midi but no tempo → default
        "d.mid": mid_none,
    })
    result = import_zip(zb, default_tempo=120)
    sc = result.tempo_source_counts
    assert sc.get("musicxml", 0) == 1
    assert sc.get("midi", 0) == 1
    assert sc.get("default", 0) == 2


# ── import_zip vs real sample ─────────────────────────────────────────────────

_SAMPLE_ZIP = Path(__file__).parent.parent / "examples" / "musicXML" / "ireal-musicxml" / "blues-50.zip"


@pytest.mark.skipif(not _SAMPLE_ZIP.exists(), reason="blues-50.zip not present")
def test_import_zip_real_sample_smoke() -> None:
    result = import_zip(_SAMPLE_ZIP.read_bytes())
    assert len(result.songs) > 0
    assert len(result.songs) + len(result.failed) > 0
    total = sum(result.tempo_source_counts.values())
    assert total == len(result.songs)


# ── find_midi_update_candidates ───────────────────────────────────────────────

def _make_song_entry(title: str, tempo: float, tmp_path: Path) -> SongEntry:
    song = SongModel(title=title, working_key="C", performance_tempo=Fraction(tempo), measures=[])
    path = save_song(tmp_path, song, mode="keep_both")
    return SongEntry(path=path, title=title, song=song)


def test_midi_update_matches_by_basename(tmp_path: Path) -> None:
    entry = _make_song_entry("Blue Moon", 120.0, tmp_path)
    mid = _make_midi(tempo_bpm=140.0)
    candidates, unmatched = find_midi_update_candidates(
        {"blue_moon.mid": mid}, [entry]
    )
    assert len(candidates) == 1
    assert candidates[0].old_tempo == pytest.approx(120.0)
    assert candidates[0].new_tempo == pytest.approx(140.0, abs=0.5)
    assert not unmatched


def test_midi_update_matches_by_title(tmp_path: Path) -> None:
    entry = _make_song_entry("All The Things You Are", 200.0, tmp_path)
    mid = _make_midi(tempo_bpm=180.0)
    candidates, _ = find_midi_update_candidates(
        {"all_the_things_you_are.mid": mid}, [entry]
    )
    assert len(candidates) == 1


def test_midi_update_unmatched_when_no_library_entry(tmp_path: Path) -> None:
    entry = _make_song_entry("Autumn Leaves", 120.0, tmp_path)
    mid = _make_midi(tempo_bpm=130.0)
    candidates, unmatched = find_midi_update_candidates(
        {"completely_different_name.mid": mid}, [entry]
    )
    assert not candidates
    assert len(unmatched) == 1


def test_midi_update_unmatched_when_no_tempo_in_midi(tmp_path: Path) -> None:
    entry = _make_song_entry("Blue Moon", 120.0, tmp_path)
    mid = _make_midi(tempo_bpm=None)
    candidates, unmatched = find_midi_update_candidates(
        {"blue_moon.mid": mid}, [entry]
    )
    assert not candidates
    assert unmatched[0][1] == "no tempo information in MIDI"


def test_midi_update_skips_non_midi_files(tmp_path: Path) -> None:
    entry = _make_song_entry("Blue Moon", 120.0, tmp_path)
    candidates, unmatched = find_midi_update_candidates(
        {"blue_moon.musicxml": b"xml"}, [entry]
    )
    assert not candidates
    assert not unmatched


# ── ImportBundleResult tempo_source_counts integrity ─────────────────────────

def test_tempo_source_counts_sum_equals_songs() -> None:
    mid = _make_midi(tempo_bpm=90.0)
    files = {
        "a.musicxml": _WITH_TEMPO_XML,
        "b.musicxml": _NO_TEMPO_XML,
        "b.mid": mid,
        "c.musicxml": _NO_TEMPO_XML,
    }
    result = import_files(files, default_tempo=120)
    total = sum(result.tempo_source_counts.values())
    assert total == len(result.songs)
