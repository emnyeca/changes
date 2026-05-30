from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from changes import cli


def _write_generic_progression(path: Path) -> Path:
    payload = {"progression": [["Cmaj7", "Dm7", "G7", "Cmaj7"]]}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _write_compact_progression(path: Path) -> Path:
    payload = {
        "name": "Blue Moon",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"], ["Cmaj7"]]},
            {"name": "A", "progression": [["Dm7"], ["Dm7"]]},
            {"name": "Solo", "progression": [["G7"], ["G7"]]},
            {"name": "Outro", "progression": [["Cmaj7"], ["Cmaj7"]]},
        ],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_cli_generic_midi_backend_still_works(tmp_path: Path, monkeypatch):
    pytest.importorskip("mido")

    input_path = _write_generic_progression(tmp_path / "input_generic.yaml")
    output_path = tmp_path / "out.mid"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            str(input_path),
            "--backend",
            "generic-midi",
            "--output",
            str(output_path),
            "--tempo",
            "120",
        ],
    )

    cli.main()
    assert output_path.exists()


def test_cli_digitone_compile_backend_still_works(tmp_path: Path, monkeypatch):
    input_path = _write_compact_progression(tmp_path / "input_compile.yaml")
    artifact_dir = tmp_path / "out_compile"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            str(input_path),
            "--backend",
            "digitone-compile",
            "--artifact-dir",
            str(artifact_dir),
        ],
    )

    cli.main()
    assert (artifact_dir / "digitone.events.yaml").exists()
    assert (artifact_dir / "digitone_compile_plan.json").exists()


def test_cli_digitone_bundle_backend_writes_artifacts_and_bundle_syx(tmp_path: Path, monkeypatch):
    input_path = _write_compact_progression(tmp_path / "input_bundle.yaml")
    artifact_dir = tmp_path / "out_bundle"

    def _fake_build(events_yaml_path: str | Path, output_syx_path: str | Path):
        Path(output_syx_path).write_bytes(b"\xF0\x01\xF7")

    monkeypatch.setattr("changes.pipeline_digitone.build_digitone_syx_from_events_yaml", _fake_build)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "changes",
            str(input_path),
            "--backend",
            "digitone-bundle",
            "--artifact-dir",
            str(artifact_dir),
            "--write-syx",
        ],
    )

    cli.main()

    assert (artifact_dir / "bundle_manifest.json").exists()
    assert (artifact_dir / "digitone_bundle_plan.json").exists()
    assert (artifact_dir / "patterns").is_dir()
    assert (artifact_dir / "BLUE_MOON.bundle.syx").exists()
