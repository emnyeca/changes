"""Minimal Streamlit UI for Changes.

Features:
- Drag-and-drop YAML progression file
- Tempo input
- Generate MIDI file
- Send voicings to a selected MIDI output port
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from math import lcm
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import streamlit as st
import yaml

from changes.midi_writer import write_midi_with_events
from changes.note import midi_to_note_name, pitch_class_to_semitone
from changes.voicing import progression_to_voicings
from changes.voice_leading import generate_voice_leading

try:
    import mido
except Exception:  # pragma: no cover
    mido = None


APP_DATA_DIR = Path.home() / "HarmonyCloud" / "progressions"
_ROOT_RE = re.compile(r"^\s*(?P<root>[A-G](?:#|b)?)")


def _ensure_app_data_dir() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _section_output_path(base_output_path: str, section_name: str) -> str:
    target = Path(base_output_path)
    safe_section = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in section_name)
    if not safe_section:
        safe_section = "section"

    stem = target.stem or "changes_output"
    suffix = target.suffix or ".mid"
    return str(target.with_name(f"{stem}_{safe_section}{suffix}"))


def _list_saved_yaml_files() -> List[Path]:
    _ensure_app_data_dir()
    files = list(APP_DATA_DIR.glob("*.yaml")) + list(APP_DATA_DIR.glob("*.yml"))
    return sorted(files, key=lambda p: p.name.lower())


def _save_uploaded_yaml(uploaded_name: str, uploaded_bytes: bytes, overwrite: bool = False) -> Path:
    _ensure_app_data_dir()
    safe_name = Path(uploaded_name).name
    destination = APP_DATA_DIR / safe_name
    if destination.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {destination.name}")
    destination.write_bytes(uploaded_bytes)
    return destination


def _delete_saved_yaml(file_name: str) -> None:
    target = APP_DATA_DIR / file_name
    if target.exists():
        target.unlink()


def _rename_saved_yaml(old_name: str, new_name: str) -> Path:
    source = APP_DATA_DIR / old_name
    if not source.exists():
        raise FileNotFoundError(f"Not found: {old_name}")

    candidate = Path(new_name.strip()).name
    if not candidate:
        raise ValueError("新しいファイル名が空です、E)

    if not (candidate.endswith(".yaml") or candidate.endswith(".yml")):
        candidate = f"{candidate}.yaml"

    destination = APP_DATA_DIR / candidate
    if destination.exists() and destination != source:
        raise FileExistsError(f"同名ファイルが既に存在しまぁE {destination.name}")

    source.rename(destination)
    return destination


def _normalize_section_names(raw_names: List[str]) -> List[str]:
    """Normalize repeated rehearsal marks by appending count (A, A2, A3...)."""
    seen: Dict[str, int] = {}
    normalized: List[str] = []
    for raw in raw_names:
        name = raw.strip() or "A"
        seen[name] = seen.get(name, 0) + 1
        count = seen[name]
        normalized.append(name if count == 1 else f"{name}{count}")
    return normalized


def _parse_time_signature(ts: str | None) -> Tuple[int | None, int | None]:
    if not ts:
        return None, None
    parts = ts.strip().split("/")
    if len(parts) != 2:
        return None, None
    try:
        num = int(parts[0])
        den = int(parts[1])
    except ValueError:
        return None, None
    if num <= 0 or den <= 0:
        return None, None
    return num, den


def _parse_uploaded_yaml_payload(uploaded_bytes: bytes) -> Dict[str, object]:
    """Parse both legacy and section-aware YAML formats."""
    data = yaml.safe_load(uploaded_bytes)

    if data is None:
        raise ValueError("YAML is empty.")

    if isinstance(data, list):
        bars = [[str(x).strip()] for x in data if str(x).strip()]
        return {
            "name": None,
            "key": None,
            "tempo": None,
            "time_signature": None,
            "sections": [{"name": "A", "progression": bars}],
        }

    if isinstance(data, dict):
        name = data.get("name")
        key = data.get("key")
        tempo_raw = data.get("tempo")
        tempo = int(tempo_raw) if isinstance(tempo_raw, int) else None
        ts_raw = data.get("time_signature")
        time_signature = str(ts_raw) if isinstance(ts_raw, str) else None

        sections = data.get("sections")
        if isinstance(sections, list):
            raw_names: List[str] = []
            raw_progressions: List[List[List[str]]] = []

            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                sec_name = str(sec.get("name") or "A").strip() or "A"
                progression = sec.get("progression")
                if not isinstance(progression, list):
                    continue

                bars: List[List[str]] = []
                for item in progression:
                    if isinstance(item, list):
                        bar = [str(x).strip() for x in item if str(x).strip()]
                        if bar:
                            bars.append(bar)
                    else:
                        s = str(item).strip()
                        if s:
                            bars.append([s])

                if bars:
                    raw_names.append(sec_name)
                    raw_progressions.append(bars)

            if raw_progressions:
                norm_names = _normalize_section_names(raw_names)
                norm_sections = [
                    {"name": section_name, "progression": progression}
                    for section_name, progression in zip(norm_names, raw_progressions)
                ]
                return {
                    "name": name,
                    "key": key,
                    "tempo": tempo,
                    "time_signature": time_signature,
                    "sections": norm_sections,
                }

        progression = data.get("progression")
        if isinstance(progression, list):
            bars: List[List[str]] = []
            for item in progression:
                if isinstance(item, list):
                    bar = [str(x).strip() for x in item if str(x).strip()]
                    if bar:
                        bars.append(bar)
                else:
                    s = str(item).strip()
                    if s:
                        bars.append([s])
            if bars:
                return {
                    "name": name,
                    "key": key,
                    "tempo": tempo,
                    "time_signature": time_signature,
                    "sections": [{"name": "A", "progression": bars}],
                }

    raise ValueError("YAML must contain progression or sections/progression.")


def _extract_bars_with_meta(payload: Dict[str, object]) -> Tuple[List[List[str]], List[Dict[str, object]]]:
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return [], []

    bars: List[List[str]] = []
    meta: List[Dict[str, object]] = []

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("name") or "A")
        progression = section.get("progression")
        if not isinstance(progression, list):
            continue

        for bar_index, bar in enumerate(progression, start=1):
            if isinstance(bar, list):
                cleaned = [str(x).strip() for x in bar if str(x).strip()]
                if cleaned:
                    bars.append(cleaned)
                    meta.append({"section": section_name, "bar_in_section": bar_index})

    return bars, meta


def _parse_uploaded_yaml_bars(uploaded_bytes: bytes) -> List[List[str]]:
    """Compatibility helper for existing tests."""
    payload = _parse_uploaded_yaml_payload(uploaded_bytes)
    bars, _ = _extract_bars_with_meta(payload)
    if not bars:
        raise ValueError("YAML must contain a progression list (e.g. progression: [[Dm7, G7, Cmaj7]]).")
    return bars


def _build_voicings_from_bars(chord_bars: List[List[str]]) -> List[List[int]]:
    raw_voicings = progression_to_voicings(chord_bars)
    return generate_voice_leading(raw_voicings)


def _build_note_triggers(
    events: List[Dict[str, int | str]],
    voicings: List[List[int]],
) -> List[List[Dict[str, int]]]:
    """Build per-event trigger list with hold duration for each voice.

    A trigger is emitted only when a voice pitch changes from the previous event.
    """
    count = min(len(events), len(voicings))
    if count == 0:
        return []

    max_voices = max(len(v) for v in voicings[:count])
    triggers: List[List[Dict[str, int]]] = [[] for _ in range(count)]

    for voice_idx in range(max_voices):
        idx = 0
        while idx < count:
            chord = voicings[idx]
            note = int(chord[voice_idx]) if voice_idx < len(chord) else None
            if note is None:
                idx += 1
                continue

            prev_note = None
            if idx > 0 and voice_idx < len(voicings[idx - 1]):
                prev_note = int(voicings[idx - 1][voice_idx])

            if prev_note == note:
                idx += 1
                continue

            hold_steps = 0
            j = idx
            while j < count:
                next_chord = voicings[j]
                next_note = int(next_chord[voice_idx]) if voice_idx < len(next_chord) else None
                if next_note != note:
                    break
                hold_steps += int(events[j]["duration_steps"])
                j += 1

            triggers[idx].append(
                {
                    "voice": voice_idx,
                    "note": note,
                    "duration_steps": hold_steps,
                }
            )
            idx += 1

    return triggers


def _format_trigger_event_lines(
    events: List[Dict[str, int | str]],
    voicings: List[List[int]],
) -> List[str]:
    """Format trigger events in a hold-aware human-readable style."""
    count = min(len(events), len(voicings))
    triggers = _build_note_triggers(events, voicings)
    lines: List[str] = []

    for idx in range(count):
        event = events[idx]
        event_triggers = sorted(triggers[idx], key=lambda x: int(x["voice"])) if idx < len(triggers) else []

        if event_triggers:
            parts = []
            for item in event_triggers:
                note_name = midi_to_note_name(int(item["note"]))
                parts.append(
                    f"[{int(item['voice'])}:{note_name} duration:{int(item['duration_steps'])}]"
                )
            note_text = " ".join(parts)
        else:
            note_text = "(hold)"

        lines.append(
            f"Step:{int(event['step'])} コーチE\"{str(event['chord'])}\" {note_text}"
        )

    return lines


def _format_basic_event_lines(
    events: List[Dict[str, int | str]],
    voicings: List[List[int]],
) -> List[str]:
    """Format events without hold merge (all voices are triggered each step)."""
    count = min(len(events), len(voicings))
    lines: List[str] = []

    for idx in range(count):
        event = events[idx]
        notes = voicings[idx]
        duration = int(event["duration_steps"])
        parts = [
            f"[{voice_idx}:{midi_to_note_name(int(note))} duration:{duration}]"
            for voice_idx, note in enumerate(notes)
        ]
        note_text = " ".join(parts) if parts else "(rest)"
        lines.append(f'Step:{int(event["step"])} コーチE"{str(event["chord"])}" {note_text}')

    return lines


def _resolve_channel_map(raw_values: List[int | None]) -> List[int | None]:
    """Clamp channel assignments into valid MIDI range 1..16 or disable with None."""
    channels: List[int | None] = []
    for value in raw_values:
        if value is None:
            channels.append(None)
        else:
            channels.append(max(1, min(16, int(value))))
    return channels


def _channel_option_to_value(option: str) -> int | None:
    if option == "送らなぁE:
        return None
    return int(option)


def _channel_value_to_option(channel: int | None) -> str:
    return "送らなぁE if channel is None else str(int(channel))


def _extract_chord_root(chord_symbol: str) -> str:
    base = chord_symbol.split("/", 1)[0]
    m = _ROOT_RE.match(base)
    if not m:
        raise ValueError(f"Unsupported chord symbol for bass root: {chord_symbol}")
    return m.group("root")


def _extract_slash_bass_root(chord_symbol: str) -> str | None:
    if "/" not in chord_symbol:
        return None
    slash = chord_symbol.split("/", 1)[1].strip()
    m = _ROOT_RE.match(slash)
    if not m:
        return None
    return m.group("root")


def _fit_bass_range_c1_b1(note: int) -> int:
    while note < 24:
        note += 12
    while note > 35:
        note -= 12
    return note


def _root_to_bass_note(chord_symbol: str) -> int:
    root = _extract_chord_root(chord_symbol)
    semitone = pitch_class_to_semitone(root)
    return _fit_bass_range_c1_b1(24 + semitone)


def _build_bassline_notes(
    events: Sequence[Dict[str, int | str]],
    switch_every: int,
    switch_enabled: bool,
) -> List[int]:
    """Build bass notes with optional root/fifth switching.

    - Default: chord root (or slash bass when provided).
    - With switching enabled: root/fifth alternation after repeated same-note count.
    - For slash chords with switching enabled: first note uses slash bass once,
      then root/fifth alternation is based on chord root.
    """
    if switch_every < 1:
        switch_every = 1

    notes: List[int] = []
    current_mode = "root"
    same_note_count = 0
    previous_output: int | None = None
    previous_harmony_key: tuple[int, int | None] | None = None
    slash_consumed = False

    for event in events:
        chord = str(event["chord"])
        root_note = _root_to_bass_note(chord)
        slash_root = _extract_slash_bass_root(chord)
        slash_note = _fit_bass_range_c1_b1(24 + pitch_class_to_semitone(slash_root)) if slash_root else None
        harmony_key = (root_note, slash_note)

        if previous_harmony_key != harmony_key:
            current_mode = "root"
            same_note_count = 0
            slash_consumed = False

        if switch_enabled and slash_note is not None and not slash_consumed:
            candidate = slash_note
            slash_consumed = True
        elif switch_enabled:
            candidate = root_note if current_mode == "root" else _fit_bass_range_c1_b1(root_note + 7)
        else:
            candidate = slash_note if slash_note is not None else root_note

        if switch_enabled:
            if previous_output == candidate:
                same_note_count += 1
            else:
                same_note_count = 1

            if same_note_count >= switch_every:
                current_mode = "fifth" if current_mode == "root" else "root"
                candidate = root_note if current_mode == "root" else _fit_bass_range_c1_b1(root_note + 7)
                same_note_count = 1

        notes.append(candidate)
        previous_output = candidate
        previous_harmony_key = harmony_key

    return notes


def _append_bass_track(voicings: Sequence[Sequence[int]], bass_notes: Sequence[int]) -> List[List[int]]:
    count = min(len(voicings), len(bass_notes))
    combined: List[List[int]] = []
    for idx in range(count):
        combined.append([int(n) for n in voicings[idx]] + [int(bass_notes[idx])])
    return combined


def _transpose_output_voicings(
    voicings: Sequence[Sequence[int]],
    chord_octave_shift: int,
    bass_octave_shift: int,
) -> List[List[int]]:
    """Transpose output notes per group: chord voices and bass voice."""
    shifted: List[List[int]] = []
    chord_delta = int(chord_octave_shift) * 12
    bass_delta = int(bass_octave_shift) * 12

    for chord in voicings:
        out_notes: List[int] = []
        for idx, note in enumerate(chord):
            delta = chord_delta if idx < 6 else bass_delta
            transposed = int(note) + delta
            out_notes.append(max(0, min(127, transposed)))
        shifted.append(out_notes)

    return shifted


def _format_chord_voicing_lines(
    events: List[Dict[str, int | str]],
    voicings: List[List[int]],
) -> List[str]:
    """Format each chord + 6-voice voicing grouped by section/bar."""
    lines: List[str] = []
    count = min(len(events), len(voicings))

    current_bar_key: Tuple[str, int] | None = None
    last_section = ""
    current_prefix = ""

    for idx in range(count):
        event = events[idx]
        section = str(event.get("section") or "A")
        bar_in_section = int(event.get("bar_in_section") or 1)
        chord = str(event["chord"])
        notes = voicings[idx]
        formatted_notes = ",".join(
            f"{voice_idx}:{midi_to_note_name(int(note))}"
            for voice_idx, note in enumerate(notes)
        )

        bar_key = (section, bar_in_section)
        chord_in_bar = int(event.get("chord_in_bar") or 0)
        row = f'[{chord_in_bar}: "{chord}" [{formatted_notes}]]'

        if bar_key != current_bar_key:
            if section != last_section:
                current_prefix = f"{section} bar{bar_in_section}:"
                last_section = section
            else:
                current_prefix = f"  bar{bar_in_section}:"

            lines.append(f"{current_prefix}{row}")
            current_bar_key = bar_key
        else:
            lines.append(f"{' ' * len(current_prefix)}{row}")

    return lines


def _build_event_schedule(
    chord_bars: List[List[str]],
    meter_numerator: int,
    meter_denominator: int,
    bar_meta: List[Dict[str, object]] | None = None,
) -> Tuple[int, int, List[Dict[str, int | str]]]:
    """Build bar-aware schedule using minimal common bar subdivision.

    For mixed events-per-bar, use minimal steps-per-bar that can represent all bars:
    - steps_per_bar = lcm(event_count_each_bar...)
    """
    if not chord_bars:
        return 0, 0, []

    event_counts = [len(bar) for bar in chord_bars if len(bar) > 0]
    if not event_counts:
        return 0, 0, []

    steps_per_bar = 1
    for count in event_counts:
        steps_per_bar = lcm(steps_per_bar, count)

    events: List[Dict[str, int | str]] = []
    event_index = 0

    for bar_index, bar in enumerate(chord_bars):
        if not bar:
            continue

        meta = bar_meta[bar_index] if bar_meta and bar_index < len(bar_meta) else {}
        section_name = str(meta.get("section") or "A")
        bar_in_section = int(meta.get("bar_in_section") or (bar_index + 1))

        duration_steps = steps_per_bar // len(bar)
        bar_start_step = bar_index * steps_per_bar + 1

        for chord_index, chord in enumerate(bar):
            events.append(
                {
                    "event_index": event_index,
                    "bar": bar_index + 1,
                    "bar_in_section": bar_in_section,
                    "section": section_name,
                    "chord_in_bar": chord_index,
                    "step": bar_start_step + chord_index * duration_steps,
                    "duration_steps": duration_steps,
                    "chord": chord,
                }
            )
            event_index += 1

    total_length = steps_per_bar * len(chord_bars)
    return steps_per_bar, total_length, events


def _compute_digitone_tempo_for_same_duration(
    input_tempo: int,
    meter_numerator: int,
    meter_denominator: int,
    steps_per_bar: int,
) -> int:
    """Compute Digitone tempo (Speed=1/8) that matches input musical duration.

    tempo_out = tempo_in * (steps_per_bar / eighths_per_bar)
    where eighths_per_bar = numerator * (8 / denominator)
    """
    eighths_per_bar = meter_numerator * (8.0 / meter_denominator)
    if eighths_per_bar <= 0:
        return max(1, int(input_tempo))
    tempo_out = float(input_tempo) * (float(steps_per_bar) / eighths_per_bar)
    return max(1, int(round(tempo_out)))


def _seconds_for_input_tempo(
    bars_count: int,
    meter_numerator: int,
    meter_denominator: int,
    input_tempo: int,
) -> float:
    """Total musical time for all bars at the input tempo."""
    beats_per_bar_quarter = float(meter_numerator) * (4.0 / float(meter_denominator))
    total_quarter_beats = float(bars_count) * beats_per_bar_quarter
    return total_quarter_beats * (60.0 / float(input_tempo))


def _seconds_for_send_tempo(
    length_steps: int,
    send_tempo: int,
) -> float:
    """Total send time at Speed=1/8 for given sequence length."""
    step_seconds = 30.0 / float(send_tempo)
    return float(length_steps) * step_seconds


def _apply_digitone_tempo_floor(
    tempo: int,
    length: int,
    events: List[Dict[str, int | str]],
) -> Tuple[int, int, List[Dict[str, int | str]]]:
    """Keep Digitone tempo >= 30 by doubling tempo/Length/step durations."""
    adjusted_tempo = int(tempo)
    scale = 1
    while adjusted_tempo < 30:
        adjusted_tempo *= 2
        scale *= 2

    if scale == 1:
        return adjusted_tempo, int(length), events

    scaled_events: List[Dict[str, int | str]] = []
    for event in events:
        scaled_events.append(
            {
                **event,
                "step": int(event["step"]) * scale,
                "duration_steps": int(event["duration_steps"]) * scale,
            }
        )

    return adjusted_tempo, int(length) * scale, scaled_events


def _send_with_optional_debug(
    voicings: List[List[int]],
    events: List[Dict[str, int | str]],
    send_tempo: int,
    selected_port: str,
    hold_same_pitch: bool,
    channel_map: List[int | None],
    per_voice_hold: List[bool] | None = None,
) -> List[str]:
    """Send MIDI or simulate send in DEBUG mode; return send logs."""
    logs: List[str] = []
    # Speed is fixed at 1/8 in this app.
    step_seconds = 30.0 / float(send_tempo)

    count = min(len(events), len(voicings))
    if count == 0:
        return logs

    max_voices = max(len(v) for v in voicings[:count])
    channels = _resolve_channel_map(channel_map)
    hold_per_voice = list(per_voice_hold) if per_voice_hold is not None else []
    if len(hold_per_voice) < max_voices:
        hold_per_voice.extend([hold_same_pitch] * (max_voices - len(hold_per_voice)))

    def _voice_note(chord: List[int], voice_idx: int) -> int | None:
        return int(chord[voice_idx]) if voice_idx < len(chord) else None

    previous_chord: List[int] | None = None

    if selected_port == "DEBUG":
        debug_epoch = time.time()
        debug_elapsed = 0.0
        logs.append("Transport:start")
        for idx in range(count):
            event = events[idx]
            chord_notes = voicings[idx]
            triggered: List[str] = []

            for voice_idx in range(max_voices):
                prev_note = _voice_note(previous_chord, voice_idx) if previous_chord is not None else None
                cur_note = _voice_note(chord_notes, voice_idx)
                ch = channels[voice_idx] if voice_idx < len(channels) else 1
                if ch is None:
                    continue
                voice_hold = bool(hold_per_voice[voice_idx])

                if voice_hold:
                    if cur_note is not None and cur_note != prev_note:
                        triggered.append(f"v{voice_idx}:ch{ch}:{midi_to_note_name(cur_note)}")
                else:
                    if cur_note is not None:
                        triggered.append(f"v{voice_idx}:ch{ch}:{midi_to_note_name(cur_note)}")

            duration = step_seconds * int(event["duration_steps"])
            ts = datetime.fromtimestamp(debug_epoch + debug_elapsed).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            trigger_text = " ".join(f"[{x}]" for x in triggered) if triggered else "[hold]"
            logs.append(f"Send:{ts} コーチE{str(event['chord'])} {trigger_text} duration:{duration:.3f}s")
            debug_elapsed += duration
            previous_chord = chord_notes
        logs.append("Transport:stop")
        return logs

    if mido is None:
        raise RuntimeError("mido が未導�Eです、EEBUG を使ぁE�� realtime 依存を導�Eしてください、E)

    with mido.open_output(selected_port) as outport:
        outport.send(mido.Message("start"))
        try:
            for idx in range(count):
                event = events[idx]
                chord_notes = voicings[idx]
                triggered: List[str] = []

                started_at = time.time()
                ts = datetime.fromtimestamp(started_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                for voice_idx in range(max_voices):
                    prev_note = _voice_note(previous_chord, voice_idx) if previous_chord is not None else None
                    cur_note = _voice_note(chord_notes, voice_idx)
                    ch_val = channels[voice_idx] if voice_idx < len(channels) else 1
                    if ch_val is None:
                        continue
                    ch = ch_val - 1
                    voice_hold = bool(hold_per_voice[voice_idx])

                    if voice_hold:
                        if prev_note is not None and prev_note != cur_note:
                            outport.send(mido.Message("note_off", note=int(prev_note), velocity=0, channel=ch))
                        if cur_note is not None and prev_note != cur_note:
                            outport.send(mido.Message("note_on", note=int(cur_note), velocity=100, channel=ch))
                            triggered.append(f"v{voice_idx}:ch{ch_val}:{midi_to_note_name(cur_note)}")
                    else:
                        if cur_note is not None:
                            outport.send(mido.Message("note_on", note=int(cur_note), velocity=100, channel=ch))
                            triggered.append(f"v{voice_idx}:ch{ch_val}:{midi_to_note_name(cur_note)}")

                time.sleep(step_seconds * int(event["duration_steps"]))

                duration_actual = time.time() - started_at
                trigger_text = " ".join(f"[{x}]" for x in triggered) if triggered else "[hold]"
                logs.append(f"Send:{ts} コーチE{str(event['chord'])} {trigger_text} duration:{duration_actual:.3f}s")
                if any(not bool(hold_per_voice[v]) for v in range(max_voices)):
                    for voice_idx in range(max_voices):
                        if bool(hold_per_voice[voice_idx]):
                            continue
                        cur_note = _voice_note(chord_notes, voice_idx)
                        ch_val = channels[voice_idx] if voice_idx < len(channels) else 1
                        if ch_val is None:
                            continue
                        if cur_note is not None:
                            outport.send(
                                mido.Message(
                                    "note_off",
                                    note=int(cur_note),
                                    velocity=0,
                                    channel=ch_val - 1,
                                )
                            )

                previous_chord = chord_notes

            if previous_chord is not None:
                for voice_idx in range(max_voices):
                    if not bool(hold_per_voice[voice_idx]):
                        continue
                    note = _voice_note(previous_chord, voice_idx)
                    ch_val = channels[voice_idx] if voice_idx < len(channels) else 1
                    if ch_val is None:
                        continue
                    if note is not None:
                        outport.send(
                            mido.Message(
                                "note_off",
                                note=int(note),
                                velocity=0,
                                channel=ch_val - 1,
                            )
                        )
        finally:
            outport.send(mido.Message("stop"))

    return logs


def _send_len_note_test_events(
    selected_port: str,
    note_channel: int,
    cc_channel: int,
    velocity: int,
    note_off_delay_ms: int,
    cc_to_note_delay_ms: int,
    sequence_events: Sequence[tuple[int, int]],
    inter_event_delay_ms: int = 0,
) -> List[str]:
    """Send CC#5 LEN then note events for Digitone STEP RECORDING debug."""
    logs: List[str] = []

    def _timestamp() -> str:
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def _log(line: str) -> None:
        logs.append(f"[{_timestamp()}] {line}")

    note_ch = max(1, min(16, int(note_channel)))
    cc_ch = max(1, min(16, int(cc_channel)))
    vel = max(1, min(127, int(velocity)))
    cc_wait = max(0, int(cc_to_note_delay_ms)) / 1000.0
    off_wait = max(0, int(note_off_delay_ms)) / 1000.0
    between_wait = max(0, int(inter_event_delay_ms)) / 1000.0

    def _emit_event(outport: mido.ports.BaseOutput | None, cc_value: int, note: int) -> None:
        cc_val = max(0, min(127, int(cc_value)))
        midi_note = max(0, min(127, int(note)))

        if outport is not None:
            outport.send(mido.Message("control_change", channel=cc_ch - 1, control=5, value=cc_val))
        _log(f"CC ch={cc_ch} controller=5 value={cc_val}")

        if cc_wait > 0:
            time.sleep(cc_wait)

        if outport is not None:
            outport.send(mido.Message("note_on", channel=note_ch - 1, note=midi_note, velocity=vel))
        _log(f"NOTE_ON ch={note_ch} note={midi_note}({midi_to_note_name(midi_note)}) velocity={vel}")

        if off_wait > 0:
            time.sleep(off_wait)

        if outport is not None:
            outport.send(mido.Message("note_off", channel=note_ch - 1, note=midi_note, velocity=0))
        _log(f"NOTE_OFF ch={note_ch} note={midi_note}({midi_to_note_name(midi_note)}) velocity=0")

    if selected_port == "DEBUG":
        for idx, (cc_value, note) in enumerate(sequence_events):
            _emit_event(None, cc_value, note)
            if idx < len(sequence_events) - 1 and between_wait > 0:
                time.sleep(between_wait)
        return logs

    if mido is None:
        raise RuntimeError("mido が未導�Eです、EEBUG を使ぁE�� realtime 依存を導�Eしてください、E)

    with mido.open_output(selected_port) as outport:
        for idx, (cc_value, note) in enumerate(sequence_events):
            _emit_event(outport, cc_value, note)
            if idx < len(sequence_events) - 1 and between_wait > 0:
                time.sleep(between_wait)

    return logs


def main() -> None:
    st.set_page_config(page_title="Changes", layout="centered")
    st.title("Changes  EMinimal UI")
    st.caption("YAMLをドラチE��&ドロチE�Eして、MIDI生�Eまた�EDigitone IIへ送信")

    saved_files = _list_saved_yaml_files()
    saved_names = [p.name for p in saved_files]

    selected_saved_name = st.selectbox(
        "保存済みYAMLを選抁E,
        options=["(選択なぁE"] + saved_names,
        index=0,
    )

    if selected_saved_name != "(選択なぁE":
        with st.expander("保存済みYAMLの管琁E):
            new_name = st.text_input("新しいファイル吁E, value=selected_saved_name)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("名前変更", use_container_width=True):
                    try:
                        renamed = _rename_saved_yaml(selected_saved_name, new_name)
                        st.success(f"名前変更しました: {renamed.name}")
                    except Exception as e:
                        st.error(f"名前変更エラー: {e}")
            with c2:
                if st.button("削除", use_container_width=True):
                    try:
                        _delete_saved_yaml(selected_saved_name)
                        st.success(f"削除しました: {selected_saved_name}")
                    except Exception as e:
                        st.error(f"削除エラー: {e}")

    uploaded = st.file_uploader("また�E新規YAMLをドラチE��&ドロチE�E", type=["yaml", "yml"])

    st.caption(f"YAML保存フォルダ: {APP_DATA_DIR}")

    uploaded_bytes: bytes | None = None
    active_source_id = ""

    if uploaded is not None:
        candidate_name = Path(uploaded.name).name
        candidate_bytes = uploaded.getvalue()
        destination = APP_DATA_DIR / candidate_name

        if destination.exists():
            st.warning(f"同名ファイルがありまぁE {destination.name}")
            duplicate_action = st.radio(
                "同名アチE�Eロード時の動佁E,
                options=["キャンセル", "上書ぁE],
                horizontal=True,
            )
            if duplicate_action == "上書ぁE:
                if st.button("上書きを実衁E):
                    try:
                        saved_path = _save_uploaded_yaml(candidate_name, candidate_bytes, overwrite=True)
                        st.success(f"上書き保存しました: {saved_path}")
                        uploaded_bytes = candidate_bytes
                        active_source_id = f"upload:{candidate_name}"
                    except Exception as e:
                        st.error(f"上書きエラー: {e}")
                else:
                    st.info("「上書きを実行」を押すと保存します、E)
            else:
                st.info("アチE�Eロード�E保存しません�E�キャンセル�E�、E)
        else:
            try:
                saved_path = _save_uploaded_yaml(candidate_name, candidate_bytes)
                st.success(f"アチE�Eロードを保存しました: {saved_path}")
                uploaded_bytes = candidate_bytes
                active_source_id = f"upload:{candidate_name}"
            except Exception as e:
                st.error(f"保存エラー: {e}")
    elif selected_saved_name != "(選択なぁE":
        saved_path = APP_DATA_DIR / selected_saved_name
        uploaded_bytes = saved_path.read_bytes()
        active_source_id = f"saved:{selected_saved_name}"
        st.info(f"保存済みファイルを使用: {saved_path}")

    if uploaded_bytes is None:
        st.info("保存済みYAMLを選ぶか、新規YAMLをアチE�Eロードしてください、E)
        return

    try:
        payload = _parse_uploaded_yaml_payload(uploaded_bytes)
        chord_bars, bar_meta = _extract_bars_with_meta(payload)
        if not chord_bars:
            raise ValueError("progression/sections が空です、E)
    except Exception as e:
        st.error(f"YAML解析エラー: {e}")
        return

    yaml_num, yaml_den = _parse_time_signature(payload.get("time_signature") if isinstance(payload, dict) else None)
    default_tempo = int(payload.get("tempo")) if isinstance(payload.get("tempo"), int) else 120
    default_numerator = int(yaml_num) if yaml_num is not None else 4
    default_denominator = int(yaml_den) if yaml_den is not None else 4

    if "hc_tempo_input" not in st.session_state:
        st.session_state["hc_tempo_input"] = 120
    if "hc_meter_numerator" not in st.session_state:
        st.session_state["hc_meter_numerator"] = 4
    if "hc_meter_denominator" not in st.session_state:
        st.session_state["hc_meter_denominator"] = 4

    if st.session_state.get("hc_defaults_source") != active_source_id:
        st.session_state["hc_tempo_input"] = default_tempo
        st.session_state["hc_meter_numerator"] = default_numerator
        st.session_state["hc_meter_denominator"] = default_denominator
        st.session_state["hc_defaults_source"] = active_source_id

    tempo = st.number_input("Tempo (BPM)", min_value=30, max_value=600, step=1, key="hc_tempo_input")
    send_tempo = st.number_input("送信チE��チE(BPM)", min_value=30, max_value=600, value=300, step=1)
    meter_col1, meter_col2 = st.columns(2)
    with meter_col1:
        meter_numerator = st.number_input("拍孁E刁E��E, min_value=3, max_value=7, step=1, key="hc_meter_numerator")
    with meter_col2:
        meter_denominator = st.selectbox("拍孁E刁E��E, options=[4, 8], key="hc_meter_denominator")
    output_path = st.text_input(
        "MIDI保存�E",
        value=str(Path.home() / "Downloads" / "changes_output.mid"),
    )

    hold_same_pitch = st.checkbox(
        "同音連続を保持して再トリガーしなぁE(Hold Trigger)",
        value=True,
    )
    st.caption("ON: 同一トラチE��で同音は保持。OFF: 毎Stepで再トリガー、E)

    channel_options = ["送らなぁE] + [str(i) for i in range(1, 17)]

    st.markdown("**Chord 6トラチE��設宁E*")
    channel_cols_top = st.columns(3)
    ch1_opt = channel_cols_top[0].selectbox("Track 1", options=channel_options, index=1)
    ch2_opt = channel_cols_top[1].selectbox("Track 2", options=channel_options, index=2)
    ch3_opt = channel_cols_top[2].selectbox("Track 3", options=channel_options, index=3)
    channel_cols_bottom = st.columns(3)
    ch4_opt = channel_cols_bottom[0].selectbox("Track 4", options=channel_options, index=4)
    ch5_opt = channel_cols_bottom[1].selectbox("Track 5", options=channel_options, index=5)
    ch6_opt = channel_cols_bottom[2].selectbox("Track 6", options=channel_options, index=6)
    chord_octave_shift = st.number_input(
        "Chord 6トラチE�� Octave Shift",
        min_value=-4,
        max_value=4,
        value=1,
        step=1,
    )

    st.markdown("**BassトラチE��設宁E*")
    bass_channel_opt = st.selectbox("Bass Track Channel", options=channel_options, index=9)
    bass_hold_same_pitch = st.checkbox(
        "Bass: 同音連続を保持して再トリガーしなぁE,
        value=False,
    )
    bass_switch_enabled = st.checkbox(
        "Bass: 同音連続で Root/Fifth を�Eり替える",
        value=False,
    )
    bass_switch_every = st.number_input(
        "Bass: 同音連続�E替回数 x",
        min_value=1,
        max_value=64,
        value=4,
        step=1,
        disabled=not bass_switch_enabled,
    )
    bass_octave_shift = st.number_input(
        "Bass Octave Shift",
        min_value=-4,
        max_value=4,
        value=2,
        step=1,
    )

    channel_map = _resolve_channel_map(
        [
            _channel_option_to_value(ch1_opt),
            _channel_option_to_value(ch2_opt),
            _channel_option_to_value(ch3_opt),
            _channel_option_to_value(ch4_opt),
            _channel_option_to_value(ch5_opt),
            _channel_option_to_value(ch6_opt),
            _channel_option_to_value(bass_channel_opt),
        ]
    )
    st.caption(f"現在のChannel割り当て: {channel_map}")

    st.caption(f"YAML既定値: tempo={default_tempo}, 拍孁E{default_numerator}/{default_denominator}")

    effective_tempo = int(tempo)
    effective_numerator = int(meter_numerator)
    effective_denominator = int(meter_denominator)

    try:
        voicings = _build_voicings_from_bars(chord_bars)
    except Exception as e:
        st.error(f"ボイシング生�Eエラー: {e}")
        return

    steps_per_bar, total_length, events = _build_event_schedule(
        chord_bars=chord_bars,
        meter_numerator=effective_numerator,
        meter_denominator=effective_denominator,
        bar_meta=bar_meta,
    )

    recommended_tempo = _compute_digitone_tempo_for_same_duration(
        input_tempo=effective_tempo,
        meter_numerator=effective_numerator,
        meter_denominator=effective_denominator,
        steps_per_bar=int(steps_per_bar),
    )

    digitone_tempo, digitone_length, scheduled_events = _apply_digitone_tempo_floor(
        tempo=int(recommended_tempo),
        length=int(total_length),
        events=events,
    )

    bass_notes = _build_bassline_notes(
        scheduled_events,
        switch_every=int(bass_switch_every),
        switch_enabled=bool(bass_switch_enabled),
    )
    combined_voicings = _append_bass_track(voicings, bass_notes)
    output_voicings = _transpose_output_voicings(
        combined_voicings,
        chord_octave_shift=int(chord_octave_shift),
        bass_octave_shift=int(bass_octave_shift),
    )
    per_voice_hold = [bool(hold_same_pitch)] * 6 + [bool(bass_hold_same_pitch)]

    input_elapsed_seconds = _seconds_for_input_tempo(
        bars_count=len(chord_bars),
        meter_numerator=effective_numerator,
        meter_denominator=effective_denominator,
        input_tempo=effective_tempo,
    )
    send_elapsed_seconds = _seconds_for_send_tempo(
        length_steps=int(digitone_length),
        send_tempo=int(send_tempo),
    )

    formatted_lines = _format_chord_voicing_lines(scheduled_events, voicings)
    st.subheader("解析結果�E�コーチE+ 6声ボイシング�E�E)
    st.code("\n".join(formatted_lines), language="text")

    st.subheader("イベント割り当て")
    if hold_same_pitch:
        event_lines = _format_trigger_event_lines(scheduled_events, output_voicings)
    else:
        event_lines = _format_basic_event_lines(scheduled_events, output_voicings)
    st.code("\n".join(event_lines), language="text")

    st.subheader("録音後にDigitoneで設定する値")
    st.code(
        "\n".join(
            [
                "Digitone",
                f"tempo:{digitone_tempo} Length:{digitone_length} (1-{digitone_length}) Speed:1/8",
            ]
        ),
        language="text",
    )

    st.subheader("時間")
    st.code(
        "\n".join(
            [
                f"入力テンポで全小節の経過にかかる時閁E {input_elapsed_seconds:.3f} 私E,
                f"送信チE��ポで全小節の経過にかかる時閁E {send_elapsed_seconds:.3f} 私E,
            ]
        ),
        language="text",
    )

    ports: List[str] = ["DEBUG"]
    if mido is not None:
        try:
            ports.extend(mido.get_output_names())
        except Exception:
            pass

    selected_port = st.selectbox("MIDI Output Port", options=ports)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("生�E (MIDIファイル)", use_container_width=True):
            try:
                write_midi_with_events(
                    output_voicings,
                    scheduled_events,
                    output_path,
                    tempo=effective_tempo,
                    hold_same_pitch=hold_same_pitch,
                    channel_map=channel_map,
                    per_voice_hold=per_voice_hold,
                )
                st.success(f"保存しました: {output_path}")
            except Exception as e:
                st.error(f"MIDI保存エラー: {e}")

    with col2:
        if selected_port != "DEBUG" and mido is None:
            st.button("送信", use_container_width=True, disabled=True)
            st.caption("mido が未導�Eのため実機送信は無効です、EEBUG は利用できます、E)
        else:
            if st.button("送信", use_container_width=True):
                try:
                    send_logs = _send_with_optional_debug(
                        voicings=output_voicings,
                        events=scheduled_events,
                        send_tempo=int(send_tempo),
                        selected_port=selected_port,
                        hold_same_pitch=hold_same_pitch,
                        channel_map=channel_map,
                        per_voice_hold=per_voice_hold,
                    )
                    st.success("送信完亁E)
                    st.subheader("送信ログ")
                    st.code("\n".join(send_logs), language="text")
                except Exception as e:
                    st.error(f"送信エラー: {e}")

    if "hc_jump_midi_log" not in st.session_state:
        st.session_state["hc_jump_midi_log"] = []
    if "hc_jump_note_channel" not in st.session_state:
        st.session_state["hc_jump_note_channel"] = 10
    if "hc_jump_cc_channel" not in st.session_state:
        st.session_state["hc_jump_cc_channel"] = 10

    with st.expander("Digitone II STEP RECORDING / JUMP MODE Debug", expanded=False):
        st.warning(
            "Digitone II側は JUMP MODE / Step 1開姁E/ SPEED=1/8X / RECEIVE NOTES&CC ON を維持してください、E
        )
        st.caption(f"現在の送信ポ�EチE {selected_port}")

        st.subheader("セクション2: Raw LEN / Note Test")
        debug_col1, debug_col2 = st.columns(2)
        with debug_col1:
            jump_note_channel = st.number_input(
                "Note送信チャンネル (AUTO CHANNEL)",
                min_value=1,
                max_value=16,
                step=1,
                key="hc_jump_note_channel",
            )
            jump_velocity = st.number_input(
                "Velocity",
                min_value=1,
                max_value=127,
                value=100,
                step=1,
            )
            jump_note_off_ms = st.number_input(
                "Note On ↁENote Off 征E��時間 (ms)",
                min_value=0,
                max_value=5000,
                value=50,
                step=10,
            )
        with debug_col2:
            jump_cc_channel = st.number_input(
                "LEN CC送信チャンネル",
                min_value=1,
                max_value=16,
                step=1,
                key="hc_jump_cc_channel",
            )
            jump_cc_to_note_ms = st.number_input(
                "CC送信征EↁENote On 征E��時間 (ms)",
                min_value=0,
                max_value=5000,
                value=50,
                step=10,
            )
            jump_len_x = st.number_input(
                "LEN x raw value",
                min_value=0,
                max_value=127,
                value=32,
                step=1,
            )
            st.caption("LEN x チE��ォルト値 32 (Digitone側で要確誁E")

        jump_between_ms = st.number_input(
            "Sequenceイベント間delay (ms)",
            min_value=0,
            max_value=5000,
            value=150,
            step=10,
        )

        btn_col1, btn_col2 = st.columns(2)
        run_events: Sequence[tuple[int, int]] | None = None

        with btn_col1:
            if st.button("C5 / LEN 8 / 1 step", use_container_width=True):
                run_events = [(8, 60)]
            if st.button("E5 / LEN x / x steps", use_container_width=True):
                run_events = [(int(jump_len_x), 64)]
        with btn_col2:
            if st.button("D5 / LEN 16 / 2 steps", use_container_width=True):
                run_events = [(16, 62)]
            if st.button("Run C5 ↁED5 ↁEE5 Sequence", use_container_width=True):
                run_events = [(8, 60), (16, 62), (int(jump_len_x), 64)]

        if run_events is not None:
            try:
                logs = _send_len_note_test_events(
                    selected_port=selected_port,
                    note_channel=int(jump_note_channel),
                    cc_channel=int(jump_cc_channel),
                    velocity=int(jump_velocity),
                    note_off_delay_ms=int(jump_note_off_ms),
                    cc_to_note_delay_ms=int(jump_cc_to_note_ms),
                    sequence_events=run_events,
                    inter_event_delay_ms=int(jump_between_ms),
                )
                history = st.session_state.get("hc_jump_midi_log", [])
                history.extend(logs)
                st.session_state["hc_jump_midi_log"] = history[-500:]
                st.success("JUMP MODEチE��チE��送信完亁E)
            except Exception as e:
                st.error(f"チE��チE��送信エラー: {e}")

        st.subheader("セクション4: MIDI Log")
        clear_col, _ = st.columns([1, 3])
        with clear_col:
            if st.button("ログをクリア", use_container_width=True):
                st.session_state["hc_jump_midi_log"] = []

        jump_log_lines = st.session_state.get("hc_jump_midi_log", [])
        if jump_log_lines:
            st.code("\n".join(jump_log_lines), language="text")
        else:
            st.code("(empty)", language="text")

    st.subheader("セクション別 生�E / 送信")
    sections = payload.get("sections")
    if isinstance(sections, list):
        for sec_idx, section in enumerate(sections):
            if not isinstance(section, dict):
                continue

            section_name = str(section.get("name") or f"section_{sec_idx + 1}")
            section_progression = section.get("progression")
            if not isinstance(section_progression, list):
                continue

            section_bars: List[List[str]] = []
            for bar in section_progression:
                if isinstance(bar, list):
                    cleaned = [str(x).strip() for x in bar if str(x).strip()]
                    if cleaned:
                        section_bars.append(cleaned)

            if not section_bars:
                continue

            try:
                section_voicings = _build_voicings_from_bars(section_bars)
            except Exception as e:
                st.error(f"{section_name} のボイシング生�Eエラー: {e}")
                continue

            section_meta = [
                {"section": section_name, "bar_in_section": i + 1}
                for i in range(len(section_bars))
            ]
            section_steps_per_bar, section_total_length, section_events = _build_event_schedule(
                chord_bars=section_bars,
                meter_numerator=effective_numerator,
                meter_denominator=effective_denominator,
                bar_meta=section_meta,
            )
            section_recommended_tempo = _compute_digitone_tempo_for_same_duration(
                input_tempo=effective_tempo,
                meter_numerator=effective_numerator,
                meter_denominator=effective_denominator,
                steps_per_bar=int(section_steps_per_bar),
            )
            section_digitone_tempo, section_digitone_length, section_scheduled_events = _apply_digitone_tempo_floor(
                tempo=int(section_recommended_tempo),
                length=int(section_total_length),
                events=section_events,
            )

            section_bass_notes = _build_bassline_notes(
                section_scheduled_events,
                switch_every=int(bass_switch_every),
                switch_enabled=bool(bass_switch_enabled),
            )
            section_combined_voicings = _append_bass_track(section_voicings, section_bass_notes)
            section_output_voicings = _transpose_output_voicings(
                section_combined_voicings,
                chord_octave_shift=int(chord_octave_shift),
                bass_octave_shift=int(bass_octave_shift),
            )
            section_per_voice_hold = [bool(hold_same_pitch)] * 6 + [bool(bass_hold_same_pitch)]

            st.markdown(f"**{section_name}**")
            st.caption(
                f"tempo:{section_digitone_tempo} Length:{section_digitone_length} Speed:1/8"
            )
            if hold_same_pitch:
                section_event_lines = _format_trigger_event_lines(section_scheduled_events, section_output_voicings)
            else:
                section_event_lines = _format_basic_event_lines(section_scheduled_events, section_output_voicings)
            st.code("\n".join(section_event_lines), language="text")

            section_col1, section_col2 = st.columns(2)
            with section_col1:
                if st.button(f"{section_name} を生戁E, key=f"generate_section_{sec_idx}", use_container_width=True):
                    try:
                        section_output = _section_output_path(output_path, section_name)
                        write_midi_with_events(
                            section_output_voicings,
                            section_scheduled_events,
                            section_output,
                            tempo=effective_tempo,
                            hold_same_pitch=hold_same_pitch,
                            channel_map=channel_map,
                            per_voice_hold=section_per_voice_hold,
                        )
                        st.success(f"{section_name} を保存しました: {section_output}")
                    except Exception as e:
                        st.error(f"{section_name} のMIDI保存エラー: {e}")

            with section_col2:
                if selected_port != "DEBUG" and mido is None:
                    st.button(
                        f"{section_name} を送信",
                        key=f"send_section_{sec_idx}",
                        use_container_width=True,
                        disabled=True,
                    )
                else:
                    if st.button(f"{section_name} を送信", key=f"send_section_{sec_idx}", use_container_width=True):
                        try:
                            section_send_logs = _send_with_optional_debug(
                                voicings=section_output_voicings,
                                events=section_scheduled_events,
                                send_tempo=int(send_tempo),
                                selected_port=selected_port,
                                hold_same_pitch=hold_same_pitch,
                                channel_map=channel_map,
                                per_voice_hold=section_per_voice_hold,
                            )
                            st.success(f"{section_name} の送信完亁E)
                            st.code("\n".join(section_send_logs), language="text")
                        except Exception as e:
                            st.error(f"{section_name} の送信エラー: {e}")


if __name__ == "__main__":
    main()
