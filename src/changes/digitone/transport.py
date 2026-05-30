from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
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


class MidiBackend(Protocol):
    def list_output_ports(self) -> list[MidiPortInfo]:
        ...

    def send_sysex_bytes(self, data: bytes, *, port_name: str) -> None:
        ...


@dataclass(frozen=True)
class FakeSysexSend:
    port_name: str
    byte_count: int
    data: bytes


class MidiTransportError(RuntimeError):
    pass


class MidiPortNotFoundError(MidiTransportError):
    pass


class InvalidSysexDataError(MidiTransportError):
    pass


class HardwareSendNotImplementedError(MidiTransportError):
    pass


class MidiBackendUnavailableError(MidiTransportError):
    pass


class HardwareSendConfirmationRequiredError(MidiTransportError):
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


def _import_mido() -> ModuleType:
    try:
        import mido  # type: ignore
    except ImportError as exc:
        raise MidiBackendUnavailableError(
            "Mido MIDI backend is unavailable. Install optional dependencies with "
            "'pip install .[midi]' (mido + python-rtmidi)."
        ) from exc
    return mido


class FakeMidiBackend:
    def __init__(self, ports: list[MidiPortInfo] | None = None) -> None:
        self._ports = list(ports or [])
        self._sent_messages: list[FakeSysexSend] = []

    def list_output_ports(self) -> list[MidiPortInfo]:
        return list(self._ports)

    @property
    def sent_messages(self) -> list[FakeSysexSend]:
        return list(self._sent_messages)

    def send_sysex_bytes(self, data: bytes, *, port_name: str) -> None:
        select_output_port(self._ports, port_name)
        self._sent_messages.append(
            FakeSysexSend(
                port_name=port_name,
                byte_count=len(data),
                data=bytes(data),
            )
        )


class BackendSysexTransport:
    def __init__(self, backend: MidiBackend) -> None:
        self._backend = backend

    def list_output_ports(self) -> list[MidiPortInfo]:
        return self._backend.list_output_ports()

    def send_sysex(self, data: bytes, *, port_name: str, dry_run: bool = True) -> SysexSendResult:
        validate_sysex_bytes(data)
        select_output_port(self._backend.list_output_ports(), port_name)

        if not dry_run:
            raise HardwareSendNotImplementedError("Hardware SysEx sending is not enabled at application level")

        return SysexSendResult(
            port_name=port_name,
            byte_count=len(data),
            dry_run=True,
            message=f"Backend dry-run only: validated {len(data)} SysEx bytes for {port_name}; no hardware send occurred.",
        )


class GuardedSysexSender:
    def __init__(self, backend: MidiBackend) -> None:
        self._backend = backend

    def send_confirmed_sysex(
        self,
        data: bytes,
        *,
        port_name: str,
        confirmation: bool,
    ) -> SysexSendResult:
        validate_sysex_bytes(data)
        select_output_port(self._backend.list_output_ports(), port_name)

        if not confirmation:
            raise HardwareSendConfirmationRequiredError(
                "Real SysEx send requires explicit confirmation"
            )

        try:
            self._backend.send_sysex_bytes(data, port_name=port_name)
        except MidiTransportError:
            raise
        except Exception as exc:
            raise MidiTransportError(f"MIDI backend send failed: {exc}") from exc

        return SysexSendResult(
            port_name=port_name,
            byte_count=len(data),
            dry_run=False,
            message=f"Guarded real send complete: wrote {len(data)} SysEx bytes to {port_name}.",
        )


class MidoMidiBackend:
    def __init__(self) -> None:
        # Keep import lazy so normal installs/tests do not require mido.
        pass

    def list_output_ports(self) -> list[MidiPortInfo]:
        mido = _import_mido()
        try:
            names = mido.get_output_names()
        except Exception as exc:
            raise MidiTransportError(f"Mido backend failed to list output ports: {exc}") from exc
        return [MidiPortInfo(name=str(name), backend="mido", is_output=True) for name in names]

    def send_sysex_bytes(self, data: bytes, *, port_name: str) -> None:
        validate_sysex_bytes(data)
        mido = _import_mido()
        select_output_port(self.list_output_ports(), port_name)
        payload = list(data[1:-1])
        try:
            message = mido.Message("sysex", data=payload)
            with mido.open_output(port_name) as output_port:
                output_port.send(message)
        except Exception as exc:
            raise MidiTransportError(f"Mido backend failed to send SysEx on '{port_name}': {exc}") from exc


class DryRunSysexTransport:
    def __init__(self, ports: list[MidiPortInfo] | None = None) -> None:
        self._backend = FakeMidiBackend(ports)
        self._transport = BackendSysexTransport(self._backend)

    def list_output_ports(self) -> list[MidiPortInfo]:
        return self._transport.list_output_ports()

    def send_sysex(self, data: bytes, *, port_name: str, dry_run: bool = True) -> SysexSendResult:
        return self._transport.send_sysex(data, port_name=port_name, dry_run=dry_run)
