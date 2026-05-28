#!/usr/bin/env python3
"""Remove Aftertone user-level Cursor hooks (~/.cursor/hooks.json)."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from install_global_claude_hooks import _strip_aftertone_entries as _strip_claude_entries
from install_global_codex_hooks import _strip_aftertone_entries as _strip_codex_entries
from install_global_hooks import _strip_aftertone_entries as _strip_cursor_entries


def _count_aftertone_commands(hooks: dict) -> int:
    n = 0
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and "aftertone-speak_summary" in (
                entry.get("command") or ""
            ):
                n += 1
    return n


def _remove_aftertone_hook_entries(hooks_data: dict) -> tuple[dict, int]:
    """Drop Aftertone hook commands (Unix + Windows); return (updated doc, removed count)."""
    out = dict(hooks_data)
    hooks = dict(out.get("hooks") or {})
    removed = _count_aftertone_commands(hooks)
    out["hooks"] = _strip_cursor_entries(hooks)
    return out, removed


def _count_codex_aftertone(hooks: dict) -> int:
    n = 0
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and "aftertone-codex-speak-on-stop" in (
                entry.get("command") or ""
            ):
                n += 1
    return n


def _remove_codex_hook_entries(hooks_data: dict) -> tuple[dict, int]:
    out = dict(hooks_data)
    hooks = dict(out.get("hooks") or {})
    removed = _count_codex_aftertone(hooks)
    out["hooks"] = _strip_codex_entries(hooks)
    return out, removed


def _count_claude_aftertone(hooks: dict) -> int:
    n = 0
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for group in entries:
            if not isinstance(group, dict):
                continue
            for h in group.get("hooks") or []:
                if isinstance(h, dict) and "aftertone-claude-speak-on-stop" in (
                    h.get("command") or ""
                ):
                    n += 1
    return n


def _remove_claude_hook_entries(settings: dict) -> tuple[dict, int]:
    out = dict(settings)
    hooks = dict(out.get("hooks") or {})
    removed = _count_claude_aftertone(hooks)
    out["hooks"] = _strip_claude_entries(hooks)
    return out, removed


def uninstall_global(*, dry_run: bool = False) -> None:
    user_cursor = Path.home() / ".cursor"
    user_hooks = user_cursor / "hooks"
    user_hooks_json = user_cursor / "hooks.json"

    user_claude = Path.home() / ".claude"
    claude_settings = user_claude / "settings.json"
    claude_skill = user_claude / "skills" / "spoken-summary" / "SKILL.md"
    claude_rule = user_claude / "rules" / "spoken-summary.md"
    user_codex = Path.home() / ".codex"
    codex_hooks_json = user_codex / "hooks.json"
    codex_rule = user_codex / "AGENTS.md"
    codex_user_commands = user_codex / "commands"
    codex_command_glob = "aftertone-*.md"

    hook_files = [
        user_hooks / "aftertone-install-dir",
        user_hooks / "aftertone-speak_summary.sh",
        user_hooks / "aftertone-speak_summary.cmd",
        user_hooks / "aftertone-root.sh",
        user_hooks / "aftertone-claude-speak-on-stop.sh",
        user_hooks / "aftertone-claude-doctor-quiet.sh",
        user_hooks / "aftertone-activate.sh",
        user_hooks / "aftertone-off.sh",
        user_hooks / "aftertone-status.sh",
        user_hooks / "aftertone-toggle.sh",
        user_hooks / "aftertone-restart.sh",
        user_hooks / "aftertone-doctor.sh",
        user_hooks / "aftertone-repair.sh",
        user_hooks / "_aftertone_common.sh",
        user_hooks / "aftertone-codex-speak-on-stop.sh",
        user_hooks / "aftertone-codex-speak-on-stop.cmd",
    ]
    command_glob = "aftertone-*.md"
    claude_user_commands = user_claude / "commands"
    claude_slash_glob = "aftertone_*.md"
    rule_file = user_cursor / "rules" / "spoken-summary.mdc"
    claude_cli = Path.home() / ".local" / "bin" / "aftertone_on"

    if dry_run:
        print(f"would remove hook files under {user_hooks} (aftertone-*)")
        if user_hooks_json.is_file():
            print(f"would strip Aftertone entries from {user_hooks_json}")
        cmds = user_cursor / "commands"
        if cmds.is_dir():
            print(f"would remove {cmds}/{command_glob}")
        if rule_file.is_file():
            print(f"would remove {rule_file}")
        if claude_cli.exists() or claude_cli.is_symlink():
            print(f"would remove {claude_cli}")
        if claude_user_commands.is_dir():
            for p in sorted(claude_user_commands.glob(claude_slash_glob)):
                print(f"would remove {p}")
        if claude_settings.is_file():
            print(f"would strip Aftertone from {claude_settings}")
        if codex_hooks_json.is_file():
            print(f"would strip Aftertone from {codex_hooks_json}")
        if codex_rule.is_file():
            print(f"would remove {codex_rule}")
        if codex_user_commands.is_dir():
            for p in sorted(codex_user_commands.glob(codex_command_glob)):
                print(f"would remove {p}")
        if claude_skill.is_file():
            print(f"would remove {claude_skill}")
        if claude_rule.is_file():
            print(f"would remove {claude_rule}")
        return

    user_hooks_json_exists = user_hooks_json.is_file()
    removed_hooks = 0
    if user_hooks_json_exists:
        existing = json.loads(user_hooks_json.read_text(encoding="utf-8"))
        updated, removed_hooks = _remove_aftertone_hook_entries(existing)
        if removed_hooks:
            backup = user_hooks_json.with_suffix(f".json.bak.{int(time.time())}")
            shutil.copy2(user_hooks_json, backup)
            if updated.get("hooks"):
                user_hooks_json.write_text(
                    json.dumps(updated, indent=2) + "\n", encoding="utf-8"
                )
            else:
                user_hooks_json.unlink()
            print(f"backup: {backup}")

    for path in hook_files:
        if path.is_file():
            path.unlink()
            print(f"removed: {path}")

    commands_dir = user_cursor / "commands"
    if commands_dir.is_dir():
        for cmd in sorted(commands_dir.glob(command_glob)):
            cmd.unlink()
            print(f"removed: {cmd}")

    if rule_file.is_file():
        rule_file.unlink()
        print(f"removed: {rule_file}")

    if claude_cli.exists() or claude_cli.is_symlink():
        claude_cli.unlink()
        print(f"removed: {claude_cli}")

    if claude_user_commands.is_dir():
        for p in sorted(claude_user_commands.glob(claude_slash_glob)):
            if p.is_file():
                p.unlink()
                print(f"removed: {p}")

    if codex_user_commands.is_dir():
        for p in sorted(codex_user_commands.glob(codex_command_glob)):
            if p.is_file():
                p.unlink()
                print(f"removed: {p}")

    if codex_rule.is_file():
        codex_rule.unlink()
        print(f"removed: {codex_rule}")

    removed_claude = 0
    if claude_settings.is_file():
        existing = json.loads(claude_settings.read_text(encoding="utf-8"))
        updated, removed_claude = _remove_claude_hook_entries(existing)
        if removed_claude:
            backup = claude_settings.with_suffix(f".json.bak.{int(time.time())}")
            shutil.copy2(claude_settings, backup)
            if updated.get("hooks"):
                claude_settings.write_text(
                    json.dumps(updated, indent=2) + "\n", encoding="utf-8"
                )
            else:
                claude_settings.unlink()
            print(f"backup: {backup}")
            print(
                f"removed {removed_claude} Claude Stop hook(s) from {claude_settings}"
            )

    if claude_skill.is_file():
        claude_skill.unlink()
        print(f"removed: {claude_skill}")

    if claude_rule.is_file():
        claude_rule.unlink()
        print(f"removed: {claude_rule}")

    removed_codex = 0
    if codex_hooks_json.is_file():
        existing = json.loads(codex_hooks_json.read_text(encoding="utf-8"))
        updated, removed_codex = _remove_codex_hook_entries(existing)
        if removed_codex:
            backup = codex_hooks_json.with_suffix(f".json.bak.{int(time.time())}")
            shutil.copy2(codex_hooks_json, backup)
            if updated.get("hooks"):
                codex_hooks_json.write_text(
                    json.dumps(updated, indent=2) + "\n", encoding="utf-8"
                )
            else:
                codex_hooks_json.unlink()
            print(f"backup: {backup}")
            print(f"removed {removed_codex} Codex Stop hook(s) from {codex_hooks_json}")

    if removed_hooks:
        print(f"removed {removed_hooks} afterAgentResponse hook(s) from {user_hooks_json}")
    elif user_hooks_json_exists:
        print(f"no Aftertone hook entries in {user_hooks_json}")
    else:
        print(f"no {user_hooks_json} (nothing to edit)")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Uninstall Aftertone user-level Cursor hooks."
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    uninstall_global(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
