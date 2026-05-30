from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MidiPortInfo:
    name: str
    backend: str | None = None
    is_output: bool = True


@dataclass(frozen=True)
class SysexSendResult:
    port_name: str
    byte_count: int
    dry_run: bool
    message: str


class SysexTransport(Protocol):
    def list_output_ports(self) -> list[MidiPortInfo]:
        ...

    def send_sysex(self, data: bytes, *, port_name: str, dry_run: bool = True) -> SysexSendResult:
        ...


class MidiTransportError(RuntimeError):
    pass


class MidiPortNotFoundError(MidiTransportError):
    pass


class InvalidSysexDataError(MidiTransportError):
    pass


class HardwareSendNotImplementedError(MidiTransportError):
    pass


def validate_sysex_bytes(data: bytes) -> None:
    if not data:
        raise InvalidSysexDataError("SysEx data must not be empty")
    if data[0] != 0xF0:
        raise InvalidSysexDataError("SysEx data must start with 0xF0")
    if data[-1] != 0xF7:
        raise InvalidSysexDataError("SysEx data must end with 0xF7")


def select_output_port(ports: list[MidiPortInfo], port_name: str) -> MidiPortInfo:
    for port in ports:
        if port.name == port_name and port.is_output:
            return port
    raise MidiPortNotFoundError(f'Output port not found: {port_name}')


class DryRunSysexTransport:
    def __init__(self, ports: list[MidiPortInfo] | None = None) -> None:
        self._ports = list(ports or [])

    def list_output_ports(self) -> list[MidiPortInfo]:
        return list(self._ports)

    def send_sysex(self, data: bytes, *, port_name: str, dry_run: bool = True) -> SysexSendResult:
        if not dry_run:
            raise HardwareSendNotImplementedError("Hardware SysEx sending is not implemented in Phase 6A")

        validate_sysex_bytes(data)
        select_output_port(self._ports, port_name)

        return SysexSendResult(
            port_name=port_name,
            byte_count=len(data),
            dry_run=True,
            message=f"Dry-run only: validated {len(data)} SysEx bytes for {port_name}; no hardware send occurred.",
        )
