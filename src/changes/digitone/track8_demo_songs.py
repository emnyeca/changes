from __future__ import annotations

from fractions import Fraction

from changes.models.song_model import HarmonyEvent, Measure, SongModel


def build_demo_cmaj7_song() -> SongModel:
    """Return a deterministic minimal Cmaj7 SongModel for Chord export demos on Digitone Track 8."""
    return SongModel(
        title="Demo Cmaj7",
        working_key="C",
        performance_tempo=Fraction(120, 1),
        measures=(
            Measure(
                number=1,
                section_id="A",
                meter_numerator=4,
                meter_denominator=4,
                absolute_start_quarters=Fraction(0, 1),
                harmony=(
                    HarmonyEvent(
                        id="h1",
                        symbol="Cmaj7",
                        measure_number=1,
                        offset_quarters=Fraction(0, 1),
                        duration_quarters=Fraction(4, 1),
                    ),
                ),
            ),
        ),
    )
