"""Render profile model and defaults."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderProfile:
    name: str
    voices: int
    voice_leading_strategy: str
    bass_enabled: bool
    bass_strategy: str
    hold_repeated_same_pitch: str
    cloud_min_midi: int
    cloud_max_midi: int
    chord_min_midi: int
    chord_max_midi: int
    bass_min_midi: int
    bass_max_midi: int


def default_render_profile() -> RenderProfile:
    return RenderProfile(
        name="default_jazz_cloud",
        voices=6,
        voice_leading_strategy="minimum_motion",
        bass_enabled=True,
        bass_strategy="slash_or_root_in_window",
        hold_repeated_same_pitch="hold_until_change",
        cloud_min_midi=48,
        cloud_max_midi=72,
        chord_min_midi=48,
        chord_max_midi=72,
        bass_min_midi=36,
        bass_max_midi=47,
    )


def render_profile_to_dict(profile: RenderProfile) -> dict:
    return {
        "version": 1,
        "type": "render_profile",
        "name": profile.name,
        "voicing": {"voices": profile.voices},
        "voice_leading": {
            "strategy": profile.voice_leading_strategy,
            "cloud_min_midi": profile.cloud_min_midi,
            "cloud_max_midi": profile.cloud_max_midi,
            "chord_min_midi": profile.chord_min_midi,
            "chord_max_midi": profile.chord_max_midi,
        },
        "bass": {
            "enabled": profile.bass_enabled,
            "strategy": profile.bass_strategy,
            "bass_min_midi": profile.bass_min_midi,
            "bass_max_midi": profile.bass_max_midi,
        },
        "hold": {"repeated_same_pitch": profile.hold_repeated_same_pitch},
    }
