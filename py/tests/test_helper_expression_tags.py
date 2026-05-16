"""Expression-tag preprocessing must not append '.' after <tag>."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helper import load_text_processor


def test_expression_tag_only_no_trailing_period() -> None:
    tp = load_text_processor(str(Path(__file__).resolve().parents[2] / "assets" / "onnx"))
    assert tp._preprocess_text("<sigh>", "en") == "<en><sigh></en>"
    assert tp._preprocess_text("<laugh>", "en") == "<en><laugh></en>"


def test_trailing_expression_tag_no_trailing_period() -> None:
    tp = load_text_processor(str(Path(__file__).resolve().parents[2] / "assets" / "onnx"))
    assert tp._preprocess_text("That worked <laugh>", "en") == "<en>That worked <laugh></en>"


def test_plain_text_still_gets_period() -> None:
    tp = load_text_processor(str(Path(__file__).resolve().parents[2] / "assets" / "onnx"))
    assert tp._preprocess_text("Hello", "en") == "<en>Hello.</en>"
