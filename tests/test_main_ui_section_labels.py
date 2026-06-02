import pytest

pytest.importorskip("streamlit")

from changes import main_ui
from changes.library import SongEntry
from changes.models.song_model import SongModel


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


def test_run_send_for_mode_respects_bundle_by_section(monkeypatch) -> None:
    calls: list[str] = []
    song = SongModel(title="Song", working_key="C", performance_tempo=120, measures=())

    monkeypatch.setattr(main_ui, "_run_send_bundle_by_section", lambda *_args: calls.append("bundle"))
    monkeypatch.setattr(main_ui, "_run_send", lambda *_args: calls.append("linear"))

    main_ui._run_send_for_mode(song, object(), "DEBUG", "Bundle by Section")
    main_ui._run_send_for_mode(song, object(), "DEBUG", "Linear")

    assert calls == ["bundle", "linear"]
