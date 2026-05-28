"""Resolve assistant text from hook JSON and transcript files."""

from __future__ import annotations

import json
import os
from pathlib import Path

from aftertone.spoken_tag import parse_spoken_summary


def _content_text(parts: object) -> str:
    if isinstance(parts, str):
        return parts.strip()
    if not isinstance(parts, list):
        return ""
    texts: list[str] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        if p.get("type") not in ("text", "output_text"):
            continue
        t = p.get("text")
        if isinstance(t, str) and t.strip():
            texts.append(t.strip())
    return "\n".join(texts)


def assistant_text_blocks(lines: list[str]) -> str:
    last_text = ""
    last_spoken_text = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        text = ""
        if obj.get("role") == "assistant":
            text = _content_text(obj.get("content"))
            if not text:
                msg = obj.get("message")
                if isinstance(msg, str):
                    text = msg.strip()
                elif isinstance(msg, dict):
                    text = _content_text(msg.get("content"))
        payload = obj.get("payload")
        if not text and isinstance(payload, dict):
            if payload.get("type") == "agent_message":
                msg = payload.get("message")
                if isinstance(msg, str):
                    text = msg.strip()
            elif payload.get("type") == "message" and payload.get("role") == "assistant":
                text = _content_text(payload.get("content"))

        if not text:
            continue
        last_text = text
        if parse_spoken_summary(text)[0]:
            last_spoken_text = text

    return last_spoken_text or last_text


def hook_inline_text(hook: dict) -> str:
    # Claude Code Stop / SubagentStop (https://code.claude.com/docs/en/hooks#stop)
    lam = hook.get("last_assistant_message")
    if isinstance(lam, str) and lam.strip():
        return lam.strip()
    for key in ("text", "response", "message", "content"):
        v = hook.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def transcript_assistant_text(hook: dict) -> str:
    transcript = hook.get("transcript_path") or os.environ.get("CURSOR_TRANSCRIPT_PATH")
    if not transcript or not os.path.isfile(transcript):
        return ""
    with open(transcript, encoding="utf-8", errors="replace") as f:
        return assistant_text_blocks(f.readlines())


def resolve_raw_text(hook: dict, event: str) -> str:
    if event in ("afterAgentResponse", "Stop", "SubagentStop"):
        inline = hook_inline_text(hook)
        if inline:
            if parse_spoken_summary(inline)[0]:
                return inline
            from_transcript = transcript_assistant_text(hook)
            if from_transcript and parse_spoken_summary(from_transcript)[0]:
                return from_transcript
            if event == "afterAgentResponse":
                return inline
        return transcript_assistant_text(hook)
    return transcript_assistant_text(hook)


def hook_event_name(hook: dict) -> str:
    return str(hook.get("hook_event_name") or hook.get("hookEventName") or "")
