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
from typing import Callable

from changes.importers.form_expander import FormExpansionResult, expand_form
from changes.importers.musicxml import (
    ImportedSong,
    extract_musicxml_groove,
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
ProgressCallback = Callable[[str, int, int, str], None]

IREAL_JAZZ_STYLE_DEFAULT_TEMPO: dict[str, int] = {
    "Afro": 110,
    "Ballad": 60,
    "Bossa Nova": 140,
    "Calypso": 120,
    "Even 16ths": 90,
    "Even 8ths": 140,
    "Funk": 140,
    "Latin": 180,
    "Latin-Swing": 180,
    "Medium Slow": 120,
    "Medium Swing": 120,
    "Medium Up Swing": 160,
    "Rock Pop": 115,
    "Samba": 200,
    "Slow Rock": 70,
    "Slow Swing": 80,
    "Up Tempo Swing": 240,
    "Waltz": 120,
}

_TEMPO_TIEBREAK_RANK: dict[str, int] = {
    "midi": 0,
    "musicxml": 1,
    "style_default": 2,
}


def _normalize_ireal_style_name(style_name: str) -> str:
    return " ".join(style_name.strip().split()).lower()


_IREAL_STYLE_DEFAULT_BY_NORMALIZED: dict[str, tuple[str, int]] = {
    _normalize_ireal_style_name(style): (style, tempo)
    for style, tempo in IREAL_JAZZ_STYLE_DEFAULT_TEMPO.items()
}


def ireal_style_default_tempo(style_name: str | None) -> tuple[str | None, float | None]:
    if style_name is None:
        return None, None
    normalized = _normalize_ireal_style_name(style_name)
    if not normalized:
        return None, None
    matched = _IREAL_STYLE_DEFAULT_BY_NORMALIZED.get(normalized)
    if matched is None:
        return style_name.strip(), None
    canonical_style, tempo = matched
    return canonical_style, float(tempo)


def choose_import_tempo(
    *,
    musicxml_tempo: float | None,
    style_default_tempo: float | None,
    midi_tempo: float | None,
    default_tempo: int,
) -> tuple[float, str]:
    candidates: list[tuple[str, float]] = []
    if musicxml_tempo is not None:
        candidates.append(("musicxml", float(musicxml_tempo)))
    if style_default_tempo is not None:
        candidates.append(("style_default", float(style_default_tempo)))
    if midi_tempo is not None:
        candidates.append(("midi", float(midi_tempo)))

    if not candidates:
        return float(default_tempo), "default"

    non_120 = [(source, value) for source, value in candidates if value != 120.0]
    pool = non_120 if non_120 else candidates
    source, value = sorted(pool, key=lambda item: _TEMPO_TIEBREAK_RANK[item[0]])[0]
    return float(value), source


def choose_midi_only_update_tempo(
    *,
    existing_tempo: float,
    midi_tempo: float,
) -> tuple[float, str]:
    """Select effective tempo for MIDI-only metadata update.

    Priority:
    - Between existing and MIDI tempos, prefer non-120 candidate.
    - If both are non-120, prefer MIDI tempo.
    - If both are 120, prefer MIDI tempo (effectively unchanged).
    """
    existing = float(existing_tempo)
    midi = float(midi_tempo)

    existing_non_120 = existing != 120.0
    midi_non_120 = midi != 120.0

    if midi_non_120 and not existing_non_120:
        return midi, "midi"
    if existing_non_120 and not midi_non_120:
        return existing, "existing"
    return midi, "midi"

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
    tempo_source: str   # "musicxml" | "style_default" | "midi" | "default"
    key_source: str     # "musicxml" | "midi" | "unknown"
    meter_source: str   # "musicxml" | "midi" | "default"
    warnings: list[str]


@dataclass
class ImportBundleResult:
    songs: list[ImportedSongCandidate]
    failed: list[tuple[str, str]]       # (source_name, error_msg)
    warnings: list[ImportWarning]
    tempo_source_counts: dict[str, int]  # {"musicxml": N, "style_default": N, "midi": N, "default": N}


@dataclass
class MidiUpdateCandidate:
    midi_source: str      # MIDI filename
    matched_path: Path    # path of existing SongModel file
    matched_title: str    # title of existing SongModel
    old_tempo: float
    new_tempo: float


@dataclass
class MidiTempoKeptCandidate:
    midi_source: str
    matched_path: Path
    matched_title: str
    existing_tempo: float
    midi_tempo: float
    reason: str


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

def extract_zip(
    zip_bytes: bytes,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, bytes]:
    """Extract files from a ZIP and return {bare filename: bytes}.

    Directory prefixes are stripped; only the file's own name is used.
    """
    if progress_callback:
        progress_callback("zip_open", 0, 1, "Opening ZIP")
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        infos = zf.infolist()
        total = max(len(infos), 1)
        if progress_callback:
            progress_callback("zip_scan", 0, total, "Scanning ZIP contents")
        for idx, info in enumerate(infos, start=1):
            if info.is_dir():
                if progress_callback:
                    progress_callback("zip_scan", idx, total, f"Skipping directory {info.filename}")
                continue
            bare = Path(info.filename).name
            if not bare:
                if progress_callback:
                    progress_callback("zip_scan", idx, total, f"Skipping unnamed ZIP entry {idx}")
                continue
            if bare not in files:  # first occurrence wins on duplicate bare names
                files[bare] = zf.read(info.filename)
            if progress_callback:
                progress_callback("zip_read", idx, total, f"Read {bare}")
    if progress_callback:
        progress_callback("zip_complete", 1, 1, f"Extracted {len(files)} file(s)")
    return files


# ── Key conversion helpers ────────────────────────────────────────────────────

_FIFTHS_TO_MAJOR = {
    -7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F",
    0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
}

# Relative minor tonic for each major key (parallel: C major → A minor tonic).
_RELATIVE_MINOR_TONIC = {
    "C": "A", "G": "E", "D": "B", "A": "F#", "E": "C#", "B": "G#",
    "F#": "D#", "C#": "A#",
    "F": "D", "Bb": "G", "Eb": "C", "Ab": "F", "Db": "Bb", "Gb": "Eb", "Cb": "Ab",
}


def _musicxml_working_key(imported: ImportedSong) -> tuple[str | None, str | None, str]:
    """Extract working_key and mode from ImportedSong's key signature.

    Returns (working_key, working_key_mode, source).
    For minor mode keys, returns the actual minor tonic (not the relative major),
    e.g. fifths=0, mode=minor → ("A", "minor"), not ("C", "major").
    """
    if imported.initial_key is None:
        return None, None, "unknown"
    fifths = int(imported.initial_key.get("fifths", 0))
    mode = str(imported.initial_key.get("mode", "major")).lower()
    major_key = _FIFTHS_TO_MAJOR.get(fifths)
    if major_key is None:
        return None, None, "unknown"
    if mode == "minor":
        return _RELATIVE_MINOR_TONIC.get(major_key, major_key), "minor", "musicxml"
    return major_key, "major", "musicxml"


def _midi_working_key(midi_key: str | None) -> tuple[str | None, str | None]:
    """Convert mido key string ('C', 'Em', 'Bb') to (working_key, working_key_mode)."""
    if not midi_key:
        return None, None
    if midi_key.endswith("m"):
        return midi_key[:-1], "minor"
    return midi_key, "major"


# ── Core import: one MusicXML ± MIDI ─────────────────────────────────────────

def import_musicxml_with_midi(
    source_name: str,
    xml_bytes: bytes,
    mid_bytes: bytes | None = None,
    default_tempo: int = DEFAULT_TEMPO,
) -> ImportedSongCandidate:
    """Build one ImportedSongCandidate from MusicXML + optional MIDI.

    Tempo selection: non-120 candidate preference with source tiebreak.
    Key/meter: MusicXML preferred; MIDI used as fallback or mismatch warning.
    """
    xml_text = xml_bytes.decode("utf-8", errors="replace")
    imported = import_musicxml_text(xml_text)
    warnings: list[str] = list(imported.warnings)

    midi_meta = parse_midi_metadata(mid_bytes) if mid_bytes else MidiMetadata()

    # Tempo candidates
    xml_tempo = extract_musicxml_tempo(xml_text)
    groove = extract_musicxml_groove(xml_text)
    canonical_style, style_default_tempo = ireal_style_default_tempo(groove)
    midi_tempo = midi_meta.tempo_bpm

    tempo, tempo_source = choose_import_tempo(
        musicxml_tempo=xml_tempo,
        style_default_tempo=style_default_tempo,
        midi_tempo=midi_tempo,
        default_tempo=default_tempo,
    )

    if groove is not None and style_default_tempo is None:
        xml_is_120_or_missing = xml_tempo is None or float(xml_tempo) == 120.0
        midi_is_120_or_missing = midi_tempo is None or float(midi_tempo) == 120.0
        if xml_is_120_or_missing and midi_is_120_or_missing:
            warnings.append(f"Unsupported iReal style default tempo: {groove}")

    # Key
    from changes.key_signature import format_working_key
    xml_key, xml_mode, key_source = _musicxml_working_key(imported)
    midi_key, midi_mode = _midi_working_key(midi_meta.key)
    if xml_key and midi_key and (xml_key != midi_key or xml_mode != midi_mode):
        xml_display = format_working_key(xml_key, xml_mode)
        midi_display = format_working_key(midi_key, midi_mode)
        warnings.append(
            f"key mismatch: MusicXML={xml_display}, MIDI={midi_display}. MusicXML was used."
        )
    working_key = xml_key or midi_key
    working_key_mode = xml_mode if xml_key else midi_mode
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

    # Form expansion
    expansion = expand_form(imported)
    for w in expansion.warnings:
        warnings.append(w)

    # Build expanded ImportedSong for SongModel conversion
    from changes.importers.musicxml import ImportedSong as _ImportedSong
    expanded_imported = _ImportedSong(
        title=imported.title,
        composer=imported.composer,
        source_software=imported.source_software,
        source_musicxml_version=imported.source_musicxml_version,
        initial_key=imported.initial_key,
        initial_time_signature=imported.initial_time_signature,
        bars=expansion.bars,
        raw_form_markers=(),
        warnings=imported.warnings,
    )

    song = imported_song_to_song_model(
        expanded_imported,
        tempo=Fraction(tempo).limit_denominator(1000),
        section_ids=expansion.section_ids,
    )
    if working_key:
        from dataclasses import replace
        song = replace(song, working_key=working_key, working_key_mode=working_key_mode)

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
    progress_callback: ProgressCallback | None = None,
) -> ImportBundleResult:
    """Import a flat dict of {filename: bytes}.

    Groups by basename, pairs MusicXML with MIDI, and builds SongModel
    candidates. MIDI-only groups are skipped (use find_midi_update_candidates
    for those).
    """
    if progress_callback:
        progress_callback("scan_files", 0, max(len(files), 1), "Scanning uploaded files")
    groups = group_files_by_basename(files)
    songs: list[ImportedSongCandidate] = []
    failed: list[tuple[str, str]] = []
    bundle_warnings: list[ImportWarning] = []
    tempo_counts: dict[str, int] = {"musicxml": 0, "style_default": 0, "midi": 0, "default": 0}

    items = sorted(groups.items())
    total = max(len(items), 1)
    for idx, (base, exts) in enumerate(items, start=1):
        if progress_callback:
            progress_callback("parse_file", idx - 1, total, f"Preparing {base}")
        xml_bytes: bytes | None = None
        for ext in MUSICXML_EXTS:
            if ext in exts:
                xml_bytes = exts[ext]
                break
        if xml_bytes is None:
            if progress_callback:
                progress_callback("parse_file", idx, total, f"Skipped MIDI-only group {base}")
            continue  # MIDI-only: handled separately

        mid_bytes: bytes | None = None
        for ext in MIDI_EXTS:
            if ext in exts:
                mid_bytes = exts[ext]
                break

        try:
            if progress_callback:
                progress_callback("songmodel_build", idx - 1, total, f"Building SongModel for {base}")
            candidate = import_musicxml_with_midi(
                source_name=base,
                xml_bytes=xml_bytes,
                mid_bytes=mid_bytes,
                default_tempo=default_tempo,
            )
            if progress_callback:
                progress_callback("validation", idx, total, f"Validated {base}")
            songs.append(candidate)
            tempo_counts[candidate.tempo_source] = (
                tempo_counts.get(candidate.tempo_source, 0) + 1
            )
            for w in candidate.warnings:
                bundle_warnings.append(ImportWarning(song_name=base, message=w))
        except Exception as exc:
            failed.append((base, str(exc)))
            if progress_callback:
                progress_callback("validation", idx, total, f"Failed {base}")

    if progress_callback:
        progress_callback("complete", 1, 1, f"Built {len(songs)} SongModel candidate(s)")
    return ImportBundleResult(
        songs=songs,
        failed=failed,
        warnings=bundle_warnings,
        tempo_source_counts=tempo_counts,
    )


def import_zip(
    zip_bytes: bytes,
    default_tempo: int = DEFAULT_TEMPO,
    progress_callback: ProgressCallback | None = None,
) -> ImportBundleResult:
    """Import all songs from a ZIP archive."""
    try:
        files = extract_zip(zip_bytes, progress_callback=progress_callback)
    except Exception as exc:
        if progress_callback:
            progress_callback("error", 1, 1, f"ZIP extraction failed: {exc}")
        return ImportBundleResult(
            songs=[],
            failed=[("(zip)", str(exc))],
            warnings=[],
            tempo_source_counts={},
        )
    return import_files(files, default_tempo=default_tempo, progress_callback=progress_callback)


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
) -> tuple[list[MidiUpdateCandidate], list[MidiTempoKeptCandidate], list[tuple[str, str]]]:
    """Match MIDI files to existing SongModel library entries.

    Matching order: (1) normalised basename, (2) normalised song title.
    Returns (updates, kept_existing, unmatched) where unmatched is [(filename, reason)].
    """
    # Build lookup: normalised_name → SongEntry
    norm_to_entry: dict[str, object] = {}
    for entry in library_entries:
        # by filename stem
        norm_to_entry.setdefault(_normalize_for_match(entry.path.stem), entry)
        # by title
        norm_to_entry.setdefault(_normalize_for_match(entry.title), entry)

    candidates: list[MidiUpdateCandidate] = []
    kept_existing: list[MidiTempoKeptCandidate] = []
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
        existing_tempo = float(entry.song.performance_tempo)
        selected_tempo, selected_source = choose_midi_only_update_tempo(
            existing_tempo=existing_tempo,
            midi_tempo=float(meta.tempo_bpm),
        )

        if selected_tempo != existing_tempo:
            candidates.append(
                MidiUpdateCandidate(
                    midi_source=fname,
                    matched_path=entry.path,
                    matched_title=entry.title,
                    old_tempo=existing_tempo,
                    new_tempo=selected_tempo,
                )
            )
            continue

        if selected_source == "existing" and float(meta.tempo_bpm) == 120.0 and existing_tempo != 120.0:
            reason = f"MIDI 120 ignored; kept {existing_tempo:.0f}"
        else:
            reason = "unchanged"

        kept_existing.append(
            MidiTempoKeptCandidate(
                midi_source=fname,
                matched_path=entry.path,
                matched_title=entry.title,
                existing_tempo=existing_tempo,
                midi_tempo=float(meta.tempo_bpm),
                reason=reason,
            )
        )

    return candidates, kept_existing, unmatched
