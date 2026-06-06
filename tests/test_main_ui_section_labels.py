import pytest
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

pytest.importorskip("streamlit")

from changes import main_ui
from changes.app_settings import AppSettings
from changes.editor import EditorState
from changes.exporters import digitone_events
from changes.importers.compact_progression import compact_progression_to_song_model
from changes.library import SongEntry
from changes.models.song_model import HarmonyEvent, Measure, SongModel


@pytest.mark.parametrize(
    ("section_id", "expected"),
    [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("Coda1", "CODA1"),
        ("coda2", "CODA2"),
        ("A__OCC1", "A1"),
        ("A__OCC2", "A2"),
        ("Intro__OCC1", "Intro"),
        ("Intro__OCC2", "Intro2"),
    ],
)
def test_section_filter_label_matches_chord_display_label(section_id: str, expected: str) -> None:
    assert main_ui._display_section_label(section_id) == expected
    assert main_ui._section_filter_label(section_id) == expected


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def _measure(
    number: int,
    symbol: str,
    *,
    meter: tuple[int, int] = (4, 4),
    section_id: str | None = None,
) -> Measure:
    numerator, denominator = meter
    length = Fraction(4 * numerator, denominator)
    return Measure(
        number=number,
        section_id=section_id,
        meter_numerator=numerator,
        meter_denominator=denominator,
        absolute_start_quarters=Fraction(0),
        harmony=(
            HarmonyEvent(
                id=f"m{number}_h1",
                symbol=symbol,
                measure_number=number,
                offset_quarters=Fraction(0),
                duration_quarters=length,
            ),
        ),
    )


def _song(*measures: Measure) -> SongModel:
    return SongModel(
        title="Meter UI",
        working_key=None,
        performance_tempo=Fraction(120),
        measures=tuple(measures),
    )


def test_dry_run_result_includes_pattern_change_basis(monkeypatch) -> None:
    monkeypatch.delattr(digitone_events, "pattern_change_basis_payload")
    song = compact_progression_to_song_model(
        {
            "name": "Dry Run",
            "tempo": 120,
            "time_signature": "4/4",
            "sections": [{"name": "A", "progression": [["Cmaj7", "Dm7", "G7", "Cmaj7"]]}],
        }
    )
    monkeypatch.setattr(main_ui.st, "session_state", _SessionState({}))

    result = main_ui._build_dry_run_result(song, song, AppSettings())

    assert result["pattern_change_policy"] == "auto_song_mode"
    assert result["pattern_change"] == 32
    assert result["pattern_change_basis"] == {
        "generated_tracks": "1..8",
        "length": 4,
        "speed": "1/8",
    }


def test_playback_song_uses_selected_song_before_dirty_editor_regenerates_sections(monkeypatch, tmp_path) -> None:
    selected_path = tmp_path / "A Night In Tunisia.song.json"
    selected_song = SongModel(title="A Night In Tunisia", working_key="D", performance_tempo=120, measures=())
    monkeypatch.setattr(
        main_ui.st,
        "session_state",
        _SessionState(
            {
                "_selected_path": selected_path,
                "_library": [
                    SongEntry(path=selected_path, title=selected_song.title, song=selected_song),
                ],
                "_editor_dirty": False,
            }
        ),
    )
    monkeypatch.setattr(main_ui, "_dirty_song", lambda: SongModel(title="Regenerated", working_key=None, performance_tempo=120, measures=()))

    assert main_ui._playback_song() is selected_song


def test_run_send_respects_bundle_by_section(monkeypatch) -> None:
    calls: list[str] = []
    song = SongModel(title="Song", working_key="C", performance_tempo=120, measures=())

    monkeypatch.setattr(main_ui, "_run_send_bundle_by_section", lambda *_args: calls.append("bundle"))
    monkeypatch.setattr(main_ui, "_run_send_linear_split", lambda *_args: calls.append("linear"))

    main_ui._run_send(song, object(), "DEBUG", main_ui._SEND_MODE_BUNDLE)
    main_ui._run_send(song, object(), "DEBUG", main_ui._SEND_MODE_LINEAR)
    main_ui._run_send(song, object(), "DEBUG", f"{main_ui._ICON_BUNDLE} Bundle by Section")

    assert calls == ["bundle", "linear", "bundle"]


def test_send_mode_label_keeps_plain_internal_value() -> None:
    assert main_ui._send_mode_label(main_ui._SEND_MODE_LINEAR).endswith(main_ui._SEND_MODE_LINEAR)
    assert main_ui._send_mode_label(main_ui._SEND_MODE_BUNDLE).endswith(main_ui._SEND_MODE_BUNDLE)
    assert main_ui._normalize_send_mode(f"{main_ui._ICON_BUNDLE} Bundle by Section") == main_ui._SEND_MODE_BUNDLE


def test_request_rerun_can_reset_song_table_without_clearing_search(monkeypatch) -> None:
    state = _SessionState({"_sl_search": "bilbao", "_songlist_table_reset_token": 4})
    monkeypatch.setattr(main_ui.st, "session_state", state)
    monkeypatch.setattr(main_ui.st, "rerun", lambda: (_ for _ in ()).throw(RuntimeError("rerun")))

    with pytest.raises(RuntimeError, match="rerun"):
        main_ui._request_rerun(reset_song_table=True, clear_song_search=False)

    assert state["_sl_search"] == "bilbao"
    assert state["_songlist_table_reset_token"] == 5
    assert state["_last_rerun_request"]["reset_song_table"] is True


def test_request_rerun_can_clear_song_search(monkeypatch) -> None:
    state = _SessionState({"_sl_search": "bilbao", "_songlist_table_reset_token": 4})
    monkeypatch.setattr(main_ui.st, "session_state", state)
    monkeypatch.setattr(main_ui.st, "rerun", lambda: (_ for _ in ()).throw(RuntimeError("rerun")))

    with pytest.raises(RuntimeError, match="rerun"):
        main_ui._request_rerun(reset_song_table=True, clear_song_search=True)

    assert state["_sl_search"] == ""
    assert state["_songlist_table_reset_token"] == 5


def test_request_rerun_stores_visible_settings_reason_only_when_passed(monkeypatch) -> None:
    state = _SessionState({"_songlist_table_reset_token": 0})
    monkeypatch.setattr(main_ui.st, "session_state", state)
    monkeypatch.setattr(main_ui.st, "rerun", lambda: (_ for _ in ()).throw(RuntimeError("rerun")))

    with pytest.raises(RuntimeError, match="rerun"):
        main_ui._request_rerun()
    assert "_last_rerun_reason" not in state

    with pytest.raises(RuntimeError, match="rerun"):
        main_ui._request_rerun(reason="visible_settings_changed")
    assert state["_last_rerun_reason"] == "visible_settings_changed"


def test_request_rerun_carries_success_message_until_rendered(monkeypatch) -> None:
    state = _SessionState({"_songlist_table_reset_token": 0})
    messages: list[str] = []
    monkeypatch.setattr(main_ui.st, "session_state", state)
    monkeypatch.setattr(main_ui.st, "rerun", lambda: (_ for _ in ()).throw(RuntimeError("rerun")))
    monkeypatch.setattr(main_ui.st, "success", lambda msg: messages.append(str(msg)))
    monkeypatch.setattr(main_ui.st, "error", lambda msg: None)

    with pytest.raises(RuntimeError, match="rerun"):
        main_ui._request_rerun(success_message="Saved.")

    assert state["_ui_success_message"] == "Saved."
    main_ui._render_pending_ui_messages()
    assert messages == ["Saved."]
    assert "_ui_success_message" not in state


def test_no_explicit_rerun_marker(monkeypatch) -> None:
    state = _SessionState({})
    monkeypatch.setattr(main_ui.st, "session_state", state)

    main_ui._no_explicit_rerun("preview_result_rendered_in_current_run")

    assert state["_last_no_explicit_rerun_reason"] == "preview_result_rendered_in_current_run"


def test_fixed_status_slot_renders_even_when_empty(monkeypatch) -> None:
    rendered: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        main_ui.st,
        "markdown",
        lambda body, unsafe_allow_html=False: rendered.append((str(body), bool(unsafe_allow_html))),
    )

    main_ui._render_fixed_status_slot(None, kind="warning")

    assert len(rendered) == 1
    assert "eub-fixed-status-warning" in rendered[0][0]
    assert "eub-fixed-status-hidden" in rendered[0][0]
    assert rendered[0][1] is True


def test_fixed_status_slot_escapes_html(monkeypatch) -> None:
    rendered: list[str] = []
    monkeypatch.setattr(
        main_ui.st,
        "markdown",
        lambda body, unsafe_allow_html=False: rendered.append(str(body)),
    )

    main_ui._render_fixed_status_slot("<b>danger</b>", kind="error")

    assert "&lt;b&gt;danger&lt;/b&gt;" in rendered[0]
    assert "<b>danger</b>" not in rendered[0]
    assert "eub-fixed-status-error" in rendered[0]


def test_hardware_write_warning_message_tracks_confirm_setting() -> None:
    settings = AppSettings(confirm_before_hardware_write=True)
    assert main_ui._hardware_write_warning(settings) is None

    settings.confirm_before_hardware_write = False
    assert main_ui._hardware_write_warning(settings) == (
        "Hardware write confirmation is disabled. SysEx will be sent immediately."
    )


def test_header_meter_summary_keeps_first_seen_order_without_duplicates() -> None:
    song = _song(
        _measure(1, "Cmaj7", meter=(4, 4)),
        _measure(2, "Dm7", meter=(4, 4)),
        _measure(3, "Fmaj7", meter=(3, 4)),
        _measure(4, "G7", meter=(3, 4)),
        _measure(5, "Cmaj7", meter=(4, 4)),
    )

    assert main_ui._song_meter_summary(song) == "4/4, 3/4"


def test_header_meter_summary_keeps_6_8_before_4_4() -> None:
    song = _song(
        _measure(1, "Dmaj7", meter=(6, 8)),
        _measure(2, "C#m7", meter=(6, 8)),
        _measure(3, "Em7", meter=(4, 4)),
    )

    assert main_ui._song_meter_summary(song) == "6/8, 4/4"


def test_chord_display_initial_meter_with_section_label(monkeypatch) -> None:
    monkeypatch.setattr(main_ui.st, "session_state", _SessionState({"_editor_section_labels": {"initial": "A1"}}))
    state = EditorState(cells=["Cmaj7", "|"], cursor=2)
    song = _song(_measure(1, "Cmaj7", meter=(4, 4), section_id="A1"))

    html = main_ui._chord_display_html(state, song)

    assert '<mark class="section-lbl">A1</mark><mark class="meter-lbl">4/4</mark>||' in html


def test_chord_display_meter_change_with_section_label_order(monkeypatch) -> None:
    monkeypatch.setattr(
        main_ui.st,
        "session_state",
        _SessionState({"_editor_section_labels": {"initial": "A1", 4: "B1"}}),
    )
    state = EditorState(cells=["Cmaj7", "|", "Dm7", "G7", "||", "Cmaj7", "Am7", "|"], cursor=8)
    song = _song(
        _measure(1, "Cmaj7", meter=(4, 4), section_id="A1"),
        _measure(2, "Dm7", meter=(4, 4), section_id="A1"),
        _measure(3, "Cmaj7", meter=(3, 4), section_id="B1"),
    )

    html = main_ui._chord_display_html(state, song)

    assert '<mark class="section-lbl">A1</mark><mark class="meter-lbl">4/4</mark>||' in html
    assert '<mark class="section-lbl">B1</mark><mark class="meter-lbl">3/4</mark>||' in html


def test_chord_display_meter_only_change_before_single_barline(monkeypatch) -> None:
    monkeypatch.setattr(main_ui.st, "session_state", _SessionState({"_editor_section_labels": {}}))
    state = EditorState(cells=["Fmaj7", "|", "Fmaj7", "|", "G7", "|"], cursor=6)
    song = _song(
        _measure(1, "Fmaj7", meter=(4, 4)),
        _measure(2, "Fmaj7", meter=(3, 4)),
        _measure(3, "G7", meter=(3, 4)),
    )

    html = main_ui._chord_display_html(state, song)

    assert '<mark class="meter-lbl">3/4</mark>|' in html


def test_chord_display_missing_barline_mapping_does_not_crash(monkeypatch) -> None:
    monkeypatch.setattr(main_ui.st, "session_state", _SessionState({"_editor_section_labels": {}}))
    state = EditorState(cells=["Cmaj7", "|"], cursor=2)
    song = _song(
        _measure(1, "Cmaj7", meter=(4, 4)),
        _measure(2, "Dm7", meter=(3, 4)),
        _measure(3, "G7", meter=(4, 4)),
    )

    html = main_ui._chord_display_html(state, song)

    assert '<mark class="meter-lbl">4/4</mark>||' in html
    assert '<mark class="meter-lbl">3/4</mark>|' in html


def test_songlist_meter_column_uses_summary_and_is_read_only(monkeypatch) -> None:
    song = _song(
        _measure(1, "Cmaj7", meter=(4, 4)),
        _measure(2, "Dm7", meter=(3, 4)),
        _measure(3, "G7", meter=(4, 4)),
    )
    monkeypatch.setattr(
        main_ui.st,
        "session_state",
        _SessionState(
            {
                "_library": [SongEntry(path=Path("song.song.json"), title="Song", song=song)],
                "_selected_path": None,
                "_songlist_table_reset_token": 0,
            }
        ),
    )
    monkeypatch.setattr(main_ui.st, "text_input", lambda *args, **kwargs: "")
    captured: dict[str, object] = {}

    def _data_editor(df, *args, **kwargs):
        captured["df"] = df.copy()
        captured["disabled"] = kwargs.get("disabled")
        return df

    monkeypatch.setattr(main_ui.st, "data_editor", _data_editor)
    monkeypatch.setattr(
        main_ui.st,
        "column_config",
        SimpleNamespace(
            CheckboxColumn=lambda *args, **kwargs: object(),
            TextColumn=lambda *args, **kwargs: object(),
            NumberColumn=lambda *args, **kwargs: object(),
        ),
    )

    main_ui._render_songlist(show_import=False)

    assert captured["disabled"] == ["Meter"]
    assert list(captured["df"]["Meter"]) == ["4/4, 3/4"]
