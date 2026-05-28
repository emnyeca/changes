from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from changes import cli


def _musicxml_path(variant: str) -> Path:
    base = Path("examples/musicXML")
    if variant == "direct":
        return base / "iRealPro" / "500 Miles High.musicxml"
    if variant == "converted":
        return base / "ireal-musicxml" / "500 Miles High.musicxml"
    raise ValueError(variant)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_occurrences(diag: dict) -> list[tuple]:
    out: list[tuple] = []
    for o in diag["occurrences"]:
        out.append(
            (
                o["measure_number"],
                o["event_order_in_measure"],
                o["canonical_chord_symbol"],
                tuple(o["local_pitch_collection"]),
                o["selected_collection_name"],
                o["selected_collection_family"],
                tuple(o["output_chord_tone_set"]),
                o["retry_level"],
            )
        )
    return out


def _manifest_event_yaml_sequence(manifest: dict, root: Path) -> list[str]:
    seq: list[str] = []
    for pattern in manifest["patterns"]:
        rel = pattern["events_yaml"]
        seq.append((root / rel).read_text(encoding="utf-8"))
    return seq


def test_cli_musicxml_bundle_generates_required_artifacts(tmp_path: Path, monkeypatch):
    musicxml = _musicxml_path("direct")
    out_dir = tmp_path / "bundle_out"

    def _fake_build(events_yaml_path: str | Path, output_syx_path: str | Path):
        Path(output_syx_path).write_bytes(b"\xF0\x7D\x01\xF7")

    monkeypatch.setattr("changes.pipeline_digitone.build_digitone_syx_from_events_yaml", _fake_build)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            "digitone-bundle",
            "--musicxml",
            str(musicxml),
            "--output",
            str(out_dir),
            "--write-syx",
        ],
    )

    cli.main()

    assert (out_dir / "bundle_manifest.json").exists()
    assert (out_dir / "digitone_bundle_plan.json").exists()
    assert (out_dir / "musicxml_harmony_resolution.json").exists()
    assert (out_dir / "patterns").is_dir()
    assert list((out_dir / "patterns").glob("*.digitone.events.yaml"))
    assert list((out_dir / "patterns").glob("*.syx"))
    assert (out_dir / "500_MILES_HIGH.bundle.syx").exists()

    diag = _read_json(out_dir / "musicxml_harmony_resolution.json")
    assert diag["occurrence_count"] > 0
    first = diag["occurrences"][0]
    assert "retry_level" in first
    assert "hard_context_pitch_classes_used" in first
    assert "color_hint_pitch_classes" in first
    assert "color_hints_applied_to_constraint_set" in first
    assert "final_local_pitch_collection_used_for_selection" in first
    assert "selected_collection_name" in first
    assert "output_chord_tone_set" in first


def test_direct_vs_converted_generate_semantically_identical_diagnostics_and_events(tmp_path: Path, monkeypatch):
    direct_xml = _musicxml_path("direct")
    converted_xml = _musicxml_path("converted")
    direct_out = tmp_path / "direct"
    converted_out = tmp_path / "converted"

    def _fake_build(events_yaml_path: str | Path, output_syx_path: str | Path):
        Path(output_syx_path).write_bytes(b"\xF0\x7D\x01\xF7")

    monkeypatch.setattr("changes.pipeline_digitone.build_digitone_syx_from_events_yaml", _fake_build)

    monkeypatch.setattr(
        sys,
        "argv",
        ["changes", "digitone-bundle", "--musicxml", str(direct_xml), "--output", str(direct_out), "--write-syx"],
    )
    cli.main()

    monkeypatch.setattr(
        sys,
        "argv",
        ["changes", "digitone-bundle", "--musicxml", str(converted_xml), "--output", str(converted_out), "--write-syx"],
    )
    cli.main()

    direct_diag = _read_json(direct_out / "musicxml_harmony_resolution.json")
    converted_diag = _read_json(converted_out / "musicxml_harmony_resolution.json")

    assert _semantic_occurrences(direct_diag) == _semantic_occurrences(converted_diag)

    direct_manifest = _read_json(direct_out / "bundle_manifest.json")
    converted_manifest = _read_json(converted_out / "bundle_manifest.json")
    assert _manifest_event_yaml_sequence(direct_manifest, direct_out) == _manifest_event_yaml_sequence(
        converted_manifest, converted_out
    )


def test_500_miles_high_measure3_gm7_uses_current_only_diatonic_after_restriction(tmp_path: Path, monkeypatch):
    direct_xml = _musicxml_path("direct")
    out_dir = tmp_path / "direct"

    def _fake_build(events_yaml_path: str | Path, output_syx_path: str | Path):
        Path(output_syx_path).write_bytes(b"\xF0\x7D\x01\xF7")

    monkeypatch.setattr("changes.pipeline_digitone.build_digitone_syx_from_events_yaml", _fake_build)
    monkeypatch.setattr(
        sys,
        "argv",
        ["changes", "digitone-bundle", "--musicxml", str(direct_xml), "--output", str(out_dir), "--write-syx"],
    )
    cli.main()

    diag = _read_json(out_dir / "musicxml_harmony_resolution.json")
    gm7 = next(
        o
        for o in diag["occurrences"]
        if o["measure_number"] == "3" and o["event_order_in_measure"] == 1 and o["canonical_chord_symbol"] == "Gm7"
    )

    assert gm7["retry_level"] == "current_only"
    assert gm7["selected_collection_family"] == "diatonic_dorian"
    assert gm7["selected_collection_name"].startswith("G_dorian")
    assert gm7["output_chord_tone_set"] == ["G", "A#", "D", "E", "F", "A"]


def test_500_miles_high_measure8_e7sharp9_prefers_harmonic_minor_with_soft_color_hint(tmp_path: Path, monkeypatch):
    direct_xml = _musicxml_path("direct")
    out_dir = tmp_path / "direct"

    def _fake_build(events_yaml_path: str | Path, output_syx_path: str | Path):
        Path(output_syx_path).write_bytes(b"\xF0\x7D\x01\xF7")

    monkeypatch.setattr("changes.pipeline_digitone.build_digitone_syx_from_events_yaml", _fake_build)
    monkeypatch.setattr(
        sys,
        "argv",
        ["changes", "digitone-bundle", "--musicxml", str(direct_xml), "--output", str(out_dir), "--write-syx"],
    )
    cli.main()

    diag = _read_json(out_dir / "musicxml_harmony_resolution.json")
    e7s9 = next(
        o
        for o in diag["occurrences"]
        if o["measure_number"] == "8" and o["event_order_in_measure"] == 1 and o["canonical_chord_symbol"] == "E7#9"
    )

    assert e7s9["retry_level"] == "current+previous"
    assert e7s9["selected_collection_family"] == "harmonic_minor"
    assert e7s9["selected_collection_name"].startswith("A_harmonic_minor")
    assert e7s9["output_chord_tone_set"] == ["E", "G#", "B", "C", "D", "F"]
    assert e7s9["color_hint_pitch_classes"] == ["G"]
    assert e7s9["color_hints_applied_to_constraint_set"] is False
    assert e7s9["final_local_pitch_collection_used_for_selection"] == ["D", "E", "F", "G#", "A", "B"]


def test_unresolved_context_fails_with_actionable_message(tmp_path: Path, monkeypatch):
    xml = tmp_path / "unresolved.musicxml"
    xml.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<score-partwise version=\"4.0\">
  <part-list><score-part id=\"P1\"><part-name>Music</part-name></score-part></part-list>
  <part id=\"P1\">
    <measure number=\"1\">
      <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <harmony>
        <root><root-step>C</root-step></root>
        <kind text=\"M9\">major-ninth</kind>
        <bass><bass-step>D</bass-step><bass-alter>-1</bass-alter></bass>
      </harmony>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["changes", "digitone-bundle", "--musicxml", str(xml), "--output", str(tmp_path / "out")],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    msg = str(exc.value)
    assert "MusicXML conversion failed" in msg
    assert "measure=1" in msg
    assert "event=1" in msg
    assert "symbol=Cmaj9/C#" in msg
    assert "local_pitch_collection" in msg
