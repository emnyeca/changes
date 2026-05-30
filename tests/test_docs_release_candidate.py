from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rc_docs_exist():
    required = [
        Path("README.md"),
        Path("docs/release-candidate-status.md"),
        Path("docs/validation-status.md"),
        Path("docs/validation-matrix.md"),
        Path("docs/fixture-inventory.md"),
        Path("docs/known-limitations.md"),
        Path("docs/e2e-user-workflow.md"),
        Path("docs/cli.md"),
    ]

    for path in required:
        assert path.exists(), f"Missing required release-candidate doc: {path}"


def test_readme_mentions_safety_boundaries():
    text = _read("README.md")

    assert "Export never sends MIDI" in text
    assert "Check never sends MIDI" in text
    assert "Real-send requires explicit confirmation" in text


def test_known_limitations_avoids_overclaiming():
    text = _read("docs/known-limitations.md")

    assert "Only the II-V-I fixture" in text
    assert "not validate full Digitone payload semantics" in text
    assert "Not a consumer installer" in text


def test_validation_status_links_first_hardware_validation():
    text = _read("docs/validation-status.md")

    assert "digitone-syx-real-send-first-validation.md" in text


def test_validation_status_distinguishes_hardware_software_and_not_yet_validated():
    text = _read("docs/validation-status.md")

    assert "## Hardware validation" in text
    assert "## Software validation" in text
    assert "## Not yet validated" in text
    assert "Software E2E validated fixtures" in text
    assert "Export/manifest validated fixtures" in text


def test_validation_matrix_contains_expected_fixture_rows():
    text = _read("docs/validation-matrix.md")

    assert "demo_cmaj7.changes.yaml" in text
    assert "demo_ii_v_i.changes.yaml" in text
    assert "demo_multibar_turnaround.changes.yaml" in text
    assert "demo_multisection_form.changes.yaml" in text


def test_docs_do_not_overclaim_validation_or_consumer_readiness():
    text = "\n".join(
        [
            _read("README.md"),
            _read("docs/release-candidate-status.md"),
            _read("docs/validation-status.md"),
            _read("docs/known-limitations.md"),
            _read("docs/validation-matrix.md"),
        ]
    ).lower()

    assert "consumer-ready" not in text
    assert "all songmodel inputs supported" not in text
    assert "all duration / len mappings validated" not in text
    assert "all track 8 mappings validated" not in text
    assert "broad hardware validation" not in text


def test_cli_docs_mention_manifest_aware_check_flags():
    text = _read("docs/cli.md")

    assert "--manifest" in text
    assert "--expect-source-title" in text
    assert "--expect-chord-events" in text
    assert "--expect-note-rows" in text


def test_release_candidate_status_has_unchecked_future_items():
    text = _read("docs/release-candidate-status.md")

    assert "- [ ]" in text
