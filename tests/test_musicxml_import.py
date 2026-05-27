from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from changes.importers.musicxml import load_musicxml_song, load_musicxml_song_model


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "musicxml"
DIRECT_FIXTURES = FIXTURE_ROOT / "ireal_direct"
CONVERTED_FIXTURES = FIXTURE_ROOT / "ireal_musicxml"
REAL_PAIR_DIRECT = Path("examples/musicXML/iRealPro")
REAL_PAIR_CONVERTED = Path("examples/musicXML/ireal-musicxml")


def _event_signature(event) -> tuple[int, str, int, int | None]:
    return (
        event.source_order_in_measure,
        event.chord.normalized_quality,
        event.chord.root_pc,
        event.chord.slash_bass_pc,
    )


def _bar_signature(song) -> tuple[tuple[str, tuple[tuple[int, str, int, int | None], ...]], ...]:
    return tuple(
        (
            bar.source_measure_number,
            tuple(_event_signature(e) for e in bar.events),
        )
        for bar in song.bars
    )


def test_import_accepts_musicxml_31_direct_and_keeps_metadata():
    song = load_musicxml_song(DIRECT_FIXTURES / "normalization_case.musicxml")

    assert song.source_musicxml_version == "3.1"
    assert song.source_software == "iReal Pro 2026.5"
    assert song.title == "Normalization Case"
    assert song.composer == "Direct Composer"
    assert song.initial_key == {"fifths": 0}
    assert song.initial_time_signature == {"beats": 4, "beat_type": 4}
    assert len(song.bars) == 10


def test_import_accepts_musicxml_40_converted_and_keeps_metadata():
    song = load_musicxml_song(CONVERTED_FIXTURES / "normalization_case.musicxml")

    assert song.source_musicxml_version == "4.0"
    assert song.source_software == "@infojunkie/ireal-musicxml 2.1.1"
    assert song.title == "Normalization Case"
    assert song.composer == "Converted Composer"
    assert song.initial_key == {"fifths": 0}
    assert song.initial_time_signature == {"beats": 4, "beat_type": 4}
    assert len(song.bars) == 10


def test_normalization_fixture_pair_equivalence_excludes_raw_representation_differences():
    direct = load_musicxml_song(DIRECT_FIXTURES / "normalization_case.musicxml")
    converted = load_musicxml_song(CONVERTED_FIXTURES / "normalization_case.musicxml")

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
