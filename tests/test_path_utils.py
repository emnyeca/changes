"""Tests for changes.path_utils."""

from __future__ import annotations

from pathlib import Path

from changes.path_utils import app_base_dir, existing_resource_path, resource_path


def test_app_base_dir_returns_project_root():
    base = app_base_dir()
    assert (base / "pyproject.toml").exists(), f"pyproject.toml not found under {base}"


def test_resource_path_resolves_from_base():
    base = app_base_dir()
    result = resource_path("docs/assets")
    assert result == base / "docs" / "assets"


def test_existing_resource_path_returns_path_when_present():
    result = existing_resource_path("pyproject.toml")
    assert result is not None
    assert result.exists()


def test_existing_resource_path_returns_none_when_missing():
    result = existing_resource_path("does/not/exist.png")
    assert result is None


def test_resource_path_accepts_path_object():
    result = resource_path(Path("pyproject.toml"))
    assert isinstance(result, Path)
