# Codex Stop Hook Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a Codex `Stop` hook payload reach Aftertone's shared speech pipeline and produce the same speakable payload as Cursor and Claude.

**Architecture:** Codex should remain a thin adapter. The existing `aftertone.prepare.prepare_payload()` path already accepts `Stop` events and extracts `last_assistant_message`; this plan adds Codex-aware session classification and tests around Codex-shaped hook JSON so the shared pipeline can treat Codex sessions separately from Claude sessions.

**Tech Stack:** Python 3, pytest, existing `py/aftertone` package, Codex hook contract from https://developers.openai.com/codex/hooks.

---

## File Structure

- Modify `py/aftertone/sessions.py`
  - Extend the adapter type from `cursor | claude` to `cursor | claude | codex`.
  - Classify Codex hooks as `codex` when a `Stop` / `SubagentStop` hook includes Codex-specific fields such as `model`, `turn_id`, or `permission_mode`, while preserving Claude classification for Claude-style Stop hooks.
  - Include `codex` in the persisted session buckets.
- Modify `tests/test_aftertone_v2.py`
  - Add Codex-shaped payload tests for `prepare_payload()`, tag-only silence, and allowlist behavior.
  - Add a regression test that Claude Stop still uses the `claude` session bucket.
- Optionally modify `py/aftertone/prepare.py`
  - Only if tests reveal a Codex-specific event field needs normalization. Do not add a separate Codex prepare path.

## Task 1: Add Codex Adapter Session Buckets

**Files:**
- Modify: `py/aftertone/sessions.py`
- Test: `tests/test_aftertone_v2.py`

- [ ] **Step 1: Write failing tests for adapter classification**

Append these tests to `tests/test_aftertone_v2.py` near the existing session tests:

```python
def test_hook_adapter_distinguishes_codex_stop_from_claude_stop():
    from aftertone.sessions import hook_adapter

    codex_hook = {
        "hook_event_name": "Stop",
        "session_id": "codex-session",
        "turn_id": "turn-1",
        "model": "gpt-5.1-codex",
        "permission_mode": "default",
        "last_assistant_message": "<spoken_summary>Codex spoke!!</spoken_summary>",
    }
    claude_hook = {
        "hook_event_name": "Stop",
        "session_id": "claude-session",
        "transcript_path": "/tmp/.claude/projects/demo/transcript.jsonl",
        "last_assistant_message": "<spoken_summary>Claude spoke!!</spoken_summary>",
    }

    assert hook_adapter(codex_hook) == "codex"
    assert hook_adapter(claude_hook) == "claude"


def test_empty_sessions_includes_codex_bucket(tmp_path):
    from aftertone.sessions import load_sessions

    assert load_sessions(tmp_path) == {"cursor": [], "claude": [], "codex": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --directory py pytest tests/test_aftertone_v2.py::test_hook_adapter_distinguishes_codex_stop_from_claude_stop tests/test_aftertone_v2.py::test_empty_sessions_includes_codex_bucket -q
```

Expected: FAIL. The first test should report that Codex is currently classified as `claude`; the second should report that the `codex` bucket is missing.

- [ ] **Step 3: Implement the adapter type and empty bucket**

In `py/aftertone/sessions.py`, change the adapter type and empty sessions shape:

```python
Adapter = Literal["cursor", "claude", "codex"]
```

Replace `_empty_sessions()` with:

```python
def _empty_sessions() -> dict[str, list[str]]:
    return {"cursor": [], "claude": [], "codex": []}
```

- [ ] **Step 4: Update all fixed adapter loops**

In `py/aftertone/sessions.py`, replace loops over `("cursor", "claude")` with `("cursor", "claude", "codex")` in:

- `load_sessions`
- `save_sessions`
- `cmd_session_off`

The resulting loop shape should be:

```python
for adapter in ("cursor", "claude", "codex"):
    ...
```

- [ ] **Step 5: Add Codex hook detection**

In `py/aftertone/sessions.py`, add this helper above `hook_adapter()`:

```python
def _looks_like_codex_hook(hook: dict) -> bool:
    if any(k in hook for k in ("turn_id", "permission_mode", "model")):
        return True
    cwd = hook.get("cwd")
    if isinstance(cwd, str) and "/.codex/" in cwd:
        return True
    return False
```

Then replace the `Stop` / `SubagentStop` branch in `hook_adapter()` with:

```python
if event in ("Stop", "SubagentStop"):
    if _looks_like_codex_hook(hook):
        return "codex"
    return "claude"
```

Do not change the `afterAgentResponse` branch.

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run --directory py pytest tests/test_aftertone_v2.py::test_hook_adapter_distinguishes_codex_stop_from_claude_stop tests/test_aftertone_v2.py::test_empty_sessions_includes_codex_bucket -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add py/aftertone/sessions.py tests/test_aftertone_v2.py
git commit -m "feat(codex): classify Codex stop hook sessions"
```

## Task 2: Prove Codex Stop Payload Prepares Speech

**Files:**
- Modify: `tests/test_aftertone_v2.py`

- [ ] **Step 1: Write failing Codex prepare test**

Append this test near `test_prepare_accepts_claude_stop_event`:

```python
def test_prepare_accepts_codex_stop_event():
    hook = {
        "hook_event_name": "Stop",
        "session_id": "codex-session-1",
        "turn_id": "turn-1",
        "model": "gpt-5.1-codex",
        "permission_mode": "default",
        "cwd": "/tmp/aftertone",
        "last_assistant_message": (
            "Implemented the Codex adapter tracer bullet.\n\n"
            "<spoken_summary>\n"
            "The Codex Stop hook path is wired for speech!!\n"
            "</spoken_summary>"
        ),
    }
    cfg = {
        "enabled": True,
        "summary_mode": "tag_only",
        "only_speak_spoken_summary": True,
        "min_chars": 5,
        "max_chars": 2000,
        "spoken_summary_max_chars": 360,
        "total_step": 8,
        "speed": 1.15,
        "lang": "en",
        "mode": "queue",
        "expression_mode": "off",
    }

    out = prepare_payload(hook, cfg)

    assert out is not None
    assert out["text"] == "The Codex Stop hook path is wired for speech!!"
    assert out["totalStep"] == 8
    assert out["speed"] == 1.15
    assert out["lang"] == "en"
    assert out["mode"] == "queue"
```

- [ ] **Step 2: Run the test**

Run:

```bash
uv run --directory py pytest tests/test_aftertone_v2.py::test_prepare_accepts_codex_stop_event -q
```

Expected: PASS if Task 1 did not disturb prepare behavior. If it fails, inspect only `py/aftertone/prepare.py` and `py/aftertone/extract.py`; do not create a Codex-only prepare path.

- [ ] **Step 3: Commit Task 2**

If the test passed without implementation changes:

```bash
git add tests/test_aftertone_v2.py
git commit -m "test(codex): cover Stop hook speech payload"
```

If implementation changes were required:

```bash
git add tests/test_aftertone_v2.py py/aftertone/prepare.py py/aftertone/extract.py
git commit -m "feat(codex): prepare Stop hook speech payload"
```

## Task 3: Prove Codex Tag-Only Silence and Unsupported Events

**Files:**
- Modify: `tests/test_aftertone_v2.py`

- [ ] **Step 1: Add no-tag silence test**

Append:

```python
def test_prepare_codex_stop_without_tag_is_silent_in_tag_only_mode():
    hook = {
        "hook_event_name": "Stop",
        "session_id": "codex-session-2",
        "turn_id": "turn-2",
        "model": "gpt-5.1-codex",
        "permission_mode": "default",
        "last_assistant_message": "No spoken tag in this response.",
    }
    cfg = {
        "enabled": True,
        "summary_mode": "tag_only",
        "only_speak_spoken_summary": True,
        "min_chars": 5,
        "max_chars": 2000,
        "spoken_summary_max_chars": 360,
        "expression_mode": "off",
    }

    assert prepare_payload(hook, cfg) is None
```

- [ ] **Step 2: Add unsupported Codex event test**

Append:

```python
def test_prepare_skips_codex_user_prompt_submit_event():
    hook = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "codex-session-3",
        "turn_id": "turn-3",
        "model": "gpt-5.1-codex",
        "permission_mode": "default",
        "prompt": "Please do the work.",
        "last_assistant_message": "<spoken_summary>Should not speak!!</spoken_summary>",
    }
    cfg = {
        "enabled": True,
        "summary_mode": "tag_only",
        "only_speak_spoken_summary": True,
        "min_chars": 5,
        "max_chars": 2000,
        "spoken_summary_max_chars": 360,
        "expression_mode": "off",
    }

    assert prepare_payload(hook, cfg) is None
```

- [ ] **Step 3: Run both tests**

Run:

```bash
uv run --directory py pytest tests/test_aftertone_v2.py::test_prepare_codex_stop_without_tag_is_silent_in_tag_only_mode tests/test_aftertone_v2.py::test_prepare_skips_codex_user_prompt_submit_event -q
```

Expected: PASS.

- [ ] **Step 4: Commit Task 3**

```bash
git add tests/test_aftertone_v2.py
git commit -m "test(codex): cover silent Stop hook cases"
```

## Task 4: Prove Codex Session Allowlist Registration

**Files:**
- Modify: `tests/test_aftertone_v2.py`
- Modify: `py/aftertone/sessions.py` only if the tests reveal a bug.

- [ ] **Step 1: Add Codex allowlist blocking and registration test**

Append:

```python
def test_codex_session_allowlist_blocks_and_registers_pending_on(tmp_path):
    from aftertone.sessions import cmd_session_on, load_sessions, save_sessions

    repo = tmp_path / "repo"
    hooks_dir = repo / ".cursor" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "speak_summary.toml").write_text(
        'enabled = true\nsession_mode = "allowlist"\n',
        encoding="utf-8",
    )
    save_sessions(repo, {"cursor": [], "claude": [], "codex": ["allowed-codex"]})

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
    hook = {
        "hook_event_name": "Stop",
        "session_id": "blocked-codex",
        "turn_id": "turn-blocked",
        "model": "gpt-5.1-codex",
        "permission_mode": "default",
        "last_assistant_message": "<spoken_summary>Blocked Codex!!</spoken_summary>",
    }

    assert prepare_payload(hook, cfg, repo) is None

    assert cmd_session_on(repo) == 0
    hook["session_id"] = "new-codex"
    hook["turn_id"] = "turn-new"
    hook["last_assistant_message"] = "<spoken_summary>Registered Codex!!</spoken_summary>"
    out = prepare_payload(hook, cfg, repo)

    assert out is not None
    assert "Registered Codex" in out["text"]
    assert load_sessions(repo)["codex"] == ["allowed-codex", "new-codex"]
```

- [ ] **Step 2: Add Claude regression test**

Append:

```python
def test_claude_stop_still_registers_claude_bucket(tmp_path):
    from aftertone.sessions import cmd_session_on, load_sessions

    repo = tmp_path / "repo"
    hooks_dir = repo / ".cursor" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "speak_summary.toml").write_text(
        'enabled = true\nsession_mode = "allowlist"\n',
        encoding="utf-8",
    )
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

    assert cmd_session_on(repo) == 0
    hook = {
        "hook_event_name": "Stop",
        "session_id": "claude-session-new",
        "transcript_path": "/tmp/.claude/projects/demo/transcript.jsonl",
        "last_assistant_message": "<spoken_summary>Registered Claude!!</spoken_summary>",
    }

    out = prepare_payload(hook, cfg, repo)

    assert out is not None
    assert load_sessions(repo)["claude"] == ["claude-session-new"]
    assert load_sessions(repo)["codex"] == []
```

- [ ] **Step 3: Run allowlist tests**

Run:

```bash
uv run --directory py pytest tests/test_aftertone_v2.py::test_codex_session_allowlist_blocks_and_registers_pending_on tests/test_aftertone_v2.py::test_claude_stop_still_registers_claude_bucket -q
```

Expected: PASS. If it fails because `save_sessions()` drops `codex`, complete Task 1 Step 4 first.

- [ ] **Step 4: Commit Task 4**

```bash
git add py/aftertone/sessions.py tests/test_aftertone_v2.py
git commit -m "test(codex): cover session allowlist behavior"
```

## Task 5: Full Verification for Issue #14

**Files:**
- Verify only; no expected edits.

- [ ] **Step 1: Run focused package tests**

Run:

```bash
uv run --directory py pytest tests/test_aftertone_v2.py -q
```

Expected: all tests in `test_aftertone_v2.py` pass.

- [ ] **Step 2: Run all Python tests**

Run:

```bash
uv run --directory py pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run whitespace/conflict checks**

Run:

```bash
git diff --check
grep -RIn -E '<<<<<<<|=======|>>>>>>>' py/aftertone py/tests docs/superpowers/plans || true
```

Expected: `git diff --check` exits 0 and `grep` prints nothing.

- [ ] **Step 4: Update GitHub issue #14**

Post a comment on issue #14 with the verification evidence:

```bash
gh issue comment 14 --body "Implemented and verified locally:

- \`uv run --directory py pytest tests/test_aftertone_v2.py -q\`
- \`uv run --directory py pytest -q\`
- \`git diff --check\`

Codex-shaped \`Stop\` payloads now prepare speech through the shared pipeline, tag-only mode stays silent without a tag, and Codex session ids use their own allowlist bucket."
```

- [ ] **Step 5: Commit final plan status if needed**

If the plan file is being committed with the implementation:

```bash
git add docs/superpowers/plans/2026-05-28-codex-stop-hook-core.md
git commit -m "docs: plan Codex Stop hook core"
```

## Self-Review

- Spec coverage: This plan covers issue #14 acceptance criteria for Codex `Stop` payload speech, tag-only silence, session allowlist behavior, JSON-or-empty stdout compatibility through the existing hook path, and tests for success/missing text/disabled or unsupported flows. It intentionally does not cover global install, Codex guidance, MCP, or public docs.
- Placeholder scan: No task contains TBD/TODO/later/fill-in instructions.
- Type consistency: The plan uses `Adapter = Literal["cursor", "claude", "codex"]`, `hook_adapter()`, `load_sessions()`, `save_sessions()`, and `prepare_payload()` consistently across tasks.
