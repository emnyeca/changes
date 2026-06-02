from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from changes.models.song_model import HarmonyEvent, Measure, SongModel


def parse_fraction_value(value: object) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"fraction value must not be bool: {value!r}")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        raise ValueError(f"fraction value must not be float: {value!r}")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("fraction value must not be empty")
        if "." in text:
            raise ValueError(f"fraction value must not be decimal text: {value!r}")
        try:
            return Fraction(text)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"invalid fraction value: {value!r}") from exc
    raise ValueError(f"unsupported fraction value type: {type(value).__name__}")


def format_fraction_value(value: Fraction) -> int | str:
    if not isinstance(value, Fraction):
        raise ValueError(f"value must be Fraction: {value!r}")
    if value.denominator == 1:
        return int(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    return value


def _require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def _require_keys(mapping: dict[str, Any], required: tuple[str, ...], field: str) -> None:
    missing = [key for key in required if key not in mapping]
    if missing:
        raise ValueError(f"{field} missing required fields: {', '.join(missing)}")


def _parse_meter_text(meter: object) -> tuple[int, int]:
    if not isinstance(meter, str):
        raise ValueError(f"meter must be string N/D: {meter!r}")
    text = meter.strip()
    if not text or "/" not in text:
        raise ValueError(f"meter must be string N/D: {meter!r}")
    num_text, den_text = text.split("/", 1)
    try:
        numerator = int(num_text)
        denominator = int(den_text)
    except ValueError as exc:
        raise ValueError(f"meter must be string N/D: {meter!r}") from exc
    if numerator <= 0 or denominator <= 0:
        raise ValueError(f"meter values must be positive: {meter!r}")
    return numerator, denominator


def song_model_from_dict(payload: dict) -> SongModel:
    data = _require_mapping(payload, "payload")
    _require_keys(
        data,
        ("version", "type", "title", "working_key", "performance_tempo", "measures"),
        "payload",
    )

    version = data["version"]
    if version != 1:
        raise ValueError(f"unsupported song model version: {version!r}")

    payload_type = data["type"]
    if payload_type != "changes.song":
        raise ValueError(f"unsupported song model type: {payload_type!r}")

    title = str(data["title"])
    working_key_raw = data["working_key"]
    working_key = None if working_key_raw is None else str(working_key_raw)
    performance_tempo = parse_fraction_value(data["performance_tempo"])

    raw_measures = _require_list(data["measures"], "payload.measures")
    measures: list[Measure] = []

    for i, raw_measure in enumerate(raw_measures, start=1):
        measure = _require_mapping(raw_measure, f"payload.measures[{i}]")
        _require_keys(
            measure,
            ("number", "section_id", "meter", "absolute_start_quarters", "harmony"),
            f"payload.measures[{i}]",
        )

        number = int(measure["number"])
        section_raw = measure["section_id"]
        section_id = None if section_raw is None else str(section_raw)
        meter_numerator, meter_denominator = _parse_meter_text(measure["meter"])
        absolute_start_quarters = parse_fraction_value(measure["absolute_start_quarters"])

        raw_harmony = _require_list(measure["harmony"], f"payload.measures[{i}].harmony")
        harmony_events: list[HarmonyEvent] = []

        for j, raw_event in enumerate(raw_harmony, start=1):
            event = _require_mapping(raw_event, f"payload.measures[{i}].harmony[{j}]")
            _require_keys(
                event,
                ("id", "symbol", "offset_quarters", "duration_quarters"),
                f"payload.measures[{i}].harmony[{j}]",
            )

            harmony_events.append(
                HarmonyEvent(
                    id=str(event["id"]),
                    symbol=str(event["symbol"]),
                    measure_number=number,
                    offset_quarters=parse_fraction_value(event["offset_quarters"]),
                    duration_quarters=parse_fraction_value(event["duration_quarters"]),
                )
            )

        measures.append(
            Measure(
                number=number,
                section_id=section_id,
                meter_numerator=meter_numerator,
                meter_denominator=meter_denominator,
                absolute_start_quarters=absolute_start_quarters,
                harmony=tuple(harmony_events),
            )
        )

    working_key_mode_raw = data.get("working_key_mode")
    working_key_mode = None if working_key_mode_raw is None else str(working_key_mode_raw)

    return SongModel(
        title=title,
        working_key=working_key,
        working_key_mode=working_key_mode,
        performance_tempo=performance_tempo,
        measures=tuple(measures),
    )


def song_model_to_dict(song: SongModel) -> dict:
    return {
        "version": 1,
        "type": "changes.song",
        "title": song.title,
        "working_key": song.working_key,
        "working_key_mode": song.working_key_mode,
        "performance_tempo": format_fraction_value(song.performance_tempo),
        "measures": [
            {
                "number": measure.number,
                "section_id": measure.section_id,
                "meter": f"{measure.meter_numerator}/{measure.meter_denominator}",
                "absolute_start_quarters": format_fraction_value(measure.absolute_start_quarters),
                "harmony": [
                    {
                        "id": event.id,
                        "symbol": event.symbol,
                        "offset_quarters": format_fraction_value(event.offset_quarters),
                        "duration_quarters": format_fraction_value(event.duration_quarters),
                    }
                    for event in measure.harmony
                ],
            }
            for measure in song.measures
        ],
    }


def load_song_model_yaml(path: str | Path) -> SongModel:
    src = Path(path)
    payload = yaml.safe_load(src.read_text(encoding="utf-8"))
    return song_model_from_dict(_require_mapping(payload, "payload"))


def dump_song_model_yaml(song: SongModel) -> str:
    payload = song_model_to_dict(song)
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
