from __future__ import annotations

from fractions import Fraction

import pytest
import yaml

from changes.digitone.track8_export_api import (
    DEFAULT_TRACK8_EXPORT_BASENAME,
    build_track8_export_manifest,
    build_track8_export_yaml_payload_from_song,
    export_track8_artifacts_from_song,
)
from changes.models.song_model import HarmonyEvent, Measure, SongModel


def _minimal_cmaj7_song_model() -> SongModel:
    return SongModel(
        title="Track8 Export API",
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


def _song_with_no_harmony_events() -> SongModel:
    return SongModel(
        title="No Harmony",
        working_key="C",
        performance_tempo=Fraction(120, 1),
        measures=(
            Measure(
                number=1,
                section_id="A",
                meter_numerator=4,
                meter_denominator=4,
                absolute_start_quarters=Fraction(0, 1),
                harmony=(),
            ),
        ),
    )


def test_build_payload_from_minimal_cmaj7_song_model():
    song = _minimal_cmaj7_song_model()

    payload = build_track8_export_yaml_payload_from_song(song, name="My Song")

    assert payload["version"] == 1
    assert payload["device"] == "digitone2"
    assert payload["name"] == "My Song"
    assert payload["pattern"]["mode"] == "per-track"
    assert payload["pattern"]["tempo"] == 120.0
    assert payload["pattern"]["change"] == "OFF"
    assert payload["pattern"]["reset"] == "INF"

    track_scale = payload["track_scale"]
    assert set(track_scale.keys()) == set(range(1, 17))
    for track in range(1, 9):
        assert track_scale[track]["length"] == 16
        assert track_scale[track]["speed"] == "1/8"
    for track in range(9, 17):
        assert track_scale[track]["length"] == 16
        assert track_scale[track]["speed"] == "1"

    assert payload["track_defaults"]["velocity"] == {
        1: 70,
        2: 70,
        3: 70,
        4: 50,
        5: 70,
        6: 50,
        7: 100,
    }

    events = payload["events"]
    assert len(events) == 6
    assert all(event["track"] == 8 for event in events)
    assert [event["note"] for event in events] == ["C4", "E4", "G4", "B4", "D5", "A5"]


def test_unsupported_profile_raises():
    song = _minimal_cmaj7_song_model()

    with pytest.raises(ValueError, match="Unsupported Chord export profile \(Digitone Track 8\)"):
        build_track8_export_yaml_payload_from_song(song, profile="unknown")


def test_export_events_yaml_only_without_toolkit(tmp_path):
    song = _minimal_cmaj7_song_model()

    paths = export_track8_artifacts_from_song(
        song,
        tmp_path,
        include_sysex=False,
    )

    assert paths.events_yaml_path.exists()
    assert paths.manifest_path.exists()
    assert paths.syx_path is None
    assert not (tmp_path / f"{DEFAULT_TRACK8_EXPORT_BASENAME}.syx").exists()

    payload = yaml.safe_load(paths.events_yaml_path.read_text(encoding="utf-8"))
    assert payload["device"] == "digitone2"

    manifest = paths.manifest_path.read_text(encoding="utf-8")
    assert "SysEx generated: no" in manifest


def test_export_writer_refuses_overwrite(tmp_path):
    song = _minimal_cmaj7_song_model()

    export_track8_artifacts_from_song(song, tmp_path, include_sysex=False)

    with pytest.raises(FileExistsError):
        export_track8_artifacts_from_song(song, tmp_path, include_sysex=False, overwrite=False)


def test_export_writer_overwrites_with_overwrite_true(tmp_path):
    song = _minimal_cmaj7_song_model()

    paths1 = export_track8_artifacts_from_song(song, tmp_path, include_sysex=False)
    paths2 = export_track8_artifacts_from_song(song, tmp_path, include_sysex=False, overwrite=True)

    assert paths1.events_yaml_path.exists()
    assert paths1.manifest_path.exists()
    assert paths2.events_yaml_path.exists()
    assert paths2.manifest_path.exists()


def test_export_with_monkeypatched_sysex_bytes(monkeypatch: pytest.MonkeyPatch, tmp_path):
    from changes.digitone import track8_export_api as export_module

    fake_syx = bytes([0xF0, 0x7D, 0x00, 0xF7])
    monkeypatch.setattr(export_module, "generate_track8_sysex_bytes_with_toolkit", lambda _yaml: fake_syx)

    song = _minimal_cmaj7_song_model()
    paths = export_track8_artifacts_from_song(song, tmp_path, include_sysex=True)

    assert paths.events_yaml_path.exists()
    assert paths.syx_path is not None
    assert paths.syx_path.exists()
    assert paths.syx_path.read_bytes() == fake_syx
    assert paths.manifest_path.exists()

    manifest = paths.manifest_path.read_text(encoding="utf-8")
    assert "SysEx generated: yes" in manifest
    assert "SysEx size bytes: 4" in manifest


def test_optional_real_toolkit_export(tmp_path):
    pytest.importorskip("digitone_syx_toolkit.events_to_syx")

    song = _minimal_cmaj7_song_model()
    paths = export_track8_artifacts_from_song(song, tmp_path, include_sysex=True)

    assert paths.syx_path is not None
    assert paths.syx_path.exists()
    syx = paths.syx_path.read_bytes()
    assert len(syx) > 0
    assert syx[0] == 0xF0
    assert syx[-1] == 0xF7


def test_manifest_is_deterministic_and_has_no_absolute_paths():
    kwargs = {
        "source_name": "My Song",
        "profile": "product-like",
        "events_yaml_filename": "my_song.events.yaml",
        "syx_filename": "my_song.syx",
        "track8_chord_event_count": 1,
        "track8_note_row_count": 6,
        "syx_size_bytes": 4,
        "sysex_generated": True,
    }

    m1 = build_track8_export_manifest(**kwargs)
    m2 = build_track8_export_manifest(**kwargs)

    assert m1 == m2
    assert "D:\\" not in m1
    assert "/home/" not in m1
    assert "/Users/" not in m1


def test_no_track8_events_raises():
    song = _song_with_no_harmony_events()

    with pytest.raises(ValueError, match="No Chord events for Digitone Track 8"):
        build_track8_export_yaml_payload_from_song(song)
