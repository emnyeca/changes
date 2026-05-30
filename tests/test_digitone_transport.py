from __future__ import annotations

import sys

import pytest

from changes.digitone.transport import (
    BackendSysexTransport,
    DryRunSysexTransport,
    FakeMidiBackend,
    HardwareSendNotImplementedError,
    InvalidSysexDataError,
    MidoMidiBackend,
    MidiPortInfo,
    MidiPortNotFoundError,
    select_output_port,
    validate_sysex_bytes,
)


def test_validate_sysex_bytes_accepts_wrapped_sysex():
    validate_sysex_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]))


def test_validate_sysex_bytes_rejects_invalid_data():
    with pytest.raises(InvalidSysexDataError):
        validate_sysex_bytes(b"")

    with pytest.raises(InvalidSysexDataError):
        validate_sysex_bytes(bytes([0x7D, 0x00, 0xF7]))

    with pytest.raises(InvalidSysexDataError):
        validate_sysex_bytes(bytes([0xF0, 0x7D, 0x00]))


def test_select_output_port_exact_match():
    ports = [
        MidiPortInfo(name="Other Device"),
        MidiPortInfo(name="Digitone II"),
    ]

    port = select_output_port(ports, "Digitone II")

    assert port.name == "Digitone II"
    assert port.is_output is True


def test_select_output_port_ignores_non_output_ports():
    ports = [MidiPortInfo(name="Digitone II", is_output=False)]

    with pytest.raises(MidiPortNotFoundError):
        select_output_port(ports, "Digitone II")


def test_dry_run_transport_lists_ports():
    ports = [MidiPortInfo(name="Port A"), MidiPortInfo(name="Port B")]
    transport = DryRunSysexTransport(ports)

    assert transport.list_output_ports() == ports


def test_dry_run_transport_send_succeeds():
    transport = DryRunSysexTransport([MidiPortInfo(name="Digitone II")])

    result = transport.send_sysex(
        bytes([0xF0, 0x7D, 0x00, 0xF7]),
        port_name="Digitone II",
        dry_run=True,
    )

    assert result.port_name == "Digitone II"
    assert result.byte_count == 4
    assert result.dry_run is True
    assert "no hardware send occurred" in result.message


def test_dry_run_transport_rejects_missing_port():
    transport = DryRunSysexTransport([MidiPortInfo(name="Digitone II")])

    with pytest.raises(MidiPortNotFoundError):
        transport.send_sysex(
            bytes([0xF0, 0x7D, 0x00, 0xF7]),
            port_name="Missing Port",
            dry_run=True,
        )


def test_dry_run_transport_rejects_dry_run_false():
    transport = DryRunSysexTransport([MidiPortInfo(name="Digitone II")])

    with pytest.raises(HardwareSendNotImplementedError):
        transport.send_sysex(
            bytes([0xF0, 0x7D, 0x00, 0xF7]),
            port_name="Digitone II",
            dry_run=False,
        )


def test_transport_import_does_not_require_midi_backend_dependencies():
    sys.modules.pop("mido", None)
    sys.modules.pop("rtmidi", None)
    sys.modules.pop("python-rtmidi", None)

    from changes.digitone.transport import DryRunSysexTransport as ImportedDryRunSysexTransport
    from changes.digitone.transport import FakeMidiBackend as ImportedFakeMidiBackend
    from changes.digitone.transport import BackendSysexTransport as ImportedBackendSysexTransport
    from changes.digitone.transport import MidoMidiBackend as ImportedMidoMidiBackend

    assert ImportedDryRunSysexTransport.__name__ == "DryRunSysexTransport"
    assert ImportedFakeMidiBackend.__name__ == "FakeMidiBackend"
    assert ImportedBackendSysexTransport.__name__ == "BackendSysexTransport"
    assert ImportedMidoMidiBackend.__name__ == "MidoMidiBackend"
    assert "mido" not in sys.modules
    assert "rtmidi" not in sys.modules


def test_fake_backend_records_send_data():
    backend = FakeMidiBackend([MidiPortInfo(name="Digitone II")])

    backend.send_sysex_bytes(bytes([0xF0, 0x7D, 0x00, 0xF7]), port_name="Digitone II")

    sent = backend.sent_messages
    assert len(sent) == 1
    assert sent[0].port_name == "Digitone II"
    assert sent[0].byte_count == 4


def test_backend_transport_dry_run_does_not_call_backend_send():
    backend = FakeMidiBackend([MidiPortInfo(name="Digitone II")])
    transport = BackendSysexTransport(backend)

    result = transport.send_sysex(
        bytes([0xF0, 0x7D, 0x00, 0xF7]),
        port_name="Digitone II",
        dry_run=True,
    )

    assert result.dry_run is True
    assert result.byte_count == 4
    assert backend.sent_messages == []
