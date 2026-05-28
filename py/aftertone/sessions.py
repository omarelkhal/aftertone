"""Per-session allowlist for spoken TTS (state JSON + optional TOML session_mode)."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Literal

from aftertone.paths import config_path, state_dir

SessionMode = Literal["all", "allowlist", "denylist"]
Adapter = Literal["cursor", "claude", "codex"]

_SESSIONS_NAME = "enabled_sessions.json"
_PENDING_ON = "pending_session_on.json"
_PENDING_OFF = "pending_session_off.json"
_PENDING_FLIP = "pending_session_flip.json"
_ENABLED_LINE = re.compile(
    r"^(\s*)enabled\s*=\s*(true|false)\s*(#.*)?$",
    re.IGNORECASE | re.MULTILINE,
)
_SESSION_MODE_LINE = re.compile(
    r"^(\s*)session_mode\s*=\s*.*?(#.*)?$",
    re.IGNORECASE | re.MULTILINE,
)
_MAX_IDS_PER_ADAPTER = 64
_STALE_PENDING_SEC = 300.0


def session_mode(cfg: dict) -> SessionMode:
    raw = str(cfg.get("session_mode", "all")).strip().lower()
    if raw in ("all", "allowlist", "denylist"):
        return raw  # type: ignore[return-value]
    return "all"


def _looks_like_codex_hook(hook: dict) -> bool:
    if any(k in hook for k in ("turn_id", "permission_mode", "model")):
        return True
    cwd = hook.get("cwd")
    if isinstance(cwd, str) and "/.codex/" in cwd:
        return True
    return False


def hook_adapter(hook: dict) -> Adapter:
    event = str(hook.get("hook_event_name") or hook.get("hookEventName") or "").strip()
    if event == "afterAgentResponse":
        return "cursor"
    if event in ("Stop", "SubagentStop"):
        if _looks_like_codex_hook(hook):
            return "codex"
        return "claude"
    tp = hook.get("transcript_path")
    if isinstance(tp, str) and ("/.claude/" in tp or tp.startswith("~/.claude")):
        return "claude"
    return "cursor"


def hook_session_id(hook: dict, adapter: Adapter | None = None) -> str | None:
    for key in ("conversation_id", "conversationId", "session_id", "sessionId"):
        v = hook.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    tp = hook.get("transcript_path")
    if isinstance(tp, str) and tp.strip():
        return f"transcript:{tp.strip()}"
    if adapter == "claude":
        cwd = hook.get("cwd") or hook.get("workspace_path")
        if isinstance(cwd, str) and cwd.strip():
            return f"cwd:{cwd.strip()}"
    return None


def _sessions_path(root: Path) -> Path:
    return state_dir(root) / _SESSIONS_NAME


def _pending_path(root: Path, action: str) -> Path:
    name = _PENDING_ON if action == "on" else _PENDING_OFF
    return state_dir(root) / name


def _empty_sessions() -> dict[str, list[str]]:
    return {"cursor": [], "claude": [], "codex": []}


def load_sessions(root: Path) -> dict[str, list[str]]:
    path = _sessions_path(root)
    if not path.is_file():
        return _empty_sessions()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_sessions()
    out = _empty_sessions()
    if isinstance(data, dict):
        for adapter in ("cursor", "claude", "codex"):
            raw = data.get(adapter)
            if isinstance(raw, list):
                out[adapter] = [str(x).strip() for x in raw if str(x).strip()][
                    :_MAX_IDS_PER_ADAPTER
                ]
    return out


def save_sessions(root: Path, data: dict[str, list[str]]) -> None:
    path = _sessions_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _empty_sessions()
    for adapter in ("cursor", "claude", "codex"):
        seen: set[str] = set()
        bucket: list[str] = []
        for sid in data.get(adapter, []):
            s = str(sid).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            bucket.append(s)
            if len(bucket) >= _MAX_IDS_PER_ADAPTER:
                break
        normalized[adapter] = bucket
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _add_session(root: Path, adapter: Adapter, session_id: str) -> bool:
    data = load_sessions(root)
    bucket = data[adapter]
    if session_id in bucket:
        return False
    bucket.append(session_id)
    save_sessions(root, data)
    return True


def _remove_session(root: Path, adapter: Adapter, session_id: str) -> bool:
    data = load_sessions(root)
    bucket = data[adapter]
    if session_id not in bucket:
        return False
    data[adapter] = [x for x in bucket if x != session_id]
    save_sessions(root, data)
    return True


def set_enabled_toml(root: Path, enabled: bool) -> None:
    path = config_path(root)
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    value = "true" if enabled else "false"
    if _ENABLED_LINE.search(text):
        text = _ENABLED_LINE.sub(
            lambda m: f"{m.group(1)}enabled = {value}{m.group(3) or ''}",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + f"\n\nenabled = {value}\n"
    path.write_text(text, encoding="utf-8")


def set_session_mode_toml(root: Path, mode: SessionMode) -> None:
    path = config_path(root)
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    line = f'"{mode}"'
    if _SESSION_MODE_LINE.search(text):
        text = _SESSION_MODE_LINE.sub(
            lambda m: f"{m.group(1)}session_mode = {line}{m.group(2) or ''}",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + f'\nsession_mode = {line}\n'
    path.write_text(text, encoding="utf-8")


def _write_pending(root: Path, action: str) -> None:
    path = _pending_path(root, action)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"action": action, "ts": time.time()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_pending(root: Path, action: str) -> dict[str, Any] | None:
    path = _pending_path(root, action)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        return None
    if not isinstance(data, dict):
        path.unlink(missing_ok=True)
        return None
    ts = float(data.get("ts") or 0)
    if ts and (time.time() - ts) > _STALE_PENDING_SEC:
        path.unlink(missing_ok=True)
        return None
    return data


def _clear_pending(root: Path, action: str) -> None:
    if action in ("on", "off"):
        _pending_path(root, action).unlink(missing_ok=True)


def _clear_all_pending(root: Path) -> None:
    for name in ("on", "off"):
        _pending_path(root, name).unlink(missing_ok=True)
    state_dir(root).joinpath(_PENDING_FLIP).unlink(missing_ok=True)


def process_pending_from_hook(root: Path, hook: dict) -> dict[str, str] | None:
    """Apply pending session on/off using this hook's session id."""
    adapter = hook_adapter(hook)
    sid = hook_session_id(hook, adapter)
    if not sid:
        return None

    out: dict[str, str] = {}
    if _read_pending(root, "on") is not None:
        added = _add_session(root, adapter, sid)
        _clear_pending(root, "on")
        out["registered"] = sid
        out["adapter"] = adapter
        out["added"] = "true" if added else "false"

    if _read_pending(root, "off") is not None:
        removed = _remove_session(root, adapter, sid)
        _clear_pending(root, "off")
        out["unregistered"] = sid
        out["adapter"] = adapter
        out["removed"] = "true" if removed else "false"

    flip_path = state_dir(root) / _PENDING_FLIP
    if flip_path.is_file():
        try:
            json.loads(flip_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            flip_path.unlink(missing_ok=True)
        else:
            data = load_sessions(root)
            bucket = data[adapter]
            if sid in bucket:
                _remove_session(root, adapter, sid)
                out["toggled"] = "off"
            else:
                _add_session(root, adapter, sid)
                out["toggled"] = "on"
            out["session_id"] = sid
            out["adapter"] = adapter
            flip_path.unlink(missing_ok=True)

    return out or None


def session_allows_speech(
    cfg: dict,
    hook: dict,
    root: Path | None = None,
) -> tuple[bool, str | None]:
    """Return (allowed, skip_reason)."""
    mode = session_mode(cfg)
    if mode == "all":
        return True, None

    adapter = hook_adapter(hook)
    sid = hook_session_id(hook, adapter)
    if not sid:
        return False, "no_session_id"

    if root is None:
        try:
            from aftertone.paths import install_root

            root = install_root()
        except FileNotFoundError:
            return mode != "allowlist", "no_install_root"

    data = load_sessions(root)
    bucket = data.get(adapter, [])
    if mode == "allowlist":
        if sid in bucket:
            return True, None
        return False, "not_allowlisted"
    if sid in bucket:
        return False, "denylisted"
    return True, None


def cmd_session_on(root: Path) -> int:
    """Enable spoken TTS for this chat only (default /aftertone-on behavior)."""
    set_enabled_toml(root, True)
    set_session_mode_toml(root, "allowlist")
    _write_pending(root, "on")
    _clear_pending(root, "off")
    state_dir(root).joinpath(_PENDING_FLIP).unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "scope": "session",
                "session_mode": "allowlist",
                "pending": "on",
                "hint": "Spoken TTS for this chat only. Send any agent reply here to register; use /aftertone-on in other chats to enable them.",
            }
        )
    )
    return 0


def cmd_session_toggle(root: Path) -> int:
    set_enabled_toml(root, True)
    set_session_mode_toml(root, "allowlist")
    _clear_pending(root, "on")
    _clear_pending(root, "off")
    flip_path = state_dir(root) / _PENDING_FLIP
    flip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = flip_path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"action": "flip", "ts": time.time()}) + "\n", encoding="utf-8")
    os.replace(tmp, flip_path)
    print(
        json.dumps(
            {
                "scope": "session",
                "pending": "flip",
                "hint": "Next reply in this chat toggles speech on or off for this chat only.",
            }
        )
    )
    return 0


def cmd_session_off(root: Path, session_id: str | None = None) -> int:
    """Disable spoken TTS for this chat only (default /aftertone-off behavior)."""
    if session_id:
        removed_any = False
        for adapter in ("cursor", "claude", "codex"):
            if _remove_session(root, adapter, session_id):
                removed_any = True
        print(
            json.dumps(
                {
                    "removed": session_id,
                    "ok": removed_any,
                    "sessions": load_sessions(root),
                }
            )
        )
        return 0

    _write_pending(root, "off")
    _clear_pending(root, "on")
    state_dir(root).joinpath(_PENDING_FLIP).unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "scope": "session",
                "pending": "off",
                "hint": "Spoken TTS off for this chat after your next reply. Other chats are unchanged.",
            }
        )
    )
    return 0


def cmd_session_list(root: Path) -> int:
    from aftertone.config import load_config

    cfg_mode = session_mode(load_config(root))
    print(
        json.dumps(
            {
                "session_mode": cfg_mode,
                "sessions": load_sessions(root),
                "pending_on": _read_pending(root, "on") is not None,
                "pending_off": _read_pending(root, "off") is not None,
            },
            indent=2,
        )
    )
    return 0


def cmd_session_clear(root: Path) -> int:
    save_sessions(root, _empty_sessions())
    _clear_all_pending(root)
    print(json.dumps({"sessions": load_sessions(root), "cleared": True}))
    return 0


def cmd_global_off(root: Path) -> int:
    """Mute all chats (legacy global kill switch)."""
    set_enabled_toml(root, False)
    _clear_all_pending(root)
    print(
        json.dumps(
            {
                "scope": "global",
                "enabled": False,
                "hint": "Spoken TTS off everywhere. Use /aftertone-on in a chat for speech there only.",
            }
        )
    )
    return 0
