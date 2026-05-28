#!/usr/bin/env python3
"""Register Aftertone user-level Cursor hooks (~/.cursor/hooks.json)."""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
from pathlib import Path

_AFTER_AGENT = "afterAgentResponse"
_CMD_UNIX = "bash ./hooks/aftertone-speak_summary.sh"
# Cursor on Windows does not execute .cmd paths unless wrapped (forum + Colin, Cursor support).
_CMD_WIN_REL = r"cmd /c hooks\aftertone-speak_summary.cmd"


def _hook_command() -> str:
    return _CMD_WIN_REL if sys.platform == "win32" else _CMD_UNIX


def _windows_hook_command(wrapper_cmd: Path) -> str:
    """Absolute path + cmd /c — Cursor on Windows often ignores relative .cmd paths."""
    return f'cmd /c "{wrapper_cmd.resolve()}"'


def _apply_windows_commands(merged: dict, wrapper_cmd: Path) -> None:
    win_cmd = _windows_hook_command(wrapper_cmd)
    hooks = merged.get("hooks") or {}
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            cmd = entry.get("command") or ""
            if "aftertone-speak_summary" in cmd:
                entry["command"] = win_cmd


def _fragment_path(template_dir: Path) -> Path:
    if sys.platform == "win32":
        win = template_dir / "hooks.windows.json"
        if win.is_file():
            return win
    return template_dir / "hooks.json"


def _strip_aftertone_entries(hooks: dict) -> dict:
    """Remove prior Aftertone hook commands so OS switches do not stack duplicates."""
    out: dict = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            out[event] = entries
            continue
        kept = [
            e
            for e in entries
            if isinstance(e, dict)
            and "aftertone-speak_summary" not in (e.get("command") or "")
        ]
        if kept:
            out[event] = kept
    return out


def _merge_hooks(existing: dict, fragment: dict) -> dict:
    out = dict(existing)
    out["version"] = max(int(out.get("version", 1)), int(fragment.get("version", 1)))
    hooks = _strip_aftertone_entries(dict(out.get("hooks") or {}))
    frag_hooks = fragment.get("hooks") or {}
    for event, entries in frag_hooks.items():
        cur = list(hooks.get(event) or [])
        seen = {e.get("command") for e in cur if isinstance(e, dict)}
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


def install_global(*, install_dir: Path, dry_run: bool = False) -> None:
    install_dir = install_dir.expanduser().resolve()
    marker = install_dir / "py" / "speak_summary_prepare.py"
    if not marker.is_file():
        raise SystemExit(f"not an Aftertone install: {install_dir}")

    user_cursor = Path.home() / ".cursor"
    user_hooks = user_cursor / "hooks"
    user_hooks_json = user_cursor / "hooks.json"
    template_dir = install_dir / "scripts" / "cursor-global"
    wrapper_src = template_dir / "aftertone-speak_summary.sh"
    wrapper_cmd_src = template_dir / "aftertone-speak_summary.cmd"
    fragment_src = _fragment_path(template_dir)
    root_sh_src = install_dir / "scripts" / "aftertone-root.sh"

    if not wrapper_src.is_file() or not fragment_src.is_file():
        raise SystemExit(f"missing templates under {template_dir}")

    if dry_run:
        print(f"would write {user_hooks / 'aftertone-install-dir'} -> {install_dir}")
        print(f"would copy {wrapper_src} -> {user_hooks / 'aftertone-speak_summary.sh'}")
        print(f"would merge {user_hooks_json}")
        return

    user_hooks.mkdir(parents=True, exist_ok=True)
    (user_hooks / "aftertone-install-dir").write_text(f"{install_dir}\n", encoding="utf-8")

    dest_wrapper = user_hooks / "aftertone-speak_summary.sh"
    shutil.copy2(wrapper_src, dest_wrapper)
    if sys.platform != "win32":
        dest_wrapper.chmod(
            dest_wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )

    if sys.platform == "win32" and wrapper_cmd_src.is_file():
        shutil.copy2(wrapper_cmd_src, user_hooks / "aftertone-speak_summary.cmd")

    if root_sh_src.is_file():
        dest_root = user_hooks / "aftertone-root.sh"
        shutil.copy2(root_sh_src, dest_root)
        if sys.platform != "win32":
            dest_root.chmod(
                dest_root.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

    fragment = json.loads(fragment_src.read_text(encoding="utf-8-sig"))
    if user_hooks_json.is_file():
        existing = json.loads(user_hooks_json.read_text(encoding="utf-8-sig"))
        backup = user_hooks_json.with_suffix(f".json.bak.{int(__import__('time').time())}")
        shutil.copy2(user_hooks_json, backup)
        merged = _merge_hooks(existing, fragment)
    else:
        merged = fragment

    dest_wrapper_cmd = user_hooks / "aftertone-speak_summary.cmd"
    if sys.platform == "win32" and dest_wrapper_cmd.is_file():
        _apply_windows_commands(merged, dest_wrapper_cmd)

    user_hooks_json.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")

    commands_src = install_dir / ".cursor" / "commands"
    if commands_src.is_dir():
        user_commands = user_cursor / "commands"
        user_commands.mkdir(parents=True, exist_ok=True)
        for cmd in commands_src.glob("aftertone-*.md"):
            shutil.copy2(cmd, user_commands / cmd.name)

    rule_src = install_dir / ".cursor" / "rules" / "spoken-summary.mdc"
    if rule_src.is_file():
        user_rules = user_cursor / "rules"
        user_rules.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rule_src, user_rules / "spoken-summary.mdc")

    has_aftertone = any(
        isinstance(e, dict) and "aftertone-speak_summary" in (e.get("command") or "")
        for e in (merged.get("hooks") or {}).get(_AFTER_AGENT, [])
    )
    win_cmd = (
        _windows_hook_command(dest_wrapper_cmd)
        if sys.platform == "win32" and dest_wrapper_cmd.is_file()
        else _hook_command()
    )
    print(f"Global Cursor hooks: {user_hooks_json}")
    print(f"Install root: {install_dir}")
    print(f"afterAgentResponse Aftertone hook: {'yes' if has_aftertone else 'no'}")
    if sys.platform == "win32" and has_aftertone:
        print(f"Windows command: {win_cmd}")

    try:
        from install_global_claude_hooks import install_global_claude

        install_global_claude(install_dir=install_dir, dry_run=dry_run)
    except SystemExit as exc:
        print(f"Claude Code hooks: skipped ({exc})", file=sys.stderr)
    except Exception as exc:
        print(f"Claude Code hooks: skipped ({exc})", file=sys.stderr)

    try:
        from install_global_codex_hooks import install_global_codex

        install_global_codex(install_dir=install_dir, dry_run=dry_run)
    except SystemExit as exc:
        print(f"Codex hooks: skipped ({exc})", file=sys.stderr)
    except Exception as exc:
        print(f"Codex hooks: skipped ({exc})", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description="Install Aftertone user-level Cursor hooks.")
    p.add_argument("--install-dir", type=Path, required=True, help="Aftertone clone root")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    install_global(install_dir=args.install_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
