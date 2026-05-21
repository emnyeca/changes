from harmony_cloud.chord_parser import parse_chord_symbol
from harmony_cloud.chord_rules import expand_chord_symbol, interpret_chord


def test_parse_core_ii_v_i_symbols():
    assert parse_chord_symbol("Dm7") == {
        "symbol": "Dm7",
        "root": "D",
        "quality": "m7",
    }
    assert parse_chord_symbol("G7") == {
        "symbol": "G7",
        "root": "G",
        "quality": "7",
    }
    assert parse_chord_symbol("Cmaj7") == {
        "symbol": "Cmaj7",
        "root": "C",
        "quality": "maj7",
    }


def test_expansion_rules_for_ii_v_i():
    assert expand_chord_symbol("Dm7") == "Dm6/9"
    assert expand_chord_symbol("G7") == "G9/13"
    assert expand_chord_symbol("Cmaj7") == "C6/9"


def test_interpret_chord_contains_intervals():
    interpreted = interpret_chord("G7")
    assert interpreted["expanded_symbol"] == "G9/13"
    assert interpreted["intervals"] == [0, 4, 7, 10, 14, 21]
