#!/usr/bin/env python3
"""POST a JSON payload file to the local tts_daemon /say endpoint (used by speak_summary.sh)."""

from __future__ import annotations

import sys
import urllib.error
import urllib.request


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: post_say_hook.py <port> <payload.json>", file=sys.stderr)
        raise SystemExit(2)
    port = sys.argv[1].strip()
    path = sys.argv[2]
    with open(path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/say",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(resp.status)
    except urllib.error.HTTPError as e:
        print(f"http_{e.code}", file=sys.stderr)
        raise SystemExit(1) from e
    except OSError as e:
        print(f"connect_error:{e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
