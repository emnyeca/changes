"""Tests for official playlist fetching.

All network I/O is mocked so CI does not need internet access.
"""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from changes.importers import official_playlists as op


# ── Helpers ───────────────────────────────────────────────────────────────────

_FAKE_IREALB = b"irealb://Test%20Song=Composer==Medium%20Swing=C==data===Jazz%20Test"


def _mock_urlopen(content: bytes):
    """Context manager that returns `content` from urlopen."""
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.return_value = content
    return MagicMock(return_value=resp)


# ── Fetch success ──────────────────────────────────────────────────────────────

def test_fetch_returns_bytes_on_success():
    with patch.object(urllib.request, "urlopen", _mock_urlopen(_FAKE_IREALB)):
        result = op.fetch_official_playlist("Jazz 1460")
    assert result == _FAKE_IREALB


def test_fetch_uses_correct_url():
    captured = {}

    def capturing_urlopen(req, timeout=None):
        captured["url"] = req.full_url if hasattr(req, "full_url") else str(req)
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.read.return_value = _FAKE_IREALB
        return resp

    with patch.object(urllib.request, "urlopen", capturing_urlopen):
        op.fetch_official_playlist("Blues 50")
    assert "blues50.txt" in captured.get("url", "")


# ── Error paths ───────────────────────────────────────────────────────────────

def test_unknown_playlist_raises_error():
    with pytest.raises(op.PlaylistFetchError) as exc_info:
        op.fetch_official_playlist("Nonexistent 999")
    assert "Unknown playlist" in exc_info.value.message
    assert exc_info.value.details


def test_http_error_raises_fetch_error():
    http_err = urllib.error.HTTPError(url="http://x", code=404, msg="Not Found", hdrs=None, fp=None)
    with patch.object(urllib.request, "urlopen", side_effect=http_err):
        with pytest.raises(op.PlaylistFetchError) as exc_info:
            op.fetch_official_playlist("Jazz 1460")
    assert "HTTP 404" in exc_info.value.message
    assert exc_info.value.details


def test_network_error_raises_fetch_error():
    url_err = urllib.error.URLError(reason="Name or service not known")
    with patch.object(urllib.request, "urlopen", side_effect=url_err):
        with pytest.raises(op.PlaylistFetchError) as exc_info:
            op.fetch_official_playlist("Brazilian 220")
    assert "network" in exc_info.value.message.lower() or "connect" in exc_info.value.message.lower()
    assert exc_info.value.details


def test_timeout_raises_fetch_error():
    with patch.object(urllib.request, "urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(op.PlaylistFetchError) as exc_info:
            op.fetch_official_playlist("Jazz 1460", timeout_seconds=1.0)
    assert exc_info.value.details


# ── Playlist catalogue ────────────────────────────────────────────────────────

def test_official_playlist_names_contains_all_six():
    assert len(op.OFFICIAL_PLAYLIST_NAMES) == 6


def test_official_playlist_names_includes_jazz():
    assert "Jazz 1460" in op.OFFICIAL_PLAYLIST_NAMES
