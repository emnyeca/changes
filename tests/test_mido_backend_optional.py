from __future__ import annotations

import sys
from dataclasses import dataclass

import pytest

import changes.digitone.transport as transport_module
from changes.digitone.transport import (
    BackendSysexTransport,
    HardwareSendNotImplementedError,
    MidiBackendUnavailableError,
    MidiPortInfo,
    MidiPortNotFoundError,
    MidiTransportError,
    MidoMidiBackend,
)


@dataclass
class _FakeMessage:
    type: str
    data: list[int]


class _FakeOutputPort:
    def __init__(self, recorder: dict[str, object], port_name: str):
        self._recorder = recorder
        self._port_name = port_name

    def __enter__(self):
        self._recorder["opened_port"] = self._port_name
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def send(self, message):
        self._recorder["sent_message"] = message


class _FakeMido:
    def __init__(self, output_names: list[str], recorder: dict[str, object], raise_on_open: Exception | None = None):
        self._output_names = output_names
        self._recorder = recorder
        self._raise_on_open = raise_on_open

    def get_output_names(self):
        return list(self._output_names)

    def Message(self, message_type: str, data):
        self._recorder["message_type"] = message_type
        self._recorder["message_data"] = list(data)
        return _FakeMessage(type=message_type, data=list(data))

    def open_output(self, port_name: str):
        self._recorder["open_output_called"] = True
        self._recorder["open_output_port"] = port_name
        if self._raise_on_open is not None:
            raise self._raise_on_open
        return _FakeOutputPort(self._recorder, port_name)


def test_importing_transport_does_not_require_mido():
    sys.modules.pop("mido", None)

    from changes.digitone.transport import MidoMidiBackend as ImportedMidoMidiBackend

    assert ImportedMidoMidiBackend.__name__ == "MidoMidiBackend"
    assert "mido" not in sys.modules


def test_mido_backend_raises_clear_unavailable_error_when_mido_missing(monkeypatch: pytest.MonkeyPatch):
    def _raise_unavailable():
        raise MidiBackendUnavailableError(
            "Mido MIDI backend is unavailable. Install optional dependencies with 'pip install .[midi]' (mido + python-rtmidi)."
        )

    monkeypatch.setattr(transport_module, "_import_mido", _raise_unavailable)

    backend = MidoMidiBackend()
    with pytest.raises(MidiBackendUnavailableError, match=r"mido|python-rtmidi|\[midi\]"):
        backend.list_output_ports()


def test_mido_backend_list_output_ports_uses_mido(monkeypatch: pytest.MonkeyPatch):
    recorder: dict[str, object] = {}
    fake_mido = _FakeMido(["Digitone II", "Other Port"], recorder)
    monkeypatch.setattr(transport_module, "_import_mido", lambda: fake_mido)

    backend = MidoMidiBackend()
    ports = backend.list_output_ports()

    assert len(ports) == 2
    assert ports[0].name == "Digitone II"
    assert ports[1].name == "Other Port"
    assert all(p.backend == "mido" for p in ports)
    assert all(p.is_output is True for p in ports)


def test_mido_backend_send_sysex_excludes_sysex_wrapper_bytes(monkeypatch: pytest.MonkeyPatch):
    recorder: dict[str, object] = {"open_output_called": False}
    fake_mido = _FakeMido(["Digitone II"], recorder)
    monkeypatch.setattr(transport_module, "_import_mido", lambda: fake_mido)

    backend = MidoMidiBackend()
    backend.send_sysex_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]), port_name="Digitone II")

    assert recorder["open_output_port"] == "Digitone II"
    assert recorder["message_type"] == "sysex"
    assert recorder["message_data"] == [0x7D, 0x00]
    sent_message = recorder["sent_message"]
    assert getattr(sent_message, "type") == "sysex"
    assert list(getattr(sent_message, "data")) == [0x7D, 0x00]


def test_mido_backend_rejects_missing_port_before_open_output(monkeypatch: pytest.MonkeyPatch):
    recorder: dict[str, object] = {"open_output_called": False}
    fake_mido = _FakeMido(["Other Port"], recorder)
    monkeypatch.setattr(transport_module, "_import_mido", lambda: fake_mido)

    backend = MidoMidiBackend()

    with pytest.raises(MidiPortNotFoundError):
        backend.send_sysex_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]), port_name="Digitone II")

    assert recorder["open_output_called"] is False


def test_mido_backend_wraps_backend_open_errors(monkeypatch: pytest.MonkeyPatch):
    recorder: dict[str, object] = {"open_output_called": False}
    fake_mido = _FakeMido(["Digitone II"], recorder, raise_on_open=RuntimeError("open failed"))
    monkeypatch.setattr(transport_module, "_import_mido", lambda: fake_mido)

    backend = MidoMidiBackend()

    with pytest.raises(MidiTransportError, match="Mido backend failed to send SysEx"):
        backend.send_sysex_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]), port_name="Digitone II")


def test_optional_real_mido_smoke_list_ports_only():
    pytest.importorskip("mido")
    backend = MidoMidiBackend()

    ports = backend.list_output_ports()

    assert isinstance(ports, list)


def test_backend_transport_with_mido_backend_still_refuses_dry_run_false(monkeypatch: pytest.MonkeyPatch):
    recorder: dict[str, object] = {"open_output_called": False}
    fake_mido = _FakeMido(["Digitone II"], recorder)
    monkeypatch.setattr(transport_module, "_import_mido", lambda: fake_mido)

    transport = BackendSysexTransport(MidoMidiBackend())

    with pytest.raises(HardwareSendNotImplementedError):
        transport.send_sysex(bytes([0xF0, 0x7D, 0x00, 0xF7]), port_name="Digitone II", dry_run=False)

    assert recorder["open_output_called"] is False
