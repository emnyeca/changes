"""Song model dataclasses and serialization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


def _fraction_to_text(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def _fraction_from_text(v: str | int | float) -> Fraction:
    return Fraction(str(v))


@dataclass(frozen=True)
class HarmonyEvent:
    id: str
    symbol: str
    measure_number: int
    offset_quarters: Fraction
    duration_quarters: Fraction


@dataclass(frozen=True)
class Measure:
    number: int
    section_id: str | None
    meter_numerator: int
    meter_denominator: int
    absolute_start_quarters: Fraction
    harmony: tuple[HarmonyEvent, ...]


@dataclass(frozen=True)
class SongModel:
    title: str
    working_key: str | None
    performance_tempo: Fraction
    measures: tuple[Measure, ...]
    working_key_mode: str | None = None


def song_model_to_dict(song: SongModel) -> dict:
    return {
        "title": song.title,
        "working_key": song.working_key,
        "working_key_mode": song.working_key_mode,
        "performance_tempo": _fraction_to_text(song.performance_tempo),
        "measures": [
            {
                "number": m.number,
                "section_id": m.section_id,
                "meter_numerator": m.meter_numerator,
                "meter_denominator": m.meter_denominator,
                "absolute_start_quarters": _fraction_to_text(m.absolute_start_quarters),
                "harmony": [
                    {
                        "id": h.id,
                        "symbol": h.symbol,
                        "measure_number": h.measure_number,
                        "offset_quarters": _fraction_to_text(h.offset_quarters),
                        "duration_quarters": _fraction_to_text(h.duration_quarters),
                    }
                    for h in m.harmony
                ],
            }
            for m in song.measures
        ],
    }


def song_model_from_dict(data: dict) -> SongModel:
    measures = []
    for m in data.get("measures", []):
        harmony = tuple(
            HarmonyEvent(
                id=str(h["id"]),
                symbol=str(h["symbol"]),
                measure_number=int(h["measure_number"]),
                offset_quarters=_fraction_from_text(h["offset_quarters"]),
                duration_quarters=_fraction_from_text(h["duration_quarters"]),
            )
            for h in m.get("harmony", [])
        )
        measures.append(
            Measure(
                number=int(m["number"]),
                section_id=(None if m.get("section_id") is None else str(m.get("section_id"))),
                meter_numerator=int(m["meter_numerator"]),
                meter_denominator=int(m["meter_denominator"]),
                absolute_start_quarters=_fraction_from_text(m["absolute_start_quarters"]),
                harmony=harmony,
            )
        )

    return SongModel(
        title=str(data.get("title") or "Untitled"),
        working_key=(None if data.get("working_key") is None else str(data.get("working_key"))),
        working_key_mode=(None if data.get("working_key_mode") is None else str(data.get("working_key_mode"))),
        performance_tempo=_fraction_from_text(data.get("performance_tempo", "120")),
        measures=tuple(measures),
    )
