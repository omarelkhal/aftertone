# Codex Guidance and Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install Codex-facing guidance and document per-chat control semantics so Codex users get reliable `<spoken_summary>` output and know how to enable speech per session.

**Architecture:** Reuse the Cursor/Claude spoken-summary rule language, but place Codex assets under `scripts/codex-global/` and install them into `~/.codex/`. Keep command/control behavior through the existing `python -m aftertone on|off|status|...` CLI rather than inventing a new runtime path.

**Tech Stack:** Python 3, pytest, markdown rule/command files, existing Aftertone CLI, Codex hooks from https://developers.openai.com/codex/hooks.

---

## File Structure

- Create `scripts/codex-global/AGENTS.md`
  - Codex-facing rule loaded from `~/.codex/AGENTS.md` or imported by user/project Codex config.
  - Mirrors the core spoken-summary instructions and TOML language lock.
- Create `scripts/codex-global/commands/aftertone-on.md`
  - Codex command guidance for enabling speech for the current chat/session.
- Create `scripts/codex-global/commands/aftertone-off.md`
  - Codex command guidance for disabling speech for the current chat/session.
- Create `scripts/codex-global/commands/aftertone-status.md`
  - Codex command guidance for checking config/daemon/session state.
- Modify `py/install_global_codex_hooks.py`
  - Copy Codex rule and command files into `~/.codex/`.
  - Keep install idempotent.
- Modify `py/uninstall_global_hooks.py`
  - Remove only Aftertone-owned Codex command files and rule when uninstalling.
- Modify `py/sync_spoken_rule_lang.py`
  - Sync the TOML language block into the Codex rule template and installed global Codex rule if present.
- Modify `py/tests/test_install_global_hooks.py`
  - Cover Codex rule/command install.
- Modify `py/tests/test_uninstall_global_hooks.py`
  - Cover Codex rule/command uninstall.
- Modify `py/tests/test_aftertone_v2.py`
  - Add a smoke-style test proving pending `aftertone on` registers a Codex session id in the shared allowlist.

## Task 1: Codex Rule and Command Assets

**Files:**
- Create: `scripts/codex-global/AGENTS.md`
- Create: `scripts/codex-global/commands/aftertone-on.md`
- Create: `scripts/codex-global/commands/aftertone-off.md`
- Create: `scripts/codex-global/commands/aftertone-status.md`

- [ ] **Step 1: Create Codex spoken-summary rule**

Create `scripts/codex-global/AGENTS.md`:

```markdown
## Aftertone spoken summaries for Codex

Aftertone speaks after a Codex turn when the global Codex `Stop` hook is installed and the current session is enabled.

Use explicit text inside `<spoken_summary>...</spoken_summary>` in your final assistant message. With `only_speak_spoken_summary = true` and `summary_mode = "tag_only"` by default, only the tag is spoken.

**`lang` in TOML = language of the spoken words.** The hook does not translate. Write the tag in the same language as `lang`, not necessarily the language the user typed.

<!-- autogen:spoken-lang:start -->
> **Locked `lang` for `<spoken_summary>` only:** `en` (from `~/aftertone/.cursor/hooks/speak_summary.toml` on global install). Write the **inner tag** only in that language — **not** the conversation language. After changing `lang`, run `/aftertone-lang` or `uv run --directory py python sync_spoken_rule_lang.py` from the Aftertone repo.
<!-- autogen:spoken-lang:end -->

Treat the tag as a short pair-programmer briefing for someone listening, not looking at the screen:

- State what happened.
- Add why it matters only when it changes the user's next thought.
- Add a next move only for blockers, risk, tests due, open decisions, incomplete work, or an obvious action.

Put exactly one block at the very end of substantive replies:

```xml
<spoken_summary>
The current session is ready to speak after Codex replies!!
</spoken_summary>
```

Do not put markdown, code, file paths, URLs, hashes, or `state="..."` in the spoken tag.

For livelier Supertonic delivery, end each sentence inside the tag with one of `!!`, `??`, `?!`, or `!?`.

If the user says `test` or asks to check speech, end with a short distinctive `<spoken_summary>` line in the configured language.
```

- [ ] **Step 2: Create Codex on command**

Create `scripts/codex-global/commands/aftertone-on.md`:

```markdown
# /aftertone-on

Enable Aftertone spoken TTS for this Codex session only.

Run exactly one command from the Aftertone install root:

```bash
uv run --directory py python -m aftertone on
```

Then include a short `<spoken_summary>` in this reply so the Codex `Stop` hook can register this session id on the allowlist. Other Codex sessions stay silent until enabled there too.

Terminal fallback without a Codex turn:

```bash
uv run --directory ~/aftertone/py python -m aftertone on
```
```

- [ ] **Step 3: Create Codex off command**

Create `scripts/codex-global/commands/aftertone-off.md`:

```markdown
# /aftertone-off

Disable Aftertone spoken TTS for this Codex session only.

Run exactly one command from the Aftertone install root:

```bash
uv run --directory py python -m aftertone off
```

The next Codex `Stop` hook with this session id clears it from the allowlist. Other sessions are unchanged.

Terminal fallback without a Codex turn:

```bash
uv run --directory ~/aftertone/py python -m aftertone off
```
```

- [ ] **Step 4: Create Codex status command**

Create `scripts/codex-global/commands/aftertone-status.md`:

```markdown
# /aftertone-status

Show Aftertone config, daemon state, and enabled session ids.

Run exactly one command from the Aftertone install root:

```bash
uv run --directory py python -m aftertone status
```
```

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/codex-global/AGENTS.md scripts/codex-global/commands
git commit -m "feat(codex): add spoken guidance assets"
```

## Task 2: Install Codex Rule and Commands

**Files:**
- Modify: `py/install_global_codex_hooks.py`
- Modify: `py/tests/test_install_global_hooks.py`

- [ ] **Step 1: Add failing install test**

Append to `py/tests/test_install_global_hooks.py`:

```python
def test_install_global_codex_copies_guidance_and_commands(tmp_path: Path, monkeypatch) -> None:
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
        json.dumps({"hooks": {"Stop": [{"type": "command", "command": "bash __AFTERTONE_CODEX_STOP__", "timeout_ms": 10000}]}}),
        encoding="utf-8",
    )
    (tpl / "AGENTS.md").write_text("Codex guidance <spoken_summary>\n", encoding="utf-8")
    (tpl / "commands" / "aftertone-on.md").write_text("aftertone on\n", encoding="utf-8")
    (tpl / "commands" / "aftertone-off.md").write_text("aftertone off\n", encoding="utf-8")

    install_global_codex(install_dir=install)

    assert (fake_home / ".codex/AGENTS.md").read_text(encoding="utf-8") == "Codex guidance <spoken_summary>\n"
    assert (fake_home / ".codex/commands/aftertone-on.md").read_text(encoding="utf-8") == "aftertone on\n"
    assert (fake_home / ".codex/commands/aftertone-off.md").read_text(encoding="utf-8") == "aftertone off\n"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py::test_install_global_codex_copies_guidance_and_commands -q
```

Expected: FAIL because install does not copy Codex guidance yet.

- [ ] **Step 3: Implement install copy**

In `py/install_global_codex_hooks.py`, inside `install_global_codex()` after writing `hooks_json`, add:

```python
    rule_src = template_dir / "AGENTS.md"
    if rule_src.is_file():
        shutil.copy2(rule_src, user_codex / "AGENTS.md")

    commands_src = template_dir / "commands"
    if commands_src.is_dir():
        commands_dest = user_codex / "commands"
        commands_dest.mkdir(parents=True, exist_ok=True)
        for cmd in sorted(commands_src.glob("aftertone-*.md")):
            shutil.copy2(cmd, commands_dest / cmd.name)
```

- [ ] **Step 4: Run focused install test**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py::test_install_global_codex_copies_guidance_and_commands -q
```

Expected: PASS.

- [ ] **Step 5: Run full install tests**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add py/install_global_codex_hooks.py py/tests/test_install_global_hooks.py
git commit -m "feat(codex): install guidance and commands"
```

## Task 3: Uninstall Codex Rule and Commands

**Files:**
- Modify: `py/uninstall_global_hooks.py`
- Modify: `py/tests/test_uninstall_global_hooks.py`

- [ ] **Step 1: Add failing uninstall test**

Append to `py/tests/test_uninstall_global_hooks.py`:

```python
def test_uninstall_global_removes_codex_guidance_and_commands(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    codex = fake_home / ".codex"
    commands = codex / "commands"
    commands.mkdir(parents=True)
    (codex / "AGENTS.md").write_text("Aftertone guidance\n", encoding="utf-8")
    (commands / "aftertone-on.md").write_text("on\n", encoding="utf-8")
    (commands / "aftertone-off.md").write_text("off\n", encoding="utf-8")
    (commands / "other.md").write_text("keep\n", encoding="utf-8")

    uninstall_global()

    assert not (codex / "AGENTS.md").exists()
    assert not (commands / "aftertone-on.md").exists()
    assert not (commands / "aftertone-off.md").exists()
    assert (commands / "other.md").exists()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run --directory py pytest tests/test_uninstall_global_hooks.py::test_uninstall_global_removes_codex_guidance_and_commands -q
```

Expected: FAIL because uninstall does not remove Codex guidance yet.

- [ ] **Step 3: Implement uninstall removal**

In `py/uninstall_global_hooks.py`, inside `uninstall_global()`, define:

```python
    codex_rule = user_codex / "AGENTS.md"
    codex_user_commands = user_codex / "commands"
    codex_command_glob = "aftertone-*.md"
```

In the dry-run block, add:

```python
        if codex_rule.is_file():
            print(f"would remove {codex_rule}")
        if codex_user_commands.is_dir():
            for p in sorted(codex_user_commands.glob(codex_command_glob)):
                print(f"would remove {p}")
```

Near the existing Claude command/rule removals, add:

```python
    if codex_user_commands.is_dir():
        for p in sorted(codex_user_commands.glob(codex_command_glob)):
            if p.is_file():
                p.unlink()
                print(f"removed: {p}")

    if codex_rule.is_file():
        codex_rule.unlink()
        print(f"removed: {codex_rule}")
```

- [ ] **Step 4: Run focused uninstall test**

Run:

```bash
uv run --directory py pytest tests/test_uninstall_global_hooks.py::test_uninstall_global_removes_codex_guidance_and_commands -q
```

Expected: PASS.

- [ ] **Step 5: Run full uninstall tests**

Run:

```bash
uv run --directory py pytest tests/test_uninstall_global_hooks.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add py/uninstall_global_hooks.py py/tests/test_uninstall_global_hooks.py
git commit -m "feat(codex): uninstall guidance and commands"
```

## Task 4: Sync Language Into Codex Rule

**Files:**
- Modify: `py/sync_spoken_rule_lang.py`
- Modify: `py/tests/test_speak_summary_config.py` or create `py/tests/test_sync_spoken_rule_lang.py`

- [ ] **Step 1: Add failing sync test**

Create `py/tests/test_sync_spoken_rule_lang.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sync_spoken_rule_lang import MARK_END, MARK_START, sync_rule


def test_sync_rule_updates_codex_global_template(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    repo = tmp_path / "repo"
    (repo / ".cursor/hooks").mkdir(parents=True)
    (repo / ".cursor/hooks/speak_summary.toml").write_text('lang = "fr"\n', encoding="utf-8")
    (repo / ".cursor/rules").mkdir(parents=True)
    (repo / ".cursor/rules/spoken-summary.mdc").write_text(
        MARK_START + "old\n" + MARK_END + "\n",
        encoding="utf-8",
    )
    (repo / "scripts/claude-global").mkdir(parents=True)
    (repo / "scripts/claude-global/spoken-summary.md").write_text(
        MARK_START + "old\n" + MARK_END + "\n",
        encoding="utf-8",
    )
    (repo / "scripts/codex-global").mkdir(parents=True)
    codex_rule = repo / "scripts/codex-global/AGENTS.md"
    codex_rule.write_text(MARK_START + "old\n" + MARK_END + "\n", encoding="utf-8")

    assert sync_rule(repo, check_only=False) == 0

    text = codex_rule.read_text(encoding="utf-8")
    assert "`fr`" in text
    assert "conversation language" in text
```

- [ ] **Step 2: Run sync test to verify failure**

Run:

```bash
uv run --directory py pytest tests/test_sync_spoken_rule_lang.py -q
```

Expected: FAIL because Codex rule is not synced yet.

- [ ] **Step 3: Add Codex blurb and sync path**

In `py/sync_spoken_rule_lang.py`, add:

```python
def _blurb_codex(lang: str) -> str:
    return (
        f"> **Locked `lang` for `<spoken_summary>` only:** `{lang}` "
        "(from `~/aftertone/.cursor/hooks/speak_summary.toml` on global install). "
        "Write the **inner tag** only in that language — **not** the conversation language. "
        "After changing `lang`, run `/aftertone-lang` or "
        "`uv run --directory py python sync_spoken_rule_lang.py` from the Aftertone repo.\n"
    )
```

Inside `sync_rule()`, after the Claude rule block, add:

```python
    codex_rule_src = repo / "scripts" / "codex-global" / "AGENTS.md"
    codex_changed = False
    if codex_rule_src.is_file():
        codex_body = codex_rule_src.read_text(encoding="utf-8")
        if MARK_START in codex_body and MARK_END in codex_body:
            codex_new, codex_changed = _replace_lang_block(
                codex_body, _blurb_codex(lang)
            )
            if codex_changed and not check_only:
                codex_rule_src.write_text(codex_new, encoding="utf-8")
                print(f"updated {codex_rule_src} (lang={lang})")
        elif not check_only:
            print(f"warn: skip {codex_rule_src} (no lang markers)", file=sys.stderr)
```

Also include `codex_changed` in the no-change condition:

```python
    if not changed and not claude_changed and not codex_changed:
```

After writing installed Claude rules, copy installed Codex rule if the source exists:

```python
    if codex_rule_src.is_file() and not check_only:
        dest = Path.home() / ".codex" / "AGENTS.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(codex_rule_src, dest)
        print(f"updated {dest}")
```

- [ ] **Step 4: Run sync test**

Run:

```bash
uv run --directory py pytest tests/test_sync_spoken_rule_lang.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add py/sync_spoken_rule_lang.py py/tests/test_sync_spoken_rule_lang.py
git commit -m "feat(codex): sync spoken language guidance"
```

## Task 5: Session Registration Smoke Test

**Files:**
- Modify: `py/tests/test_aftertone_v2.py`

- [ ] **Step 1: Add Codex session registration smoke test**

Append to `py/tests/test_aftertone_v2.py`:

```python
def test_codex_aftertone_on_registers_session_id_with_next_stop_hook(tmp_path):
    from argparse import Namespace
    from aftertone.cli import cmd_on
    from aftertone.sessions import load_sessions

    repo = tmp_path / "repo"
    hooks_dir = repo / ".cursor" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "speak_summary.toml").write_text("enabled = false\n", encoding="utf-8")
    py_dir = repo / "py"
    py_dir.mkdir(parents=True)
    (py_dir / "speak_summary_prepare.py").write_text("# test\n", encoding="utf-8")

    assert cmd_on(Namespace(repo_root=repo)) == 0

    hook = {
        "hook_event_name": "Stop",
        "session_id": "codex-session-smoke",
        "turn_id": "turn-smoke",
        "model": "gpt-5.1-codex",
        "permission_mode": "default",
        "last_assistant_message": "<spoken_summary>Codex registered this session!!</spoken_summary>",
    }
    cfg = {
        "enabled": True,
        "session_mode": "allowlist",
        "summary_mode": "tag_only",
        "only_speak_spoken_summary": True,
        "min_chars": 5,
        "max_chars": 2000,
        "spoken_summary_max_chars": 360,
        "expression_mode": "off",
    }

    out = prepare_payload(hook, cfg, repo)

    assert out is not None
    assert load_sessions(repo)["codex"] == ["codex-session-smoke"]
```

- [ ] **Step 2: Run smoke test**

Run:

```bash
uv run --directory py pytest tests/test_aftertone_v2.py::test_codex_aftertone_on_registers_session_id_with_next_stop_hook -q
```

Expected: PASS.

- [ ] **Step 3: Commit Task 5**

```bash
git add py/tests/test_aftertone_v2.py
git commit -m "test(codex): cover on command session registration"
```

## Task 6: Verification and PR Comment

**Files:**
- Verify only unless checks reveal a problem.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run --directory py pytest tests/test_install_global_hooks.py tests/test_uninstall_global_hooks.py tests/test_sync_spoken_rule_lang.py tests/test_aftertone_v2.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full Python tests**

Run:

```bash
ln -s /home/el-khal-omar/aftertone/assets assets
uv run --directory py pytest -q
rm assets
```

Expected: PASS.

- [ ] **Step 3: Run dry-run smoke checks**

Run:

```bash
uv run --directory py python install_global_codex_hooks.py --install-dir "$PWD" --dry-run
uv run --directory py python sync_spoken_rule_lang.py --repo-root "$PWD" --check
```

Expected: both exit 0.

- [ ] **Step 4: Run diff checks**

Run:

```bash
git diff --check
grep -RIn --exclude-dir=.venv -E '^<<<<<<<|^=======|^>>>>>>>' py scripts/codex-global docs/superpowers/plans || true
```

Expected: clean.

- [ ] **Step 5: Comment on issue #16**

Run:

```bash
gh issue comment 16 --body "Implemented and verified locally:

- \`uv run --directory py pytest tests/test_install_global_hooks.py tests/test_uninstall_global_hooks.py tests/test_sync_spoken_rule_lang.py tests/test_aftertone_v2.py -q\`
- \`uv run --directory py pytest -q\`
- \`uv run --directory py python install_global_codex_hooks.py --install-dir <worktree> --dry-run\`
- \`uv run --directory py python sync_spoken_rule_lang.py --repo-root <worktree> --check\`
- \`git diff --check\`

Codex guidance now installs under \`~/.codex\`, command docs explain per-session on/off/status, language locking syncs from TOML, and tests verify Codex session id registration after \`aftertone on\`."
```

- [ ] **Step 6: Commit the implementation plan**

```bash
git add docs/superpowers/plans/2026-05-28-codex-guidance-control.md
git commit -m "docs: plan Codex guidance and control"
```

## Self-Review

- Spec coverage: This plan covers Codex guidance, language locking, on/off/status command docs, terminal fallbacks, the "hook must run once" registration note, and a Codex allowlist registration smoke test.
- Placeholder scan: No task contains TBD/TODO/later/fill-in instructions.
- Type consistency: The plan consistently uses `install_global_codex()`, `sync_rule()`, `cmd_on()`, and `prepare_payload()`.
