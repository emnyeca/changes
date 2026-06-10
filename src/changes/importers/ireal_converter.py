"""iReal Pro → MusicXML conversion via the bundled ireal-musicxml external tool.

EUB Changes does not port ireal-musicxml to Python. Conversion runs in a Node
subprocess using `tools/eub-ireal-wrapper.mjs`, which imports the bundled
self-contained `build/ireal-musicxml.mjs`. The converted MusicXML is then fed
to the existing MusicXML import pipeline (import_bundle.import_files), so
SongModel generation, warnings, and save flow stay identical to a normal
MusicXML import.

Tool discovery order (Node and ireal-musicxml independently):
1. Explicit environment variable (EUB_CHANGES_NODE_EXE / EUB_CHANGES_IREAL_MUSICXML_DIR)
2. Bundled path under the app base dir (works for both repo checkout and
   PyInstaller _MEIPASS, because BuildDesktop.ps1 add-data keeps the same
   relative layout: tools/bundled/...)
3. Node only: `node` on PATH (development fallback)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from changes.path_utils import resource_path

NODE_EXE_ENV = "EUB_CHANGES_NODE_EXE"
IREAL_MUSICXML_DIR_ENV = "EUB_CHANGES_IREAL_MUSICXML_DIR"

_BUNDLED_NODE_DIR = Path("tools/bundled/node")
_BUNDLED_IREAL_DIR = Path("tools/bundled/ireal-musicxml")
_WRAPPER_RELATIVE = Path("tools/eub-ireal-wrapper.mjs")
_IREAL_LIB_RELATIVE = Path("build/ireal-musicxml.mjs")

IREAL_HTML_EXTS = frozenset({".html", ".htm"})

DEFAULT_TIMEOUT_SECONDS = 20.0
PLAYLIST_TIMEOUT_SECONDS = 120.0

ProgressCallback = Callable[[str, int, int, str], None]


class IRealConversionError(Exception):
    """iReal conversion failed. `message` is short and UI-ready; `details` holds
    converter output for an expander."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or ""


class IRealToolNotFoundError(IRealConversionError):
    """Bundled Node or ireal-musicxml could not be located."""


@dataclass(frozen=True)
class IRealConversionResult:
    musicxml_text: str
    warnings: tuple[str, ...]
    source_label: str | None = None


@dataclass(frozen=True)
class IRealPlaylistConversion:
    songs: tuple[IRealConversionResult, ...]
    warnings: tuple[str, ...]


# ── Tool discovery ────────────────────────────────────────────────────────────

def find_node_exe() -> Path | None:
    env_value = os.environ.get(NODE_EXE_ENV)
    if env_value:
        candidate = Path(env_value)
        return candidate if candidate.is_file() else None

    exe_name = "node.exe" if sys.platform == "win32" else "node"
    bundled = resource_path(_BUNDLED_NODE_DIR / exe_name)
    if bundled.is_file():
        return bundled

    which = shutil.which("node")
    return Path(which) if which else None


def find_ireal_musicxml_lib() -> Path | None:
    env_value = os.environ.get(IREAL_MUSICXML_DIR_ENV)
    if env_value:
        env_path = Path(env_value)
        if env_path.is_file():  # allow pointing directly at the .mjs bundle
            return env_path
        lib = env_path / _IREAL_LIB_RELATIVE
        return lib if lib.is_file() else None

    bundled = resource_path(_BUNDLED_IREAL_DIR / _IREAL_LIB_RELATIVE)
    return bundled if bundled.is_file() else None


def find_wrapper_script() -> Path | None:
    wrapper = resource_path(_WRAPPER_RELATIVE)
    return wrapper if wrapper.is_file() else None


def bundled_ireal_available() -> bool:
    return (
        find_node_exe() is not None
        and find_ireal_musicxml_lib() is not None
        and find_wrapper_script() is not None
    )


def _resolve_tools() -> tuple[Path, Path, Path]:
    node = find_node_exe()
    if node is None:
        raise IRealToolNotFoundError(
            "iReal converter is not available. Bundled Node.js was not found.",
            details=(
                f"Set {NODE_EXE_ENV} or place node.exe under {_BUNDLED_NODE_DIR}/ "
                "(scripts/PrepareBundledIRealMusicXML.ps1 -IncludeNode)."
            ),
        )
    lib = find_ireal_musicxml_lib()
    if lib is None:
        raise IRealToolNotFoundError(
            "iReal converter is not available. Bundled ireal-musicxml was not found.",
            details=(
                f"Set {IREAL_MUSICXML_DIR_ENV} or run "
                "scripts/PrepareBundledIRealMusicXML.ps1 to stage "
                f"{_BUNDLED_IREAL_DIR}/{_IREAL_LIB_RELATIVE}."
            ),
        )
    wrapper = find_wrapper_script()
    if wrapper is None:
        raise IRealToolNotFoundError(
            "iReal converter is not available. eub-ireal-wrapper.mjs was not found.",
            details=f"Expected at {resource_path(_WRAPPER_RELATIVE)}.",
        )
    return node, wrapper, lib


# ── Subprocess conversion ─────────────────────────────────────────────────────

def _run_converter(ireal_text: str, timeout_seconds: float) -> tuple[str, str]:
    """Run the Node wrapper on `ireal_text`. Returns (stdout, stderr) text.

    The input goes through a temp file (always cleaned up) to avoid Windows
    command-line length and encoding limits with large playlists / irealb URIs.
    """
    node, wrapper, lib = _resolve_tools()

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0

    with tempfile.TemporaryDirectory(prefix="eub_ireal_", ignore_cleanup_errors=True) as tmp_dir:
        input_path = Path(tmp_dir) / "ireal-input.html"
        input_path.write_text(ireal_text, encoding="utf-8")
        try:
            completed = subprocess.run(
                [
                    str(node),
                    str(wrapper),
                    "--lib", str(lib),
                    "--input", str(input_path),
                ],
                capture_output=True,
                timeout=timeout_seconds,
                creationflags=creationflags,
            )
        except subprocess.TimeoutExpired as exc:
            stderr_text = (exc.stderr or b"").decode("utf-8", errors="replace")
            raise IRealConversionError(
                f"iReal conversion timed out after {timeout_seconds:.0f} seconds.",
                details=stderr_text,
            ) from exc
        except OSError as exc:
            raise IRealConversionError(
                "iReal converter could not be started.",
                details=str(exc),
            ) from exc

    stdout_text = completed.stdout.decode("utf-8", errors="replace")
    stderr_text = completed.stderr.decode("utf-8", errors="replace")

    if completed.returncode != 0:
        raise IRealConversionError(
            "Invalid iReal input: the converter could not read it as iReal Pro data.",
            details=stderr_text.strip() or f"exit code {completed.returncode}",
        )
    return stdout_text, stderr_text


def _parse_converter_output(stdout_text: str, stderr_text: str) -> IRealPlaylistConversion:
    warnings = tuple(line for line in stderr_text.splitlines() if line.strip())

    if not stdout_text.strip():
        raise IRealConversionError(
            "The iReal converter returned no MusicXML.",
            details=stderr_text,
        )
    try:
        payload = json.loads(stdout_text)
        entries = payload["songs"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise IRealConversionError(
            "The iReal converter returned unexpected output.",
            details=f"{exc}\n--- stdout head ---\n{stdout_text[:500]}",
        ) from exc

    songs = tuple(
        IRealConversionResult(
            musicxml_text=str(entry["musicxml"]),
            warnings=(),
            source_label=str(entry.get("title") or "") or None,
        )
        for entry in entries
        if isinstance(entry, dict) and entry.get("musicxml")
    )
    if not songs:
        raise IRealConversionError(
            "The iReal converter returned no MusicXML.",
            details=stderr_text,
        )
    return IRealPlaylistConversion(songs=songs, warnings=warnings)


def convert_ireal_playlist_to_musicxml(
    ireal_text: str,
    *,
    timeout_seconds: float = PLAYLIST_TIMEOUT_SECONDS,
) -> IRealPlaylistConversion:
    """Convert iReal Pro input (song or playlist html / irealb:// text) to MusicXML.

    Returns every song in the input. Converter stderr lines are returned as
    playlist-level warnings (per-song attribution is not reliable upstream).
    """
    stdout_text, stderr_text = _run_converter(ireal_text, timeout_seconds)
    return _parse_converter_output(stdout_text, stderr_text)


def convert_ireal_to_musicxml(
    ireal_text: str,
    *,
    song_selector: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> IRealConversionResult:
    """Convert iReal Pro input and return a single song.

    `song_selector` filters by case-insensitive title substring. Without a
    selector, a single-song input returns that song; a playlist raises so the
    caller can fall back to convert_ireal_playlist_to_musicxml.
    """
    conversion = convert_ireal_playlist_to_musicxml(ireal_text, timeout_seconds=timeout_seconds)
    songs = conversion.songs
    if song_selector is not None:
        needle = song_selector.strip().lower()
        songs = tuple(s for s in songs if needle in (s.source_label or "").lower())
        if not songs:
            raise IRealConversionError(
                f"No song matching '{song_selector}' was found in the iReal input.",
                details="\n".join(s.source_label or "(untitled)" for s in conversion.songs),
            )
    elif len(songs) > 1:
        raise IRealConversionError(
            "The iReal input is a playlist with multiple songs but no song was selected.",
            details="\n".join(s.source_label or "(untitled)" for s in songs),
        )
    selected = songs[0]
    return IRealConversionResult(
        musicxml_text=selected.musicxml_text,
        warnings=conversion.warnings,
        source_label=selected.source_label,
    )


# ── Import pipeline bridge ────────────────────────────────────────────────────

def is_ireal_html_name(name: str) -> bool:
    return Path(name).suffix.lower() in IREAL_HTML_EXTS


_FILENAME_UNSAFE = '\\/:*?"<>|'


def _title_to_entry_name(title: str | None, fallback: str, taken: set[str]) -> str:
    base = (title or "").strip() or Path(fallback).stem
    base = "".join("_" if (c in _FILENAME_UNSAFE or ord(c) < 32) else c for c in base)
    name = f"{base}.musicxml"
    counter = 2
    while name.lower() in taken:
        name = f"{base} ({counter}).musicxml"
        counter += 1
    taken.add(name.lower())
    return name


def expand_ireal_inputs(
    file_data: dict[str, bytes],
    *,
    timeout_seconds: float = PLAYLIST_TIMEOUT_SECONDS,
    progress_callback: ProgressCallback | None = None,
) -> tuple[dict[str, bytes], list[tuple[str, str]], list[tuple[str, str]]]:
    """Replace iReal html entries in `file_data` with converted MusicXML entries.

    Returns (new_file_data, warnings, failed) where warnings and failed are
    [(source html name, message)]. Tool-not-found and conversion errors land in
    `failed` per file — the app keeps running and the existing import flow
    reports them.
    """
    expanded: dict[str, bytes] = {}
    warnings: list[tuple[str, str]] = []
    failed: list[tuple[str, str]] = []
    taken = {name.lower() for name in file_data if not is_ireal_html_name(name)}

    ireal_names = [name for name in file_data if is_ireal_html_name(name)]
    total = max(len(ireal_names), 1)
    done = 0

    for name, data in file_data.items():
        if not is_ireal_html_name(name):
            expanded[name] = data
            continue
        if progress_callback:
            progress_callback("parse_file", done, total, f"Converting iReal {name}")
        try:
            conversion = convert_ireal_playlist_to_musicxml(
                data.decode("utf-8", errors="replace"),
                timeout_seconds=timeout_seconds,
            )
        except IRealConversionError as exc:
            detail = f" ({exc.details.strip()})" if exc.details.strip() else ""
            failed.append((name, f"{exc.message}{detail}"))
            done += 1
            continue
        for song in conversion.songs:
            entry_name = _title_to_entry_name(song.source_label, name, taken)
            expanded[entry_name] = song.musicxml_text.encode("utf-8")
        for line in conversion.warnings:
            warnings.append((name, line))
        done += 1
        if progress_callback:
            progress_callback(
                "parse_file", done, total,
                f"Converted {name}: {len(conversion.songs)} song(s)",
            )

    return expanded, warnings, failed
