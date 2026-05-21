"""Minimal Streamlit UI for Harmony Cloud.

Features:
- Drag-and-drop YAML progression file
- Tempo input
- Generate MIDI file
- Send voicings to a selected MIDI output port
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import List

import streamlit as st
import yaml

from harmony_cloud.chord_parser import parse_progression
from harmony_cloud.midi_writer import write_midi
from harmony_cloud.note import midi_to_note_name
from harmony_cloud.voicing import progression_to_voicings
from harmony_cloud.voice_leading import generate_voice_leading

try:
    import mido
except Exception:  # pragma: no cover
    mido = None


APP_DATA_DIR = Path.home() / "HarmonyCloud" / "progressions"


def _ensure_app_data_dir() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


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
        raise ValueError("新しいファイル名が空です。")

    if not (candidate.endswith(".yaml") or candidate.endswith(".yml")):
        candidate = f"{candidate}.yaml"

    destination = APP_DATA_DIR / candidate
    if destination.exists() and destination != source:
        raise FileExistsError(f"同名ファイルが既に存在します: {destination.name}")

    source.rename(destination)
    return destination


def _parse_uploaded_yaml(uploaded_bytes: bytes) -> List[str]:
    """Parse uploaded YAML into flat chord list for display/validation."""
    data = yaml.safe_load(uploaded_bytes)

    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]

    if isinstance(data, dict):
        progression = data.get("progression")
        if isinstance(progression, list):
            flat: List[str] = []
            for item in progression:
                if isinstance(item, list):
                    flat.extend(str(x).strip() for x in item if str(x).strip())
                else:
                    s = str(item).strip()
                    if s:
                        flat.append(s)
            return flat

    raise ValueError("YAML must contain a progression list (e.g. progression: [[Dm7, G7, Cmaj7]]).")


def _build_voicings_from_upload(uploaded_bytes: bytes) -> List[List[int]]:
    """Reuse existing pipeline by writing upload to a temp YAML file."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(uploaded_bytes)

    try:
        progression = parse_progression(tmp_path.as_posix())
        raw_voicings = progression_to_voicings(progression)
        return generate_voice_leading(raw_voicings)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _format_chord_voicing_lines(chords: List[str], voicings: List[List[int]]) -> List[str]:
    """Format each chord + 6-voice voicing on one line for readable logs."""
    lines: List[str] = []
    count = min(len(chords), len(voicings))

    for idx in range(count):
        chord = chords[idx]
        notes = voicings[idx]
        formatted_notes = ",".join(
            f"{voice_idx}:{midi_to_note_name(int(note))}"
            for voice_idx, note in enumerate(notes)
        )
        lines.append(f'[{idx}: "{chord}" [{formatted_notes}]]')

    return lines


def _digitone_tempo_after_recording(input_tempo: int, denominator: int) -> int:
    """Calculate suggested Digitone tempo after recording for Speed 1/8 workflow."""
    if denominator == 4:
        return max(1, int(round(input_tempo / 2)))
    return max(1, int(round(input_tempo)))


def _digitone_recording_plan(input_tempo: int, denominator: int, base_length: int) -> tuple[int, int, int]:
    """Return (tempo, length, duration_steps) satisfying Digitone tempo floor.

    If calculated tempo goes below 30, double tempo and length repeatedly.
    Duration in step units is doubled in the same ratio.
    """
    tempo = _digitone_tempo_after_recording(input_tempo, denominator)
    length = max(1, int(base_length))
    duration_steps = 1

    while tempo < 30:
        tempo *= 2
        length *= 2
        duration_steps *= 2

    return int(tempo), int(length), int(duration_steps)


def _send_with_optional_debug(
    voicings: List[List[int]],
    chords: List[str],
    tempo: int,
    denominator: int,
    selected_port: str,
    duration_steps: int = 1,
) -> List[str]:
    """Send MIDI or simulate send in DEBUG mode; return send logs."""
    logs: List[str] = []
    delay_seconds = (60.0 / float(tempo)) * (4.0 / float(denominator)) * duration_steps

    count = min(len(chords), len(voicings))
    if selected_port == "DEBUG":
        for idx in range(count):
            beat_step = idx + 1
            logs.append(f"拍:{beat_step} コード:{chords[idx]} 音価:{duration_steps}")
        return logs

    if mido is None:
        raise RuntimeError("mido が未導入です。DEBUG を使うか realtime 依存を導入してください。")

    with mido.open_output(selected_port) as outport:
        for idx in range(count):
            beat_step = idx + 1
            chord_notes = voicings[idx]
            for note in chord_notes:
                outport.send(mido.Message("note_on", note=int(note), velocity=100))

            time.sleep(delay_seconds)

            for note in chord_notes:
                outport.send(mido.Message("note_off", note=int(note), velocity=0))

            logs.append(f"拍:{beat_step} コード:{chords[idx]} 音価:{duration_steps}")

    return logs


def main() -> None:
    st.set_page_config(page_title="Harmony Cloud", layout="centered")
    st.title("Harmony Cloud – Minimal UI")
    st.caption("YAMLをドラッグ&ドロップして、MIDI生成またはDigitone IIへ送信")

    saved_files = _list_saved_yaml_files()
    saved_names = [p.name for p in saved_files]

    selected_saved_name = st.selectbox(
        "保存済みYAMLを選択",
        options=["(選択なし)"] + saved_names,
        index=0,
    )

    if selected_saved_name != "(選択なし)":
        with st.expander("保存済みYAMLの管理"):
            new_name = st.text_input("新しいファイル名", value=selected_saved_name)
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

    uploaded = st.file_uploader("または新規YAMLをドラッグ&ドロップ", type=["yaml", "yml"])

    tempo = st.number_input("Tempo (BPM)", min_value=30, max_value=600, value=120, step=1)
    send_tempo = st.number_input("送信テンポ (BPM)", min_value=30, max_value=600, value=300, step=1)
    meter_col1, meter_col2 = st.columns(2)
    with meter_col1:
        meter_numerator = st.number_input("拍子 分子", min_value=3, max_value=7, value=4, step=1)
    with meter_col2:
        meter_denominator = st.selectbox("拍子 分母", options=[4, 8], index=0)
    output_path = st.text_input(
        "MIDI保存先",
        value=str(Path.home() / "Downloads" / "harmony_cloud_output.mid"),
    )

    st.caption(f"YAML保存フォルダ: {APP_DATA_DIR}")

    uploaded_bytes: bytes | None = None

    if uploaded is not None:
        candidate_name = Path(uploaded.name).name
        candidate_bytes = uploaded.getvalue()
        destination = APP_DATA_DIR / candidate_name

        if destination.exists():
            st.warning(f"同名ファイルがあります: {destination.name}")
            duplicate_action = st.radio(
                "同名アップロード時の動作",
                options=["キャンセル", "上書き"],
                horizontal=True,
            )
            if duplicate_action == "上書き":
                if st.button("上書きを実行"):
                    try:
                        saved_path = _save_uploaded_yaml(candidate_name, candidate_bytes, overwrite=True)
                        st.success(f"上書き保存しました: {saved_path}")
                        uploaded_bytes = candidate_bytes
                    except Exception as e:
                        st.error(f"上書きエラー: {e}")
                else:
                    st.info("「上書きを実行」を押すと保存します。")
            else:
                st.info("アップロードは保存しません（キャンセル）。")
        else:
            try:
                saved_path = _save_uploaded_yaml(candidate_name, candidate_bytes)
                st.success(f"アップロードを保存しました: {saved_path}")
                uploaded_bytes = candidate_bytes
            except Exception as e:
                st.error(f"保存エラー: {e}")
    elif selected_saved_name != "(選択なし)":
        saved_path = APP_DATA_DIR / selected_saved_name
        uploaded_bytes = saved_path.read_bytes()
        st.info(f"保存済みファイルを使用: {saved_path}")

    if uploaded_bytes is None:
        st.info("保存済みYAMLを選ぶか、新規YAMLをアップロードしてください。")
        return

    try:
        chords = _parse_uploaded_yaml(uploaded_bytes)
    except Exception as e:
        st.error(f"YAML解析エラー: {e}")
        return

    try:
        voicings = _build_voicings_from_upload(uploaded_bytes)
    except Exception as e:
        st.error(f"ボイシング生成エラー: {e}")
        return

    formatted_lines = _format_chord_voicing_lines(chords, voicings)
    st.subheader("解析結果（コード + 6声ボイシング）")
    st.code("\n".join(formatted_lines), language="text")

    digitone_tempo, digitone_length, duration_steps = _digitone_recording_plan(
        int(tempo),
        int(meter_denominator),
        len(formatted_lines),
    )
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

    col1, col2 = st.columns(2)

    with col1:
        if st.button("生成 (MIDIファイル)", use_container_width=True):
            try:
                write_midi(voicings, output_path, tempo=int(tempo))
                st.success(f"保存しました: {output_path}")
            except Exception as e:
                st.error(f"MIDI保存エラー: {e}")

    with col2:
        ports: List[str] = ["DEBUG"]
        if mido is not None:
            try:
                ports.extend(mido.get_output_names())
            except Exception:
                pass

        selected_port = st.selectbox("MIDI Output Port", options=ports)

        if selected_port != "DEBUG" and mido is None:
            st.button("送信", use_container_width=True, disabled=True)
            st.caption("mido が未導入のため実機送信は無効です。DEBUG は利用できます。")
        else:
            if st.button("送信", use_container_width=True):
                try:
                    send_logs = _send_with_optional_debug(
                        voicings=voicings,
                        chords=chords,
                        tempo=int(send_tempo),
                        denominator=int(meter_denominator),
                        selected_port=selected_port,
                        duration_steps=duration_steps,
                    )
                    st.success("送信完了")
                    st.subheader("送信ログ")
                    st.code("\n".join(send_logs), language="text")
                except Exception as e:
                    st.error(f"送信エラー: {e}")


if __name__ == "__main__":
    main()
