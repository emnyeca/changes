"""Digitone target profile model and defaults."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class DigitoneTargetProfile:
    name: str
    device: str
    voice_to_track: dict[str, int]
    default_velocity: int | str
    length_strategy: str
    allow_inf: bool
    approximation: str
    preferred_speed: Fraction
    fallback_speeds: tuple[Fraction, ...]
    track_default_velocity: dict[int, int] | None = None
    polyphonic_tracks: tuple[int, ...] = ()


DEFAULT_SPEED_CANDIDATES = (
    Fraction(1, 8),
    Fraction(1, 4),
    Fraction(1, 2),
    Fraction(1, 1),
    Fraction(2, 1),
)


def default_digitone_target_profile() -> DigitoneTargetProfile:
    return DigitoneTargetProfile(
        name="digitone2_jazz_cloud",
        device="digitone2",
        voice_to_track={
            "cloud_voice_1": 1,
            "cloud_voice_2": 2,
            "cloud_voice_3": 3,
            "cloud_voice_4": 4,
            "cloud_voice_5": 5,
            "cloud_voice_6": 6,
            "chord_voice_1": 1,
            "chord_voice_2": 2,
            "chord_voice_3": 3,
            "chord_voice_4": 4,
            "chord_voice_5": 5,
            "chord_voice_6": 6,
            "bass": 7,
            "chord_note_1": 8,
            "chord_note_2": 8,
            "chord_note_3": 8,
            "chord_note_4": 8,
            "chord_note_5": 8,
            "chord_note_6": 8,
        },
        default_velocity="inherit",
        length_strategy="hold_until_next_event",
        allow_inf=False,
        approximation="error",
        preferred_speed=Fraction(1, 8),
        fallback_speeds=(Fraction(1, 4), Fraction(1, 2), Fraction(1, 1), Fraction(2, 1)),
        track_default_velocity={1: 70, 2: 70, 3: 70, 4: 50, 5: 70, 6: 50, 7: 100},
        polyphonic_tracks=(8,),
    )


def speed_fraction_to_label(speed: Fraction) -> str:
    if speed.denominator == 1:
        return str(speed.numerator)
    return f"{speed.numerator}/{speed.denominator}"
