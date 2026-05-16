#!/usr/bin/env python3
"""Start/stop/status for py/tts_daemon.py (Aftertone; PID + port under .cursor/hooks/state/)."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]


def _repo_root() -> Path:
    env = (
        os.environ.get("AFTERTONE_REPO", "").strip()
        or os.environ.get("SUPERTONIC_REPO", "").strip()
    )
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def _py_dir() -> Path:
    return Path(__file__).resolve().parent


def _state_dir(repo: Path) -> Path:
    d = repo / ".cursor" / "hooks" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pid_path(repo: Path) -> Path:
    return _state_dir(repo) / "tts-daemon.pid"


def _port_path(repo: Path) -> Path:
    return _state_dir(repo) / "tts-daemon.port"


def _hook_toml(repo: Path) -> Path:
    return repo / ".cursor" / "hooks" / "speak_summary.toml"


def _load_hook_config(repo: Path) -> dict:
    p = _hook_toml(repo)
    if not p.is_file():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f)


def _voice_style_from_cfg(cfg: dict) -> str:
    """Explicit voice_style path, or ../assets/voice_styles/<voice_type>.json relative to py/."""
    vs = str(cfg.get("voice_style", "") or "").strip()
    if vs:
        return vs
    vt = str(cfg.get("voice_type", "M1") or "M1").strip() or "M1"
    if not vt.lower().endswith(".json"):
        vt = f"{vt}.json"
    return f"../assets/voice_styles/{vt}"


def _read_pid(repo: Path) -> int | None:
    pp = _pid_path(repo)
    if not pp.is_file():
        return None
    try:
        return int(pp.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _read_port(repo: Path) -> int | None:
    pp = _port_path(repo)
    if not pp.is_file():
        return None
    try:
        return int(pp.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _uv_cmd(py_dir: Path, args: list[str]) -> list[str]:
    import shutil

    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "--directory", str(py_dir), "python"] + args
    return [sys.executable] + args


def _print_hook_toml_summary(repo: Path) -> None:
    cfg = _load_hook_config(repo)
    p = _hook_toml(repo)
    if not p.is_file():
        print(f"speak_summary.toml: missing ({p})")
        return
    if not cfg:
        print(f"speak_summary.toml: empty or unreadable ({p})")
        return
    vs = _voice_style_from_cfg(cfg)
    print(
        f"speak_summary.toml (disk): port={cfg.get('port', 8765)!r} "
        f"voice_style={vs!r} lang={cfg.get('lang', 'en')!r} "
        f"speed={cfg.get('speed', 1.05)!r} use_gpu={cfg.get('use_gpu', False)!r}"
    )
    print(
        "toml hint: port / onnx_dir / voice / use_gpu → restart daemon to apply. "
        "speed / lang / total_step / max_chars / heuristics / enabled / quiet_hours → each hook, no restart."
    )


def cmd_status(repo: Path) -> int:
    _print_hook_toml_summary(repo)
    pid = _read_pid(repo)
    port = _read_port(repo)
    if pid is None or not _pid_alive(pid):
        print("tts_daemon: not running")
        return 1
    print(
        f"tts_daemon: running pid={pid} port={port} "
        "(POST /say uses this port file; if it disagrees with TOML, see port_mismatch in speak_summary-hook.log)"
    )
    if port:
        try:
            import urllib.request

            u = urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2)
            print(u.read().decode()[:500])
        except Exception as e:
            print(f"healthz: {e}")
    return 0


def cmd_stop(repo: Path) -> int:
    pid = _read_pid(repo)
    if pid is None:
        print("tts_daemon: not running")
        return 0
    if not _pid_alive(pid):
        _pid_path(repo).unlink(missing_ok=True)
        print("tts_daemon: stale pid removed")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        _pid_path(repo).unlink(missing_ok=True)
        return 0
    for _ in range(30):
        time.sleep(0.1)
        if not _pid_alive(pid):
            break
    _pid_path(repo).unlink(missing_ok=True)
    print("tts_daemon: stopped")
    return 0


def cmd_start(repo: Path, port_override: int | None) -> int:
    pid = _read_pid(repo)
    if pid is not None and _pid_alive(pid):
        print("tts_daemon: already running")
        return 0
    cfg = _load_hook_config(repo)
    port = port_override or int(cfg.get("port", 8765))
    use_gpu = bool(cfg.get("use_gpu", False))
    onnx_dir = str(cfg.get("onnx_dir", "../assets/onnx"))
    voice_style = _voice_style_from_cfg(cfg)
    lang = str(cfg.get("lang", "en"))

    py_dir = _py_dir()
    daemon_args = [
        str(py_dir / "tts_daemon.py"),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--onnx-dir",
        onnx_dir,
        "--voice-style",
        voice_style,
        "--lang",
        lang,
        "--repo-root",
        str(repo),
    ]
    if use_gpu:
        daemon_args.append("--use-gpu")

    log_path = _state_dir(repo) / "tts-daemon.log"
    log_f = open(log_path, "a", encoding="utf-8")
    cmd = _uv_cmd(py_dir, daemon_args)
    proc = subprocess.Popen(
        cmd,
        cwd=str(py_dir),
        stdin=subprocess.DEVNULL,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    _pid_path(repo).write_text(str(proc.pid), encoding="utf-8")
    _port_path(repo).write_text(str(port), encoding="utf-8")
    # Wait until healthz or timeout
    deadline = time.monotonic() + 120.0
    ok = False
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            print(f"tts_daemon: process exited early code={proc.poll()} log={log_path}")
            _pid_path(repo).unlink(missing_ok=True)
            return 1
        try:
            import urllib.request

            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
            ok = True
            break
        except Exception:
            time.sleep(0.3)
    if not ok:
        print(f"tts_daemon: healthz timeout; check {log_path}")
        return 1
    print(f"tts_daemon: started pid={proc.pid} port={port}")
    return 0


def cmd_restart(repo: Path, port: int | None) -> int:
    cmd_stop(repo)
    return cmd_start(repo, port)


def main() -> None:
    ap = argparse.ArgumentParser(description="Control Aftertone tts_daemon.")
    ap.add_argument("command", choices=("start", "stop", "status", "restart"))
    ap.add_argument("--repo-root", type=str, default="", help="Repo root (default: infer).")
    ap.add_argument("--port", type=int, default=0, help="Override port for start/restart.")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve() if args.repo_root else _repo_root()
    port = args.port or None
    if args.command == "status":
        raise SystemExit(cmd_status(repo))
    if args.command == "stop":
        raise SystemExit(cmd_stop(repo))
    if args.command == "start":
        raise SystemExit(cmd_start(repo, port))
    if args.command == "restart":
        raise SystemExit(cmd_restart(repo, port))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
