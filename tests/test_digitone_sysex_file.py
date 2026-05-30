from __future__ import annotations

from pathlib import Path

import pytest

from changes.digitone.sysex_file import read_and_validate_sysex_file
from changes.digitone.transport import InvalidSysexDataError


def test_valid_sysex_file_returns_bytes_and_info(tmp_path: Path):
    path = tmp_path / "valid.syx"
    payload = bytes([0xF0, 0x7D, 0x00, 0xF7])
    path.write_bytes(payload)

    data, info = read_and_validate_sysex_file(path)

    assert data == payload
    assert info.path == path
    assert info.byte_count == 4
    assert info.first_byte == 0xF0
    assert info.last_byte == 0xF7


def test_invalid_sysex_raises_invalid_sysex_error(tmp_path: Path):
    path = tmp_path / "invalid.syx"
    path.write_bytes(bytes([0x7D, 0x00, 0xF7]))

    with pytest.raises(InvalidSysexDataError):
        read_and_validate_sysex_file(path)


def test_missing_file_raises_file_not_found(tmp_path: Path):
    path = tmp_path / "missing.syx"

    with pytest.raises(FileNotFoundError):
        read_and_validate_sysex_file(path)


def test_empty_file_raises_invalid_sysex_error(tmp_path: Path):
    path = tmp_path / "empty.syx"
    path.write_bytes(b"")

    with pytest.raises(InvalidSysexDataError):
        read_and_validate_sysex_file(path)
