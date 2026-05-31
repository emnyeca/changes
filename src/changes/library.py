"""Song library I/O for EUB Changes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from changes.models.song_model import SongModel, song_model_from_dict, song_model_to_dict

SONG_SUFFIX = ".song.json"


@dataclass
class SongEntry:
    path: Path
    title: str
    song: SongModel | None = None
    error: str | None = None


def list_songs(library: Path) -> list[SongEntry]:
    """Return all .song.json files sorted by title (case-insensitive)."""
    library.mkdir(parents=True, exist_ok=True)
    entries = [_load_entry(p) for p in sorted(library.glob(f"*{SONG_SUFFIX}"))]
    return sorted(entries, key=lambda e: e.title.lower())


def _load_entry(path: Path) -> SongEntry:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        song = song_model_from_dict(data)
        return SongEntry(path=path, title=song.title, song=song)
    except Exception as exc:
        stem = path.stem
        if stem.endswith(".song"):
            stem = stem[: -len(".song")]
        return SongEntry(path=path, title=stem, song=None, error=str(exc))


def save_song(library: Path, song: SongModel) -> Path:
    """Save SongModel to library. Overwrites if same title already exists."""
    library.mkdir(parents=True, exist_ok=True)
    base = _safe_filename(song.title)
    path = library / f"{base}{SONG_SUFFIX}"
    if path.exists():
        try:
            existing = song_model_from_dict(json.loads(path.read_text(encoding="utf-8")))
            if existing.title == song.title:
                _write(path, song)
                return path
        except Exception:
            pass
    if not path.exists():
        _write(path, song)
        return path
    for n in range(2, 9999):
        candidate = library / f"{base} ({n}){SONG_SUFFIX}"
        if not candidate.exists():
            _write(candidate, song)
            return candidate
    raise RuntimeError(f"Too many duplicates for: {base}")


def overwrite_song(path: Path, song: SongModel) -> None:
    _write(path, song)


def delete_song(path: Path) -> None:
    path.unlink(missing_ok=True)


def import_musicxml_bytes(filename: str, data: bytes, tempo: int = 120) -> SongModel:
    """Parse MusicXML bytes and return a SongModel."""
    import tempfile, os
    from changes.importers.musicxml import load_musicxml_song, imported_song_to_song_model

    fd, tmp = tempfile.mkstemp(suffix=".musicxml")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        imported = load_musicxml_song(tmp)
        return imported_song_to_song_model(imported, tempo=Fraction(tempo))
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _write(path: Path, song: SongModel) -> None:
    path.write_text(
        json.dumps(song_model_to_dict(song), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _safe_filename(title: str) -> str:
    safe = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in title).strip()
    return safe or "Untitled"
