"""Shared Pattern Name policy for Changes Digitone exports."""

from __future__ import annotations

MAX_PATTERN_NAME_CHARS = 16

ALLOWED_PATTERN_NAME_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "\u00c5\u00c4\u00d6\u00dc\u00df\u00c6\u00d8\u00c7\u00d1"
    "0123456789~!@#$%^&()_+-= "
)


def ascii_upper_only(text: str) -> str:
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if 0x61 <= code <= 0x7A:
            out.append(chr(code - 0x20))
        else:
            out.append(ch)
    return "".join(out)


def _validate_allowed_chars(name: str, *, context: str) -> None:
    for ch in name:
        if ch not in ALLOWED_PATTERN_NAME_CHARS:
            raise ValueError(
                f"Unsupported character in {context}: {ch!r} in {name!r}. "
                "Use supported charset only or provide an explicit Pattern Name override."
            )


def normalize_validate_and_truncate_pattern_name(name: str, *, context: str) -> tuple[str, str | None]:
    if not isinstance(name, str):
        raise ValueError(f"{context} must be a string")

    normalized = ascii_upper_only(name)
    _validate_allowed_chars(normalized, context=context)

    if len(normalized) <= MAX_PATTERN_NAME_CHARS:
        return normalized, None

    fitted = normalized[:MAX_PATTERN_NAME_CHARS]
    return fitted, f'Pattern name truncated to 16 characters: "{normalized}" -> "{fitted}"'


def fit_prefixed_auto_pattern_name(prefix: str, source_title: str) -> tuple[str, str | None]:
    normalized_prefix = ascii_upper_only(prefix)
    normalized_title = ascii_upper_only(source_title)

    _validate_allowed_chars(normalized_prefix, context="auto Pattern Name prefix")
    _validate_allowed_chars(normalized_title, context="auto Pattern Name source title")

    if not normalized_prefix:
        if len(normalized_title) <= MAX_PATTERN_NAME_CHARS:
            return normalized_title, None
        fitted = normalized_title[:MAX_PATTERN_NAME_CHARS]
        return fitted, f'Pattern name truncated to 16 characters: "{normalized_title}" -> "{fitted}"'

    if len(normalized_prefix) >= MAX_PATTERN_NAME_CHARS:
        fitted = normalized_prefix[:MAX_PATTERN_NAME_CHARS]
        return fitted, f'Pattern name truncated to 16 characters: "{normalized_prefix}{normalized_title}" -> "{fitted}"'

    room = MAX_PATTERN_NAME_CHARS - len(normalized_prefix)
    if len(normalized_title) <= room:
        return normalized_prefix + normalized_title, None

    fitted = normalized_prefix + normalized_title[:room]
    return fitted, f'Pattern name truncated to 16 characters: "{normalized_prefix}{normalized_title}" -> "{fitted}"'


def finalize_single_pattern_auto_name(source_title: str) -> tuple[str, tuple[str, ...]]:
    name, warn = fit_prefixed_auto_pattern_name("", source_title)
    if warn is None:
        return name, tuple()
    return name, (warn,)
