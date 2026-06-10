"""Public iReal Pro playlist fetching.

Playlists are fetched at runtime from the ireal-musicxml demo server
(https://blog.karimratib.me/demos/chirp/), which hosts the same playlists
available at https://www.irealpro.com/main-playlists/ as plain irealb://
text files.  The data is created and maintained by iReal Pro; the hosting
server is maintained by the ireal-musicxml library author.

Network connection is required.  PlaylistFetchError is raised on any failure
(HTTP error, timeout, unknown name) so the UI can show a clean message.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Sequence

OFFICIAL_PLAYLISTS: Sequence[tuple[str, str]] = (
    ("Jazz 1460", "jazz1460"),
    ("Brazilian 220", "brazilian220"),
    ("Latin 50", "latin50"),
    ("Blues 50", "blues50"),
    ("Pop 400", "pop400"),
    ("Country 50", "country50"),
)

OFFICIAL_PLAYLIST_NAMES: tuple[str, ...] = tuple(name for name, _ in OFFICIAL_PLAYLISTS)

_SOURCE_BASE = "https://blog.karimratib.me/demos/chirp/data/{key}.txt"
DEFAULT_FETCH_TIMEOUT = 30.0
_USER_AGENT = "Mozilla/5.0 (compatible; EUBChanges)"


class PlaylistFetchError(Exception):
    """Raised when an official playlist could not be fetched."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


def fetch_official_playlist(
    playlist_name: str,
    *,
    timeout_seconds: float = DEFAULT_FETCH_TIMEOUT,
) -> bytes:
    """Fetch a named public iReal Pro playlist and return the raw bytes.

    The returned bytes contain a raw irealb:// URI.  The iReal converter
    pipeline accepts this directly (the wrapper regex handles plain text
    as well as HTML-wrapped irealb:// links).

    Raises PlaylistFetchError if the name is unknown or the fetch fails.
    """
    key = next((k for n, k in OFFICIAL_PLAYLISTS if n == playlist_name), None)
    if key is None:
        raise PlaylistFetchError(
            f"Unknown playlist: {playlist_name!r}",
            details=f"Available: {', '.join(OFFICIAL_PLAYLIST_NAMES)}",
        )
    url = _SOURCE_BASE.format(key=key)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise PlaylistFetchError(
            f"Could not fetch playlist (HTTP {exc.code}). Try again later.",
            details=f"{url} — {exc}",
        ) from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise PlaylistFetchError(
            "Could not connect to fetch the playlist. Check your network connection.",
            details=str(exc),
        ) from exc
