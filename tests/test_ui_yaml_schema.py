import pytest

pytest.importorskip("streamlit")

from changes.ui_streamlit import (
  _build_bassline_notes,
  _extract_bars_with_meta,
  _extract_chord_root,
  _format_trigger_event_lines,
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


def test_trigger_event_lines_merge_same_pitch_holds_per_voice():
    events = [
      {"step": 1, "duration_steps": 1, "chord": "Cmaj7"},
      {"step": 2, "duration_steps": 1, "chord": "Am7"},
      {"step": 3, "duration_steps": 1, "chord": "Dm7"},
      {"step": 4, "duration_steps": 1, "chord": "G7"},
    ]
    voicings = [
      [48, 52, 55, 57, 62, 64],
      [48, 52, 57, 59, 62, 66],
      [50, 53, 57, 59, 64, 67],
      [50, 53, 57, 59, 64, 67],
    ]

    lines = _format_trigger_event_lines(events, voicings)

    assert "Step:1" in lines[0]
    assert "0:C3 duration:2" in lines[0]
    assert "1:E3 duration:2" in lines[0]
    assert "Step:4" in lines[3]
    assert "(hold)" in lines[3]


def test_bass_uses_root_not_slash_bass_and_stays_c1_b1():
    events = [
      {"chord": "C/E", "duration_steps": 1},
      {"chord": "C/E", "duration_steps": 1},
    ]
    bass = _build_bassline_notes(events, switch_every=99, switch_enabled=False)

    assert _extract_chord_root("C/E") == "C"
    assert bass == [28, 28]


def test_bass_toggles_root_and_fifth_every_x_repeats():
    events = [{"chord": "Cmaj7", "duration_steps": 1} for _ in range(6)]
    bass = _build_bassline_notes(events, switch_every=3, switch_enabled=True)

    # C1(24) repeats 2 times, then switch on the 3rd slot; same rule applies to fifth.
    assert bass == [24, 24, 31, 31, 24, 24]


def test_bass_slash_chord_uses_slash_only_first_then_root_fifth_cycle():
    events = [{"chord": "Cmaj7/E", "duration_steps": 1} for _ in range(7)]
    bass = _build_bassline_notes(events, switch_every=2, switch_enabled=True)

    # First is slash bass E1, then C/G alternating by switch timing.
    assert bass == [28, 24, 31, 24, 31, 24, 31]
