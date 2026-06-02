"""Initial release Streamlit UI for EUB Changes."""

from __future__ import annotations

import base64
import functools
import re
from dataclasses import replace as _replace
from fractions import Fraction as _Frac
from pathlib import Path

import streamlit as st

from changes.app_settings import AppSettings, load_settings, save_settings
from changes.editor import EditorState, editor_to_song_model
from changes.key_signature import format_working_key, parse_working_key_display
from changes.library import SongEntry, delete_song, list_songs, overwrite_song, save_song
from changes.models.song_model import SongModel, song_model_to_dict
from changes.ui_pipeline import count_auto_split_patterns, song_to_syx_bytes

# ── Paths ─────────────────────────────────────────────────────────────────────

_ASSETS = Path(__file__).parent.parent.parent / "docs" / "assets" / "1x"
_LOGO_PATH_HEADER = _ASSETS / "eub_changes_logo.png"
_LOGO_PATH = _ASSETS / "eub_changes_logo_square_transparent.png"
_ICON_PATH = _ASSETS / "icon_cloud.png"
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
.send-area { background:white; border:1px solid #E2DAE8; border-radius:12px; padding:16px; margin-top:16px; }
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

def _range_display(center: int, lo: int, hi: int) -> str:
    return f"{_midi_name(center)} ({_midi_name(center-lo)}–{_midi_name(center+hi)})"

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

# settings_to_render_profile is imported from ui_pipeline


# ── Icon ──────────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _icon_b64() -> str:
    if _ICON_PATH.exists():
        return base64.b64encode(_ICON_PATH.read_bytes()).decode()
    return ""


@functools.lru_cache(maxsize=1)
def _header_icon_bytes() -> bytes | None:
    if _ICON_PATH.exists():
        return _ICON_PATH.read_bytes()
    return None


def _hdr_item(label: str, value: str) -> str:
    ico = _icon_b64()
    img = f'<img src="data:image/png;base64,{ico}" class="hdr-icon"/>' if ico else ""
    return f'<span class="hdr-item">{img}<span class="hdr-label">{label}</span><span class="hdr-val">{value}</span></span>'


def _render_header_field(label: str, value: str | None = None, *, render_controls=None) -> None:
    icon = _header_icon_bytes()
    if render_controls is not None:
        render_controls()
    else:
        st.write(f"**{value or ''}**")
    bottom_icon_col, bottom_label_col = st.columns([0.18, 1], gap="small", vertical_alignment="center")
    with bottom_icon_col:
        if icon is not None:
            st.image(icon, width=18)
    with bottom_label_col:
        st.caption(label)

# ── Session state ─────────────────────────────────────────────────────────────

def _ss_init() -> None:
    if "_page" not in st.session_state:
        st.session_state._page = "Main"
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
        ("pending_root", None), ("pending_acc", ""), ("ti", ""),
        ("_compose_save_mode", None), ("_compose_save_pending", None),
        ("_table_save_mode", None), ("_table_save_pending", None),
        ("_table_save_suppressed_signature", None),
        ("_songlist_table_reset_token", 0),
        ("_songlist_error_message", None),
        ("_midi_update_candidates", None), ("_midi_update_kept", None), ("_midi_update_unmatched", None),
        ("_import_bundle_result", None),
        ("_import_progress_request", None), ("_import_progress_status", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def _refresh_library() -> None:
    s = st.session_state.get("_settings") or load_settings()
    from pathlib import Path
    st.session_state._library = list_songs(Path(s.library_path))


def _reset_song_table_view() -> None:
    st.session_state._songlist_table_reset_token += 1


# ── Header data sources ───────────────────────────────────────────────────────

def _dirty_song() -> SongModel | None:
    state: EditorState = st.session_state.get("editor")
    if state and state.cells:
        try:
            return editor_to_song_model(state)
        except Exception:
            pass
    return None


def _header_song() -> SongModel | None:
    page = st.session_state._page
    if page == "Songlist":
        path = st.session_state._selected_path
        if path:
            for e in st.session_state._library:
                if e.path == path and e.song:
                    return e.song
        return None
    return _dirty_song()


def _playback_song() -> SongModel | None:
    page = st.session_state._page
    if page == "Songlist":
        path = st.session_state._selected_path
        if path:
            for e in st.session_state._library:
                if e.path == path and e.song:
                    return e.song
        return _dirty_song()
    return _dirty_song()

# ── Logo ─────────────────────────────────────────────────────────────
st.logo(
    _LOGO_PATH_HEADER, 
    link="https://github.com/emnyeca/changes/", 
    size="large", 
    icon_image=_LOGO_PATH_HEADER
    )

# ── Common header ─────────────────────────────────────────────────────────────

def _render_header() -> None:
    song = _header_song()
    title = song.title if song else "Select a song"
    key = format_working_key(song.working_key, getattr(song, "working_key_mode", None)) if song else "—"
    tempo = str(int(song.performance_tempo)) if song else "—"
    meter = (f"{song.measures[0].meter_numerator}/{song.measures[0].meter_denominator}"
             if song and song.measures else "—")
    has_selected_song = st.session_state.get("_selected_path") is not None

    def _render_transpose_controls() -> None:
        down_col, up_col = st.columns([1,1], vertical_alignment="bottom", gap="small")
        with down_col:
            if st.button("▽", key="key_down", help="Transpose down by one semitone", disabled=not has_selected_song, width="stretch"):
                _transpose_state(st.session_state.editor, -1)
                st.session_state._editor_dirty = True
                st.rerun()
        with up_col:
            if st.button("△", key="key_up", help="Transpose up by one semitone", disabled=not has_selected_song, width="stretch"):
                _transpose_state(st.session_state.editor, +1)
                st.session_state._editor_dirty = True
                st.rerun()

    with st.container(border=True):
        song_col, key_col, tempo_col, meter_col, transpose_col = st.columns([3.2, 1.2, 1.2, 1.2, 1.2], vertical_alignment="bottom", gap="small")
        with song_col:
            _render_header_field("Song", title)
        with key_col:
            _render_header_field("Key", f"{key}{' ●' if st.session_state._editor_dirty else ''}")
        with tempo_col:
            _render_header_field("Tempo", tempo)
        with meter_col:
            _render_header_field("Meter", meter)
        with transpose_col:
            _render_header_field("Transpose", render_controls=_render_transpose_controls)


# ── Sidebar ───────────────────────────────────────────────────────────────────

# ── Chord helpers (editor) ────────────────────────────────────────────────────

_ROOT_RE = re.compile(r"^([A-G][#b]?)(.*)")


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


def _cell_strip(state: EditorState) -> str:
    parts: list[str] = []
    for i, cell in enumerate(state.cells):
        if i == state.cursor:
            parts.append("▸")
        parts.append(cell)
    if state.cursor == len(state.cells):
        parts.append("▸")
    return " ".join(parts) if parts else "▸  (empty)"


# ── SYX / pattern-count helpers (delegates to ui_pipeline) ───────────────────

def _export_syx_bytes(song: SongModel, settings: AppSettings) -> bytes:
    return song_to_syx_bytes(song, settings)


def _count_patterns(song: SongModel, settings: AppSettings) -> int:
    return count_auto_split_patterns(song, settings)


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
        st.rerun()
    if c2.button("Keep both", key="tsd_keep", use_container_width=True):
        st.session_state._table_save_mode = "keep_both"
        st.rerun()
    if c3.button("Cancel", key="tsd_cancel", use_container_width=True):
        st.session_state._table_save_suppressed_signature = pending.get("signature")
        st.session_state._table_save_mode = None
        st.session_state._table_save_pending = None
        _reset_song_table_view()
        st.rerun()


@st.dialog("Discard Unsaved Changes?", dismissible=False)
def _dialog_pending_switch() -> None:
    pending_switch = st.session_state.get("_pending_switch")
    if pending_switch is None:
        return

    st.warning(f'Unsaved changes will be discarded. Switch to "{pending_switch.title}"?')
    col_cancel, col_discard = st.columns([1, 1], width="stretch", gap="small")
    if col_cancel.button("Cancel", key="sw_cancel", use_container_width=True):
        st.session_state._pending_switch = None
        st.rerun()
    if col_discard.button("Discard and switch", type="primary", key="sw_discard", use_container_width=True):
        _do_switch_song(pending_switch)
        st.rerun()


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
        st.rerun()
    if c2.button("Delete", type="primary", key="del_confirm", use_container_width=True):
        delete_song(del_path)
        if st.session_state._selected_path == del_path:
            st.session_state._selected_path = None
        st.session_state._delete_confirm = None
        _refresh_library()
        st.rerun()


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
        st.rerun()
    if c2.button("Keep both", key="ic_keep", use_container_width=True):
        st.session_state._import_conflict_mode = None
        st.session_state._import_progress_request = {"kind": "save", "mode": "keep_both"}
        st.rerun()
    if c3.button("Cancel import", key="ic_cancel", use_container_width=True):
        st.session_state._import_conflict_mode = None
        st.session_state._import_pending = []
        st.session_state._import_pending_failed = []
        st.rerun()


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
            st.session_state._import_progress_request = None
            st.session_state._import_progress_status = None
            st.rerun()


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
        or del_path is not None
        or import_conflict_pending
        or import_progress_pending
        or midi_update_pending
    )

    if st.session_state.get("_table_save_mode") in ("update", "keep_both"):
        _execute_table_save(st.session_state._table_save_mode)
        st.session_state._table_save_mode = None
        st.session_state._table_save_pending = None
        st.session_state._table_save_suppressed_signature = None
        st.rerun()

    # Process resolved imports
    if st.session_state.get("_import_conflict_mode") in ("overwrite", "keep_both"):
        st.session_state._import_progress_request = {
            "kind": "save",
            "mode": st.session_state._import_conflict_mode,
        }
        st.session_state._import_conflict_mode = None
        st.rerun()

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
    )
    filtered = [e for e in entries if search.lower() in e.title.lower()] if search else entries

    # ── Song table ────────────────────────────────────────────────────────────
    import pandas as pd

    def _meter(e: SongEntry) -> str:
        if e.song and e.song.measures:
            m = e.song.measures[0]
            return f"{m.meter_numerator}/{m.meter_denominator}"
        return "—"

    def _parse_meter(text: str) -> tuple[int, int] | None:
        m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", text)
        if not m:
            return None
        num = int(m.group(1))
        den = int(m.group(2))
        if num <= 0 or den not in (2, 4, 8):
            return None
        return num, den

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
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=ui_locked,
        key=table_key,
        column_config={
            "Select": st.column_config.CheckboxColumn("", width="small"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Key":   st.column_config.TextColumn("Key", width="small"),
            "Tempo": st.column_config.NumberColumn("Tempo", min_value=30, max_value=300, width="small"),
            "Meter": st.column_config.TextColumn("Meter", width="small"),
            "Delete": st.column_config.CheckboxColumn("🗑", width="small"),
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
                st.rerun()

    # Table-integrated delete action (rightmost column)
    delete_rows = [
        i for i in range(len(edited_df))
        if bool(edited_df.at[i, "Delete"]) and (i < len(orig_df) and not bool(orig_df.at[i, "Delete"]))
    ]
    if delete_rows and not ui_locked:
        delete_idx = delete_rows[-1]
        if 0 <= delete_idx < len(filtered):
            st.session_state._delete_confirm = filtered[delete_idx].path
            st.rerun()

    # Persist inline edits (Title / Key / Tempo / Meter)
    if not table_save_pending and not ui_locked:
        for i, entry in enumerate(filtered):
            if entry.song is None:
                continue
            new_title = edited_df.at[i, "Title"] if i < len(edited_df) else entry.title
            new_key   = edited_df.at[i, "Key"]   if i < len(edited_df) else format_working_key(entry.song.working_key, getattr(entry.song, "working_key_mode", None))
            new_tempo = edited_df.at[i, "Tempo"] if i < len(edited_df) else int(entry.song.performance_tempo)
            new_meter = edited_df.at[i, "Meter"] if i < len(edited_df) else _meter(entry)

            title_val = str(new_title).strip()
            key_val = str(new_key).strip()
            tempo_val = int(new_tempo)
            meter_val = str(new_meter).strip()

            old_title = entry.title
            old_key = format_working_key(entry.song.working_key, getattr(entry.song, "working_key_mode", None))
            old_tempo = int(entry.song.performance_tempo)
            old_meter = _meter(entry)

            if (
                title_val != old_title
                or key_val != old_key
                or tempo_val != old_tempo
                or meter_val != old_meter
            ):
                if not title_val:
                    st.session_state._songlist_error_message = "Title cannot be empty"
                    _reset_song_table_view()
                    st.rerun()
                if tempo_val < 30 or tempo_val > 300:
                    st.session_state._songlist_error_message = "Tempo must be between 30 and 300"
                    _reset_song_table_view()
                    st.rerun()

                parsed_key, parsed_mode = parse_working_key_display(key_val)
                if parsed_key is None and key_val not in ("", "-", "?"):
                    st.session_state._songlist_error_message = (
                        "Invalid key format. Examples: C, Em, F#m, Bb, C?, -"
                    )
                    _reset_song_table_view()
                    st.rerun()

                parsed_meter = _parse_meter(meter_val)
                if parsed_meter is None:
                    st.session_state._songlist_error_message = "Meter must be in n/d format (e.g. 4/4) with denominator 2, 4, or 8"
                    _reset_song_table_view()
                    st.rerun()

                meter_num, meter_den = parsed_meter
                changed_fields: list[tuple[str, str, str]] = []
                if title_val != old_title:
                    changed_fields.append(("Title", old_title, title_val))
                if key_val != old_key:
                    changed_fields.append(("Key", old_key or "(empty)", key_val or "(empty)"))
                if tempo_val != old_tempo:
                    changed_fields.append(("Tempo", str(old_tempo), str(tempo_val)))
                if meter_val != old_meter:
                    changed_fields.append(("Meter", old_meter, meter_val))

                updated_measures = tuple(
                    _replace(m, meter_numerator=meter_num, meter_denominator=meter_den)
                    for m in entry.song.measures
                )
                updated_song = SongModel(
                    title=title_val,
                    working_key=parsed_key,
                    working_key_mode=parsed_mode,
                    performance_tempo=_Frac(tempo_val).limit_denominator(1000),
                    measures=updated_measures,
                )
                signature = (
                    str(entry.path),
                    title_val,
                    parsed_key,
                    parsed_mode,
                    int(tempo_val),
                    int(meter_num),
                    int(meter_den),
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
                st.rerun()

    st.caption(f"{len(filtered)} song(s)")

    # ── Confirmation / warning dialogs ──────────────────────────────────────
    if table_save_pending:
        _dialog_table_save()
    elif pending_switch is not None:
        _dialog_pending_switch()
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
    st.subheader("Import")
    uploaded = st.file_uploader(
        "Accepts: .zip (iReal-musicxml), .musicxml, .xml / .mid, .midi is for tempo metadata only",
        type=["zip", "musicxml", "xml", "mid", "midi"],
        accept_multiple_files=True,
        key="_sl_uploader",
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
        st.rerun()

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
    if song.working_key:
        state.working_key = song.working_key
    if song.measures:
        m = song.measures[0]
        state.meter = f"{m.meter_numerator}/{m.meter_denominator}"
    # Rebuild cells from measures
    for m in song.measures:
        for h in m.harmony:
            state.insert(h.symbol)
        state.insert("|")
    st.session_state.editor = state
    st.session_state.editor_title = state.title
    st.session_state.editor_tempo = state.tempo
    st.session_state.working_key_input = state.working_key
    st.session_state._editor_dirty = False


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
        st.session_state._midi_update_candidates = None
        st.session_state._midi_update_kept = None
        st.session_state._midi_update_unmatched = None
        _refresh_library()
        st.rerun()
    if mu2.button("Cancel", key="_midi_upd_cancel", use_container_width=True):
        st.session_state._midi_update_candidates = None
        st.session_state._midi_update_kept = None
        st.session_state._midi_update_unmatched = None
        st.rerun()


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
        st.warning(f"Updated {updated}, failed {len(failed)}: " +
                   ", ".join(t for t, _ in failed))
    else:
        st.success(f"{updated} song(s) updated.")


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
    st.success(f"Saved: {path.name}")


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
    st.success(f"Saved: {saved_path.name}")


# ─────────────────────────────────────────────────────────────────────────────
# Page: Compose
# ─────────────────────────────────────────────────────────────────────────────

def _render_compose() -> None:
    state: EditorState = st.session_state.editor
    s = st.session_state._settings
    lib_path = Path(s.library_path)

    # ── Cell display ───────────────────────────────────────────────────────────
    st.markdown(f"<div class='chord-cell-display'>{_cell_strip(state)}</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page: Settings
# ─────────────────────────────────────────────────────────────────────────────

def _render_settings() -> None:
    settings: AppSettings = st.session_state._settings
    changed = False

    def _toggle(label: str, key: str, value: bool, on_label="ON", off_label="OFF") -> bool:
        opts = [on_label, off_label]
        idx = 0 if value else 1
        result = st.selectbox(label, opts, index=idx, key=key)
        return result == on_label

    # ── Cloud ─────────────────────────────────────────────────────────────────
    st.subheader("Cloud")
    c1, c2, c3 = st.columns([2, 2, 3])
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
        new_cloud_note = st.selectbox("Center note", cloud_notes, index=ci, key="_s_cloud_center")
        new_cloud_midi = _name_to_midi(new_cloud_note)
        if new_cloud_midi != settings.cloud_center_midi:
            settings.cloud_center_midi = new_cloud_midi; changed = True
    with c3:
        st.markdown(f"**Range:** `{_range_display(settings.cloud_center_midi, 12, 12)}`")

    # Per-voice track assignment (None = don't send)
    _TRACK_OPTS = ["None"] + [str(i) for i in range(1, 17)]
    st.caption("Track per voice — select **None** to exclude that voice from output")
    cloud_cols = st.columns(6)
    new_cloud_tracks = list(settings.cloud_tracks[:6])
    while len(new_cloud_tracks) < 6:
        new_cloud_tracks.append(None)
    for vi in range(6):
        cur = new_cloud_tracks[vi]
        idx = 0 if cur is None else cur
        sel = cloud_cols[vi].selectbox(
            f"V{vi + 1}", _TRACK_OPTS, index=idx, key=f"_s_cloud_t{vi + 1}",
            label_visibility="visible",
        )
        new_cloud_tracks[vi] = None if sel == "None" else int(sel)
    if new_cloud_tracks != list(settings.cloud_tracks[:6]):
        settings.cloud_tracks = new_cloud_tracks; changed = True

    st.divider()

    # ── Bass ──────────────────────────────────────────────────────────────────
    st.subheader("Bass")
    b1, b2, b3 = st.columns([2, 2, 3])
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
        new_bass_note = st.selectbox("Center note", bass_notes, index=bi, key="_s_bass_center")
        new_bass_midi = _name_to_midi(new_bass_note)
        if new_bass_midi != settings.bass_center_midi:
            settings.bass_center_midi = new_bass_midi; changed = True
    with b3:
        st.markdown(f"**Range:** `{_range_display(settings.bass_center_midi, 0, 11)}`")
    bt1, _ = st.columns(2)
    cur_bass = settings.bass_track
    bass_idx = 0 if cur_bass is None else cur_bass
    new_bass_sel = bt1.selectbox("Track", _TRACK_OPTS, index=bass_idx, key="_s_bass_track")
    new_bass_track: int | None = None if new_bass_sel == "None" else int(new_bass_sel)
    if new_bass_track != settings.bass_track:
        settings.bass_track = new_bass_track; changed = True

    st.caption("Bass Repeat Variation: planned")

    st.divider()

    # ── Chord ─────────────────────────────────────────────────────────────────
    st.subheader("Chord")
    ch1, ch2, ch3 = st.columns([2, 2, 3])
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
        new_chord_note = st.selectbox("Center note", chord_notes, index=chi, key="_s_chord_center")
        new_chord_midi = _name_to_midi(new_chord_note)
        if new_chord_midi != settings.chord_center_midi:
            settings.chord_center_midi = new_chord_midi; changed = True
    with ch3:
        st.markdown(f"**Range:** `{_range_display(settings.chord_center_midi, 12, 12)}`")
    cur_chord = settings.chord_track
    chord_idx = 0 if cur_chord is None else cur_chord
    new_chord_sel = st.selectbox("Track", _TRACK_OPTS, index=chord_idx, key="_s_chord_track")
    new_chord_track: int | None = None if new_chord_sel == "None" else int(new_chord_sel)
    if new_chord_track != settings.chord_track:
        settings.chord_track = new_chord_track; changed = True

    st.divider()

    # ── Safety ────────────────────────────────────────────────────────────────
    st.subheader("Safety")
    new_confirm = _toggle("Confirm before hardware write", "_s_confirm_hw",
                           settings.confirm_before_hardware_write)
    if new_confirm != settings.confirm_before_hardware_write:
        settings.confirm_before_hardware_write = new_confirm; changed = True

    # ── Library path ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Library")
    lib_col, browse_col = st.columns([5, 1])
    with lib_col:
        new_lib_path = st.text_input("Library folder", value=settings.library_path, key="_s_lib_path")
        if new_lib_path != settings.library_path:
            settings.library_path = new_lib_path; changed = True
            _refresh_library()
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
                    _refresh_library()
                    st.rerun()
            except Exception:
                st.info("Please enter the folder path manually")

    if changed:
        save_settings(settings)
        st.session_state._settings = settings

    # ── Advanced ──────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Advanced")
    song = _playback_song()
    if song:
        adv1, adv2 = st.columns(2)
        with adv1:
            if st.button("Export SYX", type="primary", use_container_width=True, key="_adv_syx"):
                with st.spinner("Generating SYX..."):
                    try:
                        syx = _export_syx_bytes(song, settings)
                        st.session_state._syx_bytes = syx
                        st.session_state._syx_fname = f"{song.title or 'changes'}.syx"
                        st.success("Done")
                    except ModuleNotFoundError:
                        st.error("digitone-syx-toolkit is required:\n`pip install -e ../digitone-syx-toolkit`")
                    except Exception as exc:
                        st.error(str(exc))
            if "_syx_bytes" in st.session_state:
                st.download_button("↓ Download .syx", data=st.session_state._syx_bytes,
                                   file_name=st.session_state.get("_syx_fname","changes.syx"),
                                   mime="application/octet-stream", use_container_width=True,
                                   key="_adv_syx_dl")
        with adv2:
            if st.button("Dry-run", use_container_width=True, key="_adv_dry"):
                with st.spinner("Analyzing..."):
                    try:
                        from changes.digitone.bundle_planner import compile_timeline_to_digitone_bundle_plan
                        from changes.ui_pipeline import compile_song_for_ui
                        compiled = compile_song_for_ui(song, settings)
                        bp = compile_timeline_to_digitone_bundle_plan(
                            compiled.song, compiled.timeline, compiled.target_profile
                        )
                        st.json({
                            "pattern_count": len(bp.patterns),
                            "patterns": [
                                {"name": p.pattern_name, "steps": p.total_steps, "section": p.section_label}
                                for p in bp.patterns
                            ],
                            "warnings": list(bp.warnings),
                        })
                    except Exception as exc:
                        st.error(str(exc))
    else:
        st.caption("No song loaded. Select or compose a song first.")


# ─────────────────────────────────────────────────────────────────────────────
# Preview / Send area
# ─────────────────────────────────────────────────────────────────────────────

def _render_main() -> None:
    _render_compose()
    _render_songlist(show_import=False)
    with st.expander("Import / Settings", expanded=False):
        _render_import_section()
        st.divider()
        _render_settings()


def _render_preview_send() -> None:
    song = _playback_song()
    has_selected_song = st.session_state.get("_selected_path") is not None
    settings: AppSettings = st.session_state._settings

    st.markdown("**Preview / Send**")

    # Auto split warning
    if song:
        try:
            n_pat = _count_patterns(song, settings)
            if n_pat > 1:
                st.markdown(
                    f'<span class="autosplit-warn" title="This song will be split to {n_pat} patterns automatically. '
                    f'Add section boundaries in Compose if you want musical control.">'
                    f'⚠ Auto Split → {n_pat} patterns</span>',
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

    if not settings.confirm_before_hardware_write:
        st.caption("⚠ Hardware write confirmation is OFF (see Settings)")

    # Destination
    ports = ["(Select MIDI Port Destination)"]
    try:
        import mido
        ports += mido.get_output_names()
    except Exception:
        pass
    dest = st.selectbox("Destination", ports, key="_dest_sel", label_visibility="collapsed")

    ps1, ps2 = st.columns(2)

    # Preview (Realtime MIDI)
    with ps1:
        if st.button("▶  Preview (Realtime MIDI)", use_container_width=True, key="_ps_preview", disabled=not has_selected_song):
            if not song:
                st.warning("No song loaded")
            else:
                _run_preview(song, settings, dest)

    # Send SysEx
    with ps2:
        if st.button("⬆  Send SysEx (Digitone)", type="primary", use_container_width=True, key="_ps_send", disabled=not has_selected_song):
            if not song:
                st.warning("No song loaded")
            elif settings.confirm_before_hardware_write:
                st.session_state._send_confirm = True
                st.rerun()
            else:
                _run_send(song, settings, dest)

    # Hardware write confirmation
    if st.session_state.get("_send_confirm"):
        _show_send_confirm_dialog(song, settings, dest)

    st.markdown("</div>", unsafe_allow_html=True)


def _run_preview(song: SongModel, settings: AppSettings, dest: str) -> None:
    from changes.ui_pipeline import compile_song_for_ui

    try:
        compiled = compile_song_for_ui(song, settings)
    except Exception as exc:
        st.error(f"Pipeline error: {exc}")
        return

    voice_to_track = compiled.target_profile.voice_to_track
    tempo_bpm = float(compiled.timeline.performance_tempo)

    def _q_to_sec(q):
        return float(q) * 60.0 / tempo_bpm

    # Build note schedule: (onset_sec, offset_sec, note_midi, midi_ch_0based, voice_id)
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

    if not play_notes:
        st.warning("No routed notes found (are all voices set to None?)")
        return

    play_notes.sort(key=lambda n: n[0])
    port_name = "DEBUG" if "DEBUG" in dest else dest

    with st.spinner("Running preview..."):
        try:
            logs = _send_pipeline_preview(play_notes, port_name)
            if port_name == "DEBUG" or logs:
                st.code("\n".join(logs[:60]), language="text")
        except Exception as exc:
            st.error(str(exc))


@st.dialog("Send SysEx to Digitone II?", dismissible=False)
def _show_send_confirm_dialog(song: SongModel | None, settings: AppSettings, dest: str) -> None:
    st.warning("This will write data to hardware.")
    cc1, cc2, cc3 = st.columns(3, width="stretch", gap="small")
    if cc1.button("Cancel", key="_send_conf_cancel", use_container_width=True):
        st.session_state._send_confirm = False
        st.rerun()
    if cc2.button("Send", type="primary", key="_send_conf_ok", use_container_width=True):
        st.session_state._send_confirm = False
        if song:
            _run_send(song, settings, dest)
        st.rerun()
    if cc3.button("Always Send", key="_send_conf_no_confirm", use_container_width=True):
        settings.confirm_before_hardware_write = False
        save_settings(settings)
        st.session_state._settings = settings
        st.session_state._send_confirm = False
        if song:
            _run_send(song, settings, dest)
        st.rerun()


def _send_pipeline_preview(
    play_notes: list[tuple[float, float, int, int, str]],
    port_name: str,
) -> list[str]:
    """Send note events from the compiled timeline, or log them in DEBUG mode."""
    if port_name == "DEBUG":
        logs = ["Transport:start"]
        for onset, offset, note, ch, voice_id in play_notes:
            dur = offset - onset
            logs.append(
                f"t+{onset:.2f}s  ch{ch+1}:{_midi_name(note)}  ({voice_id})  dur:{dur:.2f}s"
            )
        logs.append("Transport:stop")
        return logs

    import time
    import mido

    try:
        with mido.open_output(port_name) as out:
            active: list[tuple[float, int, int]] = []
            start = time.time()
            idx = 0
            while idx < len(play_notes) or active:
                now = time.time() - start
                # note_off for expired notes
                still_active = []
                for (off_sec, note, ch) in active:
                    if now >= off_sec:
                        out.send(mido.Message("note_off", note=note, velocity=0, channel=ch))
                    else:
                        still_active.append((off_sec, note, ch))
                active = still_active
                # note_on for notes due now
                while idx < len(play_notes) and play_notes[idx][0] <= now:
                    _, off_sec, note, ch, _ = play_notes[idx]
                    out.send(mido.Message("note_on", note=note, velocity=80, channel=ch))
                    active.append((off_sec, note, ch))
                    idx += 1
                time.sleep(0.02)
        return ["Preview complete."]
    except Exception as exc:
        return [f"MIDI error: {exc}"]


def _run_send(song: SongModel, settings: AppSettings, dest: str) -> None:
    with st.spinner("Generating SysEx..."):
        try:
            syx = _export_syx_bytes(song, settings)
            st.session_state._syx_bytes = syx
            st.session_state._syx_fname = f"{song.title or 'changes'}.syx"
        except ModuleNotFoundError:
            st.error("digitone-syx-toolkit is required: `pip install -e ../digitone-syx-toolkit`")
            return
        except Exception as exc:
            st.error(str(exc))
            return

    syx = st.session_state._syx_bytes
    port_name = "DEBUG" if "DEBUG" in dest else dest

    if port_name != "DEBUG":
        with st.spinner(f"Sending SysEx to {port_name}..."):
            err = _send_syx_via_midi(syx, port_name)
            if err:
                st.error(err)
            else:
                st.success(f"Sent to {port_name}")
    else:
        st.info("Internal (DEBUG) - download only")

    st.download_button(
        "↓ Download .syx",
        data=syx,
        file_name=st.session_state.get("_syx_fname", "changes.syx"),
        mime="application/octet-stream",
        use_container_width=True,
        key="_ps_syx_dl",
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
    _render_header()
    _render_main()
    _render_preview_send()


if __name__ == "__main__":
    main()
