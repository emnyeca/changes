"""MusicXML importer with source-independent harmony normalization.

This module accepts MusicXML from both iReal Pro direct export and
@infojunkie/ireal-musicxml output, normalizing harmony semantics into
structured chord-core events for Changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

from changes.chord_parser import ChordSymbolCore, parse_chord_core
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.note import pitch_class_to_semitone, semitone_to_pitch_class


@dataclass(frozen=True)
class RawMusicXMLDegree:
    value: int
    alter: int
    degree_type: str


@dataclass(frozen=True)
class ImportedHarmonyEvent:
    chord: ChordSymbolCore
    source_order_in_measure: int
    source_position_quarters: Fraction | None
    raw_kind_value: str | None
    raw_kind_text: str | None
    raw_degrees: tuple[RawMusicXMLDegree, ...]
    raw_root: str | None
    raw_bass: str | None


@dataclass(frozen=True)
class ImportedBar:
    source_measure_number: str
    events: tuple[ImportedHarmonyEvent, ...]


@dataclass(frozen=True)
class RawFormMarker:
    measure_number: str
    marker_type: str
    raw_payload: dict[str, str]


@dataclass(frozen=True)
class ImportedSong:
    title: str | None
    composer: str | None
    source_software: str | None
    source_musicxml_version: str | None
    initial_key: object | None
    initial_time_signature: object | None
    bars: tuple[ImportedBar, ...]
    raw_form_markers: tuple[RawFormMarker, ...]
    warnings: tuple[str, ...]


class UnsupportedMusicXMLHarmonyError(ValueError):
    """Raised when a MusicXML harmony kind cannot be normalized safely."""


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in list(parent) if _strip_ns(c.tag) == name]


def _first(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    for c in list(parent):
        if _strip_ns(c.tag) == name:
            return c
    return None


def _text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    v = (node.text or "").strip()
    return v if v else None


def _parse_int(text: str | None, default: int = 0) -> int:
    if text is None or not text.strip():
        return default
    return int(text.strip())


def _pc_token(step: str | None, alter_text: str | None) -> tuple[str, int] | None:
    if step is None:
        return None
    alter = _parse_int(alter_text, default=0)
    base = pitch_class_to_semitone(step)
    pc = (base + alter) % 12
    return semitone_to_pitch_class(pc), pc


def _degree_token(value: int, alter: int) -> str:
    if alter > 0:
        return f"#{value}"
    if alter < 0:
        return f"b{value}"
    return str(value)


def _degree_map(raw_degrees: tuple[RawMusicXMLDegree, ...]) -> dict[tuple[str, int], int]:
    out: dict[tuple[str, int], int] = {}
    for d in raw_degrees:
        key = (d.degree_type.lower(), d.value)
        out[key] = d.alter
    return out


def _contains_text(haystack: str | None, needle: str) -> bool:
    if haystack is None:
        return False
    return needle.lower() in haystack.lower()


def _classify_quality(
    kind_value: str | None,
    kind_text: str | None,
    raw_degrees: tuple[RawMusicXMLDegree, ...],
) -> str:
    kv = (kind_value or "").strip().lower()
    dm = _degree_map(raw_degrees)

    # Producer text is not identity, but keep compatibility for special forms.
    if _contains_text(kind_text, "alt"):
        return "alt"

    if kv == "suspended-fourth":
        if _contains_text(kind_text, "7b9sus4") or dm.get(("add", 9)) == -1:
            return "7b9sus4"
        if _contains_text(kind_text, "9sus4") or dm.get(("add", 9)) == 0:
            return "9sus4"
        return "7sus4"

    if kv == "minor" and dm.get(("add", 7)) == 1:
        return "mMaj7"

    if kv == "minor-seventh" and dm.get(("alter", 5)) == -1:
        return "m7b5"

    if kv == "half-diminished":
        return "m7b5"

    if kv == "diminished":
        return "dim"

    if kv == "diminished-seventh":
        return "dim7"

    if kv == "major-seventh" and dm.get(("alter", 5)) == 1:
        return "maj7#5"

    if kv == "augmented-seventh":
        if dm.get(("add", 9)) == -1:
            return "7#5b9"
        return "7#5"

    if kv == "major-minor":
        return "mMaj7"

    if kv == "dominant" and dm.get(("add", 4)) == 0 and dm.get(("subtract", 3)) == 0:
        if dm.get(("add", 9)) == -1:
            return "7b9sus4"
        return "7sus4"

    if kv == "dominant-ninth" and dm.get(("add", 4)) == 0 and dm.get(("subtract", 3)) == 0:
        return "9sus4"

    if kv == "dominant":
        if dm.get(("add", 9)) == 1 and dm.get(("alter", 5)) == -1:
            return "7#9b5"
        if dm.get(("add", 9)) == -1 and dm.get(("alter", 5)) == 1:
            return "7#5b9"
        if dm.get(("add", 9)) == -1 and dm.get(("alter", 5)) == -1:
            return "7b5b9"
        if dm.get(("add", 9)) == -1:
            return "7b9"
        if dm.get(("add", 9)) == 1:
            return "7#9"
        if dm.get(("add", 11)) == 1:
            return "7#11"
        if dm.get(("add", 13)) == -1:
            return "7b13"
        if dm.get(("alter", 5)) == 1:
            return "7#5"
        if dm.get(("alter", 5)) == -1:
            return "7b5"

    if kv == "dominant-13th" and dm.get(("alter", 9)) == -1:
        return "13b9"

    base_map = {
        "major": "",
        "minor": "m",
        "major-sixth": "6",
        "minor-sixth": "m6",
        "major-seventh": "maj7",
        "major-ninth": "maj9",
        "minor-seventh": "m7",
        "minor-ninth": "m9",
        "dominant": "7",
        "dominant-ninth": "9",
        "dominant-13th": "13",
    }
    normalized = base_map.get(kv)
    if normalized is None:
        raise UnsupportedMusicXMLHarmonyError(
            f"Unsupported MusicXML harmony kind: {kind_value!r}, text={kind_text!r}, degrees={raw_degrees!r}"
        )
    return normalized


def _build_chord_core(
    root_name: str,
    root_pc: int,
    quality: str,
    slash_bass_name: str | None,
    slash_bass_pc: int | None,
) -> ChordSymbolCore:
    symbol = f"{root_name}{quality}" if quality else root_name
    if slash_bass_name is not None:
        symbol = f"{symbol}/{slash_bass_name}"

    # Use existing parser when possible for exact core-model compatibility.
    try:
        parsed = parse_chord_core(symbol)
        return parsed
    except ValueError:
        pass

    model: dict[str, dict[str, object]] = {
        "dim": {
            "base_quality": "diminished",
            "seventh_type": None,
            "extensions": frozenset(),
            "added_degrees": frozenset(),
            "altered_degrees": frozenset({"b5"}),
            "omitted_degrees": frozenset(),
            "special_semantic_tag": "diminished",
        },
        "maj7#5": {
            "base_quality": "major",
            "seventh_type": "maj7",
            "extensions": frozenset({"7"}),
            "added_degrees": frozenset(),
            "altered_degrees": frozenset({"#5"}),
            "omitted_degrees": frozenset(),
            "special_semantic_tag": None,
        },
        "7#5b9": {
            "base_quality": "dominant",
            "seventh_type": "b7",
            "extensions": frozenset({"7", "9"}),
            "added_degrees": frozenset(),
            "altered_degrees": frozenset({"#5", "b9"}),
            "omitted_degrees": frozenset(),
            "special_semantic_tag": None,
        },
        "7b5b9": {
            "base_quality": "dominant",
            "seventh_type": "b7",
            "extensions": frozenset({"7", "9"}),
            "added_degrees": frozenset(),
            "altered_degrees": frozenset({"b5", "b9"}),
            "omitted_degrees": frozenset(),
            "special_semantic_tag": None,
        },
        "13": {
            "base_quality": "dominant",
            "seventh_type": "b7",
            "extensions": frozenset({"7", "13"}),
            "added_degrees": frozenset({"13"}),
            "altered_degrees": frozenset(),
            "omitted_degrees": frozenset(),
            "special_semantic_tag": None,
        },
        "13b9": {
            "base_quality": "dominant",
            "seventh_type": "b7",
            "extensions": frozenset({"7", "9", "13"}),
            "added_degrees": frozenset({"13"}),
            "altered_degrees": frozenset({"b9"}),
            "omitted_degrees": frozenset(),
            "special_semantic_tag": None,
        },
    }
    spec = model.get(quality)
    if spec is None:
        raise UnsupportedMusicXMLHarmonyError(f"Unsupported canonical harmony quality: {quality}")

    return ChordSymbolCore(
        symbol=symbol,
        root=root_name,
        root_pc=root_pc,
        quality=quality,
        normalized_quality=quality,
        base_quality=str(spec["base_quality"]),
        seventh_type=(None if spec["seventh_type"] is None else str(spec["seventh_type"])),
        extensions=frozenset(str(x) for x in spec["extensions"]),
        added_degrees=frozenset(str(x) for x in spec["added_degrees"]),
        altered_degrees=frozenset(str(x) for x in spec["altered_degrees"]),
        omitted_degrees=frozenset(str(x) for x in spec["omitted_degrees"]),
        slash_bass=slash_bass_name,
        slash_bass_pc=slash_bass_pc,
        special_semantic_tag=(None if spec["special_semantic_tag"] is None else str(spec["special_semantic_tag"])),
    )


def _parse_degrees(harmony: ET.Element) -> tuple[RawMusicXMLDegree, ...]:
    out: list[RawMusicXMLDegree] = []
    for degree in _children(harmony, "degree"):
        value = _parse_int(_text(_first(degree, "degree-value")), default=0)
        alter = _parse_int(_text(_first(degree, "degree-alter")), default=0)
        degree_type = (_text(_first(degree, "degree-type")) or "add").lower()
        out.append(RawMusicXMLDegree(value=value, alter=alter, degree_type=degree_type))
    return tuple(out)


def _parse_harmony_event(
    harmony: ET.Element,
    *,
    order_in_measure: int,
    divisions: int,
    cursor_quarters: Fraction,
) -> ImportedHarmonyEvent:
    kind = _first(harmony, "kind")
    kind_value = _text(kind)
    kind_text = None if kind is None else kind.attrib.get("text")

    root = _first(harmony, "root")
    root_token = _pc_token(_text(_first(root, "root-step")), _text(_first(root, "root-alter")))
    if root_token is None:
        raise ValueError("harmony element missing root-step")
    root_name, root_pc = root_token

    bass = _first(harmony, "bass")
    bass_token = _pc_token(_text(_first(bass, "bass-step")), _text(_first(bass, "bass-alter")))
    bass_name = None if bass_token is None else bass_token[0]
    bass_pc = None if bass_token is None else bass_token[1]

    raw_degrees = _parse_degrees(harmony)
    canonical_quality = _classify_quality(kind_value, kind_text, raw_degrees)

    chord = _build_chord_core(
        root_name=root_name,
        root_pc=root_pc,
        quality=canonical_quality,
        slash_bass_name=bass_name,
        slash_bass_pc=bass_pc,
    )

    offset = _text(_first(harmony, "offset"))
    source_position_quarters = cursor_quarters
    if offset is not None:
        source_position_quarters = cursor_quarters + Fraction(_parse_int(offset), divisions)

    return ImportedHarmonyEvent(
        chord=chord,
        source_order_in_measure=order_in_measure,
        source_position_quarters=source_position_quarters,
        raw_kind_value=kind_value,
        raw_kind_text=kind_text,
        raw_degrees=raw_degrees,
        raw_root=root_name,
        raw_bass=bass_name,
    )


def _parse_form_markers(measure: ET.Element, measure_number: str) -> list[RawFormMarker]:
    markers: list[RawFormMarker] = []

    for barline in _children(measure, "barline"):
        repeat = _first(barline, "repeat")
        if repeat is not None:
            direction = repeat.attrib.get("direction", "")
            times = repeat.attrib.get("times")
            normalized_times = times
            if direction == "backward" and (times is None or not times.strip()):
                normalized_times = "2"
            markers.append(
                RawFormMarker(
                    measure_number=measure_number,
                    marker_type="repeat",
                    raw_payload={
                        "direction": direction,
                        "times": "" if times is None else times,
                        "normalized_times": "" if normalized_times is None else normalized_times,
                    },
                )
            )

        ending = _first(barline, "ending")
        if ending is not None:
            markers.append(
                RawFormMarker(
                    measure_number=measure_number,
                    marker_type="ending",
                    raw_payload={
                        "number": ending.attrib.get("number", ""),
                        "type": ending.attrib.get("type", ""),
                        "text": _text(ending) or "",
                    },
                )
            )

    for direction in _children(measure, "direction"):
        d_type = _first(direction, "direction-type")
        if d_type is None:
            continue
        if _first(d_type, "segno") is not None:
            markers.append(RawFormMarker(measure_number=measure_number, marker_type="segno", raw_payload={}))
        if _first(d_type, "coda") is not None:
            markers.append(RawFormMarker(measure_number=measure_number, marker_type="coda", raw_payload={}))
        if _first(d_type, "tocoda") is not None:
            markers.append(RawFormMarker(measure_number=measure_number, marker_type="tocoda", raw_payload={}))
        words = _text(_first(d_type, "words"))
        if words is not None:
            markers.append(
                RawFormMarker(
                    measure_number=measure_number,
                    marker_type="words",
                    raw_payload={"text": words},
                )
            )

    return markers


def import_musicxml_text(xml_text: str) -> ImportedSong:
    root = ET.fromstring(xml_text)
    if _strip_ns(root.tag) != "score-partwise":
        raise ValueError("MusicXML importer supports score-partwise only")

    source_musicxml_version = root.attrib.get("version")

    identification = _first(root, "identification")
    encoding = _first(identification, "encoding")
    source_software = _text(_first(encoding, "software"))

    work = _first(root, "work")
    title = _text(_first(work, "work-title")) or _text(_first(root, "movement-title"))

    composer: str | None = None
    if identification is not None:
        for creator in _children(identification, "creator"):
            if creator.attrib.get("type") == "composer":
                composer = _text(creator)
                if composer is not None:
                    break

    part = _first(root, "part")
    if part is None:
        raise ValueError("MusicXML file has no part")

    bars: list[ImportedBar] = []
    markers: list[RawFormMarker] = []
    warnings: list[str] = []

    divisions = 1
    initial_key: dict[str, int] | None = None
    initial_time_signature: dict[str, int] | None = None

    for measure in _children(part, "measure"):
        measure_number = measure.attrib.get("number", "")

        for attributes in _children(measure, "attributes"):
            div = _text(_first(attributes, "divisions"))
            if div is not None:
                divisions = max(1, _parse_int(div, default=1))

            key = _first(attributes, "key")
            if key is not None and initial_key is None:
                initial_key = {"fifths": _parse_int(_text(_first(key, "fifths")), default=0)}

            time = _first(attributes, "time")
            if time is not None and initial_time_signature is None:
                beats = _parse_int(_text(_first(time, "beats")), default=4)
                beat_type = _parse_int(_text(_first(time, "beat-type")), default=4)
                initial_time_signature = {"beats": beats, "beat_type": beat_type}

        harmony_events: list[ImportedHarmonyEvent] = []
        order = 0
        cursor = Fraction(0, 1)

        for child in list(measure):
            tag = _strip_ns(child.tag)
            if tag == "harmony":
                order += 1
                event = _parse_harmony_event(
                    child,
                    order_in_measure=order,
                    divisions=divisions,
                    cursor_quarters=cursor,
                )
                harmony_events.append(event)
            elif tag in ("note", "backup", "forward"):
                duration = _text(_first(child, "duration"))
                if duration is None:
                    continue
                delta = Fraction(_parse_int(duration, default=0), divisions)
                if tag == "backup":
                    cursor -= delta
                else:
                    cursor += delta

        if not harmony_events:
            warnings.append(f"measure {measure_number}: no harmony events")

        bars.append(ImportedBar(source_measure_number=measure_number, events=tuple(harmony_events)))
        markers.extend(_parse_form_markers(measure, measure_number))

    return ImportedSong(
        title=title,
        composer=composer,
        source_software=source_software,
        source_musicxml_version=source_musicxml_version,
        initial_key=initial_key,
        initial_time_signature=initial_time_signature,
        bars=tuple(bars),
        raw_form_markers=tuple(markers),
        warnings=tuple(warnings),
    )


def load_musicxml_song(path: str | Path) -> ImportedSong:
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(src)
    return import_musicxml_text(src.read_text(encoding="utf-8"))


def imported_song_to_song_model(imported: ImportedSong, *, tempo: Fraction | int | str = 120) -> SongModel:
    meter = imported.initial_time_signature or {"beats": 4, "beat_type": 4}
    beats = int(meter.get("beats", 4))
    beat_type = int(meter.get("beat_type", 4))
    measure_len = Fraction(4 * beats, beat_type)

    measures: list[Measure] = []
    absolute_start = Fraction(0, 1)

    for measure_index, bar in enumerate(imported.bars, start=1):
        event_count = len(bar.events)
        if event_count == 0:
            measures.append(
                Measure(
                    number=measure_index,
                    section_id=None,
                    meter_numerator=beats,
                    meter_denominator=beat_type,
                    absolute_start_quarters=absolute_start,
                    harmony=tuple(),
                )
            )
            absolute_start += measure_len
            continue

        duration = measure_len / event_count
        harmony: list[HarmonyEvent] = []
        offset = Fraction(0, 1)
        for event_index, event in enumerate(bar.events, start=1):
            harmony.append(
                HarmonyEvent(
                    id=f"m{measure_index}_h{event_index}",
                    symbol=event.chord.symbol,
                    measure_number=measure_index,
                    offset_quarters=offset,
                    duration_quarters=duration,
                )
            )
            offset += duration

        measures.append(
            Measure(
                number=measure_index,
                section_id=None,
                meter_numerator=beats,
                meter_denominator=beat_type,
                absolute_start_quarters=absolute_start,
                harmony=tuple(harmony),
            )
        )
        absolute_start += measure_len

    return SongModel(
        title=imported.title or "Untitled",
        working_key=None,
        performance_tempo=Fraction(str(tempo)),
        measures=tuple(measures),
    )


def load_musicxml_song_model(path: str | Path, *, tempo: Fraction | int | str = 120) -> SongModel:
    imported = load_musicxml_song(path)
    return imported_song_to_song_model(imported, tempo=tempo)
