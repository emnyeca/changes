from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from changes.digitone.track8_chord_events import extract_track8_chord_events
from changes.digitone.track8_sysex_export import generate_track8_sysex_bytes_with_toolkit
from changes.digitone.track8_toolkit_adapter import changes_track8_payload_to_toolkit_events
from changes.digitone.track8_toolkit_payload import track8_chord_events_to_toolkit_payload
from changes.digitone.track8_yaml_export import dump_track8_events_yaml, finalize_track8_toolkit_event_lengths
from changes.models.song_model import HarmonyEvent, Measure, SongModel
from changes.rendering.arrangement_renderer import render_arrangement


@dataclass(frozen=True)
class Track8ProductLikeFixturePaths:
    events_yaml_path: Path
    syx_path: Path
    manifest_path: Path


PRODUCT_LIKE_TRACK_SCALE_LENGTH = 16
PRODUCT_LIKE_TRACK_SCALE_SPEED_ACTIVE = "1/8"
PRODUCT_LIKE_TRACK_SCALE_SPEED_INACTIVE = "1"

PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY = {
    1: 70,
    2: 70,
    3: 70,
    4: 50,
    5: 70,
    6: 50,
    7: 100,
}


def _minimal_cmaj7_song_model() -> SongModel:
    return SongModel(
        title="Track8 Product-like Fixture Validation",
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


def _build_product_like_track_scale() -> dict[int, dict[str, int | str]]:
    track_scale: dict[int, dict[str, int | str]] = {}
    for track in range(1, 17):
        track_scale[track] = {
            "length": PRODUCT_LIKE_TRACK_SCALE_LENGTH,
            "speed": (
                PRODUCT_LIKE_TRACK_SCALE_SPEED_ACTIVE
                if track <= 8
                else PRODUCT_LIKE_TRACK_SCALE_SPEED_INACTIVE
            ),
        }
    return track_scale


def _sanitize_finalized_rows_to_events(final_rows: list[dict]) -> list[dict[str, int | str]]:
    events: list[dict[str, int | str]] = []
    for row in final_rows:
        event: dict[str, int | str] = {
            "step": int(row["step"]),
            "track": int(row["track"]),
            "note": str(row["note"]),
            "velocity": int(row["velocity"]),
            "time": int(row.get("time", 0)),
        }
        if "length_code" in row:
            event["length_code"] = str(row["length_code"])
        else:
            event["length"] = str(row.get("length", "inherit"))
        events.append(event)
    return events


def build_track8_product_like_cmaj7_yaml_payload() -> dict:
    song = _minimal_cmaj7_song_model()
    arrangement = render_arrangement(song)
    events = extract_track8_chord_events(arrangement)
    changes_payload = track8_chord_events_to_toolkit_payload(events)
    toolkit_rows = changes_track8_payload_to_toolkit_events(changes_payload)
    final_rows = finalize_track8_toolkit_event_lengths(toolkit_rows)

    return {
        "version": 1,
        "device": "digitone2",
        "name": "T8 Product Like Cmaj7",
        "pattern": {
            "mode": "per-track",
            "tempo": 120.0,
            "change": "OFF",
            "reset": "INF",
        },
        "track_scale": _build_product_like_track_scale(),
        "track_defaults": {
            "velocity": dict(PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY),
        },
        "events": _sanitize_finalized_rows_to_events(final_rows),
    }


def build_track8_product_like_cmaj7_manifest(
    *,
    events_yaml_filename: str,
    syx_filename: str,
    syx_size_bytes: int,
) -> str:
    return "\n".join(
        [
            "# Track 8 Product-like Cmaj7 Fixture",
            "",
            "## Files",
            "",
            f"- {events_yaml_filename}",
            f"- {syx_filename}",
            "",
            "## Purpose",
            "",
            "This fixture validates product-like per-track pattern settings together with the Track 8 Cmaj7 same-step chord trigger.",
            "",
            "## Expected product-like pattern settings",
            "",
            "- Pattern mode: per-track",
            "- Tempo: 120.0",
            "- CHANGE: OFF",
            "- RESET: INF",
            "- Tracks 1-8 LENGTH: 16",
            "- Tracks 1-8 SPEED: 1/8",
            "- Tracks 9-16 LENGTH: 16",
            "- Tracks 9-16 SPEED: 1",
            "- Track default velocities:",
            "  - Track 1: 70",
            "  - Track 2: 70",
            "  - Track 3: 70",
            "  - Track 4: 50",
            "  - Track 5: 70",
            "  - Track 6: 50",
            "  - Track 7: 100",
            "",
            "## Expected Track 8 chord content",
            "",
            "- Track: 8",
            "- Step: 1",
            "- Notes: C4 E4 G4 B4 D5 A5",
            "- Velocities: 70 70 70 50 70 50",
            "- Length code: 0x4E",
            "- Micro timing: 0",
            f"- SysEx size bytes: {syx_size_bytes}",
            "",
            "## Static validation notes",
            "",
            "- events.yaml must parse with toolkit per-track schema.",
            "- track_scale must include tracks 1..16.",
            "- track_defaults.velocity must be written for tracks 1..7.",
            "- Events should include Track 8 rows only for this fixture.",
            "",
            "## Hardware validation steps",
            "",
            "1. Open Elektron Transfer.",
            f"2. Send {syx_filename} to Digitone II.",
            "3. Load the generated pattern.",
            "4. Confirm pattern mode is PER TRACK.",
            "5. Confirm LENGTH and SPEED settings if visible.",
            "6. Confirm CHANGE is OFF and RESET is INF.",
            "7. Confirm Track 1-7 default velocities if visible.",
            "8. Inspect Track 8 step 1.",
            "9. Confirm the six same-step notes are present.",
            "10. Play the pattern and confirm it sounds like a Cmaj7 voicing.",
            "",
            "## Caveats",
            "",
            "- This fixture does not validate complete song export.",
            "- This fixture does not validate bundle planner integration.",
            "- This fixture does not validate UI workflow.",
            "- This fixture does not emit Track 1-7 musical trigger events.",
            "- Track 1-7 LEN baseline behavior should be confirmed on hardware.",
            "",
            "## Notes",
            "",
            "Changes does not send MIDI or operate hardware during fixture generation.",
        ]
    ) + "\n"


def write_track8_product_like_cmaj7_fixture(
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> Track8ProductLikeFixturePaths:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    paths = Track8ProductLikeFixturePaths(
        events_yaml_path=base / "track8_product_like_cmaj7.events.yaml",
        syx_path=base / "track8_product_like_cmaj7.syx",
        manifest_path=base / "track8_product_like_cmaj7_manifest.md",
    )

    existing = [p for p in (paths.events_yaml_path, paths.syx_path, paths.manifest_path) if p.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Refusing to overwrite existing fixture files: " + ", ".join(str(p) for p in existing)
        )

    yaml_payload = build_track8_product_like_cmaj7_yaml_payload()
    yaml_text = dump_track8_events_yaml(yaml_payload)
    syx_bytes = generate_track8_sysex_bytes_with_toolkit(yaml_text)

    paths.events_yaml_path.write_text(yaml_text, encoding="utf-8")
    paths.syx_path.write_bytes(syx_bytes)

    manifest_text = build_track8_product_like_cmaj7_manifest(
        events_yaml_filename=paths.events_yaml_path.name,
        syx_filename=paths.syx_path.name,
        syx_size_bytes=len(syx_bytes),
    )
    paths.manifest_path.write_text(manifest_text, encoding="utf-8")

    return paths
