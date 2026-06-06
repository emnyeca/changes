"""Initial release Streamlit UI for EUB Changes."""

from __future__ import annotations

import html
import queue
import re
import threading
import time
import traceback as tb_module
from dataclasses import dataclass
from dataclasses import replace as _replace
from fractions import Fraction as _Frac
from pathlib import Path
from typing import Literal

import streamlit as st

from changes.app_settings import AppSettings, load_settings, save_settings
from changes.editor import EditorState, editor_to_song_model
from changes.key_signature import format_working_key, parse_working_key_display
from changes.library import SongEntry, delete_song, list_songs, overwrite_song, save_song
from changes.models.song_model import SongModel, song_model_to_dict
from changes.song_filter import extract_section_ids, filter_song_by_sections, transpose_song_model_preserving_structure
from changes.ui_pipeline import (
    count_auto_split_patterns,
    count_linear_patterns,
    song_to_syx_bytes,
    song_to_syx_bytes_bundle,
    song_to_syx_bytes_linear_split,
)

# ── Icons ─────────────────────────────────────────────────────────────────────

_ICON_LINEAR = ':material/arrow_forward:'
_ICON_BUNDLE = ':material/arrow_split:'
_ICON_IMPORT = ':material/convert_to_text:'
_ICON_LAYER_OPTIONS = ':material/account_tree:'
_ICON_SETTINGS = ':material/settings:'
_ICON_ADVANCED = ':material/logo_dev:'

_SEND_MODE_LINEAR = "Linear"
_SEND_MODE_BUNDLE = "Bundle by Section"
_SEND_MODE_OPTIONS = [_SEND_MODE_LINEAR, _SEND_MODE_BUNDLE]

# ── Paths ─────────────────────────────────────────────────────────────────────

_ASSETS = Path(__file__).parent.parent.parent / "docs" / "assets" / "1x"
_LOGO_PATH_HEADER = _ASSETS / "eub_changes_logo_header.png"
_LOGO_PATH = _ASSETS / "eub_changes_logo_square_transparent.png"
_ICON_PATH = _ASSETS / "icon_cloud.png"
_ICON_PATH_BASS = _ASSETS / "icon_bass.png"
_ICON_PATH_CHORD = _ASSETS / "icon_chord.png"
_APP_VERSION = "v0.1.0"

# ── Music constants ───────────────────────────────────────────────────────────

ROOTS = list("CDEFGAB")
_SHARP_SCALE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT_SCALE  = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_ROOT_PC: dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4,
    "F": 5, "E#": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11, "B#": 0,
}
_QUALITY_ROWS: list[list[tuple[str, str]]] = [
    [("maj",""),("m","m"),("dim","dim"),("aug","aug"),("sus2","sus2"),("sus4","sus4")],
    [("maj7","maj7"),("m7","m7"),("7","7"),("m7b5","m7b5"),("dim7","dim7"),("m6","m6"),("6","6"),("alt","alt")],
    [("maj9","maj9"),("m9","m9"),("9","9"),("13","13"),("7b9","7b9"),("7#9","7#9"),("7#11","7#11"),("7b13","7b13"),("add9","add9")],
]
_TEXT_INSTRUCTIONS = """\
**Valid Tokens** | Token | Example |
|---|---|
| Chord symbol | `Cmaj7` `Bbm7` `F#7` `Eb7b9` `G/B` |
| Repeat previous chord | `%` |
| Bar line | `|` |
| Section divider | `||` |

- Press **Enter** to commit tokens / use spaces to commit multiple tokens
- **ASCII only** — use `b` / `#` (do not use ♭/♯)
- Root letter is auto-capitalized: `cmaj7` -> `Cmaj7`
"""

# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
<style>
.stApp { background-color: #FAF7FA; }
[data-testid="stSidebar"] { background: #F0EBF4 !important; border-right: 1px solid #E2DAE8; }
[data-testid="stSidebarContent"] { background: #F0EBF4 !important; }
[data-testid="stSidebar"] hr { border-color: #DDD4E8 !important; margin: 8px 0 !important; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] { display: none !important; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] { border-radius: 10px; padding: 4px 8px; margin: 2px 0; transition: background 0.15s; cursor: pointer; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] p { font-size: 14px; font-weight: 500; color: #6B5F80; }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background: rgba(124,92,191,0.09) !important; }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) { background: rgba(124,92,191,0.15) !important; }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) p { color: #7C5CBF !important; font-weight: 700 !important; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div:first-child { display: none !important; }
.sidebar-version { text-align:center; font-size:11px; color:#AFA0C4; padding:12px 0 4px; }
[data-testid="stHorizontalBlock"]:first-of-type [data-testid="stButton"] button { height:36px; }
.chord-cell-display { font-family:'JetBrains Mono','Fira Code',monospace; white-space:pre-wrap; word-break:break-all; background:white; border:1px solid #E2DAE8; padding:12px 16px; border-radius:10px; font-size:14px; line-height:1.9; color:#2D2840; margin:6px 0 10px; }
.chord-cell-display .section-lbl { background:#E8E0F4; color:#7C5CBF; border-radius:4px; padding:1px 5px; font-size:12px; font-weight:700; margin-right:2px; }
.chord-cell-display .meter-lbl { background:#E9EEF6; color:#53627A; border:1px solid #D5DEEA; border-radius:4px; padding:1px 5px; font-size:12px; font-weight:700; margin-right:2px; }
.send-area { background:white; border:1px solid #E2DAE8; border-radius:12px; padding:16px; margin-top:16px; }
.eub-status-slot { margin:4px 0; display:flex; flex-direction:column; gap:4px; }
.eub-status-line { padding:7px 10px; border-radius:7px; font-size:13px; line-height:1.35; white-space:pre-line; }
.eub-status-line-info { background:#EEF3FA; border:1px solid #C9D6E6; color:#31445F; }
.eub-status-line-warning { background:#FFF4DF; border:1px solid #F2C572; color:#6F4A00; }
.eub-status-line-error { background:#FFF0F0; border:1px solid #E4A2A2; color:#842029; }
.eub-status-line-success { background:#EEF8EF; border:1px solid #B8D9BD; color:#24572F; }
.autosplit-warn { color:#E07000; font-size:13px; }
button[kind="primary"] { background:#7C5CBF !important; border-color:#7C5CBF !important; color:white !important; border-radius:10px !important; font-weight:600 !important; }
button[kind="primary"]:hover { background:#6B4FA0 !important; border-color:#6B4FA0 !important; }
button[kind="secondary"] { border-color:#C8B8DC !important; color:#7C5CBF !important; border-radius:10px !important; background:white !important; }
button[kind="secondary"]:hover { background:rgba(124,92,191,0.07) !important; }
[data-testid="stDownloadButton"] button { background:#4B3F6B !important; border-color:#4B3F6B !important; color:white !important; border-radius:10px !important; }
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input { border-radius:8px !important; border-color:#E2DAE8 !important; background:white !important; }
</style>
"""

# ── MIDI helpers ──────────────────────────────────────────────────────────────

_NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def _midi_name(n: int) -> str:
    return f"{_NOTE_NAMES[n % 12]}{n // 12 - 1}"

def _active_accidental_scale() -> list[str]:
    settings = getattr(st.session_state, "_settings", None)
    if settings and getattr(settings, "note_accidental", "flat") == "sharp":
        return _SHARP_SCALE
    return _FLAT_SCALE

def _midi_display_name(n: int) -> str:
    scale = _active_accidental_scale()
    return f"{scale[n % 12]}{n // 12 - 1}"

def _range_display(center: int, lo: int, hi: int) -> str:
    return f"{_midi_display_name(center)} ({_midi_display_name(center-lo)}–{_midi_display_name(center+hi)})"

def _note_options(lo_midi: int, hi_midi: int) -> list[str]:
    return [_midi_name(n) for n in range(lo_midi, hi_midi + 1)]

def _note_options_index(options: list[str], midi: int) -> int:
    name = _midi_name(midi)
    return options.index(name) if name in options else 0

def _name_to_midi(name: str) -> int:
    for base in range(0, 128, 12):
        if _midi_name(base) == name:
            return base
    note_part = name[:-1] if name[-1].lstrip("-").isdigit() else name
    oct_part = name[len(note_part):]
    pc = _NOTE_NAMES.index(note_part) if note_part in _NOTE_NAMES else 0
    return (int(oct_part) + 1) * 12 + pc

def _render_header_field(label: str, icon: str, value: str | None = None, *, render_controls=None, render_title=False, has_song=True) -> None:
    if render_controls is not None:
        render_controls()
    elif render_title:
        if has_song:
            st.markdown(f"### {value or ''}{'<span style="color:orange; font-size:16px"> ●</span>' if st.session_state._editor_dirty else ''}", unsafe_allow_html=True)
        else:
            st.caption("### Select a song")
    else:
        st.write(f"**{value or ''}**")
    
    st.caption(f"{icon} {label}", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

def _ss_init() -> None:
    if "_settings" not in st.session_state:
        st.session_state._settings = load_settings()
    if "_library" not in st.session_state:
        _refresh_library()
    if "_selected_path" not in st.session_state:
        st.session_state._selected_path = None
    if "editor" not in st.session_state:
        st.session_state.editor = EditorState()
    if "_editor_dirty" not in st.session_state:
        st.session_state._editor_dirty = False
    # editor sub-keys
    for key, default in [
        ("editor_title", ""), ("editor_tempo", 120), ("meter_num", 4),
        ("meter_den", 4), ("working_key_input", "C"), ("editor_mode", "button"),
        ("_editor_working_key_mode", None),
        ("pending_root", None), ("pending_acc", ""), ("ti", ""),
        ("_compose_save_mode", None), ("_compose_save_pending", None),
        ("_table_save_mode", None), ("_table_save_pending", None),
        ("_table_save_suppressed_signature", None),
        ("_songlist_table_reset_token", 0),
        ("_songlist_error_message", None),
        ("_pending_deselect", False),
        ("_midi_update_candidates", None), ("_midi_update_kept", None), ("_midi_update_unmatched", None),
        ("_import_bundle_result", None),
        ("_import_progress_request", None), ("_import_progress_status", None),
        ("_import_uploader_reset_token", 0),
        ("_send_confirm_mode", None),
        # Action-specific isolated result state
        ("_send_area_ok", False), ("_send_area_ok_detail", None),
        ("_send_area_error", None),
        ("_adv_syx_ok", False), ("_adv_syx_bytes", None), ("_adv_syx_fname", None), ("_adv_syx_error", None),
        ("_dry_run_result", None), ("_dry_run_error", None),
        # Transpose dirty override: preserves original SongModel structure on transpose
        ("_dirty_song_override", None), ("_dirty_song_override_cells", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default
    # Preview dialog state
    for key, default in _PREVIEW_STATE_KEYS:
        if key not in st.session_state:
            st.session_state[key] = default


def _refresh_library() -> None:
    s = st.session_state.get("_settings") or load_settings()
    st.session_state._library = list_songs(Path(s.library_path))


def _reset_song_table_view(*, clear_search: bool = False) -> None:
    st.session_state._songlist_table_reset_token += 1
    if clear_search:
        st.session_state["_sl_search"] = ""


def _request_rerun(
    *,
    reason: str | None = None,
    reset_song_table: bool = False,
    clear_song_search: bool = False,
    refresh_library: bool = False,
    close_send_confirm: bool = False,
    clear_import_state: bool = False,
    success_message: str | None = None,
    error_message: str | None = None,
) -> None:
    request = {
        "reason": reason,
        "reset_song_table": reset_song_table,
        "clear_song_search": clear_song_search,
        "refresh_library": refresh_library,
        "close_send_confirm": close_send_confirm,
        "clear_import_state": clear_import_state,
        "success_message": success_message,
        "error_message": error_message,
    }
    st.session_state["_last_rerun_request"] = request
    if reason:
        st.session_state["_last_rerun_reason"] = reason
    if refresh_library:
        _refresh_library()
    if reset_song_table:
        _reset_song_table_view(clear_search=clear_song_search)
    if close_send_confirm:
        st.session_state._send_confirm = False
        st.session_state._send_confirm_mode = None
    if clear_import_state:
        st.session_state._import_progress_request = None
        st.session_state._import_progress_status = None
        st.session_state._import_pending = []
        st.session_state._import_pending_failed = []
        st.session_state._import_conflict_mode = None
        st.session_state._import_conflict_titles = []
    if success_message:
        st.session_state["_ui_success_message"] = success_message
    if error_message:
        st.session_state["_ui_error_message"] = error_message
    st.rerun()


def _no_explicit_rerun(reason: str) -> None:
    st.session_state["_last_no_explicit_rerun_reason"] = reason


def _render_pending_ui_messages() -> None:
    msg = st.session_state.pop("_ui_success_message", None)
    if msg:
        st.success(str(msg))
    err = st.session_state.pop("_ui_error_message", None)
    if err:
        st.error(str(err))


# ── Header data sources ───────────────────────────────────────────────────────

def _dirty_song() -> SongModel | None:
    override = st.session_state.get("_dirty_song_override")
    if override is not None:
        # Validate override is still consistent with editor cells (no manual edits since transpose)
        override_cells = st.session_state.get("_dirty_song_override_cells")
        state_for_check: EditorState = st.session_state.get("editor")
        current_cells = tuple(state_for_check.cells) if state_for_check else ()
        if override_cells == current_cells:
            return override
        # Editor cells changed since override was set (manual edit); invalidate
        st.session_state["_dirty_song_override"] = None

    state: EditorState = st.session_state.get("editor")
    if state and state.cells:
        try:
            song = editor_to_song_model(state)
            mode = st.session_state.get("_editor_working_key_mode")
            if mode is not None:
                return _replace(song, working_key_mode=mode)
            return song
        except Exception:
            pass
    return None


def _selected_library_song() -> SongModel | None:
    path = st.session_state.get("_selected_path")
    if path:
        for e in st.session_state.get("_library", []):
            if e.path == path and e.song:
                return e.song
    return None


def _display_section_label(section_id: str | None) -> str:
    if section_id is None:
        return ""
    text = str(section_id).strip()
    if not text:
        return ""
    coda_match = re.match(r"^(coda)(.*)$", text, flags=re.IGNORECASE)
    if coda_match:
        return f"CODA{coda_match.group(2)}"
    match = _SECTION_OCC_RE.match(text)
    if not match:
        return text
    label = match.group("label") or text
    occ = int(match.group("occ"))
    if occ <= 1 and len(label) > 1:
        return label
    return f"{label}{occ}"


def _current_song() -> SongModel | None:
    selected = _selected_library_song()
    if selected is not None and not st.session_state.get("_editor_dirty"):
        return selected
    return _dirty_song() or selected


def _section_filter_label(section_id: str | None) -> str:
    return _display_section_label(section_id)


def _playback_song() -> SongModel | None:
    return _current_song()


def _meter_label(numerator: int, denominator: int) -> str:
    return f"{int(numerator)}/{int(denominator)}"


def _song_meter_summary(song: SongModel | None) -> str:
    if song is None or not song.measures:
        return "—"
    seen: set[tuple[int, int]] = set()
    labels: list[str] = []
    for measure in song.measures:
        meter = (int(measure.meter_numerator), int(measure.meter_denominator))
        if meter in seen:
            continue
        seen.add(meter)
        labels.append(_meter_label(*meter))
    return ", ".join(labels) if labels else "—"


def _barline_cell_indices(state: EditorState) -> list[int]:
    return [i for i, cell in enumerate(state.cells) if cell in ("|", "||")]


def _meter_labels_by_barline_index(
    song: SongModel | None,
    state: EditorState,
) -> dict[int | str, str]:
    if song is None or not song.measures:
        return {}

    labels: dict[int | str, str] = {
        "initial": _meter_label(
            song.measures[0].meter_numerator,
            song.measures[0].meter_denominator,
        )
    }
    previous = (
        int(song.measures[0].meter_numerator),
        int(song.measures[0].meter_denominator),
    )
    barline_indices = _barline_cell_indices(state)
    for measure_index, measure in enumerate(song.measures[1:], start=2):
        current = (int(measure.meter_numerator), int(measure.meter_denominator))
        if current == previous:
            continue
        barline_offset = measure_index - 2
        if barline_offset < len(barline_indices):
            labels[barline_indices[barline_offset]] = _meter_label(*current)
        previous = current
    return labels

# ── Logo ─────────────────────────────────────────────────────────────
st.logo(
    _LOGO_PATH_HEADER, 
    link="https://github.com/emnyeca/changes/", 
    size="large", 
    icon_image=_LOGO_PATH_HEADER
    )

# ── Common header ─────────────────────────────────────────────────────────────

def _render_header() -> None:
    song = _current_song()
    title = song.title if song else "Select a song"
    key = format_working_key(song.working_key, getattr(song, "working_key_mode", None)) if song else "—"
    tempo = str(int(song.performance_tempo)) if song else "—"
    meter = _song_meter_summary(song)
    has_selected_song = st.session_state.get("_selected_path") is not None

    def _render_transpose_controls() -> None:
        down_col, up_col = st.columns([1,1], vertical_alignment="bottom", gap="small")
        with down_col:
            if st.button("▽", key="key_down", help="Transpose down by one semitone", disabled=not has_selected_song, width="stretch"):
                base_song = _current_song()
                _transpose_state(st.session_state.editor, -1)
                st.session_state._editor_dirty = True
                if base_song is not None:
                    transposed = transpose_song_model_preserving_structure(
                        base_song,
                        lambda sym: _transpose_chord(sym, -1),
                        lambda key: _transpose_root(key, -1),
                    )
                    st.session_state["_dirty_song_override"] = transposed
                    st.session_state["_dirty_song_override_cells"] = tuple(st.session_state.editor.cells)
                _request_rerun()
        with up_col:
            if st.button("△", key="key_up", help="Transpose up by one semitone", disabled=not has_selected_song, width="stretch"):
                base_song = _current_song()
                _transpose_state(st.session_state.editor, +1)
                st.session_state._editor_dirty = True
                if base_song is not None:
                    transposed = transpose_song_model_preserving_structure(
                        base_song,
                        lambda sym: _transpose_chord(sym, +1),
                        lambda key: _transpose_root(key, +1),
                    )
                    st.session_state["_dirty_song_override"] = transposed
                    st.session_state["_dirty_song_override_cells"] = tuple(st.session_state.editor.cells)
                _request_rerun()

    with st.container(border=True):
        song_col, key_col, tempo_col, meter_col, transpose_col = st.columns([3.2, 1.2, 1.2, 1.2, 1.2], vertical_alignment="bottom", gap="small")
        with song_col:
            _composer = getattr(song, "composer", None) if song else None
            _song_label = f"Song by {_composer}" if _composer else "Song"
            _render_header_field(_song_label, ":material/library_music:", title, render_title=True, has_song=bool(song))
        with key_col:
            _render_header_field("Key", ":material/key:", key)
        with tempo_col:
            _render_header_field("Tempo", ":material/pace:", tempo)
        with meter_col:
            _render_header_field("Meter", ":material/pie_chart:", meter)
        with transpose_col:
            _render_header_field("Transpose", ":material/piano:", render_controls=_render_transpose_controls)


# ── Sidebar ───────────────────────────────────────────────────────────────────

# ── Chord helpers (editor) ────────────────────────────────────────────────────

_ROOT_RE = re.compile(r"^([A-G][#b]?)(.*)")
_SECTION_OCC_RE = re.compile(r"^(?P<label>.+?)(?:__|_)OCC(?P<occ>\d+)$")


def _is_valid_chord(token: str) -> bool:
    try:
        from changes.chord_parser import parse_chord_core
        parse_chord_core(token)
        return True
    except Exception:
        return False


def _is_valid_token(token: str) -> bool:
    return token in ("|", "||", "%") or _is_valid_chord(token)


def _transpose_root(root: str, semitones: int) -> str:
    pc = _ROOT_PC.get(root, 0)
    new_pc = (pc + semitones) % 12
    return _active_accidental_scale()[new_pc]


def _normalize_chord_accidental(symbol: str) -> str:
    """Rewrite chord root (and slash bass) to match the active accidental setting."""
    if symbol in ("|", "||", "%"):
        return symbol
    scale = _active_accidental_scale()
    slash: str | None = None
    main = symbol
    if "/" in symbol:
        main, slash = symbol.split("/", 1)
    m = _ROOT_RE.match(main)
    if not m:
        return symbol
    pc = _ROOT_PC.get(m.group(1))
    if pc is None:
        return symbol
    new_main = scale[pc] + m.group(2)
    if slash:
        sm = _ROOT_RE.match(slash)
        if sm:
            slash_pc = _ROOT_PC.get(sm.group(1))
            new_slash = (scale[slash_pc] + sm.group(2)) if slash_pc is not None else slash
        else:
            new_slash = slash
        return f"{new_main}/{new_slash}"
    return new_main


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
    if state.working_key:
        state.working_key = _transpose_root(state.working_key, semitones)


def _normalize_token(raw: str) -> str:
    t = raw.strip()
    if t in ("|", "||", "%"):
        return t
    if not t or t[0].lower() not in "abcdefg":
        return t
    def _norm(text: str) -> str:
        if not text or text[0].lower() not in "abcdefg":
            return text
        root = text[0].upper()
        rest = text[1:]
        return root + (rest[0] + rest[1:].lower() if rest and rest[0] in "b#" else rest.lower())
    if "/" in t:
        a, b = t.split("/", 1)
        return _norm(a) + "/" + _norm(b)
    return _norm(t)


def _process_text_input() -> None:
    state: EditorState = st.session_state.editor
    raw: str = st.session_state.get("ti", "")
    if raw.strip():
        for part in raw.split():
            token = _normalize_token(part)
            if _is_valid_token(token):
                state.insert(token)
                st.session_state._editor_dirty = True
    st.session_state["ti"] = ""


def _badge_html(class_name: str, label: str) -> str:
    return f'<mark class="{class_name}">{label}</mark>'


def _chord_display_html(state: EditorState, song: SongModel | None = None) -> str:
    """Build HTML chord display with highlighted section and meter labels."""
    section_labels: dict[int | str, str] = st.session_state.get(
        "_editor_section_labels", {}
    )
    meter_labels = _meter_labels_by_barline_index(song, state)
    parts: list[str] = []

    initial = section_labels.get("initial", "")
    initial_meter = meter_labels.get("initial", "")
    initial_badges: list[str] = []
    if initial:
        initial_badges.append(_badge_html("section-lbl", _display_section_label(str(initial))))
    if initial_meter:
        initial_badges.append(_badge_html("meter-lbl", str(initial_meter)))
    if initial_badges:
        parts.append("".join(initial_badges) + "||")

    for i, cell in enumerate(state.cells):
        if i == state.cursor:
            parts.append("▸")
        if cell == "||":
            label = section_labels.get(i, "")
            meter = meter_labels.get(i, "")
            badges: list[str] = []
            if label:
                badges.append(_badge_html("section-lbl", _display_section_label(str(label))))
            if meter:
                badges.append(_badge_html("meter-lbl", str(meter)))
            parts.append("".join(badges) + "||" if badges else "||")
        elif cell == "|":
            meter = meter_labels.get(i, "")
            parts.append(_badge_html("meter-lbl", str(meter)) + "|" if meter else "|")
        else:
            parts.append(_normalize_chord_accidental(cell))

    if state.cursor == len(state.cells):
        parts.append("▸")

    return " ".join(parts) if parts else "▸  (empty)"


@st.dialog("Save Edited Song", dismissible=False)
def _dialog_table_save() -> None:
    pending = st.session_state.get("_table_save_pending")
    if pending is None:
        return

    existing_title = str(pending.get("existing_title") or "Untitled")
    changes = pending.get("changes") or []
    st.warning(f'You are editing the existing song "{existing_title}". How would you like to save?')
    st.markdown("**Changed fields:**")
    if changes:
        for field, before, after in changes:
            st.write(f"- {field}: `{before}` -> `{after}`")
    else:
        st.write("- No field-level diff available")

    c1, c2, c3 = st.columns(3, width = "stretch", gap="small")
    if c1.button("Update", type="primary", key="tsd_update", use_container_width=True):
        st.session_state._table_save_mode = "update"
        _request_rerun()
    if c2.button("Keep both", key="tsd_keep", use_container_width=True):
        st.session_state._table_save_mode = "keep_both"
        _request_rerun()
    if c3.button("Cancel", key="tsd_cancel", use_container_width=True):
        st.session_state._table_save_suppressed_signature = pending.get("signature")
        st.session_state._table_save_mode = None
        st.session_state._table_save_pending = None
        _request_rerun(reset_song_table=True)


@st.dialog("Discard Unsaved Changes?", dismissible=False)
def _dialog_pending_switch() -> None:
    pending_switch = st.session_state.get("_pending_switch")
    if pending_switch is None:
        return

    st.warning(f'Unsaved changes will be discarded. Switch to "{pending_switch.title}"?')
    col_cancel, col_discard = st.columns([1, 1], width="stretch", gap="small")
    if col_cancel.button("Cancel", key="sw_cancel", use_container_width=True):
        st.session_state._pending_switch = None
        _request_rerun(reset_song_table=True)
    if col_discard.button("Discard and switch", type="primary", key="sw_discard", use_container_width=True):
        _do_switch_song(pending_switch)
        _request_rerun(reset_song_table=True)


def _do_deselect_song() -> None:
    from changes.editor import EditorState
    st.session_state._selected_path = None
    st.session_state._pending_deselect = False
    st.session_state.editor = EditorState()
    st.session_state._editor_dirty = False
    st.session_state._dirty_song_override = None
    st.session_state._dirty_song_override_cells = None


def _try_deselect_song() -> None:
    if st.session_state._editor_dirty:
        st.session_state._pending_deselect = True
        _reset_song_table_view()
    else:
        _do_deselect_song()


@st.dialog("Discard Unsaved Changes?", dismissible=False)
def _dialog_pending_deselect() -> None:
    if not st.session_state.get("_pending_deselect"):
        return
    st.warning("Unsaved changes will be discarded.")
    col_cancel, col_discard = st.columns([1, 1], width="stretch", gap="small")
    if col_cancel.button("Cancel", key="desel_cancel", use_container_width=True):
        st.session_state._pending_deselect = False
        _request_rerun(reset_song_table=True)
    if col_discard.button("Discard", type="primary", key="desel_discard", use_container_width=True):
        _do_deselect_song()
        _request_rerun(reset_song_table=True)


@st.dialog("Delete Song", dismissible=False)
def _dialog_delete_confirm() -> None:
    del_path = st.session_state.get("_delete_confirm")
    if del_path is None:
        return

    entries: list[SongEntry] = st.session_state.get("_library", [])
    entry = next((e for e in entries if e.path == del_path), None)
    name = entry.title if entry else del_path.name
    st.warning(f'Delete "{name}"? This removes the SongModel file.')
    c1, c2 = st.columns([1, 1], width="stretch", gap="small")
    if c1.button("Cancel", key="del_cancel", use_container_width=True):
        st.session_state._delete_confirm = None
        _request_rerun(reset_song_table=True)
    if c2.button("Delete", type="primary", key="del_confirm", use_container_width=True):
        delete_song(del_path)
        if st.session_state._selected_path == del_path:
            st.session_state._selected_path = None
        st.session_state._delete_confirm = None
        _request_rerun(
            refresh_library=True,
            reset_song_table=True,
            success_message=f"Deleted: {name}",
        )


@st.dialog("Import Conflicts", dismissible=False)
def _dialog_import_conflict() -> None:
    conflicts = st.session_state.get("_import_conflict_titles", [])
    st.warning(
        f"Duplicate titles found: {', '.join(conflicts)}\n\n"
        "How should duplicates be handled?"
    )
    c1, c2, c3 = st.columns(3, width="stretch", gap="small")
    if c1.button("Overwrite all", type="primary", key="ic_over", use_container_width=True):
        st.session_state._import_conflict_mode = None
        st.session_state._import_progress_request = {"kind": "save", "mode": "overwrite"}
        _request_rerun()
    if c2.button("Keep both", key="ic_keep", use_container_width=True):
        st.session_state._import_conflict_mode = None
        st.session_state._import_progress_request = {"kind": "save", "mode": "keep_both"}
        _request_rerun()
    if c3.button("Cancel import", key="ic_cancel", use_container_width=True):
        _request_rerun(clear_import_state=True)


@st.dialog("Import Progress", dismissible=False)
def _dialog_import_progress() -> None:
    request = st.session_state.get("_import_progress_request")
    status = st.session_state.get("_import_progress_status")
    progress = st.progress(0)
    message = st.empty()

    if request is not None and status is None:
        try:
            _run_import_progress_request(request, progress, message)
            status = st.session_state._import_progress_status
        except Exception as exc:
            st.session_state._import_progress_request = None
            status = {"ok": False, "message": str(exc)}
            st.session_state._import_progress_status = status

    if status:
        progress.progress(100)
        if status.get("ok"):
            st.success(status.get("message", "Import completed."))
        else:
            st.error(status.get("message", "Import failed."))
        if st.button("Close", type="primary", key="_import_progress_close", use_container_width=True):
            status_message = status.get("message", "Import completed.")
            st.session_state._import_progress_request = None
            st.session_state._import_progress_status = None
            st.session_state._import_uploader_reset_token += 1
            _request_rerun(
                reset_song_table=True,
                success_message=status_message if status.get("ok") else None,
                error_message=status_message if not status.get("ok") else None,
            )


def _run_import_progress_request(request: dict, progress, message) -> None:
    stage_base = {
        "zip_open": 2,
        "zip_scan": 8,
        "zip_read": 18,
        "zip_complete": 28,
        "scan_files": 34,
        "parse_file": 42,
        "songmodel_build": 52,
        "validation": 72,
        "save": 84,
        "complete": 96,
        "error": 100,
    }
    stage_span = {
        "zip_open": 4,
        "zip_scan": 10,
        "zip_read": 10,
        "zip_complete": 4,
        "scan_files": 6,
        "parse_file": 10,
        "songmodel_build": 20,
        "validation": 12,
        "save": 12,
        "complete": 4,
        "error": 0,
    }

    def _progress(stage: str, current: int, total: int, text: str) -> None:
        safe_total = max(int(total), 1)
        ratio = min(max(int(current), 0) / safe_total, 1.0)
        pct = min(100, int(stage_base.get(stage, 1) + stage_span.get(stage, 1) * ratio))
        progress.progress(pct)
        message.write(f"**{stage.replace('_', ' ').title()}**  {current}/{safe_total}  {text}")

    kind = request.get("kind")
    if kind == "prepare":
        _start_import(request.get("files", []), progress_callback=_progress)
        result = st.session_state.get("_import_result")
        conflicts = st.session_state.get("_import_conflict_titles") or []
        if conflicts:
            msg = f"Validation found {len(conflicts)} duplicate title(s). Close this dialog to choose how to save."
            ok = True
        elif result:
            msg = f"Import completed. Success: {result['ok']}  Failed: {len(result['failed'])}"
            ok = int(result.get("ok", 0)) > 0 or not result.get("failed")
        else:
            msg = "Import prepared."
            ok = True
        st.session_state._import_progress_status = {"ok": ok, "message": msg}
    elif kind == "save":
        mode = str(request.get("mode") or "keep_both")
        _do_import(mode, progress_callback=_progress)
        st.session_state._import_pending = []
        st.session_state._import_conflict_titles = []
        _refresh_library()
        result = st.session_state.get("_import_result") or {"ok": 0, "failed": []}
        ok = int(result.get("ok", 0))
        failed = result.get("failed", [])
        st.session_state._import_progress_status = {
            "ok": ok > 0 or not failed,
            "message": f"Import completed. Success: {ok}  Failed: {len(failed)}",
        }
    else:
        raise ValueError(f"Unknown import progress request: {kind}")

    st.session_state._import_progress_request = None


# ─────────────────────────────────────────────────────────────────────────────
# Page: Songlist
# ─────────────────────────────────────────────────────────────────────────────

def _render_songlist(show_import: bool = True) -> None:
    entries: list[SongEntry] = st.session_state._library
    table_save_pending = st.session_state.get("_table_save_mode") == "pending"
    pending_switch = st.session_state.get("_pending_switch")
    pending_deselect = bool(st.session_state.get("_pending_deselect"))
    del_path = st.session_state.get("_delete_confirm")
    import_conflict_pending = st.session_state.get("_import_conflict_mode") == "pending"
    import_progress_pending = (
        st.session_state.get("_import_progress_request") is not None
        or st.session_state.get("_import_progress_status") is not None
    )
    midi_update_pending = st.session_state.get("_midi_update_candidates") is not None

    ui_locked = (
        table_save_pending
        or pending_switch is not None
        or pending_deselect
        or del_path is not None
        or import_conflict_pending
        or import_progress_pending
        or midi_update_pending
    )

    if st.session_state.get("_table_save_mode") in ("update", "keep_both"):
        _execute_table_save(st.session_state._table_save_mode)
        saved_name = st.session_state.get("_table_save_last_saved_name")
        st.session_state._table_save_mode = None
        st.session_state._table_save_pending = None
        st.session_state._table_save_suppressed_signature = None
        _request_rerun(
            reset_song_table=True,
            refresh_library=True,
            success_message=f"Saved: {saved_name}" if saved_name else "Saved.",
        )

    # Process resolved imports
    if st.session_state.get("_import_conflict_mode") in ("overwrite", "keep_both"):
        st.session_state._import_progress_request = {
            "kind": "save",
            "mode": st.session_state._import_conflict_mode,
        }
        st.session_state._import_conflict_mode = None
        _request_rerun()

    # ── Search ────────────────────────────────────────────────────────────────
    if st.session_state.get("_songlist_error_message"):
        st.error(str(st.session_state._songlist_error_message))
        st.session_state._songlist_error_message = None

    search = st.text_input(
        "Search songs",
        placeholder="Search With Title…",
        label_visibility="collapsed",
        key="_sl_search",
        disabled=ui_locked,
        icon=":material/search:"
    )
    filtered = [e for e in entries if search.lower() in e.title.lower()] if search else entries

    # ── Song table ────────────────────────────────────────────────────────────
    import pandas as pd

    def _meter(e: SongEntry) -> str:
        return _song_meter_summary(e.song)

    # Keep column dtypes stable even when filtered is empty; Streamlit data_editor
    # rejects text column configs if pandas infers float dtype from empty data.
    orig_df = pd.DataFrame({
        "Select": pd.Series([st.session_state._selected_path == e.path for e in filtered], dtype="bool"),
        "Title": pd.Series([e.title+"⚠" if e.error else e.title for e in filtered], dtype="string"),
        "Key":   pd.Series([format_working_key(e.song.working_key, getattr(e.song, "working_key_mode", None)) if e.song else "-" for e in filtered], dtype="string"),
        "Tempo": pd.Series([int(e.song.performance_tempo) if e.song else 0 for e in filtered], dtype="Int64"),
        "Meter": pd.Series([_meter(e) for e in filtered], dtype="string"),
        "Delete": pd.Series([False for _ in filtered], dtype="bool"),
    })

    table_key = f"_sl_table_{int(st.session_state._songlist_table_reset_token)}"
    edited_df = st.data_editor(
        orig_df,
        height=260,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=True if ui_locked else ["Meter"],
        key=table_key,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", width="small"),
            "Title": st.column_config.TextColumn(f"{len(filtered)} song(s)", width="large"),
            "Key":   st.column_config.TextColumn("Key", width="small"),
            "Tempo": st.column_config.NumberColumn("Tempo", min_value=30, max_value=300, width="small"),
            "Meter": st.column_config.TextColumn("Meter", width="small"),
            "Delete": st.column_config.CheckboxColumn("Delete", width="small"),
        },
    )

    # Table-integrated single-row select (radio-like)
    selected_rows = [i for i in range(len(edited_df)) if bool(edited_df.at[i, "Select"])]
    if selected_rows and not ui_locked:
        # Prefer a newly selected row when multiple rows are checked.
        newly_selected = [
            i for i in selected_rows
            if i < len(orig_df) and (not bool(orig_df.at[i, "Select"]))
        ]
        target_idx = (newly_selected[-1] if newly_selected else selected_rows[0])
        if 0 <= target_idx < len(filtered):
            target_entry = filtered[target_idx]
            if st.session_state._selected_path != target_entry.path:
                _try_select_song(target_entry)
                _request_rerun(reset_song_table=True)
    elif not selected_rows and not ui_locked and st.session_state._selected_path is not None:
        # Deselect: user unchecked the currently selected row
        deselected = [
            i for i in range(min(len(edited_df), len(orig_df)))
            if bool(orig_df.at[i, "Select"]) and not bool(edited_df.at[i, "Select"])
        ]
        if deselected:
            _try_deselect_song()
            _request_rerun(reset_song_table=True)

    # Table-integrated delete action (rightmost column)
    delete_rows = [
        i for i in range(len(edited_df))
        if bool(edited_df.at[i, "Delete"]) and (i < len(orig_df) and not bool(orig_df.at[i, "Delete"]))
    ]
    if delete_rows and not ui_locked:
        delete_idx = delete_rows[-1]
        if 0 <= delete_idx < len(filtered):
            st.session_state._delete_confirm = filtered[delete_idx].path
            _request_rerun(reset_song_table=True)

    # Persist inline edits (Title / Key / Tempo)
    if not table_save_pending and not ui_locked:
        for i, entry in enumerate(filtered):
            if entry.song is None:
                continue
            new_title = edited_df.at[i, "Title"] if i < len(edited_df) else entry.title
            new_key   = edited_df.at[i, "Key"]   if i < len(edited_df) else format_working_key(entry.song.working_key, getattr(entry.song, "working_key_mode", None))
            new_tempo = edited_df.at[i, "Tempo"] if i < len(edited_df) else int(entry.song.performance_tempo)

            title_val = str(new_title).strip()
            key_val = str(new_key).strip()
            tempo_val = int(new_tempo)

            old_title = entry.title
            old_key = format_working_key(entry.song.working_key, getattr(entry.song, "working_key_mode", None))
            old_tempo = int(entry.song.performance_tempo)

            if (
                title_val != old_title
                or key_val != old_key
                or tempo_val != old_tempo
            ):
                if not title_val:
                    st.session_state._songlist_error_message = "Title cannot be empty"
                    _request_rerun(reset_song_table=True)
                if tempo_val < 30 or tempo_val > 300:
                    st.session_state._songlist_error_message = "Tempo must be between 30 and 300"
                    _request_rerun(reset_song_table=True)

                parsed_key, parsed_mode = parse_working_key_display(key_val)
                if parsed_key is None and key_val not in ("", "-", "?"):
                    st.session_state._songlist_error_message = (
                        "Invalid key format. Examples: C, Em, F#m, Bb, C?, -"
                    )
                    _request_rerun(reset_song_table=True)

                changed_fields: list[tuple[str, str, str]] = []
                if title_val != old_title:
                    changed_fields.append(("Title", old_title, title_val))
                if key_val != old_key:
                    changed_fields.append(("Key", old_key or "(empty)", key_val or "(empty)"))
                if tempo_val != old_tempo:
                    changed_fields.append(("Tempo", str(old_tempo), str(tempo_val)))

                updated_song = SongModel(
                    title=title_val,
                    working_key=parsed_key,
                    working_key_mode=parsed_mode,
                    performance_tempo=_Frac(tempo_val).limit_denominator(1000),
                    measures=entry.song.measures,
                )
                signature = (
                    str(entry.path),
                    title_val,
                    parsed_key,
                    parsed_mode,
                    int(tempo_val),
                )
                if signature == st.session_state.get("_table_save_suppressed_signature"):
                    continue
                st.session_state._table_save_mode = "pending"
                st.session_state._table_save_pending = {
                    "path": entry.path,
                    "song": updated_song,
                    "existing_title": entry.title,
                    "signature": signature,
                    "changes": changed_fields,
                }
                _request_rerun(reset_song_table=True)

    # ── Confirmation / warning dialogs ──────────────────────────────────────
    if table_save_pending:
        _dialog_table_save()
    elif pending_switch is not None:
        _dialog_pending_switch()
    elif pending_deselect:
        _dialog_pending_deselect()
    elif del_path is not None:
        _dialog_delete_confirm()
    elif import_progress_pending:
        _dialog_import_progress()
    elif import_conflict_pending:
        _dialog_import_conflict()
    elif midi_update_pending:
        _render_midi_update_confirm()

    if show_import:
        _render_import_section(disabled=ui_locked)


def _render_import_section(disabled: bool = False) -> None:
    # ── Import ────────────────────────────────────────────────────────────────
    st.subheader(f"{_ICON_IMPORT} Import")
    uploaded = st.file_uploader(
        "Accepts: .zip (iReal-musicxml), .musicxml, .xml / .mid, .midi is for tempo metadata only",
        type=["zip", "musicxml", "xml", "mid", "midi"],
        accept_multiple_files=True,
        key=f"_sl_uploader_{st.session_state._import_uploader_reset_token}",
        disabled=disabled,
    )
    if uploaded and st.button("Import", type="primary", key="_sl_import_btn", disabled=disabled):
        st.session_state._import_progress_status = None
        st.session_state._import_progress_request = {
            "kind": "prepare",
            "files": [
                {"name": f.name, "data": f.getvalue()}
                for f in uploaded
            ],
        }
        _request_rerun()

    # Show last import result
    bundle_result = st.session_state.get("_import_bundle_result")
    result = st.session_state.get("_import_result")
    if result:
        lines = [f"**Import completed.**\n\nSuccess: {result['ok']}  Failed: {len(result['failed'])}"]
        if bundle_result is not None:
            sc = bundle_result.tempo_source_counts
            lines.append(
                f"\n**Tempo source:**\n"
                f"- MusicXML: {sc.get('musicxml', 0)}\n"
                f"- Style default: {sc.get('style_default', 0)}\n"
                f"- MIDI fallback: {sc.get('midi', 0)}\n"
                f"- Default: {sc.get('default', 0)}"
            )
            if bundle_result.warnings:
                lines.append("\n**Warnings:**\n" + "\n".join(
                    f"- {w.song_name}: {w.message}" for w in bundle_result.warnings[:20]
                ))
        if result["failed"]:
            lines.append("\n**Failed:**\n" + "\n".join(
                f"- {n}: {e}" for n, e in result["failed"]
            ))
        st.info("\n".join(lines))


def _try_select_song(entry: SongEntry) -> None:
    if st.session_state._editor_dirty:
        st.session_state._pending_switch = entry
    else:
        _do_switch_song(entry)


def _do_switch_song(entry: SongEntry) -> None:
    st.session_state._selected_path = entry.path
    st.session_state._pending_switch = None
    if entry.song:
        _load_song_into_editor(entry.song)


def _load_song_into_editor(song: SongModel) -> None:
    from changes.editor import EditorState
    state = EditorState()
    state.title = song.title
    state.tempo = int(song.performance_tempo)
    state.composer = getattr(song, "composer", None)
    if song.working_key:
        state.working_key = song.working_key
    if song.measures:
        m = song.measures[0]
        state.meter = f"{m.meter_numerator}/{m.meter_denominator}"

    # Rebuild cells from measures.
    # Section boundary: insert || instead of trailing |, record label for display.
    # This avoids the "| ||" double-separator that looks like an empty bar.
    section_labels: dict[int | str, str] = {}
    prev_section: str | None = None
    measures_list = list(song.measures)

    for m_idx, m in enumerate(measures_list):
        if m.section_id != prev_section:
            if prev_section is None:
                # First section: record initial label
                if m.section_id:
                    section_labels["initial"] = m.section_id
            else:
                # New section: record label position (before ||) then insert ||
                if m.section_id:
                    section_labels[len(state.cells)] = m.section_id
                state.insert("||")
            prev_section = m.section_id

        for h in m.harmony:
            state.insert(h.symbol)

        # Insert | only when the next measure is in the same section (or last measure).
        # When next measure starts a new section, skip the trailing | — the || will be
        # inserted on the next iteration, avoiding the "| ||" double-separator.
        next_m = measures_list[m_idx + 1] if m_idx + 1 < len(measures_list) else None
        if next_m is None or next_m.section_id == m.section_id:
            state.insert("|")

    st.session_state._editor_section_labels = section_labels
    st.session_state.editor = state
    st.session_state.editor_title = state.title
    st.session_state.editor_tempo = state.tempo
    st.session_state.working_key_input = state.working_key
    st.session_state._editor_working_key_mode = song.working_key_mode
    st.session_state._editor_dirty = False
    st.session_state._dirty_song_override = None
    st.session_state._dirty_song_override_cells = None


@st.dialog("MIDI Metadata Update", dismissible=False)
def _render_midi_update_confirm() -> None:
    """Show before/after tempo for matched MIDI files and let user confirm update."""
    candidates = st.session_state.get("_midi_update_candidates") or []
    kept = st.session_state.get("_midi_update_kept") or []
    unmatched = st.session_state.get("_midi_update_unmatched") or []

    matched_count = len(candidates) + len(kept)
    st.write(f"**Matched:** {matched_count}")
    st.write(f"**Tempo updates:** {len(candidates)}")
    st.write(f"**Kept existing tempo:** {len(kept)}")
    st.write(f"**Unmatched:** {len(unmatched)}")

    if candidates:
        st.write("\n**Tempo updates:**")
        for c in candidates:
            st.write(f"- **{c.matched_title}**: {c.old_tempo:.0f} -> {c.new_tempo:.0f}")

    if kept:
        st.write("\n**Kept existing tempo:**")
        for k in kept:
            if k.reason.startswith("MIDI 120 ignored"):
                st.write(f"- **{k.matched_title}**: kept {k.existing_tempo:.0f} (MIDI {k.midi_tempo:.0f} ignored)")
            else:
                st.write(f"- **{k.matched_title}**: kept {k.existing_tempo:.0f} ({k.reason})")

    if not candidates and not kept:
        st.warning("No matching songs found in library.")

    if unmatched:
        with st.expander(f"{len(unmatched)} unmatched / skipped"):
            for fname, reason in unmatched:
                st.write(f"- `{fname}`: {reason}")

    mu1, mu2 = st.columns(2, width="stretch", gap="small")
    if mu1.button("Apply all", type="primary", key="_midi_upd_ok", disabled=not candidates, use_container_width=True):
        _apply_midi_updates(candidates)
        updated = st.session_state.get("_midi_update_last_updated", 0)
        failed = st.session_state.get("_midi_update_last_failed", [])
        st.session_state._midi_update_candidates = None
        st.session_state._midi_update_kept = None
        st.session_state._midi_update_unmatched = None
        message = f"Updated {updated}, failed {len(failed)}." if failed else f"{updated} song(s) updated."
        _request_rerun(
            refresh_library=True,
            reset_song_table=True,
            success_message=message,
        )
    if mu2.button("Cancel", key="_midi_upd_cancel", use_container_width=True):
        st.session_state._midi_update_candidates = None
        st.session_state._midi_update_kept = None
        st.session_state._midi_update_unmatched = None
        _request_rerun(reset_song_table=True)


def _apply_midi_updates(candidates: list) -> None:
    import json
    from fractions import Fraction as _Frac
    from dataclasses import replace as _replace
    from changes.models.song_model import song_model_from_dict

    updated = 0
    failed = []
    for c in candidates:
        try:
            data = json.loads(c.matched_path.read_text(encoding="utf-8"))
            song = song_model_from_dict(data)
            song = _replace(song, performance_tempo=_Frac(c.new_tempo).limit_denominator(1000))
            overwrite_song(c.matched_path, song)
            updated += 1
        except Exception as exc:
            failed.append((c.matched_title, str(exc)))

    if failed:
        st.session_state._midi_update_last_failed = failed
    else:
        st.session_state._midi_update_last_failed = []
    st.session_state._midi_update_last_updated = updated


def _supports_progress_callback(func) -> bool:
    import inspect

    try:
        return "progress_callback" in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def _extract_zip_with_optional_progress(extract_zip_func, raw: bytes, progress_callback=None) -> dict[str, bytes]:
    if _supports_progress_callback(extract_zip_func):
        return extract_zip_func(raw, progress_callback=progress_callback)
    if progress_callback:
        progress_callback("zip_open", 0, 1, "Opening ZIP")
    files = extract_zip_func(raw)
    if progress_callback:
        progress_callback("zip_complete", 1, 1, f"Extracted {len(files)} file(s)")
    return files


def _import_files_with_optional_progress(import_files_func, file_data: dict[str, bytes], progress_callback=None):
    if _supports_progress_callback(import_files_func):
        return import_files_func(file_data, default_tempo=120, progress_callback=progress_callback)
    if progress_callback:
        progress_callback("songmodel_build", 0, max(len(file_data), 1), "Building SongModel candidates")
    result = import_files_func(file_data, default_tempo=120)
    if progress_callback:
        progress_callback("complete", 1, 1, f"Built {len(result.songs)} SongModel candidate(s)")
    return result


def _start_import(files: list, progress_callback=None) -> None:
    from changes.importers.import_bundle import (
        MIDI_EXTS,
        MUSICXML_EXTS,
        extract_zip,
        find_midi_update_candidates,
        import_files,
    )
    from changes.library import list_songs

    s = st.session_state._settings
    lib_path = Path(s.library_path)

    # Read all uploaded bytes; separate ZIPs from direct files
    file_data: dict[str, bytes] = {}
    upload_failed: list[tuple[str, str]] = []
    total_files = max(len(files), 1)
    for idx, f in enumerate(files, start=1):
        name = str(f["name"]) if isinstance(f, dict) else str(f.name)
        raw = f["data"] if isinstance(f, dict) else f.read()
        ext = Path(name).suffix.lower()
        if progress_callback:
            progress_callback("scan_files", idx, total_files, f"Received {name}")
        if ext == ".zip":
            try:
                file_data.update(_extract_zip_with_optional_progress(extract_zip, raw, progress_callback))
            except Exception as exc:
                st.warning(f"ZIP extraction failed for {name}: {exc}")
                upload_failed.append((name, str(exc)))
        else:
            file_data[name] = raw

    has_xml = any(Path(n).suffix.lower() in MUSICXML_EXTS for n in file_data)
    has_mid = any(Path(n).suffix.lower() in MIDI_EXTS for n in file_data)

    if not has_xml and not has_mid:
        if progress_callback:
            progress_callback("error", 1, 1, "No importable MusicXML or MIDI files found")
        failed = upload_failed or [("import", "No importable MusicXML or MIDI files found")]
        st.session_state._import_bundle_result = None
        st.session_state._import_pending = []
        st.session_state._import_pending_failed = failed
        st.session_state._import_result = {"ok": 0, "failed": failed}
        return

    if not has_xml and has_mid:
        # MIDI-only → metadata update flow
        mid_files = {n: d for n, d in file_data.items()
                     if Path(n).suffix.lower() in MIDI_EXTS}
        candidates, kept, unmatched = find_midi_update_candidates(mid_files, list_songs(lib_path))
        st.session_state._midi_update_candidates = candidates
        st.session_state._midi_update_kept = kept
        st.session_state._midi_update_unmatched = unmatched
        st.session_state._import_bundle_result = None
        return

    # MusicXML (± MIDI) import
    st.session_state._midi_update_candidates = None
    st.session_state._midi_update_kept = None
    st.session_state._midi_update_unmatched = None

    bundle_result = _import_files_with_optional_progress(import_files, file_data, progress_callback)
    st.session_state._import_bundle_result = bundle_result

    pending = [(c.source_name, c.song) for c in bundle_result.songs]
    existing_titles = {e.title.lower() for e in list_songs(lib_path)}

    st.session_state._import_pending = pending
    st.session_state._import_pending_failed = upload_failed + list(bundle_result.failed)

    conflict_titles = [
        song.title for _, song in pending if song.title.lower() in existing_titles
    ]
    if conflict_titles:
        st.session_state._import_conflict_mode = "pending"
        st.session_state._import_conflict_titles = conflict_titles
    else:
        _do_import("keep_both", progress_callback=progress_callback)
        _refresh_library()


def _do_import(mode: str, progress_callback=None) -> None:
    pending = st.session_state.get("_import_pending", [])
    failed = list(st.session_state.get("_import_pending_failed", []))
    s = st.session_state._settings
    lib_path = Path(s.library_path)

    ok = 0
    total = max(len(pending), 1)
    for idx, (filename, song) in enumerate(pending, start=1):
        try:
            if progress_callback:
                progress_callback("save", idx - 1, total, f"Saving {filename}")
            save_song(lib_path, song, mode=mode)
            ok += 1
            if progress_callback:
                progress_callback("save", idx, total, f"Saved {filename}")
        except Exception as exc:
            failed.append((filename, str(exc)))
            if progress_callback:
                progress_callback("save", idx, total, f"Failed {filename}")

    if progress_callback:
        progress_callback("complete", 1, 1, f"Saved {ok} song(s)")
    st.session_state._import_result = {"ok": ok, "failed": failed}


# ─────────────────────────────────────────────────────────────────────────────
# Page: Compose — save helpers
# ─────────────────────────────────────────────────────────────────────────────

def _execute_compose_save(mode: str) -> None:
    """Commit a pending Compose save with the chosen mode."""
    song: SongModel | None = st.session_state.get("_compose_save_pending")
    if song is None:
        return
    s = st.session_state._settings
    lib_path = Path(s.library_path)
    selected_path = st.session_state._selected_path

    if mode == "update":
        if selected_path is not None:
            # Editing an existing song: overwrite its file directly
            overwrite_song(selected_path, song)
            path = selected_path
        else:
            # New composition whose title matches an existing song: find and overwrite it
            path = save_song(lib_path, song, mode="overwrite")
    else:
        path = save_song(lib_path, song, mode="keep_both")

    st.session_state._selected_path = path
    st.session_state._editor_dirty = False
    _refresh_library()
    st.session_state._compose_save_last_saved_name = path.name


def _execute_table_save(mode: str) -> None:
    """Commit a pending Song Table metadata edit with the chosen mode."""
    pending = st.session_state.get("_table_save_pending")
    if pending is None:
        return

    path: Path = pending["path"]
    song: SongModel = pending["song"]
    s = st.session_state._settings
    lib_path = Path(s.library_path)

    if mode == "update":
        overwrite_song(path, song)
        saved_path = path
    else:
        saved_path = save_song(lib_path, song, mode="keep_both")

    st.session_state._selected_path = saved_path
    _refresh_library()
    _load_song_into_editor(song)
    st.session_state._table_save_last_saved_name = saved_path.name


# ─────────────────────────────────────────────────────────────────────────────
# Page: Compose
# ─────────────────────────────────────────────────────────────────────────────

def _render_compose() -> None:
    state: EditorState = st.session_state.editor
    s = st.session_state._settings
    lib_path = Path(s.library_path)

    # ── Cell display ───────────────────────────────────────────────────────────
    st.markdown(
        f"<div class='chord-cell-display'>{_chord_display_html(state, _current_song())}</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Page: Settings
# ─────────────────────────────────────────────────────────────────────────────

def _pattern_change_helpers():
    from importlib import reload

    from changes.exporters import digitone_events

    if not hasattr(digitone_events, "pattern_change_basis_payload"):
        digitone_events = reload(digitone_events)
    return digitone_events.pattern_change_basis_payload, digitone_events.pattern_change_value


def _build_dry_run_result(song: SongModel, effective_dry: SongModel, settings: AppSettings) -> dict:
    from changes.digitone.bundle_planner import compile_timeline_to_digitone_bundle_plan
    from changes.song_filter import extract_section_ids as _sec_ids
    from changes.ui_pipeline import compile_song_for_ui

    pattern_change_basis_payload, pattern_change_value = _pattern_change_helpers()
    compiled = compile_song_for_ui(effective_dry, settings)
    bp = compile_timeline_to_digitone_bundle_plan(
        compiled.song, compiled.timeline, compiled.target_profile
    )
    timing = bp.timing
    all_secs_orig = _sec_ids(song)
    all_secs_eff = _sec_ids(compiled.song)
    sel_secs = list(st.session_state.get("_section_filter_selected") or [])

    enabled_layers: list[str] = []
    if any(t is not None for t in settings.cloud_tracks[:6]):
        enabled_layers.append(f"Cloud ({sum(1 for t in settings.cloud_tracks[:6] if t is not None)}/6 voices)")
    if settings.bass_track is not None:
        enabled_layers.append(f"Bass → Track {settings.bass_track}")
    if settings.chord_track is not None:
        enabled_layers.append(f"Chord → Track {settings.chord_track}")
    disabled_layers = [lbl for lbl in ["Cloud", "Bass", "Chord"] if not any(lbl in x for x in enabled_layers)]

    per_pattern_validation = [
        {
            "name": p.pattern_name,
            "steps": p.total_steps,
            "section_id": p.section_id,
            "pattern_change": pattern_change_value(
                length=p.total_steps,
                speed_ratio=timing.speed_ratio,
                policy=settings.pattern_change_policy,
            ),
            "events": len(p.events),
            "events_note": "diagnostic only; Digitone II is not limited to 128 note events per pattern",
        }
        for p in bp.patterns
    ]
    first_pattern = bp.patterns[0] if bp.patterns else None
    pattern_change = (
        pattern_change_value(
            length=first_pattern.total_steps,
            speed_ratio=timing.speed_ratio,
            policy=settings.pattern_change_policy,
        )
        if first_pattern is not None
        else None
    )
    pattern_change_basis = (
        pattern_change_basis_payload(length=first_pattern.total_steps, speed=timing.speed)
        if first_pattern is not None
        else None
    )

    from collections import defaultdict

    rp = compiled.render_profile
    tl_events = list(compiled.timeline.events)

    def _q(v):
        """FractionをJSONで見やすい文字列にする"""
        return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"

    def _event_detail(e) -> dict:
        return {
            "id": e.id,
            "onset_quarters": _q(e.onset_quarters),
            "duration_quarters": _q(e.duration_quarters),
            "role": e.role,
            "voice_id": e.voice_id,
            "note_midi": e.note_midi,
            "velocity": e.velocity,
            "source_harmony_id": e.source_harmony_id,
            "retrigger": e.retrigger,
        }

    def _layer_stats(role: str) -> dict:
        evs = [e for e in tl_events if e.role == role]
        notes = [e.note_midi for e in evs]

        by_onset = defaultdict(list)
        for e in evs:
            by_onset[e.onset_quarters].append(e)

        onset_groups = []
        for onset, onset_evs in sorted(by_onset.items(), key=lambda x: x[0]):
            onset_notes = [e.note_midi for e in onset_evs]
            onset_groups.append({
                "onset_quarters": _q(onset),
                "count": len(onset_evs),
                "notes": sorted(onset_notes),
                "note_min": min(onset_notes),
                "note_max": max(onset_notes),
                "spread": max(onset_notes) - min(onset_notes),
                "details": [
                    _event_detail(e)
                    for e in sorted(
                        onset_evs,
                        key=lambda x: (
                            x.voice_id,
                            x.note_midi,
                        ),
                    )
                ],
            })

        return {
            "count": len(evs),
            "note_min": min(notes) if notes else None,
            "note_max": max(notes) if notes else None,
            "unique_onsets": len(by_onset),
            "events": {
                "details": [
                    _event_detail(e)
                    for e in sorted(
                        evs,
                        key=lambda x: (
                            x.onset_quarters,
                            x.voice_id,
                            x.note_midi,
                        ),
                    )
                ]
            },
            "by_onset": onset_groups,
        }

    cloud_evs = [e for e in tl_events if e.role == "cloud"]

    cloud_out_of_range = [
        _event_detail(e)
        for e in cloud_evs
        if not (rp.cloud_min_midi <= e.note_midi <= rp.cloud_max_midi)
    ]

    cloud_groups = _layer_stats("cloud")["by_onset"]
    cloud_centers_by_onset = [
        {
            "onset_quarters": group["onset_quarters"],
            "average": sum(group["notes"]) / len(group["notes"]),
            "note_min": group["note_min"],
            "note_max": group["note_max"],
            "spread": group["spread"],
        }
        for group in cloud_groups
    ]

    cloud_repaired_voicings = []
    for idx, occ in enumerate(compiled.arrangement.occurrences):
        if occ.cloud is None:
            continue
        notes = sorted(int(n.note_midi) for n in occ.cloud.notes)
        if not notes:
            continue
        avg = sum(notes) / len(notes)
        spread = max(notes) - min(notes)
        avg_ok = abs(avg - rp.cloud_center_midi) <= rp.cloud_average_tolerance
        spread_ok = rp.cloud_spread_min <= spread <= rp.cloud_spread_max
        cloud_repaired_voicings.append({
            "index": idx + 1,
            "symbol": occ.symbol,
            "onset_quarters": _q(occ.onset_quarters),
            "notes": notes,
            "average": round(avg, 2),
            "spread": spread,
            "average_ok": avg_ok,
            "spread_ok": spread_ok,
        })

    _crv_total = len(cloud_repaired_voicings)
    _crv_avg_ok = sum(1 for v in cloud_repaired_voicings if v["average_ok"])
    _crv_spread_ok = sum(1 for v in cloud_repaired_voicings if v["spread_ok"])
    _crv_both_ok = sum(1 for v in cloud_repaired_voicings if v["average_ok"] and v["spread_ok"])

    return {
        "song": {
            "original_title": song.title,
            "original_measures": len(song.measures),
            "effective_title": effective_dry.title,
            "effective_measures": len(effective_dry.measures),
            "selected_sections": sel_secs,
            "section_filter_active": effective_dry is not song,
        },
        "song_meta": {
            "key_mode": f"{compiled.song.working_key} {compiled.song.working_key_mode or ''}".strip(),
            "tempo": float(compiled.song.performance_tempo),
            "meter": (f"{compiled.song.measures[0].meter_numerator}/{compiled.song.measures[0].meter_denominator}"
                      if compiled.song.measures else "?"),
            "cloud_voice_leading_seed": compiled.song.cloud_voice_leading_seed,
        },
        "sections": {
            "all_section_ids_original": all_secs_orig,
            "all_section_ids_effective": all_secs_eff,
            "fallback_ALL_used": all_secs_orig == ["ALL"],
        },
        "render_settings": {
            "cloud_tracks": list(settings.cloud_tracks[:6]),
            "bass_track": settings.bass_track,
            "chord_track": settings.chord_track,
            "cloud_trigger": settings.cloud_trigger_policy,
            "bass_trigger": settings.bass_trigger_policy,
            "chord_trigger": settings.chord_trigger_policy,
            "cloud_center_midi": settings.cloud_center_midi,
            "bass_center_midi": settings.bass_center_midi,
            "chord_center_midi": settings.chord_center_midi,
        },
        "pattern_change_policy": settings.pattern_change_policy,
        "pattern_change": pattern_change,
        "pattern_change_basis": pattern_change_basis,
        "output": {
            "enabled_layers": enabled_layers,
            "disabled_layers": disabled_layers,
            "total_timeline_events": len(compiled.timeline.events),
            "total_compiled_events": sum(len(p.events) for p in bp.patterns),
            "total_events_note": "diagnostic only; Digitone II is not limited to 128 note events per pattern",
        },
        "timing": {
            "performance_tempo": float(compiled.timeline.performance_tempo),
            "device_tempo": float(timing.device_tempo),
            "speed": timing.speed,
            "q_step": str(timing.q_step),
        },
        "bundle": {
            "pattern_count": len(bp.patterns),
            "patterns": per_pattern_validation,
            "warnings": list(bp.warnings),
        },
        "render_profile": {
            "cloud_center_midi": rp.cloud_center_midi,
            "cloud_spread_min": rp.cloud_spread_min,
            "cloud_spread_max": rp.cloud_spread_max,
            "cloud_average_tolerance": rp.cloud_average_tolerance,
            "chord_min_midi": rp.chord_min_midi,
            "chord_max_midi": rp.chord_max_midi,
            "bass_min_midi": rp.bass_min_midi,
            "bass_max_midi": rp.bass_max_midi,
        },
        "cloud_voicing_control": {
            "center_midi": rp.cloud_center_midi,
            "spread_min": rp.cloud_spread_min,
            "spread_max": rp.cloud_spread_max,
            "average_tolerance": rp.cloud_average_tolerance,
        },
        "timeline": {
            "total_events": len(tl_events),
            "roles": {
                "cloud": _layer_stats("cloud"),
                "bass": _layer_stats("bass"),
                "chord": _layer_stats("chord"),
            },
        },
        "cloud_legacy_range_reference": {
            "note": "legacy compat field; cloud voice leading uses center/spread, not this range",
            "range": [rp.cloud_min_midi, rp.cloud_max_midi],
            "out_of_range_count": len(cloud_out_of_range),
            "out_of_range": cloud_out_of_range,
        },
        "cloud_repaired_voicings": {
            "note": "repaired voicings from render_arrangement(); not affected by hold_until_change",
            "total": _crv_total,
            "average_ok_count": _crv_avg_ok,
            "spread_ok_count": _crv_spread_ok,
            "both_ok_count": _crv_both_ok,
            "voicings": cloud_repaired_voicings,
        },
        "cloud_voice_leading": {
            "note": "timeline-event based; may undercount due to hold_until_change — use cloud_repaired_voicings for accuracy",
            "centers_by_onset": cloud_centers_by_onset,
            "average_min": min((g["average"] for g in cloud_centers_by_onset), default=None),
            "average_max": max((g["average"] for g in cloud_centers_by_onset), default=None),
        },
    }


def _render_settings() -> None:
    st.subheader(
        f"{_ICON_LAYER_OPTIONS} Layer Options",
        help=(
            "Choose how the song is rendered into Digitone layers. "
            "Cloud spreads harmony across up to six voices, Bass creates a low single-note layer, "
            "and Chord sends the full chord to one track. "
            "Use these options to set retrigger behavior, pitch ranges, and which Digitone tracks receive each layer."
        ),
    )
    settings: AppSettings = st.session_state._settings
    changed = False
    library_path_changed = False

    def _toggle(label: str, key: str, value: bool, help: str | None = None) -> bool:
        value = bool(value)
        synced_key = f"{key}__settings_value"
        previous_value = st.session_state.get(synced_key)
        if key not in st.session_state:
            st.session_state[key] = value
        elif previous_value is not None and previous_value != value and st.session_state[key] == previous_value:
            st.session_state[key] = value
        st.session_state[synced_key] = value
        return st.toggle(label, value=value, key=key, help=help)

    # ── Cloud ─────────────────────────────────────────────────────────────────
    c0, c1, c2 = st.columns([1, 3, 3], vertical_alignment="bottom")
    with c0:
        st.image(_ICON_PATH, width=60)
    with c1:
        new_cloud_trigger = "retrigger" if _toggle(
            "Retrigger", "_s_cloud_trig",
            settings.cloud_trigger_policy == "retrigger"
        ) else "hold_until_change"
        if new_cloud_trigger != settings.cloud_trigger_policy:
            settings.cloud_trigger_policy = new_cloud_trigger; changed = True
    with c2:
        cloud_notes = _note_options(36, 84)
        ci = _note_options_index(cloud_notes, settings.cloud_center_midi)
        new_cloud_note = st.selectbox(
            "Center note",
            cloud_notes,
            index=ci,
            key="_s_cloud_center",
            format_func=lambda n: _midi_display_name(_name_to_midi(n)),
        )
        new_cloud_midi = _name_to_midi(new_cloud_note)
        if new_cloud_midi != settings.cloud_center_midi:
            settings.cloud_center_midi = new_cloud_midi; changed = True

    # Per-voice track assignment (None = don't send)
    _TRACK_OPTS = ["None"] + [f"Tr.{i}" for i in range(1, 9)]
    cloud_cols = st.columns([1,1,1,1,1,1,1])
    cloud_cols[0].write(" ")
    new_cloud_tracks = list(settings.cloud_tracks[:6])
    while len(new_cloud_tracks) < 6:
        new_cloud_tracks.append(None)
    for vi in range(6):
        cur = new_cloud_tracks[vi]
        cur_val = "None" if cur is None else f"Tr.{cur}"
        idx = _TRACK_OPTS.index(cur_val) if cur_val in _TRACK_OPTS else 0
        sel = cloud_cols[vi + 1].selectbox(
            f"Voice{vi + 1} to", _TRACK_OPTS, index=idx, key=f"_s_cloud_t{vi + 1}",
            label_visibility="visible",
        )
        if sel == "None":
            new_cloud_tracks[vi] = None
        else:
            new_cloud_tracks[vi] = int(sel.removeprefix("Tr."))
    if new_cloud_tracks != list(settings.cloud_tracks[:6]):
        settings.cloud_tracks = new_cloud_tracks; changed = True

    st.space("small")

    # ── Bass ──────────────────────────────────────────────────────────────────
    
    b0, b1, b2, b3 = st.columns([1, 2, 2, 2], vertical_alignment="bottom")
    with b0:
        st.image(_ICON_PATH_BASS, width=60)
    with b1:
        new_bass_trigger = "retrigger" if _toggle(
            "Retrigger", "_s_bass_trig",
            settings.bass_trigger_policy == "retrigger"
        ) else "hold_until_change"
        if new_bass_trigger != settings.bass_trigger_policy:
            settings.bass_trigger_policy = new_bass_trigger; changed = True
    with b2:
        bass_notes = _note_options(12, 60)
        bi = _note_options_index(bass_notes, settings.bass_center_midi)
        new_bass_note = st.selectbox(
            "Center note(Range)",
            bass_notes,
            index=bi,
            key="_s_bass_center",
            format_func=lambda n: _range_display(_name_to_midi(n), 0, 11),
        )
        new_bass_midi = _name_to_midi(new_bass_note)
        if new_bass_midi != settings.bass_center_midi:
            settings.bass_center_midi = new_bass_midi; changed = True
    with b3:
        cur_bass = settings.bass_track
        bass_val = "None" if cur_bass is None else f"Tr.{cur_bass}"
        bass_idx = _TRACK_OPTS.index(bass_val) if bass_val in _TRACK_OPTS else 0
        new_bass_sel = st.selectbox("Voice to", _TRACK_OPTS, index=bass_idx, key="_s_bass_track")
        if new_bass_sel == "None":
            new_bass_track: int | None = None 
        else:
            new_bass_track = int(new_bass_sel.removeprefix("Tr."))
        if new_bass_track != settings.bass_track:
            settings.bass_track = new_bass_track; changed = True
    bass_annotation = st.columns([1, 6])
    bass_annotation[0].write(" ")
    bass_annotation[1].caption("Bass Repeat Variation: planned")
    st.space("small")

    # ── Chord ─────────────────────────────────────────────────────────────────
    ch0, ch1, ch2, ch3 = st.columns([1, 2, 2, 2], vertical_alignment="bottom")

    with ch0:
        st.image(_ICON_PATH_CHORD, width=60)

    with ch1:
        new_chord_trigger = "retrigger" if _toggle(
            "Retrigger", "_s_chord_trig",
            settings.chord_trigger_policy == "retrigger",
        ) else "hold_until_change"
        if new_chord_trigger != settings.chord_trigger_policy:
            settings.chord_trigger_policy = new_chord_trigger; changed = True

    with ch2:
        chord_notes = _note_options(36, 84)
        chi = _note_options_index(chord_notes, settings.chord_center_midi)
        new_chord_note = st.selectbox(
            "Center note(Range)",
            chord_notes,
            index=chi,
            key="_s_chord_center",
            format_func=lambda n: _range_display(_name_to_midi(n), 12, 12),
        )
        new_chord_midi = _name_to_midi(new_chord_note)
        if new_chord_midi != settings.chord_center_midi:
            settings.chord_center_midi = new_chord_midi; changed = True

    with ch3:
        cur_chord = settings.chord_track
        chord_track_val = "None" if cur_chord is None else f"Tr.{cur_chord}"
        chord_track_index = _TRACK_OPTS.index(chord_track_val) if chord_track_val in _TRACK_OPTS else 0
        new_chord_sel = st.selectbox(
            "Voices to",
            _TRACK_OPTS,
            index=chord_track_index,
            key="_s_chord_track",
        )
        if new_chord_sel == "None":
            new_chord_track: int | None = None
        else:
            new_chord_track = int(new_chord_sel.removeprefix("Tr."))
        if new_chord_track != settings.chord_track:
            settings.chord_track = new_chord_track; changed = True

    st.divider()

    # ── Settings ───────────────────────────────────────────────────────────────
    st.subheader(f"{_ICON_SETTINGS} Settings")
    current_pattern_policy = getattr(settings, "pattern_change_policy", "auto_song_mode")
    pattern_policy_bool = False if current_pattern_policy == "off" else True
    _CHANGE_SETTING_IMAGE = Path("docs/assets/CHANGE_setting.png")
    change_img_col, change_toggle_col, accidentals_toggle_col, hardware_write_confirm_toggle_col = st.columns(4, vertical_alignment="center")
    with change_img_col:
        if _CHANGE_SETTING_IMAGE.exists():
            st.image(
                _CHANGE_SETTING_IMAGE,
                use_container_width=True,
            )
        else:
            st.caption("CHANGE setting image not found.")
    with change_toggle_col:
        new_pattern_policy_enabled = _toggle(
            "Auto Change",
            "_s_pattern_change_enabled",
            pattern_policy_bool,
            help=(
                "Auto for Song Mode sets PATTERN CHANGE from the generated Track 1-8 length/speed "
                "so queued Song mode patterns advance at the end of each generated section. "
                "OFF keeps the previous behavior."
            ),
        )
        new_pattern_policy = "auto_song_mode" if new_pattern_policy_enabled else "off"
        if new_pattern_policy != current_pattern_policy:
            settings.pattern_change_policy = new_pattern_policy
            changed = True
    with accidentals_toggle_col:
        current_accidental = getattr(settings, "note_accidental", "flat")
        new_accidental = "flat" if _toggle(
            "Flat Accidentals",
            "_s_flat_accidentals",
            current_accidental == "flat",
        ) else "sharp"
        if new_accidental != current_accidental:
            settings.note_accidental = new_accidental; changed = True
    with hardware_write_confirm_toggle_col:
        new_confirm = _toggle("Confirm before hardware write", "_s_confirm_hw_enabled",
                            settings.confirm_before_hardware_write)
        if new_confirm != settings.confirm_before_hardware_write:
            settings.confirm_before_hardware_write = new_confirm; changed = True

    # ── Library path ──────────────────────────────────────────────────────────
    lib_col, browse_col = st.columns([4, 1], vertical_alignment="bottom")
    with lib_col:
        new_lib_path = st.text_input("Library folder", value=settings.library_path, key="_s_lib_path", icon=":material/folder:")
        if new_lib_path != settings.library_path:
            settings.library_path = new_lib_path; changed = True
            library_path_changed = True
    with browse_col:
        st.write("")
        if st.button("Browse…", key="_s_lib_browse", use_container_width=True):
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes("-topmost", 1)
                folder = filedialog.askdirectory(
                    title="Select Library Folder",
                    initialdir=settings.library_path,
                )
                root.destroy()
                if folder:
                    settings.library_path = folder
                    changed = True
                    save_settings(settings)
                    st.session_state._settings = settings
                    _request_rerun(
                        reason="visible_settings_changed",
                        refresh_library=True,
                        reset_song_table=True,
                    )
            except Exception:
                st.info("Please enter the folder path manually")

    if changed:
        save_settings(settings)
        st.session_state._settings = settings
        _request_rerun(
            reason="visible_settings_changed",
            refresh_library=library_path_changed,
            reset_song_table=library_path_changed,
        )

    # ── Advanced ──────────────────────────────────────────────────────────────
    st.divider()
    st.subheader(f"{_ICON_ADVANCED} Advanced")
    song = _current_song()

    # Compute disabled state for Advanced actions using the same conditions as
    # Preview / Send (no layers, no sections selected, no song loaded).
    _adv_selected_sections: set[str] = set()
    _adv_song_has_real = False
    if song:
        _adv_selected_sections = set(st.session_state.get("_section_filter_selected") or [])
        from changes.song_filter import FALLBACK_ALL_SECTION
        _adv_all_sec = extract_section_ids(song)
        _adv_song_has_real = _adv_all_sec != [FALLBACK_ALL_SECTION]
    _adv_disable_reason = _action_disabled_reason(
        has_selected_song=song is not None,
        settings=settings,
        selected_sections=_adv_selected_sections,
        song_has_sections=_adv_song_has_real,
    )
    adv_actions_disabled = song is None or _adv_disable_reason is not None

    if song:
        adv1, adv2 = st.columns(2)
        with adv1:
            if st.button("Export SYX", type="primary", use_container_width=True,
                         key="_adv_syx_btn", disabled=adv_actions_disabled):
                # Clear previous state before new action
                st.session_state._adv_syx_ok = False
                st.session_state._adv_syx_bytes = None
                st.session_state._adv_syx_fname = None
                st.session_state._adv_syx_error = None
                with st.spinner("Generating SYX..."):
                    try:
                        effective_adv = _filtered_song_for_send(song)
                        if not effective_adv.measures:
                            raise ValueError("No measures selected. Select at least one section.")
                        syx = song_to_syx_bytes(effective_adv, settings)
                        st.session_state._adv_syx_ok = True
                        st.session_state._adv_syx_bytes = syx
                        st.session_state._adv_syx_fname = f"{song.title or 'changes'}.syx"
                    except ModuleNotFoundError:
                        st.session_state._adv_syx_error = "digitone-syx-toolkit is required: `pip install -e ../digitone-syx-toolkit`"
                    except Exception as exc:
                        import traceback as _tb_exp
                        st.session_state._adv_syx_error = f"{type(exc).__name__}: {exc}\n\n{_tb_exp.format_exc()}"
                _no_explicit_rerun("advanced_export_result_rendered_in_current_run")
            if st.session_state.get("_adv_syx_ok") and st.session_state.get("_adv_syx_bytes"):
                syx_b = st.session_state._adv_syx_bytes
                st.success(f"Export done — {len(syx_b):,} bytes")
                st.download_button(
                    "↓ Download .syx",
                    data=syx_b,
                    file_name=st.session_state.get("_adv_syx_fname", "changes.syx"),
                    mime="application/octet-stream",
                    use_container_width=True,
                    key="_adv_syx_dl",
                )
            elif st.session_state.get("_adv_syx_error"):
                st.error(st.session_state._adv_syx_error)
            if _adv_disable_reason and song:
                st.caption(f"⚠ {_adv_disable_reason}")
        with adv2:
            if st.button("Dry-run", use_container_width=True, key="_adv_dry",
                         disabled=adv_actions_disabled):
                st.session_state._dry_run_result = None
                st.session_state._dry_run_error = None
                with st.spinner("Analyzing..."):
                    try:
                        import traceback as _tb
                        effective_dry = _filtered_song_for_send(song)
                        if not effective_dry.measures:
                            raise ValueError("No measures selected. Select at least one section.")
                        st.session_state._dry_run_result = _build_dry_run_result(song, effective_dry, settings)
                    except Exception as exc:
                        st.session_state._dry_run_error = {
                            "summary": str(exc),
                            "type": type(exc).__name__,
                            "traceback": _tb.format_exc(),
                        }
                _no_explicit_rerun("advanced_dry_run_result_rendered_in_current_run")
        if st.session_state.get("_dry_run_result"):
            st.json(st.session_state._dry_run_result)
        elif st.session_state.get("_dry_run_error"):
            err = st.session_state._dry_run_error
            st.error(f"{err['type']}: {err['summary']}")
            with st.expander("Traceback"):
                st.code(err["traceback"], language="text")
    else:
        st.caption("No song loaded. Select or compose a song first.")


# ─────────────────────────────────────────────────────────────────────────────
# Preview / Send area
# ─────────────────────────────────────────────────────────────────────────────

def _render_main() -> None:
    _render_compose()
    _render_songlist(show_import=False)


def _has_any_layer(settings: AppSettings) -> bool:
    """Return True when at least one Cloud/Bass/Chord output track is configured."""
    has_cloud = any(t is not None for t in settings.cloud_tracks[:6])
    has_bass = settings.bass_track is not None
    has_chord = settings.chord_track is not None
    return has_cloud or has_bass or has_chord


def _action_disabled_reason(
    *,
    has_selected_song: bool,
    settings: AppSettings,
    selected_sections: set[str],
    song_has_sections: bool,
) -> str | None:
    """Return a short human-readable reason if actions should be disabled, else None."""
    if not has_selected_song:
        return None
    if not _has_any_layer(settings):
        return "Enable at least one layer: Cloud, Bass, or Chord."
    if song_has_sections and not selected_sections:
        return "Select at least one section to preview or export."
    return None


def _render_status_slot(statuses: list[tuple[str, str | None]]) -> None:
    visible_statuses = [(kind, message) for kind, message in statuses if message]

    items: list[str] = []
    for kind, message in visible_statuses:
        normalized_kind = kind if kind in {"info", "warning", "error", "success"} else "info"
        safe_message = html.escape(str(message))
        items.append(
            f'<div class="eub-status-line eub-status-line-{normalized_kind}">{safe_message}</div>'
        )
    st.markdown("Status: none" if not items else
        f'<div class="eub-status-slot">{"".join(items)}</div>',
        unsafe_allow_html=True,
    )


def _hardware_write_warning(settings: AppSettings) -> str | None:
    if settings.confirm_before_hardware_write:
        return None
    return "Hardware write confirmation is disabled. SysEx will be sent immediately."


def _section_filter_signature(song: SongModel, song_path) -> tuple:
    return (str(song_path), len(song.measures), tuple(extract_section_ids(song)))


def _get_or_init_section_filter(song: SongModel, song_path) -> set[str]:
    """Return current section selection with the following policy:

    - Path changed (new song): reset to all sections.
    - Same path, signature changed:
        - Valid subset: preserve selection.
        - Stale non-empty: reset to all sections.
        - Empty: preserve as user intent (all-unchecked state).
    """
    sections = set(extract_section_ids(song))
    signature = _section_filter_signature(song, song_path)
    cached_signature = st.session_state.get("_section_filter_signature")
    cached_path = st.session_state.get("_section_filter_song_path")
    selected: set[str] = set(st.session_state.get("_section_filter_selected") or [])

    path_str = str(song_path)
    path_changed = cached_path != path_str
    signature_changed = cached_signature != signature

    if path_changed:
        selected = sections
    elif signature_changed:
        if selected and selected.issubset(sections):
            pass  # valid subset: keep
        elif selected:
            selected = sections  # stale non-empty: reset to all
        # else: empty is preserved as user intent

    st.session_state._section_filter_signature = signature
    st.session_state._section_filter_song_path = path_str
    st.session_state._section_filter_selected = selected
    return selected


def _filtered_song_for_send(song: SongModel) -> SongModel:
    """Apply section filter from session state to a song before sending.

    Empty selection is NOT treated as all-selected; it returns a song with 0 measures.
    Callers must check len(result.measures) > 0 before passing to the planner.
    The Preview/Send buttons are already disabled by _action_disabled_reason when empty.
    """
    song_path = st.session_state.get("_selected_path")
    selected = _get_or_init_section_filter(song, song_path)
    if not selected:
        return _replace(song, measures=())
    all_sections = set(extract_section_ids(song))
    if selected != all_sections:
        return filter_song_by_sections(song, selected)
    return song


def _render_section_filter(song: SongModel) -> None:
    """Render section selection checkboxes if the song has multiple sections."""
    sections = extract_section_ids(song)
    if len(sections) < 2:
        return

    song_path = st.session_state.get("_selected_path")
    selected = _get_or_init_section_filter(song, song_path)

    st.caption("Sections to send:")
    new_selected: set[str] = set()

    cols = st.columns(min(len(sections), 8))
    for i, sec_id in enumerate(sections):
        if cols[i % len(cols)].checkbox(_display_section_label(sec_id), value=sec_id in selected, key=f"_sf_{sec_id}"):
            new_selected.add(sec_id)

    st.session_state._section_filter_selected = new_selected


def _render_preview_send() -> None:
    _sync_preview_state()
    song = _current_song()
    has_selected_song = st.session_state.get("_selected_path") is not None
    settings: AppSettings = st.session_state._settings

    mode, section = st.columns([1,2], border=False, gap="medium", vertical_alignment="bottom")
    # ── Send mode ──────────────────────────────────────────────────────────────
    with mode:
        st.session_state["_send_mode"] = _normalize_send_mode(st.session_state.get("_send_mode"))
        send_mode = st.radio(
            "Send mode",
            _SEND_MODE_OPTIONS,
            key="_send_mode",
            format_func=_send_mode_label,
            help=(
                "Linear treats the song as one continuous performance and auto-splits only when needed. "
                "Best for quick live use with fewer pattern changes.\n\n"
                "Bundle by Section exports each song section as a separate pattern. "
                "Useful for structured Song Mode setup, but it may create more patterns."
            ),
            horizontal=True,
        )

    # ── Section filter ─────────────────────────────────────────────────────────
    with section:
        if song:
            _render_section_filter(song)

    # ── Compute disable conditions ─────────────────────────────────────────────
    song_path = st.session_state.get("_selected_path")
    selected_sections: set[str] = set()
    song_has_real_sections = False
    if song:
        selected_sections = _get_or_init_section_filter(song, song_path)
        all_sec_ids = extract_section_ids(song)
        from changes.song_filter import FALLBACK_ALL_SECTION
        song_has_real_sections = all_sec_ids != [FALLBACK_ALL_SECTION]

    disable_reason = _action_disabled_reason(
        has_selected_song=has_selected_song,
        settings=settings,
        selected_sections=selected_sections,
        song_has_sections=song_has_real_sections,
    )
    actions_disabled = not has_selected_song or disable_reason is not None
    action_status_message: str | None = None
    action_status_kind = "info"

    # Auto split info / warnings
    if song:
        effective_song = _filtered_song_for_send(song)
        try:
            if not _is_bundle_send_mode(send_mode):
                n_pat = count_linear_patterns(effective_song, settings)
                if n_pat > 1:
                    action_status_message = f"Auto Split -> {n_pat} patterns"
                    action_status_kind = "warning"
                else:
                    sections = extract_section_ids(effective_song)
                    n_sec = len(sections) if sections != ["ALL"] else 0
                    action_status_message = f"Linear: {len(effective_song.measures)} measures" + (f" / {n_sec} section(s)" if n_sec else "")
            else:
                sections = extract_section_ids(effective_song)
                autosplit_warnings = []
                n_patterns_total = 0
                for sec_id in sections:
                    sec_song = filter_song_by_sections(effective_song, {sec_id})
                    try:
                        n = count_auto_split_patterns(sec_song, settings)
                        n_patterns_total += max(1, n)
                        if n > 1:
                            autosplit_warnings.append(f"{_display_section_label(sec_id)} Auto Split -> {n} patterns")
                    except Exception:
                        n_patterns_total += 1
                if not n_patterns_total:
                    n_patterns_total = 1
                label = (
                    "ALL (no sections)"
                    if sections == ["ALL"]
                    else f"{len(sections)} section(s) / {n_patterns_total} pattern(s)"
                )
                if autosplit_warnings:
                    action_status_message = ", ".join(autosplit_warnings)
                    action_status_kind = "warning"
                else:
                    action_status_message = f"Bundle by Section: {label}"
        except Exception:
            pass

    # Destination
    ports = ["(Select MIDI Port Destination)", "DEBUG"]
    ps0, ps1, ps2 = st.columns(3)

    preview_running = _preview_is_running()

    # Preview (Realtime MIDI)
    with ps0:
        try:
            import mido
            ports += mido.get_output_names()
        except Exception:
            pass
        dest = st.selectbox("Destination", ports, key="_dest_sel", label_visibility="collapsed")
    with ps1:
        preview_btn_disabled = actions_disabled or preview_running
        if st.button("▶  Preview (Realtime MIDI)", use_container_width=True, key="_ps_preview", disabled=preview_btn_disabled):
            if not song:
                st.warning("No song loaded")
            else:
                _start_preview(_filtered_song_for_send(song), settings, dest)
                st.rerun()

    # Send SysEx
    with ps2:
        send_btn_disabled = actions_disabled or preview_running
        if st.button("⬆  Send SysEx (Digitone)", type="primary", use_container_width=True, key="_ps_send", disabled=send_btn_disabled):
            if not song:
                st.warning("No song loaded")
            elif settings.confirm_before_hardware_write:
                st.session_state._send_confirm = True
                st.session_state._send_confirm_mode = send_mode
                _request_rerun()
            else:
                effective = _filtered_song_for_send(song)
                _run_send(effective, settings, dest, send_mode)
                _no_explicit_rerun("send_result_rendered_in_current_run")

    # Preview dialog — shown whenever preview state is not idle
    if st.session_state.get("_preview_state", "idle") != "idle":
        _dialog_preview()

    # Hardware write confirmation
    if st.session_state.get("_send_confirm"):
        effective = _filtered_song_for_send(song) if song else song
        confirm_mode = st.session_state.get("_send_confirm_mode", send_mode)
        _show_send_confirm_dialog(effective, settings, dest, confirm_mode)

    # Persistent send results
    send_success_message: str | None = None
    send_error = st.session_state.get("_send_area_error")
    send_error_message = send_error.get("summary", "Send failed") if send_error else None
    if st.session_state.get("_send_area_ok"):
        detail = st.session_state.get("_send_area_ok_detail") or {}
        dest_label = detail.get("dest", "?")
        mode_label = detail.get("mode", "?")
        pat_names = detail.get("pattern_names", [])
        pat_count = detail.get("patterns", len(pat_names))
        pat_info = f"\nPatterns: {pat_count}" + (
            (" (" + ", ".join(pat_names[:6]) + ("..." if len(pat_names) > 6 else "") + ")")
            if pat_names else ""
        )
        send_success_message = f"Send completed.\nDestination: {dest_label}\nMode: {mode_label}{pat_info}"

    _render_status_slot([
        (action_status_kind, action_status_message),
        ("warning", disable_reason),
        ("warning", _hardware_write_warning(settings)),
        ("success", send_success_message),
        ("error", send_error_message),
    ])

    if send_error:
        with st.expander("Error details"):
            ctx = send_error.get("context", {})
            if ctx:
                st.json(ctx)
            tb = send_error.get("traceback")
            if tb:
                st.code(tb, language="text")

    st.markdown("</div>", unsafe_allow_html=True)


def _clear_send_area_state() -> None:
    for k in ("_send_area_ok", "_send_area_ok_detail", "_send_area_error"):
        st.session_state[k] = None if k != "_send_area_ok" else False


def _store_send_error(
    exc: Exception,
    *,
    action: str,
    song: SongModel,
    dest: str,
    send_mode: str,
    settings: AppSettings,
) -> None:
    import traceback as _tb
    selected_sections = list(st.session_state.get("_section_filter_selected") or [])
    enabled_layers: list[str] = []
    if any(t is not None for t in settings.cloud_tracks[:6]):
        enabled_layers.append("Cloud")
    if settings.bass_track is not None:
        enabled_layers.append("Bass")
    if settings.chord_track is not None:
        enabled_layers.append("Chord")
    st.session_state._send_area_error = {
        "summary": str(exc),
        "context": {
            "action": action,
            "song": song.title,
            "send_mode": send_mode,
            "destination": dest,
            "selected_sections": selected_sections,
            "enabled_layers": enabled_layers,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        },
        "traceback": _tb.format_exc(),
    }


def _port_name(dest: str) -> str:
    return "DEBUG" if "DEBUG" in dest else dest


def _normalize_send_mode(send_mode: str | None) -> str:
    if send_mode and send_mode.endswith(_SEND_MODE_BUNDLE):
        return _SEND_MODE_BUNDLE
    return _SEND_MODE_LINEAR


def _send_mode_label(send_mode: str) -> str:
    if send_mode == _SEND_MODE_BUNDLE:
        return f"{_ICON_BUNDLE} {_SEND_MODE_BUNDLE}"
    return f"{_ICON_LINEAR} {_SEND_MODE_LINEAR}"


def _is_bundle_send_mode(send_mode: str) -> bool:
    return _normalize_send_mode(send_mode) == _SEND_MODE_BUNDLE


def _finish_send_segments(
    song: SongModel,
    dest: str,
    send_mode: str,
    segments: list[tuple[str, bytes]],
    *,
    empty_summary: str,
    send_description: str,
) -> None:
    if not segments:
        st.session_state._send_area_error = {
            "summary": empty_summary,
            "context": {"song": song.title, "send_mode": send_mode},
            "traceback": "",
        }
        return

    combined_syx = b"".join(syx for _, syx in segments)
    pat_names = [name for name, _ in segments]
    port_name = _port_name(dest)

    if port_name != "DEBUG":
        with st.spinner(f"Sending {len(segments)} {send_description} to {port_name}..."):
            err = _send_syx_via_midi(combined_syx, port_name)
            if err:
                st.session_state._send_area_error = {
                    "summary": err,
                    "context": {
                        "action": "midi_send",
                        "song": song.title,
                        "send_mode": send_mode,
                        "destination": port_name,
                        "pattern_names": pat_names,
                    },
                    "traceback": "",
                }
                return

    st.session_state._send_area_ok = True
    st.session_state._send_area_ok_detail = {
        "dest": port_name,
        "mode": send_mode,
        "patterns": len(segments),
        "pattern_names": pat_names,
    }


def _run_send_bundle_by_section(song: SongModel, settings: AppSettings, dest: str, send_mode: str = "Bundle by Section") -> None:
    """Compile via bundle planner (preserves section-prefixed pattern names) and send."""
    _clear_send_area_state()

    with st.spinner("Compiling bundle..."):
        try:
            segments = song_to_syx_bytes_bundle(song, settings)
        except ModuleNotFoundError:
            exc_msg = "digitone-syx-toolkit is required: `pip install -e ../digitone-syx-toolkit`"
            st.session_state._send_area_error = {"summary": exc_msg, "context": {}, "traceback": ""}
            return
        except Exception as exc:
            _store_send_error(exc, action="bundle_compile", song=song, dest=dest, send_mode=send_mode, settings=settings)
            return

    _finish_send_segments(
        song,
        dest,
        send_mode,
        segments,
        empty_summary="Bundle compile produced no segments.",
        send_description="pattern(s)",
    )


# ── Realtime preview state keys ──────────────────────────────────────────────
# "_preview_state": "idle" | "running" | "stopping" | "finished" | "stopped" | "error" | "debug_log"
# "_preview_stop_event": threading.Event | None
# "_preview_thread": threading.Thread | None
# "_preview_result_queue": queue.Queue | None
# "_preview_error": str | None
# "_preview_traceback": str | None
# "_preview_logs": list[str] | None
# "_preview_result_message": str | None
# "_preview_started_at": float | None
# "_preview_port_name": str | None

_PREVIEW_STATE_KEYS = [
    ("_preview_state", "idle"),
    ("_preview_stop_event", None),
    ("_preview_thread", None),
    ("_preview_result_queue", None),
    ("_preview_error", None),
    ("_preview_traceback", None),
    ("_preview_logs", None),
    ("_preview_result_message", None),
    ("_preview_started_at", None),
    ("_preview_port_name", None),
]


@dataclass
class PreviewWorkerResult:
    status: Literal["finished", "stopped", "error"]
    message: str
    error: str | None = None
    traceback: str | None = None


def _preview_worker(
    play_notes: list[tuple[float, float, int, int, str]],
    port_name: str,
    stop_event: threading.Event,
    result_queue: "queue.Queue[PreviewWorkerResult]",
) -> None:
    """Worker thread: sends MIDI note events, respects stop_event, sends note_off on exit."""
    import mido

    active: list[tuple[float, int, int]] = []
    channels_used: set[int] = set()
    try:
        with mido.open_output(port_name) as out:
            try:
                idx = 0
                start = time.perf_counter()
                while (idx < len(play_notes) or active) and not stop_event.is_set():
                    now = time.perf_counter() - start
                    # 1. note_off for expired notes (before note_on for same tick)
                    still_active = []
                    for off_sec, note, ch in active:
                        if now >= off_sec:
                            out.send(mido.Message("note_off", note=note, velocity=0, channel=ch))
                        else:
                            still_active.append((off_sec, note, ch))
                    active = still_active
                    # 2. note_on for notes due now
                    while idx < len(play_notes) and play_notes[idx][0] <= now:
                        _, off_sec, note, ch, _ = play_notes[idx]
                        out.send(mido.Message("note_on", note=note, velocity=80, channel=ch))
                        active.append((off_sec, note, ch))
                        channels_used.add(ch)
                        idx += 1
                    # 3. sleep until next event, capped at 5ms so Stop responds quickly
                    next_on = play_notes[idx][0] if idx < len(play_notes) else None
                    next_off = min(t for t, _, _ in active) if active else None
                    candidates = [x for x in (next_on, next_off) if x is not None]
                    if candidates:
                        now = time.perf_counter() - start
                        timeout = max(0.0, min(min(candidates) - now, 0.005))
                        stop_event.wait(timeout)
            finally:
                # note_off while port is still open — guaranteed cleanup path
                for _, note, ch in active:
                    try:
                        out.send(mido.Message("note_off", note=note, velocity=0, channel=ch))
                    except Exception:
                        pass
                # All Notes Off CC as safety net for each channel used
                for ch in channels_used:
                    try:
                        out.send(mido.Message("control_change", control=123, value=0, channel=ch))
                    except Exception:
                        pass
    except Exception as exc:
        result_queue.put(PreviewWorkerResult(
            status="error",
            message=f"MIDI error: {exc}",
            error=str(exc),
            traceback=tb_module.format_exc(),
        ))
        return

    if stop_event.is_set():
        result_queue.put(PreviewWorkerResult(status="stopped", message="Preview stopped."))
    else:
        result_queue.put(PreviewWorkerResult(status="finished", message="Preview complete."))


def _sync_preview_state() -> None:
    """Poll worker thread completion and update session_state accordingly."""
    state = st.session_state.get("_preview_state", "idle")
    if state not in ("running", "stopping"):
        return
    thread: threading.Thread | None = st.session_state.get("_preview_thread")
    if thread is None or thread.is_alive():
        return
    result_queue: "queue.Queue[PreviewWorkerResult] | None" = st.session_state.get("_preview_result_queue")
    result: PreviewWorkerResult | None = None
    if result_queue is not None:
        try:
            result = result_queue.get_nowait()
        except queue.Empty:
            pass
    if result is None:
        result = PreviewWorkerResult(status="finished", message="Preview complete.")
    st.session_state["_preview_state"] = result.status
    st.session_state["_preview_result_message"] = result.message
    st.session_state["_preview_error"] = result.error
    st.session_state["_preview_traceback"] = result.traceback
    st.session_state["_preview_thread"] = None


def _build_play_notes(
    song: "SongModel",
    settings: "AppSettings",
) -> "list[tuple[float, float, int, int, str]] | None":
    """Compile song and return play_notes list, or None on error (sets st.error)."""
    from changes.ui_pipeline import compile_song_for_ui

    try:
        compiled = compile_song_for_ui(song, settings)
    except Exception as exc:
        st.error(f"Pipeline error: {exc}")
        return None

    voice_to_track = compiled.target_profile.voice_to_track
    tempo_bpm = float(compiled.timeline.performance_tempo)

    def _q_to_sec(q: float) -> float:
        return float(q) * 60.0 / tempo_bpm

    play_notes = []
    for ev in compiled.timeline.events:
        track = voice_to_track.get(ev.voice_id)
        if track is None:
            continue
        play_notes.append((
            _q_to_sec(ev.onset_quarters),
            _q_to_sec(ev.onset_quarters + ev.duration_quarters),
            ev.note_midi,
            track - 1,
            ev.voice_id,
        ))
    play_notes.sort(key=lambda n: n[0])
    return play_notes


def _start_preview(song: "SongModel", settings: "AppSettings", dest: str) -> None:
    """Initiate a preview: DEBUG mode sets debug_log state, real port starts worker thread."""
    if _preview_is_running():
        return
    play_notes = _build_play_notes(song, settings)
    if play_notes is None:
        return
    if not play_notes:
        st.warning("No routed notes found (are all voices set to None?)")
        return

    port_name = _port_name(dest)
    st.session_state["_preview_port_name"] = port_name
    st.session_state["_preview_started_at"] = time.time()

    if port_name == "DEBUG":
        logs = ["Transport:start"]
        for onset, offset, note, ch, voice_id in play_notes:
            dur = offset - onset
            logs.append(
                f"t+{onset:.2f}s  ch{ch+1}:{_midi_name(note)}  ({voice_id})  dur:{dur:.2f}s"
            )
        logs.append("Transport:stop")
        st.session_state["_preview_state"] = "debug_log"
        st.session_state["_preview_logs"] = logs
        st.session_state["_preview_thread"] = None
        return

    stop_event = threading.Event()
    result_queue: "queue.Queue[PreviewWorkerResult]" = queue.Queue()
    t = threading.Thread(
        target=_preview_worker,
        args=(play_notes, port_name, stop_event, result_queue),
        daemon=True,
    )
    st.session_state["_preview_stop_event"] = stop_event
    st.session_state["_preview_result_queue"] = result_queue
    st.session_state["_preview_thread"] = t
    st.session_state["_preview_state"] = "running"
    t.start()


def _stop_preview() -> None:
    """Signal the worker thread to stop."""
    stop_event: threading.Event | None = st.session_state.get("_preview_stop_event")
    if stop_event is not None:
        stop_event.set()
    st.session_state["_preview_state"] = "stopping"


def _clear_preview_dialog_state() -> None:
    """Reset all preview state keys to their idle defaults."""
    for key, default in _PREVIEW_STATE_KEYS:
        st.session_state[key] = default


def _preview_is_running() -> bool:
    return st.session_state.get("_preview_state", "idle") in ("running", "stopping")


@st.dialog("Preview", dismissible=False)
def _dialog_preview() -> None:
    _sync_preview_state()
    state = st.session_state.get("_preview_state", "idle")
    port_name = st.session_state.get("_preview_port_name", "")

    if state in ("running", "stopping"):
        label = "Stopping..." if state == "stopping" else f"Playing on {port_name}..."
        with st.spinner(label):
            pass
        if state == "running":
            if st.button("Stop Preview", key="_preview_stop_btn", use_container_width=True):
                _stop_preview()
                st.rerun()
        else:
            st.button("Stopping...", key="_preview_stopping_btn", disabled=True, use_container_width=True)
        # Poll until the worker finishes; 0.5s keeps MIDI timing priority over UI refresh
        time.sleep(0.5)
        st.rerun()

    elif state == "debug_log":
        logs = st.session_state.get("_preview_logs") or []
        st.code("\n".join(logs[:60]), language="text")
        if st.button("Close", key="_preview_close_btn", use_container_width=True):
            _clear_preview_dialog_state()
            st.rerun()

    elif state == "finished":
        msg = st.session_state.get("_preview_result_message") or "Preview complete."
        st.success(msg)
        if st.button("Close", key="_preview_close_btn", use_container_width=True):
            _clear_preview_dialog_state()
            st.rerun()

    elif state == "stopped":
        msg = st.session_state.get("_preview_result_message") or "Preview stopped."
        st.info(msg)
        if st.button("Close", key="_preview_close_btn", use_container_width=True):
            _clear_preview_dialog_state()
            st.rerun()

    elif state == "error":
        err = st.session_state.get("_preview_error") or "Unknown error"
        st.error(f"Preview error: {err}")
        tb = st.session_state.get("_preview_traceback")
        if tb:
            with st.expander("Details"):
                st.code(tb, language="text")
        if st.button("Close", key="_preview_close_btn", use_container_width=True):
            _clear_preview_dialog_state()
            st.rerun()

    else:
        # Fallback / idle — should not normally appear, but close gracefully
        if st.button("Close", key="_preview_close_btn", use_container_width=True):
            _clear_preview_dialog_state()
            st.rerun()


def _run_send(song: SongModel, settings: AppSettings, dest: str, send_mode: str) -> None:
    if _is_bundle_send_mode(send_mode):
        _run_send_bundle_by_section(song, settings, dest, send_mode)
    else:
        _run_send_linear_split(song, settings, dest, send_mode)


@st.dialog("Send SysEx to Digitone II?", dismissible=False)
def _show_send_confirm_dialog(song: SongModel | None, settings: AppSettings, dest: str, send_mode: str) -> None:
    st.warning("This will write data to hardware.")

    # Show MIDI port prominently
    port_name = dest if dest and not dest.startswith("(Select") else None
    if port_name:
        st.markdown(f"**Destination:**\n\n`{port_name}`")
    else:
        st.error("No MIDI destination selected. Please select a MIDI port.")
    st.caption(f"Send mode: {send_mode}")

    send_allowed = port_name is not None
    cc1, cc2, cc3 = st.columns(3, width="stretch", gap="small")
    if cc1.button("Cancel", key="_send_conf_cancel", use_container_width=True):
        _request_rerun(close_send_confirm=True)
    if cc2.button("Send", type="primary", key="_send_conf_ok", disabled=not send_allowed, use_container_width=True):
        if song:
            _run_send(song, settings, dest, send_mode)
        _request_rerun(close_send_confirm=True)
    if cc3.button("Always Send", key="_send_conf_no_confirm", disabled=not send_allowed, use_container_width=True):
        settings.confirm_before_hardware_write = False
        save_settings(settings)
        st.session_state._settings = settings
        if song:
            _run_send(song, settings, dest, send_mode)
        _request_rerun(close_send_confirm=True, reason="visible_settings_changed")


def _run_send_linear_split(song: SongModel, settings: AppSettings, dest: str, send_mode: str = "Linear") -> None:
    _clear_send_area_state()

    with st.spinner("Generating Linear Auto Split SysEx..."):
        try:
            segments = song_to_syx_bytes_linear_split(song, settings)
        except ModuleNotFoundError:
            exc_msg = "digitone-syx-toolkit is required: `pip install -e ../digitone-syx-toolkit`"
            st.session_state._send_area_error = {"summary": exc_msg, "context": {}, "traceback": ""}
            return
        except Exception as exc:
            _store_send_error(exc, action="linear_split_export", song=song, dest=dest, send_mode=send_mode, settings=settings)
            return

    _finish_send_segments(
        song,
        dest,
        send_mode,
        segments,
        empty_summary="Linear Auto Split produced no patterns.",
        send_description="Linear pattern(s)",
    )


def _send_syx_via_midi(syx_bytes: bytes, port_name: str) -> str | None:
    """Send raw SysEx bytes to a MIDI output port. Returns error string or None."""
    import time
    try:
        import mido
    except ImportError:
        return "mido is not installed"

    # Parse SysEx messages (F0 ... F7 sequences)
    messages: list[list[int]] = []
    i = 0
    while i < len(syx_bytes):
        if syx_bytes[i] == 0xF0:
            try:
                j = syx_bytes.index(0xF7, i)
            except ValueError:
                break
            messages.append(list(syx_bytes[i + 1 : j]))
            i = j + 1
        else:
            i += 1

    if not messages:
        return "No SysEx messages found"

    try:
        with mido.open_output(port_name) as out:
            for data in messages:
                out.send(mido.Message("sysex", data=data))
                time.sleep(0.05)
        return None
    except Exception as exc:
        return f"MIDI send error: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="EUB Changes",
        layout="wide",
        page_icon=str(_LOGO_PATH) if _LOGO_PATH.exists() else "🎵",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    _ss_init()
    _render_pending_ui_messages()
    _render_header()
    _render_main()
    _render_preview_send()
    with st.expander("Import / Layer Options / Settings / Advanced", expanded=False, icon=_ICON_IMPORT):
        _render_import_section()
        st.divider()
        _render_settings()


if __name__ == "__main__":
    main()
