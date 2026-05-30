from __future__ import annotations

import pytest

from changes.digitone.track8_length_encoding import encode_digitone_length_from_duration_quarters


def test_encodes_whole_bar_duration():
    assert encode_digitone_length_from_duration_quarters("4") == "0x4E"


def test_encodes_half_bar_duration():
    assert encode_digitone_length_from_duration_quarters("2") == "0x3E"


def test_encodes_one_quarter_duration():
    assert encode_digitone_length_from_duration_quarters("1") == "0x2E"


def test_encodes_eighth_note_duration():
    assert encode_digitone_length_from_duration_quarters("1/2") == "0x1E"


def test_rejects_non_exact_duration():
    with pytest.raises(ValueError, match="no exact finite Digitone explicit length code"):
        encode_digitone_length_from_duration_quarters("1/3")


@pytest.mark.parametrize("duration_quarters", ["0", "-1"])
def test_rejects_zero_or_negative_duration(duration_quarters: str):
    with pytest.raises(ValueError, match="must be > 0"):
        encode_digitone_length_from_duration_quarters(duration_quarters)


def test_rejects_invalid_duration_string():
    with pytest.raises(ValueError, match="invalid duration_quarters"):
        encode_digitone_length_from_duration_quarters("abc")
