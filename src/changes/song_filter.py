"""Section-based SongModel filtering helpers.

Pure functions with no UI or external dependencies so they can be tested
in CI environments where streamlit is not installed.
"""

from __future__ import annotations

from dataclasses import replace as _replace
from fractions import Fraction

from changes.models.song_model import SongModel


def extract_section_ids(song: SongModel) -> list[str]:
    """Return ordered unique section_ids from a SongModel (first-occurrence order)."""
    seen: dict[str, None] = {}
    for m in song.measures:
        if m.section_id is not None:
            seen.setdefault(m.section_id, None)
    return list(seen.keys())


def filter_song_by_sections(song: SongModel, selected: set[str]) -> SongModel:
    """Return a new SongModel containing only measures in the selected section_ids.

    absolute_start_quarters is re-computed from zero for the filtered measures.
    Measures with section_id=None are included only if None is in selected.
    """
    filtered_measures = [m for m in song.measures if m.section_id in selected]

    new_measures = []
    absolute_start = Fraction(0)
    for new_num, m in enumerate(filtered_measures, start=1):
        if m.harmony:
            measure_len = (
                m.harmony[-1].offset_quarters + m.harmony[-1].duration_quarters
            )
        else:
            measure_len = Fraction(4 * m.meter_numerator, m.meter_denominator)
        new_measures.append(
            _replace(m, number=new_num, absolute_start_quarters=absolute_start)
        )
        absolute_start += measure_len

    return _replace(song, measures=tuple(new_measures))
