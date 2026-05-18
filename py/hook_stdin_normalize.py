#!/usr/bin/env python3
"""Rewrite Cursor hook stdin as UTF-8; parse JSON with Windows path escape fixes."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Cursor on Windows may emit single-backslash paths (invalid JSON: \U in \Users).
_INVALID_JSON_ESCAPE = re.compile(r'(?<!\\)\\(?!["\\/bfnrtu])')


def decode_hook_bytes(raw: bytes) -> str:
    if not raw:
        return ""
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be")
    if len(raw) >= 4 and raw[0] in (0x7B, 0x20, 0x09) and raw[1] == 0:
        return raw.decode("utf-16-le")
    return raw.decode("utf-8-sig", errors="replace")


def loads_hook_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fixed = _INVALID_JSON_ESCAPE.sub(r"\\\\", text)
        return json.loads(fixed)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: hook_stdin_normalize.py <path>", file=sys.stderr)
        raise SystemExit(2)
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    if not raw.strip():
        return
    text = decode_hook_bytes(raw).lstrip("\ufeff")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
