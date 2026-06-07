"""Application resource path utilities.

Use `resource_path()` / `existing_resource_path()` for read-only assets that
are bundled with the app (images, sample data, etc.).
Do NOT use these for user data, library paths, or export destinations.
"""

from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    """Return the application base directory.

    Works in both normal source execution and PyInstaller bundled execution.
    In frozen mode, returns sys._MEIPASS (the unpacked bundle root).
    In source mode, searches upward from this file for the project root.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent

    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
        if (parent / "docs" / "assets").exists() and (parent / "src").exists():
            return parent
    return current.parent


def resource_path(relative_path: str | Path) -> Path:
    """Resolve a bundled read-only resource path from the application base directory."""
    return app_base_dir() / Path(relative_path)


def existing_resource_path(relative_path: str | Path) -> Path | None:
    """Resolve a bundled resource path, returning None if the file does not exist."""
    path = resource_path(relative_path)
    return path if path.exists() else None
