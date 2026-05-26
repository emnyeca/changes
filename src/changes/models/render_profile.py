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


def default_render_profile() -> RenderProfile:
    return RenderProfile(
        name="default_jazz_cloud",
        voices=6,
        voice_leading_strategy="minimum_motion",
        bass_enabled=True,
        bass_strategy="existing_behavior",
        hold_repeated_same_pitch="hold_until_change",
    )


def render_profile_to_dict(profile: RenderProfile) -> dict:
    return {
        "version": 1,
        "type": "render_profile",
        "name": profile.name,
        "voicing": {"voices": profile.voices},
        "voice_leading": {"strategy": profile.voice_leading_strategy},
        "bass": {"enabled": profile.bass_enabled, "strategy": profile.bass_strategy},
        "hold": {"repeated_same_pitch": profile.hold_repeated_same_pitch},
    }
