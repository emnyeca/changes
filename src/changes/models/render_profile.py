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
    cloud_trigger_policy: str
    bass_trigger_policy: str
    chord_trigger_policy: str
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
        cloud_trigger_policy="hold_until_change",
        bass_trigger_policy="hold_until_change",
        chord_trigger_policy="retrigger",
        cloud_min_midi=51,
        cloud_max_midi=69,
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
        "trigger": {
            "cloud": profile.cloud_trigger_policy,
            "bass": profile.bass_trigger_policy,
            "chord": profile.chord_trigger_policy,
        },
    }
