"""Tests for user-level Cursor hook registration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from install_global_hooks import _merge_hooks, install_global
from install_global_codex_hooks import _merge_codex_hooks


def test_merge_hooks_appends_without_duplicates() -> None:
    existing = {
        "version": 1,
        "hooks": {
            "afterAgentResponse": [{"command": "bash ./hooks/other.sh", "timeout": 1}],
        },
    }
    fragment = {
        "version": 1,
        "hooks": {
            "afterAgentResponse": [
                {"command": "bash ./hooks/aftertone-speak_summary.sh", "timeout": 8},
            ],
        },
    }
    merged = _merge_hooks(existing, fragment)
    cmds = [h["command"] for h in merged["hooks"]["afterAgentResponse"]]
    assert cmds == [
        "bash ./hooks/other.sh",
        "bash ./hooks/aftertone-speak_summary.sh",
    ]


def test_merge_codex_hooks_appends_without_duplicates() -> None:
    existing = {
        "hooks": {
            "Stop": [
                {"type": "command", "command": "bash /tmp/other.sh", "timeout_ms": 1000},
            ],
        },
    }
    fragment = {
        "hooks": {
            "Stop": [
                {
                    "type": "command",
                    "command": "bash /tmp/aftertone-codex-speak-on-stop.sh",
                    "timeout_ms": 10000,
                },
            ],
        },
    }

    merged = _merge_codex_hooks(existing, fragment)

    cmds = [h["command"] for h in merged["hooks"]["Stop"]]
    assert cmds == [
        "bash /tmp/other.sh",
        "bash /tmp/aftertone-codex-speak-on-stop.sh",
    ]


def test_merge_codex_hooks_replaces_stale_aftertone_entries() -> None:
    existing = {
        "hooks": {
            "Stop": [
                {
                    "type": "command",
                    "command": "bash /old/aftertone-codex-speak-on-stop.sh",
                    "timeout_ms": 10000,
                },
                {"type": "command", "command": "bash /tmp/other.sh", "timeout_ms": 1000},
            ],
        },
    }
    fragment = {
        "hooks": {
            "Stop": [
                {
                    "type": "command",
                    "command": "bash /new/aftertone-codex-speak-on-stop.sh",
                    "timeout_ms": 10000,
                },
            ],
        },
    }

    merged = _merge_codex_hooks(existing, fragment)

    cmds = [h["command"] for h in merged["hooks"]["Stop"]]
    assert cmds == ["bash /tmp/other.sh", "bash /new/aftertone-codex-speak-on-stop.sh"]


def test_install_global_writes_files(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    install = tmp_path / "aftertone"
    (install / "py").mkdir(parents=True)
    (install / "py" / "speak_summary_prepare.py").write_text("# stub\n")
    (install / "scripts" / "cursor-global").mkdir(parents=True)
    wrapper = install / "scripts/cursor-global/aftertone-speak_summary.sh"
    wrapper.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
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
    (install / ".cursor/hooks/speak_summary.sh").parent.mkdir(parents=True)
    (install / ".cursor/hooks/speak_summary.sh").write_text("# stub\n")

    install_global(install_dir=install)

    assert (fake_home / ".cursor/hooks/aftertone-install-dir").read_text().strip() == str(
        install.resolve()
    )
    assert (fake_home / ".cursor/hooks/aftertone-speak_summary.sh").is_file()
    hooks = json.loads((fake_home / ".cursor/hooks.json").read_text())
    assert any(
        e.get("command") == "bash ./hooks/aftertone-speak_summary.sh"
        for e in hooks["hooks"]["afterAgentResponse"]
    )


def test_install_global_writes_codex_hooks(tmp_path: Path, monkeypatch) -> None:
    from install_global_codex_hooks import install_global_codex

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    install = tmp_path / "aftertone"
    (install / "py").mkdir(parents=True)
    (install / "py" / "speak_summary_prepare.py").write_text("# stub\n")
    tpl = install / "scripts" / "codex-global"
    tpl.mkdir(parents=True)
    (tpl / "aftertone-codex-speak-on-stop.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (tpl / "aftertone-codex-speak-on-stop.cmd").write_text("@echo off\n", encoding="utf-8")
    (tpl / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "type": "command",
                            "command": "__AFTERTONE_CODEX_STOP__",
                            "timeout_ms": 10000,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    install_global_codex(install_dir=install)

    hooks = json.loads((fake_home / ".codex/hooks.json").read_text())
    command = hooks["hooks"]["Stop"][0]["command"]
    assert command.startswith("bash ")
    assert "bash bash" not in command
    assert "aftertone-codex-speak-on-stop.sh" in command
    assert (fake_home / ".cursor/hooks/aftertone-codex-speak-on-stop.sh").is_file()


def test_install_global_windows_cmd(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setattr("install_global_hooks.sys.platform", "win32")

    install = tmp_path / "aftertone"
    (install / "py").mkdir(parents=True)
    (install / "py" / "speak_summary_prepare.py").write_text("# stub\n")
    tpl = install / "scripts/cursor-global"
    tpl.mkdir(parents=True)
    (tpl / "aftertone-speak_summary.sh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    (tpl / "aftertone-speak_summary.cmd").write_text("@echo off\n", encoding="utf-8")
    (tpl / "hooks.windows.json").write_text(
        json.dumps(
            {
                "version": 1,
                "hooks": {
                    "afterAgentResponse": [
                        {
                            "command": r"cmd /c hooks\aftertone-speak_summary.cmd",
                            "timeout": 8,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (install / ".cursor/hooks/speak_summary.sh").parent.mkdir(parents=True)
    (install / ".cursor/hooks/speak_summary.sh").write_text("# stub\n")

    install_global(install_dir=install)

    assert (fake_home / ".cursor/hooks/aftertone-speak_summary.cmd").is_file()
    hooks = json.loads((fake_home / ".cursor/hooks.json").read_text())
    assert any(
        "aftertone-speak_summary.cmd" in (e.get("command") or "")
        and "cmd /c" in (e.get("command") or "")
        for e in hooks["hooks"]["afterAgentResponse"]
    )


def test_install_global_codex_windows_cmd(tmp_path: Path, monkeypatch) -> None:
    from install_global_codex_hooks import install_global_codex

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setattr("install_global_codex_hooks.sys.platform", "win32")

    install = tmp_path / "aftertone"
    (install / "py").mkdir(parents=True)
    (install / "py" / "speak_summary_prepare.py").write_text("# stub\n")
    tpl = install / "scripts" / "codex-global"
    tpl.mkdir(parents=True)
    (tpl / "aftertone-codex-speak-on-stop.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (tpl / "aftertone-codex-speak-on-stop.cmd").write_text("@echo off\n", encoding="utf-8")
    (tpl / "hooks.windows.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "type": "command",
                            "command": "cmd /c \"__AFTERTONE_CODEX_STOP_CMD__\"",
                            "timeout_ms": 10000,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    install_global_codex(install_dir=install)

    hooks = json.loads((fake_home / ".codex/hooks.json").read_text())
    cmd = hooks["hooks"]["Stop"][0]["command"]
    assert "cmd /c" in cmd
    assert "aftertone-codex-speak-on-stop.cmd" in cmd
    assert (fake_home / ".cursor/hooks/aftertone-codex-speak-on-stop.cmd").is_file()


def test_install_global_codex_copies_guidance_and_commands(
    tmp_path: Path, monkeypatch
) -> None:
    from install_global_codex_hooks import install_global_codex

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    install = tmp_path / "aftertone"
    (install / "py").mkdir(parents=True)
    (install / "py" / "speak_summary_prepare.py").write_text("# stub\n")
    tpl = install / "scripts" / "codex-global"
    (tpl / "commands").mkdir(parents=True)
    (tpl / "aftertone-codex-speak-on-stop.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (tpl / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "type": "command",
                            "command": "bash __AFTERTONE_CODEX_STOP__",
                            "timeout_ms": 10000,
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (tpl / "AGENTS.md").write_text("Codex guidance <spoken_summary>\n", encoding="utf-8")
    (tpl / "commands" / "aftertone-on.md").write_text("aftertone on\n", encoding="utf-8")
    (tpl / "commands" / "aftertone-off.md").write_text("aftertone off\n", encoding="utf-8")

    install_global_codex(install_dir=install)

    assert (
        fake_home / ".codex/AGENTS.md"
    ).read_text(encoding="utf-8") == "Codex guidance <spoken_summary>\n"
    assert (
        fake_home / ".codex/commands/aftertone-on.md"
    ).read_text(encoding="utf-8") == "aftertone on\n"
    assert (
        fake_home / ".codex/commands/aftertone-off.md"
    ).read_text(encoding="utf-8") == "aftertone off\n"
