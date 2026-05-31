from __future__ import annotations

from dataclasses import replace

from changes.chord_parser import parse_chord_core
from changes.digitone.bundle_planner import compile_timeline_to_digitone_bundle_plan
from changes.harmonic_context import (
    UnsupportedHarmonicContextError,
    build_local_pitch_collection,
    chord_tone_pitch_classes,
    extract_output_chord_tone_set,
    resolve_scale_collection_with_retry,
    select_scale_collection,
)
from changes.importers.compact_progression import compact_progression_to_song_model
from changes.models.digitone_target_profile import default_digitone_target_profile
from changes.models.render_profile import default_render_profile
from changes.rendering.arrangement_flattener import flatten_arrangement_to_timeline
from changes.rendering.arrangement_renderer import render_arrangement


_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _pcs_to_names(pcs):
    return sorted(_NAMES[p] for p in pcs)


def test_structured_chord_core_has_musicxml_ready_fields():
    core = parse_chord_core("C7#9b5/E")
    assert core.root_pc == 0
    assert core.base_quality == "dominant"
    assert core.seventh_type == "b7"
    assert "#9" in core.altered_degrees
    assert "b5" in core.altered_degrees
    assert core.slash_bass_pc == 4


def test_constituent_pitch_classes_canonical_scope():
    expected = {
        "C": ["C", "E", "G"],
        "Cm": ["C", "D#", "G"],
        "C6": ["A", "C", "E", "G"],
        "Cm6": ["A", "C", "D#", "G"],
        "Cmaj7": ["B", "C", "E", "G"],
        "Cm7": ["A#", "C", "D#", "G"],
        "CmMaj7": ["B", "C", "D#", "G"],
        "Cm9": ["A#", "C", "D", "D#", "G"],
        "Cm7b5": ["A#", "C", "D#", "F#"],
        "Cdim7": ["A", "C", "D#", "F#"],
        "C7": ["A#", "C", "E", "G"],
        "C9": ["A#", "C", "D", "E", "G"],
        "C7b9": ["A#", "C", "C#", "E", "G"],
        "C7#9": ["A#", "C", "D#", "E", "G"],
        "C7b5": ["A#", "C", "E", "F#"],
        "C7#5": ["A#", "C", "E", "G#"],
        "C7#11": ["A#", "C", "E", "F#", "G"],
        "C7b13": ["A#", "C", "E", "G", "G#"],
        "C7#9b5": ["A#", "C", "D#", "E", "F#"],
        "C7sus4": ["A#", "C", "F", "G"],
        "C9sus4": ["A#", "C", "D", "F", "G"],
        "C7b9sus4": ["A#", "C", "C#", "F", "G"],
        "Calt": ["C", "C#", "E", "G#"],
    }

    for symbol, names in expected.items():
        assert _pcs_to_names(chord_tone_pitch_classes(symbol)) == names

    assert _pcs_to_names(chord_tone_pitch_classes("C/E", include_bass=True)) == ["C", "E", "G"]
    assert _pcs_to_names(chord_tone_pitch_classes("Dm7/G", include_bass=True)) == ["A", "C", "D", "F", "G"]


def test_g7b13_and_g7sharp5_constituents_are_not_collapsed():
    assert chord_tone_pitch_classes("G7b13") != chord_tone_pitch_classes("G7#5")


def test_sus_heptatonic_output_uses_14513b79_rule():
    progression = ["Fmaj7", "C7sus4", "Bbmaj7"]
    _local, selected = resolve_scale_collection_with_retry(progression, 1, circular=True)
    out = extract_output_chord_tone_set("C7sus4", selected)
    assert _pcs_to_names(out) == ["A", "A#", "C", "D", "F", "G"]


def test_alt_does_not_force_melodic_minor():
    _local, selected = resolve_scale_collection_with_retry(["Galt"], 0, circular=True)
    assert selected.family == "harmonic_minor"


def test_retry_attempt2_prefers_previous_plus_current_not_current_plus_next():
    progression = ["Cmaj7", "G7", "F#maj7"]
    local, _selected = resolve_scale_collection_with_retry(progression, 1, circular=True)

    prev_current = set(chord_tone_pitch_classes("Cmaj7")) | set(chord_tone_pitch_classes("G7"))
    current_next = set(chord_tone_pitch_classes("G7")) | set(chord_tone_pitch_classes("F#maj7"))

    assert set(local) == prev_current
    assert set(local) != current_next


def test_plain_major_cannot_select_diminished_after_symmetric_eligibility_restriction():
    diminished_only_local = frozenset({0, 1, 3, 4, 6, 7, 9, 10})
    try:
        selected = select_scale_collection("Cmaj7", diminished_only_local)
        assert selected.family != "diminished"
    except UnsupportedHarmonicContextError:
        pass


def test_full_song_context_crosses_sections_and_occurrences_are_position_sensitive():
    payload = {
        "name": "CTX",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "A", "progression": [["Cmaj7"], ["Am7"]]},
            {"name": "B", "progression": [["Dm7"], ["G7"]]},
            {"name": "A", "progression": [["Cmaj7"], ["F#7"]]},
        ],
    }
    song = compact_progression_to_song_model(payload)
    progression = [h.symbol for m in song.measures for h in m.harmony]

    local_first_a = build_local_pitch_collection(progression, 0, circular=True)
    local_second_a = build_local_pitch_collection(progression, 4, circular=True)

    assert local_first_a != local_second_a
    assert 6 in local_first_a or 6 in local_second_a  # boundary context carries across sections


def test_bundle_split_does_not_recompute_harmony_selection():
    payload = {
        "name": "SPLIT",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "A", "progression": [["Cmaj7"] for _ in range(300)]},
        ],
    }
    rp = replace(default_render_profile(), hold_repeated_same_pitch="retrigger")
    song = compact_progression_to_song_model(payload)
    timeline = flatten_arrangement_to_timeline(render_arrangement(song, rp))

    bundle = compile_timeline_to_digitone_bundle_plan(song, timeline, default_digitone_target_profile())
    assert len(bundle.patterns) >= 2

    progression = [h.symbol for m in song.measures for h in m.harmony]
    local, selected = resolve_scale_collection_with_retry(progression, 0, circular=True)
    expected = set(extract_output_chord_tone_set(progression[0], selected))

    first_harmony_events = [e.note_midi % 12 for e in timeline.events if e.source_harmony_id == "m1_h1" and e.role == "chord"]
    assert set(first_harmony_events) == expected
    assert len(local) > 0
