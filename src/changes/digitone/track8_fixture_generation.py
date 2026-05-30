from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from changes.digitone.track8_chord_events import extract_track8_chord_events
from changes.digitone.track8_sysex_export import generate_track8_sysex_bytes_with_toolkit
from changes.digitone.track8_toolkit_adapter import changes_track8_payload_to_toolkit_events
from changes.digitone.track8_toolkit_payload import track8_chord_events_to_toolkit_payload
from changes.digitone.track8_yaml_export import (
    build_track8_events_yaml_payload,
    dump_track8_events_yaml,
    finalize_track8_toolkit_event_lengths,
)
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_renderer import render_arrangement


@dataclass(frozen=True)
class Track8FixturePaths:
    events_yaml_path: Path
    syx_path: Path
    manifest_path: Path


def _minimal_cmaj7_song_model() -> SongModel:
    return SongModel(
        title="Track8 Hardware Validation",
        working_key="C",
        performance_tempo=Fraction(120, 1),
        measures=(
            Measure(
                number=1,
                section_id="A",
                meter_numerator=4,
                meter_denominator=4,
                absolute_start_quarters=Fraction(0, 1),
                harmony=(
                    HarmonyEvent(
                        id="h1",
                        symbol="Cmaj7",
                        measure_number=1,
                        offset_quarters=Fraction(0, 1),
                        duration_quarters=Fraction(4, 1),
                    ),
                ),
            ),
        ),
    )


def build_track8_cmaj7_hardware_validation_yaml_payload() -> dict:
    song = _minimal_cmaj7_song_model()
    arrangement = render_arrangement(song)
    events = extract_track8_chord_events(arrangement)
    changes_payload = track8_chord_events_to_toolkit_payload(events)
    toolkit_rows = changes_track8_payload_to_toolkit_events(changes_payload)
    final_rows = finalize_track8_toolkit_event_lengths(toolkit_rows)
    return build_track8_events_yaml_payload(
        final_rows,
        name="T8 Cmaj7 Changes",
        tempo=120.0,
    )


def build_track8_cmaj7_hardware_validation_manifest(
    *,
    events_yaml_filename: str,
    syx_filename: str,
    syx_size_bytes: int,
) -> str:
    return "\n".join(
        [
            "# Track 8 Cmaj7 Hardware Validation Fixture",
            "",
            "## Files",
            "",
            f"- {events_yaml_filename}",
            f"- {syx_filename}",
            "",
            "## Purpose",
            "",
            "This fixture verifies that Changes can generate a Digitone II Track 8 same-step six-note chord trigger through digitone-syx-toolkit.",
            "",
            "## Expected musical content",
            "",
            "- Pattern name: T8 Cmaj7 Changes",
            "- Tempo: 120.0",
            "- Track: 8",
            "- Step: 1",
            "- Notes: C4 E4 G4 B4 D5 A5",
            "- Velocities: 70 70 70 50 70 50",
            "- Length code: 0x4E",
            "- Micro timing: 0",
            "- SysEx size bytes: " + str(syx_size_bytes),
            "",
            "## Hardware validation steps",
            "",
            "1. Open Elektron Transfer.",
            f"2. Send {syx_filename} to Digitone II.",
            "3. Load the generated pattern.",
            "4. Inspect Track 8 step 1.",
            "5. Confirm that the six note records are present on the same step.",
            "6. Confirm note order and velocities if the UI exposes them.",
            "7. Play the pattern and confirm a Cmaj7 voicing is triggered.",
            "",
            "## Notes",
            "",
            "This fixture is for validation only.",
            "It does not prove final export workflow integration.",
            "No MIDI or hardware send is performed by Changes during fixture generation.",
        ]
    ) + "\n"


def write_track8_cmaj7_hardware_validation_fixture(
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> Track8FixturePaths:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    paths = Track8FixturePaths(
        events_yaml_path=base / "track8_cmaj7_changes.events.yaml",
        syx_path=base / "track8_cmaj7_changes.syx",
        manifest_path=base / "track8_cmaj7_changes_manifest.md",
    )

    existing = [p for p in (paths.events_yaml_path, paths.syx_path, paths.manifest_path) if p.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Refusing to overwrite existing fixture files: " + ", ".join(str(p) for p in existing)
        )

    yaml_payload = build_track8_cmaj7_hardware_validation_yaml_payload()
    yaml_text = dump_track8_events_yaml(yaml_payload)
    syx_bytes = generate_track8_sysex_bytes_with_toolkit(yaml_text)

    paths.events_yaml_path.write_text(yaml_text, encoding="utf-8")
    paths.syx_path.write_bytes(syx_bytes)

    manifest_text = build_track8_cmaj7_hardware_validation_manifest(
        events_yaml_filename=paths.events_yaml_path.name,
        syx_filename=paths.syx_path.name,
        syx_size_bytes=len(syx_bytes),
    )
    paths.manifest_path.write_text(manifest_text, encoding="utf-8")

    return paths
