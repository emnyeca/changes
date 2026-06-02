"""Phase 2 pure Chord register realization.

This module converts 2–6 Chord pitch classes into ascending MIDI notes inside
the configured Chord register.  Voice count matches the pitch-class input:
6 mandatory notes → 6 realized notes; 3 mandatory notes → 3, and so on.
The velocity profile always stores 6 slots; outputs are sliced to match.

It intentionally does not integrate with renderer roles, Track 8 mapping,
MIDI export, SysEx export, or bundle planning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .chord_engine import ChordConstructionResult


class ChordRealizationError(ValueError):
    """Raised when Chord register realization cannot produce a valid result.

    Valid results have 2–6 distinct pitch classes that fit within the register.
    """


CHORD_REGISTER_MIN_MIDI = 48
CHORD_REGISTER_MAX_MIDI = 69


@dataclass(frozen=True)
class ChordRegisterPolicy:
    min_midi: int = CHORD_REGISTER_MIN_MIDI
    max_midi: int = CHORD_REGISTER_MAX_MIDI


ChordLengthMode = Literal["explicit_event_length", "inherit"]


@dataclass(frozen=True)
class ChordPerformancePolicy:
    velocity_low_to_high: tuple[int, ...] = (70, 70, 70, 50, 70, 50)
    length_mode: ChordLengthMode = "explicit_event_length"


@dataclass(frozen=True)
class ChordRealizationResult:
    source_symbol: str
    source_pitch_classes: tuple[int, ...]
    canonical_stacked_midi_notes: tuple[int, ...]
    realized_midi_notes: tuple[int, ...]
    velocities: tuple[int, ...]
    length_mode: ChordLengthMode
    diagnostics: tuple[str, ...]


def _validate_source_pitch_classes(source_pitch_classes: tuple[int, ...]) -> None:
    if len(source_pitch_classes) < 2 or len(source_pitch_classes) > 6:
        raise ChordRealizationError(
            f"Chord realization requires 2 to 6 pitch classes: {source_pitch_classes}"
        )
    if len(set(source_pitch_classes)) != len(source_pitch_classes):
        raise ChordRealizationError(
            f"Chord realization requires distinct pitch classes: {source_pitch_classes}"
        )
    bad = [pc for pc in source_pitch_classes if pc < 0 or pc > 11]
    if bad:
        raise ChordRealizationError(
            f"Chord realization pitch classes must be in 0..11: {source_pitch_classes}"
        )


def _validate_register_policy(register_policy: ChordRegisterPolicy) -> None:
    if register_policy.min_midi >= register_policy.max_midi:
        raise ChordRealizationError(
            f"Chord register requires min_midi < max_midi: {register_policy.min_midi} >= {register_policy.max_midi}"
        )


def _validate_velocity_profile(performance_policy: ChordPerformancePolicy) -> None:
    profile = performance_policy.velocity_low_to_high
    if len(profile) != 6:
        raise ChordRealizationError(
            f"Chord velocity profile must contain exactly six values: {profile}"
        )
    if any((not isinstance(v, int)) for v in profile):
        raise ChordRealizationError(
            f"Chord velocity profile values must be integers: {profile}"
        )
    bad = [v for v in profile if v < 1 or v > 127]
    if bad:
        raise ChordRealizationError(
            f"Chord velocity profile values must be in 1..127: {profile}"
        )
    if performance_policy.length_mode not in ("explicit_event_length", "inherit"):
        raise ChordRealizationError(
            f"Unsupported chord length mode: {performance_policy.length_mode}"
        )


def _lowest_midi_at_or_above(start_midi: int, pitch_class: int) -> int:
    return start_midi + ((pitch_class - start_midi) % 12)


def _build_canonical_stack(source_pitch_classes: tuple[int, ...], min_midi: int) -> tuple[int, ...]:
    stacked: list[int] = []
    first = _lowest_midi_at_or_above(min_midi, source_pitch_classes[0])
    stacked.append(first)
    for pitch_class in source_pitch_classes[1:]:
        next_note = _lowest_midi_at_or_above(stacked[-1] + 1, pitch_class)
        stacked.append(next_note)
    return tuple(stacked)


def _fold_to_register(
    canonical_stacked: tuple[int, ...],
    *,
    min_midi: int,
    max_midi: int,
) -> tuple[int, ...]:
    folded: list[int] = []
    for note in canonical_stacked:
        current = note
        while current > max_midi:
            current -= 12
        if current < min_midi:
            raise ChordRealizationError(
                "Chord realization failed after octave fold: "
                f"note {note} folded below register {min_midi}..{max_midi}"
            )
        folded.append(current)
    return tuple(folded)


def realize_chord_register(
    construction: ChordConstructionResult,
    *,
    register_policy: ChordRegisterPolicy = ChordRegisterPolicy(),
    performance_policy: ChordPerformancePolicy = ChordPerformancePolicy(),
) -> ChordRealizationResult:
    source_pitch_classes = tuple(construction.final_pitch_classes)
    _validate_source_pitch_classes(source_pitch_classes)
    _validate_register_policy(register_policy)
    _validate_velocity_profile(performance_policy)

    canonical_stacked = _build_canonical_stack(source_pitch_classes, register_policy.min_midi)
    folded_unsorted = _fold_to_register(
        canonical_stacked,
        min_midi=register_policy.min_midi,
        max_midi=register_policy.max_midi,
    )

    realized_midi_notes = tuple(sorted(folded_unsorted))
    if len(set(realized_midi_notes)) != len(realized_midi_notes):
        raise ChordRealizationError(
            "Chord realization produced duplicate MIDI notes after fold/sort: "
            f"source_pitch_classes={source_pitch_classes} canonical_stacked={canonical_stacked} "
            f"folded_unsorted={folded_unsorted}"
        )
    if any((note < register_policy.min_midi or note > register_policy.max_midi) for note in realized_midi_notes):
        raise ChordRealizationError(
            "Chord realization produced out-of-range notes: "
            f"realized={realized_midi_notes} register={register_policy.min_midi}..{register_policy.max_midi}"
        )

    velocities = tuple(performance_policy.velocity_low_to_high[:len(realized_midi_notes)])
    diagnostics = (
        f"source_symbol={construction.source_symbol}",
        f"source_pitch_classes={source_pitch_classes}",
        f"register_min_midi={register_policy.min_midi}",
        f"register_max_midi={register_policy.max_midi}",
        f"canonical_stacked_midi_notes={canonical_stacked}",
        f"folded_unsorted_midi_notes={folded_unsorted}",
        f"realized_midi_notes={realized_midi_notes}",
        f"velocities={velocities}",
        f"length_mode={performance_policy.length_mode}",
    )

    return ChordRealizationResult(
        source_symbol=construction.source_symbol,
        source_pitch_classes=source_pitch_classes,
        canonical_stacked_midi_notes=canonical_stacked,
        realized_midi_notes=realized_midi_notes,
        velocities=velocities,
        length_mode=performance_policy.length_mode,
        diagnostics=diagnostics,
    )
