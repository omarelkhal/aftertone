# Codex Global Hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register and remove Aftertone user-level Codex `Stop` hooks under `~/.codex/hooks.json`.

**Architecture:** Add a focused Codex installer module that mirrors the Claude installer shape while preserving the existing Cursor installer as the top-level global install entrypoint. Codex templates live under `scripts/codex-global/`, install writes wrapper scripts under `~/.cursor/hooks/` beside the existing shared wrappers, and uninstall strips only Aftertone-owned Codex entries.

**Tech Stack:** Python 3, pytest, JSON hook config files, shell and Windows command wrappers, official Codex hook contract from https://developers.openai.com/codex/hooks.

---

## File Structure

- Create `py/install_global_codex_hooks.py`
  - Register user-level Codex hooks in `~/.codex/hooks.json`.
  - Copy Codex wrapper scripts into `~/.cursor/hooks/`.
  - Preserve unrelated Codex hooks and replace stale Aftertone entries on reinstall.
- Modify `py/install_global_hooks.py`
  - Call `install_global_codex()` after Cursor and Claude install, matching the existing Claude cascade pattern.
- Modify `py/uninstall_global_hooks.py`
  - Strip Codex Aftertone entries from `~/.codex/hooks.json`.
  - Remove copied Codex wrapper files from `~/.cursor/hooks/`.
- Create `scripts/codex-global/hooks.json`
  - Codex `Stop` hook fragment for Unix-like systems.
- Create `scripts/codex-global/hooks.windows.json`
  - Codex `Stop` hook fragment for Windows command override.
- Create `scripts/codex-global/aftertone-codex-speak-on-stop.sh`
  - Unix wrapper that resolves install root and runs `python -m aftertone.hook_run --stdin`.
- Create `scripts/codex-global/aftertone-codex-speak-on-stop.cmd`
  - Windows wrapper with equivalent behavior.
- Modify `py/tests/test_install_global_hooks.py`
  - Add install/merge/idempotency tests for Codex hooks.
- Modify `py/tests/test_uninstall_global_hooks.py`
  - Add uninstall tests for Codex hook removal.

## Task 1: Codex Hook Template and Merge Function

**Files:**
- Create: `scripts/codex-global/hooks.json`
- Create: `scripts/codex-global/hooks.windows.json`
- Create: `py/install_global_codex_hooks.py`
- Test: `py/tests/test_install_global_hooks.py`

- [ ] **Step 1: Add failing Codex merge tests**

Append this to `py/tests/test_install_global_hooks.py`:

```python
from install_global_codex_hooks import _merge_codex_hooks


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
```

- [ ] **Step 2: Run tests to verify import failure**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py::test_merge_codex_hooks_appends_without_duplicates tests/test_install_global_hooks.py::test_merge_codex_hooks_replaces_stale_aftertone_entries -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'install_global_codex_hooks'`.

- [ ] **Step 3: Create Codex hook fragments**

Create `scripts/codex-global/hooks.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "bash __AFTERTONE_CODEX_STOP__",
        "timeout_ms": 10000
      }
    ]
  }
}
```

Create `scripts/codex-global/hooks.windows.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "cmd /c \"__AFTERTONE_CODEX_STOP_CMD__\"",
        "timeout_ms": 10000
      }
    ]
  }
}
```

- [ ] **Step 4: Create installer module skeleton and merge logic**

Create `py/install_global_codex_hooks.py`:

```python
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
```

- [ ] **Step 5: Run focused merge tests**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py::test_merge_codex_hooks_appends_without_duplicates tests/test_install_global_hooks.py::test_merge_codex_hooks_replaces_stale_aftertone_entries -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add py/install_global_codex_hooks.py scripts/codex-global/hooks.json scripts/codex-global/hooks.windows.json py/tests/test_install_global_hooks.py
git commit -m "feat(codex): add hook merge templates"
```

## Task 2: Install Global Codex Hooks

**Files:**
- Modify: `py/install_global_codex_hooks.py`
- Modify: `py/install_global_hooks.py`
- Create: `scripts/codex-global/aftertone-codex-speak-on-stop.sh`
- Create: `scripts/codex-global/aftertone-codex-speak-on-stop.cmd`
- Test: `py/tests/test_install_global_hooks.py`

- [ ] **Step 1: Add failing install test**

Append to `py/tests/test_install_global_hooks.py`:

```python
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
                            "command": "bash __AFTERTONE_CODEX_STOP__",
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
    assert any(
        "aftertone-codex-speak-on-stop.sh" in (h.get("command") or "")
        for h in hooks["hooks"]["Stop"]
    )
    assert (fake_home / ".cursor/hooks/aftertone-codex-speak-on-stop.sh").is_file()
```

- [ ] **Step 2: Run install test to verify failure**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py::test_install_global_writes_codex_hooks -q
```

Expected: FAIL because `install_global_codex` is not implemented.

- [ ] **Step 3: Create Unix wrapper**

Create `scripts/codex-global/aftertone-codex-speak-on-stop.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

INSTALL_FILE="${HOME}/.cursor/hooks/aftertone-install-dir"
if [[ -f "${INSTALL_FILE}" ]]; then
  AFTERTONE_INSTALL_DIR="$(cat "${INSTALL_FILE}")"
else
  AFTERTONE_INSTALL_DIR="${AFTERTONE_INSTALL_DIR:-${AFTERTONE_REPO:-${HOME}/aftertone}}"
fi
export AFTERTONE_INSTALL_DIR

cd "${AFTERTONE_INSTALL_DIR}/py"
if [[ -x ".venv/bin/python" ]]; then
  exec .venv/bin/python -m aftertone.hook_run --stdin
fi
exec uv run python -m aftertone.hook_run --stdin
```

- [ ] **Step 4: Create Windows wrapper**

Create `scripts/codex-global/aftertone-codex-speak-on-stop.cmd`:

```bat
@echo off
setlocal

set "INSTALL_FILE=%USERPROFILE%\.cursor\hooks\aftertone-install-dir"
if exist "%INSTALL_FILE%" (
  set /p AFTERTONE_INSTALL_DIR=<"%INSTALL_FILE%"
) else if not "%AFTERTONE_INSTALL_DIR%"=="" (
  rem keep existing AFTERTONE_INSTALL_DIR
) else if not "%AFTERTONE_REPO%"=="" (
  set "AFTERTONE_INSTALL_DIR=%AFTERTONE_REPO%"
) else (
  set "AFTERTONE_INSTALL_DIR=%USERPROFILE%\aftertone"
)

cd /d "%AFTERTONE_INSTALL_DIR%\py"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m aftertone.hook_run --stdin
) else (
  uv run python -m aftertone.hook_run --stdin
)
```

- [ ] **Step 5: Implement install_global_codex**

Append to `py/install_global_codex_hooks.py`:

```python
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
        dest_stop.chmod(dest_stop.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
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
```

- [ ] **Step 6: Wire Codex from global install**

In `py/install_global_hooks.py`, inside `install_global()` after the Claude install try/except block, add:

```python
    try:
        from install_global_codex_hooks import install_global_codex

        install_global_codex(install_dir=install_dir, dry_run=dry_run)
    except SystemExit as exc:
        print(f"Codex hooks: skipped ({exc})", file=sys.stderr)
    except Exception as exc:
        print(f"Codex hooks: skipped ({exc})", file=sys.stderr)
```

- [ ] **Step 7: Run install test**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py::test_install_global_writes_codex_hooks -q
```

Expected: PASS.

- [ ] **Step 8: Run existing install tests**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit Task 2**

```bash
git add py/install_global_codex_hooks.py py/install_global_hooks.py scripts/codex-global py/tests/test_install_global_hooks.py
git commit -m "feat(codex): install global Stop hook"
```

## Task 3: Windows Command Coverage

**Files:**
- Modify: `py/tests/test_install_global_hooks.py`
- Modify: `py/install_global_codex_hooks.py` only if needed.

- [ ] **Step 1: Add Windows install test**

Append:

```python
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
```

- [ ] **Step 2: Run Windows test**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py::test_install_global_codex_windows_cmd -q
```

Expected: PASS.

- [ ] **Step 3: Commit Task 3**

```bash
git add py/install_global_codex_hooks.py py/tests/test_install_global_hooks.py
git commit -m "test(codex): cover Windows hook command"
```

## Task 4: Uninstall Codex Hooks

**Files:**
- Modify: `py/uninstall_global_hooks.py`
- Test: `py/tests/test_uninstall_global_hooks.py`

- [ ] **Step 1: Add failing uninstall tests**

Append to `py/tests/test_uninstall_global_hooks.py`:

```python
from uninstall_global_hooks import _remove_codex_hook_entries


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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run --directory py pytest tests/test_uninstall_global_hooks.py::test_remove_codex_hook_entries_keeps_other_hooks tests/test_uninstall_global_hooks.py::test_uninstall_global_removes_codex_hooks -q
```

Expected: FAIL because `_remove_codex_hook_entries` is not implemented.

- [ ] **Step 3: Implement Codex removal helpers**

In `py/uninstall_global_hooks.py`, add this import:

```python
from install_global_codex_hooks import _strip_aftertone_entries as _strip_codex_entries
```

Add these helpers near the Cursor removal helpers:

```python
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
```

- [ ] **Step 4: Wire Codex into uninstall_global**

In `uninstall_global()`, define:

```python
    user_codex = Path.home() / ".codex"
    codex_hooks_json = user_codex / "hooks.json"
```

Add these files to `hook_files`:

```python
        user_hooks / "aftertone-codex-speak-on-stop.sh",
        user_hooks / "aftertone-codex-speak-on-stop.cmd",
```

In the dry-run block, add:

```python
        if codex_hooks_json.is_file():
            print(f"would strip Aftertone from {codex_hooks_json}")
```

After the Claude settings removal block, add:

```python
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
```

- [ ] **Step 5: Run uninstall tests**

Run:

```bash
uv run --directory py pytest tests/test_uninstall_global_hooks.py::test_remove_codex_hook_entries_keeps_other_hooks tests/test_uninstall_global_hooks.py::test_uninstall_global_removes_codex_hooks -q
```

Expected: PASS.

- [ ] **Step 6: Run all install/uninstall tests**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py tests/test_uninstall_global_hooks.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

```bash
git add py/uninstall_global_hooks.py py/tests/test_uninstall_global_hooks.py
git commit -m "feat(codex): uninstall global Stop hook"
```

## Task 5: Full Verification and Issue Update

**Files:**
- Verify only unless checks reveal a problem.

- [ ] **Step 1: Run focused install/uninstall tests**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py tests/test_uninstall_global_hooks.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full Python tests**

Run:

```bash
uv run --directory py pytest -q
```

Expected: PASS. If the isolated worktree lacks `assets/`, temporarily symlink the existing local assets directory for asset-dependent tests and remove the symlink before committing:

```bash
ln -s /home/el-khal-omar/aftertone/assets assets
uv run --directory py pytest -q
rm assets
```

- [ ] **Step 3: Run dry-run smoke checks**

Run:

```bash
uv run --directory py python install_global_codex_hooks.py --install-dir "$PWD" --dry-run
uv run --directory py python uninstall_global_hooks.py --dry-run
```

Expected: both commands print intended Codex actions and exit 0 without touching real user files.

- [ ] **Step 4: Run diff checks**

Run:

```bash
git diff --check
grep -RIn -E '^<<<<<<<|^=======|^>>>>>>>' py scripts docs/superpowers/plans || true
```

Expected: `git diff --check` exits 0 and `grep` prints nothing.

- [ ] **Step 5: Comment on issue #15**

Run:

```bash
gh issue comment 15 --body "Implemented and verified locally:

- \`uv run --directory py pytest tests/test_install_global_hooks.py tests/test_uninstall_global_hooks.py -q\`
- \`uv run --directory py pytest -q\`
- \`uv run --directory py python install_global_codex_hooks.py --install-dir \\\"$PWD\\\" --dry-run\`
- \`uv run --directory py python uninstall_global_hooks.py --dry-run\`
- \`git diff --check\`

Global install now registers a Codex Stop hook under \`~/.codex/hooks.json\`, preserves unrelated hooks, replaces stale Aftertone entries, and uninstall removes only Aftertone-owned Codex entries."
```

- [ ] **Step 6: Commit the implementation plan**

```bash
git add docs/superpowers/plans/2026-05-28-codex-global-hooks.md
git commit -m "docs: plan Codex global hooks"
```

## Self-Review

- Spec coverage: This plan covers install merge, unrelated-hook preservation, idempotent reinstall, uninstall stripping, Linux/macOS and Windows command representation, and temporary-home tests.
- Placeholder scan: No task contains TBD/TODO/later/fill-in instructions.
- Type consistency: The plan consistently uses `install_global_codex()`, `_merge_codex_hooks()`, `_strip_aftertone_entries()`, and `_remove_codex_hook_entries()`.
