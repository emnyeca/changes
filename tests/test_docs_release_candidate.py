from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_core_docs_exist():
    required = [
        Path("README.md"),
        Path("docs/product-architecture.md"),
        Path("docs/current-state.md"),
        Path("docs/known-limitations.md"),
        Path("docs/cli.md"),
    ]

    for path in required:
        assert path.exists(), f"Missing required doc: {path}"


def test_readme_mentions_safety_boundaries():
    text = _read("README.md")

    assert "Export never sends MIDI" in text
    assert "Check never sends MIDI" in text
    assert "Real-send requires explicit confirmation" in text


def test_product_docs_include_core_headings():
    readme = _read("README.md")
    architecture = _read("docs/product-architecture.md")
    current_state = _read("docs/current-state.md")

    assert "Cloud" in readme
    assert "Bass" in readme
    assert "Chord" in readme
    assert "レイヤーモデル" in architecture
    assert "Cloud" in architecture
    assert "Bass" in architecture
    assert "Chord" in architecture
    assert "Track 8" in architecture
    assert "Track 8" in current_state


def test_docs_do_not_overclaim_consumer_readiness_or_total_validation():
    text = "\n".join(
        [
            _read("README.md"),
            _read("docs/product-architecture.md"),
            _read("docs/current-state.md"),
            _read("docs/known-limitations.md"),
        ]
    ).lower()

    assert "consumer-ready" not in text
    assert "all songmodel inputs supported" not in text
    assert "all duration / len mappings validated" not in text
    assert "all track 8 mappings validated" not in text
    assert "broad hardware validation" not in text
    assert "track 8 is the main product feature" not in text


def test_cli_docs_mention_manifest_aware_check_flags():
    text = _read("docs/cli.md")

    assert "--manifest" in text
    assert "--expect-source-title" in text
    assert "--expect-chord-events" in text
    assert "--expect-note-rows" in text
