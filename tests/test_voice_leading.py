from changes.harmonic_context import (
    build_local_pitch_collection,
    extract_output_chord_tone_set,
    select_scale_collection,
)
from changes.voicing import progression_to_voicings
from changes.voice_leading import generate_voice_leading


def _movement(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def _pc_set(notes):
    return {n % 12 for n in notes}


def test_ii_v_i_voice_leading_preserves_context_selected_pitch_class_sets():
    progression = [["Dm7", "G7", "Cmaj7"]]
    raw = progression_to_voicings(progression, base_octave=3)
    led = generate_voice_leading(raw)

    assert len(led) == 3
    assert all(len(chord) == 6 for chord in led)

    flat = [c for bar in progression for c in bar]
    expected_pc_sets = []
    for idx, symbol in enumerate(flat):
        local = build_local_pitch_collection(flat, idx, circular=True)
        selected = select_scale_collection(symbol, local)
        expected_pc_sets.append(set(extract_output_chord_tone_set(symbol, selected)))

    for idx, chord in enumerate(led):
        assert _pc_set(chord) == expected_pc_sets[idx]
        assert len(_pc_set(chord)) == 6

    # ii->V and V->I should both be controlled movement.
    assert _movement(led[0], led[1]) <= 18
    assert _movement(led[1], led[2]) <= 18


def test_blue_moon_head_voice_leading_keeps_am7_with_f_not_f_sharp():
    progression = [["Cmaj7", "Am7", "Dm7", "G7"]]
    raw = progression_to_voicings(progression, base_octave=3)
    led = generate_voice_leading(raw)

    am7_pc = _pc_set(led[1])
    assert 5 in am7_pc  # F
    assert 6 not in am7_pc  # F#
