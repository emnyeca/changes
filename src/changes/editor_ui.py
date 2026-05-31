"""Streamlit Editor UI for EUB Changes chord progression input."""

from __future__ import annotations

import streamlit as st

from changes.editor import EditorState, editor_to_song_model
from changes.models.song_model import song_model_to_dict

ROOTS = list("CDEFGAB")

# (display_label, quality_suffix)
_QUALITY_ROWS: list[list[tuple[str, str]]] = [
    [
        ("maj", ""),
        ("m", "m"),
        ("dim", "dim"),
        ("aug", "aug"),
        ("sus2", "sus2"),
        ("sus4", "sus4"),
    ],
    [
        ("maj7", "maj7"),
        ("m7", "m7"),
        ("7", "7"),
        ("m7b5", "m7b5"),
        ("dim7", "dim7"),
        ("m6", "m6"),
        ("6", "6"),
        ("alt", "alt"),
    ],
    [
        ("maj9", "maj9"),
        ("m9", "m9"),
        ("9", "9"),
        ("13", "13"),
        ("7b9", "7b9"),
        ("7#9", "7#9"),
        ("7#11", "7#11"),
        ("7b13", "7b13"),
        ("add9", "add9"),
    ],
]


def _init_state() -> None:
    if "editor" not in st.session_state:
        st.session_state.editor = EditorState()
    # Metadata keys (Streamlit manages these through widget key mechanism)
    if "editor_title" not in st.session_state:
        st.session_state.editor_title = st.session_state.editor.title
    if "editor_tempo" not in st.session_state:
        st.session_state.editor_tempo = st.session_state.editor.tempo
    if "editor_meter" not in st.session_state:
        st.session_state.editor_meter = st.session_state.editor.meter
    # Pending chord builder
    if "pending_root" not in st.session_state:
        st.session_state.pending_root = None
    if "pending_acc" not in st.session_state:
        st.session_state.pending_acc = ""


def _cell_strip(state: EditorState) -> str:
    """Render cells as a text line with ▸ at cursor position."""
    parts: list[str] = []
    for i, cell in enumerate(state.cells):
        if i == state.cursor:
            parts.append("▸")
        parts.append(cell)
    if state.cursor == len(state.cells):
        parts.append("▸")
    return " ".join(parts) if parts else "▸  (empty)"


def main() -> None:
    st.set_page_config(page_title="Changes — Editor", layout="wide")
    _init_state()

    state: EditorState = st.session_state.editor

    st.title("Changes — Editor")

    # ── Metadata ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        title = st.text_input("Title", key="editor_title")
        state.title = title
    with col2:
        tempo = st.number_input("Tempo", min_value=40, max_value=300, step=1, key="editor_tempo")
        state.tempo = int(tempo)
    with col3:
        meter = st.text_input("Meter", key="editor_meter")
        state.meter = meter

    # ── Cell display ──────────────────────────────────────────────────────────
    st.code(_cell_strip(state), language=None)

    # Pending chord indicator
    pr = st.session_state.pending_root
    pa = st.session_state.pending_acc
    if pr:
        st.info(f"Pending: **{pr}{pa}** — select quality to insert")
    else:
        st.caption("Root → (accidental) → quality")

    # ── Root row ──────────────────────────────────────────────────────────────
    st.write("**Root**")
    root_cols = st.columns(len(ROOTS))
    for i, r in enumerate(ROOTS):
        if root_cols[i].button(r, key=f"root_{r}", use_container_width=True):
            st.session_state.pending_root = r
            st.session_state.pending_acc = ""
            st.rerun()

    # ── Accidental row ────────────────────────────────────────────────────────
    st.write("**Accidental**")
    acc_cols = st.columns([1, 1, 3])
    if acc_cols[0].button("♭", key="acc_b", use_container_width=True):
        st.session_state.pending_acc = "b"
        st.rerun()
    if acc_cols[1].button("♯", key="acc_s", use_container_width=True):
        st.session_state.pending_acc = "#"
        st.rerun()
    acc_cols[2].caption(f"{'♭ (b)' if pa == 'b' else '♯ (#)' if pa == '#' else '♮ natural'} selected")

    # ── Quality rows ──────────────────────────────────────────────────────────
    st.write("**Quality**")
    for row in _QUALITY_ROWS:
        q_cols = st.columns(len(row))
        for i, (label, suffix) in enumerate(row):
            if q_cols[i].button(label, key=f"q_{label}", use_container_width=True):
                if st.session_state.pending_root:
                    chord = f"{st.session_state.pending_root}{st.session_state.pending_acc}{suffix}"
                    state.insert(chord)
                    st.session_state.pending_root = None
                    st.session_state.pending_acc = ""
                else:
                    st.warning("Root を選んでから Quality を押してください")
                st.rerun()

    # ── Structure row ─────────────────────────────────────────────────────────
    st.write("**Structure**")
    s = st.columns(8)
    if s[0].button("|", key="s_bar", use_container_width=True):
        state.insert("|"); st.rerun()
    if s[1].button("||", key="s_sec", use_container_width=True):
        state.insert("||"); st.rerun()
    if s[2].button("%", key="s_rep", use_container_width=True):
        state.insert("%"); st.rerun()
    if s[3].button("←", key="s_left", use_container_width=True):
        state.move_left(); st.rerun()
    if s[4].button("→", key="s_right", use_container_width=True):
        state.move_right(); st.rerun()
    if s[5].button("Undo", key="s_undo", use_container_width=True):
        state.undo(); st.rerun()
    if s[6].button("Delete", key="s_del", use_container_width=True):
        state.delete(); st.rerun()
    if s[7].button("Clear", key="s_clear", use_container_width=True):
        state.clear(); st.rerun()

    # ── Preview ───────────────────────────────────────────────────────────────
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


if __name__ == "__main__":
    main()
