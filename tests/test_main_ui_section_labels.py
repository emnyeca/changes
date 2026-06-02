import pytest

pytest.importorskip("streamlit")

from changes import main_ui


@pytest.mark.parametrize(
    ("section_id", "expected"),
    [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("Coda1", "Coda1"),
        ("A__OCC1", "A1"),
        ("A__OCC2", "A2"),
        ("Intro__OCC1", "Intro"),
        ("Intro__OCC2", "Intro2"),
    ],
)
def test_section_filter_label_matches_chord_display_label(section_id: str, expected: str) -> None:
    assert main_ui._display_section_label(section_id) == expected
    assert main_ui._section_filter_label(section_id) == expected
