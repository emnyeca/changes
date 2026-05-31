"""Streamlit UI for EUB Changes — Songlist / Compose / Settings."""

from __future__ import annotations

import base64
import functools
import os
import re
import tempfile
from pathlib import Path

import streamlit as st
import yaml

from changes.app_settings import AppSettings, load_settings, save_settings
from changes.editor import EditorState, editor_to_song_model
from changes.library import delete_song, import_musicxml_bytes, list_songs, overwrite_song, save_song, SongEntry
from changes.models.render_profile import RenderProfile
from changes.models.song_model import SongModel, song_model_to_dict

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

# ── Render profile builder ────────────────────────────────────────────────────

def _settings_to_render_profile(s: AppSettings) -> RenderProfile:
    cc = s.cloud_center_midi
    bc = s.bass_center_midi
    ch = s.chord_center_midi
    return RenderProfile(
        name="ui_custom",
        voices=6,
        voice_leading_strategy="minimum_motion",
        bass_enabled=True,
        bass_strategy="slash_or_root_in_window",
        cloud_trigger_policy=s.cloud_trigger_policy,
        bass_trigger_policy=s.bass_trigger_policy,
        chord_trigger_policy=s.chord_trigger_policy,
        cloud_min_midi=cc - 12,
        cloud_max_midi=cc + 12,
        chord_min_midi=ch - 12,
        chord_max_midi=ch + 12,
        bass_min_midi=bc,
        bass_max_midi=bc + 11,
    )

# ── SongModel → playback data ─────────────────────────────────────────────────

def _song_to_bars(song: SongModel) -> tuple[list[list[str]], list[dict]]:
    """Extract chord_bars and bar_meta from a SongModel."""
    bars: list[list[str]] = []
    meta: list[dict] = []
    for m in song.measures:
        symbols = [h.symbol for h in m.harmony]
        if symbols:
            bars.append(symbols)
            label = m.section_id.split("__OCC")[0] if m.section_id else "A"
            meta.append({"section": label, "bar_in_section": m.number})
    return bars, meta

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


# ── SYX export helper ─────────────────────────────────────────────────────────

def _export_syx_bytes(song: SongModel, settings: AppSettings) -> bytes:
    from changes.rendering.arrangement_renderer import render_arrangement
    from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
    from changes.digitone.planner import compile_timeline_to_digitone_plan
    from changes.exporters.digitone_events import digitone_compile_plan_to_events_yaml_payload
    from changes.models.digitone_target_profile import default_digitone_target_profile
    from changes.digitone_backend import build_digitone_syx_from_events_yaml

    rp = _settings_to_render_profile(settings)
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


def _count_patterns(song: SongModel, settings: AppSettings) -> int:
    try:
        from changes.rendering.arrangement_renderer import render_arrangement
        from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
        from changes.digitone.bundle_planner import compile_timeline_to_digitone_bundle_plan
        from changes.models.digitone_target_profile import default_digitone_target_profile
        rp = _settings_to_render_profile(settings)
        tp = default_digitone_target_profile()
        arrangement = render_arrangement(song, rp)
        timeline = flatten_arrangement_to_timeline(arrangement, render_profile=rp)
        bundle_plan = compile_timeline_to_digitone_bundle_plan(song, timeline, tp)
        return len(bundle_plan.patterns)
    except Exception:
        return 1


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

    orig_df = pd.DataFrame({
        "Title": [e.title for e in filtered],
        "Key":   [e.song.working_key or "" if e.song else "" for e in filtered],
        "Tempo": [int(e.song.performance_tempo) if e.song else 0 for e in filtered],
        "Meter": [_meter(e) for e in filtered],
        "⚠":    ["⚠" if e.error else "" for e in filtered],
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
    from changes.library import SongEntry, list_songs
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
            if mode == "overwrite":
                save_song(lib_path, song)
            else:
                save_song(lib_path, song)
            ok += 1
        except Exception as exc:
            failed.append((filename, str(exc)))

    st.session_state._import_result = {"ok": ok, "failed": failed}


# ─────────────────────────────────────────────────────────────────────────────
# Page: Compose
# ─────────────────────────────────────────────────────────────────────────────

def _render_compose() -> None:
    state: EditorState = st.session_state.editor
    s = st.session_state._settings
    lib_path = Path(s.library_path)

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
        if state.cells:
            try:
                song = editor_to_song_model(state)
                path = save_song(lib_path, song)
                st.session_state._selected_path = path
                st.session_state._editor_dirty = False
                _refresh_library()
                st.success(f"Saved: {path.name}")
            except ValueError as exc:
                st.error(f"変換エラー: {exc}")
        else:
            st.warning("コードを入力してください")


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
        st.markdown(f"**Range:** `{_range_display(settings.cloud_center_midi, 12, 11)}`")
        st.caption(f"Voices 1-6 → Tracks {settings.cloud_track_base}–{settings.cloud_track_base+5}")
    new_cloud_base = st.number_input("Track base (voice 1 → this track)", min_value=1, max_value=3,
                                      value=settings.cloud_track_base, step=1, key="_s_cloud_base")
    if int(new_cloud_base) != settings.cloud_track_base:
        settings.cloud_track_base = int(new_cloud_base); changed = True

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
    new_bass_track = bt1.number_input("Track", min_value=1, max_value=16,
                                       value=settings.bass_track, step=1, key="_s_bass_track")
    if int(new_bass_track) != settings.bass_track:
        settings.bass_track = int(new_bass_track); changed = True

    st.write("**Bass playback options**")
    new_sw_en = st.checkbox("Switch root/fifth (switch_enabled)", value=settings.bass_switch_enabled,
                             key="_s_bass_sw_en")
    if new_sw_en != settings.bass_switch_enabled:
        settings.bass_switch_enabled = new_sw_en; changed = True
    if settings.bass_switch_enabled:
        new_sw_every = st.number_input(
            "Switch after N same notes (switch_every)", min_value=1, max_value=32,
            value=settings.bass_switch_every, step=1, key="_s_bass_sw_ev"
        )
        if int(new_sw_every) != settings.bass_switch_every:
            settings.bass_switch_every = int(new_sw_every); changed = True

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
        st.markdown(f"**Range:** `{_range_display(settings.chord_center_midi, 12, 11)}`")
    new_chord_track = st.number_input("Track", min_value=1, max_value=16,
                                       value=settings.chord_track, step=1, key="_s_chord_track")
    if int(new_chord_track) != settings.chord_track:
        settings.chord_track = int(new_chord_track); changed = True

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
    new_lib_path = st.text_input("Library folder", value=settings.library_path, key="_s_lib_path")
    if new_lib_path != settings.library_path:
        settings.library_path = new_lib_path; changed = True
        _refresh_library()

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
                            from changes.rendering.arrangement_renderer import render_arrangement
                            from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
                            from changes.digitone.bundle_planner import compile_timeline_to_digitone_bundle_plan
                            from changes.models.digitone_target_profile import default_digitone_target_profile
                            rp = _settings_to_render_profile(settings)
                            tp = default_digitone_target_profile()
                            arrangement = render_arrangement(song, rp)
                            timeline = flatten_arrangement_to_timeline(arrangement, render_profile=rp)
                            bp = compile_timeline_to_digitone_bundle_plan(song, timeline, tp)
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
                _run_send(song, settings)

    # Hardware write confirmation
    if st.session_state.get("_send_confirm"):
        st.warning("**Send SysEx to Digitone II?**")
        cc1, cc2 = st.columns(2)
        if cc1.button("Cancel", key="_send_conf_cancel"):
            st.session_state._send_confirm = False; st.rerun()
        if cc2.button("Send", type="primary", key="_send_conf_ok"):
            st.session_state._send_confirm = False
            if song:
                _run_send(song, settings)

    st.markdown("</div>", unsafe_allow_html=True)


def _run_preview(song: SongModel, settings: AppSettings, dest: str) -> None:
    from math import lcm
    from changes.voicing import progression_to_voicings
    from changes.voice_leading import generate_voice_leading

    bars, _ = _song_to_bars(song)
    if not bars:
        st.warning("再生可能なコードがありません"); return

    raw_voicings = progression_to_voicings(bars)
    voicings = generate_voice_leading(raw_voicings)

    event_counts = [len(b) for b in bars if b]
    steps_per_bar = 1
    for cnt in event_counts:
        steps_per_bar = lcm(steps_per_bar, cnt)

    events = []
    for bi, bar in enumerate(bars):
        dur = steps_per_bar // len(bar)
        bar_start = bi * steps_per_bar + 1
        for ci, chord in enumerate(bar):
            events.append({"step": bar_start + ci*dur, "duration_steps": dur, "chord": chord})

    bass_notes: list[int] = []
    for ev in events:
        chord_str = str(ev["chord"])
        root_str = chord_str.split("/")[-1] if "/" in chord_str else chord_str
        m = re.match(r"^([A-G][#b]?)", root_str)
        root_name = m.group(1) if m else "C"
        pc = _ROOT_PC.get(root_name, 0)
        b = settings.bass_center_midi + ((pc - settings.bass_center_midi % 12) % 12)
        while b < settings.bass_center_midi:
            b += 12
        while b > settings.bass_center_midi + 11:
            b -= 12
        bass_notes.append(b)

    # Channel map: cloud → 1..6, bass → 7
    n_voices = max(len(v) for v in voicings) if voicings else 0
    channel_map = list(range(1, min(n_voices, 6) + 1)) + [settings.bass_track]
    out_voicings = [list(v) + [bass_notes[i]] for i, v in enumerate(voicings[:len(events)])]

    port_name = "DEBUG" if "DEBUG" in dest else dest

    with st.spinner("Preview中…"):
        try:
            logs = _send_preview_impl(out_voicings, events, int(song.performance_tempo),
                                      port_name, channel_map)
            if port_name == "DEBUG" or logs:
                st.code("\n".join(logs[:30]), language="text")
        except Exception as exc:
            st.error(str(exc))


def _send_preview_impl(voicings, events, tempo, port_name, channel_map) -> list[str]:
    step_seconds = 60.0 / float(tempo)
    logs: list[str] = []
    count = min(len(events), len(voicings))

    if port_name == "DEBUG":
        logs.append("Transport:start")
        elapsed = 0.0
        for i in range(count):
            ev = events[i]
            notes = voicings[i]
            parts = [f"ch{channel_map[vi] if vi < len(channel_map) else vi+1}:{_midi_name(int(n))}" for vi, n in enumerate(notes)]
            dur = step_seconds * int(ev["duration_steps"])
            logs.append(f"t+{elapsed:.2f}s chord:{ev['chord']} [{' '.join(parts)}] dur:{dur:.2f}s")
            elapsed += dur
        logs.append("Transport:stop")
        return logs

    try:
        import time
        import mido
        with mido.open_output(port_name) as out:
            out.send(mido.Message("start"))
            prev = None
            try:
                for i in range(count):
                    ev = events[i]
                    notes = voicings[i]
                    for vi, note in enumerate(notes):
                        ch = (channel_map[vi] if vi < len(channel_map) else 1) - 1
                        if prev is not None and vi < len(prev) and int(prev[vi]) == int(note):
                            continue
                        out.send(mido.Message("note_on", note=int(note), velocity=80, channel=ch))
                    time.sleep(step_seconds * int(ev["duration_steps"]))
                    for vi, note in enumerate(notes):
                        ch = (channel_map[vi] if vi < len(channel_map) else 1) - 1
                        out.send(mido.Message("note_off", note=int(note), velocity=0, channel=ch))
                    prev = notes
            finally:
                out.send(mido.Message("stop"))
        return ["Preview sent."]
    except Exception as exc:
        return [f"MIDI error: {exc}"]


def _run_send(song: SongModel, settings: AppSettings) -> None:
    with st.spinner("SysEx生成中…"):
        try:
            syx = _export_syx_bytes(song, settings)
            st.session_state._syx_bytes = syx
            st.session_state._syx_fname = f"{song.title or 'changes'}.syx"
            st.success("SysEx ready for download")
        except ModuleNotFoundError:
            st.error("digitone-syx-toolkit が必要です: `pip install -e ../digitone-syx-toolkit`")
        except Exception as exc:
            st.error(str(exc))
    if "_syx_bytes" in st.session_state:
        st.download_button(
            "↓ Download .syx",
            data=st.session_state._syx_bytes,
            file_name=st.session_state.get("_syx_fname", "changes.syx"),
            mime="application/octet-stream",
            use_container_width=True,
            key="_ps_syx_dl",
        )


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
