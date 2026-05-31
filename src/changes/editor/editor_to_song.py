"""Convert EditorState to SongModel.

Pipeline:
  EditorState.cells
  -> split at | and || into measure buffers
  -> resolve % to previous chord
  -> fill empty buffers with previous chord
  -> distribute equal duration across cells in each buffer
  -> merge consecutive same-chord cells into single HarmonyEvent
  -> build Measure / SongModel
"""

from __future__ import annotations

from fractions import Fraction

from changes.editor.editor_state import EditorState
from changes.models.song_model import HarmonyEvent, Measure, SongModel


def _parse_meter(meter: str) -> tuple[int, int]:
    parts = meter.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid meter: {meter!r}")
    num, den = int(parts[0]), int(parts[1])
    if num <= 0 or den <= 0:
        raise ValueError(f"Invalid meter: {meter!r}")
    return num, den


def _next_section_label(current: str) -> str:
    return chr(ord(current) + 1)


def editor_to_song_model(state: EditorState) -> SongModel:
    title = state.title.strip() or "NO TITLE"
    tempo = Fraction(state.tempo)
    meter_num, meter_den = _parse_meter(state.meter)
    measure_length = Fraction(4 * meter_num, meter_den)

    measures: list[Measure] = []
    measure_number = 0
    absolute_start = Fraction(0)
    last_chord: str | None = None
    current_section_label = "A"

    def flush(buffer: list[str]) -> None:
        nonlocal measure_number, absolute_start, last_chord

        # Determine effective chord tokens for this measure
        if not buffer:
            if last_chord is None:
                return  # leading empty measure before any chord — skip
            chord_tokens: list[str] = [last_chord]
        else:
            chord_tokens = buffer

        # Resolve % tokens
        resolved: list[str] = []
        for token in chord_tokens:
            if token == "%":
                if last_chord is None:
                    raise ValueError("'%' used before any chord has been entered")
                resolved.append(last_chord)
            else:
                resolved.append(token)
                last_chord = token

        if not resolved:
            return

        # Equal duration per cell, then merge consecutive same-chord
        duration_each = measure_length / len(resolved)
        merged: list[list] = []
        for symbol in resolved:
            if merged and merged[-1][0] == symbol:
                merged[-1][1] += duration_each
            else:
                merged.append([symbol, duration_each])

        # Build Measure
        section_id = f"{current_section_label}__OCC1"
        measure_number += 1
        offset = Fraction(0)
        harmony: list[HarmonyEvent] = []
        for h_index, (symbol, dur) in enumerate(merged, start=1):
            harmony.append(
                HarmonyEvent(
                    id=f"m{measure_number}_h{h_index}",
                    symbol=symbol,
                    measure_number=measure_number,
                    offset_quarters=offset,
                    duration_quarters=dur,
                )
            )
            offset += dur

        measures.append(
            Measure(
                number=measure_number,
                section_id=section_id,
                meter_numerator=meter_num,
                meter_denominator=meter_den,
                absolute_start_quarters=absolute_start,
                harmony=tuple(harmony),
            )
        )
        absolute_start += measure_length

    # Scan cells
    current_buffer: list[str] = []
    for cell in state.cells:
        if cell == "||":
            flush(current_buffer)
            current_buffer = []
            current_section_label = _next_section_label(current_section_label)
        elif cell == "|":
            flush(current_buffer)
            current_buffer = []
        else:
            current_buffer.append(cell)

    # Trailing tokens after the last barline (or the whole input if no barlines).
    # Empty trailing buffer is skipped — a trailing | is only a visual close, not a new measure.
    if current_buffer:
        flush(current_buffer)

    if not measures:
        raise ValueError("Editor state produced no measures")

    return SongModel(
        title=title,
        working_key=state.working_key or None,
        performance_tempo=tempo,
        measures=tuple(measures),
    )
