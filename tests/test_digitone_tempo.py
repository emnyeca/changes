from fractions import Fraction

import pytest

from changes.digitone_tempo import compute_digitone_device_tempo, validate_digitone_device_tempo


def test_compute_digitone_device_tempo_known_examples():
    assert compute_digitone_device_tempo(120, Fraction(4, 1)) == 60.0
    assert compute_digitone_device_tempo(120, Fraction(2, 1)) == 120.0
    assert compute_digitone_device_tempo(120, Fraction(1, 1)) == 240.0


def test_compute_digitone_device_tempo_validation_failure_for_half_step():
    device_tempo = compute_digitone_device_tempo(120, Fraction(1, 2))
    assert device_tempo == 480.0
    with pytest.raises(ValueError, match="30.0..300.0"):
        validate_digitone_device_tempo(device_tempo)
