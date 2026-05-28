#!/usr/bin/env python3
"""
Sync the configured speak_summary `lang` into .cursor/rules/spoken-summary.mdc.

Cursor rules are static files; they do not read TOML when the model runs. This
script copies `lang` from speak_summary.toml into a marked block so the agent
prompt always shows the current code (e.g. fr, en) without manual copy-paste.

Run after changing lang in the TOML (from **repository root**, so paths resolve):

  uv run --directory py python sync_spoken_rule_lang.py

Optional: `--repo-root /abs/path/to/repo` if you run from another cwd.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

MARK_START = "<!-- autogen:spoken-lang:start -->\n"
MARK_END = "<!-- autogen:spoken-lang:end -->"


def _load_lang(toml_path: Path) -> str:
    with toml_path.open("rb") as f:
        data = tomllib.load(f)
    raw = data.get("lang", "en")
    lang = str(raw).strip() or "en"
    # single token for display / instruction
    return lang.replace("`", "").replace("\n", "")[:16]


def _blurb(lang: str) -> str:
    return (
        f"> **Locked `lang` for `<spoken_summary>` only:** `{lang}` "
        "(from [`.cursor/hooks/speak_summary.toml`](../hooks/speak_summary.toml)). "
        "The hook does **not** translate. Write the **inner tag** only in that language — "
        "**even when the user writes in another language**; the rest of your reply may follow the user. "
        "After changing `lang` in the TOML, from the **repo root** run: "
        "`uv run --directory py python sync_spoken_rule_lang.py`\n"
    )


def _blurb_claude(lang: str) -> str:
    return (
        f"> **Locked `lang` for `<spoken_summary>` only:** `{lang}` "
        "(from `~/aftertone/.cursor/hooks/speak_summary.toml` on global install). "
        "Write the **inner tag** only in that language — **not** the conversation language. "
        "After changing `lang`, run `/aftertone-lang` or "
        "`uv run --directory py python sync_spoken_rule_lang.py` from the Aftertone repo.\n"
    )


def _blurb_codex(lang: str) -> str:
    return (
        f"> **Locked `lang` for `<spoken_summary>` only:** `{lang}` "
        "(from `~/aftertone/.cursor/hooks/speak_summary.toml` on global install). "
        "Write the **inner tag** only in that language — **not** the conversation language. "
        "After changing `lang`, run `/aftertone-lang` or "
        "`uv run --directory py python sync_spoken_rule_lang.py` from the Aftertone repo.\n"
    )


def _user_cursor_rule_path() -> Path | None:
    """Global install copies the rule to ~/.cursor/rules; keep it in sync with TOML."""
    marker = Path.home() / ".cursor" / "hooks" / "aftertone-install-dir"
    if not marker.is_file():
        return None
    return Path.home() / ".cursor" / "rules" / "spoken-summary.mdc"


def _replace_lang_block(body: str, blurb: str) -> tuple[str, bool]:
    if MARK_START not in body or MARK_END not in body:
        return body, False
    before, rest = body.split(MARK_START, 1)
    _mid, after = rest.split(MARK_END, 1)
    new_block = MARK_START + blurb + MARK_END
    new_body = before + new_block + after
    return new_body, new_body != body


def sync_rule(repo: Path, *, check_only: bool) -> int:
    toml_path = repo / ".cursor" / "hooks" / "speak_summary.toml"
    mdc_path = repo / ".cursor" / "rules" / "spoken-summary.mdc"
    if not toml_path.is_file():
        print(f"error: missing {toml_path}", file=sys.stderr)
        return 2
    if not mdc_path.is_file():
        print(f"error: missing {mdc_path}", file=sys.stderr)
        return 2

    lang = _load_lang(toml_path)
    body = mdc_path.read_text(encoding="utf-8")
    if MARK_START not in body or MARK_END not in body:
        print(
            f"error: markers not found in {mdc_path} "
            f"(need {MARK_START.strip()} … {MARK_END})",
            file=sys.stderr,
        )
        return 2

    new_body, changed = _replace_lang_block(body, _blurb(lang))

    claude_rule_src = repo / "scripts" / "claude-global" / "spoken-summary.md"
    claude_changed = False
    if claude_rule_src.is_file():
        claude_body = claude_rule_src.read_text(encoding="utf-8")
        if MARK_START in claude_body and MARK_END in claude_body:
            claude_new, claude_changed = _replace_lang_block(
                claude_body, _blurb_claude(lang)
            )
            if claude_changed and not check_only:
                claude_rule_src.write_text(claude_new, encoding="utf-8")
                print(f"updated {claude_rule_src} (lang={lang})")
        elif not check_only:
            print(f"warn: skip {claude_rule_src} (no lang markers)", file=sys.stderr)

    if claude_rule_src.is_file() and not check_only:
        for dest in (
            Path.home() / ".claude" / "rules" / "spoken-summary.md",
            repo / ".claude" / "rules" / "spoken-summary.md",
        ):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(claude_rule_src, dest)
            print(f"updated {dest}")

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

    if codex_rule_src.is_file() and not check_only:
        dest = Path.home() / ".codex" / "AGENTS.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(codex_rule_src, dest)
        print(f"updated {dest}")

    if not changed and not claude_changed and not codex_changed:
        if check_only:
            print("ok: rules already match TOML")
        else:
            print(f"ok: already synced (lang={lang})")
        return 0

    if check_only:
        print(
            f"error: rule out of sync with TOML (lang={lang}); run without --check",
            file=sys.stderr,
        )
        return 1

    mdc_path.write_text(new_body, encoding="utf-8")
    print(f"updated {mdc_path} (lang={lang})")

    user_mdc = _user_cursor_rule_path()
    if user_mdc is not None:
        user_mdc.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mdc_path, user_mdc)
        print(f"updated {user_mdc} (global Cursor rule, lang={lang})")

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: parent of py/ containing this script)",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the rule file does not match TOML (CI / pre-commit).",
    )
    args = p.parse_args()
    from aftertone_paths import resolve_repo_root

    repo = resolve_repo_root(args.repo_root)
    return sync_rule(repo, check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
