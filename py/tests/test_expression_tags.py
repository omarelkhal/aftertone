"""Unit tests for expression_tags.apply_expression."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from expression_tags import apply_expression, normalize_mode, normalize_state


def test_normalize_mode_invalid() -> None:
    assert normalize_mode("bogus") == "off"
    assert normalize_mode("subtle") == "subtle"


def test_off_strips_inline() -> None:
    out = apply_expression("Done <laugh> now.", None, "off")
    assert "<" not in out
    assert out == "Done now."


def test_subtle_blocked_prefix() -> None:
    out = apply_expression("Daemon is down.", "blocked", "subtle")
    assert out.startswith("<sigh> ")
    assert "<laugh>" not in out


def test_subtle_strips_agent_inline() -> None:
    out = apply_expression("Done <laugh> now.", "shipped", "subtle")
    assert out == "Done now."


def test_expressive_debugging_breath() -> None:
    out = apply_expression("Tracing the hook.", "debugging", "expressive")
    assert out.startswith("<breath> ")


def test_passthrough_keeps_one_tag() -> None:
    out = apply_expression("Wow <laugh> <sigh> end.", None, "passthrough")
    assert out.count("<") == 1
    assert "<laugh>" in out or "<sigh>" in out


def test_normalize_state() -> None:
    assert normalize_state("blocked") == "blocked"
    assert normalize_state("BLOCKED") == "blocked"
    assert normalize_state("nope") is None
