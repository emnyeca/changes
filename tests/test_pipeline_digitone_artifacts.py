from __future__ import annotations

import json
from pathlib import Path

import yaml

from changes.pipeline_digitone import (
    compile_digitone_bundle_pipeline,
    compile_digitone_pipeline,
    save_digitone_bundle_artifacts,
    save_digitone_pipeline_artifacts,
)


def test_pipeline_artifacts_written(tmp_path: Path):
    payload = {
        "name": "BlueMoon",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {
                "name": "A",
                "progression": [["Cmaj7", "Dm7", "G7", "Cmaj7"]],
            }
        ],
    }

    song, timeline, plan, events_payload = compile_digitone_pipeline(payload)

    out = save_digitone_pipeline_artifacts(tmp_path, song, timeline, plan, events_payload, write_syx=False)

    assert out["song_model_json"].exists()
    assert out["rendered_timeline_json"].exists()
    assert out["digitone_compile_plan_json"].exists()
    assert out["events_yaml"].exists()
    assert "syx" not in out

    loaded = yaml.safe_load(out["events_yaml"].read_text(encoding="utf-8"))
    assert loaded["events"]
    assert loaded["version"] == 1
    assert loaded["device"] == "digitone2"
    assert loaded["name"] == plan.pattern_name
    assert loaded["pattern"]["speed"] == plan.speed


def test_bundle_artifacts_written_with_manifest_and_order(tmp_path: Path):
    payload = {
        "name": "Blue Moon",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"]]},
            {"name": "A", "progression": [["Dm7"]]},
            {"name": "Solo", "progression": [["G7"]]},
        ],
    }

    song, timeline, bundle_plan = compile_digitone_bundle_pipeline(payload)
    out = save_digitone_bundle_artifacts(tmp_path, song, timeline, bundle_plan, write_syx=False)

    assert out["song_model_json"].exists()
    assert out["rendered_timeline_json"].exists()
    assert out["digitone_bundle_plan_json"].exists()
    assert out["bundle_manifest_json"].exists()
    assert out["patterns_dir"].is_dir()
    assert "bundle_syx" not in out

    manifest = json.loads(out["bundle_manifest_json"].read_text(encoding="utf-8"))
    manifest_patterns = manifest["patterns"]
    assert len(manifest_patterns) == len(bundle_plan.patterns)

    expected_names = [p.pattern_name for p in bundle_plan.patterns]
    assert [p["pattern_name"] for p in manifest_patterns] == expected_names

    expected_paths = [f"patterns/{i:02d}_" for i in range(1, len(manifest_patterns) + 1)]
    for expected_prefix, entry in zip(expected_paths, manifest_patterns, strict=True):
        assert entry["events_yaml"].startswith(expected_prefix)
        events_path = tmp_path / entry["events_yaml"]
        assert events_path.exists()

        payload_loaded = yaml.safe_load(events_path.read_text(encoding="utf-8"))
        assert payload_loaded["name"] == entry["pattern_name"]


def test_bundle_artifacts_write_syx_and_concat_in_manifest_order(tmp_path: Path, monkeypatch):
    payload = {
        "name": "Blue Moon",
        "tempo": 120,
        "time_signature": "4/4",
        "sections": [
            {"name": "Intro", "progression": [["Cmaj7"]]},
            {"name": "A", "progression": [["Dm7"]]},
            {"name": "Solo", "progression": [["G7"]]},
        ],
    }

    def _fake_build(events_yaml_path: str | Path, output_syx_path: str | Path):
        path = Path(events_yaml_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        pattern_name = str(data["name"])
        marker = f"<{pattern_name}>".encode("ascii", errors="ignore")
        Path(output_syx_path).write_bytes(marker)

    monkeypatch.setattr("changes.pipeline_digitone.build_digitone_syx_from_events_yaml", _fake_build)

    song, timeline, bundle_plan = compile_digitone_bundle_pipeline(payload)
    out = save_digitone_bundle_artifacts(tmp_path, song, timeline, bundle_plan, write_syx=True)

    assert out["bundle_syx"].exists()
    manifest = json.loads(out["bundle_manifest_json"].read_text(encoding="utf-8"))
    assert "bundle_syx" in manifest

    concatenated_expected = b""
    for entry in manifest["patterns"]:
        assert entry["syx"].startswith("patterns/")
        syx_path = tmp_path / entry["syx"]
        assert syx_path.exists()
        concatenated_expected += syx_path.read_bytes()

    bundle_bytes = (tmp_path / manifest["bundle_syx"]).read_bytes()
    assert bundle_bytes == concatenated_expected
