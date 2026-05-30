from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .transport import validate_sysex_bytes


@dataclass(frozen=True)
class SysexFileInfo:
    path: Path
    byte_count: int
    first_byte: int
    last_byte: int


def read_and_validate_sysex_file(path: str | Path) -> tuple[bytes, SysexFileInfo]:
    src = Path(path)
    data = src.read_bytes()
    validate_sysex_bytes(data)

    info = SysexFileInfo(
        path=src,
        byte_count=len(data),
        first_byte=data[0],
        last_byte=data[-1],
    )
    return data, info
