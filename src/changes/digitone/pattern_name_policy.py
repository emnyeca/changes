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


def strip_disallowed_chars(text: str) -> str:
    return "".join(ch for ch in text if ch in ALLOWED_PATTERN_NAME_CHARS)


def normalize_validate_and_truncate_pattern_name(name: str, *, context: str) -> tuple[str, str | None]:
    if not isinstance(name, str):
        raise ValueError(f"{context} must be a string")

    raw = ascii_upper_only(name)
    normalized = strip_disallowed_chars(raw)

    diag: list[str] = []
    if normalized != raw:
        diag.append(f'Unsupported characters stripped from {context}: "{raw}" -> "{normalized}"')

    if len(normalized) <= MAX_PATTERN_NAME_CHARS:
        return normalized, "; ".join(diag) if diag else None

    fitted = normalized[:MAX_PATTERN_NAME_CHARS]
    diag.append(f'Pattern name truncated to 16 characters: "{normalized}" -> "{fitted}"')
    return fitted, "; ".join(diag)


def fit_prefixed_auto_pattern_name(prefix: str, source_title: str) -> tuple[str, str | None]:
    raw_prefix = ascii_upper_only(prefix)
    raw_title = ascii_upper_only(source_title)
    normalized_prefix = strip_disallowed_chars(raw_prefix)
    normalized_title = strip_disallowed_chars(raw_title)

    diag: list[str] = []
    if normalized_prefix != raw_prefix:
        diag.append(f'Unsupported characters stripped from pattern name prefix: "{raw_prefix}" -> "{normalized_prefix}"')
    if normalized_title != raw_title:
        diag.append(f'Unsupported characters stripped from pattern name title: "{raw_title}" -> "{normalized_title}"')

    if not normalized_prefix:
        if len(normalized_title) <= MAX_PATTERN_NAME_CHARS:
            return normalized_title, "; ".join(diag) if diag else None
        fitted = normalized_title[:MAX_PATTERN_NAME_CHARS]
        diag.append(f'Pattern name truncated to 16 characters: "{normalized_title}" -> "{fitted}"')
        return fitted, "; ".join(diag)

    if len(normalized_prefix) >= MAX_PATTERN_NAME_CHARS:
        fitted = normalized_prefix[:MAX_PATTERN_NAME_CHARS]
        diag.append(f'Pattern name truncated to 16 characters: "{normalized_prefix}{normalized_title}" -> "{fitted}"')
        return fitted, "; ".join(diag)

    room = MAX_PATTERN_NAME_CHARS - len(normalized_prefix)
    if len(normalized_title) <= room:
        return normalized_prefix + normalized_title, "; ".join(diag) if diag else None

    fitted = normalized_prefix + normalized_title[:room]
    diag.append(f'Pattern name truncated to 16 characters: "{normalized_prefix}{normalized_title}" -> "{fitted}"')
    return fitted, "; ".join(diag)


def finalize_single_pattern_auto_name(source_title: str) -> tuple[str, tuple[str, ...]]:
    name, warn = fit_prefixed_auto_pattern_name("", source_title)
    if warn is None:
        return name, tuple()
    return name, (warn,)
