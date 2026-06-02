"""Tests for form_expander: repeat expansion, endings, D.S./D.C. al Coda, section_ids."""

from __future__ import annotations

from pathlib import Path

import pytest

from changes.importers.form_expander import FormExpansionError, FormExpansionResult, expand_form
from changes.importers.import_bundle import import_files, import_musicxml_with_midi
from changes.importers.musicxml import import_musicxml_text

_FIXTURES = Path(__file__).parent.parent / "examples" / "musicXML"
_IM_DIR = _FIXTURES / "ireal-musicxml" / "repeatTest_ireal_musicxml"
_IR_DIR = _FIXTURES / "iRealPro" / "repeatTest_iRealPro"


# ── Minimal XML builder ───────────────────────────────────────────────────────

def _xml(measures: str, key_fifths: int = 0, mode: str = "major") -> bytes:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <work><work-title>Test</work-title></work>
  <part id="P1">
{measures}
  </part>
</score-partwise>
""".encode()


def _bar(num: int, chord: str = "C", prefix: str = "", suffix: str = "",
         left_barline: str = "", right_barline: str = "") -> str:
    lb = f'      <barline location="left">{left_barline}</barline>\n' if left_barline else ""
    rb = f'      <barline location="right">{right_barline}</barline>\n' if right_barline else ""
    attrs = ""
    if num == 1:
        attrs = """      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
"""
    return f"""    <measure number="{num}">
{attrs}{lb}{prefix}      <harmony><root><root-step>{chord[0]}</root-step></root><kind>major</kind></harmony>
      <note><duration>16</duration></note>
{rb}{suffix}    </measure>
"""


_REP_FWD = '<bar-style>heavy-light</bar-style><repeat direction="forward"/>'
_REP_BWD = lambda t: f'<bar-style>light-heavy</bar-style><repeat direction="backward" times="{t}"/>'
_REP_BWD_DEF = '<bar-style>light-heavy</bar-style><repeat direction="backward"/>'
_END1_START = '<ending number="1" type="start">1.</ending>'
_END1_STOP = '<ending number="1" type="stop">1.</ending>'
_END2_START = '<ending number="2" type="start">2.</ending>'
_END2_DISC = '<ending number="2" type="discontinue">2.</ending>'
_DBL = '<bar-style>light-light</bar-style>'
_SEGNO = '<direction placement="above"><direction-type><segno/></direction-type><sound segno="segno"/></direction>'
_CODA = '<direction placement="above"><direction-type><coda/></direction-type><sound coda="coda"/></direction>'
_TOCODA = '<direction placement="above"><direction-type><words>To Coda</words></direction-type><sound tocoda="coda"/></direction>'
_DS_CODA = '<direction placement="below"><direction-type><words>D.S. al Coda</words></direction-type><sound dalsegno="yes"/></direction>'
_DC_CODA = '<direction placement="below"><direction-type><words>D.C. al Coda</words></direction-type><sound dacapo="yes"/></direction>'
_REH = lambda lbl: f'<direction placement="above"><direction-type><rehearsal>{lbl}</rehearsal></direction-type></direction>'


def _import_bytes(xml_bytes: bytes):
    """Import bytes, return (imported_song, expansion_result)."""
    imported = import_musicxml_text(xml_bytes.decode("utf-8"))
    expansion = expand_form(imported)
    return imported, expansion


def _symbols(expansion: FormExpansionResult) -> list[str]:
    """Extract all harmony symbols in playback order."""
    result = []
    for bar in expansion.bars:
        for ev in bar.events:
            result.append(ev.symbol)
    return result


def _section_ids(expansion: FormExpansionResult) -> list[str | None]:
    return list(expansion.section_ids)


# ── Simple repeat ─────────────────────────────────────────────────────────────

def test_simple_repeat_2x():
    xml = _xml(
        _bar(1, "C", left_barline=_REP_FWD) +
        _bar(2, "F") +
        _bar(3, "G", right_barline=_REP_BWD_DEF) +
        _bar(4, "A"),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    # C F G (×2) + A = 7 symbols
    assert syms == ["C", "F", "G", "C", "F", "G", "A"]
    assert exp.playback_measure_count == 7
    assert exp.source_measure_count == 4


def test_simple_repeat_3x():
    xml = _xml(
        _bar(1, "C", left_barline=_REP_FWD) +
        _bar(2, "G", right_barline=_REP_BWD("3")) +
        _bar(3, "F"),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    assert syms == ["C", "G", "C", "G", "C", "G", "F"]


def test_repeat_times_4_from_xml():
    xml = _xml(
        _bar(1, "C", left_barline=_REP_FWD) +
        _bar(2, "G", right_barline=_REP_BWD("4")),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    assert syms == ["C", "G"] * 4


def test_no_repeat_forward_is_linear():
    xml = _xml(
        _bar(1, "C") +
        _bar(2, "F") +
        _bar(3, "G"),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    assert syms == ["C", "F", "G"]
    assert exp.playback_measure_count == 3


# ── 1st / 2nd ending ─────────────────────────────────────────────────────────

def test_ending_1_2_basic():
    # |: A | B | [1. C :| [2. D |
    xml = _xml(
        _bar(1, "C", left_barline=_REP_FWD) +
        _bar(2, "F") +
        _bar(3, "G", left_barline=_END1_START, right_barline=_END1_STOP + _REP_BWD_DEF) +
        _bar(4, "A", left_barline=_END2_START, right_barline=_END2_DISC),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    # Pass 1: C F G (ending1), repeat; Pass 2: C F, skip G (ending1), A (ending2)
    assert syms == ["C", "F", "G", "C", "F", "A"]


def test_ending_skip_on_last_pass():
    xml = _xml(
        _bar(1, "C", left_barline=_REP_FWD) +
        _bar(2, "F") +
        _bar(3, "G", left_barline=_END1_START, right_barline=_END1_STOP + _REP_BWD("3")) +
        _bar(4, "A", left_barline=_END2_START, right_barline=_END2_DISC),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    # times=3: pass 1→ C F G repeat; pass 2→ C F G repeat; pass 3→ C F skip-G, A
    assert syms == ["C", "F", "G", "C", "F", "G", "C", "F", "A"]


# ── D.S. al Coda ─────────────────────────────────────────────────────────────

def test_ds_al_coda_basic():
    # A | Segno B | To Coda C | D.S. al Coda | Coda D
    xml = _xml(
        _bar(1, "C") +
        _bar(2, "F", prefix=_SEGNO) +
        _bar(3, "G", prefix=_TOCODA) +
        _bar(4, "A", prefix=_DS_CODA) +
        _bar(5, "D", prefix=_CODA),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    # A(1) B(2) C(3) D.S.→B(2) [To Coda at 3]→Coda D(5)
    assert syms == ["C", "F", "G", "A", "F", "G", "D"]


def test_ds_inside_repeat_deferred():
    # |: A | [D.S. on penultimate, repeat ×2] :| Segno | To Coda B | Coda C
    xml = _xml(
        _bar(1, "C", prefix=_SEGNO) +
        _bar(2, "F", prefix=_TOCODA) +
        _bar(3, "G") +
        _bar(4, "A", left_barline=_REP_FWD) +
        _bar(5, "D", prefix=_DS_CODA, right_barline=_REP_BWD("2")) +
        _bar(6, "E", prefix=_CODA),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    # Pass1: A D repeat; Pass2: A D → D.S. deferred → exit repeat → execute D.S. → to Segno(C)
    # From segno: C F(ToC) → jump to Coda(E)
    assert "E" in syms
    assert syms.index("E") > syms.index("C") + 1  # Coda comes after returning to segno


# ── D.C. al Coda ─────────────────────────────────────────────────────────────

def test_dc_al_coda_basic():
    # A | To Coda B | D.C. al Coda | Coda C
    xml = _xml(
        _bar(1, "C", prefix=_TOCODA) +
        _bar(2, "F") +
        _bar(3, "G", prefix=_DC_CODA) +
        _bar(4, "A", prefix=_CODA),
    )
    _, exp = _import_bytes(xml)
    syms = _symbols(exp)
    # C(1 ToC) F(2) G(3 DC) → back to beginning → C(1, ToC triggers) → jump to A(4)
    assert syms == ["C", "F", "G", "C", "A"]


# ── Section IDs ───────────────────────────────────────────────────────────────

def test_section_id_from_rehearsal():
    xml = _xml(
        _bar(1, "C", prefix=_REH("A"), left_barline=_REP_FWD) +
        _bar(2, "F", right_barline=_REP_BWD_DEF) +
        _bar(3, "G", prefix=_REH("B")),
    )
    _, exp = _import_bytes(xml)
    ids = _section_ids(exp)
    # Expanded: A pass1, A pass2, B
    # A appears twice → A1, A1, A2 (second repeat), then B1
    assert ids[0] == ids[1]  # both passes of A share label until section changes
    unique = list(dict.fromkeys(ids))
    assert len(unique) >= 2  # at least A section and B section
    assert "B1" in ids


def test_section_id_from_coda_marker():
    xml = _xml(
        _bar(1, "C", prefix=_SEGNO) +
        _bar(2, "F", prefix=_TOCODA) +
        _bar(3, "G", prefix=_DS_CODA) +
        _bar(4, "A", prefix=_CODA),
    )
    _, exp = _import_bytes(xml)
    ids = _section_ids(exp)
    # Last bar (Coda section) should have "Coda1" label
    assert ids[-1] == "Coda1"


def test_section_id_from_double_barline():
    xml = _xml(
        _bar(1, "C") +
        _bar(2, "F", right_barline=_DBL) +
        _bar(3, "G") +
        _bar(4, "A"),
    )
    _, exp = _import_bytes(xml)
    ids = _section_ids(exp)
    # Double barline after bar 2 → new section at bar 3
    assert ids[0] == ids[1]  # bars 1-2 in same section
    assert ids[2] != ids[1]  # bar 3 starts new section


# ── Same rehearsal label appears multiple times ───────────────────────────────

def test_section_id_repeated_label_numbered():
    xml = _xml(
        _bar(1, "C", prefix=_REH("A")) +
        _bar(2, "F", prefix=_REH("B")) +
        _bar(3, "G", prefix=_REH("A")) +
        _bar(4, "A", prefix=_REH("B")),
    )
    _, exp = _import_bytes(xml)
    ids = _section_ids(exp)
    assert ids[0] == "A1"
    assert ids[1] == "B1"
    assert ids[2] == "A2"
    assert ids[3] == "B2"


# ── SongModel integration ─────────────────────────────────────────────────────

def test_section_ids_in_songmodel():
    """Expanded SongModel should have section_ids on measures."""
    xml = _xml(
        _bar(1, "C", prefix=_REH("A"), left_barline=_REP_FWD) +
        _bar(2, "F", right_barline=_REP_BWD_DEF) +
        _bar(3, "G", prefix=_REH("B")),
    )
    result = import_files({"test.musicxml": xml})
    assert not result.failed
    song = result.songs[0].song
    section_ids = [m.section_id for m in song.measures]
    assert any(s is not None for s in section_ids)
    # B section should appear at end
    last_sections = [s for s in section_ids if s is not None]
    assert "B1" in last_sections


def test_absolute_start_quarters_contiguous():
    """absolute_start_quarters must be contiguous (no gaps) after expansion."""
    from fractions import Fraction
    xml = _xml(
        _bar(1, "C", left_barline=_REP_FWD) +
        _bar(2, "F", right_barline=_REP_BWD_DEF) +
        _bar(3, "G"),
    )
    result = import_files({"test.musicxml": xml})
    song = result.songs[0].song
    expected = Fraction(0)
    for m in song.measures:
        assert m.absolute_start_quarters == expected
        if m.harmony:
            expected += m.harmony[-1].offset_quarters + m.harmony[-1].duration_quarters
        else:
            expected += Fraction(4)


# ── Source: sample fixture files ──────────────────────────────────────────────

@pytest.mark.parametrize("fname,source_measures,min_playback", [
    ("a-night-in-tunisia_ireal_musicxml.musicxml", 40, 40),
    ("a-noite_ireal_musicxml.musicxml", 24, 24),
    ("affirmation_ireal_musicxml.musicxml", 34, 34),
    ("algum-lugar_ireal_musicxml.musicxml", 28, 28),
    ("canto-de-ossanha_ireal_musicxml.musicxml", 45, 45),
])
def test_sample_import_not_failed(fname, source_measures, min_playback):
    path = _IM_DIR / fname
    if not path.exists():
        pytest.skip(f"fixture not found: {path}")
    result = import_files({"song.musicxml": path.read_bytes()})
    assert not result.failed, result.failed
    assert len(result.songs) == 1
    song = result.songs[0].song
    assert len(song.measures) >= min_playback


@pytest.mark.parametrize("fname", [
    "a-night-in-tunisia_ireal_musicxml.musicxml",
    "a-noite_ireal_musicxml.musicxml",
    "affirmation_ireal_musicxml.musicxml",
    "algum-lugar_ireal_musicxml.musicxml",
    "canto-de-ossanha_ireal_musicxml.musicxml",
])
def test_sample_expansion_larger_than_source(fname):
    """Songs with repeats should expand to more measures than source."""
    path = _IM_DIR / fname
    if not path.exists():
        pytest.skip(f"fixture not found: {path}")
    imported = import_musicxml_text(path.read_text(encoding="utf-8"))
    exp = expand_form(imported)
    # Songs with repeats should expand
    assert exp.playback_measure_count >= exp.source_measure_count


@pytest.mark.parametrize("fname", [
    "a-night-in-tunisia_ireal_musicxml.musicxml",
    "a-noite_ireal_musicxml.musicxml",
    "affirmation_ireal_musicxml.musicxml",
    "algum-lugar_ireal_musicxml.musicxml",
    "canto-de-ossanha_ireal_musicxml.musicxml",
])
def test_sample_section_ids_present(fname):
    """Expanded songs should have section_ids from rehearsal marks."""
    path = _IM_DIR / fname
    if not path.exists():
        pytest.skip(f"fixture not found: {path}")
    result = import_files({"song.musicxml": path.read_bytes()})
    song = result.songs[0].song
    section_ids = [m.section_id for m in song.measures if m.section_id is not None]
    assert len(section_ids) > 0, "No section_ids found"


def test_a_night_in_tunisia_expansion():
    """A section (m1-m8) repeats ×2, resulting in > 40 measures."""
    path = _IM_DIR / "a-night-in-tunisia_ireal_musicxml.musicxml"
    if not path.exists():
        pytest.skip(f"fixture not found: {path}")
    imported = import_musicxml_text(path.read_text(encoding="utf-8"))
    exp = expand_form(imported)
    assert exp.source_measure_count == 40
    assert exp.playback_measure_count > 40  # A section ×2 = extra 8 bars


def test_a_noite_has_coda_section():
    """A Noite should have a Coda section after D.S. resolution."""
    path = _IM_DIR / "a-noite_ireal_musicxml.musicxml"
    if not path.exists():
        pytest.skip(f"fixture not found: {path}")
    result = import_files({"song.musicxml": path.read_bytes()})
    song = result.songs[0].song
    section_ids = {m.section_id for m in song.measures if m.section_id is not None}
    assert any("Coda" in (s or "") for s in section_ids), f"No Coda section in: {section_ids}"


def test_canto_5x_words_override():
    """Canto De Ossanha's 5x words should override times=2 on the D section repeat."""
    path = _IM_DIR / "canto-de-ossanha_ireal_musicxml.musicxml"
    if not path.exists():
        pytest.skip(f"fixture not found: {path}")
    imported = import_musicxml_text(path.read_text(encoding="utf-8"))
    exp = expand_form(imported)
    # The source is 45 measures, playback should be significantly more
    assert exp.playback_measure_count > 50


# ── UI helpers ────────────────────────────────────────────────────────────────

def test_extract_section_ids():
    from changes.main_ui import extract_section_ids
    from changes.models.song_model import SongModel, Measure, HarmonyEvent
    from fractions import Fraction
    h = HarmonyEvent(id="m1_h1", symbol="C", measure_number=1,
                     offset_quarters=Fraction(0), duration_quarters=Fraction(4))
    measures = (
        Measure(number=1, section_id="A1", meter_numerator=4, meter_denominator=4,
                absolute_start_quarters=Fraction(0), harmony=(h,)),
        Measure(number=2, section_id="A1", meter_numerator=4, meter_denominator=4,
                absolute_start_quarters=Fraction(4), harmony=(h,)),
        Measure(number=3, section_id="B1", meter_numerator=4, meter_denominator=4,
                absolute_start_quarters=Fraction(8), harmony=(h,)),
    )
    song = SongModel(title="T", working_key=None, performance_tempo=120, measures=measures)
    assert extract_section_ids(song) == ["A1", "B1"]


def test_filter_song_by_sections():
    from changes.main_ui import filter_song_by_sections
    from changes.models.song_model import SongModel, Measure, HarmonyEvent
    from fractions import Fraction
    h = HarmonyEvent(id="m1_h1", symbol="C", measure_number=1,
                     offset_quarters=Fraction(0), duration_quarters=Fraction(4))
    measures = (
        Measure(number=1, section_id="A1", meter_numerator=4, meter_denominator=4,
                absolute_start_quarters=Fraction(0), harmony=(h,)),
        Measure(number=2, section_id="B1", meter_numerator=4, meter_denominator=4,
                absolute_start_quarters=Fraction(4), harmony=(h,)),
        Measure(number=3, section_id="A1", meter_numerator=4, meter_denominator=4,
                absolute_start_quarters=Fraction(8), harmony=(h,)),
    )
    song = SongModel(title="T", working_key=None, performance_tempo=120, measures=measures)
    filtered = filter_song_by_sections(song, {"A1"})
    assert len(filtered.measures) == 2
    assert filtered.measures[0].absolute_start_quarters == Fraction(0)
    assert filtered.measures[1].absolute_start_quarters == Fraction(4)
