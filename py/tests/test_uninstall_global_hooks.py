"""Tests for user-level Cursor hook removal."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from install_global_hooks import install_global
from uninstall_global_hooks import (
    _remove_aftertone_hook_entries,
    _remove_codex_hook_entries,
    uninstall_global,
)


def test_remove_aftertone_hook_entries_keeps_other_hooks() -> None:
    existing = {
        "version": 1,
        "hooks": {
            "afterAgentResponse": [
                {"command": "bash ./hooks/other.sh", "timeout": 1},
                {"command": "bash ./hooks/aftertone-speak_summary.sh", "timeout": 8},
            ],
        },
    }
    updated, removed = _remove_aftertone_hook_entries(existing)
    assert removed == 1
    cmds = [h["command"] for h in updated["hooks"]["afterAgentResponse"]]
    assert cmds == ["bash ./hooks/other.sh"]


def test_remove_aftertone_hook_entries_removes_windows_cmd() -> None:
    existing = {
        "version": 1,
        "hooks": {
            "afterAgentResponse": [
                {
                    "command": r"cmd /c hooks\aftertone-speak_summary.cmd",
                    "timeout": 8,
                },
            ],
        },
    }
    updated, removed = _remove_aftertone_hook_entries(existing)
    assert removed == 1
    assert "afterAgentResponse" not in updated["hooks"]


def test_remove_aftertone_hook_entries_drops_empty_event() -> None:
    existing = {
        "version": 1,
        "hooks": {
            "afterAgentResponse": [
                {"command": "bash ./hooks/aftertone-speak_summary.sh", "timeout": 8},
            ],
        },
    }
    updated, removed = _remove_aftertone_hook_entries(existing)
    assert removed == 1
    assert "afterAgentResponse" not in updated["hooks"]


def test_remove_codex_hook_entries_keeps_other_hooks() -> None:
    existing = {
        "hooks": {
            "Stop": [
                {"type": "command", "command": "bash /tmp/other.sh", "timeout_ms": 1000},
                {
                    "type": "command",
                    "command": "bash /tmp/aftertone-codex-speak-on-stop.sh",
                    "timeout_ms": 10000,
                },
            ],
        },
    }

    updated, removed = _remove_codex_hook_entries(existing)

    assert removed == 1
    assert updated["hooks"]["Stop"] == [
        {"type": "command", "command": "bash /tmp/other.sh", "timeout_ms": 1000},
    ]


def test_uninstall_global_removes_files(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    install = tmp_path / "aftertone"
    (install / "py").mkdir(parents=True)
    (install / "py" / "speak_summary_prepare.py").write_text("# stub\n")
    (install / "scripts" / "cursor-global").mkdir(parents=True)
    (install / "scripts/cursor-global/aftertone-speak_summary.sh").write_text(
        "#!/bin/bash\nexit 0\n", encoding="utf-8"
    )
    (install / "scripts/cursor-global/hooks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "hooks": {
                    "afterAgentResponse": [
                        {
                            "command": "bash ./hooks/aftertone-speak_summary.sh",
                            "timeout": 8,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (install / ".cursor/commands").mkdir(parents=True)
    (install / ".cursor/commands/aftertone-on.md").write_text("# on\n")
    (install / ".cursor/rules").mkdir(parents=True)
    (install / ".cursor/rules/spoken-summary.mdc").write_text("# rule\n")

    install_global(install_dir=install)
    uninstall_global()

    assert not (fake_home / ".cursor/hooks/aftertone-install-dir").exists()
    assert not (fake_home / ".cursor/hooks/aftertone-speak_summary.sh").exists()
    assert not (fake_home / ".cursor/commands/aftertone-on.md").exists()
    assert not (fake_home / ".cursor/rules/spoken-summary.mdc").exists()
    assert not (fake_home / ".cursor/hooks.json").exists()


def test_uninstall_global_removes_codex_hooks(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    codex = fake_home / ".codex"
    codex.mkdir()
    (codex / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {"type": "command", "command": "bash /tmp/other.sh", "timeout_ms": 1000},
                        {
                            "type": "command",
                            "command": "bash /tmp/aftertone-codex-speak-on-stop.sh",
                            "timeout_ms": 10000,
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    cursor_hooks = fake_home / ".cursor" / "hooks"
    cursor_hooks.mkdir(parents=True)
    (cursor_hooks / "aftertone-codex-speak-on-stop.sh").write_text("#!/bin/bash\n")
    (cursor_hooks / "aftertone-codex-speak-on-stop.cmd").write_text("@echo off\n")

    uninstall_global()

    hooks = json.loads((codex / "hooks.json").read_text())
    assert hooks["hooks"]["Stop"] == [
        {"type": "command", "command": "bash /tmp/other.sh", "timeout_ms": 1000},
    ]
    assert not (cursor_hooks / "aftertone-codex-speak-on-stop.sh").exists()
    assert not (cursor_hooks / "aftertone-codex-speak-on-stop.cmd").exists()


def test_uninstall_global_removes_codex_guidance_and_commands(
    tmp_path: Path, monkeypatch
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    codex = fake_home / ".codex"
    commands = codex / "commands"
    prompts = codex / "prompts"
    commands.mkdir(parents=True)
    prompts.mkdir(parents=True)
    (codex / "AGENTS.md").write_text("Aftertone guidance\n", encoding="utf-8")
    (commands / "aftertone-on.md").write_text("on\n", encoding="utf-8")
    (commands / "aftertone-off.md").write_text("off\n", encoding="utf-8")
    (commands / "other.md").write_text("keep\n", encoding="utf-8")
    (prompts / "aftertone-on.md").write_text("on\n", encoding="utf-8")
    (prompts / "aftertone-off.md").write_text("off\n", encoding="utf-8")
    (prompts / "other.md").write_text("keep\n", encoding="utf-8")

    uninstall_global()

    assert not (codex / "AGENTS.md").exists()
    assert not (commands / "aftertone-on.md").exists()
    assert not (commands / "aftertone-off.md").exists()
    assert (commands / "other.md").exists()
    assert not (prompts / "aftertone-on.md").exists()
    assert not (prompts / "aftertone-off.md").exists()
    assert (prompts / "other.md").exists()
