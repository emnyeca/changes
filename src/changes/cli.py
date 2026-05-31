"""Command-line interface for Changes export tools."""

import argparse
from pathlib import Path
import sys

import yaml

from .digitone.track8_demo_songs import build_demo_cmaj7_song
from .digitone.track8_export_api import (
    DEFAULT_TRACK8_EXPORT_BASENAME,
    export_track8_artifacts_from_song,
)
from .digitone.transport import (
    DryRunSysexTransport,
    GuardedSysexSender,
    MidiPortInfo,
    MidoMidiBackend,
)
from .digitone.sysex_file import read_and_validate_sysex_file
from .digitone.manifest_check import parse_track8_manifest, validate_sysex_against_manifest
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


def _create_mido_backend() -> MidoMidiBackend:
    return MidoMidiBackend()


def _build_top_level_help_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="changes",
        usage=(
            "changes [--help]\n"
            "       changes export digitone-track8 ...\n"
            "       changes check digitone-syx ...\n"
            "       changes send digitone-syx ...\n"
            "       changes digitone-bundle ...\n"
            "       changes INPUT --backend {generic-midi,digitone-compile,digitone-bundle} ..."
        ),
        description=(
            "Changes CLI with modern Chord export/check/send commands for Digitone Track 8 and legacy progression export compatibility. "
            "Export and send remain separate."
        ),
        epilog=(
            "Modern commands:\n"
            "  export digitone-track8   Export Chord artifacts for Digitone II Track 8\n"
            "  check digitone-syx       Validate an existing .syx envelope or manifest metadata without sending\n"
            "  send digitone-syx        List ports, dry-run, or guarded-send an existing .syx\n\n"
            "Legacy commands:\n"
            "  digitone-bundle          Build Digitone bundle artifacts from MusicXML\n"
            "  INPUT --backend generic-midi      Export generic MIDI\n"
            "  INPUT --backend digitone-compile  Build Digitone compile artifacts\n"
            "  INPUT --backend digitone-bundle   Build Digitone bundle artifacts from YAML"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def _print_top_level_help() -> None:
    _build_top_level_help_parser().print_help()


def _print_export_group_help() -> None:
    parser = argparse.ArgumentParser(
        prog="changes export",
        description="Modern export commands. Export writes artifacts only and does not send MIDI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.print_help()
    print()
    print("Available export commands:")
    print("  digitone-track8   Export Chord artifacts for Digitone II Track 8 from SongModel YAML v1 or demo input")


def _print_send_group_help() -> None:
    parser = argparse.ArgumentParser(
        prog="changes send",
        description="Modern send commands. Real-send is always explicit and requires confirmation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.print_help()
    print()
    print("Available send commands:")
    print("  digitone-syx   List ports, dry-run, or guarded-send an existing .syx file")


def _print_check_group_help() -> None:
    parser = argparse.ArgumentParser(
        prog="changes check",
        description="Modern check commands. Checks validate artifacts only and never send MIDI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.print_help()
    print()
    print("Available check commands:")
    print("  digitone-syx   Validate an existing .syx file envelope and optional manifest metadata")


def _build_digitone_sysex_check_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a Digitone .syx file envelope without MIDI send or hardware access"
    )
    parser.add_argument("--syx", required=True, help="Path to a SysEx file")
    parser.add_argument("--manifest", help="Optional Chord export manifest (Digitone Track 8) to cross-check .syx metadata")
    parser.add_argument("--expect-source-title", help="Optional expected source title for manifest validation")
    parser.add_argument("--expect-chord-events", type=int, help="Optional expected Track 8 chord event count")
    parser.add_argument("--expect-note-rows", type=int, help="Optional expected Track 8 note row count")
    return parser


def _run_digitone_sysex_check_cli(argv: list[str]) -> None:
    parser = _build_digitone_sysex_check_parser()
    args = parser.parse_args(argv)
    syx_path = Path(args.syx)

    try:
        _, info = read_and_validate_sysex_file(syx_path)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"SysEx check failed: {exc}") from exc

    print("Digitone SysEx file validated:")
    print(f"  syx: {info.path}")
    print(f"  bytes: {info.byte_count}")
    print(f"  first_byte: 0x{info.first_byte:02x}")
    print(f"  last_byte: 0x{info.last_byte:02x}")
    print("  valid: yes")

    if not args.manifest:
        return

    manifest_path = Path(args.manifest)
    try:
        manifest = parse_track8_manifest(manifest_path)
        result = validate_sysex_against_manifest(
            syx_byte_count=info.byte_count,
            manifest=manifest,
            expected_source_title=args.expect_source_title,
            expected_chord_event_count=args.expect_chord_events,
            expected_note_row_count=args.expect_note_rows,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise SystemExit(f"Manifest validation failed: {exc}") from exc

    print("Manifest validation:")
    print(f"  manifest: {manifest.path}")
    print(f"  source_title: {result.source_title if result.source_title is not None else 'n/a'}")
    print(
        "  track8_chord_event_count: "
        f"{result.track8_chord_event_count if result.track8_chord_event_count is not None else 'n/a'}"
    )
    print(
        "  track8_note_row_count: "
        f"{result.track8_note_row_count if result.track8_note_row_count is not None else 'n/a'}"
    )
    print(f"  sysex_size: {result.manifest_sysex_size if result.manifest_sysex_size is not None else 'n/a'}")
    print("  manifest_match: yes")
    if result.warnings:
        print("  warnings:")
        for warning in result.warnings:
            print(f"    - {warning}")


def _build_digitone_sysex_send_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "List MIDI ports, validate a .syx file with dry-run, or perform an explicitly confirmed "
            "Digitone II real-send. Port listing and real-send require the optional MIDI extra "
            "(pip install .[midi]); dry-run does not."
        )
    )
    parser.add_argument("--syx", help="Path to a SysEx file")
    parser.add_argument("--port", help="MIDI output port name")
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument(
        "--list-ports",
        action="store_true",
        help="List MIDI output ports via the optional mido backend; does not read .syx or send hardware",
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate SysEx bytes and the selected port name without hardware write",
    )
    mode_group.add_argument(
        "--real-send",
        action="store_true",
        help="Perform guarded real-send after explicit confirmation; writes to hardware",
    )
    parser.add_argument(
        "--yes-i-understand-this-writes-to-hardware",
        action="store_true",
        help="Required with --real-send; acknowledges that hardware will be written",
    )
    return parser


def _run_digitone_sysex_send_cli(argv: list[str]) -> None:
    parser = _build_digitone_sysex_send_parser()
    args = parser.parse_args(argv)

    if not (args.list_ports or args.dry_run or args.real_send):
        raise SystemExit(
            "SysEx send failed: choose exactly one of --dry-run, --real-send, or --list-ports"
        )

    if args.list_ports:
        try:
            backend = _create_mido_backend()
            ports = backend.list_output_ports()
        except (RuntimeError, ValueError, OSError) as exc:
            raise SystemExit(f"SysEx send failed: {exc}") from exc

        print("Available MIDI output ports:")
        if not ports:
            print("  (none)")
        for port in ports:
            print(f"  - {port.name}")
        return

    if not args.syx:
        raise SystemExit("SysEx send failed: --syx is required for send mode")
    if not args.port:
        raise SystemExit("SysEx send failed: --port is required for send mode")

    syx_path = Path(args.syx)

    try:
        syx_bytes, _ = read_and_validate_sysex_file(syx_path)
        if args.dry_run:
            transport = DryRunSysexTransport([MidiPortInfo(name=args.port)])
            result = transport.send_sysex(syx_bytes, port_name=args.port, dry_run=True)
        else:
            if not args.yes_i_understand_this_writes_to_hardware:
                raise RuntimeError(
                    "Real-send requires --yes-i-understand-this-writes-to-hardware to confirm hardware write"
                )
            sender = GuardedSysexSender(_create_mido_backend())
            result = sender.send_confirmed_sysex(
                syx_bytes,
                port_name=args.port,
                confirmation=True,
            )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"SysEx send failed: {exc}") from exc

    if args.dry_run:
        print("Dry-run SysEx send validated:")
    else:
        print("Guarded real SysEx send completed:")
    print(f"  syx: {syx_path}")
    print(f"  port: {result.port_name}")
    print(f"  bytes: {result.byte_count}")
    print(f"  hardware_send: {'yes' if args.real_send else 'no'}")
    if args.real_send:
        print("  warning: hardware was written")


def _build_track8_export_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export Chord artifacts for Digitone II Track 8 from SongModel YAML v1 or built-in demo input; "
            "does not send MIDI"
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--demo",
        help="Built-in demo song id for development/testing (currently only: cmaj7)",
    )
    source_group.add_argument("--input", help="Path to SongModel YAML v1 file")
    parser.add_argument("--output-dir", required=True, help="Output directory for Chord artifacts (Digitone Track 8)")
    parser.add_argument(
        "--basename",
        default=DEFAULT_TRACK8_EXPORT_BASENAME,
        help="Base filename for generated artifacts",
    )
    parser.add_argument("--name", default=None, help="Pattern name to write in exported YAML")
    parser.add_argument(
        "--events-yaml-only",
        action="store_true",
        help="Write only .events.yaml + manifest and skip SysEx generation",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing artifact files",
    )
    return parser


def _run_track8_export_cli(argv: list[str]) -> None:
    parser = _build_track8_export_parser()
    args = parser.parse_args(argv)

    try:
        if args.demo is not None:
            if args.demo != "cmaj7":
                raise ValueError(f"Unsupported demo: {args.demo}. Supported demos: cmaj7")
            song = build_demo_cmaj7_song()
        else:
            assert args.input is not None
            song = load_song_model_yaml(args.input)

        export_name = args.name
        if export_name is None:
            export_name = song.title

        paths = export_track8_artifacts_from_song(
            song,
            args.output_dir,
            basename=args.basename,
            name=export_name,
            include_sysex=not bool(args.events_yaml_only),
            overwrite=bool(args.overwrite),
        )
    except (RuntimeError, ValueError, FileExistsError, OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"Chord export failed (Digitone Track 8): {exc}") from exc

    print("Wrote Chord export artifacts (Digitone Track 8):")
    print(f"  events_yaml: {paths.events_yaml_path}")
    if paths.syx_path is not None:
        print(f"  syx: {paths.syx_path}")
    else:
        print("  syx: not generated (--events-yaml-only)")
    print(f"  manifest: {paths.manifest_path}")


def _run_export_group_cli(argv: list[str]) -> None:
    if not argv or argv[0] in {"-h", "--help"}:
        _print_export_group_help()
        return

    if argv[0] == "digitone-track8":
        _run_track8_export_cli(argv[1:])
        return

    raise SystemExit(f"Unknown export command: {argv[0]}")


def _run_send_group_cli(argv: list[str]) -> None:
    if not argv or argv[0] in {"-h", "--help"}:
        _print_send_group_help()
        return

    if argv[0] == "digitone-syx":
        _run_digitone_sysex_send_cli(argv[1:])
        return

    raise SystemExit(f"Unknown send command: {argv[0]}")


def _run_check_group_cli(argv: list[str]) -> None:
    if not argv or argv[0] in {"-h", "--help"}:
        _print_check_group_help()
        return

    if argv[0] == "digitone-syx":
        _run_digitone_sysex_check_cli(argv[1:])
        return

    raise SystemExit(f"Unknown check command: {argv[0]}")


def _run_musicxml_digitone_bundle_cli(argv: list[str]) -> None:
        sub = argparse.ArgumentParser(description="MusicXML to Digitone bundle artifacts")
        sub.add_argument("--musicxml", required=True, help="Path to MusicXML file")
        sub.add_argument("--output", required=True, help="Output directory for artifacts")
        sub.add_argument("--tempo", type=int, default=120, help="Performance BPM metadata")
        sub.add_argument("--write-syx", action="store_true", help="Also emit per-pattern SYX and bundle SYX")
        sub_args = sub.parse_args(argv)

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


def _run_legacy_root_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        description="Legacy generic progression export CLI with optional Digitone backend modes"
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
        help="Legacy output backend mode",
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
    args = parser.parse_args(argv)

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


def main() -> None:
    """Run the Changes CLI."""
    argv = sys.argv[1:]

    if not argv or argv[0] in {"-h", "--help"}:
        _print_top_level_help()
        return

    if argv[0] == "send":
        _run_send_group_cli(argv[1:])
        return

    if argv[0] == "check":
        _run_check_group_cli(argv[1:])
        return

    if argv[0] == "export":
        _run_export_group_cli(argv[1:])
        return

    if argv[0] == "digitone-bundle":
        _run_musicxml_digitone_bundle_cli(argv[1:])
        return

    _run_legacy_root_cli(argv)


if __name__ == "__main__":
    main()
