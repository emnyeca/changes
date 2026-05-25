import pytest

pytest.importorskip("streamlit")

from changes.ui_streamlit import (
    _apply_digitone_tempo_floor,
    _build_event_schedule,
    _compute_digitone_tempo_for_same_duration,
    _parse_uploaded_yaml_bars,
)


WALTZ_YAML = b"""name: \"Waltz\"
key: \"F\"
progression:
  - [Fmaj7]
  - [A7, Dm7]
  - [Gm7, C7, Fmaj7]
"""


def _event_triplets(events):
    return [(int(e["step"]), str(e["chord"]), int(e["duration_steps"])) for e in events]


def test_waltz_120_3_4_schedule():
    bars = _parse_uploaded_yaml_bars(WALTZ_YAML)
    steps_per_bar, length, events = _build_event_schedule(bars, 3, 4)

    assert steps_per_bar == 6
    assert length == 18

    tempo = _compute_digitone_tempo_for_same_duration(120, 3, 4, steps_per_bar)
    tempo, length, events = _apply_digitone_tempo_floor(tempo, length, events)

    assert tempo == 120
    assert length == 18
    assert _event_triplets(events) == [
        (1, "Fmaj7", 6),
        (7, "A7", 3),
        (10, "Dm7", 3),
        (13, "Gm7", 2),
        (15, "C7", 2),
        (17, "Fmaj7", 2),
    ]


def test_waltz_120_4_4_schedule():
    bars = _parse_uploaded_yaml_bars(WALTZ_YAML)
    steps_per_bar, length, events = _build_event_schedule(bars, 4, 4)

    assert steps_per_bar == 6
    assert length == 18

    tempo = _compute_digitone_tempo_for_same_duration(120, 4, 4, steps_per_bar)
    tempo, length, events = _apply_digitone_tempo_floor(tempo, length, events)

    assert tempo == 90
    assert length == 18
    assert _event_triplets(events) == [
        (1, "Fmaj7", 6),
        (7, "A7", 3),
        (10, "Dm7", 3),
        (13, "Gm7", 2),
        (15, "C7", 2),
        (17, "Fmaj7", 2),
    ]
