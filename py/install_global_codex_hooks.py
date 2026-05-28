#!/usr/bin/env python3
"""Register Aftertone user-level Codex hooks (~/.codex/hooks.json)."""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
import time
from pathlib import Path

_MARKER = "aftertone-codex-speak-on-stop"
_STOP_SH = "aftertone-codex-speak-on-stop.sh"
_STOP_CMD = "aftertone-codex-speak-on-stop.cmd"


def _strip_aftertone_entries(hooks: dict) -> dict:
    out: dict = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            out[event] = entries
            continue
        kept = [
            h
            for h in entries
            if isinstance(h, dict) and _MARKER not in (h.get("command") or "")
        ]
        if kept:
            out[event] = kept
    return out


def _merge_codex_hooks(existing: dict, fragment: dict) -> dict:
    out = dict(existing)
    hooks = _strip_aftertone_entries(dict(out.get("hooks") or {}))
    frag_hooks = fragment.get("hooks") or {}
    for event, entries in frag_hooks.items():
        cur = list(hooks.get(event) or [])
        seen = {h.get("command") for h in cur if isinstance(h, dict)}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("command") in seen:
                continue
            cur.append(entry)
            seen.add(entry.get("command"))
        hooks[event] = cur
    out["hooks"] = hooks
    return out


def _fragment_path(template_dir: Path) -> Path:
    if sys.platform == "win32":
        win = template_dir / "hooks.windows.json"
        if win.is_file():
            return win
    return template_dir / "hooks.json"


def _substitute_commands(obj: object, stop_sh: str, stop_cmd: str) -> object:
    if isinstance(obj, dict):
        return {k: _substitute_commands(v, stop_sh, stop_cmd) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_commands(x, stop_sh, stop_cmd) for x in obj]
    if isinstance(obj, str):
        return (
            obj.replace("__AFTERTONE_CODEX_STOP__", stop_sh)
            .replace("__AFTERTONE_CODEX_STOP_CMD__", stop_cmd)
        )
    return obj
