"""Streamlit UI for EUB Changes — Songlist / Compose / Settings."""

from __future__ import annotations

import base64
import functools
import re
from pathlib import Path

import streamlit as st

from changes.app_settings import AppSettings, load_settings, save_settings
from changes.editor import EditorState, editor_to_song_model
from changes.library import SongEntry, delete_song, import_musicxml_bytes, list_songs, overwrite_song, save_song
from changes.models.song_model import SongModel, song_model_to_dict
from changes.ui_pipeline import count_auto_split_patterns, song_to_syx_bytes

# ── Paths ─────────────────────────────────────────────────────────────────────

_ASSETS = Path(__file__).parent.parent.parent / "docs" / "assets" / "1x"
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
**有効なトークン** | トークン | 例 |
|---|---|
| コードシンボル | `Cmaj7` `Bbm7` `F#7` `Eb7b9` `G/B` |
| 直前コード繰り返し | `%` |
| 小節線 | `|` |
| セクション区切り | `||` |

- **Enter** でトークンを確定 / スペース区切りで複数確定可
- **半角のみ** — `b` / `#` を使う（♭/♯ 不可）
- ルートは自動大文字変換: `cmaj7` → `Cmaj7`
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
.common-header { display:flex; align-items:center; gap:24px; background:white; border:1px solid #E2DAE8; border-radius:12px; padding:10px 20px; margin-bottom:16px; flex-wrap:wrap; }
.hdr-item { display:flex; align-items:center; gap:6px; }
.hdr-icon { width:20px; height:20px; }
.hdr-label { font-size:11px; color:#9A8AB0; font-weight:500; margin-right:2px; }
.hdr-val { font-size:14px; color:#2D2840; font-weight:600; }
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

def _hdr_item(label: str, value: str) -> str:
    ico = _icon_b64()
    img = f'<img src="data:image/png;base64,{ico}" class="hdr-icon"/>' if ico else ""
    return f'<span class="hdr-item">{img}<span class="hdr-label">{label}</span><span class="hdr-val">{value}</span></span>'

# ── Session state ─────────────────────────────────────────────────────────────

def _ss_init() -> None:
    if "_page" not in st.session_state:
        st.session_state._page = "Songlist"
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
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def _refresh_library() -> None:
    s = st.session_state.get("_settings") or load_settings()
    from pathlib import Path
    st.session_state._library = list_songs(Path(s.library_path))


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


# ── Common header ─────────────────────────────────────────────────────────────

def _render_header() -> None:
    song = _header_song()
    title = song.title if song else "—"
    key   = (song.working_key or "—") if song else "—"
    tempo = str(int(song.performance_tempo)) if song else "—"
    meter = (f"{song.measures[0].meter_numerator}/{song.measures[0].meter_denominator}"
             if song and song.measures else "—")
    dirty_badge = ' <span style="color:#E07000;font-size:11px;">●</span>' if st.session_state._editor_dirty else ""
    html = (
        f'<div class="common-header">'
        f'{_hdr_item("Song", title + dirty_badge)}'
        f'{_hdr_item("Key", key)}'
        f'{_hdr_item("Tempo", tempo)}'
        f'{_hdr_item("Meter", meter)}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("<div style='padding:20px 16px 8px;text-align:center'>", unsafe_allow_html=True)
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), width=110)
        else:
            st.markdown("### EUB Changes")
        st.markdown("</div>", unsafe_allow_html=True)
        st.divider()

        pages = ["Songlist", "Compose", "Settings"]
        current_idx = pages.index(st.session_state._page) if st.session_state._page in pages else 0
        choice = st.radio("nav", pages, index=current_idx, label_visibility="collapsed")
        if choice != st.session_state._page:
            st.session_state._page = choice
            st.rerun()

        st.markdown(f"<div class='sidebar-version'>{_APP_VERSION}</div>", unsafe_allow_html=True)


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


# ─────────────────────────────────────────────────────────────────────────────
# Page: Songlist
# ─────────────────────────────────────────────────────────────────────────────

def _render_songlist() -> None:
    entries: list[SongEntry] = st.session_state._library

    # ── Dirty warning (switching songs while Compose has unsaved edits) ────────
    pending = st.session_state.get("_pending_switch")
    if pending is not None:
        st.warning(
            f'**Unsaved changes will be discarded.**  Switch to "{pending.title}"?'
        )
        col_cancel, col_discard = st.columns([1, 1])
        if col_cancel.button("Cancel", key="sw_cancel"):
            st.session_state._pending_switch = None
            st.rerun()
        if col_discard.button("Discard and switch", type="primary", key="sw_discard"):
            _do_switch_song(pending)
            st.rerun()
        return

    # ── Delete confirmation ────────────────────────────────────────────────────
    del_path = st.session_state.get("_delete_confirm")
    if del_path is not None:
        entry = next((e for e in entries if e.path == del_path), None)
        name = entry.title if entry else del_path.name
        st.warning(f'**Delete "{name}"?**  This removes the SongModel file.')
        c1, c2 = st.columns([1, 1])
        if c1.button("Cancel", key="del_cancel"):
            st.session_state._delete_confirm = None
            st.rerun()
        if c2.button("Delete", type="primary", key="del_confirm"):
            delete_song(del_path)
            if st.session_state._selected_path == del_path:
                st.session_state._selected_path = None
            st.session_state._delete_confirm = None
            _refresh_library()
            st.rerun()
        return

    # ── Import conflict dialog ─────────────────────────────────────────────────
    if st.session_state.get("_import_conflict_mode") == "pending":
        conflicts = st.session_state.get("_import_conflict_titles", [])
        st.warning(
            f"**Duplicate titles found:** {', '.join(conflicts)}\n\n"
            "How should duplicates be handled?"
        )
        c1, c2, c3 = st.columns(3)
        if c1.button("Overwrite all", type="primary", key="ic_over"):
            st.session_state._import_conflict_mode = "overwrite"
            st.rerun()
        if c2.button("Keep both", key="ic_keep"):
            st.session_state._import_conflict_mode = "keep_both"
            st.rerun()
        if c3.button("Cancel import", key="ic_cancel"):
            st.session_state._import_conflict_mode = None
            st.session_state._import_pending = []
            st.rerun()
        return

    # Process resolved imports
    if st.session_state.get("_import_conflict_mode") in ("overwrite", "keep_both"):
        _do_import(st.session_state._import_conflict_mode)
        st.session_state._import_conflict_mode = None
        st.session_state._import_pending = []
        _refresh_library()
        st.rerun()

    # ── Search ────────────────────────────────────────────────────────────────
    search = st.text_input("Search songs", placeholder="Title…", label_visibility="collapsed", key="_sl_search")
    filtered = [e for e in entries if search.lower() in e.title.lower()] if search else entries

    # ── Song table ────────────────────────────────────────────────────────────
    import pandas as pd

    def _meter(e: SongEntry) -> str:
        if e.song and e.song.measures:
            m = e.song.measures[0]
            return f"{m.meter_numerator}/{m.meter_denominator}"
        return "—"

    # Keep column dtypes stable even when filtered is empty; Streamlit data_editor
    # rejects text column configs if pandas infers float dtype from empty data.
    orig_df = pd.DataFrame({
        "Title": pd.Series([e.title for e in filtered], dtype="string"),
        "Key":   pd.Series([e.song.working_key or "" if e.song else "" for e in filtered], dtype="string"),
        "Tempo": pd.Series([int(e.song.performance_tempo) if e.song else 0 for e in filtered], dtype="Int64"),
        "Meter": pd.Series([_meter(e) for e in filtered], dtype="string"),
        "⚠":    pd.Series(["⚠" if e.error else "" for e in filtered], dtype="string"),
    })

    edited_df = st.data_editor(
        orig_df,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="_sl_table",
        column_config={
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Key":   st.column_config.TextColumn("Key", width="small"),
            "Tempo": st.column_config.NumberColumn("Tempo", disabled=True, width="small"),
            "Meter": st.column_config.TextColumn("Meter", disabled=True, width="small"),
            "⚠":    st.column_config.TextColumn("", disabled=True, width="small"),
        },
    )

    # Persist inline edits (Title / Key)
    for i, entry in enumerate(filtered):
        if entry.song is None:
            continue
        new_title = edited_df.at[i, "Title"] if i < len(edited_df) else entry.title
        new_key   = edited_df.at[i, "Key"]   if i < len(edited_df) else (entry.song.working_key or "")
        if new_title != entry.title or new_key != (entry.song.working_key or ""):
            updated = SongModel(
                title=new_title or entry.song.title,
                working_key=new_key or None,
                performance_tempo=entry.song.performance_tempo,
                measures=entry.song.measures,
            )
            overwrite_song(entry.path, updated)
            _refresh_library()
            st.rerun()

    # ── Row actions ───────────────────────────────────────────────────────────
    st.caption(f"{len(filtered)} song(s)")
    for i, entry in enumerate(filtered):
        c1, c2, c3 = st.columns([6, 1, 1])
        c1.markdown(
            f"{'**→ ' if st.session_state._selected_path == entry.path else ''}"
            f"{entry.title}"
            f"{'** ✓' if st.session_state._selected_path == entry.path else ''}"
        )
        if c2.button("Select", key=f"sl_sel_{i}"):
            _try_select_song(entry)
            st.rerun()
        if c3.button("🗑", key=f"sl_del_{i}", help=f'Delete "{entry.title}"'):
            st.session_state._delete_confirm = entry.path
            st.rerun()

    # ── Import MusicXML ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("Import MusicXML")
    uploaded = st.file_uploader(
        "Upload MusicXML files", type=["musicxml", "xml", "mxl"],
        accept_multiple_files=True, key="_sl_uploader",
    )
    tempo_for_import = st.number_input("Default tempo for imported files", min_value=30, max_value=300, value=120, step=1)
    if uploaded and st.button("Import", type="primary", key="_sl_import_btn"):
        _start_import(uploaded, int(tempo_for_import))
        st.rerun()

    # Show last import result
    result = st.session_state.get("_import_result")
    if result:
        st.info(
            f"**Import completed.**\n\nSuccess: {result['ok']}\nFailed: {len(result['failed'])}"
            + ("\n\n**Failed files:**\n" + "\n".join(f"- {n}: {e}" for n, e in result["failed"]) if result["failed"] else "")
        )


def _try_select_song(entry: SongEntry) -> None:
    if st.session_state._editor_dirty and st.session_state._page == "Songlist":
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


def _start_import(files: list, tempo: int) -> None:
    from changes.library import list_songs
    s = st.session_state._settings
    lib_path = Path(s.library_path)
    existing_titles = {e.title.lower() for e in list_songs(lib_path)}

    pending = []
    failed = []
    for f in files:
        try:
            song = import_musicxml_bytes(f.name, f.read(), tempo=tempo)
            pending.append((f.name, song))
        except Exception as exc:
            failed.append((f.name, str(exc)))

    st.session_state._import_pending = pending
    st.session_state._import_pending_failed = failed

    conflict_titles = [song.title for _, song in pending if song.title.lower() in existing_titles]
    if conflict_titles:
        st.session_state._import_conflict_mode = "pending"
        st.session_state._import_conflict_titles = conflict_titles
    else:
        _do_import("keep_both")
        _refresh_library()
        st.session_state._import_result = {
            "ok": len(pending),
            "failed": failed,
        }


def _do_import(mode: str) -> None:
    pending = st.session_state.get("_import_pending", [])
    failed = list(st.session_state.get("_import_pending_failed", []))
    s = st.session_state._settings
    lib_path = Path(s.library_path)

    ok = 0
    for filename, song in pending:
        try:
            save_song(lib_path, song, mode=mode)
            ok += 1
        except Exception as exc:
            failed.append((filename, str(exc)))

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


# ─────────────────────────────────────────────────────────────────────────────
# Page: Compose
# ─────────────────────────────────────────────────────────────────────────────

def _render_compose() -> None:
    state: EditorState = st.session_state.editor
    s = st.session_state._settings
    lib_path = Path(s.library_path)

    # ── Compose save confirmation dialog ─────────────────────────────────────
    if st.session_state._compose_save_mode == "pending":
        song = st.session_state._compose_save_pending
        selected_path = st.session_state._selected_path
        if selected_path is not None:
            existing_title = next(
                (e.title for e in st.session_state._library if e.path == selected_path),
                selected_path.name,
            )
            st.warning(
                f'**既存の曲 "{existing_title}" を編集しています。どのように保存しますか？**'
            )
        else:
            st.warning(f'**同名の曲 "{song.title}" が既に存在します。どのように保存しますか？**')
        csd1, csd2, csd3 = st.columns(3)
        if csd1.button("更新する", type="primary", key="csd_update"):
            st.session_state._compose_save_mode = "update"
            st.rerun()
        if csd2.button("両方保持する", key="csd_keep"):
            st.session_state._compose_save_mode = "keep_both"
            st.rerun()
        if csd3.button("キャンセル", key="csd_cancel"):
            st.session_state._compose_save_mode = None
            st.session_state._compose_save_pending = None
            st.rerun()
        return

    # Execute resolved Compose save
    if st.session_state._compose_save_mode in ("update", "keep_both"):
        _execute_compose_save(st.session_state._compose_save_mode)
        st.session_state._compose_save_mode = None
        st.session_state._compose_save_pending = None
        st.rerun()

    # ── Row 1: Title / Tempo / Key + transpose ────────────────────────────────
    r1 = st.columns([4, 1, 2, 1, 1])
    with r1[0]:
        title = st.text_input("Title", key="editor_title")
        if title != state.title:
            state.title = title
            st.session_state._editor_dirty = True
    with r1[1]:
        tempo = st.number_input("Tempo", min_value=30, max_value=300, step=1, key="editor_tempo")
        if int(tempo) != state.tempo:
            state.tempo = int(tempo)
            st.session_state._editor_dirty = True
    with r1[2]:
        _KEY_OPTS = ["C","Db","D","Eb","E","F","F#","Gb","G","Ab","A","Bb","B"]
        ki = _KEY_OPTS.index(state.working_key) if state.working_key in _KEY_OPTS else 0
        kv = st.selectbox("Key", _KEY_OPTS, index=ki, key="working_key_input")
        if kv != state.working_key:
            state.working_key = kv
            st.session_state._editor_dirty = True
    with r1[3]:
        st.write("")
        if st.button("△", key="key_up", use_container_width=True, help="半音上"):
            _transpose_state(state, +1); st.session_state._editor_dirty = True; st.rerun()
    with r1[4]:
        st.write("")
        if st.button("▽", key="key_down", use_container_width=True, help="半音下"):
            _transpose_state(state, -1); st.session_state._editor_dirty = True; st.rerun()

    # ── Row 2: Meter ──────────────────────────────────────────────────────────
    r2 = st.columns([1, 1, 1, 1, 1, 2, 3])
    r2[0].write("**Meter**")
    if r2[1].button("−", key="meter_minus", use_container_width=True):
        st.session_state.meter_num = max(1, st.session_state.meter_num - 1)
        st.session_state._editor_dirty = True; st.rerun()
    r2[2].write(f"**{st.session_state.meter_num}**")
    if r2[3].button("+", key="meter_plus", use_container_width=True):
        st.session_state.meter_num += 1
        st.session_state._editor_dirty = True; st.rerun()
    r2[4].write("**/**")
    den_opts = [2, 4, 8]
    den_idx = den_opts.index(st.session_state.meter_den) if st.session_state.meter_den in den_opts else 1
    new_den = r2[5].selectbox("den", den_opts, index=den_idx, key="meter_den_widget", label_visibility="collapsed")
    if new_den != st.session_state.meter_den:
        st.session_state.meter_den = new_den
        st.session_state._editor_dirty = True
    state.meter = f"{st.session_state.meter_num}/{st.session_state.meter_den}"

    # ── Mode toggle ────────────────────────────────────────────────────────────
    mode = st.session_state.editor_mode
    if st.button("テキスト入力に切り替え" if mode == "button" else "ボタン入力に切り替え", key="mode_toggle"):
        st.session_state.editor_mode = "text" if mode == "button" else "button"; st.rerun()

    # ── Cell display ───────────────────────────────────────────────────────────
    st.markdown(f"<div class='chord-cell-display'>{_cell_strip(state)}</div>", unsafe_allow_html=True)

    # ── Input area ─────────────────────────────────────────────────────────────
    def _mark_dirty() -> None:
        st.session_state._editor_dirty = True

    if mode == "text":
        st.text_input("コード入力 — Enter で確定", key="ti", on_change=_process_text_input,
                      placeholder="例: Cmaj7  または  |  または  %")
        with st.expander("入力インストラクション"):
            st.markdown(_TEXT_INSTRUCTIONS)
        sc = st.columns(5)
        if sc[0].button("← 左", key="t_left", use_container_width=True): state.move_left(); st.rerun()
        if sc[1].button("右 →", key="t_right", use_container_width=True): state.move_right(); st.rerun()
        if sc[2].button("Undo", key="t_undo", use_container_width=True): state.undo(); st.rerun()
        if sc[3].button("Delete", key="t_del", use_container_width=True): state.delete(); _mark_dirty(); st.rerun()
        if sc[4].button("Clear", key="t_clear", use_container_width=True): state.clear(); _mark_dirty(); st.rerun()
    else:
        pr = st.session_state.pending_root
        pa = st.session_state.pending_acc
        if pr:
            st.info(f"Pending: **{pr}{pa}** — quality を選択")
        else:
            st.caption("Root → (Accidental) → Quality")
        st.write("**Root**")
        rc = st.columns(len(ROOTS))
        for i, r in enumerate(ROOTS):
            if rc[i].button(r, key=f"root_{r}", use_container_width=True):
                st.session_state.pending_root = r; st.session_state.pending_acc = ""; st.rerun()
        st.write("**Accidental**")
        ac = st.columns([1, 1, 3])
        if ac[0].button("♭", key="acc_b", use_container_width=True): st.session_state.pending_acc = "b"; st.rerun()
        if ac[1].button("♯", key="acc_s", use_container_width=True): st.session_state.pending_acc = "#"; st.rerun()
        ac[2].caption(f"{'♭ (b)' if pa=='b' else '♯ (#)' if pa=='#' else '♮ natural'} selected")
        st.write("**Quality**")
        for row in _QUALITY_ROWS:
            qc = st.columns(len(row))
            for i, (label, suffix) in enumerate(row):
                if qc[i].button(label, key=f"q_{label}", use_container_width=True):
                    if pr:
                        state.insert(f"{pr}{pa}{suffix}")
                        st.session_state.pending_root = None; st.session_state.pending_acc = ""
                        _mark_dirty()
                    else:
                        st.warning("Root を選んでから Quality を押してください")
                    st.rerun()
        st.write("**Structure**")
        s2 = st.columns(8)
        if s2[0].button("|",     key="s_bar",   use_container_width=True): state.insert("|");  _mark_dirty(); st.rerun()
        if s2[1].button("||",    key="s_sec",   use_container_width=True): state.insert("||"); _mark_dirty(); st.rerun()
        if s2[2].button("%",     key="s_rep",   use_container_width=True): state.insert("%");  _mark_dirty(); st.rerun()
        if s2[3].button("←",     key="s_left",  use_container_width=True): state.move_left();  st.rerun()
        if s2[4].button("→",     key="s_right", use_container_width=True): state.move_right(); st.rerun()
        if s2[5].button("Undo",  key="s_undo",  use_container_width=True): state.undo();       st.rerun()
        if s2[6].button("Delete",key="s_del",   use_container_width=True): state.delete(); _mark_dirty(); st.rerun()
        if s2[7].button("Clear", key="s_clear", use_container_width=True): state.clear(); _mark_dirty(); st.rerun()

    # ── Preview ────────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Preview — SongModel")
    if state.cells:
        try:
            song = editor_to_song_model(state)
            lines = [
                f"[{m.section_id}]  m{m.number}:  " +
                "  ".join(f"{h.symbol}({h.duration_quarters}q)" for h in m.harmony)
                for m in song.measures
            ]
            st.code("\n".join(lines), language=None)
            with st.expander("SongModel JSON"):
                st.json(song_model_to_dict(song))
        except ValueError as exc:
            st.warning(f"変換エラー: {exc}")
    else:
        st.caption("No input yet.")

    # ── Save ──────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("💾  Save", type="primary", use_container_width=True, key="compose_save"):
        if not state.cells:
            st.warning("コードを入力してください")
        else:
            try:
                song = editor_to_song_model(state)
                selected_path = st.session_state._selected_path
                existing_titles = {e.title.lower() for e in st.session_state._library}
                needs_dialog = (
                    selected_path is not None
                    or song.title.lower() in existing_titles
                )
                if needs_dialog:
                    st.session_state._compose_save_mode = "pending"
                    st.session_state._compose_save_pending = song
                    st.rerun()
                else:
                    path = save_song(lib_path, song, mode="keep_both")
                    st.session_state._selected_path = path
                    st.session_state._editor_dirty = False
                    _refresh_library()
                    st.success(f"Saved: {path.name}")
            except ValueError as exc:
                st.error(f"変換エラー: {exc}")


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
                st.info("フォルダパスを直接入力してください")

    if changed:
        save_settings(settings)
        st.session_state._settings = settings

    # ── Advanced ──────────────────────────────────────────────────────────────
    st.divider()
    with st.expander("Advanced"):
        song = _playback_song()
        if song:
            adv1, adv2 = st.columns(2)
            with adv1:
                if st.button("Export SYX", type="primary", use_container_width=True, key="_adv_syx"):
                    with st.spinner("SYX生成中…"):
                        try:
                            syx = _export_syx_bytes(song, settings)
                            st.session_state._syx_bytes = syx
                            st.session_state._syx_fname = f"{song.title or 'changes'}.syx"
                            st.success("完了")
                        except ModuleNotFoundError:
                            st.error("digitone-syx-toolkit が必要です:\n`pip install -e ../digitone-syx-toolkit`")
                        except Exception as exc:
                            st.error(str(exc))
                if "_syx_bytes" in st.session_state:
                    st.download_button("↓ Download .syx", data=st.session_state._syx_bytes,
                                       file_name=st.session_state.get("_syx_fname","changes.syx"),
                                       mime="application/octet-stream", use_container_width=True,
                                       key="_adv_syx_dl")
            with adv2:
                if st.button("Dry-run", use_container_width=True, key="_adv_dry"):
                    with st.spinner("解析中…"):
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

def _render_preview_send() -> None:
    song = _playback_song()
    settings: AppSettings = st.session_state._settings

    st.markdown("<div class='send-area'>", unsafe_allow_html=True)
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
    ports = ["Internal (DEBUG)"]
    try:
        import mido
        ports += mido.get_output_names()
    except Exception:
        pass
    dest = st.selectbox("Destination", ports, key="_dest_sel", label_visibility="collapsed")

    ps1, ps2 = st.columns(2)

    # Preview (Realtime MIDI)
    with ps1:
        if st.button("▶  Preview (Realtime MIDI)", use_container_width=True, key="_ps_preview"):
            if not song:
                st.warning("曲がありません")
            else:
                _run_preview(song, settings, dest)

    # Send SysEx
    with ps2:
        if st.button("⬆  Send SysEx (Digitone)", type="primary", use_container_width=True, key="_ps_send"):
            if not song:
                st.warning("曲がありません")
            elif settings.confirm_before_hardware_write:
                st.session_state._send_confirm = True
                st.rerun()
            else:
                _run_send(song, settings, dest)

    # Hardware write confirmation
    if st.session_state.get("_send_confirm"):
        st.warning("**Send SysEx to Digitone II?**")
        cc1, cc2 = st.columns(2)
        if cc1.button("Cancel", key="_send_conf_cancel"):
            st.session_state._send_confirm = False; st.rerun()
        if cc2.button("Send", type="primary", key="_send_conf_ok"):
            st.session_state._send_confirm = False
            if song:
                _run_send(song, settings, dest)

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
        st.warning("ルーティングされたノートがありません（全voiceがNone？）")
        return

    play_notes.sort(key=lambda n: n[0])
    port_name = "DEBUG" if "DEBUG" in dest else dest

    with st.spinner("Preview中…"):
        try:
            logs = _send_pipeline_preview(play_notes, port_name)
            if port_name == "DEBUG" or logs:
                st.code("\n".join(logs[:60]), language="text")
        except Exception as exc:
            st.error(str(exc))


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
    with st.spinner("SysEx生成中…"):
        try:
            syx = _export_syx_bytes(song, settings)
            st.session_state._syx_bytes = syx
            st.session_state._syx_fname = f"{song.title or 'changes'}.syx"
        except ModuleNotFoundError:
            st.error("digitone-syx-toolkit が必要です: `pip install -e ../digitone-syx-toolkit`")
            return
        except Exception as exc:
            st.error(str(exc))
            return

    syx = st.session_state._syx_bytes
    port_name = "DEBUG" if "DEBUG" in dest else dest

    if port_name != "DEBUG":
        with st.spinner(f"SysEx送信中 → {port_name}…"):
            err = _send_syx_via_midi(syx, port_name)
            if err:
                st.error(err)
            else:
                st.success(f"Sent to {port_name}")
    else:
        st.info("Internal (DEBUG) — ダウンロードのみ")

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
        return "mido がインストールされていません"

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
        return "SysExメッセージが見つかりませんでした"

    try:
        with mido.open_output(port_name) as out:
            for data in messages:
                out.send(mido.Message("sysex", data=data))
                time.sleep(0.05)
        return None
    except Exception as exc:
        return f"MIDI送信エラー: {exc}"


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
    _render_sidebar()
    _render_header()

    page = st.session_state._page
    if page == "Songlist":
        _render_songlist()
    elif page == "Compose":
        _render_compose()
    else:
        _render_settings()

    _render_preview_send()


if __name__ == "__main__":
    main()
