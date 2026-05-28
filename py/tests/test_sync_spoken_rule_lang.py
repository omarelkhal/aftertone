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
    (repo / ".cursor/hooks/speak_summary.toml").write_text(
        'lang = "fr"\n',
        encoding="utf-8",
    )
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
