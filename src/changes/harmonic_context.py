"""Context-aware harmonic selection for six-slot voicing generation.

This module owns musical-context decisions:
- chord-tone extraction from supported symbols
- local pitch collection construction (prev/current/next distinct chord)
- deterministic scale-collection selection
- output slot extraction (1, 3, 5, 6/13, 7, 9)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .chord_parser import parse_chord_symbol
from .note import pitch_class_to_semitone, semitone_to_pitch_class


@dataclass(frozen=True)
class ChordCore:
    symbol: str
    root: str
    quality: str
    bass: str | None


@dataclass(frozen=True)
class ScaleCollection:
    name: str
    priority: int
    pitch_classes: frozenset[int]


SUPPORTED_QUALITIES = {"maj7", "m7", "7"}
CHROMATIC_COLLECTION = ScaleCollection(
    name="chromatic_fallback",
    priority=99,
    pitch_classes=frozenset(range(12)),
)

# Preferred six-slot color for currently supported chord qualities.
SLOT_INTERVAL_BLUEPRINTS: dict[str, tuple[int, int, int, int, int, int]] = {
    "maj7": (0, 4, 7, 9, 11, 2),
    "m7": (0, 3, 7, 9, 10, 2),
    "7": (0, 4, 7, 9, 10, 2),
}


def _major_collection(root_pc: int) -> frozenset[int]:
    return frozenset((root_pc + i) % 12 for i in (0, 2, 4, 5, 7, 9, 11))


def _diatonic_collection_candidates() -> tuple[ScaleCollection, ...]:
    out: list[ScaleCollection] = []
    for tonic in range(12):
        out.append(
            ScaleCollection(
                name=f"{semitone_to_pitch_class(tonic)}_diatonic",
                priority=1,
                pitch_classes=_major_collection(tonic),
            )
        )
    return tuple(out)


DIATONIC_COLLECTIONS = _diatonic_collection_candidates()


def parse_chord_core(symbol: str) -> ChordCore:
    text = str(symbol).strip()
    left, right = text, None
    if "/" in text:
        left, right = text.split("/", 1)
        right = right.strip() or None

    parsed = parse_chord_symbol(left.strip())
    if parsed["quality"] not in SUPPORTED_QUALITIES:
        raise ValueError(f"Unsupported chord quality: {parsed['quality']}")

    bass: str | None = None
    if right is not None:
        # Slash bass parsing intentionally limited to pitch class only.
        if len(right) >= 2 and right[1] in ("#", "b"):
            bass = right[:2]
        else:
            bass = right[:1]
        if bass:
            pitch_class_to_semitone(bass)

    return ChordCore(symbol=text, root=parsed["root"], quality=parsed["quality"], bass=bass)


def chord_tone_pitch_classes(symbol: str, include_bass: bool = False) -> frozenset[int]:
    core = parse_chord_core(symbol)
    root_pc = pitch_class_to_semitone(core.root)

    if core.quality == "maj7":
        intervals = (0, 4, 7, 11)
    elif core.quality == "m7":
        intervals = (0, 3, 7, 10)
    elif core.quality == "7":
        intervals = (0, 4, 7, 10)
    else:  # pragma: no cover
        raise ValueError(f"Unsupported chord quality: {core.quality}")

    pcs = {(root_pc + i) % 12 for i in intervals}
    if include_bass and core.bass is not None:
        pcs.add(pitch_class_to_semitone(core.bass))
    return frozenset(pcs)


def _normalize_progression(progression: Sequence[str | Sequence[str]]) -> list[str]:
    out: list[str] = []
    for item in progression:
        if isinstance(item, (list, tuple)):
            for s in item:
                text = str(s).strip()
                if text:
                    out.append(text)
        else:
            text = str(item).strip()
            if text:
                out.append(text)
    return out


def _find_distinct_index(
    symbols: Sequence[str],
    current_index: int,
    direction: int,
    *,
    circular: bool,
) -> int | None:
    n = len(symbols)
    if n == 0:
        return None

    current_symbol = symbols[current_index]
    cursor = current_index
    visited = 0

    while visited < n - 1:
        cursor += direction
        if circular:
            cursor %= n
        elif cursor < 0 or cursor >= n:
            return None

        visited += 1
        if symbols[cursor] != current_symbol:
            return cursor

    return None


def build_local_pitch_collection(
    progression: Sequence[str | Sequence[str]],
    index: int,
    *,
    circular: bool = True,
    include_slash_bass: bool = True,
) -> frozenset[int]:
    symbols = _normalize_progression(progression)
    if not symbols:
        raise ValueError("progression must not be empty")
    if index < 0 or index >= len(symbols):
        raise IndexError(f"index out of range: {index}")

    local = set(chord_tone_pitch_classes(symbols[index], include_bass=include_slash_bass))

    prev_idx = _find_distinct_index(symbols, index, -1, circular=circular)
    if prev_idx is not None:
        local.update(chord_tone_pitch_classes(symbols[prev_idx], include_bass=include_slash_bass))

    next_idx = _find_distinct_index(symbols, index, +1, circular=circular)
    if next_idx is not None:
        local.update(chord_tone_pitch_classes(symbols[next_idx], include_bass=include_slash_bass))

    return frozenset(local)


def _collection_scale_intervals_from_root(collection: Iterable[int], root_pc: int) -> tuple[int, ...]:
    rel = sorted(((pc - root_pc) % 12) for pc in collection)
    return tuple(rel)


def _extract_slots_from_heptatonic_intervals(intervals: tuple[int, ...]) -> tuple[int, int, int, int, int, int]:
    if len(intervals) != 7:
        raise ValueError("heptatonic interval extraction requires 7 notes")
    return (
        intervals[0],
        intervals[2],
        intervals[4],
        intervals[5],
        intervals[6],
        intervals[1],
    )


def _chord_quality_constraints(quality: str) -> tuple[int, int, int]:
    if quality == "maj7":
        return (4, 7, 11)
    if quality == "m7":
        return (3, 7, 10)
    if quality == "7":
        return (4, 7, 10)
    raise ValueError(f"Unsupported chord quality: {quality}")


def select_scale_collection(symbol: str, local_pitch_collection: set[int] | frozenset[int]) -> ScaleCollection:
    core = parse_chord_core(symbol)
    root_pc = pitch_class_to_semitone(core.root)
    local = set(local_pitch_collection)

    constrained_third, constrained_fifth, constrained_seventh = _chord_quality_constraints(core.quality)
    desired = SLOT_INTERVAL_BLUEPRINTS[core.quality]

    candidates: list[tuple[int, int, ScaleCollection]] = []
    for candidate in DIATONIC_COLLECTIONS:
        pcs = set(candidate.pitch_classes)
        if not local.issubset(pcs):
            continue

        intervals = _collection_scale_intervals_from_root(pcs, root_pc)
        if 0 not in intervals:
            continue
        if constrained_third not in intervals or constrained_fifth not in intervals or constrained_seventh not in intervals:
            continue
        if len(intervals) != 7:
            continue

        slots = _extract_slots_from_heptatonic_intervals(intervals)
        mismatch_score = sum(2 if i in (3, 5) else 1 for i, (a, b) in enumerate(zip(slots, desired)) if a != b)
        candidates.append((candidate.priority, mismatch_score, candidate))

    if candidates:
        candidates.sort(key=lambda row: (row[0], row[1], row[2].name))
        return candidates[0][2]

    return CHROMATIC_COLLECTION


def extract_output_chord_tone_set(symbol: str, selected_collection: ScaleCollection) -> tuple[int, int, int, int, int, int]:
    core = parse_chord_core(symbol)
    root_pc = pitch_class_to_semitone(core.root)

    if selected_collection == CHROMATIC_COLLECTION:
        intervals = SLOT_INTERVAL_BLUEPRINTS[core.quality]
    else:
        rel = _collection_scale_intervals_from_root(selected_collection.pitch_classes, root_pc)
        if len(rel) != 7 or 0 not in rel:
            intervals = SLOT_INTERVAL_BLUEPRINTS[core.quality]
        else:
            intervals = _extract_slots_from_heptatonic_intervals(rel)

    return tuple((root_pc + i) % 12 for i in intervals)


def output_chord_tone_names(symbol: str, progression: Sequence[str | Sequence[str]], index: int) -> tuple[str, ...]:
    local = build_local_pitch_collection(progression, index)
    selected = select_scale_collection(symbol, local)
    tones = extract_output_chord_tone_set(symbol, selected)
    return tuple(semitone_to_pitch_class(pc) for pc in tones)
