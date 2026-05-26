"""Streamlit UI for generic MIDI workflow in Changes."""

from __future__ import annotations

from datetime import datetime
import json
from math import lcm
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
import re
import time

import streamlit as st
import yaml

from changes.midi_writer import write_midi_with_events
from changes.models.digitone_compile_plan import digitone_compile_plan_to_dict
from changes.models.rendered_timeline import rendered_timeline_to_dict
from changes.models.song_model import song_model_to_dict
from changes.note import midi_to_note_name, pitch_class_to_semitone
from changes.pipeline_digitone import compile_digitone_pipeline, save_digitone_pipeline_artifacts
from changes.voicing import progression_to_voicings
from changes.voice_leading import generate_voice_leading

try:
    import mido
except Exception:  # pragma: no cover
    mido = None


APP_DATA_DIR = Path.home() / "EUBChanges" / "progressions"
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
        raise ValueError("new file name is empty")

    if not (candidate.endswith(".yaml") or candidate.endswith(".yml")):
        candidate = f"{candidate}.yaml"

    destination = APP_DATA_DIR / candidate
    if destination.exists() and destination != source:
        raise FileExistsError(f"File already exists: {destination.name}")

    source.rename(destination)
    return destination


def _normalize_section_names(raw_names: List[str]) -> List[str]:
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
    data = yaml.safe_load(uploaded_bytes)

    if data is None:
        raise ValueError("YAML is empty")

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

    raise ValueError("YAML must contain progression or sections/progression")


def _parse_uploaded_yaml_bars(uploaded_bytes: bytes) -> List[List[str]]:
    payload = _parse_uploaded_yaml_payload(uploaded_bytes)
    bars, _ = _extract_bars_with_meta(payload)
    if not bars:
        raise ValueError("progression is empty")
    return bars


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


def _build_voicings_from_bars(chord_bars: List[List[str]]) -> List[List[int]]:
    raw_voicings = progression_to_voicings(chord_bars)
    return generate_voice_leading(raw_voicings)


def _build_note_triggers(events: List[Dict[str, int | str]], voicings: List[List[int]]) -> List[List[Dict[str, int]]]:
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

            triggers[idx].append({"voice": voice_idx, "note": note, "duration_steps": hold_steps})
            idx += 1

    return triggers


def _format_trigger_event_lines(events: List[Dict[str, int | str]], voicings: List[List[int]]) -> List[str]:
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
                parts.append(f"[{int(item['voice'])}:{note_name} duration:{int(item['duration_steps'])}]")
            note_text = " ".join(parts)
        else:
            note_text = "(hold)"

        lines.append(f"Step:{int(event['step'])} chord:\"{str(event['chord'])}\" {note_text}")

    return lines


def _format_basic_event_lines(events: List[Dict[str, int | str]], voicings: List[List[int]]) -> List[str]:
    count = min(len(events), len(voicings))
    lines: List[str] = []

    for idx in range(count):
        event = events[idx]
        notes = voicings[idx]
        duration = int(event["duration_steps"])
        parts = [f"[{voice_idx}:{midi_to_note_name(int(note))} duration:{duration}]" for voice_idx, note in enumerate(notes)]
        note_text = " ".join(parts) if parts else "(rest)"
        lines.append(f"Step:{int(event['step'])} chord:\"{str(event['chord'])}\" {note_text}")

    return lines


def _resolve_channel_map(raw_values: List[int | None]) -> List[int | None]:
    channels: List[int | None] = []
    for value in raw_values:
        if value is None:
            channels.append(None)
        else:
            channels.append(max(1, min(16, int(value))))
    return channels


def _channel_option_to_value(option: str) -> int | None:
    return None if option == "off" else int(option)


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


def _build_bassline_notes(events: Sequence[Dict[str, int | str]], switch_every: int, switch_enabled: bool) -> List[int]:
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


def _transpose_output_voicings(voicings: Sequence[Sequence[int]], chord_octave_shift: int, bass_octave_shift: int) -> List[List[int]]:
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


def _format_chord_voicing_lines(events: List[Dict[str, int | str]], voicings: List[List[int]]) -> List[str]:
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
        formatted_notes = ",".join(f"{voice_idx}:{midi_to_note_name(int(note))}" for voice_idx, note in enumerate(notes))

        bar_key = (section, bar_in_section)
        chord_in_bar = int(event.get("chord_in_bar") or 0)
        row = f"[{chord_in_bar}: \"{chord}\" [{formatted_notes}]]"

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


def _build_event_schedule(chord_bars: List[List[str]], meter_numerator: int, meter_denominator: int, bar_meta: List[Dict[str, object]] | None = None) -> Tuple[int, int, List[Dict[str, int | str]]]:
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


def _send_with_optional_debug(
    voicings: List[List[int]],
    events: List[Dict[str, int | str]],
    send_tempo: int,
    selected_port: str,
    hold_same_pitch: bool,
    channel_map: List[int | None],
    per_voice_hold: List[bool] | None = None,
) -> List[str]:
    logs: List[str] = []
    step_seconds = 60.0 / float(send_tempo)
    count = min(len(events), len(voicings))
    if count == 0:
        return logs

    max_voices = max(len(v) for v in voicings[:count])
    channels = _resolve_channel_map(channel_map)
    hold_per_voice = list(per_voice_hold) if per_voice_hold is not None else []
    if len(hold_per_voice) < max_voices:
        hold_per_voice.extend([hold_same_pitch] * (max_voices - len(hold_per_voice)))

    def _voice_note(chord: List[int] | None, voice_idx: int) -> int | None:
        if chord is None or voice_idx >= len(chord):
            return None
        return int(chord[voice_idx])

    previous_chord: List[int] | None = None

    if selected_port == "DEBUG":
        epoch = time.time()
        elapsed = 0.0
        logs.append("Transport:start")
        for idx in range(count):
            event = events[idx]
            chord_notes = voicings[idx]
            triggered: List[str] = []
            for voice_idx in range(max_voices):
                prev_note = _voice_note(previous_chord, voice_idx)
                cur_note = _voice_note(chord_notes, voice_idx)
                ch = channels[voice_idx] if voice_idx < len(channels) else 1
                if ch is None:
                    continue
                if hold_per_voice[voice_idx]:
                    if cur_note is not None and cur_note != prev_note:
                        triggered.append(f"v{voice_idx}:ch{ch}:{midi_to_note_name(cur_note)}")
                elif cur_note is not None:
                    triggered.append(f"v{voice_idx}:ch{ch}:{midi_to_note_name(cur_note)}")
            duration = step_seconds * int(event["duration_steps"])
            ts = datetime.fromtimestamp(epoch + elapsed).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            logs.append(f"Send:{ts} chord:{event['chord']} {' '.join(triggered) if triggered else '[hold]'} duration:{duration:.3f}s")
            elapsed += duration
            previous_chord = chord_notes
        logs.append("Transport:stop")
        return logs

    if mido is None:
        raise RuntimeError("mido is required for realtime send")

    with mido.open_output(selected_port) as outport:
        outport.send(mido.Message("start"))
        try:
            for idx in range(count):
                event = events[idx]
                chord_notes = voicings[idx]
                for voice_idx in range(max_voices):
                    prev_note = _voice_note(previous_chord, voice_idx)
                    cur_note = _voice_note(chord_notes, voice_idx)
                    ch_val = channels[voice_idx] if voice_idx < len(channels) else 1
                    if ch_val is None:
                        continue
                    ch = ch_val - 1
                    if hold_per_voice[voice_idx]:
                        if prev_note is not None and prev_note != cur_note:
                            outport.send(mido.Message("note_off", note=int(prev_note), velocity=0, channel=ch))
                        if cur_note is not None and prev_note != cur_note:
                            outport.send(mido.Message("note_on", note=int(cur_note), velocity=100, channel=ch))
                    elif cur_note is not None:
                        outport.send(mido.Message("note_on", note=int(cur_note), velocity=100, channel=ch))

                time.sleep(step_seconds * int(event["duration_steps"]))

                for voice_idx in range(max_voices):
                    if hold_per_voice[voice_idx]:
                        continue
                    cur_note = _voice_note(chord_notes, voice_idx)
                    ch_val = channels[voice_idx] if voice_idx < len(channels) else 1
                    if ch_val is None or cur_note is None:
                        continue
                    outport.send(mido.Message("note_off", note=int(cur_note), velocity=0, channel=ch_val - 1))

                previous_chord = chord_notes

            if previous_chord is not None:
                for voice_idx in range(max_voices):
                    if not hold_per_voice[voice_idx]:
                        continue
                    note = _voice_note(previous_chord, voice_idx)
                    ch_val = channels[voice_idx] if voice_idx < len(channels) else 1
                    if ch_val is None or note is None:
                        continue
                    outport.send(mido.Message("note_off", note=int(note), velocity=0, channel=ch_val - 1))
        finally:
            outport.send(mido.Message("stop"))

    return logs


def main() -> None:
    st.set_page_config(page_title="Changes", layout="centered")
    st.title("EUB Changes")
    st.caption("Generic MIDI export/realtime send UI")

    saved_files = _list_saved_yaml_files()
    saved_names = [p.name for p in saved_files]

    selected_saved_name = st.selectbox("Saved YAML", options=["(none)"] + saved_names, index=0)
    uploaded = st.file_uploader("Upload progression YAML", type=["yaml", "yml"])

    uploaded_bytes: bytes | None = None
    if uploaded is not None:
        uploaded_bytes = uploaded.getvalue()
    elif selected_saved_name != "(none)":
        uploaded_bytes = (APP_DATA_DIR / selected_saved_name).read_bytes()

    if uploaded_bytes is None:
        st.info("Upload or select a YAML file")
        return

    try:
        payload = _parse_uploaded_yaml_payload(uploaded_bytes)
        chord_bars, bar_meta = _extract_bars_with_meta(payload)
        if not chord_bars:
            raise ValueError("progression is empty")
    except Exception as exc:
        st.error(f"YAML parse error: {exc}")
        return

    st.subheader("Digitone Compile Pipeline")
    artifact_dir = st.text_input(
        "Digitone artifact output directory",
        value=str(Path.home() / "Downloads" / "changes_digitone_artifacts"),
    )
    write_syx = st.checkbox("Also generate SYX (requires digitone-syx-toolkit)", value=False)
    if st.button("Compile Digitone Artifacts", use_container_width=True):
        try:
            song_model, rendered_timeline, compile_plan, events_payload = compile_digitone_pipeline(payload)
            artifacts = save_digitone_pipeline_artifacts(
                output_dir=artifact_dir,
                song=song_model,
                timeline=rendered_timeline,
                plan=compile_plan,
                events_payload=events_payload,
                write_syx=write_syx,
            )
            st.success(f"Digitone artifacts written to: {artifact_dir}")
            st.write(
                f"speed={compile_plan.speed}, q_step={compile_plan.q_step}, "
                f"device_tempo={float(compile_plan.device_tempo):.3f}, total_steps={compile_plan.total_steps}"
            )
            for key, path in artifacts.items():
                st.write(f"{key}: {path}")

            with st.expander("Song Model JSON"):
                st.code(json.dumps(song_model_to_dict(song_model), indent=2, ensure_ascii=True), language="json")
            with st.expander("Rendered Timeline JSON"):
                st.code(json.dumps(rendered_timeline_to_dict(rendered_timeline), indent=2, ensure_ascii=True), language="json")
            with st.expander("Digitone Compile Plan JSON"):
                st.code(json.dumps(digitone_compile_plan_to_dict(compile_plan), indent=2, ensure_ascii=True), language="json")
            with st.expander("Digitone Events YAML Payload"):
                st.code(yaml.safe_dump(events_payload, sort_keys=False, allow_unicode=False), language="yaml")
        except Exception as exc:
            st.error(f"Digitone compile error: {exc}")

    default_tempo = int(payload.get("tempo") or 120) if isinstance(payload, dict) else 120
    tempo = st.number_input("Tempo (BPM)", min_value=30, max_value=300, value=default_tempo, step=1)
    send_tempo = st.number_input("Realtime Send Tempo (BPM)", min_value=30, max_value=300, value=120, step=1)
    output_path = st.text_input("MIDI output path", value=str(Path.home() / "Downloads" / "changes_output.mid"))

    hold_same_pitch = st.checkbox("Hold repeated same pitch", value=True)

    channel_options = ["off"] + [str(i) for i in range(1, 17)]
    channel_cols = st.columns(4)
    chord_channels = [
        channel_cols[0].selectbox("Track 1", channel_options, index=1),
        channel_cols[1].selectbox("Track 2", channel_options, index=2),
        channel_cols[2].selectbox("Track 3", channel_options, index=3),
        channel_cols[3].selectbox("Track 4", channel_options, index=4),
    ]
    channel_cols2 = st.columns(3)
    chord_channels.extend([
        channel_cols2[0].selectbox("Track 5", channel_options, index=5),
        channel_cols2[1].selectbox("Track 6", channel_options, index=6),
    ])
    bass_channel = channel_cols2[2].selectbox("Bass", channel_options, index=9)

    channel_map = _resolve_channel_map([_channel_option_to_value(x) for x in chord_channels] + [_channel_option_to_value(bass_channel)])

    try:
        voicings = _build_voicings_from_bars(chord_bars)
    except Exception as exc:
        st.error(f"Voicing error: {exc}")
        return

    _, _, events = _build_event_schedule(chord_bars=chord_bars, meter_numerator=4, meter_denominator=4, bar_meta=bar_meta)
    bass_notes = _build_bassline_notes(events, switch_every=4, switch_enabled=False)
    output_voicings = _append_bass_track(voicings, bass_notes)
    per_voice_hold = [bool(hold_same_pitch)] * 6 + [False]

    st.subheader("Voicings")
    st.code("\n".join(_format_chord_voicing_lines(events, voicings)), language="text")
    st.subheader("Events")
    lines = _format_trigger_event_lines(events, output_voicings) if hold_same_pitch else _format_basic_event_lines(events, output_voicings)
    st.code("\n".join(lines), language="text")

    ports = ["DEBUG"]
    if mido is not None:
        try:
            ports.extend(mido.get_output_names())
        except Exception:
            pass
    selected_port = st.selectbox("MIDI Output Port", options=ports)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate MIDI", use_container_width=True):
            try:
                write_midi_with_events(output_voicings, events, output_path, tempo=int(tempo), hold_same_pitch=hold_same_pitch, channel_map=channel_map, per_voice_hold=per_voice_hold)
                st.success(f"Saved: {output_path}")
            except Exception as exc:
                st.error(f"MIDI save error: {exc}")
    with c2:
        if st.button("Send Realtime", use_container_width=True):
            try:
                logs = _send_with_optional_debug(
                    voicings=output_voicings,
                    events=events,
                    send_tempo=int(send_tempo),
                    selected_port=selected_port,
                    hold_same_pitch=hold_same_pitch,
                    channel_map=channel_map,
                    per_voice_hold=per_voice_hold,
                )
                st.success("Send complete")
                st.code("\n".join(logs), language="text")
            except Exception as exc:
                st.error(f"Send error: {exc}")


if __name__ == "__main__":
    main()
