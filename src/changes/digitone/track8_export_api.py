from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from changes.digitone.track8_chord_events import extract_track8_chord_events
from changes.digitone.track8_product_like_fixture_generation import (
    PRODUCT_LIKE_TRACK_DEFAULT_VELOCITY,
    PRODUCT_LIKE_TRACK_SCALE_LENGTH,
    PRODUCT_LIKE_TRACK_SCALE_SPEED_ACTIVE,
    PRODUCT_LIKE_TRACK_SCALE_SPEED_INACTIVE,
)
from changes.digitone.track8_sysex_export import generate_track8_sysex_bytes_with_toolkit
from changes.digitone.track8_toolkit_adapter import changes_track8_payload_to_toolkit_events
from changes.digitone.track8_toolkit_payload import track8_chord_events_to_toolkit_payload
from changes.digitone.track8_yaml_export import dump_track8_events_yaml, finalize_track8_toolkit_event_lengths
from changes.models.song_model import SongModel
from changes.rendering.arrangement_renderer import render_arrangement

DEFAULT_TRACK8_EXPORT_BASENAME = "changes_track8_export"
DEFAULT_TRACK8_EXPORT_PROFILE = "product-like"


@dataclass(frozen=True)
class Track8ExportPaths:
    events_yaml_path: Path
    syx_path: Path | None
    manifest_path: Path


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


def build_track8_export_yaml_payload_from_song(
    song: SongModel,
    *,
    profile: str = DEFAULT_TRACK8_EXPORT_PROFILE,
    name: str | None = None,
) -> dict:
    if profile != DEFAULT_TRACK8_EXPORT_PROFILE:
        raise ValueError(f"Unsupported Chord export profile (Digitone Track 8): {profile}")

    arrangement = render_arrangement(song)
    chord_events = extract_track8_chord_events(arrangement)
    if not chord_events:
        raise ValueError("No Chord events for Digitone Track 8 were generated from song")

    changes_payload = track8_chord_events_to_toolkit_payload(chord_events)
    toolkit_rows = changes_track8_payload_to_toolkit_events(changes_payload)
    final_rows = finalize_track8_toolkit_event_lengths(toolkit_rows)

    payload_name = name if name is not None else "Changes Chord Export (Track 8)"

    return {
        "version": 1,
        "device": "digitone2",
        "name": str(payload_name),
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


def build_track8_export_manifest(
    *,
    source_name: str | None,
    profile: str,
    events_yaml_filename: str,
    syx_filename: str | None,
    track8_chord_event_count: int,
    track8_note_row_count: int,
    syx_size_bytes: int | None,
    sysex_generated: bool,
) -> str:
    lines = [
        "# Chord Export Artifacts (Digitone Track 8)",
        "",
        "## Summary",
        "",
    ]

    if source_name:
        lines.append(f"- Source name: {source_name}")
    lines.extend(
        [
            f"- Profile: {profile}",
            "",
            "## Output files",
            "",
            f"- events_yaml: {events_yaml_filename}",
            f"- manifest: {DEFAULT_TRACK8_EXPORT_BASENAME}_manifest.md" if events_yaml_filename == f"{DEFAULT_TRACK8_EXPORT_BASENAME}.events.yaml" else "- manifest: see generated manifest filename",
        ]
    )

    if syx_filename is not None:
        lines.append(f"- syx: {syx_filename}")
    else:
        lines.append("- syx: not generated")

    lines.extend(
        [
            "",
            "## Product-like pattern settings",
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
            "## Chord export counts (Digitone Track 8)",
            "",
            f"- Track 8 chord event count: {track8_chord_event_count}",
            f"- Track 8 note row count: {track8_note_row_count}",
            "",
            "## SysEx status",
            "",
            f"- SysEx generated: {'yes' if sysex_generated else 'no'}",
        ]
    )

    if sysex_generated and syx_size_bytes is not None:
        lines.append(f"- SysEx size bytes: {syx_size_bytes}")
    else:
        lines.append("- SysEx size bytes: n/a")

    lines.extend(
        [
            "",
            "## Toolkit dependency note",
            "",
            "- .events.yaml export does not require digitone-syx-toolkit.",
            "- .syx export requires digitone-syx-toolkit and uses lazy import through Changes integration helpers.",
            "- Dependency direction remains changes -> digitone-syx-toolkit.",
            "",
            "## Safety",
            "",
            "- This API does not send MIDI.",
            "- This API does not operate hardware.",
            "- This API does not provide CLI commands.",
            "",
            "## Caveats",
            "",
            "- SongModel/project file loading is not implemented here.",
            "- This export path targets Chord product-like artifacts on Digitone Track 8 only.",
            "- Verify generated artifacts before any external transfer.",
        ]
    )

    return "\n".join(lines) + "\n"


def export_track8_artifacts_from_song(
    song: SongModel,
    output_dir: str | Path,
    *,
    basename: str = DEFAULT_TRACK8_EXPORT_BASENAME,
    profile: str = DEFAULT_TRACK8_EXPORT_PROFILE,
    name: str | None = None,
    include_sysex: bool = True,
    overwrite: bool = False,
) -> Track8ExportPaths:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    events_yaml_path = base / f"{basename}.events.yaml"
    manifest_path = base / f"{basename}_manifest.md"
    syx_path = base / f"{basename}.syx" if include_sysex else None

    output_paths: list[Path] = [events_yaml_path, manifest_path]
    if syx_path is not None:
        output_paths.append(syx_path)

    existing = [path for path in output_paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError("Refusing to overwrite existing export files: " + ", ".join(str(p) for p in existing))

    arrangement = render_arrangement(song)
    chord_events = extract_track8_chord_events(arrangement)
    if not chord_events:
        raise ValueError("No Chord events for Digitone Track 8 were generated from song")

    yaml_payload = build_track8_export_yaml_payload_from_song(song, profile=profile, name=name)
    yaml_text = dump_track8_events_yaml(yaml_payload)
    events_yaml_path.write_text(yaml_text, encoding="utf-8")

    syx_bytes: bytes | None = None
    if include_sysex:
        syx_bytes = generate_track8_sysex_bytes_with_toolkit(yaml_text)
        assert syx_path is not None
        syx_path.write_bytes(syx_bytes)

    manifest_text = build_track8_export_manifest(
        source_name=str(song.title) if song.title else None,
        profile=profile,
        events_yaml_filename=events_yaml_path.name,
        syx_filename=syx_path.name if syx_path is not None else None,
        track8_chord_event_count=len(chord_events),
        track8_note_row_count=len(yaml_payload.get("events", [])),
        syx_size_bytes=(len(syx_bytes) if syx_bytes is not None else None),
        sysex_generated=syx_bytes is not None,
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    return Track8ExportPaths(
        events_yaml_path=events_yaml_path,
        syx_path=syx_path,
        manifest_path=manifest_path,
    )
