#!/usr/bin/env python3
"""Toggle or set speak_summary.toml enabled (spoken TTS on/off). No daemon restart."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

_ENABLED_LINE = re.compile(
    r"^(\s*)enabled\s*=\s*(true|false)\s*(#.*)?$",
    re.IGNORECASE | re.MULTILINE,
)


def _repo_root() -> Path:
    env = (
        os.environ.get("AFTERTONE_REPO", "").strip()
        or os.environ.get("SUPERTONIC_REPO", "").strip()
    )
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def _toml_path(repo: Path) -> Path:
    return repo / ".cursor" / "hooks" / "speak_summary.toml"


def _read_enabled(toml_path: Path) -> bool:
    with toml_path.open("rb") as f:
        cfg = tomllib.load(f)
    v = cfg.get("enabled", True)
    if isinstance(v, str):
        return v.strip().lower() not in ("0", "false", "no", "off")
    return bool(v)


def _write_enabled(toml_path: Path, enabled: bool) -> None:
    text = toml_path.read_text(encoding="utf-8")
    value = "true" if enabled else "false"
    if _ENABLED_LINE.search(text):
        text = _ENABLED_LINE.sub(
            lambda m: f"{m.group(1)}enabled = {value}{m.group(3) or ''}",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + f"\n\nenabled = {value}\n"
    toml_path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Toggle spoken-summary TTS (speak_summary.toml enabled)."
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=("toggle", "on", "off", "status"),
        default="toggle",
        help="toggle (default), on, off, or status",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Aftertone repo root (default: AFTERTONE_REPO or parent of py/)",
    )
    args = parser.parse_args()
    repo = (args.repo_root or _repo_root()).resolve()
    toml_path = _toml_path(repo)
    if not toml_path.is_file():
        print(f"speak_summary.toml not found: {toml_path}", file=sys.stderr)
        return 1

    current = _read_enabled(toml_path)
    if args.action == "status":
        print("on" if current else "off")
        return 0

    if args.action == "toggle":
        new = not current
    elif args.action == "on":
        new = True
    else:
        new = False

    if new == current and args.action != "toggle":
        print("on" if new else "off")
        return 0

    _write_enabled(toml_path, new)
    label = "on" if new else "off"
    print(label)
    print(f"Spoken summary TTS: {label} ({toml_path})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
