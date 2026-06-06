"""Tests for Realtime MIDI Preview worker and state helpers."""
from __future__ import annotations

import queue
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

import pytest

pytest.importorskip("streamlit")

from changes import main_ui
from changes.main_ui import (
    PreviewWorkerResult,
    _PREVIEW_STATE_KEYS,
    _clear_preview_dialog_state,
    _preview_is_running,
    _preview_worker,
    _sync_preview_state,
)


# ── Fake mido helpers ─────────────────────────────────────────────────────────


@dataclass
class _FakeMsg:
    type: str
    note: int = 0
    velocity: int = 0
    channel: int = 0
    control: int = 0
    value: int = 0


class _RecordingPort:
    def __init__(self) -> None:
        self.sent: list[_FakeMsg] = []

    def __enter__(self) -> "_RecordingPort":
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def send(self, msg: _FakeMsg) -> None:
        self.sent.append(msg)


class _FakeMido:
    def __init__(
        self,
        port: _RecordingPort,
        raise_on_open: Exception | None = None,
    ) -> None:
        self._port = port
        self._raise_on_open = raise_on_open

    def Message(self, msg_type: str, **kwargs: Any) -> _FakeMsg:
        return _FakeMsg(type=msg_type, **kwargs)

    def open_output(self, port_name: str) -> _RecordingPort:
        if self._raise_on_open is not None:
            raise self._raise_on_open
        return self._port


class _SessionState(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _fresh_session_state() -> _SessionState:
    return _SessionState({key: default for key, default in _PREVIEW_STATE_KEYS})


# ── Worker tests ──────────────────────────────────────────────────────────────


def _run_worker_sync(
    play_notes: list[tuple[float, float, int, int, str]],
    port: _RecordingPort,
    stop_event: threading.Event,
    *,
    raise_on_open: Exception | None = None,
) -> PreviewWorkerResult:
    """Run _preview_worker in a thread with fake mido; return its result."""
    fake_mido = _FakeMido(port, raise_on_open=raise_on_open)
    result_queue: queue.Queue[PreviewWorkerResult] = queue.Queue()

    original = sys.modules.get("mido", None)
    sys.modules["mido"] = fake_mido  # type: ignore[assignment]
    try:
        t = threading.Thread(
            target=_preview_worker,
            args=(play_notes, "FakePort", stop_event, result_queue),
            daemon=True,
        )
        t.start()
        t.join(timeout=5.0)
    finally:
        if original is None:
            sys.modules.pop("mido", None)
        else:
            sys.modules["mido"] = original

    assert not t.is_alive(), "Worker thread did not finish within timeout"
    return result_queue.get_nowait()


def test_worker_stop_event_exits_loop() -> None:
    """Worker exits promptly when stop_event is set before start."""
    # One note far in the future — worker would block for 60s if stop didn't work
    play_notes = [(60.0, 61.0, 60, 0, "v1")]
    stop_event = threading.Event()
    stop_event.set()

    result = _run_worker_sync(play_notes, _RecordingPort(), stop_event)

    assert result.status == "stopped"


def test_worker_sends_note_off_for_active_notes_on_stop() -> None:
    """Active note gets note_off when stop_event fires mid-playback."""
    # note_on at t=0, note_off scheduled at t=30 (will never arrive naturally)
    play_notes = [(0.0, 30.0, 60, 0, "v1")]
    stop_event = threading.Event()
    port = _RecordingPort()

    fake_mido = _FakeMido(port)
    result_queue: queue.Queue[PreviewWorkerResult] = queue.Queue()

    original = sys.modules.get("mido", None)
    sys.modules["mido"] = fake_mido  # type: ignore[assignment]
    try:
        t = threading.Thread(
            target=_preview_worker,
            args=(play_notes, "FakePort", stop_event, result_queue),
            daemon=True,
        )
        t.start()
        # Wait for at least one loop tick (0.02s) so note_on is dispatched
        time.sleep(0.12)
        stop_event.set()
        t.join(timeout=5.0)
    finally:
        if original is None:
            sys.modules.pop("mido", None)
        else:
            sys.modules["mido"] = original

    assert not t.is_alive()
    types = [m.type for m in port.sent]
    assert "note_on" in types, "note_on should have been sent"
    assert "note_off" in types, "note_off must be sent for active note on stop"

    result = result_queue.get_nowait()
    assert result.status == "stopped"


def test_worker_sends_all_notes_off_cc_for_used_channels() -> None:
    """All Notes Off CC (control=123) is sent for each channel that received a note_on."""
    play_notes = [(0.0, 30.0, 60, 2, "v1")]  # channel 2
    stop_event = threading.Event()
    port = _RecordingPort()

    fake_mido = _FakeMido(port)
    result_queue: queue.Queue[PreviewWorkerResult] = queue.Queue()

    original = sys.modules.get("mido", None)
    sys.modules["mido"] = fake_mido  # type: ignore[assignment]
    try:
        t = threading.Thread(
            target=_preview_worker,
            args=(play_notes, "FakePort", stop_event, result_queue),
            daemon=True,
        )
        t.start()
        time.sleep(0.12)
        stop_event.set()
        t.join(timeout=5.0)
    finally:
        if original is None:
            sys.modules.pop("mido", None)
        else:
            sys.modules["mido"] = original

    cc_msgs = [m for m in port.sent if m.type == "control_change" and m.control == 123]
    channels = {m.channel for m in cc_msgs}
    assert 2 in channels, "All Notes Off CC should be sent for channel 2"


def test_worker_completes_naturally_and_returns_finished() -> None:
    """Worker returns 'finished' when all notes are played without stop."""
    # Very short note: onset=0, offset=0.01 — fits within a single 0.02s tick
    play_notes = [(0.0, 0.01, 60, 0, "v1")]
    stop_event = threading.Event()
    port = _RecordingPort()

    result = _run_worker_sync(play_notes, port, stop_event)

    assert result.status == "finished"
    assert not stop_event.is_set()


def test_worker_captures_error_in_queue() -> None:
    """An exception opening the port is captured as an error result."""
    play_notes = [(0.0, 0.5, 60, 0, "v1")]
    stop_event = threading.Event()
    port = _RecordingPort()

    result = _run_worker_sync(
        play_notes,
        port,
        stop_event,
        raise_on_open=RuntimeError("port unavailable"),
    )

    assert result.status == "error"
    assert result.error is not None
    assert "port unavailable" in result.error
    assert result.traceback is not None


# ── Session state helper tests ────────────────────────────────────────────────


def test_preview_is_running_returns_true_for_running_state(monkeypatch: pytest.MonkeyPatch) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = "running"
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    assert _preview_is_running() is True


def test_preview_is_running_returns_true_for_stopping_state(monkeypatch: pytest.MonkeyPatch) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = "stopping"
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    assert _preview_is_running() is True


@pytest.mark.parametrize("state", ["idle", "finished", "stopped", "error", "debug_log"])
def test_preview_is_running_returns_false_for_inactive_states(
    monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = state
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    assert _preview_is_running() is False


def test_clear_preview_dialog_state_resets_all_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = "error"
    ss["_preview_error"] = "something went wrong"
    ss["_preview_traceback"] = "Traceback..."
    ss["_preview_logs"] = ["line1", "line2"]
    ss["_preview_result_message"] = "Preview error: ..."
    ss["_preview_thread"] = threading.Thread(target=lambda: None)
    ss["_preview_stop_event"] = threading.Event()
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    _clear_preview_dialog_state()

    assert ss["_preview_state"] == "idle"
    assert ss["_preview_error"] is None
    assert ss["_preview_traceback"] is None
    assert ss["_preview_logs"] is None
    assert ss["_preview_result_message"] is None
    assert ss["_preview_thread"] is None
    assert ss["_preview_stop_event"] is None


def test_sync_preview_state_moves_running_to_finished_when_thread_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = "running"

    result_q: queue.Queue[PreviewWorkerResult] = queue.Queue()
    result_q.put(PreviewWorkerResult(status="finished", message="Preview complete."))

    dead_thread = threading.Thread(target=lambda: None)
    dead_thread.start()
    dead_thread.join()

    ss["_preview_thread"] = dead_thread
    ss["_preview_result_queue"] = result_q
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    _sync_preview_state()

    assert ss["_preview_state"] == "finished"
    assert ss["_preview_result_message"] == "Preview complete."
    assert ss["_preview_thread"] is None


def test_sync_preview_state_moves_stopping_to_stopped_when_thread_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = "stopping"

    result_q: queue.Queue[PreviewWorkerResult] = queue.Queue()
    result_q.put(PreviewWorkerResult(status="stopped", message="Preview stopped."))

    dead_thread = threading.Thread(target=lambda: None)
    dead_thread.start()
    dead_thread.join()

    ss["_preview_thread"] = dead_thread
    ss["_preview_result_queue"] = result_q
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    _sync_preview_state()

    assert ss["_preview_state"] == "stopped"
    assert ss["_preview_thread"] is None


def test_sync_preview_state_does_nothing_when_thread_alive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = "running"

    barrier = threading.Barrier(2)

    def _hold() -> None:
        barrier.wait()
        barrier.wait()

    live_thread = threading.Thread(target=_hold, daemon=True)
    live_thread.start()
    barrier.wait()

    ss["_preview_thread"] = live_thread
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    _sync_preview_state()

    assert ss["_preview_state"] == "running", "state must not change while thread is alive"

    barrier.wait()
    live_thread.join(timeout=2.0)


def test_sync_preview_state_captures_error_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ss = _fresh_session_state()
    ss["_preview_state"] = "running"

    result_q: queue.Queue[PreviewWorkerResult] = queue.Queue()
    result_q.put(
        PreviewWorkerResult(
            status="error",
            message="MIDI error: port unavailable",
            error="port unavailable",
            traceback="Traceback (most recent call last):\n  ...",
        )
    )

    dead_thread = threading.Thread(target=lambda: None)
    dead_thread.start()
    dead_thread.join()

    ss["_preview_thread"] = dead_thread
    ss["_preview_result_queue"] = result_q
    monkeypatch.setattr(main_ui.st, "session_state", ss)

    _sync_preview_state()

    assert ss["_preview_state"] == "error"
    assert ss["_preview_error"] == "port unavailable"
    assert ss["_preview_traceback"] is not None
