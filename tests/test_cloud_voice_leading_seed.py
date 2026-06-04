"""Tests for cloud_voice_leading_seed deterministic tie-break feature."""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest

from changes.importers.compact_progression import compact_progression_to_song_model
from changes.models.song_model import (
    SongModel,
    derive_voice_leading_seed,
    song_model_from_dict,
    song_model_to_dict,
)
from changes.voice_leading import (
    _assign_minimum_motion_target,
    _deterministic_bit,
    generate_voice_leading,
)
from changes.voicing import progression_to_voicings


# ── derive_voice_leading_seed ─────────────────────────────────────────────────

def test_derive_seed_is_deterministic():
    assert derive_voice_leading_seed("hello") == derive_voice_leading_seed("hello")


def test_derive_seed_fits_31_bit():
    seed = derive_voice_leading_seed("anything")
    assert 0 <= seed <= 0x7FFF_FFFF


def test_derive_seed_differs_for_different_content():
    assert derive_voice_leading_seed("song A") != derive_voice_leading_seed("song B")


# ── _deterministic_bit ────────────────────────────────────────────────────────

def test_deterministic_bit_is_stable():
    a = _deterministic_bit(42, "cloud_tiebreak", 1, 0, 6)
    b = _deterministic_bit(42, "cloud_tiebreak", 1, 0, 6)
    assert a == b


def test_deterministic_bit_returns_0_or_1():
    for seed in [0, 1, 42, 999, 2_147_483_647]:
        bit = _deterministic_bit(seed, "cloud_tiebreak", 0, 0, 6)
        assert bit in (0, 1)


def test_deterministic_bit_varies_across_seeds():
    # Among 20 seeds, both 0 and 1 should appear for the same context
    bits = {_deterministic_bit(s, "cloud_tiebreak", 0, 0, 6) for s in range(20)}
    assert bits == {0, 1}


# ── _assign_minimum_motion_target tie-break ───────────────────────────────────
#
# Single-voice scenario guarantees a tritone tie-break:
#   prev=60 (C4), target PC=6 (F#).
#   candidates: F#3=54, F#4=66, F#5=78.
#   |54-60|=6, |66-60|=6, |78-60|=18  →  tied = [54, 66].

def test_tie_break_seed_none_picks_lower_on_tritone():
    # With no seed, legacy behavior picks the lower of tied candidates.
    result = _assign_minimum_motion_target([60], [6], tie_break_seed=None)
    assert result[0] == 54


def test_tie_break_seeded_is_deterministic():
    r1 = _assign_minimum_motion_target([60], [6], tie_break_seed=12345, chord_index=2)
    r2 = _assign_minimum_motion_target([60], [6], tie_break_seed=12345, chord_index=2)
    assert r1 == r2


def test_tie_break_different_seeds_produce_both_directions():
    # Among seeds 0..49, both F#3 (54, "down") and F#4 (66, "up") should appear.
    outcomes = {
        _assign_minimum_motion_target([60], [6], tie_break_seed=s, chord_index=1)[0]
        for s in range(50)
    }
    assert 54 in outcomes and 66 in outcomes


# ── generate_voice_leading with tie_break_seed ────────────────────────────────
#
# Single-voice bounded case: C4 (60) → F# (PC 6, MIDI 6), range 51..69.
# F#3=54 and F#4=66 are both in range and both equidistant from 60 → tie-break occurs.

_TRITONE_VOICINGS = [[60], [6]]  # MIDI 6 = F#0, PC=6; generates tritone from 60


def test_generate_voice_leading_same_seed_is_deterministic():
    r1 = generate_voice_leading(_TRITONE_VOICINGS, min_midi=51, max_midi=69, tie_break_seed=42)
    r2 = generate_voice_leading(_TRITONE_VOICINGS, min_midi=51, max_midi=69, tie_break_seed=42)
    assert r1 == r2


def test_generate_voice_leading_seed_none_matches_no_seed():
    voicings = progression_to_voicings([["Cmaj7", "Am7", "Dm7", "G7"]])
    r_none = generate_voice_leading(voicings, min_midi=51, max_midi=69, tie_break_seed=None)
    r_default = generate_voice_leading(voicings, min_midi=51, max_midi=69)
    assert r_none == r_default


def test_generate_voice_leading_seed_none_picks_lower_on_tritone():
    led = generate_voice_leading(_TRITONE_VOICINGS, min_midi=51, max_midi=69, tie_break_seed=None)
    assert led[1][0] == 54  # lower of tied candidates


def test_generate_voice_leading_different_seeds_produce_both_directions():
    outcomes = {
        generate_voice_leading(_TRITONE_VOICINGS, min_midi=51, max_midi=69, tie_break_seed=s)[1][0]
        for s in range(50)
    }
    assert 54 in outcomes and 66 in outcomes


# ── SongModel serialization ───────────────────────────────────────────────────

def test_song_model_seed_round_trips():
    song = SongModel(
        title="T", working_key="C", performance_tempo=Fraction(120),
        measures=(), cloud_voice_leading_seed=123_456_789,
    )
    restored = song_model_from_dict(song_model_to_dict(song))
    assert restored.cloud_voice_leading_seed == 123_456_789


def test_song_model_seed_none_round_trips():
    song = SongModel(
        title="T", working_key=None, performance_tempo=Fraction(120),
        measures=(), cloud_voice_leading_seed=None,
    )
    restored = song_model_from_dict(song_model_to_dict(song))
    assert restored.cloud_voice_leading_seed is None


def test_song_model_from_dict_without_seed_field_gives_none():
    data = {"title": "Old Song", "working_key": "C", "performance_tempo": "120", "measures": []}
    song = song_model_from_dict(data)
    assert song.cloud_voice_leading_seed is None


# ── Import assigns seed ───────────────────────────────────────────────────────

def _minimal_payload(name: str = "Test", chord: str = "Cmaj7") -> dict:
    return {
        "name": name, "tempo": 120, "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [[chord]]}],
    }


def test_compact_progression_import_assigns_nonnone_seed():
    song = compact_progression_to_song_model(_minimal_payload())
    assert song.cloud_voice_leading_seed is not None
    assert 0 <= song.cloud_voice_leading_seed <= 0x7FFF_FFFF


def test_compact_progression_same_payload_same_seed():
    p = _minimal_payload()
    assert (compact_progression_to_song_model(p).cloud_voice_leading_seed ==
            compact_progression_to_song_model(p).cloud_voice_leading_seed)


def test_compact_progression_different_payload_different_seed():
    s1 = compact_progression_to_song_model(_minimal_payload("Song A", "Cmaj7"))
    s2 = compact_progression_to_song_model(_minimal_payload("Song B", "Dm7"))
    assert s1.cloud_voice_leading_seed != s2.cloud_voice_leading_seed


def test_musicxml_import_assigns_nonnone_seed():
    from fractions import Fraction
    from changes.importers.musicxml import (
        ImportedBar,
        ImportedHarmonyEvent,
        ImportedSong,
        imported_song_to_song_model,
    )

    event = ImportedHarmonyEvent(
        symbol="Cmaj7",
        chord=None,
        source_order_in_measure=0,
        source_position_quarters=Fraction(0),
        raw_kind_value=None,
        raw_kind_text=None,
        raw_degrees=(),
        raw_root=None,
        raw_bass=None,
    )
    bar = ImportedBar(source_measure_number="1", events=(event,))
    imported = ImportedSong(
        title="Test Song", composer=None, source_software=None,
        source_musicxml_version=None, initial_key=None, initial_time_signature=None,
        bars=(bar,), raw_form_markers=(), warnings=(),
    )
    song = imported_song_to_song_model(imported, tempo=120)
    assert song.cloud_voice_leading_seed is not None
    assert 0 <= song.cloud_voice_leading_seed <= 0x7FFF_FFFF


# ── render_arrangement uses seed ─────────────────────────────────────────────

def test_render_arrangement_same_seed_same_cloud_notes():
    from changes.rendering.arrangement_renderer import render_arrangement
    from changes.models.render_profile import default_render_profile

    rp = default_render_profile()
    song = compact_progression_to_song_model({
        "name": "GS", "tempo": 120, "time_signature": "4/4",
        "sections": [{"name": "A", "progression": [["Bmaj7", "D7", "Gmaj7", "Bb7", "Ebmaj7"]]}],
    })

    arr_a = render_arrangement(song, rp)
    arr_b = render_arrangement(song, rp)

    cloud_a = [tuple(n.note_midi for n in occ.cloud.notes) for occ in arr_a.occurrences]
    cloud_b = [tuple(n.note_midi for n in occ.cloud.notes) for occ in arr_b.occurrences]
    assert cloud_a == cloud_b


def test_render_arrangement_seed_none_gives_consistent_result():
    from changes.rendering.arrangement_renderer import render_arrangement
    from changes.models.render_profile import default_render_profile

    rp = default_render_profile()
    song = dataclasses.replace(
        compact_progression_to_song_model({
            "name": "GS", "tempo": 120, "time_signature": "4/4",
            "sections": [{"name": "A", "progression": [["Bmaj7", "D7", "Gmaj7"]]}],
        }),
        cloud_voice_leading_seed=None,
    )

    cloud_a = [tuple(n.note_midi for n in occ.cloud.notes) for occ in render_arrangement(song, rp).occurrences]
    cloud_b = [tuple(n.note_midi for n in occ.cloud.notes) for occ in render_arrangement(song, rp).occurrences]
    assert cloud_a == cloud_b  # deterministic even with seed=None (legacy mode)
