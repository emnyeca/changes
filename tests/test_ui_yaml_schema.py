import pytest

pytest.importorskip("streamlit")

from harmony_cloud.ui_streamlit import (
  _extract_bars_with_meta,
  _format_chord_voicing_lines,
  _parse_uploaded_yaml_payload,
)


SECTION_YAML = b"""name: "Suite"
key: "C"
time_signature: "3/4"
tempo: 120
sections:
  - name: "A"
    progression:
      - [Dm7, G7, Cmaj7]
  - name: "A"
    progression:
      - [Fmaj7]
"""


def test_sections_yaml_is_parsed_with_duplicate_name_normalization():
    payload = _parse_uploaded_yaml_payload(SECTION_YAML)

    sections = payload["sections"]
    assert isinstance(sections, list)
    assert [s["name"] for s in sections] == ["A", "A2"]
    assert payload["time_signature"] == "3/4"
    assert payload["tempo"] == 120


def test_sections_yaml_extracts_bar_metadata():
    payload = _parse_uploaded_yaml_payload(SECTION_YAML)
    bars, meta = _extract_bars_with_meta(payload)

    assert bars == [["Dm7", "G7", "Cmaj7"], ["Fmaj7"]]
    assert meta == [
        {"section": "A", "bar_in_section": 1},
        {"section": "A2", "bar_in_section": 1},
    ]


def test_voicing_output_shows_rehearsal_mark_only_on_first_bar_of_section():
    events = [
      {"section": "A", "bar_in_section": 1, "chord_in_bar": 0, "chord": "Cmaj7"},
      {"section": "A", "bar_in_section": 1, "chord_in_bar": 1, "chord": "Am7"},
      {"section": "A", "bar_in_section": 2, "chord_in_bar": 0, "chord": "Dm7"},
      {"section": "B", "bar_in_section": 1, "chord_in_bar": 0, "chord": "Fmaj7"},
    ]
    voicings = [
      [48, 52, 55, 57, 62, 64],
      [48, 52, 57, 59, 62, 66],
      [50, 53, 57, 59, 64, 67],
      [53, 57, 60, 64, 67, 71],
    ]

    lines = _format_chord_voicing_lines(events, voicings)

    assert lines[0].startswith("A bar1:")
    assert lines[1].startswith("       [1:")
    assert lines[2].startswith("  bar2:")
    assert lines[3].startswith("B bar1:")
