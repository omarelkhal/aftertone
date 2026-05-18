#!/usr/bin/env python3
"""One-line diagnosis when speak_summary_prepare returns {}."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hook_stdin_normalize import decode_hook_bytes, loads_hook_json


def main() -> None:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    try:
        text = decode_hook_bytes(raw)
        d = loads_hook_json(text)
    except json.JSONDecodeError as exc:
        print(f"json_error={exc} bytes={len(raw)}")
        return
    ev = d.get("hook_event_name") or d.get("hookEventName") or "?"
    t = d.get("text") if isinstance(d.get("text"), str) else ""
    print(
        f"event={ev} text_len={len(t)} "
        f"has_spoken_tag={('<spoken_summary>' in t.lower())} "
        f"has_transcript={bool(d.get('transcript_path'))}"
    )


if __name__ == "__main__":
    main()
