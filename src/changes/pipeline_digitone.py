"""High-level SongModel -> RenderedTimeline -> DigitoneCompilePlan pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from changes.digitone.planner import compile_timeline_to_digitone_plan
from changes.exporters.digitone_events import digitone_compile_plan_to_events_yaml_payload
from changes.exporters.digitone_syx import compile_plan_to_syx_bytes
from changes.importers.compact_progression import compact_progression_to_song_model
from changes.models.digitone_compile_plan import DigitoneCompilePlan, digitone_compile_plan_to_dict
from changes.models.digitone_target_profile import DigitoneTargetProfile, default_digitone_target_profile
from changes.models.render_profile import RenderProfile, default_render_profile
from changes.models.rendered_timeline import RenderedTimeline, rendered_timeline_to_dict
from changes.models.song_model import SongModel, song_model_to_dict
from changes.rendering.timeline_renderer import render_timeline


class DigitonePipelineArtifacts(dict):
    pass


def compile_digitone_pipeline(
    payload: dict,
    render_profile: RenderProfile | None = None,
    target_profile: DigitoneTargetProfile | None = None,
) -> tuple[SongModel, RenderedTimeline, DigitoneCompilePlan, dict]:
    rp = render_profile or default_render_profile()
    tp = target_profile or default_digitone_target_profile()

    song = compact_progression_to_song_model(payload)
    timeline = render_timeline(song, rp)
    plan = compile_timeline_to_digitone_plan(timeline, tp)
    events_payload = digitone_compile_plan_to_events_yaml_payload(plan)

    return song, timeline, plan, events_payload


def save_digitone_pipeline_artifacts(
    output_dir: str | Path,
    song: SongModel,
    timeline: RenderedTimeline,
    plan: DigitoneCompilePlan,
    events_payload: dict,
    write_syx: bool = False,
    syx_filename: str = "digitone_pattern.syx",
) -> DigitonePipelineArtifacts:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    song_json = out / "song_model.json"
    timeline_json = out / "rendered_timeline.json"
    plan_json = out / "digitone_compile_plan.json"
    events_yaml = out / "digitone.events.yaml"

    song_json.write_text(json.dumps(song_model_to_dict(song), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    timeline_json.write_text(
        json.dumps(rendered_timeline_to_dict(timeline), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    plan_json.write_text(json.dumps(digitone_compile_plan_to_dict(plan), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    events_yaml.write_text(yaml.safe_dump(events_payload, sort_keys=False, allow_unicode=False), encoding="utf-8")

    artifacts: DigitonePipelineArtifacts = DigitonePipelineArtifacts(
        {
            "song_model_json": song_json,
            "rendered_timeline_json": timeline_json,
            "digitone_compile_plan_json": plan_json,
            "events_yaml": events_yaml,
        }
    )

    if write_syx:
        syx_path = out / syx_filename
        syx_bytes = compile_plan_to_syx_bytes(plan)
        syx_path.write_bytes(syx_bytes)
        artifacts["syx"] = syx_path

    return artifacts
