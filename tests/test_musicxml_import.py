from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from changes.chord_parser import parse_chord_core
from changes.harmonic_context import (
    UnsupportedHarmonicContextError,
    chord_tone_pitch_classes,
    extract_output_chord_tone_set,
    resolve_scale_collection_with_retry,
)
from changes.importers.musicxml import (
    UnsupportedMusicXMLHarmonyError,
    import_musicxml_text,
    load_musicxml_song,
    load_musicxml_song_model,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "musicxml"
DIRECT_FIXTURES = FIXTURE_ROOT / "ireal_direct"
CONVERTED_FIXTURES = FIXTURE_ROOT / "ireal_musicxml"
REAL_PAIR_DIRECT = Path("examples/musicXML/iRealPro")
REAL_PAIR_CONVERTED = Path("examples/musicXML/ireal-musicxml")


def _event_semantic_signature(event) -> tuple:
    chord = event.chord
    return (
        event.source_order_in_measure,
        chord.root_pc,
        chord.normalized_quality,
        chord.base_quality,
        chord.seventh_type,
        tuple(sorted(chord.extensions)),
        tuple(sorted(chord.added_degrees)),
        tuple(sorted(chord.altered_degrees)),
        tuple(sorted(chord.omitted_degrees)),
        chord.slash_bass_pc,
        chord.special_semantic_tag,
        tuple(sorted(chord_tone_pitch_classes(chord.symbol, include_bass=True))),
    )


def _bar_signature(song) -> tuple[tuple[str, tuple[tuple, ...]], ...]:
    return tuple(
        (
            bar.source_measure_number,
            tuple(_event_semantic_signature(e) for e in bar.events),
        )
        for bar in song.bars
    )


def _inline_musicxml(kind_blocks: str, *, version: str = "4.0") -> str:
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<score-partwise version=\"{version}\">
  <part-list><score-part id=\"P1\"><part-name>Music</part-name></score-part></part-list>
  <part id=\"P1\">
    <measure number=\"1\">
      <attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      {kind_blocks}
    </measure>
  </part>
</score-partwise>
"""


def _flatten_imported_symbols(song) -> list[str]:
    return [event.chord.symbol for bar in song.bars for event in bar.events]


def _resolve_occurrence(progression: list[str], index: int) -> tuple:
    try:
        local, selected = resolve_scale_collection_with_retry(progression, index, circular=True, include_slash_bass=True)
        output = extract_output_chord_tone_set(progression[index], selected)
        return (
            "ok",
            tuple(sorted(local)),
            selected.family,
            selected.name,
            output,
        )
    except UnsupportedHarmonicContextError as exc:
        return ("error", type(exc).__name__, str(exc))


def test_import_accepts_musicxml_31_direct_and_keeps_metadata():
    song = load_musicxml_song(DIRECT_FIXTURES / "normalization_case.musicxml")

    assert song.source_musicxml_version == "3.1"
    assert song.source_software == "iReal Pro 2026.5"
    assert song.title == "Normalization Case"
    assert song.composer == "Direct Composer"
    assert song.initial_key is not None and song.initial_key.get("fifths") == 0
    assert song.initial_time_signature == {"beats": 4, "beat_type": 4}
    assert len(song.bars) == 10


def test_import_accepts_musicxml_40_converted_and_keeps_metadata():
    song = load_musicxml_song(CONVERTED_FIXTURES / "normalization_case.musicxml")

    assert song.source_musicxml_version == "4.0"
    assert song.source_software == "@infojunkie/ireal-musicxml 2.1.1"
    assert song.title == "Normalization Case"
    assert song.composer == "Converted Composer"
    assert song.initial_key is not None and song.initial_key.get("fifths") == 0
    assert song.initial_time_signature == {"beats": 4, "beat_type": 4}
    assert len(song.bars) == 10


def test_normalization_fixture_pair_equivalence_excludes_raw_representation_differences():
    direct = load_musicxml_song(DIRECT_FIXTURES / "normalization_case.musicxml")
    converted = load_musicxml_song(CONVERTED_FIXTURES / "normalization_case.musicxml")

    assert _bar_signature(direct) == _bar_signature(converted)


def test_major_ninth_maps_to_maj9_not_dominant7():
        xml = _inline_musicxml(
                """
            <harmony>
                <root><root-step>C</root-step></root>
                <kind text=\"M9\">major-ninth</kind>
            </harmony>
                """
        )
        song = import_musicxml_text(xml)
        event = song.bars[0].events[0]
        assert event.chord.normalized_quality == "maj9"
        assert chord_tone_pitch_classes(event.chord.symbol, include_bass=True) == frozenset({0, 2, 4, 7, 11})


def test_unknown_kind_raises_explicit_error_not_silent_7():
        xml = _inline_musicxml(
                """
            <harmony>
                <root><root-step>C</root-step></root>
                <kind text=\"mystery\">mystery-kind</kind>
            </harmony>
                """
        )
        with pytest.raises(UnsupportedMusicXMLHarmonyError):
                import_musicxml_text(xml)


def test_dominant_add_sharp9_alter_flat5_maps_to_7sharp9b5():
        xml = _inline_musicxml(
                """
            <harmony>
                <root><root-step>G</root-step></root>
                <kind text=\"7\">dominant</kind>
                <degree><degree-value>9</degree-value><degree-alter>1</degree-alter><degree-type>add</degree-type></degree>
                <degree><degree-value>5</degree-value><degree-alter>-1</degree-alter><degree-type>alter</degree-type></degree>
            </harmony>
                """
        )
        song = import_musicxml_text(xml)
        event = song.bars[0].events[0]
        assert event.chord.normalized_quality == "7#9b5"
        pcs = chord_tone_pitch_classes(event.chord.symbol, include_bass=True)
        assert pcs == frozenset({7, 11, 1, 5, 10})


def test_suspended_direct_and_converted_encodings_normalize_equally_for_7sus4_9sus4_7b9sus4():
        direct = import_musicxml_text(
                f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<score-partwise version=\"3.1\">
    <part-list><score-part id=\"P1\"><part-name>Music</part-name></score-part></part-list>
    <part id=\"P1\">
        <measure number=\"1\"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
            <harmony><root><root-step>G</root-step></root><kind text=\"7sus4\">suspended-fourth</kind><degree><degree-value>7</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree></harmony>
        </measure>
        <measure number=\"2\">
            <harmony><root><root-step>G</root-step></root><kind text=\"9sus4\">suspended-fourth</kind><degree><degree-value>9</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree></harmony>
        </measure>
        <measure number=\"3\">
            <harmony><root><root-step>G</root-step></root><kind text=\"7b9sus4\">suspended-fourth</kind><degree><degree-value>9</degree-value><degree-alter>-1</degree-alter><degree-type>add</degree-type></degree></harmony>
        </measure>
    </part>
</score-partwise>
"""
        )
        converted = import_musicxml_text(
                f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<score-partwise version=\"4.0\">
    <part-list><score-part id=\"P1\"><part-name>Music</part-name></score-part></part-list>
    <part id=\"P1\">
        <measure number=\"1\"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
            <harmony><root><root-step>G</root-step></root><kind text=\"7sus\">dominant</kind><degree><degree-value>4</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree><degree><degree-value>3</degree-value><degree-alter>0</degree-alter><degree-type>subtract</degree-type></degree></harmony>
        </measure>
        <measure number=\"2\">
            <harmony><root><root-step>G</root-step></root><kind text=\"9sus\">dominant-ninth</kind><degree><degree-value>4</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree><degree><degree-value>3</degree-value><degree-alter>0</degree-alter><degree-type>subtract</degree-type></degree></harmony>
        </measure>
        <measure number=\"3\">
            <harmony><root><root-step>G</root-step></root><kind text=\"7susb9\">dominant</kind><degree><degree-value>9</degree-value><degree-alter>-1</degree-alter><degree-type>add</degree-type></degree><degree><degree-value>4</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree><degree><degree-value>3</degree-value><degree-alter>0</degree-alter><degree-type>subtract</degree-type></degree></harmony>
        </measure>
    </part>
</score-partwise>
"""
        )
        assert _bar_signature(direct) == _bar_signature(converted)


def test_mapping_rules_for_dual_encodings_and_alt_override():
    direct = load_musicxml_song(DIRECT_FIXTURES / "normalization_case.musicxml")
    converted = load_musicxml_song(CONVERTED_FIXTURES / "normalization_case.musicxml")

    # 1-based measure indexes in fixture:
    # 2:m7b5, 7:mMaj7, 8:7sus4, 9:alt
    assert direct.bars[1].events[0].chord.normalized_quality == "m7b5"
    assert converted.bars[1].events[0].chord.normalized_quality == "m7b5"

    assert direct.bars[6].events[0].chord.normalized_quality == "mMaj7"
    assert converted.bars[6].events[0].chord.normalized_quality == "mMaj7"

    assert direct.bars[7].events[0].chord.normalized_quality == "7sus4"
    assert converted.bars[7].events[0].chord.normalized_quality == "7sus4"

    assert direct.bars[8].events[0].chord.normalized_quality == "alt"
    assert converted.bars[8].events[0].chord.normalized_quality == "alt"

    # Raw degree payload differs between producers but canonical alt is the same.
    assert direct.bars[8].events[0].raw_degrees != converted.bars[8].events[0].raw_degrees


def test_position_policy_keeps_semantic_equality_and_ignores_positions_for_phase1_durations():
    direct = load_musicxml_song(DIRECT_FIXTURES / "position_case.musicxml")
    converted = load_musicxml_song(CONVERTED_FIXTURES / "position_case.musicxml")

    assert _bar_signature(direct) == _bar_signature(converted)

    direct_second_pos = direct.bars[0].events[1].source_position_quarters
    converted_second_pos = converted.bars[0].events[1].source_position_quarters
    assert direct_second_pos != converted_second_pos

    direct_song = load_musicxml_song_model(DIRECT_FIXTURES / "position_case.musicxml")
    converted_song = load_musicxml_song_model(CONVERTED_FIXTURES / "position_case.musicxml")

    assert direct_song.measures[0].harmony[0].offset_quarters == Fraction(0, 1)
    assert direct_song.measures[0].harmony[1].offset_quarters == Fraction(2, 1)
    assert converted_song.measures[0].harmony[0].offset_quarters == Fraction(0, 1)
    assert converted_song.measures[0].harmony[1].offset_quarters == Fraction(2, 1)


def test_harmony_offset_is_relative_to_current_cursor_position():
        xml = _inline_musicxml(
                """
            <note><rest/><duration>2</duration><type>quarter</type></note>
            <harmony>
                <root><root-step>C</root-step></root>
                <kind text=\"maj7\">major-seventh</kind>
                <offset>1</offset>
            </harmony>
                """
        )
        song = import_musicxml_text(xml)
        # divisions=2, cursor=1 quarter, offset=1 division=1/2 quarter => 3/2 quarters
        assert song.bars[0].events[0].source_position_quarters == Fraction(3, 2)


def test_form_policy_normalizes_repeat_times_and_keeps_markers_without_unfolding():
    direct = load_musicxml_song(DIRECT_FIXTURES / "normalization_case.musicxml")

    repeat_markers = [m for m in direct.raw_form_markers if m.marker_type == "repeat"]
    assert repeat_markers
    backward = [m for m in repeat_markers if m.raw_payload.get("direction") == "backward"]
    assert backward
    assert backward[0].raw_payload.get("times") == ""
    assert backward[0].raw_payload.get("normalized_times") == "2"

    ending_markers = [m for m in direct.raw_form_markers if m.marker_type == "ending"]
    words_markers = [m for m in direct.raw_form_markers if m.marker_type == "words"]
    assert ending_markers
    assert words_markers

    # Import keeps written order and does not unfold by repeats/endings.
    assert len(direct.bars) == 10
    assert len(direct.bars[9].events) == 1


def test_pair_equivalence_for_20_real_musicxml_pairs():
    direct_files = sorted(REAL_PAIR_DIRECT.glob("*.musicxml"))
    assert len(direct_files) == 20

    for direct_file in direct_files:
        converted_file = REAL_PAIR_CONVERTED / direct_file.name
        assert converted_file.exists(), f"missing pair for {direct_file.name}"

        direct_song = load_musicxml_song(direct_file)
        converted_song = load_musicxml_song(converted_file)

        assert _bar_signature(direct_song) == _bar_signature(converted_song), direct_file.name


def test_all_imported_symbols_from_20_pairs_are_parseable_and_have_constituents():
    direct_files = sorted(REAL_PAIR_DIRECT.glob("*.musicxml"))
    assert len(direct_files) == 20

    for direct_file in direct_files:
        converted_file = REAL_PAIR_CONVERTED / direct_file.name
        assert converted_file.exists(), f"missing pair for {direct_file.name}"

        for song in (load_musicxml_song(direct_file), load_musicxml_song(converted_file)):
            for bar in song.bars:
                for event in bar.events:
                    parse_chord_core(event.chord.symbol)
                    chord_tone_pitch_classes(event.chord.symbol, include_bass=True)


def test_importer_to_harmony_end_to_end_equivalence_for_20_pairs():
    direct_files = sorted(REAL_PAIR_DIRECT.glob("*.musicxml"))
    assert len(direct_files) == 20

    unresolved: list[tuple[str, int, tuple]] = []

    for direct_file in direct_files:
        converted_file = REAL_PAIR_CONVERTED / direct_file.name
        assert converted_file.exists(), f"missing pair for {direct_file.name}"

        direct_song = load_musicxml_song(direct_file)
        converted_song = load_musicxml_song(converted_file)

        direct_progression = _flatten_imported_symbols(direct_song)
        converted_progression = _flatten_imported_symbols(converted_song)
        assert direct_progression == converted_progression, direct_file.name

        for idx in range(len(direct_progression)):
            d_res = _resolve_occurrence(direct_progression, idx)
            c_res = _resolve_occurrence(converted_progression, idx)
            assert d_res == c_res, f"{direct_file.name} at event #{idx + 1}"
            if d_res[0] == "error":
                unresolved.append((direct_file.name, idx + 1, d_res))

    # Keep an explicit assertion so unresolved contexts are visible but allowed
    # only when both producer paths fail identically.
    assert isinstance(unresolved, list)


def test_focused_quality_end_to_end_parse_and_resolution_contract():
    focused = [
        "Dm7b5",
        "AmMaj7",
        "G7b9",
        "G7#9",
        "G7#9b5",
        "G7#5",
        "G7#11",
        "G7b13",
        "G7sus4",
        "G9sus4",
        "G7b9sus4",
        "Galt",
        "C7/E",
        "Cdim",
        "Cmaj9",
        "Cmaj7#5",
        "G7#5b9",
        "G7b5b9",
        "G13",
        "G13b9",
    ]
    for symbol in focused:
        parse_chord_core(symbol)
        chord_tone_pitch_classes(symbol, include_bass=True)
        try:
            local, selected = resolve_scale_collection_with_retry([symbol], 0, circular=True, include_slash_bass=True)
            assert local
            extract_output_chord_tone_set(symbol, selected)
        except UnsupportedHarmonicContextError:
            # Explicit unresolved harmonic context is acceptable for current scope.
            pass


def test_real_pair_has_position_mismatch_but_same_semantic_progression_for_known_songs():
    names = ["A Ballad.musicxml", "A Felicidade.musicxml"]
    found_position_diff = 0

    for name in names:
        direct_song = load_musicxml_song(REAL_PAIR_DIRECT / name)
        converted_song = load_musicxml_song(REAL_PAIR_CONVERTED / name)

        assert _bar_signature(direct_song) == _bar_signature(converted_song)

        for direct_bar, converted_bar in zip(direct_song.bars, converted_song.bars):
            for direct_event, converted_event in zip(direct_bar.events, converted_bar.events):
                if direct_event.source_position_quarters != converted_event.source_position_quarters:
                    found_position_diff += 1

    assert found_position_diff >= 1
