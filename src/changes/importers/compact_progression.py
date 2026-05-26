"""Importer for compact progression input into SongModel."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import yaml

from changes.models.song_model import HarmonyEvent, Measure, SongModel


def _parse_time_signature(text: str) -> tuple[int, int]:
    parts = text.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid time_signature: {text}")
    num = int(parts[0])
    den = int(parts[1])
    if num <= 0 or den <= 0:
        raise ValueError(f"Invalid time_signature: {text}")
    return num, den


def compact_progression_to_song_model(payload: dict) -> SongModel:
    title = str(payload.get("name") or "Untitled")
    key = payload.get("key")
    working_key = None if key is None else str(key)
    performance_tempo = Fraction(str(payload.get("tempo", 120)))

    ts = str(payload.get("time_signature", "4/4"))
    meter_numerator, meter_denominator = _parse_time_signature(ts)
    measure_length_quarters = Fraction(4 * meter_numerator, meter_denominator)

    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("compact progression requires non-empty sections")

    measures: list[Measure] = []
    absolute_start = Fraction(0, 1)
    measure_number = 0

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("name") or "A")
        progression = section.get("progression")
        if not isinstance(progression, list):
            continue

        for bar in progression:
            if isinstance(bar, list):
                symbols = [str(x).strip() for x in bar if str(x).strip()]
            else:
                text = str(bar).strip()
                symbols = [text] if text else []

            if not symbols:
                continue

            measure_number += 1
            duration = measure_length_quarters / len(symbols)
            harmony: list[HarmonyEvent] = []
            offset = Fraction(0, 1)
            for chord_index, symbol in enumerate(symbols, start=1):
                harmony.append(
                    HarmonyEvent(
                        id=f"m{measure_number}_h{chord_index}",
                        symbol=symbol,
                        measure_number=measure_number,
                        offset_quarters=offset,
                        duration_quarters=duration,
                    )
                )
                offset += duration

            measures.append(
                Measure(
                    number=measure_number,
                    section_id=section_name,
                    meter_numerator=meter_numerator,
                    meter_denominator=meter_denominator,
                    absolute_start_quarters=absolute_start,
                    harmony=tuple(harmony),
                )
            )
            absolute_start += measure_length_quarters

    if not measures:
        raise ValueError("compact progression produced no measures")

    return SongModel(
        title=title,
        working_key=working_key,
        performance_tempo=performance_tempo,
        measures=tuple(measures),
    )


def load_compact_progression_song_model(path: str | Path) -> SongModel:
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(src)
    payload = yaml.safe_load(src.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("compact progression input must be a mapping")
    return compact_progression_to_song_model(payload)
