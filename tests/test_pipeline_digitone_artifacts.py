from __future__ import annotations

from pathlib import Path

import yaml

from changes.pipeline_digitone import compile_digitone_pipeline, save_digitone_pipeline_artifacts


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
    assert loaded["pattern"]["speed"] == plan.speed
