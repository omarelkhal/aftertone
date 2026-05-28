"""Build POST /say JSON from Cursor hook stdin (v2 entry)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

from aftertone.config import cfg_enabled, load_config, summary_mode
from aftertone.extract import hook_event_name, resolve_raw_text
from aftertone.sessions import process_pending_from_hook, session_allows_speech
from aftertone.hook_json import decode_hook_bytes, loads_hook_json
from aftertone.paths import install_root, state_dir
from aftertone.summary import build_speakable_text
from aftertone.text_utils import cfg_float_bounded, cfg_int_bounded, in_quiet_hours

# Post-response hook events that may carry assistant text (Cursor vs Claude Code).
_RESPONSE_HOOK_EVENTS = frozenset(
    {"afterAgentResponse", "Stop", "SubagentStop"}
)


def _skip(hook: dict, reason: str) -> None:
    hook["_aftertone_skip_reason"] = reason


def _has_transcript_path(hook: dict) -> bool:
    transcript = hook.get("transcript_path")
    return isinstance(transcript, str) and bool(transcript.strip())


def _codex_transcript_retry_delays(cfg: dict) -> list[float]:
    raw = cfg.get("codex_transcript_retry_delays", "0.15,0.35,0.75")
    if isinstance(raw, (int, float)):
        return [max(0.0, min(float(raw), 2.0))]
    if not isinstance(raw, str):
        return []
    delays: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            delays.append(max(0.0, min(float(part), 2.0)))
        except ValueError:
            continue
    return delays[:5]


def prepare_payload(hook: dict, cfg: dict | None = None, root=None) -> dict | None:
    if root is None:
        try:
            root = install_root()
        except FileNotFoundError:
            root = None

    cfg = cfg if cfg is not None else load_config(root)

    event = hook_event_name(hook)
    if (not event or event in _RESPONSE_HOOK_EVENTS) and root is not None:
        process_pending_from_hook(root, hook)

    if not cfg_enabled(cfg):
        _skip(hook, "disabled")
        return None

    allowed, skip_reason = session_allows_speech(cfg, hook, root)
    if not allowed:
        _skip(hook, skip_reason or "session_blocked")
        return None

    quiet = str(cfg.get("quiet_hours", ""))
    if os.environ.get("SPEAK_SUMMARY_IGNORE_QUIET", "").strip() not in (
        "1",
        "true",
        "yes",
    ) and in_quiet_hours(datetime.now().astimezone(), quiet):
        _skip(hook, "quiet_hours")
        return None

    min_chars = int(cfg.get("min_chars", 5))
    max_chars = int(cfg.get("max_chars", 2000))
    h_max = cfg_int_bounded(cfg, "heuristic_max_sentences", 2, 1, 3)
    h_code_max = cfg_int_bounded(cfg, "heuristic_max_sentences_code_heavy", 1, 1, 3)
    fence_thr = cfg_float_bounded(cfg, "heuristic_code_fence_fraction", 0.35, 0.05, 0.95)

    if event and event not in _RESPONSE_HOOK_EVENTS:
        _skip(hook, f"event:{event}")
        return None

    mode = summary_mode(cfg)
    expression_mode = str(cfg.get("expression_mode", "off")).lower()

    def _apply_expression(text: str, flow_state: str | None, mode_name: str) -> str:
        if expression_mode in ("", "off"):
            return text
        from expression_tags import apply_expression

        return apply_expression(text, flow_state, mode_name)

    text = ""
    retry_delays = []
    if event == "Stop" and _has_transcript_path(hook):
        retry_delays = _codex_transcript_retry_delays(cfg)

    for delay in [0.0, *retry_delays]:
        if delay:
            time.sleep(delay)
        raw_text = resolve_raw_text(hook, event or "afterAgentResponse")
        if not raw_text:
            continue
        text, _source = build_speakable_text(
            raw_text,
            cfg,
            mode,
            min_chars=min_chars,
            max_chars=max_chars,
            h_max=h_max,
            h_code_max=h_code_max,
            fence_thr=fence_thr,
            apply_expression_fn=_apply_expression,
        )
        if text:
            break
    if not text:
        _skip(hook, "no_text")
        return None

    return {
        "text": text,
        "generation_id": hook.get("generation_id"),
        "conversation_id": hook.get("conversation_id"),
        "totalStep": int(cfg.get("total_step", 8)),
        "speed": float(cfg.get("speed", 1.0)),
        "lang": str(cfg.get("lang", "en")),
        "mode": str(cfg.get("mode", "queue")).lower(),
    }


def _daemon_port(repo) -> int:
    cfg = load_config(repo)
    port = int(cfg.get("port", 8765))
    port_file = state_dir(repo) / "tts-daemon.port"
    if port_file.is_file():
        try:
            port = int(port_file.read_text(encoding="utf-8").strip())
        except ValueError:
            pass
    return port


def post_say_payload(repo, payload: dict) -> tuple[int, int]:
    """POST /say; returns (http_status, post_ms)."""
    port = _daemon_port(repo)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/say",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
    except urllib.error.URLError:
        raise
    post_ms = int((time.perf_counter() - t0) * 1000)
    return status, post_ms


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare hook JSON for /say")
    parser.add_argument(
        "--post",
        action="store_true",
        help="Prepare and POST in one process (faster hook on Windows)",
    )
    args = parser.parse_args()

    t_prepare = time.perf_counter()
    raw_hook = decode_hook_bytes(sys.stdin.buffer.read())
    try:
        hook = loads_hook_json(raw_hook)
    except json.JSONDecodeError as exc:
        print(f"hook_json_invalid: {exc}", file=sys.stderr)
        print("{}")
        return

    try:
        root = install_root()
    except FileNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        print("{}")
        return

    cfg = load_config(root)
    out = prepare_payload(hook, cfg, root)
    prepare_ms = int((time.perf_counter() - t_prepare) * 1000)
    if out is None:
        print("{}")
        return
    print(json.dumps(out, ensure_ascii=False))

    if not args.post:
        return

    post_ms = 0
    http_status = 0
    try:
        http_status, post_ms = post_say_payload(root, out)
    except urllib.error.URLError as exc:
        print(
            f"hook_metrics prepare_ms={prepare_ms} post_ms=0 http=0 post_error={exc}",
            file=sys.stderr,
        )
        return
    print(
        f"hook_metrics prepare_ms={prepare_ms} post_ms={post_ms} http={http_status} "
        f"payload_chars={len(out.get('text', ''))}",
        file=sys.stderr,
    )
