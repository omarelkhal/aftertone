"""Tests for voice_presets display names."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_presets import (
    resolve_voice_preset_id,
    voice_display_name,
    voice_picker_label,
    voice_picker_line,
)


def test_display_name_includes_gender():
    assert voice_display_name("F4") == "Sara (female)"
    assert voice_display_name("M1") == "James (male)"


def test_picker_label():
    assert voice_picker_label("F4") == "Sara (female)"
    assert voice_picker_line("M3") == "M3|David (male)"


def test_resolve_by_human_name():
    assert resolve_voice_preset_id("Sara") == "F4"
    assert resolve_voice_preset_id("sara") == "F4"
    assert resolve_voice_preset_id("Sara (female)") == "F4"
    assert resolve_voice_preset_id("James") == "M1"
    assert resolve_voice_preset_id("f4") == "F4"


def test_resolve_unknown():
    assert resolve_voice_preset_id("not-a-voice") is None
