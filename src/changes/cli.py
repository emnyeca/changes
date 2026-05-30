"""Command-line interface for Changes generic MIDI export."""

import argparse
from pathlib import Path
import sys

import yaml

from .digitone.track8_demo_songs import build_demo_cmaj7_song
from .digitone.track8_export_api import (
    DEFAULT_TRACK8_EXPORT_BASENAME,
    export_track8_artifacts_from_song,
)
from .models.song_model_yaml import load_song_model_yaml
from .harmonic_context import UnsupportedHarmonicContextError
from .chord_parser import parse_progression
from .pipeline_digitone import (
    compile_musicxml_digitone_bundle_pipeline,
    compile_digitone_bundle_pipeline,
    compile_digitone_pipeline,
    save_digitone_bundle_artifacts,
    save_digitone_pipeline_artifacts,
)
from .voicing import progression_to_voicings
from .voice_leading import generate_voice_leading
from .midi_writer import write_midi


def _run_track8_export_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Export Track 8 artifacts from demo or SongModel YAML")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--demo", help="Demo song id (currently only: cmaj7)")
    source_group.add_argument("--input", help="Path to SongModel YAML v1 file")
    parser.add_argument("--output-dir", required=True, help="Output directory for Track 8 artifacts")
    parser.add_argument(
        "--basename",
        default=DEFAULT_TRACK8_EXPORT_BASENAME,
        help="Base filename for generated artifacts",
    )
    parser.add_argument("--name", default=None, help="Pattern name to write in exported YAML")
    parser.add_argument(
        "--events-yaml-only",
        action="store_true",
        help="Write only events.yaml + manifest and skip SysEx generation",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )
    args = parser.parse_args(argv)

    try:
        if args.demo is not None:
            if args.demo != "cmaj7":
                raise ValueError(f"Unsupported demo: {args.demo}. Supported demos: cmaj7")
            song = build_demo_cmaj7_song()
        else:
            assert args.input is not None
            song = load_song_model_yaml(args.input)

        paths = export_track8_artifacts_from_song(
            song,
            args.output_dir,
            basename=args.basename,
            name=args.name,
            include_sysex=not bool(args.events_yaml_only),
            overwrite=bool(args.overwrite),
        )
    except (RuntimeError, ValueError, FileExistsError, OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"Track 8 export failed: {exc}") from exc

    print("Wrote Track 8 export artifacts:")
    print(f"  events_yaml: {paths.events_yaml_path}")
    if paths.syx_path is not None:
        print(f"  syx: {paths.syx_path}")
    else:
        print("  syx: not generated (--events-yaml-only)")
    print(f"  manifest: {paths.manifest_path}")


def main() -> None:
    """Run the Changes CLI."""
    if len(sys.argv) > 2 and sys.argv[1] == "export" and sys.argv[2] == "digitone-track8":
        _run_track8_export_cli(sys.argv[3:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "digitone-bundle":
        sub = argparse.ArgumentParser(description="MusicXML to Digitone bundle artifacts")
        sub.add_argument("--musicxml", required=True, help="Path to MusicXML file")
        sub.add_argument("--output", required=True, help="Output directory for artifacts")
        sub.add_argument("--tempo", type=int, default=120, help="Performance BPM metadata")
        sub.add_argument("--write-syx", action="store_true", help="Also emit per-pattern SYX and bundle SYX")
        sub_args = sub.parse_args(sys.argv[2:])

        try:
            song, timeline, bundle_plan, diagnostics = compile_musicxml_digitone_bundle_pipeline(
                musicxml_path=sub_args.musicxml,
                tempo=sub_args.tempo,
            )
        except UnsupportedHarmonicContextError as exc:
            raise SystemExit(f"MusicXML conversion failed: {exc}") from exc

        artifacts = save_digitone_bundle_artifacts(
            output_dir=sub_args.output,
            song=song,
            timeline=timeline,
            bundle_plan=bundle_plan,
            write_syx=bool(sub_args.write_syx),
            harmony_resolution=diagnostics,
        )

        print(f"Wrote MusicXML bundle artifacts to: {sub_args.output}")
        print(f"  source_title={bundle_plan.source_title}")
        print(f"  pattern_count={len(bundle_plan.patterns)}")
        print(f"  harmony_resolution: {artifacts['musicxml_harmony_resolution_json']}")
        print(f"  manifest: {artifacts['bundle_manifest_json']}")
        if "bundle_syx" in artifacts:
            print(f"  bundle_syx: {artifacts['bundle_syx']}")
        return

    parser = argparse.ArgumentParser(
        description="Generate six-voice chord clouds and export to generic MIDI"
    )
    parser.add_argument(
        "input",
        help="Path to a YAML file containing the chord progression",
    )
    parser.add_argument(
        "--output",
        default="output.mid",
        help="Path to write the resulting MIDI file",
    )
    parser.add_argument(
        "--tempo",
        type=int,
        default=120,
        help="BPM for generic MIDI export",
    )
    parser.add_argument(
        "--backend",
        choices=["generic-midi", "digitone-compile", "digitone-bundle"],
        default="generic-midi",
        help="Output backend mode",
    )
    parser.add_argument(
        "--artifact-dir",
        default="out_digitone",
        help="Output directory for digitone-compile artifacts",
    )
    parser.add_argument(
        "--write-syx",
        action="store_true",
        help="When backend is digitone-compile or digitone-bundle, also emit SYX via digitone-syx-toolkit",
    )
    args = parser.parse_args()

    if args.backend == "generic-midi":
        progression = parse_progression(args.input)
        voicings = progression_to_voicings(progression)
        voices_led = generate_voice_leading(voicings)
        write_midi(voices_led, args.output, tempo=args.tempo)
        print(f"Wrote generic MIDI: {args.output}")
        return

    payload = yaml.safe_load(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("digitone-compile backend requires mapping YAML input")

    if args.backend == "digitone-compile":
        song, timeline, plan, events_payload = compile_digitone_pipeline(payload)
        artifacts = save_digitone_pipeline_artifacts(
            output_dir=args.artifact_dir,
            song=song,
            timeline=timeline,
            plan=plan,
            events_payload=events_payload,
            write_syx=bool(args.write_syx),
        )

        print(f"Wrote artifacts to: {args.artifact_dir}")
        print(f"  source_title={plan.source_title}")
        print(f"  pattern_name={plan.pattern_name}")
        print(
            "  speed="
            f"{plan.speed} q_step={plan.q_step} device_tempo={float(plan.device_tempo):.3f} total_steps={plan.total_steps}"
        )
        for key, path in artifacts.items():
            print(f"  {key}: {path}")
        return

    song, timeline, bundle_plan = compile_digitone_bundle_pipeline(payload)
    artifacts = save_digitone_bundle_artifacts(
        output_dir=args.artifact_dir,
        song=song,
        timeline=timeline,
        bundle_plan=bundle_plan,
        write_syx=bool(args.write_syx),
    )

    print(f"Wrote bundle artifacts to: {args.artifact_dir}")
    print(f"  source_title={bundle_plan.source_title}")
    print(f"  pattern_count={len(bundle_plan.patterns)}")
    print(
        "  shared_timing="
        f"speed={bundle_plan.timing.speed} q_step={bundle_plan.timing.q_step} device_tempo={float(bundle_plan.timing.device_tempo):.3f}"
    )
    for pattern in bundle_plan.patterns:
        print(f"  [{pattern.segment_index:02d}] {pattern.pattern_name}")
    print(f"  manifest: {artifacts['bundle_manifest_json']}")
    if "bundle_syx" in artifacts:
        print(f"  bundle_syx: {artifacts['bundle_syx']}")
    for key, path in artifacts.items():
        if key not in {"bundle_manifest_json", "bundle_syx"}:
            print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
