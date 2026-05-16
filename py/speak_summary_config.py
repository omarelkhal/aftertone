#!/usr/bin/env python3
"""Read or update speak_summary.toml settings (lang, speed, mode, voice). No hook restart for most keys."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from expression_tags import EXPRESSION_MODES, normalize_mode
from helper import AVAILABLE_LANGS
from voice_presets import (
    DEFAULT_VOICE_ORDER,
    resolve_voice_preset_id,
    voice_display_name,
    voice_picker_line,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

_SPEED_MIN = 0.5
_SPEED_MAX = 2.0
_MODES = frozenset({"queue", "interrupt"})
# Supertonic-3 voice_style stems (used before assets are downloaded).
_DEFAULT_VOICE_PRESETS = frozenset(
    {f"F{i}" for i in range(1, 6)} | {f"M{i}" for i in range(1, 6)}
)


def _repo_root(explicit: Path | None) -> Path:
    from aftertone_paths import resolve_repo_root

    return resolve_repo_root(explicit)


def _py_dir() -> Path:
    return Path(__file__).resolve().parent


def _toml_path(repo: Path) -> Path:
    return repo / ".cursor" / "hooks" / "speak_summary.toml"


def _load_cfg(toml_path: Path) -> dict:
    with toml_path.open("rb") as f:
        return tomllib.load(f)


def _key_line_pattern(key: str) -> re.Pattern[str]:
    return re.compile(
        rf"^(\s*){re.escape(key)}\s*=\s*.*?(#.*)?$",
        re.IGNORECASE | re.MULTILINE,
    )


def _replace_key(text: str, key: str, value_line: str) -> str:
    """Replace one `key = ...` line; value_line is full RHS e.g. '"fr"' or '1.05'."""
    pat = _key_line_pattern(key)
    if pat.search(text):
        return pat.sub(
            lambda m: f"{m.group(1)}{key} = {value_line}{m.group(2) or ''}",
            text,
            count=1,
        )
    return text.rstrip() + f"\n{key} = {value_line}\n"


def _read_enabled(cfg: dict) -> bool:
    v = cfg.get("enabled", True)
    if isinstance(v, str):
        return v.strip().lower() not in ("0", "false", "no", "off")
    return bool(v)


def _voice_styles_dir(repo: Path) -> Path:
    return repo / "assets" / "voice_styles"


def _list_voice_presets(repo: Path) -> list[str]:
    d = _voice_styles_dir(repo)
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def _resolve_voice_arg(repo: Path, arg: str) -> tuple[str, str]:
    """
    Return (voice_type, voice_style) for TOML.
    Preset id -> voice_type only, voice_style cleared.
    Path or *.json -> voice_style set, voice_type left as preset placeholder.
    """
    raw = arg.strip()
    if not raw:
        raise ValueError("voice argument is empty")
    if "/" not in raw and not raw.endswith(".json"):
        by_name = resolve_voice_preset_id(raw)
        if by_name:
            raw = by_name
    if "/" in raw or raw.endswith(".json"):
        style = raw if raw.endswith(".json") else f"{raw}.json"
        if not style.startswith("../") and not style.startswith("/"):
            style = f"../assets/voice_styles/{Path(style).name}"
        return ("M1", style)
    preset = raw.removesuffix(".json")
    presets = _list_voice_presets(repo)
    known = set(presets) | _DEFAULT_VOICE_PRESETS
    if preset not in known:
        hint = ", ".join(presets) if presets else ", ".join(sorted(_DEFAULT_VOICE_PRESETS))
        raise ValueError(f"unknown voice preset {preset!r}; available: {hint}")
    return (preset, "")


def _sync_spoken_rule(repo: Path) -> int:
    from sync_spoken_rule_lang import sync_rule

    return sync_rule(repo, check_only=False)


def _daemon_restart(repo: Path) -> int:
    py = _py_dir()
    cmd = [sys.executable, str(py / "tts_daemon_ctl.py"), "restart", "--repo-root", str(repo)]
    import shutil

    uv = shutil.which("uv")
    if uv:
        cmd = [uv, "run", "--directory", str(py), "python", "tts_daemon_ctl.py", "restart", "--repo-root", str(repo)]
    proc = subprocess.run(cmd, cwd=str(py))
    return proc.returncode


def cmd_status(repo: Path) -> int:
    toml_path = _toml_path(repo)
    if not toml_path.is_file():
        print(f"error: missing {toml_path}", file=sys.stderr)
        return 1
    cfg = _load_cfg(toml_path)
    enabled = _read_enabled(cfg)
    lang = str(cfg.get("lang", "en"))
    speed = cfg.get("speed", 1.05)
    mode = str(cfg.get("mode", "queue")).lower()
    vt = str(cfg.get("voice_type", "M1"))
    vs = str(cfg.get("voice_style", "") or "").strip()
    print(f"enabled: {'on' if enabled else 'off'}")
    print(f"lang: {lang}")
    print(f"speed: {speed}")
    print(f"mode: {mode}")
    print(f"expression_mode: {normalize_mode(cfg.get('expression_mode', 'off'))}")
    print(f"voice_type: {vt} ({voice_display_name(vt)})")
    print(f"voice_style: {vs or '(empty, uses voice_type)'}")
    print("hook_keys_no_restart: lang, speed, mode, enabled, heuristics, quiet_hours")
    print("daemon_restart_needed_for: voice_style, voice_type, port, onnx_dir, use_gpu")
    return 0


def cmd_set_lang(repo: Path, code: str) -> int:
    lang = code.strip().lower()
    if lang not in AVAILABLE_LANGS:
        print(
            f"error: invalid lang {code!r}; must be one of: {', '.join(AVAILABLE_LANGS)}",
            file=sys.stderr,
        )
        return 1
    toml_path = _toml_path(repo)
    text = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(_replace_key(text, "lang", f'"{lang}"'), encoding="utf-8")
    print(f"lang={lang}")
    rc = _sync_spoken_rule(repo)
    if rc != 0:
        print("warning: sync_spoken_rule_lang failed", file=sys.stderr)
        return rc
    print("synced .cursor/rules/spoken-summary.mdc")
    return 0


def cmd_set_speed(repo: Path, value: str) -> int:
    try:
        speed = float(value)
    except ValueError:
        print(f"error: speed must be a number, got {value!r}", file=sys.stderr)
        return 1
    if not (_SPEED_MIN <= speed <= _SPEED_MAX):
        print(
            f"error: speed {speed} out of range [{_SPEED_MIN}, {_SPEED_MAX}]",
            file=sys.stderr,
        )
        return 1
    toml_path = _toml_path(repo)
    text = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(_replace_key(text, "speed", str(speed)), encoding="utf-8")
    print(f"speed={speed}")
    return 0


def cmd_set_mode(repo: Path, value: str) -> int:
    mode = value.strip().lower()
    if mode not in _MODES:
        print(f"error: mode must be queue or interrupt, got {value!r}", file=sys.stderr)
        return 1
    toml_path = _toml_path(repo)
    text = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(_replace_key(text, "mode", f'"{mode}"'), encoding="utf-8")
    print(f"mode={mode}")
    return 0


def cmd_set_voice(repo: Path, arg: str, *, restart: bool, ensure: bool) -> int:
    if ensure and not _list_voice_presets(repo):
        rc = _run_bootstrap(repo)
        if rc != 0:
            return rc
    try:
        voice_type, voice_style = _resolve_voice_arg(repo, arg)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    toml_path = _toml_path(repo)
    text = toml_path.read_text(encoding="utf-8")
    text = _replace_key(text, "voice_type", f'"{voice_type}"')
    if voice_style:
        text = _replace_key(text, "voice_style", f'"{voice_style}"')
    else:
        text = _replace_key(text, "voice_style", '""')
    toml_path.write_text(text, encoding="utf-8")
    print(
        f"voice={voice_display_name(voice_type)} ({voice_type}) "
        f"voice_style={voice_style or '(empty)'}"
    )
    print("daemon_restart_required: true", file=sys.stderr)
    if restart:
        print("restarting daemon...", file=sys.stderr)
        return _daemon_restart(repo)
    print(
        "run: cd py && uv run python tts_daemon_ctl.py restart --repo-root ..",
        file=sys.stderr,
    )
    return 0


def _run_bootstrap(repo: Path) -> int:
    script = repo / "scripts" / "bootstrap.sh"
    if not script.is_file():
        print(f"error: missing {script}", file=sys.stderr)
        return 1
    env = {**os.environ, "SKIP_WEB": "1"}
    print("fetching assets (bootstrap)…", file=sys.stderr)
    proc = subprocess.run(["bash", str(script)], cwd=str(repo), env=env)
    return proc.returncode


def cmd_list_voices(repo: Path, *, ensure: bool) -> int:
    if ensure and not _list_voice_presets(repo):
        rc = _run_bootstrap(repo)
        if rc != 0:
            return rc
    presets = _list_voice_presets(repo)
    if not presets:
        print(
            "no voice JSON files under assets/voice_styles/ "
            "(run: bash scripts/bootstrap.sh)",
            file=sys.stderr,
        )
        return 1
    print(" ".join(presets))
    return 0


def _ordered_presets(repo: Path) -> list[str]:
    on_disk = set(_list_voice_presets(repo))
    if not on_disk:
        return list(DEFAULT_VOICE_ORDER)
    ordered = [p for p in DEFAULT_VOICE_ORDER if p in on_disk]
    ordered.extend(sorted(on_disk - set(ordered)))
    return ordered


def cmd_voice_picker(repo: Path) -> int:
    """Print id|label lines for Agent AskQuestion (Supertonic display names)."""
    for pid in _ordered_presets(repo):
        print(voice_picker_line(pid))
    return 0


def cmd_list_langs() -> int:
    print(" ".join(AVAILABLE_LANGS))
    return 0


# Curated labels for interactive pickers (codes must stay in AVAILABLE_LANGS).
_LANG_PICKER: tuple[tuple[str, str], ...] = (
    ("en", "English (en)"),
    ("fr", "French (fr)"),
    ("de", "German (de)"),
    ("es", "Spanish (es)"),
    ("it", "Italian (it)"),
    ("pt", "Portuguese (pt)"),
    ("ja", "Japanese (ja)"),
    ("ko", "Korean (ko)"),
    ("ar", "Arabic (ar)"),
    ("hi", "Hindi (hi)"),
    ("ru", "Russian (ru)"),
    ("nl", "Dutch (nl)"),
    ("pl", "Polish (pl)"),
    ("tr", "Turkish (tr)"),
    ("vi", "Vietnamese (vi)"),
)


def cmd_lang_picker() -> int:
    """Print id|label lines for Agent AskQuestion (common languages only)."""
    for code, label in _LANG_PICKER:
        if code in AVAILABLE_LANGS:
            print(f"{code}|{label}")
    print("other|Other language (you will type the code)")
    return 0


_SPEED_PICKER: tuple[tuple[str, str], ...] = (
    ("0.9", "Slower (0.9)"),
    ("1.0", "Normal (1.0)"),
    ("1.05", "Default (1.05)"),
    ("1.1", "Slightly faster (1.1)"),
    ("1.2", "Faster (1.2)"),
    ("1.5", "Fast (1.5)"),
)


def cmd_speed_picker() -> int:
    for value, label in _SPEED_PICKER:
        print(f"{value}|{label}")
    return 0


_EXPRESSION_PICKER: tuple[tuple[str, str], ...] = (
    ("off", "Off — plain speech only"),
    ("subtle", "Subtle — sigh on blocked (recommended)"),
    ("expressive", "Expressive — sigh and breath on more states"),
    ("passthrough", "Passthrough — keep one inline tag you write"),
)


def cmd_expression_picker() -> int:
    for value, label in _EXPRESSION_PICKER:
        print(f"{value}|{label}")
    return 0


def cmd_set_expression(repo: Path, value: str) -> int:
    mode = value.strip().lower()
    if mode not in EXPRESSION_MODES:
        allowed = ", ".join(sorted(EXPRESSION_MODES))
        print(
            f"error: expression_mode must be one of: {allowed}, got {value!r}",
            file=sys.stderr,
        )
        return 1
    toml_path = _toml_path(repo)
    text = toml_path.read_text(encoding="utf-8")
    toml_path.write_text(
        _replace_key(text, "expression_mode", f'"{mode}"'), encoding="utf-8"
    )
    print(f"expression_mode={mode}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure speak_summary.toml (lang, speed, mode, voice)."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Aftertone repo root (default: AFTERTONE_REPO or parent of py/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Print current TOML settings")

    p_voices = sub.add_parser(
        "voices", help="List voice_type presets from assets/voice_styles/"
    )
    p_voices.add_argument(
        "--ensure",
        action="store_true",
        help="Run scripts/bootstrap.sh if no voice JSON files are present",
    )

    sub.add_parser("langs", help="Print all supported lang codes (space-separated)")
    sub.add_parser(
        "voice-picker",
        help="Print id|label lines for voice presets (James (male), …)",
    )
    sub.add_parser(
        "lang-picker",
        help="Print id|label lines for common languages (for interactive pickers)",
    )
    sub.add_parser(
        "speed-picker",
        help="Print id|label lines for common speed values",
    )
    sub.add_parser(
        "expression-picker",
        help="Print id|label lines for expression_mode (for interactive pickers)",
    )

    p_set = sub.add_parser("set", help="Update one setting")
    set_sub = p_set.add_subparsers(dest="setting", required=True)

    p_lang = set_sub.add_parser("lang", help="Set lang and sync spoken-summary rule")
    p_lang.add_argument("code", help=f"Language code ({len(AVAILABLE_LANGS)} supported)")

    p_speed = set_sub.add_parser("speed", help="Set playback speed")
    p_speed.add_argument("value", help=f"Float in [{_SPEED_MIN}, {_SPEED_MAX}]")

    p_mode = set_sub.add_parser("mode", help="Set queue or interrupt")
    p_mode.add_argument("value", choices=sorted(_MODES))

    p_expr = set_sub.add_parser(
        "expression",
        help="Set expression_mode (off, subtle, expressive, passthrough)",
    )
    p_expr.add_argument("value", help="Expression mode name")

    p_voice = set_sub.add_parser("voice", help="Set voice_type or voice_style path")
    p_voice.add_argument("value", help="Preset (M1, F2, …) or path to .json")
    p_voice.add_argument(
        "--restart",
        action="store_true",
        help="Restart tts_daemon after updating voice",
    )
    p_voice.add_argument(
        "--ensure",
        action="store_true",
        help="Run bootstrap if assets/voice_styles/*.json are missing",
    )

    args = parser.parse_args()
    repo = _repo_root(args.repo_root)
    toml_path = _toml_path(repo)
    if args.command not in (
        "voices",
        "voice-picker",
        "langs",
        "lang-picker",
        "speed-picker",
        "expression-picker",
    ) and not toml_path.is_file():
        print(f"error: missing {toml_path}", file=sys.stderr)
        return 1

    if args.command == "status":
        return cmd_status(repo)
    if args.command == "voices":
        return cmd_list_voices(repo, ensure=args.ensure)
    if args.command == "voice-picker":
        return cmd_voice_picker(repo)
    if args.command == "langs":
        return cmd_list_langs()
    if args.command == "lang-picker":
        return cmd_lang_picker()
    if args.command == "speed-picker":
        return cmd_speed_picker()
    if args.command == "expression-picker":
        return cmd_expression_picker()
    if args.setting == "lang":
        return cmd_set_lang(repo, args.code)
    if args.setting == "speed":
        return cmd_set_speed(repo, args.value)
    if args.setting == "mode":
        return cmd_set_mode(repo, args.value)
    if args.setting == "expression":
        return cmd_set_expression(repo, args.value)
    if args.setting == "voice":
        return cmd_set_voice(
            repo, args.value, restart=args.restart, ensure=args.ensure
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
