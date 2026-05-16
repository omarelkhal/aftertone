"""Map spoken-summary flow state to Supertonic 3 inline expression tags."""

from __future__ import annotations

import re

EXPRESSION_MODES = frozenset({"off", "subtle", "expressive", "passthrough"})

# Documented Supertonic 3 examples; unknown tags are stripped in passthrough mode.
KNOWN_EXPRESSION_TAGS = frozenset(
    {
        "laugh",
        "breath",
        "sigh",
        "whisper",
    }
)

_INLINE_TAG_RE = re.compile(r"<([a-z][a-z0-9_]*)>", re.IGNORECASE)

# Flow states from .cursor/rules/spoken-summary.mdc (optional on <spoken_summary>).
VALID_STATES = frozenset(
    {
        "blocked",
        "debugging",
        "shipped",
        "explore",
        "risk",
        "question",
        "test",
    }
)

_SUBTLE_PREFIX: dict[str, str] = {
    "blocked": "sigh",
}

_EXPRESSIVE_PREFIX: dict[str, str] = {
    "blocked": "sigh",
    "debugging": "breath",
}


def normalize_mode(raw: object, *, default: str = "off") -> str:
    mode = str(raw or default).strip().lower()
    if mode not in EXPRESSION_MODES:
        return default
    return mode


def normalize_state(raw: object | None) -> str | None:
    if raw is None:
        return None
    state = str(raw).strip().lower()
    if not state or state not in VALID_STATES:
        return None
    return state


def strip_inline_tags(text: str) -> str:
    """Remove all <tag> tokens (agents should not use these in subtle mode)."""

    def _drop(m: re.Match[str]) -> str:
        name = m.group(1).lower()
        if name in KNOWN_EXPRESSION_TAGS:
            return " "
        return m.group(0)

    return re.sub(r"\s+", " ", _INLINE_TAG_RE.sub(_drop, text)).strip()


def _count_inline_tags(text: str) -> int:
    return sum(
        1
        for m in _INLINE_TAG_RE.finditer(text)
        if m.group(1).lower() in KNOWN_EXPRESSION_TAGS
    )


def sanitize_passthrough(text: str, *, max_tags: int = 1) -> str:
    """Keep at most `max_tags` allowlisted inline tags; drop the rest."""
    seen = 0

    def _keep(m: re.Match[str]) -> str:
        nonlocal seen
        name = m.group(1).lower()
        if name not in KNOWN_EXPRESSION_TAGS:
            return " "
        if seen >= max_tags:
            return " "
        seen += 1
        return m.group(0)

    return re.sub(r"\s+", " ", _INLINE_TAG_RE.sub(_keep, text)).strip()


def apply_expression(
    text: str,
    state: str | None,
    mode: object,
    *,
    default_mode: str = "off",
) -> str:
    """
    Apply Supertonic expression tags to speakable text.

    - off: strip inline tags; no state mapping.
    - subtle: state → at most one prefix tag; strip agent inline tags.
    - expressive: subtle + breath on debugging.
    - passthrough: keep up to one allowlisted inline tag; ignore state.
    """
    text = (text or "").strip()
    if not text:
        return ""

    m = normalize_mode(mode, default=default_mode)
    if m == "off":
        return strip_inline_tags(text)

    if m == "passthrough":
        return sanitize_passthrough(text, max_tags=1)

    text = strip_inline_tags(text)
    st = normalize_state(state)
    if not st:
        return text

    tag: str | None = None
    if m == "expressive":
        tag = _EXPRESSIVE_PREFIX.get(st)
    else:
        tag = _SUBTLE_PREFIX.get(st)

    if not tag:
        return text
    return f"<{tag}> {text}"
