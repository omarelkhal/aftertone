"""Aftertone v2 package tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aftertone.config import summary_mode
from aftertone.defaults import apply_install_defaults
from aftertone.hook_json import decode_hook_bytes, loads_hook_json
from aftertone.prepare import prepare_payload
from aftertone.summary import build_speakable_text
from aftertone.text_utils import heuristic_spoken


def test_summary_mode_tag_only_default():
    assert summary_mode({}) == "tag_only"
    assert summary_mode({"only_speak_spoken_summary": False}) == "tag_only"
    assert summary_mode({"summary_mode": "auto"}) == "auto"
    assert summary_mode({"summary_mode": "heuristic"}) == "heuristic"


def test_windows_path_json_escape():
    raw = r'{"text":"ok","transcript_path":"c:\Users\pc\file.jsonl"}'
    d = loads_hook_json(raw)
    assert "Users" in d["transcript_path"]


def test_utf16_hook_decode():
    payload = '{"text":"hello"}'
    utf16 = payload.encode("utf-16-le")
    assert loads_hook_json(decode_hook_bytes(utf16))["text"] == "hello"


def test_auto_summary_without_tag():
    cfg = {
        "enabled": True,
        "summary_mode": "auto",
        "min_chars": 5,
        "max_chars": 2000,
        "heuristic_max_sentences": 2,
        "heuristic_max_sentences_code_heavy": 1,
        "heuristic_code_fence_fraction": 0.35,
        "expression_mode": "off",
    }
    raw = "Sure. The daemon is running and tests passed."
    text, source = build_speakable_text(
        raw,
        cfg,
        "auto",
        min_chars=5,
        max_chars=2000,
        h_max=2,
        h_code_max=1,
        fence_thr=0.35,
        apply_expression_fn=lambda t, _s, _m: t,
    )
    assert source in ("heuristic", "excerpt")
    assert "daemon" in text.lower() or "tests" in text.lower()


def test_tag_only_silent_without_tag():
    cfg = {"summary_mode": "tag_only", "expression_mode": "off"}
    text, source = build_speakable_text(
        "No tag here, just prose.",
        cfg,
        "tag_only",
        min_chars=5,
        max_chars=2000,
        h_max=2,
        h_code_max=1,
        fence_thr=0.35,
        apply_expression_fn=lambda t, _s, _m: t,
    )
    assert source == "empty"
    assert text == ""


def test_prepare_payload_after_agent_response():
    hook = {
        "hook_event_name": "afterAgentResponse",
        "text": "Implemented v2. The hook now auto-summarizes when tags are missing.",
        "generation_id": "g1",
    }
    cfg = {
        "enabled": True,
        "summary_mode": "auto",
        "min_chars": 5,
        "max_chars": 2000,
        "total_step": 4,
        "speed": 1.0,
        "lang": "en",
        "mode": "queue",
        "heuristic_max_sentences": 2,
        "heuristic_max_sentences_code_heavy": 1,
        "heuristic_code_fence_fraction": 0.35,
        "expression_mode": "off",
    }
    out = prepare_payload(hook, cfg)
    assert out is not None
    assert "text" in out
    assert len(out["text"]) >= 5


def test_prepare_skips_unrelated_hook_events():
    hook = {"hook_event_name": "UserPromptSubmit", "text": "hello"}
    cfg = {"enabled": True, "summary_mode": "auto"}
    assert prepare_payload(hook, cfg) is None


def test_resolve_raw_text_prefers_last_assistant_message():
    from aftertone.extract import resolve_raw_text

    hook = {
        "hook_event_name": "Stop",
        "last_assistant_message": (
            "<spoken_summary>Spoken from last assistant message!!</spoken_summary>"
        ),
        "transcript_path": "/nonexistent/transcript.jsonl",
    }
    raw = resolve_raw_text(hook, "Stop")
    assert "last assistant message" in raw


def test_session_allowlist_blocks_unlisted(tmp_path):
    from aftertone.sessions import save_sessions

    repo = tmp_path / "repo"
    hooks = repo / ".cursor" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "speak_summary.toml").write_text(
        'enabled = true\nsession_mode = "allowlist"\n',
        encoding="utf-8",
    )
    save_sessions(repo, {"cursor": ["conv-allowed"], "claude": []})

    hook = {
        "hook_event_name": "afterAgentResponse",
        "text": "Hello. <spoken_summary>Hi there!!</spoken_summary>",
        "conversation_id": "conv-other",
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
    assert prepare_payload(hook, cfg, repo) is None

    hook["conversation_id"] = "conv-allowed"
    out = prepare_payload(hook, cfg, repo)
    assert out is not None
    assert "Hi there" in out["text"]


def test_cli_on_registers_session_allowlist(tmp_path):
    from aftertone.cli import cmd_on
    from argparse import Namespace
    from aftertone.sessions import load_sessions

    repo = tmp_path / "repo"
    hooks = repo / ".cursor" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "speak_summary.toml").write_text("enabled = false\n", encoding="utf-8")
    py_dir = repo / "py"
    py_dir.mkdir(parents=True)
    (py_dir / "speak_summary_prepare.py").write_text("# test\n", encoding="utf-8")

    rc = cmd_on(Namespace(repo_root=repo))
    assert rc == 0
    text = (hooks / "speak_summary.toml").read_text(encoding="utf-8")
    assert 'session_mode = "allowlist"' in text
    assert "enabled = true" in text


def test_pending_session_on_registers_id(tmp_path):
    from aftertone.sessions import cmd_session_on, load_sessions

    repo = tmp_path / "repo"
    hooks = repo / ".cursor" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "speak_summary.toml").write_text("enabled = true\n", encoding="utf-8")
    cmd_session_on(repo)

    hook = {
        "hook_event_name": "afterAgentResponse",
        "text": "ok <spoken_summary>Registered!!</spoken_summary>",
        "conversation_id": "conv-new",
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
    assert "conv-new" in load_sessions(repo)["cursor"]


def test_prepare_accepts_claude_stop_event():
    hook = {
        "hook_event_name": "Stop",
        "last_assistant_message": (
            "Done.\n\n<spoken_summary>\n"
            "The Claude Stop hook path is wired for speech!!\n"
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
        "expression_mode": "off",
    }
    out = prepare_payload(hook, cfg)
    assert out is not None
    assert "Claude Stop" in out["text"]


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


def test_wait_spoken_job_reads_jsonl(tmp_path):
    from aftertone.cli import _find_spoken_job, _wait_spoken_job

    spoken = tmp_path / ".cursor" / "hooks" / "state" / "spoken"
    spoken.mkdir(parents=True)
    from datetime import date

    log = spoken / f"{date.today().isoformat()}.jsonl"
    log.write_text(
        json.dumps({"job_id": "other", "took_ms": 1}) + "\n",
        encoding="utf-8",
    )

    repo = tmp_path

    import aftertone.cli as cli_mod

    orig = cli_mod._spoken_log_path
    cli_mod._spoken_log_path = lambda r: log  # type: ignore[assignment]
    try:
        assert _find_spoken_job(repo, "missing") is None
        log.write_text(
            log.read_text(encoding="utf-8")
            + json.dumps(
                {
                    "job_id": "abc",
                    "first_audio_ms": 4200,
                    "took_ms": 9000,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        rec = _wait_spoken_job(repo, "abc", timeout_sec=1.0)
        assert rec is not None
        assert rec["first_audio_ms"] == 4200
    finally:
        cli_mod._spoken_log_path = orig


def test_apply_install_defaults_full_spoken_summary(tmp_path: Path) -> None:
    toml = tmp_path / "speak_summary.toml"
    toml.write_text(
        "summary_mode = \"auto\"\n"
        "total_step = 5\n"
        "spoken_summary_max_sentences = 1\n",
        encoding="utf-8",
    )
    apply_install_defaults(toml)
    text = toml.read_text(encoding="utf-8")
    assert 'summary_mode = "tag_only"' in text
    assert "total_step = 8" in text
    assert "spoken_summary_max_sentences = 0" in text
