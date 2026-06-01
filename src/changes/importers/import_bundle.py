"""Import bundle: ZIP / MusicXML+MIDI pairing / tempo fallback / MIDI update.

Responsibilities:
- ZIP extraction and file classification
- Basename grouping and MusicXML↔MIDI pairing
- MIDI metadata extraction (tempo, key, meter)
- MusicXML tempo detection (delegates to musicxml.extract_musicxml_tempo)
- SongModel generation with metadata fallback priority
- ImportBundleResult assembly
- MIDI-only metadata update candidate matching
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from changes.importers.musicxml import (
    ImportedSong,
    extract_musicxml_tempo,
    import_musicxml_text,
    imported_song_to_song_model,
)
from changes.models.song_model import SongModel

# ── File extension sets ───────────────────────────────────────────────────────

MUSICXML_EXTS = frozenset({".musicxml", ".xml"})
MIDI_EXTS = frozenset({".mid", ".midi"})
_IGNORE_EXTS = frozenset({".mscx"})
_KNOWN_EXTS = MUSICXML_EXTS | MIDI_EXTS | _IGNORE_EXTS

DEFAULT_TEMPO = 120

# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class MidiMetadata:
    tempo_bpm: float | None = None
    key: str | None = None    # e.g. "C", "Em" (mido convention)
    meter: str | None = None  # e.g. "4/4"


@dataclass
class ImportWarning:
    song_name: str
    message: str


@dataclass
class ImportedSongCandidate:
    source_name: str
    song: SongModel
    tempo_source: str   # "musicxml" | "midi" | "default"
    key_source: str     # "musicxml" | "midi" | "unknown"
    meter_source: str   # "musicxml" | "midi" | "default"
    warnings: list[str]


@dataclass
class ImportBundleResult:
    songs: list[ImportedSongCandidate]
    failed: list[tuple[str, str]]       # (source_name, error_msg)
    warnings: list[ImportWarning]
    tempo_source_counts: dict[str, int]  # {"musicxml": N, "midi": N, "default": N}


@dataclass
class MidiUpdateCandidate:
    midi_source: str      # MIDI filename
    matched_path: Path    # path of existing SongModel file
    matched_title: str    # title of existing SongModel
    old_tempo: float
    new_tempo: float


# ── MIDI metadata parser ──────────────────────────────────────────────────────

def parse_midi_metadata(midi_bytes: bytes) -> MidiMetadata:
    """Extract tempo, key signature, and time signature from raw MIDI bytes.

    Uses mido when available; falls back to a pure-Python scanner.
    Only the first occurrence of each meta event type is used (v1 policy).
    """
    try:
        import mido
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes))
        tempo_bpm: float | None = None
        key: str | None = None
        meter: str | None = None
        for track in midi.tracks:
            for msg in track:
                if msg.type == "set_tempo" and tempo_bpm is None:
                    tempo_bpm = round(60_000_000 / msg.tempo, 2)
                elif msg.type == "key_signature" and key is None:
                    key = msg.key
                elif msg.type == "time_signature" and meter is None:
                    meter = f"{msg.numerator}/{msg.denominator}"
        return MidiMetadata(tempo_bpm=tempo_bpm, key=key, meter=meter)
    except Exception:
        return _parse_midi_metadata_raw(midi_bytes)


def _parse_midi_metadata_raw(midi_bytes: bytes) -> MidiMetadata:
    """Pure-Python MIDI meta event scanner (fallback if mido is unavailable)."""
    if len(midi_bytes) < 14 or midi_bytes[:4] != b"MThd":
        return MidiMetadata()

    def _vlq(data: bytes, pos: int) -> tuple[int, int]:
        val = 0
        while pos < len(data):
            b = data[pos]; pos += 1
            val = (val << 7) | (b & 0x7F)
            if not (b & 0x80):
                break
        return val, pos

    n_tracks = int.from_bytes(midi_bytes[10:12], "big")
    pos = 14
    tempo_bpm: float | None = None
    key: str | None = None
    meter: str | None = None

    for _ in range(n_tracks):
        if pos + 8 > len(midi_bytes) or midi_bytes[pos:pos+4] != b"MTrk":
            break
        chunk_len = int.from_bytes(midi_bytes[pos+4:pos+8], "big")
        end = min(pos + 8 + chunk_len, len(midi_bytes))
        pos += 8
        running = 0
        while pos < end:
            _, pos = _vlq(midi_bytes, pos)
            if pos >= end:
                break
            b = midi_bytes[pos]
            if b == 0xFF:  # meta event
                pos += 1
                if pos >= end:
                    break
                meta_type = midi_bytes[pos]; pos += 1
                length, pos = _vlq(midi_bytes, pos)
                payload = midi_bytes[pos:pos+length]; pos += length
                if meta_type == 0x51 and len(payload) >= 3 and tempo_bpm is None:
                    us = int.from_bytes(payload[:3], "big")
                    if us > 0:
                        tempo_bpm = round(60_000_000 / us, 2)
                elif meta_type == 0x58 and len(payload) >= 2 and meter is None:
                    num = payload[0]; den = 2 ** payload[1]
                    meter = f"{num}/{den}"
                elif meta_type == 0x59 and len(payload) >= 2 and key is None:
                    sf = payload[0] if payload[0] < 128 else payload[0] - 256
                    is_minor = payload[1] == 1
                    key = _key_sig_to_str(sf, is_minor)
            elif b & 0x80:
                running = b; pos += 1
                hi = b & 0xF0
                if hi in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                    pos += 2
                elif hi in (0xC0, 0xD0):
                    pos += 1
                elif b in (0xF0, 0xF7):
                    l, pos = _vlq(midi_bytes, pos); pos += l
            else:
                hi = running & 0xF0
                if hi in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                    pos += 2
                elif hi in (0xC0, 0xD0):
                    pos += 1
                else:
                    pos += 1
        pos = end

    return MidiMetadata(tempo_bpm=tempo_bpm, key=key, meter=meter)


_SHARP_MAJ = ["C", "G", "D", "A", "E", "B", "F#", "C#"]
_FLAT_MAJ  = ["C", "F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"]
_SHARP_MIN = ["A", "E", "B", "F#", "C#", "G#", "D#", "A#"]
_FLAT_MIN  = ["A", "D", "G", "C", "F", "Bb", "Eb", "Ab"]


def _key_sig_to_str(sharps_flats: int, is_minor: bool) -> str:
    idx = min(abs(sharps_flats), 7)
    if is_minor:
        root = _SHARP_MIN[idx] if sharps_flats >= 0 else _FLAT_MIN[idx]
        return root + "m"
    return _SHARP_MAJ[idx] if sharps_flats >= 0 else _FLAT_MAJ[idx]


# ── File grouping ─────────────────────────────────────────────────────────────

def group_files_by_basename(
    files: dict[str, bytes],
) -> dict[str, dict[str, bytes]]:
    """Group files by normalised basename. Returns {basename: {".ext": bytes}}.

    Basename is lowercased. Unknown extensions are ignored. .mscx is stored
    but callers should skip it (v1 policy: ignore .mscx).
    """
    groups: dict[str, dict[str, bytes]] = {}
    for name, data in files.items():
        p = Path(name)
        ext = p.suffix.lower()
        if ext not in _KNOWN_EXTS or ext in _IGNORE_EXTS:
            continue  # .mscx and unknown extensions are silently dropped
        base = p.stem.lower()
        groups.setdefault(base, {})[ext] = data
    return groups


# ── ZIP extraction ────────────────────────────────────────────────────────────

def extract_zip(zip_bytes: bytes) -> dict[str, bytes]:
    """Extract files from a ZIP and return {bare filename: bytes}.

    Directory prefixes are stripped; only the file's own name is used.
    """
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            bare = Path(info.filename).name
            if not bare:
                continue
            files[bare] = zf.read(info.filename)
    return files


# ── Key conversion helpers ────────────────────────────────────────────────────

_FIFTHS_TO_KEY = {
    -7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F",
    0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
}


def _musicxml_working_key(imported: ImportedSong) -> tuple[str | None, str]:
    """Extract working_key from ImportedSong's key signature. Returns (key, source)."""
    if imported.initial_key is not None:
        fifths = imported.initial_key.get("fifths", 0)
        key = _FIFTHS_TO_KEY.get(int(fifths))
        if key:
            return key, "musicxml"
    return None, "unknown"


def _midi_working_key(midi_key: str | None) -> str | None:
    """Convert mido key string ('C', 'Em', 'Bb') to working_key (tonic only)."""
    if not midi_key:
        return None
    return midi_key[:-1] if midi_key.endswith("m") else midi_key


# ── Core import: one MusicXML ± MIDI ─────────────────────────────────────────

def import_musicxml_with_midi(
    source_name: str,
    xml_bytes: bytes,
    mid_bytes: bytes | None = None,
    default_tempo: int = DEFAULT_TEMPO,
) -> ImportedSongCandidate:
    """Build one ImportedSongCandidate from MusicXML + optional MIDI.

    Tempo priority: MusicXML → MIDI → default.
    Key/meter: MusicXML preferred; MIDI used as fallback or mismatch warning.
    """
    xml_text = xml_bytes.decode("utf-8", errors="replace")
    imported = import_musicxml_text(xml_text)
    warnings: list[str] = list(imported.warnings)

    midi_meta = parse_midi_metadata(mid_bytes) if mid_bytes else MidiMetadata()

    # Tempo
    xml_tempo = extract_musicxml_tempo(xml_text)
    if xml_tempo is not None:
        tempo = xml_tempo
        tempo_source = "musicxml"
    elif midi_meta.tempo_bpm is not None:
        tempo = midi_meta.tempo_bpm
        tempo_source = "midi"
    else:
        tempo = float(default_tempo)
        tempo_source = "default"

    # Key
    xml_key, key_source = _musicxml_working_key(imported)
    midi_key = _midi_working_key(midi_meta.key)
    if xml_key and midi_key and xml_key != midi_key:
        warnings.append(
            f"key mismatch: MusicXML={xml_key}, MIDI={midi_key}. MusicXML was used."
        )
    working_key = xml_key or midi_key
    if not xml_key and midi_key:
        key_source = "midi"

    # Meter
    xml_ts = imported.initial_time_signature
    midi_meter = midi_meta.meter
    if xml_ts:
        b, bt = xml_ts.get("beats", 4), xml_ts.get("beat_type", 4)
        xml_meter_str = f"{b}/{bt}"
        meter_source = "musicxml"
        if midi_meter and midi_meter != xml_meter_str:
            warnings.append(
                f"meter mismatch: MusicXML={xml_meter_str}, MIDI={midi_meter}. MusicXML was used."
            )
    elif midi_meter:
        meter_source = "midi"
    else:
        meter_source = "default"

    song = imported_song_to_song_model(
        imported, tempo=Fraction(tempo).limit_denominator(1000)
    )
    if working_key:
        from dataclasses import replace
        song = replace(song, working_key=working_key)

    return ImportedSongCandidate(
        source_name=source_name,
        song=song,
        tempo_source=tempo_source,
        key_source=key_source,
        meter_source=meter_source,
        warnings=warnings,
    )


# ── Batch import ──────────────────────────────────────────────────────────────

def import_files(
    files: dict[str, bytes],
    default_tempo: int = DEFAULT_TEMPO,
) -> ImportBundleResult:
    """Import a flat dict of {filename: bytes}.

    Groups by basename, pairs MusicXML with MIDI, and builds SongModel
    candidates. MIDI-only groups are skipped (use find_midi_update_candidates
    for those).
    """
    groups = group_files_by_basename(files)
    songs: list[ImportedSongCandidate] = []
    failed: list[tuple[str, str]] = []
    bundle_warnings: list[ImportWarning] = []
    tempo_counts: dict[str, int] = {"musicxml": 0, "midi": 0, "default": 0}

    for base, exts in sorted(groups.items()):
        xml_bytes: bytes | None = None
        for ext in MUSICXML_EXTS:
            if ext in exts:
                xml_bytes = exts[ext]
                break
        if xml_bytes is None:
            continue  # MIDI-only: handled separately

        mid_bytes: bytes | None = None
        for ext in MIDI_EXTS:
            if ext in exts:
                mid_bytes = exts[ext]
                break

        try:
            candidate = import_musicxml_with_midi(
                source_name=base,
                xml_bytes=xml_bytes,
                mid_bytes=mid_bytes,
                default_tempo=default_tempo,
            )
            songs.append(candidate)
            tempo_counts[candidate.tempo_source] = (
                tempo_counts.get(candidate.tempo_source, 0) + 1
            )
            for w in candidate.warnings:
                bundle_warnings.append(ImportWarning(song_name=base, message=w))
        except Exception as exc:
            failed.append((base, str(exc)))

    return ImportBundleResult(
        songs=songs,
        failed=failed,
        warnings=bundle_warnings,
        tempo_source_counts=tempo_counts,
    )


def import_zip(
    zip_bytes: bytes,
    default_tempo: int = DEFAULT_TEMPO,
) -> ImportBundleResult:
    """Import all songs from a ZIP archive."""
    try:
        files = extract_zip(zip_bytes)
    except Exception as exc:
        return ImportBundleResult(
            songs=[],
            failed=[("(zip)", str(exc))],
            warnings=[],
            tempo_source_counts={},
        )
    return import_files(files, default_tempo=default_tempo)


# ── MIDI-only metadata update ─────────────────────────────────────────────────

def _normalize_for_match(name: str) -> str:
    """Lowercase, strip extension, collapse separators."""
    stem = Path(name).stem.lower()
    for ch in ("-", "_", " "):
        stem = stem.replace(ch, "_")
    return stem


def find_midi_update_candidates(
    midi_files: dict[str, bytes],
    library_entries: list,
) -> tuple[list[MidiUpdateCandidate], list[tuple[str, str]]]:
    """Match MIDI files to existing SongModel library entries.

    Matching order: (1) normalised basename, (2) normalised song title.
    Returns (candidates, unmatched) where unmatched is [(filename, reason)].
    """
    # Build lookup: normalised_name → SongEntry
    norm_to_entry: dict[str, object] = {}
    for entry in library_entries:
        # by filename stem
        norm_to_entry.setdefault(_normalize_for_match(entry.path.stem), entry)
        # by title
        norm_to_entry.setdefault(_normalize_for_match(entry.title), entry)

    candidates: list[MidiUpdateCandidate] = []
    unmatched: list[tuple[str, str]] = []

    for fname, mid_bytes in midi_files.items():
        if Path(fname).suffix.lower() not in MIDI_EXTS:
            continue
        meta = parse_midi_metadata(mid_bytes)
        if meta.tempo_bpm is None:
            unmatched.append((fname, "no tempo information in MIDI"))
            continue
        entry = norm_to_entry.get(_normalize_for_match(fname))
        if entry is None:
            unmatched.append((fname, "no matching song in library"))
            continue
        if entry.song is None:
            unmatched.append((fname, "matched song file could not be loaded"))
            continue
        candidates.append(
            MidiUpdateCandidate(
                midi_source=fname,
                matched_path=entry.path,
                matched_title=entry.title,
                old_tempo=float(entry.song.performance_tempo),
                new_tempo=meta.tempo_bpm,
            )
        )

    return candidates, unmatched
