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
    IREAL_JAZZ_STYLE_DEFAULT_TEMPO,
    MIDI_EXTS,
    MUSICXML_EXTS,
    ImportBundleResult,
    MidiMetadata,
    MidiUpdateCandidate,
    _midi_working_key,
    _musicxml_working_key,
    choose_import_tempo,
    choose_midi_only_update_tempo,
    extract_zip,
    find_midi_update_candidates,
    group_files_by_basename,
    ireal_style_default_tempo,
    import_files,
    import_musicxml_with_midi,
    import_zip,
    parse_midi_metadata,
)
from changes.importers.musicxml import extract_musicxml_groove, extract_musicxml_tempo
from changes.library import SongEntry, save_song
from changes.models.song_model import SongModel

# ── Fixture paths ──────────────────────────────────────────────────────────────

_FIXTURES = Path(__file__).parent / "fixtures" / "import_bundle"
_WITH_TEMPO_XML = (_FIXTURES / "with_tempo.musicxml").read_bytes()
_NO_TEMPO_XML   = (_FIXTURES / "no_tempo.musicxml").read_bytes()


# ── MIDI byte builder (avoids committing binary fixtures) ──────────────────────

def _make_midi(
    tempo_bpm: float | None = 120.0,
    key_sf: int | None = 0,
    key_minor: bool = False,
    meter: tuple[int, int] | None = (4, 4),
) -> bytes:
    """Build a minimal MIDI type-0 file without external dependencies.

    Uses the MIDI binary format directly so the test suite works even
    when the optional 'midi' extras (mido) are not installed in CI.
    """
    _DENOM_BYTE = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5}

    def _vlq(n: int) -> bytes:
        if n == 0:
            return b"\x00"
        parts: list[int] = []
        while n:
            parts.append(n & 0x7F)
            n >>= 7
        parts.reverse()
        for i in range(len(parts) - 1):
            parts[i] |= 0x80
        return bytes(parts)

    def _meta(type_byte: int, data: bytes) -> bytes:
        return b"\x00\xFF" + bytes([type_byte]) + _vlq(len(data)) + data

    track = b""
    if meter is not None:
        db = _DENOM_BYTE.get(meter[1], 2)
        track += _meta(0x58, bytes([meter[0], db, 24, 8]))
    if key_sf is not None:
        sf_byte = key_sf & 0xFF  # two's complement unsigned representation
        track += _meta(0x59, bytes([sf_byte, 1 if key_minor else 0]))
    if tempo_bpm is not None:
        us = round(60_000_000 / tempo_bpm)
        track += _meta(0x51, us.to_bytes(3, "big"))
    track += _meta(0x2F, b"")  # end of track

    header = (
        b"MThd"
        + (6).to_bytes(4, "big")
        + (0).to_bytes(2, "big")   # format 0
        + (1).to_bytes(2, "big")   # 1 track
        + (480).to_bytes(2, "big") # 480 PPQ
    )
    chunk = b"MTrk" + len(track).to_bytes(4, "big") + track
    return header + chunk


def _make_zip(pairs: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in pairs.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_musicxml_with_groove(groove: str, *, include_tempo: float | None = None) -> bytes:
        tempo_attr = f' tempo="{include_tempo}"' if include_tempo is not None else ""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
    <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
    <part id="P1">
        <measure number="1">
            <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
            <direction>
                <sound{tempo_attr}>
                    <play>
                        <other-play type="groove">{groove}</other-play>
                    </play>
                </sound>
            </direction>
            <harmony>
                <root><root-step>C</root-step></root>
                <kind text="7">dominant</kind>
            </harmony>
        </measure>
    </part>
</score-partwise>
"""
        return xml.encode("utf-8")


# ── extract_musicxml_tempo ────────────────────────────────────────────────────

def test_extract_tempo_from_sound_element() -> None:
    assert extract_musicxml_tempo(_WITH_TEMPO_XML.decode()) == 120.0


def test_extract_tempo_returns_none_when_absent() -> None:
    assert extract_musicxml_tempo(_NO_TEMPO_XML.decode()) is None


def test_extract_musicxml_groove_reads_other_play_groove() -> None:
    xml = _make_musicxml_with_groove("Ballad")
    assert extract_musicxml_groove(xml.decode("utf-8")) == "Ballad"


def test_extract_musicxml_groove_strips_whitespace() -> None:
    xml = _make_musicxml_with_groove("   Medium Swing   ")
    assert extract_musicxml_groove(xml.decode("utf-8")) == "Medium Swing"


def test_extract_musicxml_groove_returns_none_when_absent() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <harmony><root><root-step>C</root-step></root><kind text="7">dominant</kind></harmony>
    </measure>
  </part>
</score-partwise>
"""
    assert extract_musicxml_groove(xml.decode("utf-8")) is None


@pytest.mark.parametrize(
    ("style", "expected_tempo"),
    [
        ("Ballad", 60),
        ("Medium Swing", 120),
        ("Medium Up Swing", 160),
        ("Up Tempo Swing", 240),
        ("Bossa Nova", 140),
        ("Slow Swing", 80),
    ],
)
def test_ireal_style_default_mapping(style: str, expected_tempo: int) -> None:
    canonical, tempo = ireal_style_default_tempo(style)
    assert canonical == style
    assert tempo == float(expected_tempo)
    assert IREAL_JAZZ_STYLE_DEFAULT_TEMPO[style] == expected_tempo


def test_ireal_style_mapping_normalization_is_case_and_whitespace_tolerant() -> None:
    canonical, tempo = ireal_style_default_tempo("   mEdIUm   sWinG   ")
    assert canonical == "Medium Swing"
    assert tempo == 120.0


@pytest.mark.parametrize(
    ("musicxml_tempo", "style_default_tempo", "midi_tempo", "default_tempo", "expected"),
    [
        (None, 60.0, 120.0, 120, (60.0, "style_default")),
        (None, 60.0, 95.0, 120, (95.0, "midi")),
        (100.0, 60.0, None, 120, (100.0, "musicxml")),
        (120.0, 120.0, 120.0, 120, (120.0, "midi")),
        (None, 120.0, None, 120, (120.0, "style_default")),
        (None, None, None, 120, (120.0, "default")),
    ],
)
def test_choose_import_tempo_rule(
    musicxml_tempo: float | None,
    style_default_tempo: float | None,
    midi_tempo: float | None,
    default_tempo: int,
    expected: tuple[float, str],
) -> None:
    assert choose_import_tempo(
        musicxml_tempo=musicxml_tempo,
        style_default_tempo=style_default_tempo,
        midi_tempo=midi_tempo,
        default_tempo=default_tempo,
    ) == expected


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


def test_extract_zip_reports_progress_stages() -> None:
    events: list[tuple[str, int, int, str]] = []
    callback = lambda stage, current, total, message: events.append((stage, current, total, message))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("subdir/song-a.musicxml", b"xml")
        zf.writestr("song-b.mid", b"mid")

    files = extract_zip(buf.getvalue(), progress_callback=callback)

    stages = [stage for stage, _, _, _ in events]
    assert files["song-a.musicxml"] == b"xml"
    assert "zip_open" in stages
    assert "zip_scan" in stages
    assert "zip_read" in stages
    assert stages[-1] == "zip_complete"


# ── Tempo fallback priority ───────────────────────────────────────────────────

def test_non_120_midi_wins_when_musicxml_is_120() -> None:
    # MusicXML has 120, MIDI has 80 -> non-120 preference picks MIDI.
    mid = _make_midi(tempo_bpm=80.0)
    c = import_musicxml_with_midi("t", _WITH_TEMPO_XML, mid, default_tempo=60)
    assert float(c.song.performance_tempo) == pytest.approx(80.0, abs=0.5)
    assert c.tempo_source == "midi"


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


def test_groove_ballad_with_midi_120_uses_style_default_60() -> None:
    xml = _make_musicxml_with_groove("Ballad")
    mid = _make_midi(tempo_bpm=120.0)
    c = import_musicxml_with_midi("ballad", xml, mid, default_tempo=120)
    assert float(c.song.performance_tempo) == pytest.approx(60.0, abs=0.5)
    assert c.tempo_source == "style_default"


def test_groove_medium_up_swing_with_midi_120_uses_style_default_160() -> None:
    xml = _make_musicxml_with_groove("Medium Up Swing")
    mid = _make_midi(tempo_bpm=120.0)
    c = import_musicxml_with_midi("mus", xml, mid, default_tempo=120)
    assert float(c.song.performance_tempo) == pytest.approx(160.0, abs=0.5)
    assert c.tempo_source == "style_default"


def test_groove_medium_swing_120_with_midi_120_prefers_midi_tiebreak() -> None:
    xml = _make_musicxml_with_groove("Medium Swing")
    mid = _make_midi(tempo_bpm=120.0)
    c = import_musicxml_with_midi("ms", xml, mid, default_tempo=120)
    assert float(c.song.performance_tempo) == pytest.approx(120.0, abs=0.5)
    assert c.tempo_source == "midi"


def test_unknown_groove_with_midi_120_falls_back_to_midi_and_warns() -> None:
    xml = _make_musicxml_with_groove("Totally Unknown Style")
    mid = _make_midi(tempo_bpm=120.0)
    c = import_musicxml_with_midi("unk", xml, mid, default_tempo=120)
    assert float(c.song.performance_tempo) == pytest.approx(120.0, abs=0.5)
    assert c.tempo_source == "midi"
    assert any("Unsupported iReal style default tempo" in w for w in c.warnings)


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


# ── _midi_working_key ─────────────────────────────────────────────────────────

def test_midi_working_key_major() -> None:
    assert _midi_working_key("C") == ("C", "major")

def test_midi_working_key_flat_major() -> None:
    assert _midi_working_key("Bb") == ("Bb", "major")

def test_midi_working_key_minor() -> None:
    assert _midi_working_key("Em") == ("E", "minor")

def test_midi_working_key_sharp_minor() -> None:
    assert _midi_working_key("F#m") == ("F#", "minor")

def test_midi_working_key_none() -> None:
    assert _midi_working_key(None) == (None, None)


# ── working_key_mode on imported SongModel ────────────────────────────────────

def test_import_sets_major_mode() -> None:
    # with_tempo.musicxml has fifths=0 (no mode element → defaults to major)
    c = import_musicxml_with_midi("t", _WITH_TEMPO_XML)
    assert c.song.working_key == "C"
    assert c.song.working_key_mode == "major"


_NO_KEY_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work><work-title>No Key Song</work-title></work>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <harmony><root><root-step>C</root-step></root><kind>major</kind></harmony>
      <note><duration>16</duration></note>
    </measure>
  </part>
</score-partwise>
"""


def test_import_minor_mode_from_midi() -> None:
    # No XML key → MIDI key Am (minor) is used as fallback
    mid = _make_midi(key_sf=0, key_minor=True)
    c = import_musicxml_with_midi("t", _NO_KEY_XML, mid)
    assert c.song.working_key == "A"
    assert c.song.working_key_mode == "minor"


def test_key_mismatch_includes_mode_in_warning() -> None:
    # XML C major, MIDI Am — same tonic, different mode → mismatch
    mid = _make_midi(key_sf=0, key_minor=True)
    c = import_musicxml_with_midi("t", _WITH_TEMPO_XML, mid)
    assert any("key mismatch" in w for w in c.warnings)
    # Warning should include mode info ("C" vs "Am" display)
    warning_text = " ".join(c.warnings)
    assert "major" in warning_text or "minor" in warning_text or "Am" in warning_text


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


def test_import_files_reports_songmodel_progress_stages() -> None:
    events: list[tuple[str, int, int, str]] = []
    callback = lambda stage, current, total, message: events.append((stage, current, total, message))
    files = {"alone.musicxml": _WITH_TEMPO_XML}

    result = import_files(files, progress_callback=callback)

    stages = [stage for stage, _, _, _ in events]
    assert len(result.songs) == 1
    assert "scan_files" in stages
    assert "parse_file" in stages
    assert "songmodel_build" in stages
    assert "validation" in stages
    assert stages[-1] == "complete"


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
    events: list[tuple[str, int, int, str]] = []
    callback = lambda stage, current, total, message: events.append((stage, current, total, message))
    result = import_zip(b"not a zip", progress_callback=callback)
    assert len(result.failed) == 1
    assert events[-1][0] == "error"


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
    assert sc.get("style_default", 0) == 0
    assert sc.get("midi", 0) == 1
    assert sc.get("default", 0) == 2


def test_import_zip_uses_style_default_for_ballad_and_up_tempo_swing() -> None:
    mid_120 = _make_midi(tempo_bpm=120.0)
    zb = _make_zip(
        {
            "ballad.musicxml": _make_musicxml_with_groove("Ballad"),
            "ballad.mid": mid_120,
            "up.musicxml": _make_musicxml_with_groove("Up Tempo Swing"),
            "up.mid": mid_120,
        }
    )

    result = import_zip(zb, default_tempo=120)

    assert len(result.failed) == 0
    assert len(result.songs) == 2

    by_name = {s.source_name: s for s in result.songs}
    assert float(by_name["ballad"].song.performance_tempo) == pytest.approx(60.0, abs=0.5)
    assert by_name["ballad"].tempo_source == "style_default"

    assert float(by_name["up"].song.performance_tempo) == pytest.approx(240.0, abs=0.5)
    assert by_name["up"].tempo_source == "style_default"

    assert result.tempo_source_counts.get("style_default", 0) == 2


def test_import_zip_accepts_no_chord_harmony_without_failure() -> None:
        nc_xml = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<score-partwise version=\"4.0\">
    <part-list><score-part id=\"P1\"><part-name>Music</part-name></score-part></part-list>
    <part id=\"P1\">
        <measure number=\"1\">
            <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
            <harmony><kind text=\"N.C.\">none</kind></harmony>
            <harmony><root><root-step>C</root-step></root><kind text=\"7\">dominant</kind></harmony>
        </measure>
    </part>
</score-partwise>
"""
        zb = _make_zip({"nc-case.musicxml": nc_xml})

        result = import_zip(zb)

        assert len(result.failed) == 0
        assert len(result.songs) == 1
        harmony_symbols = [h.symbol for m in result.songs[0].song.measures for h in m.harmony]
        assert harmony_symbols == ["N.C.", "C7"]


# ── import_zip vs real sample ─────────────────────────────────────────────────

# blues-50.zip is gitignored (real song data). Copy it to
# examples/musicXML/ireal-musicxml/ locally to run this smoke test.
_SAMPLE_ZIP = Path(__file__).parent.parent / "examples" / "musicXML" / "ireal-musicxml" / "blues-50.zip"


@pytest.mark.skipif(not _SAMPLE_ZIP.exists(), reason="blues-50.zip not present (gitignored local sample)")
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
    candidates, kept, unmatched = find_midi_update_candidates(
        {"blue_moon.mid": mid}, [entry]
    )
    assert len(candidates) == 1
    assert len(kept) == 0
    assert candidates[0].old_tempo == pytest.approx(120.0)
    assert candidates[0].new_tempo == pytest.approx(140.0, abs=0.5)
    assert not unmatched


def test_midi_update_matches_by_title(tmp_path: Path) -> None:
    entry = _make_song_entry("All The Things You Are", 200.0, tmp_path)
    mid = _make_midi(tempo_bpm=180.0)
    candidates, kept, _ = find_midi_update_candidates(
        {"all_the_things_you_are.mid": mid}, [entry]
    )
    assert len(candidates) == 1
    assert len(kept) == 0


def test_midi_update_unmatched_when_no_library_entry(tmp_path: Path) -> None:
    entry = _make_song_entry("Autumn Leaves", 120.0, tmp_path)
    mid = _make_midi(tempo_bpm=130.0)
    candidates, kept, unmatched = find_midi_update_candidates(
        {"completely_different_name.mid": mid}, [entry]
    )
    assert not candidates
    assert not kept
    assert len(unmatched) == 1


def test_midi_update_unmatched_when_no_tempo_in_midi(tmp_path: Path) -> None:
    entry = _make_song_entry("Blue Moon", 120.0, tmp_path)
    mid = _make_midi(tempo_bpm=None)
    candidates, kept, unmatched = find_midi_update_candidates(
        {"blue_moon.mid": mid}, [entry]
    )
    assert not candidates
    assert not kept
    assert unmatched[0][1] == "no tempo information in MIDI"


def test_midi_update_skips_non_midi_files(tmp_path: Path) -> None:
    entry = _make_song_entry("Blue Moon", 120.0, tmp_path)
    candidates, kept, unmatched = find_midi_update_candidates(
        {"blue_moon.musicxml": b"xml"}, [entry]
    )
    assert not candidates
    assert not kept
    assert not unmatched


@pytest.mark.parametrize(
    ("existing", "midi", "expected_tempo", "expected_source"),
    [
        (60.0, 120.0, 60.0, "existing"),
        (120.0, 60.0, 60.0, "midi"),
        (100.0, 95.0, 95.0, "midi"),
        (120.0, 120.0, 120.0, "midi"),
        (60.0, 60.0, 60.0, "midi"),
    ],
)
def test_choose_midi_only_update_tempo(
    existing: float,
    midi: float,
    expected_tempo: float,
    expected_source: str,
) -> None:
    tempo, source = choose_midi_only_update_tempo(existing_tempo=existing, midi_tempo=midi)
    assert tempo == pytest.approx(expected_tempo)
    assert source == expected_source


def test_midi_update_keeps_existing_when_existing_non120_and_midi_is_120(tmp_path: Path) -> None:
    entry = _make_song_entry("A Blossom Fell", 60.0, tmp_path)
    mid = _make_midi(tempo_bpm=120.0)

    updates, kept, unmatched = find_midi_update_candidates({"a_blossom_fell.mid": mid}, [entry])

    assert len(updates) == 0
    assert len(kept) == 1
    assert kept[0].existing_tempo == pytest.approx(60.0)
    assert kept[0].midi_tempo == pytest.approx(120.0)
    assert "MIDI 120 ignored" in kept[0].reason
    assert not unmatched


def test_midi_update_uses_midi_non120_when_existing_is_120(tmp_path: Path) -> None:
    entry = _make_song_entry("Boom Boom", 120.0, tmp_path)
    mid = _make_midi(tempo_bpm=166.0)

    updates, kept, unmatched = find_midi_update_candidates({"boom_boom.mid": mid}, [entry])

    assert len(updates) == 1
    assert updates[0].old_tempo == pytest.approx(120.0)
    assert updates[0].new_tempo == pytest.approx(166.0, abs=0.5)
    assert len(kept) == 0
    assert not unmatched


def test_midi_update_kept_when_tempos_are_equal(tmp_path: Path) -> None:
    entry = _make_song_entry("No Change", 60.0, tmp_path)
    mid = _make_midi(tempo_bpm=60.0)

    updates, kept, unmatched = find_midi_update_candidates({"no_change.mid": mid}, [entry])

    assert len(updates) == 0
    assert len(kept) == 1
    assert kept[0].reason == "unchanged"
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
