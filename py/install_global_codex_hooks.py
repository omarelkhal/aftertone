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
        kept = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # Legacy flat command form from early Codex adapter builds.
            if _MARKER in (entry.get("command") or ""):
                continue
            nested = entry.get("hooks")
            if isinstance(nested, list):
                nested_kept = [
                    h
                    for h in nested
                    if not (
                        isinstance(h, dict)
                        and _MARKER in (h.get("command") or "")
                    )
                ]
                if nested_kept:
                    next_entry = dict(entry)
                    next_entry["hooks"] = nested_kept
                    kept.append(next_entry)
                continue
            kept.append(entry)
        if kept:
            out[event] = kept
    return out


def _commands(entry: dict) -> list[str]:
    command = entry.get("command")
    if isinstance(command, str):
        return [command]
    nested = entry.get("hooks")
    if not isinstance(nested, list):
        return []
    return [
        h.get("command")
        for h in nested
        if isinstance(h, dict) and isinstance(h.get("command"), str)
    ]


def _merge_codex_hooks(existing: dict, fragment: dict) -> dict:
    out = dict(existing)
    hooks = _strip_aftertone_entries(dict(out.get("hooks") or {}))
    frag_hooks = fragment.get("hooks") or {}
    for event, entries in frag_hooks.items():
        cur = list(hooks.get(event) or [])
        seen = {cmd for h in cur if isinstance(h, dict) for cmd in _commands(h)}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_commands = _commands(entry)
            if any(cmd in seen for cmd in entry_commands):
                continue
            cur.append(entry)
            seen.update(entry_commands)
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


def install_global_codex(*, install_dir: Path, dry_run: bool = False) -> None:
    install_dir = install_dir.expanduser().resolve()
    marker = install_dir / "py" / "speak_summary_prepare.py"
    if not marker.is_file():
        raise SystemExit(f"not an Aftertone install: {install_dir}")

    template_dir = install_dir / "scripts" / "codex-global"
    stop_src = template_dir / _STOP_SH
    stop_cmd_src = template_dir / _STOP_CMD
    fragment_src = _fragment_path(template_dir)
    if not stop_src.is_file() or not fragment_src.is_file():
        raise SystemExit(f"missing templates under {template_dir}")

    user_codex = Path.home() / ".codex"
    user_hooks = Path.home() / ".cursor" / "hooks"
    hooks_json = user_codex / "hooks.json"
    dest_stop = user_hooks / _STOP_SH
    dest_cmd = user_hooks / _STOP_CMD

    stop_command = f'bash "{dest_stop.resolve()}"'
    cmd_command = str(dest_cmd.resolve())

    if dry_run:
        print(f"would copy {stop_src} -> {dest_stop}")
        print(f"would merge {hooks_json}")
        return

    user_hooks.mkdir(parents=True, exist_ok=True)
    user_codex.mkdir(parents=True, exist_ok=True)
    shutil.copy2(stop_src, dest_stop)
    if sys.platform != "win32":
        dest_stop.chmod(
            dest_stop.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
    if stop_cmd_src.is_file():
        shutil.copy2(stop_cmd_src, dest_cmd)

    fragment = json.loads(fragment_src.read_text(encoding="utf-8-sig"))
    fragment = _substitute_commands(fragment, stop_command, cmd_command)
    if hooks_json.is_file():
        existing = json.loads(hooks_json.read_text(encoding="utf-8-sig"))
        backup = hooks_json.with_suffix(f".json.bak.{int(time.time())}")
        shutil.copy2(hooks_json, backup)
        merged = _merge_codex_hooks(existing, fragment)
        print(f"backup: {backup}")
    else:
        merged = fragment

    hooks_json.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")

    rule_src = template_dir / "AGENTS.md"
    if rule_src.is_file():
        shutil.copy2(rule_src, user_codex / "AGENTS.md")

    commands_src = template_dir / "commands"
    if commands_src.is_dir():
        commands_dest = user_codex / "commands"
        commands_dest.mkdir(parents=True, exist_ok=True)
        for cmd in sorted(commands_src.glob("aftertone-*.md")):
            shutil.copy2(cmd, commands_dest / cmd.name)

    prompts_src = template_dir / "prompts"
    if prompts_src.is_dir():
        prompts_dest = user_codex / "prompts"
        prompts_dest.mkdir(parents=True, exist_ok=True)
        for prompt in sorted(prompts_src.glob("aftertone-*.md")):
            shutil.copy2(prompt, prompts_dest / prompt.name)

    print(f"Global Codex hooks: {hooks_json}")
    print(f"Install root: {install_dir}")


def main() -> None:
    p = argparse.ArgumentParser(description="Install Aftertone user-level Codex hooks.")
    p.add_argument("--install-dir", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    install_global_codex(install_dir=args.install_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
