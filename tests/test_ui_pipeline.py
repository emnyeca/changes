"""Tests for ui_pipeline helpers (settings → profiles, target profile routing)."""

from __future__ import annotations

import pytest

from changes.app_settings import AppSettings
from changes.ui_pipeline import count_auto_split_patterns, count_linear_patterns, settings_to_render_profile, settings_to_target_profile
from changes.importers.compact_progression import compact_progression_to_song_model


# ── settings_to_render_profile ────────────────────────────────────────────────

def test_render_profile_uses_trigger_policies() -> None:
    s = AppSettings(
        cloud_trigger_policy="retrigger",
        bass_trigger_policy="hold_until_change",
        chord_trigger_policy="retrigger",
    )
    rp = settings_to_render_profile(s)
    assert rp.cloud_trigger_policy == "retrigger"
    assert rp.bass_trigger_policy == "hold_until_change"
    assert rp.chord_trigger_policy == "retrigger"


def test_render_profile_midi_ranges() -> None:
    s = AppSettings(cloud_center_midi=60, bass_center_midi=36, chord_center_midi=60)
    rp = settings_to_render_profile(s)
    assert rp.cloud_min_midi == 51  # center 60 - 9
    assert rp.cloud_max_midi == 69  # center 60 + 9
    assert rp.bass_min_midi == 36
    assert rp.bass_max_midi == 47


def test_render_profile_bass_disabled_when_bass_track_none() -> None:
    s = AppSettings(bass_track=None)
    rp = settings_to_render_profile(s)
    assert rp.bass_enabled is False


def test_render_profile_bass_enabled_when_bass_track_set() -> None:
    s = AppSettings(bass_track=7)
    rp = settings_to_render_profile(s)
    assert rp.bass_enabled is True


# ── settings_to_target_profile — routing ─────────────────────────────────────

def test_target_profile_default_routing() -> None:
    s = AppSettings()
    tp = settings_to_target_profile(s)
    v2t = tp.voice_to_track
    assert v2t["cloud_voice_1"] == 1
    assert v2t["cloud_voice_6"] == 6
    assert v2t["bass"] == 7
    assert v2t["chord_note_1"] == 8
    assert v2t["chord_note_6"] == 8


def test_target_profile_cloud_none_voices_excluded() -> None:
    s = AppSettings(cloud_tracks=[1, 1, None, None, None, None])
    tp = settings_to_target_profile(s)
    v2t = tp.voice_to_track
    assert "cloud_voice_1" in v2t
    assert "cloud_voice_2" in v2t
    assert "cloud_voice_3" not in v2t
    assert "cloud_voice_6" not in v2t


def test_target_profile_bass_none_excluded() -> None:
    s = AppSettings(bass_track=None)
    tp = settings_to_target_profile(s)
    assert "bass" not in tp.voice_to_track


def test_target_profile_chord_none_excluded() -> None:
    s = AppSettings(chord_track=None)
    tp = settings_to_target_profile(s)
    v2t = tp.voice_to_track
    assert not any(k.startswith("chord_note") for k in v2t)


def test_target_profile_chord_track_is_polyphonic() -> None:
    s = AppSettings(chord_track=8)
    tp = settings_to_target_profile(s)
    assert 8 in tp.polyphonic_tracks


def test_target_profile_shared_track_becomes_polyphonic() -> None:
    # Two cloud voices on the same track → that track is polyphonic
    s = AppSettings(cloud_tracks=[3, 3, 4, 5, 6, 7], bass_track=None, chord_track=None)
    tp = settings_to_target_profile(s)
    assert 3 in tp.polyphonic_tracks
    assert 4 not in tp.polyphonic_tracks


def test_target_profile_custom_routing() -> None:
    s = AppSettings(
        cloud_tracks=[1, 1, None, None, None, None],
        bass_track=2,
        chord_track=None,
    )
    tp = settings_to_target_profile(s)
    v2t = tp.voice_to_track
    assert v2t["cloud_voice_1"] == 1
    assert v2t["cloud_voice_2"] == 1
    assert v2t["bass"] == 2
    assert not any(k.startswith("chord_note") for k in v2t)
    # track 1 has 2 voices → polyphonic
    assert 1 in tp.polyphonic_tracks
    # track 2 has only bass → not polyphonic (no chord)
    assert 2 not in tp.polyphonic_tracks


def test_target_profile_rejects_cross_layer_track_conflict() -> None:
    s = AppSettings(
        cloud_tracks=[1, 1, 1, 1, 1, 1],
        bass_track=1,
        chord_track=1,
    )

    with pytest.raises(ValueError, match="cloud and bass cannot share"):
        settings_to_target_profile(s)


def test_target_profile_cloud_voices_may_share_track() -> None:
    s = AppSettings(
        cloud_tracks=[1, 1, 2, 2, 3, 3],
        bass_track=None,
        chord_track=None,
    )
    tp = settings_to_target_profile(s)

    assert tp.voice_to_track["cloud_voice_1"] == 1
    assert tp.voice_to_track["cloud_voice_2"] == 1
    assert 1 in tp.polyphonic_tracks


def test_target_profile_enabled_changes_layers_may_use_tracks_1_to_8() -> None:
    s = AppSettings(
        cloud_tracks=[8, None, None, None, None, None],
        bass_track=7,
        chord_track=6,
    )
    tp = settings_to_target_profile(s)

    assert tp.voice_to_track["cloud_voice_1"] == 8
    assert tp.voice_to_track["bass"] == 7
    assert tp.voice_to_track["chord_note_1"] == 6


@pytest.mark.parametrize(
    "settings",
    [
        AppSettings(cloud_tracks=[9, None, None, None, None, None], bass_track=None, chord_track=None),
        AppSettings(cloud_tracks=[None, None, None, None, None, None], bass_track=9, chord_track=None),
        AppSettings(cloud_tracks=[None, None, None, None, None, None], bass_track=None, chord_track=9),
        AppSettings(cloud_tracks=[16, None, None, None, None, None], bass_track=None, chord_track=None),
    ],
)
def test_target_profile_rejects_changes_layer_tracks_9_to_16(settings: AppSettings) -> None:
    with pytest.raises(ValueError, match="Tracks 9..16 are reserved"):
        settings_to_target_profile(settings)


def test_target_profile_rejects_track_outside_1_to_8() -> None:
    s = AppSettings(bass_track=17, chord_track=None)

    with pytest.raises(ValueError, match="1..8"):
        settings_to_target_profile(s)


def test_count_linear_patterns_ignores_bundle_section_splits() -> None:
    song = compact_progression_to_song_model(
        {
            "name": "Two Sections",
            "tempo": 120,
            "time_signature": "4/4",
            "sections": [
                {"name": "A", "progression": [["Cmaj7"] for _ in range(8)]},
                {"name": "B", "progression": [["Dm7"] for _ in range(8)]},
            ],
        }
    )
    settings = AppSettings()

    assert count_auto_split_patterns(song, settings) == 2
    assert count_linear_patterns(song, settings) == 1
