"""Streamlit Editor UI for EUB Changes chord progression input."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import streamlit as st
import yaml

from changes.editor import EditorState, editor_to_song_model
from changes.models.song_model import song_model_to_dict

# ── Config ───────────────────────────────────────────────────────────────────

_LOGO_PATH = Path(__file__).parent.parent.parent / "docs" / "assets" / "1x" / "eub_changes_logo_square.png"
_APP_VERSION = "0.1.0"

# ── Music constants ──────────────────────────────────────────────────────────

ROOTS = list("CDEFGAB")

_SHARP_SCALE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT_SCALE  = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

_ROOT_PC: dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "F": 5, "E#": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
}

_QUALITY_ROWS: list[list[tuple[str, str]]] = [
    [
        ("maj", ""), ("m", "m"), ("dim", "dim"), ("aug", "aug"),
        ("sus2", "sus2"), ("sus4", "sus4"),
    ],
    [
        ("maj7", "maj7"), ("m7", "m7"), ("7", "7"), ("m7b5", "m7b5"),
        ("dim7", "dim7"), ("m6", "m6"), ("6", "6"), ("alt", "alt"),
    ],
    [
        ("maj9", "maj9"), ("m9", "m9"), ("9", "9"), ("13", "13"),
        ("7b9", "7b9"), ("7#9", "7#9"), ("7#11", "7#11"),
        ("7b13", "7b13"), ("add9", "add9"),
    ],
]

_TEXT_INSTRUCTIONS = """\
**有効なトークン**

| トークン | 例 |
|---|---|
| コードシンボル | `Cmaj7` `Bbm7` `F#7` `Eb7b9` `G/B` |
| 直前コード繰り返し | `%` |
| 小節線 | `|` |
| セクション区切り | `||` |

**入力ルール**

- **Enter** でトークンを確定（スペース不要）
- スペース区切りで複数トークンを一度に確定することも可能
- 不正なトークンは破棄され、直前の確定済み状態に戻る
- **半角のみ** — ♭/♯ は使わず `b` / `#` を使う
  - 例: `Bb7` `F#maj7` `Eb7b9`
- **大文字・小文字どちらでも入力可** — ルートは自動的に大文字へ変換される
  - 例: `cmaj7` → `Cmaj7`、`bbm7` → `Bbm7`
- コードシンボルの書式: `ルート + [b/#] + クオリティ`
  - ルート: A–G
  - クオリティ: maj7 m7 7 m7b5 dim7 6 m6 alt
    maj9 m9 9 13 7b9 7#9 7#11 7b13 add9 dim aug sus2 sus4 …
"""

# ── CSS ──────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* App background */
.stApp {
    background-color: #FAF7FA;
}

/* Sidebar background */
[data-testid="stSidebar"] {
    background: #F0EBF4 !important;
    border-right: 1px solid #E2DAE8;
}
[data-testid="stSidebarContent"] {
    background: #F0EBF4 !important;
    padding-top: 0 !important;
}

/* Sidebar logo container */
.sidebar-logo-wrap {
    padding: 20px 16px 8px;
    display: flex;
    justify-content: center;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: #DDD4E8 !important;
    margin: 8px 0 !important;
}

/* Nav: hide group label */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    display: none !important;
}

/* Nav: each radio option */
[data-testid="stSidebar"] [data-testid="stRadioOption"] {
    border-radius: 10px;
    padding: 4px 8px;
    margin: 2px 0;
    transition: background 0.15s;
    cursor: pointer;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {
    font-size: 14px;
    font-weight: 500;
    color: #6B5F80;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
    background: rgba(124, 92, 191, 0.09) !important;
}

/* Active nav item */
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) {
    background: rgba(124, 92, 191, 0.15) !important;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) p {
    color: #7C5CBF !important;
    font-weight: 700 !important;
}

/* Hide radio indicator dot */
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div:first-child {
    display: none !important;
}

/* Sidebar version badge */
.sidebar-version {
    text-align: center;
    font-size: 11px;
    color: #AFA0C4;
    padding: 12px 0 4px;
}

/* Chord cell display */
.chord-cell-display {
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    white-space: pre-wrap;
    word-break: break-all;
    background: white;
    border: 1px solid #E2DAE8;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 14px;
    line-height: 1.9;
    color: #2D2840;
    margin: 6px 0 10px;
}

/* Primary buttons */
button[kind="primary"] {
    background: #7C5CBF !important;
    border-color: #7C5CBF !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
button[kind="primary"]:hover {
    background: #6B4FA0 !important;
    border-color: #6B4FA0 !important;
    color: white !important;
}

/* Secondary / default buttons */
button[kind="secondary"] {
    border-color: #C8B8DC !important;
    color: #7C5CBF !important;
    border-radius: 10px !important;
    background: white !important;
}
button[kind="secondary"]:hover {
    background: rgba(124, 92, 191, 0.07) !important;
    border-color: #9A7CC8 !important;
}

/* Download button */
[data-testid="stDownloadButton"] button {
    background: #4B3F6B !important;
    border-color: #4B3F6B !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: #3A2F54 !important;
    border-color: #3A2F54 !important;
}

/* Text inputs */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    border-radius: 8px !important;
    border-color: #E2DAE8 !important;
    background: white !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #7C5CBF !important;
    box-shadow: 0 0 0 3px rgba(124, 92, 191, 0.14) !important;
}

/* Action bar at bottom of Compose */
.action-bar {
    margin-top: 8px;
    padding-top: 16px;
    border-top: 1px solid #E2DAE8;
}
</style>
"""

# ── Chord helpers ─────────────────────────────────────────────────────────────

_ROOT_RE = re.compile(r"^([A-G][#b]?)(.*)")


def _is_valid_chord_symbol(token: str) -> bool:
    try:
        from changes.chord_parser import parse_chord_core
        parse_chord_core(token)
        return True
    except Exception:
        return False


def _is_valid_token(token: str) -> bool:
    return token in ("|", "||", "%") or _is_valid_chord_symbol(token)


def _transpose_root(root: str, semitones: int) -> str:
    pc = _ROOT_PC.get(root, 0)
    new_pc = (pc + semitones) % 12
    return (_SHARP_SCALE if semitones > 0 else _FLAT_SCALE)[new_pc]


def _transpose_chord(symbol: str, semitones: int) -> str:
    if symbol in ("|", "||", "%"):
        return symbol
    slash: str | None = None
    main = symbol
    if "/" in symbol:
        main, slash = symbol.split("/", 1)
    m = _ROOT_RE.match(main)
    if not m:
        return symbol
    new_main = _transpose_root(m.group(1), semitones) + m.group(2)
    if slash:
        sm = _ROOT_RE.match(slash)
        new_slash = (_transpose_root(sm.group(1), semitones) + sm.group(2)) if sm else slash
        return f"{new_main}/{new_slash}"
    return new_main


def _transpose_state(state: EditorState, semitones: int) -> None:
    state._snapshot()
    state.cells = [_transpose_chord(c, semitones) for c in state.cells]


# ── Session state init ────────────────────────────────────────────────────────

def _init_state() -> None:
    if "editor" not in st.session_state:
        st.session_state.editor = EditorState()
    state: EditorState = st.session_state.editor

    if "editor_title" not in st.session_state:
        st.session_state.editor_title = state.title
    if "editor_tempo" not in st.session_state:
        st.session_state.editor_tempo = state.tempo
    if "meter_num" not in st.session_state:
        st.session_state.meter_num = 4
    if "meter_den" not in st.session_state:
        st.session_state.meter_den = 4
    if "working_key_input" not in st.session_state:
        st.session_state.working_key_input = state.working_key
    if "editor_mode" not in st.session_state:
        st.session_state.editor_mode = "button"
    if "pending_root" not in st.session_state:
        st.session_state.pending_root = None
    if "pending_acc" not in st.session_state:
        st.session_state.pending_acc = ""
    if "ti" not in st.session_state:
        st.session_state.ti = ""


# ── Text input processing ─────────────────────────────────────────────────────

def _normalize_token(raw: str) -> str:
    """Capitalize root letter; lowercase quality. Structural tokens unchanged."""
    t = raw.strip()
    if t in ("|", "||", "%"):
        return t
    if not t or t[0].lower() not in "abcdefg":
        return t

    def _normalize_part(text: str) -> str:
        if not text or text[0].lower() not in "abcdefg":
            return text
        root = text[0].upper()
        rest = text[1:]
        if rest and rest[0] in ("b", "#"):
            return root + rest[0] + rest[1:].lower()
        return root + rest.lower()

    if "/" in t:
        main, bass = t.split("/", 1)
        return _normalize_part(main) + "/" + _normalize_part(bass)
    return _normalize_part(t)


def _process_text_input() -> None:
    """on_change callback: commit tokens on Enter (field cleared after commit)."""
    state: EditorState = st.session_state.editor
    raw: str = st.session_state.get("ti", "")

    if not raw.strip():
        st.session_state["ti"] = ""
        return

    for part in raw.split():
        token = _normalize_token(part)
        if _is_valid_token(token):
            state.insert(token)

    st.session_state["ti"] = ""


# ── Cell display ──────────────────────────────────────────────────────────────

def _cell_strip(state: EditorState) -> str:
    parts: list[str] = []
    for i, cell in enumerate(state.cells):
        if i == state.cursor:
            parts.append("▸")
        parts.append(cell)
    if state.cursor == len(state.cells):
        parts.append("▸")
    return " ".join(parts) if parts else "▸  (empty)"


# ── Export ───────────────────────────────────────────────────────────────────

def _export_syx_bytes(state: EditorState) -> bytes:
    """Generate Digitone II .syx bytes from the current editor state."""
    from changes.rendering.arrangement_renderer import render_arrangement
    from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
    from changes.digitone.planner import compile_timeline_to_digitone_plan
    from changes.exporters.digitone_events import digitone_compile_plan_to_events_yaml_payload
    from changes.models.digitone_target_profile import default_digitone_target_profile
    from changes.models.render_profile import default_render_profile
    from changes.digitone_backend import build_digitone_syx_from_events_yaml

    song = editor_to_song_model(state)
    rp = default_render_profile()
    tp = default_digitone_target_profile()
    arrangement = render_arrangement(song, rp)
    timeline = flatten_arrangement_to_timeline(arrangement, render_profile=rp)
    plan = compile_timeline_to_digitone_plan(timeline, tp)
    events_payload = digitone_compile_plan_to_events_yaml_payload(
        plan, track_default_velocity=tp.track_default_velocity
    )

    yaml_fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
    syx_fd, syx_path = tempfile.mkstemp(suffix=".syx")
    try:
        os.close(syx_fd)
        with os.fdopen(yaml_fd, "w") as f:
            yaml.safe_dump(events_payload, f, allow_unicode=False, sort_keys=False)
        build_digitone_syx_from_events_yaml(yaml_path, syx_path)
        return Path(syx_path).read_bytes()
    finally:
        for p in (yaml_path, syx_path):
            try:
                os.unlink(p)
            except OSError:
                pass


# ── Pages ─────────────────────────────────────────────────────────────────────

def _render_compose() -> None:
    _init_state()
    state: EditorState = st.session_state.editor

    st.title("Compose")

    # ── Row 1: Title / Tempo / Key + transpose ────────────────────────────────
    r1 = st.columns([4, 1, 2, 1, 1])

    with r1[0]:
        title = st.text_input("Title", key="editor_title")
        state.title = title

    with r1[1]:
        tempo = st.number_input("Tempo", min_value=30, max_value=300, step=1, key="editor_tempo")
        state.tempo = int(tempo)

    with r1[2]:
        _KEY_OPTIONS = ["C", "Db", "D", "Eb", "E", "F", "F#", "Gb", "G", "Ab", "A", "Bb", "B"]
        key_idx = _KEY_OPTIONS.index(state.working_key) if state.working_key in _KEY_OPTIONS else 0
        key_val = st.selectbox("Key", _KEY_OPTIONS, index=key_idx, key="working_key_input")
        state.working_key = key_val

    with r1[3]:
        st.write("")
        if st.button("△", key="key_up", use_container_width=True, help="半音上"):
            _transpose_state(state, +1)
            st.rerun()

    with r1[4]:
        st.write("")
        if st.button("▽", key="key_down", use_container_width=True, help="半音下"):
            _transpose_state(state, -1)
            st.rerun()

    # ── Row 2: Meter ──────────────────────────────────────────────────────────
    r2 = st.columns([1, 1, 1, 1, 1, 2, 3])
    r2[0].write("**Meter**")

    if r2[1].button("−", key="meter_minus", use_container_width=True):
        st.session_state.meter_num = max(1, st.session_state.meter_num - 1)
        st.rerun()

    r2[2].write(f"**{st.session_state.meter_num}**")

    if r2[3].button("+", key="meter_plus", use_container_width=True):
        st.session_state.meter_num += 1
        st.rerun()

    r2[4].write("**/**")

    den_options = [2, 4, 8]
    den_idx = den_options.index(st.session_state.meter_den) if st.session_state.meter_den in den_options else 1
    new_den = r2[5].selectbox(
        "den",
        den_options,
        index=den_idx,
        key="meter_den_widget",
        label_visibility="collapsed",
    )
    st.session_state.meter_den = new_den
    state.meter = f"{st.session_state.meter_num}/{st.session_state.meter_den}"

    # ── Mode toggle ────────────────────────────────────────────────────────────
    mode = st.session_state.editor_mode
    toggle_label = "テキスト入力に切り替え" if mode == "button" else "ボタン入力に切り替え"
    if st.button(toggle_label, key="mode_toggle"):
        st.session_state.editor_mode = "text" if mode == "button" else "button"
        st.rerun()

    # ── Cell display ───────────────────────────────────────────────────────────
    st.markdown(
        f"<div class='chord-cell-display'>{_cell_strip(state)}</div>",
        unsafe_allow_html=True,
    )

    # ── Input area ─────────────────────────────────────────────────────────────
    if st.session_state.editor_mode == "text":
        st.text_input(
            "コード入力 — Enter で確定",
            key="ti",
            on_change=_process_text_input,
            placeholder="例: Cmaj7  または  |  または  %",
        )

        with st.expander("入力インストラクション", expanded=True):
            st.markdown(_TEXT_INSTRUCTIONS)

        st.write("**操作**")
        sc = st.columns(5)
        if sc[0].button("← 左", key="t_left", use_container_width=True):
            state.move_left(); st.rerun()
        if sc[1].button("右 →", key="t_right", use_container_width=True):
            state.move_right(); st.rerun()
        if sc[2].button("Undo", key="t_undo", use_container_width=True):
            state.undo(); st.rerun()
        if sc[3].button("Delete", key="t_del", use_container_width=True):
            state.delete(); st.rerun()
        if sc[4].button("Clear", key="t_clear", use_container_width=True):
            state.clear(); st.rerun()

    else:
        pr = st.session_state.pending_root
        pa = st.session_state.pending_acc
        if pr:
            st.info(f"Pending: **{pr}{pa}** — quality を選択して確定")
        else:
            st.caption("Root → (Accidental) → Quality")

        st.write("**Root**")
        rc = st.columns(len(ROOTS))
        for i, r in enumerate(ROOTS):
            if rc[i].button(r, key=f"root_{r}", use_container_width=True):
                st.session_state.pending_root = r
                st.session_state.pending_acc = ""
                st.rerun()

        st.write("**Accidental**")
        ac = st.columns([1, 1, 3])
        if ac[0].button("♭", key="acc_b", use_container_width=True):
            st.session_state.pending_acc = "b"; st.rerun()
        if ac[1].button("♯", key="acc_s", use_container_width=True):
            st.session_state.pending_acc = "#"; st.rerun()
        ac[2].caption(
            f"{'♭ (b)' if pa == 'b' else '♯ (#)' if pa == '#' else '♮ natural'} selected"
        )

        st.write("**Quality**")
        for row in _QUALITY_ROWS:
            qc = st.columns(len(row))
            for i, (label, suffix) in enumerate(row):
                if qc[i].button(label, key=f"q_{label}", use_container_width=True):
                    if st.session_state.pending_root:
                        chord = f"{st.session_state.pending_root}{st.session_state.pending_acc}{suffix}"
                        state.insert(chord)
                        st.session_state.pending_root = None
                        st.session_state.pending_acc = ""
                    else:
                        st.warning("Root を選んでから Quality を押してください")
                    st.rerun()

        st.write("**Structure**")
        s = st.columns(8)
        if s[0].button("|",      key="s_bar",   use_container_width=True): state.insert("|");   st.rerun()
        if s[1].button("||",     key="s_sec",   use_container_width=True): state.insert("||");  st.rerun()
        if s[2].button("%",      key="s_rep",   use_container_width=True): state.insert("%");   st.rerun()
        if s[3].button("←",      key="s_left",  use_container_width=True): state.move_left();   st.rerun()
        if s[4].button("→",      key="s_right", use_container_width=True): state.move_right();  st.rerun()
        if s[5].button("Undo",   key="s_undo",  use_container_width=True): state.undo();        st.rerun()
        if s[6].button("Delete", key="s_del",   use_container_width=True): state.delete();      st.rerun()
        if s[7].button("Clear",  key="s_clear", use_container_width=True): state.clear();       st.rerun()

    # ── Preview ────────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Preview — SongModel")

    if state.cells:
        try:
            song = editor_to_song_model(state)
            lines: list[str] = []
            for m in song.measures:
                chords = "  ".join(
                    f"{h.symbol}({h.duration_quarters}q)" for h in m.harmony
                )
                lines.append(f"[{m.section_id}]  m{m.number}:  {chords}")
            st.code("\n".join(lines), language=None)
            with st.expander("SongModel JSON"):
                st.json(song_model_to_dict(song))
        except ValueError as exc:
            st.warning(f"変換エラー: {exc}")
    else:
        st.caption("No input yet.")

    # ── Action buttons ────────────────────────────────────────────────────────
    st.markdown("<div class='action-bar'>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("Export Syx", type="primary", use_container_width=True, key="export_syx_btn"):
            if not state.cells:
                st.warning("コードを入力してください")
            else:
                with st.spinner("SYX生成中..."):
                    try:
                        syx_bytes = _export_syx_bytes(state)
                        st.session_state._syx_bytes = syx_bytes
                        st.session_state._syx_fname = f"{state.title.strip() or 'changes'}.syx"
                        st.success("SYX生成完了")
                    except ModuleNotFoundError:
                        st.error(
                            "digitone-syx-toolkit が必要です:  \n"
                            "`pip install -e ../digitone-syx-toolkit`"
                        )
                    except ValueError as exc:
                        st.error(f"変換エラー: {exc}")

        if "_syx_bytes" in st.session_state:
            st.download_button(
                "↓ Download .syx",
                data=st.session_state._syx_bytes,
                file_name=st.session_state.get("_syx_fname", "changes.syx"),
                mime="application/octet-stream",
                use_container_width=True,
                key="download_syx_btn",
            )

    with btn_col2:
        if st.button("Send to Digitone II", use_container_width=True, key="send_digitone_btn"):
            st.info("Coming soon: MIDI経由でDigitone IIへ転送します")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_generate() -> None:
    st.title("Generate")
    st.divider()
    st.info("このページは開発中です。")


def _render_songlist() -> None:
    st.title("Songlist")
    st.divider()
    st.info("このページは開発中です。")


# ── Sidebar ──────────────────────────────────────────────────────────────────

def _build_sidebar() -> str:
    with st.sidebar:
        st.markdown("<div class='sidebar-logo-wrap'>", unsafe_allow_html=True)
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), width=110)
        else:
            st.markdown("### EUB Changes")
        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        page = st.radio(
            "Navigation",
            ["Compose", "Generate", "Songlist"],
            label_visibility="collapsed",
        )

        st.markdown(
            f"<div class='sidebar-version'>v{_APP_VERSION}</div>",
            unsafe_allow_html=True,
        )

    return page  # type: ignore[return-value]


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="EUB Changes",
        layout="wide",
        page_icon=str(_LOGO_PATH) if _LOGO_PATH.exists() else "🎵",
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    page = _build_sidebar()

    if page == "Compose":
        _render_compose()
    elif page == "Generate":
        _render_generate()
    else:
        _render_songlist()


if __name__ == "__main__":
    main()
