from changes.chord_parser import parse_progression
from changes.voicing import progression_to_voicings
from changes.voice_leading import generate_voice_leading


def _movement(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def test_ii_v_i_voice_leading_is_deterministic_and_small_motion():
    progression = parse_progression("examples/ii_v_i.progression.yaml")
    raw = progression_to_voicings(progression, base_octave=3)
    led = generate_voice_leading(raw)

    assert len(led) == 3
    assert all(len(chord) == 6 for chord in led)

    # Fixed expected first chord from Dm6/9 (D3 + intervals [0,3,7,9,14,17]).
    assert led[0] == [50, 53, 57, 59, 64, 67]

    # ii->V and V->I should both be controlled movement.
    assert _movement(led[0], led[1]) <= 18
    assert _movement(led[1], led[2]) <= 18
