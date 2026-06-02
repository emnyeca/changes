"""Tests for newly supported chord kinds: m11, maj13, aug, 5, 11."""

from __future__ import annotations

import pytest

from changes.chord_parser import parse_chord_core
from changes.chord_engine import construct_chord_pitch_classes
from changes.harmonic_context import (
    chord_tone_pitch_classes,
    hard_context_pitch_classes,
    output_chord_tone_names,
    resolve_scale_collection_with_retry,
)
from changes.importers.import_bundle import import_files

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _pc_names(pcs) -> list[str]:
    return sorted(_NOTE_NAMES[pc % 12] for pc in pcs)


# ── chord_parser ──────────────────────────────────────────────────────────────

class TestChordParserNewKinds:
    def test_cm11(self):
        core = parse_chord_core("Cm11")
        assert core.normalized_quality == "m11"
        assert core.base_quality == "minor"
        assert core.seventh_type == "b7"
        assert {"7", "9", "11"}.issubset(core.extensions)

    def test_cmaj13(self):
        core = parse_chord_core("Cmaj13")
        assert core.normalized_quality == "maj13"
        assert core.base_quality == "major"
        assert core.seventh_type == "maj7"
        assert {"7", "9", "13"}.issubset(core.extensions)

    def test_caug(self):
        core = parse_chord_core("Caug")
        assert core.normalized_quality == "aug"
        assert core.special_semantic_tag == "augmented"

    def test_c5(self):
        core = parse_chord_core("C5")
        assert core.normalized_quality == "5"
        assert core.special_semantic_tag == "power"

    def test_c11(self):
        core = parse_chord_core("C11")
        assert core.normalized_quality == "11"
        assert core.special_semantic_tag == "sus"

    def test_slash_bass_power(self):
        core = parse_chord_core("C5/G")
        assert core.normalized_quality == "5"
        assert core.slash_bass == "G"

    def test_sharp_root_minor11(self):
        core = parse_chord_core("F#m11")
        assert core.root == "F#"
        assert core.normalized_quality == "m11"

    def test_flat_root_aug(self):
        core = parse_chord_core("Bbaug")
        assert core.root == "Bb"
        assert core.normalized_quality == "aug"


# ── MusicXML import ───────────────────────────────────────────────────────────

def _make_musicxml(kind_value: str, kind_text: str, root_step: str = "C") -> bytes:
    xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work><work-title>Test</work-title></work>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <harmony>
        <root><root-step>{root_step}</root-step></root>
        <kind text="{kind_text}">{kind_value}</kind>
      </harmony>
      <note><duration>16</duration></note>
    </measure>
  </part>
</score-partwise>
"""
    return xml.encode("utf-8")


def _make_musicxml_slash(
    kind_value: str, kind_text: str, bass_step: str, root_step: str = "C"
) -> bytes:
    xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work><work-title>Test</work-title></work>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <harmony>
        <root><root-step>{root_step}</root-step></root>
        <kind text="{kind_text}">{kind_value}</kind>
        <bass><bass-step>{bass_step}</bass-step></bass>
      </harmony>
      <note><duration>16</duration></note>
    </measure>
  </part>
</score-partwise>
"""
    return xml.encode("utf-8")


@pytest.mark.parametrize("kind_value,kind_text,expected_symbol", [
    ("minor-11th",    "m11", "Cm11"),
    ("augmented",     "+",   "Caug"),
    ("power",         "5",   "C5"),
    ("major-13th",    "M13", "Cmaj13"),
    ("dominant-11th", "11",  "C11"),
])
def test_musicxml_import_kind(kind_value, kind_text, expected_symbol):
    xml = _make_musicxml(kind_value, kind_text)
    result = import_files({"test.musicxml": xml})
    assert not result.failed, result.failed
    assert len(result.songs) == 1
    measures = result.songs[0].song.measures
    assert len(measures) > 0
    harmony = measures[0].harmony
    assert len(harmony) > 0
    assert harmony[0].symbol == expected_symbol


def test_musicxml_import_power_slash_bass():
    xml = _make_musicxml_slash("power", "5", "G")
    result = import_files({"test.musicxml": xml})
    assert not result.failed
    assert result.songs[0].song.measures[0].harmony[0].symbol == "C5/G"


# ── harmonic_context ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("symbol", ["Cm11", "Cmaj13", "Caug", "C5", "C11"])
def test_hard_context_does_not_raise(symbol):
    pcs = hard_context_pitch_classes(symbol)
    assert len(pcs) >= 2


@pytest.mark.parametrize("symbol", ["Cm11", "Cmaj13", "Caug", "C5", "C11"])
def test_output_chord_tone_names_does_not_raise(symbol):
    names = output_chord_tone_names(symbol, [symbol], 0)
    assert len(names) == 6


def test_cm11_chord_tones():
    # C Eb G Bb D F
    pcs = chord_tone_pitch_classes("Cm11")
    names = _pc_names(pcs)
    assert "C" in names
    assert "D#" in names or "Eb" in names   # minor third
    assert "G" in names
    assert "A#" in names or "Bb" in names   # b7
    assert "D" in names                      # 9
    assert "F" in names                      # 11


def test_cmaj13_chord_tones():
    # C E G B D A
    pcs = chord_tone_pitch_classes("Cmaj13")
    names = _pc_names(pcs)
    assert "C" in names
    assert "E" in names
    assert "G" in names
    assert "B" in names                      # maj7
    assert "D" in names                      # 9
    assert "A" in names                      # 13


def test_caug_chord_tones():
    pcs = chord_tone_pitch_classes("Caug")
    names = _pc_names(pcs)
    assert "C" in names
    assert "E" in names
    assert "G#" in names or "Ab" in names   # #5


def test_c5_chord_tones():
    pcs = chord_tone_pitch_classes("C5")
    names = _pc_names(pcs)
    assert "C" in names
    assert "G" in names
    assert len(pcs) == 2


def test_c11_chord_tones():
    # C F G Bb D (5 tones)
    pcs = chord_tone_pitch_classes("C11")
    names = _pc_names(pcs)
    assert "C" in names
    assert "F" in names
    assert "G" in names
    assert "A#" in names or "Bb" in names
    assert "D" in names


# ── chord_engine ─────────────────────────────────────────────────────────────

def _whole_tone_collection(root_pc: int) -> tuple[int, ...]:
    return tuple((root_pc + i) % 12 for i in (0, 2, 4, 6, 8, 10))


def _major_scale(root_pc: int) -> tuple[int, ...]:
    return tuple((root_pc + i) % 12 for i in (0, 2, 4, 5, 7, 9, 11))


def test_construct_cm11_uses_all_six_mandatory():
    core = parse_chord_core("Cm11")
    # Cm11 has 6 mandatory notes — no tensions needed
    dorian_c = tuple((0 + i) % 12 for i in (0, 2, 3, 5, 7, 9, 10))
    result = construct_chord_pitch_classes(core, dorian_c)
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6
    expected_pcs = {0, 3, 7, 10, 2, 5}  # C Eb G Bb D F
    assert set(result.mandatory_pitch_classes) == expected_pcs


def test_construct_cmaj13_uses_all_six_mandatory():
    core = parse_chord_core("Cmaj13")
    major_c = _major_scale(0)
    result = construct_chord_pitch_classes(core, major_c)
    assert len(result.final_pitch_classes) == 6
    expected_pcs = {0, 4, 7, 11, 2, 9}  # C E G B D A
    assert set(result.mandatory_pitch_classes) == expected_pcs


def test_construct_caug_six_notes():
    core = parse_chord_core("Caug")
    wt = _whole_tone_collection(0)
    result = construct_chord_pitch_classes(core, wt)
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6
    assert 0 in result.mandatory_pitch_classes  # C
    assert 4 in result.mandatory_pitch_classes  # E
    assert 8 in result.mandatory_pitch_classes  # G#


def test_construct_c5_six_notes():
    core = parse_chord_core("C5")
    major_c = _major_scale(0)
    result = construct_chord_pitch_classes(core, major_c)
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6
    assert 0 in result.mandatory_pitch_classes  # C
    assert 7 in result.mandatory_pitch_classes  # G


def test_construct_c11_six_notes():
    core = parse_chord_core("C11")
    major_c = _major_scale(0)
    result = construct_chord_pitch_classes(core, major_c)
    assert len(result.final_pitch_classes) == 6
    assert len(set(result.final_pitch_classes)) == 6
    # C F G Bb D mandatory — needs 1 tension from collection
    assert 0 in result.mandatory_pitch_classes  # C
    assert 5 in result.mandatory_pitch_classes  # F
    assert 7 in result.mandatory_pitch_classes  # G


# ── import batch smoke test ───────────────────────────────────────────────────

_BATCH_MUSICXML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <work><work-title>Chord Kinds Smoke</work-title></work>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <harmony><root><root-step>C</root-step></root><kind text="m11">minor-11th</kind></harmony>
      <note><duration>4</duration></note>
      <harmony><root><root-step>F</root-step></root><kind text="+">augmented</kind></harmony>
      <note><duration>4</duration></note>
      <harmony><root><root-step>G</root-step></root><kind text="5">power</kind></harmony>
      <note><duration>4</duration></note>
      <harmony><root><root-step>E</root-step></root><kind text="M13">major-13th</kind></harmony>
      <note><duration>4</duration></note>
    </measure>
    <measure number="2">
      <harmony><root><root-step>A</root-step></root><kind text="11">dominant-11th</kind></harmony>
      <note><duration>16</duration></note>
    </measure>
  </part>
</score-partwise>
"""


def test_import_batch_all_new_kinds_no_failed():
    result = import_files({"smoke.musicxml": _BATCH_MUSICXML})
    assert not result.failed, result.failed
    assert len(result.songs) == 1
    symbols = [
        h.symbol
        for m in result.songs[0].song.measures
        for h in m.harmony
    ]
    assert "Cm11" in symbols
    assert "Faug" in symbols
    assert "G5" in symbols
    assert "Emaj13" in symbols
    assert "A11" in symbols
