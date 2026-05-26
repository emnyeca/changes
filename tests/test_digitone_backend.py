from pathlib import Path
import sys

import pytest

from changes import digitone_backend


def test_wrapper_reports_dependency_error_when_toolkit_missing(monkeypatch):
    monkeypatch.setattr(
        digitone_backend.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ModuleNotFoundError("digitone_syx_toolkit")),
    )

    with pytest.raises(ModuleNotFoundError, match="digitone-syx-toolkit"):
        digitone_backend._load_toolkit_builder()


def test_wrapper_calls_toolkit_builder(monkeypatch, tmp_path: Path):
    calls = {}

    class _Result:
        output_file = Path("out.syx")

    def _fake_builder(*, events_yaml, output_file):
        calls["events_yaml"] = Path(events_yaml)
        calls["output_file"] = Path(output_file)
        calls["called"] = True
        return _Result()

    monkeypatch.setattr(digitone_backend, "_load_toolkit_builder", lambda: _fake_builder)

    result = digitone_backend.build_digitone_syx_from_events_yaml(
        tmp_path / "sample.events.yaml",
        tmp_path / "sample.syx",
    )

    assert calls["called"] is True
    assert calls["events_yaml"].name == "sample.events.yaml"
    assert calls["output_file"].name == "sample.syx"
    assert result.output_file == Path("out.syx")


def test_wrapper_integration_with_local_toolkit_if_available(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    toolkit_src = repo_root / "digitone-syx-toolkit" / "src"
    events_yaml = repo_root / "digitone-syx-toolkit" / "captures" / "generated" / "events" / "trial1_minimal_trigger.events.yaml"

    if not toolkit_src.exists() or not events_yaml.exists():
        pytest.skip("Local digitone-syx-toolkit fixture is not available")

    sys.path.insert(0, str(toolkit_src))
    try:
        out = tmp_path / "trial1_from_changes.syx"
        result = digitone_backend.build_digitone_syx_from_events_yaml(events_yaml, out)
        assert out.exists()
        assert out.stat().st_size > 0
        assert Path(result.output_file).name == out.name
    finally:
        if str(toolkit_src) in sys.path:
            sys.path.remove(str(toolkit_src))
