"""Supertonic-3 built-in voices — human picker labels; TOML still uses M1, F2, …"""

from __future__ import annotations

# Preset id -> first name (display only; maps to assets/voice_styles/<id>.json).
VOICE_NAMES: dict[str, str] = {
    "F1": "Elena",
    "F2": "Mia",
    "F3": "Claire",
    "F4": "Sara",
    "F5": "Lily",
    "M1": "James",
    "M2": "Marcus",
    "M3": "David",
    "M4": "Noah",
    "M5": "Owen",
}

VOICE_GENDER: dict[str, str] = {
    "F1": "female",
    "F2": "female",
    "F3": "female",
    "F4": "female",
    "F5": "female",
    "M1": "male",
    "M2": "male",
    "M3": "male",
    "M4": "male",
    "M5": "male",
}

DEFAULT_VOICE_ORDER: tuple[str, ...] = (
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
)


def _normalize_id(preset_id: str) -> str:
    return preset_id.strip().removesuffix(".json").upper()


def voice_display_name(preset_id: str) -> str:
    """e.g. Sara (female)"""
    key = _normalize_id(preset_id)
    name = VOICE_NAMES.get(key)
    gender = VOICE_GENDER.get(key)
    if name and gender:
        return f"{name} ({gender})"
    return key


def voice_picker_label(preset_id: str) -> str:
    return voice_display_name(preset_id)


def voice_picker_line(preset_id: str) -> str:
    key = _normalize_id(preset_id)
    return f"{key}|{voice_picker_label(key)}"


def resolve_voice_preset_id(arg: str) -> str | None:
    """Map preset id or human name (e.g. Sara, sara) to canonical id (F4, …)."""
    raw = arg.strip().removesuffix(".json")
    if not raw:
        return None
    key = raw.upper()
    if key in VOICE_NAMES:
        return key
    # Strip optional "(female)" / "(male)" suffixes from pasted labels.
    low = raw.lower()
    for suffix in (" (female)", " (male)", "(female)", "(male)"):
        if low.endswith(suffix):
            low = low[: -len(suffix)].strip()
            break
    for pid, name in VOICE_NAMES.items():
        if low == name.lower():
            return pid
    return None
